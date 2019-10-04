import numpy as np
import scipy.optimize

# todo
# tune for sets of complex tones with different spectra

class Dissonancereduction:
    """ Tuning algorithm class. Maps a set of notes to a set of frequencies.
    In particular, it provides an algorithm to tune a given set of notes to reduce the innermusical
    dissonance as well as the dissonance between the music and a given set of fixed frequencies.
    
    Attributes
    ----------
    amplitude_threshold : float
        Lowest amplitude where a sine wave at 1 kHz is barely audible.
        (Defaul value = 2e-5, the threshold of hearing in Air in Pa)
    method : str
        Optimization method to use. See scipy.optimize.minimize for options. (Defaul value = "L-BFGS-B")
    relative_bounds : pair of floats
        Lower and upper bound of the range around each fundamental frequency the algorithm searches.
        Given as an interval. If the given optimization method does not support bounds you will see a warning but other
        than that the bounds are just ignored.
        (Default value: (2**(-1/36), 2**(1/36)), which means 1/3 of an equal tempered semitone up and down)
    max_iterations : int
        Maximal number of iteration of the optimization method.
        If None is given the method optimizes until it stops for some other reason. (Default value = None)
    """

    def __init__(self, amplitude_threshold = 2e-5,
                 method="L-BFGS-B", relative_bounds=(2**(-1/36), 2**(1/36)), max_iterations=None):
        """__init__ method
        
        Parameters
        ----------
        amplitude_threshold : float
        Lowest amplitude where a sine wave at 1 kHz is barely audible.
            (Defaul value = 2e-5, the threshold of hearing in Air in Pa)
        method : string
            Optimization method to use. See scipy.optimize.minimize for options. (Defaul value = "L-BFGS-B")
        relative_bounds : pair of floats
            Lower and upper bound of the range around each fundamental frequency the algorithm searches.
            Given as an interval. If the given optimization method does not support bounds you will see a warning but other
            than that the bounds are just ignored.
            (Default value: (2**(-1/36), 2**(1/36)), which means 1/3 of an equal tempered semitone up and down)
        max_iterations : int
            Maximal number of iteration of the optimization method.
            If None is given the method optimizes until it stops for some other reason. (Default value = None)
        """
        self.method = method
        self.options = dict()
        self.relative_bounds = relative_bounds
        self.max_iterations = max_iterations
        self.amplitude_threshold = amplitude_threshold
            
    @property
    def max_iterations(self):
        """int : Maximal number of iteration of the optimization method.
        If None is given the method optimizes until it stops for some other reason. (Default value = None)"""
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
            
    @property
    def amplitude_threshold(self):
        """float : Lowest amplitude where a sine wave at 1 kHz is barely audible.
        (Defaul value = 2e-5, the threshold of hearing in Air in Pa)"""
        return 10**self._amp_threshold_log
    
    @amplitude_threshold.setter
    def amplitude_threshold(self, amplitude_threshold):
        if amplitude_threshold <= 0.:
            amplitude_threshold = 1e-10
        self._amp_threshold_log = np.log10(amplitude_threshold)
     
    def quasi_constants(self, fundamentals_freq, fundamentals_amp, partials_pos,
                        partials_amp, fixed_freq, fixed_amp):
        """Calculate quasi-constants for a set of complx tones and fixed frequencies to be tuned.
        Calculate values that will be practically constant during optimization
        as well as sorting out pairs of partials that will never be relevant during tuning.
        This is only technically valid if frequencies are not changed sinificantly more than 1/2 semitone.
        
        Parameters
        ----------
        fundamentals_freq : np.array
            Array of fundamental frequencies of the complex tones.
        fundamentals_amp : np.array
            Array of amplitudes of the complex tones.
        partials_pos : np.array
            Array of relative positions of the partials of the complex tones.
            Assumes a single timbre for all complex tones, tuning complex tones with different timbres is currently
            not supported.
        partials_amp : np.array
            Array of relative amplitudes of the partials of the complex tones.
            Assumes a single timbre for all complex tones, tuning complex tones with different timbres is currently
            not supported.
        fixed_freq : np.array
            Array of fixed frequencies, e.g. some other instrument to tune to or frequencies found in environmental noise.
        fixed_amp : np.array
            Array of amplitudes for the fixed frequencies.
            
        Returns
        -------
        relevant_pairs : np.array
            If [i, k, j, l] in relevant_pairs, then the dissonance of partial k of tone i and partial l of tone 
            j will be relevant to the calculation of the total dissonance.
        critical_bandwidths : np.array
            The critical bandwidths at the mean frequency of every relevant pair.
        volume_factors : np.array
            The volume_factor of every relevant pair.
        """
        
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

        # calculation of difference in CBW
        hs = np.abs(p1s - p2s) / critical_bandwidths
        
        # sorting out irrelevant pairs and preventing errors when taking the log of v later
        cond = np.where(np.logical_and(np.logical_and(hs < 1.46, v1s > 0), v2s > 0))
        critical_bandwidths = critical_bandwidths[cond]
        relevant_pairs = ids[cond].astype(int)
        p1s = p1s[cond]
        p2s = p2s[cond]
        v1s = v1s[cond]
        v2s = v2s[cond]
        
        # approx of auditory level / 20
        # - much easier to calculate than the actual loudness or loudness level and still accurate enough
        # for our purpose as a model of the human loudness perception.
        # Since we are more interested in cutting partials that are outside the human hearing range
        # than subtle differences inside the human hearing range we can drop the second summand of 
        # $L_{pt}(f)$ (see my thesis), loosing the small bump between 2 and 5 kHz, to save even more computation time
        v1s = np.log10(v1s) - self._amp_threshold_log - 45.71633305 * p1s**(-0.8) - 5e-17 * p1s**4
        v2s = np.log10(v2s) - self._amp_threshold_log - 45.71633305 * p2s**(-0.8) - 5e-17 * p2s**4
        
        # sorting out more irrelevant pairs (pairs where at least one of the partials is inaudible)
        cond = np.where(np.logical_and(v1s > 0., v2s > 0.))
        
        # aggregating the volume measures
        volume_factors = np.minimum(v1s[cond], v2s[cond])
        
        return relevant_pairs[cond], critical_bandwidths[cond], volume_factors
    
    def dissonance_and_gradient(self, fundamentals_freq, partials_pos, fixed_freq,
                                critical_bandwidths, volume_factors, relevant_pairs):
        """Calculates the dissonance and its (corrected) gradient.
        Calculates the dissonance of the complex tones together with the fixed frequencies
        and its gradient with respect to the fundamental frequencies of the complex tones.
        The latter is corrected to prevent the "higher is better" behavior.
        
        Parameters
        ----------
        fundamentals_freq : np.array
            Array of fundamental frequencies of the complex tones.
        partials_pos : np.array
            Array of relative positions of the partials of the complex tones.
            Assumes a single timbre for all complex tones, tuning complex tones with different timbres is currently
            not supported.
        fixed_freq : np.array
            Array of fixed frequencies, e.g. some other instrument to tune to or frequencies found in environmental noise.
        critical_bandwidths : np.array
            The critical bandwidths at the mean frequency of every relevant pair. As calculated with quasi_constants.
        volume_factors : np.array
            The volume_factor of every relevant pair. As calculated with quasi_constants.
        relevant_pairs : np.array
            If [i, k, j, l] in relevant_pairs, then the dissonance of partial k of tone i and partial l of tone 
            j will be relevant to the calculation of the total dissonance. As calculated with quasi_constants.
            
        Returns
        -------
        total_dissonance : float
            The total dissonance of the complex tones together with the fixed frequencies.
        gradient : np.array
            Its gradient with respect to the fundamental frequencies of the complex tones.
        """

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
        # (0.5 * (p2s / p1s - 1) + 1) is the correction factor to prevent the "higher is better" behavior
        simple_grads1 = dhdcs * r1s * (0.5 * (p2s / p1s - 1) + 1)  # p2/p1 is the interval from the perspective of p1
        simple_grads2 = dhdcs * r2s * (0.5 * (p1s / p2s - 1) + 1)  # p1/p2 is the interval from the perspective of p2
    

        # sum all simple gradients where complex tone i is involved
        gradient = np.array([np.sum(simple_grads1[relevant_pairs[:,0] == i]) 
                             - np.sum(simple_grads2[relevant_pairs[:,2] == i])
                    for i in range(len(fundamentals_freq))])

        return total_dissonance, gradient
        
    def tune(self, fundamentals_freq, fundamentals_amp, partials_pos, partials_amp, fixed_freq=[], fixed_amp=[]):
        """Tune a set of complex tones.
        Tune a set of complex tones to minimize the dissonance it produces together with a set of fixed frequencies.
        
        Parameters
        ----------
        fundamentals_freq : np.array
            Array of fundamental frequencies of the complex tones.
        fundamentals_amp : np.array
            Array of amplitudes of the complex tones.
        partials_pos : np.array
            Array of relative positions of the partials of the complex tones.
            Assumes a single timbre for all complex tones, tuning complex tones with different timbres is currently
            not supported.
        partials_amp : np.array
            Array of relative amplitudes of the partials of the complex tones.
            Assumes a single timbre for all complex tones, tuning complex tones with different timbres is currently
            not supported.
        fixed_freq : np.array
            Array of fixed frequencies, e.g. some other instrument to tune to or frequencies found in environmental noise.
            (Default value = [])
        fixed_amp : np.array
            Array of amplitudes for the fixed frequencies. (Default value = [])
            
        Returns
        -------
        res : scipy.optimize.optimize.OptimizeResult
            Result of the optimization, see scipy.optimize.optimize.OptimizeResult.
            res.x contains the tuned fundamental frequencies.
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
        """Calculates the dissonance and its (corrected) gradient.
        Calculates the dissonance of the complex tones together with the fixed frequencies
        and its gradient with respect to the fundamental frequencies of the complex tones.
        The latter is corrected to prevent the "higher is better" behavior.
        
        Calculates quasi_constants and dissonance_and_gradient one after the other.
        Just for testing, not optimized for multiple evaluations of similar values you need in optimization.
        
        Parameters
        ----------
        See parameters of quasi_constants
            
        Returns
        -------
        See returns of dissonance_and_gradient
        """
        
        relevant_pairs, critical_bandwidths, volume_factors = self.quasi_constants(
            fundamentals_freq, fundamentals_amp, partials_pos, partials_amp, fixed_freq, fixed_amp
        )
        dissonance, gradient = self.dissonance_and_gradient(
                fundamentals_freq, partials_pos, fixed_freq, critical_bandwidths, volume_factors, relevant_pairs
        )
        return dissonance, gradient
        