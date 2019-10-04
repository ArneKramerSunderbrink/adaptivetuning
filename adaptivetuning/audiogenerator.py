import time
import numpy as np
import sc3nb
from .scale import Scale

class KeyData:
    """KeyData class. Collects all the data about a specific tone needed for e.g. a Tuner.
    In particular, it provides functionality to compute the current amplitude based on a adsr envelope.
    
    In one of three states:
    Before press (only when initialized with pressed=False):
        self._pressed = False
        self._timestamp = None
    pressed:
        self._pressed = True
        self._timestamp = time of press
    released:
        self._pressed = False
        self._timestamp = time of release
        
    Attributes
    ----------
    amplitude : float
        Absolute amplitude of the tone. See current_amplitude. (Default value = 1)
    attack_time : float
        Attack time of the adsr envelope of the tone. (Default value = 0)
    decay_time : float
        Decay time of the adsr envelope of the tone. (Default value = 0)
    sustain_level : float
        Sustain level of the adsr envelope of the tone. (Default value = 1)
    release_time : float
        Release time of the adsr envelope of the tone. (Default value = 0)
    frequency : float
        Frequency of the tone. (Default value = 440)
    partials_pos : list of floats
        Relative positions of the partials of the tone.
        Note that the fundamental (relative position 1) is also a partial!
        (Default value = [1], only the fundamental.)
    partials_amp : list of floats
        Relative amplitude of the partials.
        Should have the same length as partials_pos but this class does not check.
        (Defaut value = [1])
    get_now : function
        A function that returns the current time in seconds when called.
        When None is given it is set to time.time. (Default value = None)
    pressed : bool
        Whether the key is currently pressed. Read only after init. (Default value = True)
    currently_running : bool
        Whether the key is currently running,
        i.e. The key is pressed or it has been released but the release time is stil running.
    current_env : float
        Current envelop hight in (0,1).
    current_amplitude : float
        Current amplitude of the tone. Equal to amplitude * current_env.
    """
    
    def __init__(self, amplitude=1, attack_time=0, decay_time=0, sustain_level=1, release_time=0,
                 frequency=440, partials_pos=[1], partials_amp=[1], get_now=None, pressed=True):
        """__init__ method
        
        Parameters
        ----------
        amplitude : float
            Absolute amplitude of the tone. See current_amplitude. (Default value = 1)
        attack_time : float
            Attack time of the adsr envelope of the tone. (Default value = 0)
        decay_time : float
            Decay time of the adsr envelope of the tone. (Default value = 0)
        sustain_level : float
            Sustain level of the adsr envelope of the tone. (Default value = 1)
        release_time : float
            Release time of the adsr envelope of the tone. (Default value = 0)
        frequency : float
            Frequency of the tone. (Default value = 440)
        partials_pos : list of floats
            Relative positions of the partials of the tone.
            Note that the fundamental (relative position 1) is also a partial!
            (Default value = [1], only the fundamental.)
        partials_amp : list of floats
            Relative amplitude of the partials.
            Should have the same length as partials_pos but this class does not check.
            (Defaut value = [1])
        get_now : function
            A function that returns the current time in seconds when called.
            When None is given it is set to time.time. (Default value = None)
        pressed : bool
            Whether the key is currently pressed. Read only after init. (Default value = True)
        """
        self.amplitude = amplitude
        self.attack_time = attack_time
        self.decay_time = decay_time
        self.sustain_level = sustain_level
        self.release_time = release_time
        self.frequency = frequency
        self.partials_pos = partials_pos
        self.partials_amp = partials_amp
        
        self.get_now = get_now
        if self.get_now is None: self.get_now = time.time
        
        if pressed:
            self.press()
        else:
            self._pressed = False
            self._timestamp = None
    
    @property
    def pressed(self):
        """bool : True if the key is currently pressed, false if released or not pressed yet. Read only after init."""
        return self._pressed
    
    @property
    def currently_running(self):
        """bool : True if the key is pressed or it has been released but the release time is stil running."""
        return self._pressed \
               or (self._timestamp is not None and self.get_now() - self._timestamp < self.release_time)
    
    @property
    def current_env(self):
        """float: current envelop hight in (0,1)."""
        if self._timestamp is None:
            return 0
        t = self.get_now() - self._timestamp
        if self._pressed:
            if t < self.attack_time:
                m = 1 / self.attack_time
                n = 0
            elif t < self.attack_time + self.decay_time:
                m = (self.sustain_level - 1) / self.decay_time
                n = 1 - self.attack_time * m
            else:
                m = 0
                n = self.sustain_level
        else:
            if t < self.release_time:
                m = - self._env_when_released / self.release_time
                n = self._env_when_released
            else:
                m = 0
                n = 0
        return m * t + n
    
    @property
    def current_amplitude(self):
        """float : Current amplitude. Equal to amplitude * current_env."""
        return self.amplitude * self.current_env
    
    def press(self):
        """Press the key. If it is already pressed this restarts the envelope."""
        self._pressed = True
        self._timestamp = self.get_now()
    
    def release(self):
        """Starts the release phase of the tone if it is currently pressed. Else nothing happens."""
        if self._pressed:
            self._env_when_released = self.current_env
            self._timestamp = self.get_now()
            self._pressed = False
            
    def fast_release(self):
        """Sets the release time to 0 and releases the key."""
        self.release_time = 0
        self.release()
        
        
class CustomSynth(sc3nb.synth.Synth):
        """Custom synth class. Inherits sc3nb.synth.Synth.
        Has to be freed manually or via doneAction, it is not automatically freed on deletion!
        Only works with a SynthDef that provides a sustained envelope with a matching release
        and a gate called 'gate' without Done.freeSelf and a second envelope with a fast release
        and with Done.freeSelf.
        """ 
        def release(self):
            """Call this method to start the normal release of the Synth."""
            self.set("gate", 0)

        def fast_release_and_free(self):
            """Call this method to start the fast release of the Synth and free it.
            It is essentialy free without the risc of clicking.
            """
            self.set("fast_gate", 0)

        def set_frequency(self, frequency):
            """Change the frequency of th running synth."""
            self.set("freq", frequency)

        def set_amplitude(self, amplitude):
            """Change the amplitude of th running synth."""
            self.set("amp", amplitude)
        
        def __del__(self):
            """This synth is not automatically freed on deletion.
            This allows the to call fast_release_and_free and delet the reference of the Synth immediately without
            error messages or warnings from SuperCollider because we try to free the synth two times.
            """
            pass  # pass instead of self.free()
        
        
class Audiogenerator:
    """Audiogenerator class. Manages a microtonal polyphonic additive synthesizer.
    
    Attributes
    ----------
    sc : sc3nb.SC or None
        sc3nb.SC object to communicate with SuperCollider.
        If None is given the synthesizer runs silently.
        Setting sc automatically sends the SynthDef to SuperCollider (Default value = None)
    global_amplitude : float
        Master volume of the synthesizer. (Default value = 0.01)
    scale : adaptivetuning.Scale
        A Scale that manages the tuning of the synthesizer.
        If None is given, the default scale is used which is 12TET.
        Setting a new scale of changing the current scale changes the tuning of currently running synths.
        (Default value = None)
    partials_amp : Relative amplitude of the partials.
        Note that the fundamental (relative position 1) is also a partial!
        Audiogenerator makes sure it has allways the same length as partials_pos by cutting surplus values
        or adding values if needed.
        If None is given the amplitudes of the overtones decay exponentially with factor 0.88.
        (Defaut value = None)
        
        artials_amp can be given as a dictionary of instructions (not on construction though!).
        {'method': 'harmonic', 'nr_partials': int (default len(partials_amp)), 'factor': float (default 1)}
        for [1 / (i * factor) for i in range(1, nr_partial + 1)]
        {'method': 'exponential', 'nr_partials': int (default len(partials_amp)), 'base': float (default 0.8)}
        for [base**i for i in range(0, nr_partial)]
    partials_pos : list of floats
        Relative positions of the partials of the tone.
        Note that the fundamental (relative position 1) is also a partial!
        Audiogenerator makes sure it has allways the same length as partials_pos by cutting surplus values
        or adding values if needed.
        If None is given 12 harmonic partials are used.
        (Default value = None)
    attack_time : float
        Attack time (in seconds) of the adsr-envelope of the synth. (Default value = 0)
    decay_time : float
        Decay time (in seconds) of the adsr-envelope of the synth. (Default value = 0)
    sustain_level : float
        Sustain level (in amplitude) of the adsr-envelope of the synth. (Default value = 1)
    release_time : float
        Release time (in seconds) of the adsr-envelope of the synth. (Default value = 0)
    glide_time : float
        Time the synthesizer take to interpolate from one value to another if frequency or amplitude is changed.
        Setting it to 0 risks artifacts (klicks), big values result in a audible sliding sound. (Default value = 0.1)
    audio_bus : int
        First buss on which the synth is played.
        Generally, 0 is the left speaker and 1 is the right speaker.
        If stereo is true the synth will play on audio_bus and audio_bus + 1. (Default value = 0)
    stereo : bool
        If true the synthesizer plays (the same signal) on the busses audio_bus and audio_bus + 1. (Default value = True)
    silent : bool
        If silent is true there will be no actual communication with SuperCollider.
        I.e. no Synthdefinition will be created, no Synths will be created in SuperCollider.
        Everything else works as usual - good for testing.
        If sc = None, silent is true. (Default value = False)
    get_now : function
        A function that returns the current time in seconds when called.
        When None is given it is set to time.time. (Default value = None)
    keys : dict of adaptivetuning.KeyData
        List of all keys (0 to 128). Stores informations about when they were pressed, released,
        what's their frequency, partial positions, what's their current amplitude, etc.
        Don't change manually, use note_on, note_change_freq, scale['A4'] = 123 etc.
    synths : dict of adaptivetuning.CustomSynth
        Custom version of sc3nb.synth.Synth that represents a SuperCollider synths.
        Don't change manually, use note_on, note_change_freq, scale['A4'] = 123 etc.
    """
    
    presets = {
        'piano': {'partials_amp': [3.7, 5.4, 1.2, 1.1, 0.95, 0.6, 0.5, 0.65, 0, 0.1, 0.2],
                  'partials_pos': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                  'attack_time': 0.0001, 'decay_time': 4, 'sustain_level': 0, 'release_time': 0.5},
        'pad':   {'partials_amp': [(3 / 5)**i for i in range(11)],
                  'partials_pos': [i for i in range(1, 12)],
                  'attack_time': 0.7, 'decay_time': 1, 'sustain_level': 0.9, 'release_time': 2.5,
                  'glide_time': 1.5}
    }
    
    
    def __init__(self, sc=None, global_amplitude=0.01, scale=None,
                 partials_amp=None, partials_pos=None,
                 attack_time=0.1, decay_time=0.1, sustain_level=0.8, release_time=0.2,
                 glide_time=0.1, audio_bus=0, stereo=True, silent=False, get_now=None):
        """___init___ method
        
        Parameters
        ----------
        sc: sc3nb.SC or None
            sc3nb.SC object to communicate with SuperCollider.
            If None is given the synthesizer runs silently.
            Setting sc automatically sends the SynthDef to SuperCollider (Default value = None)
        global_amplitude: float
            Master volume of the synthesizer. (Default value = 0.01)
        scale: adaptivetuning.Scale
            A Scale that manages the tuning of the synthesizer.
            If None is given, the default scale is used which is 12TET.
            Setting a new scale of changing the current scale changes the tuning of currently running synths.
            (Default value = None)
        partials_amp : Relative amplitude of the partials.
            Note that the fundamental (relative position 1) is also a partial!
            Audiogenerator makes sure it has allways the same length as partials_pos by cutting surplus values
            or adding values if needed.
            If None is given the amplitudes of the overtones decay exponentially with factor 0.88.
            (Defaut value = None)

            artials_amp can be given as a dictionary of instructions (not on construction though!).
            {'method': 'harmonic', 'nr_partials': int (default len(partials_amp)), 'factor': float (default 1)}
            for [1 / (i * factor) for i in range(1, nr_partial + 1)]
            {'method': 'exponential', 'nr_partials': int (default len(partials_amp)), 'base': float (default 0.8)}
            for [base**i for i in range(0, nr_partial)]
        partials_pos : list of floats
            Relative positions of the partials of the tone.
            Note that the fundamental (relative position 1) is also a partial!
            Audiogenerator makes sure it has allways the same length as partials_pos by cutting surplus values
            or adding values if needed.
            If None is given 12 harmonic partials are used.
            (Default value = None)
        attack_time : float
            Attack time (in seconds) of the adsr-envelope of the synth. (Default value = 0)
        decay_time : float
            Decay time (in seconds) of the adsr-envelope of the synth. (Default value = 0)
        sustain_level : float
            Sustain level (in amplitude) of the adsr-envelope of the synth. (Default value = 1)
        release_time : float
            Release time (in seconds) of the adsr-envelope of the synth. (Default value = 0)
        glide_time : float
            Time the synthesizer take to interpolate from one value to another if frequency or amplitude is changed.
            Setting it to 0 risks artifacts (klicks), big values result in a audible sliding sound. (Default value = 0.1)
        audio_bus : int
            First buss on which the synth is played.
            Generally, 0 is the left speaker and 1 is the right speaker.
            If stereo is true the synth will play on audio_bus and audio_bus + 1. (Default value = 0)
        stereo : bool
            If true the synthesizer plays (the same signal) on the busses audio_bus and audio_bus + 1. (Default value = True)
        silent : bool
            If silent is true there will be no actual communication with SuperCollider.
            I.e. no Synthdefinition will be created, no Synths will be created in SuperCollider.
            Everything else works as usual - good for testing.
            If sc = None, silent is true. (Default value = False)
        get_now : function
            A function that returns the current time in seconds when called.
            When None is given it is set to time.time. (Default value = None)
        """
        
        # We need to manage them seperately so that we can have lag between setting of the key infos and actually
        # playing of the synth such that the key infos are representing what will sound in the future
        self.keys = {i: KeyData(pressed=False) for i in range(128)}
        self.synths = {i: None for i in range(128)}
        
        
        # Generally the setter pressupose that the whole setup is done, that's why the protected attributes
        # are set directly here
        self._global_amp = global_amplitude
        if scale == None:
            scale = Scale(specified_pitches=range(128))
        # previous on_change method will be overwritten!
        scale.on_change = lambda pitch, freq: self.note_change_freq(pitch, freq)
        self._scale = scale
        
        if partials_amp is None and partials_pos is None:
            self._partials_amp = [0.88**i for i in range(12)]
            self._partials_pos = [i + 1 for i in range(12)]
        elif partials_amp is None:
            self._partials_pos = partials_pos
            self._partials_amp = [0.88**i for i in range(len(partials_pos))]
        elif partials_pos is None:
            self._partials_amp = partials_amp
            self._partials_pos = [i + 1 for i in range(len(partials_pos))]
        else:
            self._partials_amp = partials_amp
            self._partials_pos = partials_pos
        self._attack_time = attack_time
        self._decay_time = decay_time
        self._sustain_level = sustain_level
        self._release_time = release_time
        self._glide_time = glide_time
        self._audio_bus = audio_bus
        self._stereo = stereo
        self._silent = silent
        if get_now is None: get_now = time.time
        self._get_now = get_now
        
        # this not only stores sc but also sets up the synthdefinition
        self.sc = sc
    
    @property
    def global_amplitude(self):
        """float : Master volume of the synthesizer. (Default value = 0.01)"""
        return self._global_amp
    
    @global_amplitude.setter
    def global_amplitude(self, global_amp):
        # if there are running synthesizers, change their volumes accordingly
        # by multiplying with global_amp / self._global_amp
        for p in self.keys:
            if self.keys[p] is not None:
                self.keys[p].amplitude = global_amp / self._global_amp
            if self.synths[p] is not None:
                self.synths[p].set("amp", global_amp / self._global_amp)
        self._global_amp = global_amp
        
    @property
    def scale(self):
        """adaptivetuning.Scale : A Scale that manages the tuning of the synthesizer.
        If None is given, the default scale is used which is 12TET. (Default value = None)
        Setting a new scale of changing the current scale changes the tuning of currently running synths.
        """
        return self._scale
    
    @scale.setter
    def scale(self, scale):
        if scale == None:
            scale = Scale(specified_pitches=range(128))
        
        # if there are running synthesizers, change their frequencies accordingly
        for p in self.keys:
            self.note_change_freq(p, scale[p])
                
        # previous on_change method will be overwritten!
        scale.on_change = lambda pitch, freq: self.note_change_freq(pitch, freq)
        
        self._scale = scale
        
    @property
    def partials_amp(self):
        """sequence of floats : Relative amplitude of the partials.
        Note that the fundamental (relative position 1) is also a partial!
        Audiogenerator makes sure it has allways the same length as partials_pos by cutting surplus values
        or adding values if needed.
        If None is given the amplitudes of the overtones decay exponentially with factor 0.88.
        (Defaut value = None)
        
        artials_amp can be given as a dictionary of instructions (not on construction though!).
        {'method': 'harmonic', 'nr_partials': int (default len(partials_amp)), 'factor': float (default 1)}
        for [1 / (i * factor) for i in range(1, nr_partial + 1)]
        {'method': 'exponential', 'nr_partials': int (default len(partials_amp)), 'base': float (default 0.8)}
        for [base**i for i in range(0, nr_partial)]
        """
        return self._partials_amp
    
    @partials_amp.setter
    def partials_amp(self, partials_amp):
        if partials_amp is None:
            partials_amp = [0.88**i for i in range(len(partials_pos))]
        
        if isinstance(partials_amp, dict) and 'method' in partials_amp:
            if partials_amp['method'] == 'harmonic':
                if 'nr_partials' not in partials_amp: partials_amp['nr_partials'] = len(self.partials_amp)
                if 'factor' not in partials_amp: partials_amp['factor'] = 1
                partials_amp = [1 / (i * partials_amp['factor']) for i in range(1, partials_amp['nr_partials'] + 1)]
            elif partials_amp['method'] == 'exponential':
                if 'nr_partials' not in partials_amp: partials_amp['nr_partials'] = len(self.partials_amp)
                if 'base' not in partials_amp: partials_amp['base'] = 0.8
                partials_amp = [partials_amp['base']**i for i in range(0, partials_amp['nr_partials'])]
        
        if len(self.partials_pos) > len(partials_amp):
            # cut superfluous values
            self._partials_pos = self._partials_pos[:len(partials_amp)]
        elif len(self.partials_pos) < len(partials_amp):
            # pad with harmonic overtones
            self._partials_pos = self._partials_pos + [i for i in range(len(self.partials_pos), len(partials_amp))]
        
        self.set_synth_def(partials_amp=partials_amp)
    
    @property
    def partials_pos(self):
        """sequence of floats : Relative positions of the partials of the tone.
        Note that the fundamental (relative position 1) is also a partial!
        Audiogenerator makes sure it has allways the same length as partials_pos by cutting surplus values
        or adding values if needed.
        If None is given 12 harmonic partials are used.
        (Default value = None)
        
        partials_pos can be given as a dictopnary of instructions (not on construction though!).
        {'method': 'harmonic', 'nr_partials': int (default len(partials_amp)), 'octave': float (default 2)}
        for [octave**log2(i) for i in range(1, nr_partial + 1)]
        """
        return self._partials_pos
    
    @partials_pos.setter
    def partials_pos(self, partials_pos):
        if partials_pos is None:
            partials_pos = [i + 1 for i in range(len(partials_pos))]
        if isinstance(partials_pos, dict) and 'method' in partials_pos:
            if partials_pos['method'] == 'harmonic':
                if 'nr_partials' not in partials_pos: partials_pos['nr_partials'] = len(self.partials_pos)
                if 'octave' not in partials_pos: partials_pos['octave'] = 2
                partials_pos = [partials_pos['octave']**np.log2(i)
                                for i in range(1, partials_pos['nr_partials'] + 1)]
        
        if len(self.partials_amp) > len(partials_pos):
            # cut superfluous values
            self._partials_amp = self._partials_amp[:len(partials_pos)]
        elif len(self.partials_amp) < len(partials_pos):
            # pad with zeros
            self._partials_amp = self._partials_amp + [0 for _ in range(len(self.partials_amp), len(partials_pos))]
        
        self.set_synth_def(partials_pos=partials_pos)
    
    @property
    def attack_time(self):
        """float : Attack time (in seconds) of the adsr-envelope of the synth. (Default value = 0)"""
        return self._attack_time
    
    @attack_time.setter
    def attack_time(self, attack_time):
        self.set_synth_def(attack_time=attack_time)
    
    @property
    def decay_time(self):
        """float : Decay time (in seconds) of the adsr-envelope of the synth. (Default value = 0)"""
        return self._decay_time
    
    @decay_time.setter
    def decay_time(self, decay_time):
        self.set_synth_def(decay_time=decay_time)
        
    @property
    def sustain_level(self):
        """float : Sustain level (in amplitude) of the adsr-envelope of the synth. (Default value = 1)"""
        return self._sustain_level
    
    @sustain_level.setter
    def sustain_level(self, sustain_level):
        self.set_synth_def(sustain_level=sustain_level)
        
    @property
    def release_time(self):
        """float : Release time (in seconds) of the adsr-envelope of the synth. (Default value = 0)"""
        return self._release_time
    
    @release_time.setter
    def release_time(self, release_time):
        self.set_synth_def(release_time=release_time)
        
    @property
    def glide_time(self):
        """float : Time the synthesizer take to interpolate from one value to another if frequency or amplitude is changed.
        Setting it to 0 risks artifacts (klicks), big values result in a audible sliding sound. (Default value = 0.1)
        """
        return self._glide_time
    
    @glide_time.setter
    def glide_time(self, glide_time):
        self.set_synth_def(glide_time=glide_time)
        
    @property
    def audio_bus(self):
        """int : First buss on which the synth is played.
        Generally, 0 is the left speaker and 1 is the right speaker.
        If stereo is true the synth will play on audio_bus and audio_bus + 1. (Default value = 0)
        """
        return self._audio_bus
    
    @audio_bus.setter
    def audio_bus(self, audio_bus):
        self.set_synth_def(audio_bus=audio_bus)
        
    @property
    def stereo(self):
        """Bool : If true the synthesizer plays (the same signal) on the busses audio_bus and audio_bus + 1.
        (Default value = True)"""
        return self._stereo
    
    @stereo.setter
    def stereo(self, stereo):
        self.set_synth_def(stereo=stereo)
    
    @property
    def silent(self):
        """Bool : If silent is true there will be no actual communication with SuperCollider.
        I.e. no Synthdefinition will be created, no Synths will be created in SuperCollider.
        Everything else works as usual - good for testing.
        If sc = None, silent is true. (Default value = False)"""
        return self._silent
    
    @silent.setter
    def silent(self, silent):
        if silent:
            self.stop_all()
        else:
            if self._sc is None:
                silent = True
        self._silent = silent
    
    @property
    def get_now(self):
        """function : A function that returns the current time in seconds when called.
        When None is given it is set to time.time. (Default value = None)"""
        return self._get_now
    
    @get_now.setter
    def get_now(self, get_now):
        if get_now is None:
            get_now = time.time
        self._get_now = get_now   
    
    @property
    def sc(self):
        """sc3nb.SC or None : sc3nb.SC object to communicate with SuperCollider.
        If None is given the synthesizer runs silently.
        Setting sc automatically sends the SynthDef to SuperCollider (Default value = None)
        """
        return self._sc
    
    @sc.setter
    def sc(self, sc):
        self._sc = sc
        self.silent = sc is None
        
        if self.silent: return
        
        self._microsynth_def = self._sc.SynthDef(name="microsynth_def", definition="""
        { |amp=0.5, freq=440, gate=1, fast_gate=1|
                var freq_lagged = Lag.kr(freq, {{glide_time}});
                var amp_lagged = Lag.kr(amp, {{glide_time}});
                var partials_amp = {{partials_amp}};
                var partials_pos = {{partials_pos}};
                var freqs = Array.fill(partials_amp.size, { |i| freq_lagged * partials_pos.at(i) });
                var waves = Array.fill(partials_amp.size, { |i| SinOsc.ar(freqs.at(i),mul: partials_amp.at(i))});
                var mixedwaves = amp_lagged * Mix.ar(waves);
                var env = EnvGen.ar(Env.adsr({{attack_time}}, {{decay_time}}, {{sustain_level}}, {{release_time}}),
                                    gate);
                var fast_env = EnvGen.ar(Env.asr(0.0, sustainLevel: 1.0, releaseTime: 0.01),
                                 fast_gate, doneAction: Done.freeSelf);
                var signal = mixedwaves * env * fast_env;
                Out.ar({{audio_bus}}, signal!{{stereo}});
        }""")
        self.set_synth_def()
            
    def set_synth_def(self, partials_amp=None, partials_pos=None,
                  attack_time=None, decay_time=None, sustain_level=None, release_time=None,
                  glide_time=None, audio_bus=None, stereo=None):
        """Changes the given parameters of the SynthDef and (if not silent) sends the new Definition to SuperCollider.

        Parameters
        ----------
        For all parameters: If None is given they are not changed, default value is None.
        For meaning of the parameters see __init__
        """
        
        if partials_amp  is not None: self._partials_amp = partials_amp
        if partials_pos  is not None: self._partials_pos = partials_pos
        if attack_time   is not None: self._attack_time = attack_time
        if decay_time    is not None: self._decay_time = decay_time
        if sustain_level is not None: self._sustain_level = sustain_level
        if release_time  is not None: self._release_time = release_time
        if glide_time    is not None: self._glide_time = glide_time
        if audio_bus     is not None: self._audio_bus = audio_bus
        if stereo        is not None: self._stereo = stereo
        
        if len(self._partials_amp) < len(self._partials_pos):
            self._partials_pos = self._partials_pos[:len(self._partials_amp)]
        elif len(self._partials_amp) > len(self._partials_pos):
            self._partials_amp = self._partials_amp[:len(self._partials_pos)]
        
        if self.silent: return
        
        self._microsynth_def.reset()
        self._microsynth_def.set_context('partials_amp', Audiogenerator.sequence_to_string(self._partials_amp))
        self._microsynth_def.set_context('partials_pos', Audiogenerator.sequence_to_string(self._partials_pos))
        self._microsynth_def.set_context('attack_time', self._attack_time)
        self._microsynth_def.set_context('decay_time', self._decay_time)
        self._microsynth_def.set_context('sustain_level', self._sustain_level)
        self._microsynth_def.set_context('release_time', self._release_time)
        self._microsynth_def.set_context('glide_time', self._glide_time)
        self._microsynth_def.set_context('audio_bus', self._audio_bus)
        if self._stereo:
            self._microsynth_def.set_context('stereo', 2)
        else:
            self._microsynth_def.set_context('stereo', 1)
        
        self._microsynth_name = self._microsynth_def.create()
    
    def set_synth_def_with_dict(self, dictionary):
        """Same as set_synth_def but you give arguments with a dictionary.
        Unknown arguments will be irgnored.
        If know key value pair for an argument is given it won't be changed.
        
        Parameters
        ----------
        dictionary : dict
            {'arg': value} for arguments arg of set_synth_def
        """
        # Actually I don't know why I needed this anymore. But it does not hurt to leave it here I gues.
        keys = ['partials_amp', 'partials_pos', 'attack_time', 'decay_time', 'sustain_level',
                'release_time', 'glide_time', 'audio_bus', 'stereo']
        for key in keys:
            if key not in dictionary: dictionary[key] = None
        self.set_synth_def(partials_amp=dictionary['partials_amp'],
                           partials_pos=dictionary['partials_pos'],
                           attack_time=dictionary['attack_time'],
                           decay_time=dictionary['decay_time'],
                           sustain_level=dictionary['sustain_level'], 
                           release_time=dictionary['release_time'],
                           glide_time=dictionary['glide_time'],
                           audio_bus=dictionary['audio_bus'],
                           stereo=dictionary['stereo'])
        
    def note_on(self, pitch, amp, freq=None):
        """Same as register_note_on(pitch, amp, freq) followed by play_note_on(pitch)"""
        self.register_note_on(pitch, amp, freq)
        self.play_note_on(pitch)
        
    def register_note_on(self, pitch, amp, freq=None):
        """Register a note in the keys dictionary without playing it.
        You need this function only if you want to have lag between registering the key info and the playing
        of the synth, especially if you want to do something else in the time between registering and playing
        (e.g. finding an optimal tuning for the pitch).
        
        Parameters
        ----------
        pitch : int
            midi pitch of the tone to be played.
        amp : float
            Amplitude of the tone to be played.
        freq : float
            Frequency of the tone to be played.
            If None is given the frequency in the Scale is used. (Default value = None)
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if freq is None:
            freq = self._scale[pitch]
        amp = self._global_amp * amp
        
        self.keys[pitch] = KeyData(
            amp, self.attack_time, self.decay_time, self.sustain_level, self.release_time,
            freq, self.partials_pos, self.partials_amp, self.get_now
        )
    
    def play_note_on(self, pitch):
        """Play a note without registering it.
        You need this function only if you want to have lag between registering the key info and the playing
        of the synth, especially if you want to do something else in the time between registering and playing
        (e.g. finding an optimal tuning for the pitch).
        
        The key MUST be registered before it is played.
        
        Parameters
        ----------
        pitch : int
            midi pitch of the tone to be played.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
            
        # if there is still a synth on that pitch (running or not), stop it immediately
        if self.synths[pitch] is not None:
            self.synths[pitch].fast_release_and_free()
        
        if self.silent:
            self.synths[pitch] = None
        else:
            self.synths[pitch] = CustomSynth(
                self._sc,
                name=self._microsynth_name,
                args={
                    "freq": self.keys[pitch].frequency,
                    "amp" : self.keys[pitch].amplitude
                }
            )
    
    def note_off(self, pitch):
        """Same as register_note_off(pitch, amp, freq) followed by play_note_off(pitch)"""
        self.register_note_off(pitch)
        self.play_note_off(pitch)
            
    def register_note_off(self, pitch):
        """Register a note release in the keys dictionary without sending it to SuperCollider.
        You need this function only if you want to have lag between registering the key info and the playing
        of the synth, especially if you want to do something else in the time between registering and playing
        (e.g. finding an optimal tuning for the pitch).
        
        Parameters
        ----------
        pitch : int
            midi pitch of the tone to be released.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.keys[pitch] is None:
            return
        elif self.keys[pitch].pressed:
            self.keys[pitch].release()
            
    def play_note_off(self, pitch):
        """Telling SuperCollider to release the given key without registering the release.
        You need this function only if you want to have lag between registering the key info and the playing
        of the synth, especially if you want to do something else in the time between registering and playing
        (e.g. finding an optimal tuning for the pitch).
        
        Parameters
        ----------
        pitch : int
            midi pitch of the tone to be released.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.synths[pitch] is None:
            return
        else:
            self.synths[pitch].release()
    
    def note_change_freq(self, pitch, freq):
        """Changes the frequency of the given pitch.
        This has an effect only on a currently running Synth of that pitch.
        It does not change the tuning of future synths of that pitch.
        In general it is better to use the Scale to change frequencies.
        
        Parameters
        ----------
        pitch : int
            midi pitch of the tone to be changed.
        freq : float
            New frequency of the pitch.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.keys[pitch] is not None:
            self.keys[pitch].frequency = freq
        if self.synths[pitch] is not None:
            self.synths[pitch].set_frequency(freq)
     
    def note_change_amp(self, pitch, amp):
        """Changes the amplitude of the given pitch.
        This has an effect only on a currently running Synth of that pitch.
        It does not change the tuning of future synths of that pitch.
        
        Parameters
        ----------
        pitch : int
            midi pitch of the tone to be changed.
        amp : float
            New amplitude of the pitch.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.keys[pitch] is not None:
            self.keys[pitch].amplitude = self._global_amp * amp
        if self.synths[pitch] is not None:
            self.synths[pitch].set_amplitude(self._global_amp * amp)
    
    def stop_all(self):
        """Fast-release and free all running synths."""
        self.register_stop_all()
        self.play_stop_all()
    
    def register_stop_all(self):
        """Register a fast release all keys without sending the message to SuperCollider.
        You need this function only if you want to have lag between registering the key info and the playing
        of the synth, especially if you want to do something else in the time between registering and playing
        (e.g. finding an optimal tuning for the pitch).
        """
        for p in self.keys:
            if self.keys[p] is not None:
                self.keys[p].fast_release()
                
    def play_stop_all(self):
        """Telling SuperCollider to fast release all running synths without registering the release.
        You need this function only if you want to have lag between registering the key info and the playing
        of the synth, especially if you want to do something else in the time between registering and playing
        (e.g. finding an optimal tuning for the pitch).
        """
        for p in self.keys:
            if self.synths[p] is not None:
                self.synths[p].fast_release_and_free()
                self.synths[p] = None
    
    def __del__(self):
        """Stop all running synths on deletion."""
        self.stop_all()
        
    
    # static methods
    
    def sequence_to_string(sequence):
        """Formats a sequence like a super collider float array literal."""
        return '[' + ', '.join([str(float(x)) for x in sequence]) + ']'
    