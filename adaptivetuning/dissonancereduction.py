import numpy as np
import scipy.optimize

# todo
# doku
# tune auch für verschiedene timbres

class Dissonancereduction:
    """ Tuning algorithm class. Maps a set of notes to a set of frequencies.
    In particular, it provides an algorithm to tune a given set of notes to reduce the innermusical
    dissonance as well as the dissonance between the music and a given set of fixed frequencies.
    
    Attributes
    ----------
    ... TODO
    
    """

    def __init__(self, amplitude_threshold = 0.00002,
                 method="L-BFGS-B", relative_bounds=(2**(-1/36), 2**(1/36)), max_iterations=None):
        self.method = method
        self.options = dict()
        self.relative_bounds = relative_bounds
        self.max_iterations = max_iterations
        if amplitude_threshold <= 0.:
            amplitude_threshold = 0.00000001 
        self.amp_threshold_log = np.log10(amplitude_threshold)
            
    @property
    def max_iterations(self):
        """int : Maximal iterations of the optimization algorithm."""
        if 'maxiter' in self.options:
            return self.options['maxiter']
        else:
            return None
    
    @max_iterations.setter
    def max_iterations(self, max_iterations):
        if max_iterations is None:
            if 'maxiter' in self.options:
                del self.options['maxiter']
        else:
            self.options['maxiter'] = max_iterations
     
    def quasi_constants(self, fundamentals_freq, fundamentals_amp, partials_pos,
                        partials_amp, fixed_freq, fixed_amp):
        """Tune a set of Complex tones.
        
        Parameters
        ----------
        ...
            
        Returns
        -------
        relevant_pairs: np.array
            If [i, k, j, l] in relevant_pairs, then the dissonance of partial k of tone i and partial l of tone 
            j is not zero or close to zero so their dissonance is relevant to the calculation of the total
            dissonance.
        critical_bandwidths: np.array
            The critical bandwidths at the mean frequency of every relevant pair.
        volume_factors: np.array
            The volume_factor of every relevant pair.
        """
        # the loudness values of the partials depend on the frequency of the partials,
        # but during the optimization the changes frequencies are so small that the changes in phon can be
        # neglected
        # -> calculate volume factor
        # once and treat it as a constant during optimization
        # same goes for the bandwidth
        
        if len(fundamentals_freq) == 0 or (len(fundamentals_freq) == 1 and len(fixed_freq) == 0):
            return np.array([]), np.array([]), np.array([])
        
        # a row corresponds to a complex tone
        frequencies = np.outer(fundamentals_freq, partials_pos)
        amplitudes = np.outer(fundamentals_amp, partials_amp)

        # all pairs of partials and their volumes
        # including for every two partials only one pair
        # a partial does not form a pair with itself
        args = np.array([
            [i, k, j, l,
            frequencies[i,k],
            frequencies[j,l],
            amplitudes[i,k],
            amplitudes[j,l]]
            for (i,j) in [(i,j) for i in range(len(fundamentals_freq)) for j in range(i + 1, len(fundamentals_freq))]
            for (k,l) in [(k,l) for k in range(len(partials_pos)) for l in range(len(partials_pos))]
        ] + [[i, k, f, -1,
            frequencies[i,k],
            fixed_freq[f],
            amplitudes[i,k],
            fixed_amp[f]]
            for i in range(len(fundamentals_freq))
            for k in range(len(partials_pos))
            for f in range(len(fixed_freq))
        ])

        ids = args[:,0:4]
        p1s = args[:,4]
        p2s = args[:,5]
        v1s = args[:,6]
        v2s = args[:,7]

        # approximation by Zwicker and Terhardt
        critical_bandwidths = 25 + 75 * (1 + 3.5e-07 * (p1s + p2s)**2)**0.69

        hs = np.abs(p1s - p2s) / critical_bandwidths
        cond = np.where(np.logical_and(np.logical_and(hs < 1.46, v1s > 0), v2s > 0))
        critical_bandwidths = critical_bandwidths[cond]
        relevant_pairs = ids[cond].astype(int)
        p1s = p1s[cond]
        p2s = p2s[cond]
        v1s = v1s[cond]
        v2s = v2s[cond]
        
        # approx of auditory level / 20
        # since we are more interested in cutting partials that are outside the human hearing range
        # than subtle differences inside the human hearing range we can drop the second summand of 
        # $L_{pt}(f)$, loosing the small bump between 2 and 5 kHz, to save even more computation time
        # - much easier to calculate and still accurate enough for our purpose as a model of the
        # human loudness perception.
        v1s = np.log10(v1s) - self.amp_threshold_log - 45.71633305 * p1s**(-0.8) - 5e-17 * p1s**4
        v2s = np.log10(v2s) - self.amp_threshold_log - 45.71633305 * p2s**(-0.8) - 5e-17 * p2s**4
        
        cond = np.where(np.logical_or(v1s > 0., v2s > 0.))
        
        volume_factors = np.minimum(v1s[cond], v2s[cond])
        
        return relevant_pairs[cond], critical_bandwidths[cond], volume_factors
    
    def dissonance_and_gradient(self, fundamentals_freq, partials_pos, fixed_freq,
                                critical_bandwidths, volume_factors, relevant_pairs):
        # Returns dissonance and gradient of dissonance with respect to the fundamentals

        # frequencies of fundamentals are given in absolute values (Hz) in fundamentals
        # frequencies of partials are given relative the the fundamental frequency
        # e.g. [1,2] means that the complex tones are made up of 2 partials: the fundamental and the octave
        # fixed pos are the absolute freqs of the fixed simple tones

        # a row corresponds to a complex tone
        positions = np.outer(fundamentals_freq, partials_pos)

        # all relevant pairs of frequencies of partials
        args = np.array([
            [positions[i,k], positions[j,l]] if l >= 0 else [positions[i,k], fixed_freq[j]]
            for (i, k, j, l) in relevant_pairs
        ])
        try:
            p1s = args[:,0]
            p2s = args[:,1]
        except IndexError:
            # no relevant pairs
            return 0, np.zeros(len(fundamentals_freq))

        # differences between frequencies in critical bandwidth
        hs = np.abs(p1s - p2s) / critical_bandwidths

        # dissonances (roughness / beating) for pairs of simple tones
        ds = hs**2 * np.exp(- 8 * hs)

        total_dissonance = np.sum(ds * volume_factors)

        # calculate gradients:
        dhdcs = volume_factors \
                * 2 * hs * np.exp(- 8 * hs) * (1 - 4 * hs) \
                * np.where(p1s > p2s, np.ones(len(p1s)), -1 * np.ones(len(p1s))) / critical_bandwidths

        # positions of the partials of the relevant pairs relative to their fundamental,
        # partials_pos should be a np.array
        try:
            r1s = partials_pos[relevant_pairs[:,1]]
            r2s = np.where(relevant_pairs[:,3] >= 0, partials_pos[relevant_pairs[:,3]], 0.)
        except TypeError:
            partials_pos = np.array(partials_pos)
            r1s = partials_pos[relevant_pairs[:,1]]
            r2s = np.where(relevant_pairs[:,3] >= 0, partials_pos[relevant_pairs[:,3]], 0.)

        # gradients with respect to fundamental of the first and the second partial of the pair
        #simple_grads1 = dhdcs * r1s
        #simple_grads2 = dhdcs * r2s
        simple_grads1 = dhdcs * r1s * (0.5 * (p2s / p1s - 1) + 1)  # p2/p1 ist das intervall von p1 aus gesehen zum korrigieren
        simple_grads2 = dhdcs * r2s * (0.5 * (p1s / p2s - 1) + 1)  # p1/p2 ist das intervall von p2 aus gesehen zum korrigieren
    

        # sum all simple gradients where complex tone i is involved
        gradient = np.array([np.sum(simple_grads1[relevant_pairs[:,0] == i]) 
                             - np.sum(simple_grads2[relevant_pairs[:,2] == i])
                    for i in range(len(fundamentals_freq))])

        return total_dissonance, gradient
        
    def tune(self, fundamentals_freq, fundamentals_amp, partials_pos, partials_amp, fixed_freq=[], fixed_amp=[]):
        """Tune a set of Complex tones.
        
        Parameters
        ----------
        ...
            
        Returns
        -------
        : optimization result or dictionary
            ...
            
        """
        # If there are no fundamentals, dissonance is 0
        # If there is only one fundamental and no fixed frequencies, dissonance is 0
        if len(fundamentals_freq) == 0:
            res = {
                  'fun': 0,
             'hess_inv': None,
                  'jac': np.array([]),
              'message': b'NO OPTIMIZATION VARIABLE',
                 'nfev': 0,
                  'nit': 0,
               'status': 0,
              'success': True,
                    'x': np.array([])
            }
            return res
        
        relevant_pairs, critical_bandwidths, volume_factors = self.quasi_constants(
            fundamentals_freq, fundamentals_amp, partials_pos, partials_amp, fixed_freq, fixed_amp
        )

        if self.relative_bounds is None:
            bounds = None
        else:
            bounds = [(f * self.relative_bounds[0], f * self.relative_bounds[1]) for f in fundamentals_freq]
        
        res = scipy.optimize.minimize(
            lambda fs: self.dissonance_and_gradient(
                fs, partials_pos, fixed_freq, critical_bandwidths, volume_factors, relevant_pairs
            ),
            fundamentals_freq,
            method=self.method,
            bounds=bounds,
            options=self.options,
            jac=True
        )

        return res
    
    def single_dissonance_and_gradient(self, fundamentals_freq, fundamentals_amp, 
                                       partials_pos, partials_amp, fixed_freq=[], fixed_amp=[]):
        # Not optimized for multiple evaluations
        
        relevant_pairs, critical_bandwidths, volume_factors = self.quasi_constants(
            fundamentals_freq, fundamentals_amp, partials_pos, partials_amp, fixed_freq, fixed_amp
        )
        dissonance, gradient = self.dissonance_and_gradient(
                fundamentals_freq, partials_pos, fixed_freq, critical_bandwidths, volume_factors, relevant_pairs
        )
        return dissonance, gradient
        