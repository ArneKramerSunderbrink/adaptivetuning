from adaptivetuning import Audiogenerator
from adaptivetuning import Scale

def approx_equal(a, b, epsilon = 0.01):
    if isinstance(a, list):
        return all([approx_equal(a[i], b[i]) for i in range(len(a))])
    return abs((a - b) / (0.5 * (a + b))) < epsilon

def test_setters_getters():
    audiogenerator = Audiogenerator(sc=None)
    audiogenerator.global_amplitude = 0.02
    assert audiogenerator.global_amplitude == 0.02
    audiogenerator.attack_time = 0.2
    assert audiogenerator.attack_time == 0.2
    audiogenerator.decay_time = 1.2
    assert audiogenerator.decay_time == 1.2
    audiogenerator.sustain_level = 0.1
    assert audiogenerator.sustain_level == 0.1
    audiogenerator.release_time = 1.1
    assert audiogenerator.release_time == 1.1
    audiogenerator.lag_time = 1.1
    assert audiogenerator.lag_time == 1.1
    audiogenerator.audio_bus = 2
    assert audiogenerator.audio_bus == 2
    audiogenerator.stereo = False
    assert not audiogenerator.stereo
    audiogenerator.set_synth_def_with_dict({'partials_pos': [1,2,3], 'attack_time': 0.1, 'decay_time': 0.2,
                                            'sustain_level': 0.5, 'release_time': 0.1, 'audio_bus': 0})
    assert audiogenerator.partials_pos == [1,2,3]
    assert len(audiogenerator.partials_amp) == 3
    assert audiogenerator.attack_time == 0.1
    assert audiogenerator.decay_time == 0.2
    assert audiogenerator.sustain_level == 0.5
    assert audiogenerator.release_time == 0.1
    assert audiogenerator.audio_bus == 0

    audiogenerator.partials_amp = [0.1, 0.2, 0.3]
    assert audiogenerator.partials_amp == [0.1, 0.2, 0.3]
    assert len(audiogenerator.partials_pos) == 3
    audiogenerator.partials_pos = range(1,5)
    assert audiogenerator.partials_pos == range(1,5)
    assert audiogenerator.partials_amp == [0.1, 0.2, 0.3, 0]
    audiogenerator.partials_amp = {'method': 'harmonic', 'factor': 1, 'nr_partials': 4}
    assert audiogenerator.partials_amp == [1, 1/2, 1/3, 1/4]
    audiogenerator.partials_amp = {'method': 'exponential', 'base': 0.2, 'nr_partials': 3}
    assert approx_equal(audiogenerator.partials_amp, [1, 0.2, 0.04])
    audiogenerator.partials_pos = {'method': 'harmonic', 'octave': 2, 'nr_partials': 4}
    assert audiogenerator.partials_pos == [1,2,3,4]
    del audiogenerator
    
    
def test_note_on_off():
    audiogenerator = Audiogenerator(sc=None)
    audiogenerator.note_on('A4', 0.7)
    assert audiogenerator.keys[69].frequency == 440
    audiogenerator.scale = Scale(reference_frequency=450)
    assert audiogenerator.keys[69].frequency == 450
    audiogenerator.scale[69] = 460
    assert audiogenerator.keys[69].frequency == 460
    audiogenerator.note_change_freq('A4', 470)
    assert audiogenerator.keys[69].frequency == 470
    audiogenerator.note_change_amp('A4', 0.5)
    assert audiogenerator.keys[69].amplitude == 0.5 * audiogenerator.global_amplitude
    audiogenerator.note_off('A4')
    audiogenerator.note_on('A4', 0.8)
    audiogenerator.attack_time = 0.1
    audiogenerator.note_on('A4', 0.2)
    assert audiogenerator.keys[69].attack_time == 0.1
    audiogenerator.attack_time = 0.2
    assert audiogenerator.keys[69].attack_time == 0.1
    audiogenerator.note_on('A#4', 0.2)
    assert audiogenerator.keys[70].attack_time == 0.2
    audiogenerator.note_off('A4')
    audiogenerator.stop_all()
    assert not audiogenerator.keys[69].currently_running
    assert not audiogenerator.keys[70].currently_running
    
    
def test_release():
    now = 0
    def get_now():
        return now

    audiogenerator = Audiogenerator(sc=None, get_now=get_now, release_time=2)

    audiogenerator.note_on('A4', 1)
    assert audiogenerator.keys[69].currently_running
    audiogenerator.note_off('A4')
    assert audiogenerator.keys[69].currently_running
    now = 1
    audiogenerator.note_off('A4')
    assert audiogenerator.keys[69].currently_running
    now = 2.1

