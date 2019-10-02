from adaptivetuning import KeyData

def approx_equal(a, b, epsilon = 0.01):
    if isinstance(a, list):
        return all([approx_equal(a[i], b[i]) for i in range(len(a))])
    return abs((a - b) / (0.5 * (a + b))) < epsilon

def test_envelope():
    now = 123
    def get_now():
        return now
    
    k = KeyData(amplitude=0.8, attack_time=0.1, decay_time=0.2, sustain_level=0.3, release_time=0.4,
                frequency=123, partials_pos=[1,2,3], partials_amp=[1, 0.7, 0.2], get_now=get_now)
    assert k.amplitude == 0.8
    assert k.attack_time == 0.1
    assert k.decay_time == 0.2
    assert k.sustain_level == 0.3
    assert k.release_time == 0.4
    assert k.frequency == 123
    assert k.partials_pos == [1,2,3]
    assert k.partials_amp == [1, 0.7, 0.2]
    assert k.pressed
    assert k.currently_running
    assert k._timestamp == 123
    assert k.current_amplitude == 0
    now += k.attack_time
    assert approx_equal(k.current_amplitude, 0.8)
    now += k.decay_time
    assert approx_equal(k.current_amplitude, 0.8 * 0.3)
    now += 543
    assert approx_equal(k.current_amplitude, 0.8 * 0.3)
    assert k._timestamp == 123
    k.release()
    assert k._timestamp == 123 + k.attack_time + k.decay_time + 543
    assert not k.pressed
    assert k.currently_running
    assert approx_equal(k.current_amplitude, 0.8 * 0.3)
    now += k.release_time * 0.999
    assert k._timestamp == 123 + k.attack_time + k.decay_time + 543
    assert not k.pressed
    assert k.currently_running
    assert k.current_amplitude < 0.001
    now += k.release_time * 0.002
    assert not k.pressed
    assert not k.currently_running
    assert k.current_amplitude == 0