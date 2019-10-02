import numpy as np
import time

# see http://www.huygens-fokker.org/scala/scl_format.html for specification
def read_scala(filename):
    """Reads a .scl file and returns the list of intervales in frequency ratios specified there
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
    if not intervals_in_cents:
        intervals = [Scale.freq_ratio_to_cents(i) for i in intervals]
    
    if description is None:
        description = 'Scala file saved with adaptivetuning ' + time.asctime()
    
    lines = ['! ' + filename, ' ' + description, ' ' + str(len(intervals)), '!']
    lines += [' ' + str(float(i)) for i in intervals]

    with open(filename, 'w') as f:
        f.write('\n'.join(lines))


# todo write doku
class Scale:
    """Scale class. Manages a dictionary that assigns every pitches a frequency.
    """
    
    pitchclasses = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
        'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    }
    
    # some historical tuning rounded to nearest cent
    # all intended to be 12-tone scales with octave = 2
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
                 init_12TET=True, on_change=None):
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
        if init_12TET:
            self.tune_all_equal_temperament()
    
    @property
    def specified_pitches(self):
        """dict_keys : Pitches for wich frequencies are specified. Nonempty, positive values.
        Can be set with list or range.
        New specified pitches are set to 0.
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
        """int : Reference pitch. In pitch_range."""
        return self._reference_pitch
    
    @reference_pitch.setter
    def reference_pitch(self, reference_pitch):
        if isinstance(reference_pitch, str):
            reference_pitch = Scale.pitchname_to_pitch(reference_pitch)
        self._reference_pitch = reference_pitch
        
    @property
    def reference_frequency(self):
        """float : Frequency of Reference pitch, > 0.
        Important: the reference is not part of the Scale,
        i.e. sclae[reference_pitch] (or any other method to acces a tuning) does not necesseraly
        return reference_frequency and sclae[reference_pitch] = f (or any other tuning method)
        never changes the reference_frequency.
        The reference is only used as a parameter in the tune_by_interval and tune_in_cents methods
        """
        return self._reference_frequency
    
    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = reference_frequency
    
    @property
    def pitches_per_octave(self):
        """int : Number of pitches per octave > 0."""
        return self._pitches_per_octave
    
    @pitches_per_octave.setter
    def pitches_per_octave(self, pitches_per_octave):
        self._pitches_per_octave = pitches_per_octave
    
    @property
    def octave_interval(self):
        """float : Interval size of the octave."""
        return self._octave_interval
    
    @octave_interval.setter
    def octave_interval(self, octave_interval):
        self._octave_interval = octave_interval
    
    @property
    def on_change(self):
        """Function : Gets called every time a tuning changes.
        Arguments: pitch, frequency
        If you don't want all the messages from the initial setting of the scale, set the onchange after
        the initialisation.
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
            index : int or str or slice or tuple of ints and strings
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
            index : int or str or slice or tuple of ints and strings
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
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        # float pitches are allowed but are not guarantied to work with
        # the conveniend tuning methods like tune pitchclass
        self.dictionary[pitch] = frequency
        if self.on_change is not None:
            self.on_change(pitch, frequency)
        
    def tune_pitchclass(self, pitch, frequency):
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
        # if pitches is None, len(frequencies) has to be equal to picthes per octave
        # if pitches is None, only specified frequencies will be tuned
        if pitches is None:
            for i in range(self.pitches_per_octave):
                self.tune_pitchclass(self.reference_pitch + i, frequencies[i])
        else:
            for i in range(len(pitches)):
                self.tune_pitch(pitches[i], frequencies[i])
            
    def tune_pitch_by_interval(self, pitch, interval):
        self.tune_pitch(pitch, interval * self.reference_frequency)
    
    def tune_pitchclass_by_interval(self, pitch, interval):
        self.tune_pitchclass(pitch, interval * self.reference_frequency)
        
    def tune_all_by_interval(self, intervals, pitches=None):
        # if pitches is None, len(intervals) has to be equal to picthes per octave
        self.tune_all([interval * self.reference_frequency for interval in intervals], pitches)
        
    def tune_pitch_by_interval_in_cents(self, pitch, cents):
        # interval is given in cents
        self.tune_pitch(pitch, 2**(cents/1200) * self.reference_frequency)
        
    def tune_pitchclass_by_interval_in_cents(self, pitch, cents):
        # interval is given in cents
        self.tune_pitchclass(pitch, 2**(cents/1200) * self.reference_frequency)
    
    def tune_all_by_interval_in_cents(self, cents, pitches=None):
        # if pitches is None, len(cents) has to be equal to picthes per octave
        # because when pitches is None, all octaves in specified_pitches get tuned
        self.tune_all([2**(c/1200) * self.reference_frequency for c in cents], pitches)
    
    def tune_all_equal_temperament(self):
        self.tune_all_by_interval([
            self.octave_interval**(p / self.pitches_per_octave)
            for p in range(self.pitches_per_octave)
        ])
    
    def generalize_to_midi_range(self, pitch):
        # generalizes a pitch to all other pitches of the same pitchclass in midi range (0-127)
        # other tune_pitchclass, this creates new specified pitches
        # octaves of pitch will be put to the midi octaves: pitch + i * 12
        # regardless of self.pitches_per_octave
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
        # allways the names of the keys you have to press on a standard midi-keyboard,
        # i.e. it assumes 12 tones per octave, regardless of what this.pitches_per_octave is
        if name[1] == '#' or name[1] == 'b':
            return Scale.pitchclasses[name[0:2]] + 12 * (int(name[2:]) + 1)
        else:
            return Scale.pitchclasses[name[0]] + 12 * (int(name[1:]) + 1)
    
    def pitch_to_pitchname(pitch):
        # allways the names of the keys you have to press on a standard midi-keyboard,
        # i.e. it assumes 12 tones per octave, regardless of what this.pitches_per_octave is
        
        # filter to get consistent accidentals (always #)
        for name, pitchclass in filter(lambda pair: pair[0].find('b') == -1, Scale.pitchclasses.items()):
            if pitch % 12 == pitchclass:
                pitchclassname = name
        return pitchclassname + str(pitch // 12 - 1)
    
    def cents_to_freq_ratio(cents):
        return 2**(cents / 1200)
    
    def freq_ratio_to_cents(interval):
        return np.log2(interval) * 1200