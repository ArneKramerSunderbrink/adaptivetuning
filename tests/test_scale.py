from adaptivetuning import Scale
from adaptivetuning import read_scala
import numpy as np

def approx_equal(a, b, epsilon = 0.01):
    if isinstance(a, list):
        return all([approx_equal(a[i], b[i]) for i in range(len(a))])
    return abs((a - b) / (0.5 * (a + b))) < epsilon

# pitchname_test
def test_pitchname():
    scale = Scale()
    assert Scale.pitchname_to_pitch('A4') == 69
    assert Scale.pitchname_to_pitch('Ab-1') == 8
    assert Scale.pitchname_to_pitch('A-1') == 9
    assert Scale.pitchname_to_pitch('B8') == 119

    assert Scale.pitch_to_pitchname(69) == 'A4'
    assert Scale.pitch_to_pitchname(8) == 'Ab-1' or Scale.pitch_to_pitchname(8) == 'G#-1'
    assert Scale.pitch_to_pitchname(9) == 'A-1'
    assert Scale.pitch_to_pitchname(119) == 'B8'

    
def test_getter():
    scale = Scale()
    assert max(scale.specified_pitches) == 127
    assert scale[127] == scale[128]
    assert scale[69.5] == scale['A4']
    assert scale[69.51] == scale['A#4']
    assert len(scale[:]) == 128
    assert len(scale[:123]) == 123
    assert len(scale[123:]) == 128 - 123
    assert len(scale[::2]) == 128 / 2
    assert scale['A4', 'A5'] == [440, 880]
    
    
def test_setter():
    scale = Scale()
    scale['A4'] = 400
    assert scale[69] == 400
    assert scale[69.4] == 400  # not specified but near to a specified
    scale[69.5] = 500
    assert scale[69.5] == 500
    assert scale[69.4] == 500  # not specified but near to a specified
    scale[1:10:2] = [1,2,3,4,5]
    assert scale[1:10:2] == [1,2,3,4,5]
    scale['A4', 'C#2'] = [1,2]
    assert scale['A4', 'C#2'] == [1,2]
    
    
def test_callback():
    class Callback:
        def __init__(self):
            self.pitch = None
            self.frequency = None

        def call(self, pitch, frequency):
            #print(pitch, frequency)
            self.pitch = pitch
            self.frequency = frequency

    c = Callback()

    scale = Scale()
    scale.on_change = c.call
    assert c.frequency == None
    assert c.pitch == None
    scale['A4'] = 440
    assert c.frequency == 440
    assert c.pitch == 69
    
    
def test_tune_all_by_interval_in_cents():
    intervals_in_cents = Scale.tunings_in_cents['Werkmeister 4']

    scale = Scale(reference_pitch='C4', reference_frequency=440/Scale.cents_to_freq_ratio(intervals_in_cents[9]))

    scale.tune_all_by_interval_in_cents(intervals_in_cents)

    assert scale['A4'] == 440
    assert approx_equal(Scale.freq_ratio_to_cents(scale['E3'] / scale['C3']), intervals_in_cents[4])
    
def test_generalize_to_midi_range():
    diatonic_pitches = ['C4','D4', 'E4', 'F4', 'G4', 'A4', 'B4']
    diatonic_intervals = [1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8]
    scale = Scale(reference_pitch=diatonic_pitches[0], reference_frequency=440/diatonic_intervals[5],
                  pitches_per_octave=len(diatonic_pitches), octave_interval=2,
                  specified_pitches=diatonic_pitches, init_ET=False)

    assert scale[tuple(diatonic_pitches)] == [0, 0, 0, 0, 0, 0, 0]

    scale.tune_all_by_interval(diatonic_intervals, diatonic_pitches)

    assert scale['G4'] / scale['E4'] == 6/5
    assert scale['F4'] / scale['D4'] == 32/27  # different minor third
    assert scale['A4'] / scale['D4'] == 40/27  # flat fifth

    assert min(scale.specified_pitches) == Scale.pitchname_to_pitch('C4')
    assert max(scale.specified_pitches) == Scale.pitchname_to_pitch('B4')

    scale.generalize_to_midi_range(diatonic_pitches)

    assert min(scale.specified_pitches) == Scale.pitchname_to_pitch('C-1')
    assert max(scale.specified_pitches) == Scale.pitchname_to_pitch('G9')

    assert scale['G6'] / scale['E6'] == 6/5
    assert scale['F0'] / scale['D0'] == 32/27  
    assert scale['A3'] / scale['D2'] == 40/27 * 2
    
    
def test_tune_all_by_interval():
    intervals = [1, 27/25, 25/21, 9/7, 7/5, 75/49, 5/3, 9/5, 49/25, 15/7, 7/3, 63/25, 25/9]
    scale = Scale(reference_pitch='C4', reference_frequency=260,
                                 pitches_per_octave=13, octave_interval=3)
    scale.tune_all_by_interval(intervals)
    assert scale[60+13] == 3 * scale[60]
    assert scale[20+26+11] == scale[20] * 9 * intervals[11]
    
    
def test_specified_pitches():
    scale = Scale(specified_pitches=range(69, 69+12, 2), octave_interval=2.5)
    assert list(scale.specified_pitches) == [69, 71, 73, 75, 77, 79]
    assert scale['A#4'] == 440  # not specified
    scale.specified_pitches = [69, 70, 71, 72, 73]
    assert scale['A4'] == 440  # old specification
    assert scale['A#4'] == 0  # now specified and set to 0
    
    
def test_tuning():
    scale = Scale()
    scale.tune_pitch('A4', 441)
    assert scale[69] == 441
    scale['A#4'] = 442
    assert scale[70] == 442
    scale[69:73] = [500, 501, 502, 503]
    assert scale[69:73] == [500, 501, 502, 503]
    
    scale = Scale()
    assert scale['E5'] / scale['A4'] != 3/2  # ET!
    scale.tune_pitch_by_interval('E5', 3/2)
    assert scale['E5'] / scale['A4'] == 3/2
    
    scale = Scale()
    scale.tune_pitchclass('C3', 100)
    assert approx_equal(scale['C2'], 50)
    assert approx_equal(scale['C3'], 100)
    assert approx_equal(scale['C4'], 200)
    scale.reference_frequency = 400
    scale.tune_pitchclass_by_interval('C3', 1.1)
    assert approx_equal(scale['C2'], 220)
    assert approx_equal(scale['C3'], 440)
    assert approx_equal(scale['C4'], 880)
    
    scale = Scale()
    # 10 tone equal temperament witch octave streched to 10 : 1
    scale.reference_pitch = 33
    scale.reference_frequency = 1
    scale.pitches_per_octave = 10
    scale.octave_interval = 10
    scale.tune_all_equal_temperament()
    assert approx_equal(10 * scale[33], scale[43])
    assert approx_equal(scale[33]/scale[34], scale[98]/scale[99])
    
    scale = Scale()
    scale.tune_pitch_by_interval_in_cents(70, 123)
    assert abs(np.log2(scale[70] / scale[69]) * 1200 - 123) < 1e-10
    scale.tune_pitchclass_by_interval_in_cents(70, 345)
    assert abs(np.log2(scale[70] / scale[69]) * 1200 - 345) < 1e-10
    assert abs(np.log2(scale[70+12] / scale[69]) * 1200 - (345 + 1200)) < 1e-10