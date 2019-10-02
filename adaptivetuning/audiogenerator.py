import time
import numpy as np
import sc3nb
from .scale import Scale

class KeyData:
    """KeyData class. Collects all the data about a specific key needed for e.g. a Tuner.
    In particular, it provides functionality to compute the current amplitude based on a adsr-envelope.
    
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
    """
    
    def __init__(self, amplitude=1, attack_time=0, decay_time=0, sustain_level=1, release_time=0,
                 frequency=440, partials_pos=[1], partials_amp=[0], get_now=None, pressed=True):
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
        """bool : True if the key is currently pressed, false if released. Read only."""
        return self._pressed
    
    @property
    def currently_running(self):
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
        """float : Current amplitude."""
        return self.amplitude * self.current_env
    
    def press(self):
        self._pressed = True
        self._timestamp = self.get_now()
    
    def release(self):
        if self._pressed:
            self._env_when_released = self.current_env
            self._timestamp = self.get_now()
            self._pressed = False
            
    def fast_release(self):
        self.release_time = 0
        self.release()
        
        
class CustomSynth(sc3nb.synth.Synth):
        """Custom synth class
        Has to be freed manually or via doneAction, it is not automatically freed on deletion!
        Only works with a SynthDef that provides a sustained envelope with a matching release
        and a gate called 'gate' without Done.freeSelf and a second envelope with a fast release
        and with Done.freeSelf.
        """ 
        def release(self):
            self.set("gate", 0)

        def fast_release_and_free(self):
            self.set("fast_gate", 0)

        def set_frequency(self, frequency):
            self.set("freq", frequency)

        def set_amplitude(self, amplitude):
            self.set("amp", amplitude)
        
        def __del__(self):
            pass  # pass instead of self.free()
        
        
# is it a problem to have at worst 128 Synth runing in Osc?

# todo 
# write docu

#todo besser alle keys am anfang initialisieren und dann für immer behalten,
# dann brauch ich nicht immer nachfragen ob die existieren

class Audiogenerator:
    """Audiogenerator class. Manages a microtonal additive synthesizer.
    
    Attributes
    ----------
    sc: sc3nb.SC or None
        bla
    global_amp: float
        bla
    scale: Scale
    ...TODO
    
    protected:
    _microsynth_def
    _microsynth_name
    
    keys: dict of keys
    synths: dict of synths
    
    partials_amp: sequence of floats
    partials_pos: sequence of floats
    attack_time: float
    decay_time: float
    sustain_level: float
    release_time: float
    glide_time: float
    audio_bus: int
    stereo: bool
    silent: bool
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
    
    
    def __init__(self, sc=None, global_amp=0.01, scale=None,
                 partials_amp=None, partials_pos=None,
                 attack_time=0.1, decay_time=0.1, sustain_level=0.8, release_time=0.2,
                 glide_time=0.1, audio_bus=0, stereo=True, silent=False, get_now=None):
        """___init___ method
        
        Parameters
        ----------
        sc: SC
            A SC object to communicate with super collider.
        """
        
        # We need to manage them seperately so that we can have lag between setting of the key infos and actually
        # playing of the synth such that the key infos are representing what will sound in the future
        self.keys = {i: KeyData(pressed=False) for i in range(128)}
        self.synths = {i: None for i in range(128)}
        
        
        # Generally the setter pressupose that the whole setup is done, that's why the protected attributes
        # are set directly here
        self._global_amp = global_amp
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
        """float : Global amplitude factor of the sound audio generator."""
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
        """Scale : Manages a dictionary that assigns every pitch a frequency."""
        return self._scale
    
    @scale.setter
    def scale(self, scale):
        # if there are running synthesizers, change their frequencies accordingly
        for p in self.keys:
            self.note_change_freq(p, scale[p])
                
        # previous on_change method will be overwritten!
        scale.on_change = lambda pitch, freq: self.note_change_freq(pitch, freq)
        
        self._scale = scale
        
    @property
    def partials_amp(self):
        """sequence of floats : Volume of the partials of the Synth in amplitude.
        artials_amp can be given as a dictopnary of instructions (not on construction though!).
        {'method': 'harmonic', 'nr_partials': int (default len(partials_amp)), 'factor': float (default 1)}
        for [1 / (i * factor) for i in range(1, nr_partial + 1)]
        {'method': 'exponential', 'nr_partials': int (default len(partials_amp)), 'base': float (default 0.8)}
        for [base**i for i in range(0, nr_partial)]
        """
        return self._partials_amp
    
    @partials_amp.setter
    def partials_amp(self, partials_amp):
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
        """sequence of floats : Relative position of the partials of the Synth in amplitude.
        Don't forget the fundamental (relative position = 1) - it's also a partial!
        
        partials_pos can be given as a dictopnary of instructions (not on construction though!).
        {'method': 'harmonic', 'nr_partials': int (default len(partials_amp)), 'octave': float (default 2)}
        for [octave**log2(i) for i in range(1, nr_partial + 1)]
        ()
        """
        return self._partials_pos
    
    @partials_pos.setter
    def partials_pos(self, partials_pos):
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
        """float : Attack time (in seconds) of the adsr-envelope of the synth."""
        return self._attack_time
    
    @attack_time.setter
    def attack_time(self, attack_time):
        self.set_synth_def(attack_time=attack_time)
    
    @property
    def decay_time(self):
        """float : Decay time (in seconds) of the adsr-envelope of the synth."""
        return self._decay_time
    
    @decay_time.setter
    def decay_time(self, decay_time):
        self.set_synth_def(decay_time=decay_time)
        
    @property
    def sustain_level(self):
        """float : Sustain level (in amplitude) of the adsr-envelope of the synth."""
        return self._sustain_level
    
    @sustain_level.setter
    def sustain_level(self, sustain_level):
        self.set_synth_def(sustain_level=sustain_level)
        
    @property
    def release_time(self):
        """float : Release time (in seconds) of the adsr-envelope of the synth."""
        return self._release_time
    
    @release_time.setter
    def release_time(self, release_time):
        self.set_synth_def(release_time=release_time)
        
    @property
    def glide_time(self):
        """float : Glide time (in seconds) of the the synth.
        The time it takes to change the amp or felocity of a sounding tone.
        Setting it to 0 risks artifacts, big values result in a audible sliding sound."""
        return self._glide_time
    
    @glide_time.setter
    def glide_time(self, glide_time):
        self.set_synth_def(glide_time=glide_time)
        
    @property
    def audio_bus(self):
        """int : Audiobuss to play the synth on.
        Generally, 0 is the left speaker and 1 is the right speaker.
        If stereo is true the synth will play on audio_bus and audio_bus + 1"""
        return self._audio_bus
    
    @audio_bus.setter
    def audio_bus(self, audio_bus):
        self.set_synth_def(audio_bus=audio_bus)
        
    @property
    def stereo(self):
        """Bool : If stereo is true the synth will play on audio_bus and audio_bus + 1"""
        return self._stereo
    
    @stereo.setter
    def stereo(self, stereo):
        self.set_synth_def(stereo=stereo)
    
    @property
    def silent(self):
        """Bool : If silent is true there will be no actual communication with super collider.
        I.e. no Synthdefinition will be created, no Synths will be created in super collider.
        Everything else works as usual - good for testing.
        Can only be set to True if sc is not None"""
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
        """Function : Returns the current time in seconds."""
        return self._get_now
    
    @get_now.setter
    def get_now(self, get_now):
        self._get_now = get_now   
    
    @property
    def sc(self):
        """SC : A SC object to communicate with super collider.
        Setting sc also sends the SynthDef"""
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
        # Dictionary {'arg': value} for arguments of set_synth_def.
        # Unknown arguments will be irgnored.
        # If know key value pair for an argument is given it won't be changed.
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
        self.register_note_on(pitch, amp, freq)
        self.play_note_on(pitch)
        
    def register_note_on(self, pitch, amp, freq=None):
        # you need this function only if you want to have lag between registering the key info and the playing
        # of the synth, especially if you want to do something else in the time between registering and playing
        # (e.g. finding an optimal tuning for the pitch).
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
        self.register_note_off(pitch)
        self.play_note_off(pitch)
            
    def register_note_off(self, pitch):
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.keys[pitch] is None:
            return
        elif self.keys[pitch].pressed:
            self.keys[pitch].release()
            
    def play_note_off(self, pitch):
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.synths[pitch] is None:
            return
        else:
            self.synths[pitch].release()
    
    def note_change_freq(self, pitch, freq):
        """This has an effect only on a currently running Synth of that pitch.
        It does not change the tuning of future synths of that pitch.
        """
        if isinstance(pitch, str):
            pitch = Scale.pitchname_to_pitch(pitch)
        
        if self.keys[pitch] is not None:
            self.keys[pitch].frequency = freq
        if self.synths[pitch] is not None:
            self.synths[pitch].set_frequency(freq)
     
    def note_change_amp(self, pitch, amp):
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
        for p in self.keys:
            if self.keys[p] is not None:
                self.keys[p].fast_release()
                
    def play_stop_all(self):
        for p in self.keys:
            if self.synths[p] is not None:
                self.synths[p].fast_release_and_free()
                self.synths[p] = None
    
    def __del__(self):
        self.stop_all()
        
    
    # static methods
    
    def sequence_to_string(sequence):
        """Formats a sequence like a super collider float array literal"""
        return '[' + ', '.join([str(float(x)) for x in sequence]) + ']'
    