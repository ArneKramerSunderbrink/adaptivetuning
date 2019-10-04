import numpy as np
import time

def read_scala(filename):
    """Reads a .scl file and returns the list of intervales in specified there.
    See http://www.huygens-fokker.org/scala/scl_format.html for specification.

    Parameters
    ----------
    filename: str
        Path to the file to be read.

    Returns
    -------
    list of floats
        A list of all intervals (as frequency ratios) specified in the scala file.
    """
    with open(filename) as f:
        lines = f.readlines()
    
    # remove comments and whitespace
    lines = map(lambda l: l.strip(), filter(lambda l: not l.startswith('!'), lines))
    lines = list(lines)
    
    # remove description and take the number of lines that are promised in line 2
    lines = lines[2: int(lines[1])+2]
    
    intervals = []
    for line in lines:
        if line.find(".") >= 0:
            cents = float(line)
            intervals.append(Scale.cents_to_freq_ratio(cents))
        else:
            line = line.split("/")
            if len(line) == 1:
                intervals.append(float(line[0]))
            else:
                intervals.append(float(line[0]) / float(line[1]))
        
    return intervals


def write_scala(intervals, filename, description=None, intervals_in_cents=False):
    """Write a .scl file.
    See http://www.huygens-fokker.org/scala/scl_format.html for specification.

    Parameters
    ----------
    intervals : list of loats
        The intervals to be written to the file.
    filename: str
        Path to the file to be written.
    description : str
        A describton for the header of the file. If None is given,
        description = 'Scala file saved with adaptivetuning ' + time.asctime()
    intervals_in_cents : bool
        Specifies whether the intervals given in the first parameter are given in cents or as frequency ratios.
    """
    if not intervals_in_cents:
        intervals = [Scale.freq_ratio_to_cents(i) for i in intervals]
    
    if description is None:
        description = 'Scala file saved with adaptivetuning ' + time.asctime()
    
    lines = ['! ' + filename, ' ' + description, ' ' + str(len(intervals)), '!']
    lines += [' ' + str(float(i)) for i in intervals]

    with open(filename, 'w') as f:
        f.write('\n'.join(lines))


class Scale:
    """Scale class. Manages a dictionary that assigns every pitches a frequency.
    
    In general: Everywhere where a pitch can be given as an argument, it can be given as an int representing its
    midi number or a str of the format 'A4', 'A#4', 'Bb4', etc. 
    
    Attributes
    ----------
    reference_pitch : int
        The reference pitch used in tune_all and similar methods. (Default value = 69)
    reference_frequency : float
        Frequency of Reference pitch (Hz), used in methods like tune_pitch_by_interval and similar methods. > 0.
        Important: the reference is not part of the Scale,
        i.e. scale[reference_pitch] (or any other method to acces a tuning) does not necesseraly
        return reference_frequency and scale[reference_pitch] = f (or any other tuning method)
        never changes the reference_frequency. (Default value = 440)
    pitches_per_octave : int
        The number of pitches per octave used in tune_all and similar methods. (Default value = 12)
    octave_interval : float
        Frequency ratio of the octave used in tune_pitchclass and similar methods. (Default value = 2)
    specified_pitches : dict_keys
        Pitches for wich frequencies are specified. Nonempty, positive values.
        Can be set with list or range.
        New specified pitches are set to 0. (Default value = range(128))
    on_change : function
        Gets called every time a tuning changes (e.g. to signal an audiogenerator).
        Arguments: pitch, frequency
        If you don't want all the messages from the initial setting of the scale, set the onchange after
        the initialisation.
        Set to None if you don't want a callback. (Default value = None)
    """
    
    """Dictionary with Name and nr semitones of all pitchclasses"""
    pitchclasses = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
        'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    }
    
    """Some historical tuning rounded to nearest cent
    all intended to be 12-tone scales with octave = 2"""
    tunings_in_cents = {
        '12TET':        [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100],
        
        # From Loy 2011: Musimathics, p. 56
        'Pythagorean':  [0,  90, 204, 294, 408, 498, 612, 702, 792, 906,  996, 1110],
        'Natural (JI)': [0, 112, 204, 316, 386, 498, 610, 702, 814, 884,  996, 1088],
        
        # Historical tunings found in Sethares 2005: Tuning, Timbre, Spectrum, Scale, p. 377
        '1/4 Comma A':  [0,  76, 193, 310, 386, 503, 580, 697, 772, 890, 1007, 1083],
        'Barca':        [0,  92, 197, 296, 393, 498, 590, 698, 794, 895,  996, 1092],
        'Barca A':      [0,  92, 200, 296, 397, 498, 594, 702, 794, 899,  998, 1095],
        'Bethisy':      [0,  87, 193, 289, 386, 492, 589, 697, 787, 890,  993, 1087],
        'Chaumont':     [0,  76, 193, 289, 386, 503, 580, 697, 773, 890,  996, 1083],
        'Corrette':     [0,  76, 193, 289, 386, 503, 580, 697, 783, 890,  996, 1083],
        "d'Alembert":   [0,  87, 193, 290, 386, 497, 587, 697, 787, 890,  994, 1087],
        'Kirnberger 2': [0,  90, 204, 294, 386, 498, 590, 702, 792, 895,  996, 1088],
        'Kirnberger 3': [0,  90, 193, 294, 386, 498, 590, 697, 792, 890,  996, 1088],
        'Marpourg':     [0,  84, 193, 294, 386, 503, 580, 697, 789, 890,  999, 1083],
        'Rameau b':     [0,  93, 193, 305, 386, 503, 582, 697, 800, 890, 1007, 1083],
        'Rameau #':     [0,  76, 193, 286, 386, 498, 580, 697, 775, 890,  993, 1038],
        'Valloti':      [0,  90, 196, 294, 392, 498, 588, 698, 792, 894,  996, 1090],
        'Valloti A':    [0,  90, 200, 294, 396, 498, 592, 702, 792, 898,  996, 1094],
        'Werkmeister 3':[0,  90, 192, 294, 390, 498, 588, 696, 792, 888,  996, 1092],
        'Werkmeister 4':[0,  82, 196, 294, 392, 498, 588, 694, 784, 890, 1004, 1086],
        'Werkmeister 5':[0,  96, 204, 300, 396, 504, 600, 702, 792, 900, 1002, 1098]
    }
    
    def __init__(self, reference_pitch=69, reference_frequency=440,
                 pitches_per_octave=12, octave_interval=2, specified_pitches=range(128),
                 init_ET=True, on_change=None):
        """__init__ method
        
        Parameters
        ----------
        reference_pitch : int
            The reference pitch used in tune_all and similar methods. (Default value = 69)
        reference_frequency : float
            Frequency of Reference pitch (Hz), used in methods like tune_pitch_by_interval and similar methods. > 0.
            Important: the reference is not part of the Scale,
            i.e. scale[reference_pitch] (or any other method to acces a tuning) does not necesseraly
            return reference_frequency and scale[reference_pitch] = f (or any other tuning method)
            never changes the reference_frequency. (Default value = 440)
        pitches_per_octave : int
            The number of pitches per octave used in tune_all and similar methods. (Default value = 12)
        octave_interval : float
            Frequency ratio of the octave used in tune_pitchclass and similar methods. (Default value = 2)
        specified_pitches : dict_keys
            Pitches for wich frequencies are specified. Nonempty, positive values.
            Can be set with list or range.
            New specified pitches are set to 0. (Default value = range(128))
        init_ET : bool
            If true, initialize all frequencies with tune_all_equal_temperament, else initialize to all to 0.
            (Default value = True)
        on_change : function
            Gets called every time a tuning changes (e.g. to signal an audiogenerator).
            Arguments: pitch, frequency
            If you don't want all the messages from the initial setting of the scale, set the onchange after
            the initialisation.
            Set to None if you don't want a callback. (Default value = None)
        """
        # specified pitches is range or list, when list then strings are possible
        
        if isinstance(reference_pitch, str):
            reference_pitch = Scale.pitchname_to_pitch(reference_pitch)
        self.reference_pitch = reference_pitch
        self.reference_frequency = reference_frequency
        self.pitches_per_octave = pitches_per_octave
        self.octave_interval = octave_interval
        self.on_change = on_change
        
        
        if isinstance(specified_pitches, list):
            for i in range(len(specified_pitches)):
                if isinstance(specified_pitches[i], str):
                    specified_pitches[i] = Scale.pitchname_to_pitch(specified_pitches[i])
        
        self.dictionary = {i: 0 for i in specified_pitches}
        if init_ET:
            self.tune_all_equal_temperament()
    
    @property
    def specified_pitches(self):
        """dict_keys : Pitches for wich frequencies are specified. Nonempty, positive values.
        Can be set with list (of int or str) or range.
        New specified pitches are set to 0. (Default value = range(128))
        """
        return self.dictionary.keys()
    
    @specified_pitches.setter
    def specified_pitches(self, specified_pitches):
        if isinstance(specified_pitches, list):
            for i in range(len(specified_pitches)):
                if isinstance(specified_pitches[i], str):
                    specified_pitches[i] = Scale.pitchname_to_pitch(specified_pitches[i])
        
        self.dictionary = {i: self[i] if i in self.specified_pitches else 0
                           for i in specified_pitches}
    
    @property
    def reference_pitch(self):
        """int : The reference pitch used in tune_all and similar methods. (Default value = 69)"""
        return self._reference_pitch
    
    @reference_pitch.setter
    def reference_pitch(self, reference_pitch):
        if isinstance(reference_pitch, str):
            reference_pitch = Scale.pitchname_to_pitch(reference_pitch)
        self._reference_pitch = reference_pitch
        
    @property
    def reference_frequency(self):
        """float : Frequency of Reference pitch (Hz), used in methods like tune_pitch_by_interval and similar methods. > 0.
        Important: the reference is not part of the Scale,
        i.e. scale[reference_pitch] (or any other method to acces a tuning) does not necesseraly
        return reference_frequency and scale[reference_pitch] = f (or any other tuning method)
        never changes the reference_frequency. (Default value = 440)
        """
        return self._reference_frequency
    
    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = reference_frequency
    
    @property
    def pitches_per_octave(self):
        """int : The number of pitches per octave used in tune_all and similar methods. (Default value = 12)"""
        return self._pitches_per_octave
    
    @pitches_per_octave.setter
    def pitches_per_octave(self, pitches_per_octave):
        self._pitches_per_octave = pitches_per_octave
    
    @property
    def octave_interval(self):
        """float : Frequency ratio of the octave used in tune_pitchclass and similar methods. (Default value = 2)"""
        return self._octave_interval
    
    @octave_interval.setter
    def octave_interval(self, octave_interval):
        self._octave_interval = octave_interval
    
    @property
    def on_change(self):
        """Function : Gets called every time a tuning changes (e.g. to signal an audiogenerator).
        Arguments: pitch, frequency
        If you don't want all the messages from the initial setting of the scale, set the onchange after
        the initialisation.
        Set to None if you don't want a callback. (Default value = None)
        """
        return self._on_change
    
    @on_change.setter
    def on_change(self, on_change):
        if on_change is not None: staticmethod(on_change)
        self._on_change = on_change
     
    def __getitem__(self, index):
        """Access elements of the pitch-frequency-dictionary through slicing.
        
        Parameters
        ----------
        index : int or str or slice or tuple of int and str
            Slicing argument.
            
        Returns
        -------
        a : float or list
            The frequency the pitch
        """
        if isinstance(index, int) or isinstance(index, float):
            try:
                return self.dictionary[index]
            except KeyError:
                index = min(self.specified_pitches, key=lambda p: abs(index - p))
                return self.dictionary[index]
        elif isinstance(index, str):
            index = Scale.pitchname_to_pitch(index)
            return self[index]
        elif isinstance(index, slice):
            start = index.start if index.start is not None else min(self.specified_pitches)
            stop = index.stop if index.stop is not None else max(self.specified_pitches) + 1
            pitches = range(start, stop, index.step) if index.step is not None else range(start, stop)
            return [self[i] for i in pitches]
        elif isinstance(index, tuple) or isinstance(index, list):
            return [self[i] for i in index]
        
    def __setitem__(self, index, value):
        """Set elements of the pitch-frequency-dictionary through slicing.
        
        Parameters
        ----------
        index : int or str or slice or tuple of int and str
            Slicing argument.
        value : int or float or list thereof
            The frequency the pitch will be tuned to
        """
        if isinstance(index, int) or isinstance(index, float) or isinstance(index, str):
            self.tune_pitch(index, value)
        elif isinstance(index, slice):
            start, stop, step = index.indices(max(self.specified_pitches) + 1)
            count = 0
            for i in range(start, stop, step):
                self.tune_pitch(i, value[count])
                count += 1
        elif isinstance(index, tuple) or isinstance(index, list):
            count = 0
            for i in index:
                self.tune_pitch(i, value[count])
                count += 1
    
    def tune_pitch(self, pitch, frequency):
        """Tune a single pitch to a specific frequency.
        This is mainly for internal use.
        Use the slicing method (scale[pitch] = frequency), that is much more flexible.
        
        Parameters
        ----------
        pitch : int or str
            Pitch to tune.
        frequency : float
            Frequency to tune to.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        # float pitches are allowed but are not guarantied to work with
        # the conveniend tuning methods like tune pitchclass
        self.dictionary[pitch] = frequency
        if self.on_change is not None:
            self.on_change(pitch, frequency)
        
    def tune_pitchclass(self, pitch, frequency):
        """Tune a every pitch of a pitchclass to a specific frequency.
        E.g. tune_pitchclass('D4', 500) tunes D4=500, D5=500*octave_interval, D3=500/octave_interval, etc.
     
        Tunes only pitches in specified_pitches.
        
        Parameters
        ----------
        pitch : int or str
            Pitch of the pitchclass to be tune.
        frequency : float
            Frequency to tune the given pitch to.
        """
        # tunes only specified frequencies
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        i = 0
        while True:
            p = i * self.pitches_per_octave + pitch
            if p in self.specified_pitches:
                self.tune_pitch(p, frequency * self.octave_interval**i)
            elif p > max(self.specified_pitches):
                break
            i += 1
        i = -1
        while True:
            p = i * self.pitches_per_octave + pitch
            if p in self.specified_pitches:
                self.tune_pitch(p, frequency * self.octave_interval**i)
            elif p < min(self.specified_pitches):
                break
            i -= 1
            
    def tune_all(self, frequencies, pitches=None):
        """Tune all pitches.
        If pitches is given, every pitch in pitches is tuned to the corresponding frequency in frequencies.
        If pitches is None, len(frequencies) has to be equal to pitches_per_octave
        then, tune_pitchclass is called for every pitch in range(pitches_per_octave) and every frequency in frequencies.
        
        Parameters
        ----------
        frequencies : list of float
            Frequencies to be tuned to.
        pitches : list of int or str
            Pitches to be tuned.
        """
        if pitches is None:
            for i in range(self.pitches_per_octave):
                self.tune_pitchclass(self.reference_pitch + i, frequencies[i])
        else:
            for i in range(len(pitches)):
                self.tune_pitch(pitches[i], frequencies[i])
            
    def tune_pitch_by_interval(self, pitch, interval):
        """Tune pitch to form a specific interval with the reference frequency.
        
        Parameters
        ----------
        pitch : int or str
            Pitch to be tuned.
        interval : list of int or str
            Target interval.
        """
        self.tune_pitch(pitch, interval * self.reference_frequency)
    
    def tune_pitchclass_by_interval(self, pitch, interval):
        """Tune pitch by interval and the other pitches of the pitchclass accordingly.
        
        Parameters
        ----------
        pitch : int or str
            Pitch to be tuned.
        interval : list of int or str
            Target interval.
        """
        self.tune_pitchclass(pitch, interval * self.reference_frequency)
        
    def tune_all_by_interval(self, intervals, pitches=None):
        """Same as tune_all with intervals (relative to the reference frequency) instead of frequencies."""
        self.tune_all([interval * self.reference_frequency for interval in intervals], pitches)
        
    def tune_pitch_by_interval_in_cents(self, pitch, cents):
        """Same as tune_pitch_by_interval but interval given in cents."""
        self.tune_pitch(pitch, 2**(cents/1200) * self.reference_frequency)
        
    def tune_pitchclass_by_interval_in_cents(self, pitch, cents):
        """Same as tune_pitchclass_by_interval but interval given in cents."""
        self.tune_pitchclass(pitch, 2**(cents/1200) * self.reference_frequency)
    
    def tune_all_by_interval_in_cents(self, cents, pitches=None):
        """Same as tune_pitch_by_interval but interval given in cents.
        
        Can be conveniently used together with the presets in tunings_in_cents.
        e.g. tune_all_by_interval_in_cents(Scale.tunings_in_cents['Werkmeister 4'])
        """
        self.tune_all([2**(c/1200) * self.reference_frequency for c in cents], pitches)
    
    def tune_all_equal_temperament(self):
        """Tunes all specified pitches according to an equal tempered scale.
        Using the stored pitches per octave and octave interval."""
        self.tune_all_by_interval([
            self.octave_interval**(p / self.pitches_per_octave)
            for p in range(self.pitches_per_octave)
        ])
    
    def generalize_to_midi_range(self, pitch):
        """Generalizes a pitch (or a list of pitches) to all other pitches of the same pitchclass in midi range (0-127).
        Other than tune_pitchclass, this creates new specified pitches.
        Octaves of pitch will be put to the midi octaves: pitch + i * 12 regardless of self.pitches_per_octave
        
        The is meant for creating a scale that is meant to be played with the standard keyboard layout. For example:
        diatonic_pitches = ['C4','D4', 'E4', 'F4', 'G4', 'A4', 'B4']
        diatonic_intervals = [1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8]
        s = Scale(reference_pitch=diatonic_pitches[0], 260,
                  pitches_per_octave=len(diatonic_pitches), octave_interval=2,
                  specified_pitches=diatonic_pitches, init_ET=False)
        s.tune_all_by_interval(diatonic_intervals, diatonic_pitches)
        s.generalize_to_midi_range(diatonic_pitches)
        (setting pitches_per_octave=len(diatonic_pitches) has no effect here other than beeing 'semantically correct')
        
        Parameters
        ----------
        pitch : int or str or list of int or str
            Pitch(es) to generalize.
        """
        if isinstance(pitch, list) or isinstance(pitch, tuple) or isinstance(pitch, range):
            for p in pitch:
                self.generalize_to_midi_range(p)
        else:
            if isinstance(pitch, str):
                pitch = Scale.pitchname_to_pitch(pitch)
            for i in range(- (pitch // 12), (127 - pitch) // 12 + 1):
                p = pitch + i * 12
                self.tune_pitch(p, self[pitch] * self.octave_interval**i)
    
    
    ## static methods
    
    def pitchname_to_pitch(name):
        """Translates pitchnames ('A#4') to midi numbers (70).
        Scientific pitch notation.
        Allways the names of the keys you have to press on a standard midi-keyboard,
        i.e. it assumes 12 tones per octave, regardless of what this.pitches_per_octave is.
        
        Parameters
        ----------
        name : str
            Pitchname to translate.
            
        Returns
        -------
        int
            Midi pitch of the given name.
        """
        if name[1] == '#' or name[1] == 'b':
            return Scale.pitchclasses[name[0:2]] + 12 * (int(name[2:]) + 1)
        else:
            return Scale.pitchclasses[name[0]] + 12 * (int(name[1:]) + 1)
    
    def pitch_to_pitchname(pitch):
        """Translates midi numbers (70) to pitchnames ('A#4').
        Scientific pitch notation.
        Allways the names of the keys you have to press on a standard midi-keyboard,
        i.e. it assumes 12 tones per octave, regardless of what this.pitches_per_octave is.
        Allways the sharp version (not Bb4).
        
        Parameters
        ----------
        pitch : int
            Midi pitch to translate.
            
        Returns
        -------
        str
            Name of the given midi pitch.
        """
        # filter to get consistent accidentals (always #)
        for name, pitchclass in filter(lambda pair: pair[0].find('b') == -1, Scale.pitchclasses.items()):
            if pitch % 12 == pitchclass:
                pitchclassname = name
        return pitchclassname + str(pitch // 12 - 1)
    
    def cents_to_freq_ratio(cents):
        """Calculates frequency ratio from cents.
        
        Parameters
        ----------
        cents : float
            Cents to translate.
            
        Returns
        -------
        float
            Corresponding frequency ratio.
        """
        return 2**(cents / 1200)
    
    def freq_ratio_to_cents(interval):
        """Calculates cents from frequency ratio.
        
        Parameters
        ----------
        interval : float
            Frequency ratio to translate.
            
        Returns
        -------
        float
            Corresponding cent value.
        """
        return np.log2(interval) * 1200