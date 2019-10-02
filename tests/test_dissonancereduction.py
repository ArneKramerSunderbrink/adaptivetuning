from adaptivetuning import Dissonancereduction
import numpy as np

def approx_equal(a, b, epsilon = 0.01):
    if isinstance(a, list):
        return all([approx_equal(a[i], b[i], epsilon) for i in range(len(a))])
    return abs((a - b) / (0.5 * (a + b))) < epsilon

def test_reduction():
    ji_intervals = [1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8, 2]
    partials_vol_piano = np.array([3.7, 5.4, 1.2, 1.1, 0.95, 0.6, 0.5, 0.65, 0.001, 0.1, 0.2]) / 5.4

    # A major chord in closed position with added octave
    notes = [0, 4, 7, 12]
    et_fundamentals = [440 * 2**(i/12) for i in notes]  # equal tempered version of that chord
    ji_fundamentals = [440 * ji_intervals[i] for i in notes]  # just version
    fundamentals_vol = np.ones(len(notes))
    partials_pos = list(range(1, len(partials_vol_piano) + 1))
    partials_vol = partials_vol_piano

    # The partials of the tonic are used as fixed positions
    fixed_freq = [et_fundamentals[0] * p for p in partials_pos]
    fixed_vol = [fundamentals_vol[0] * v for v in partials_vol]

    dissonancereduction = Dissonancereduction()

    relevant_pairs, critical_bandwidths, volume_factors = dissonancereduction.quasi_constants(
        np.array(et_fundamentals[1:]), np.array(fundamentals_vol[1:]),
        np.array(partials_pos), np.array(partials_vol),
        np.array(fixed_freq), np.array(fixed_vol))

    # droping pairs with v = 0 or h > 1.46 reduces the amount of relevant pairs from 1210 to 140
    assert len(relevant_pairs) == 140

    # The second overtone of the tonic (2, -1) and the first overtone of the fifths (1, 1) are close -> relevant
    assert [1, 1, 2, -1] in relevant_pairs.tolist()

    # The fundamental of the tonic (0, -1) and the first overtone of the fifths (1, 1) are not close -> irrelevant
    assert [1, 1, 0, -1] not in relevant_pairs.tolist()

    # The eighth overtones of the third and fifths are close -> relevant
    assert [0, 8, 1, 8] in relevant_pairs.tolist()

    # but since the eighth overtone of our piano is very week, the volume factor of the pair is small:
    assert approx_equal(volume_factors[relevant_pairs.tolist().index([0, 8, 1, 8])], 0.8608141448259226)

    # The first overtones are strong -> big volume factor
    assert approx_equal(volume_factors[relevant_pairs.tolist().index([0, 1, 1, 1])], 4.5313189239810825)

    # First overtones of the third and the fifths ([0, 1, 1, 1]) are approximately at 1200 HZ where the critical
    # bandwidth is approximately 200 Hz, our approximation is very rough of course
    assert approx_equal(critical_bandwidths[relevant_pairs.tolist().index([0, 1, 1, 1])], 187.33314724834622)

    # Third overtones of the third and the fifths ([0, 3, 1, 3]) are approximately at 2400 HZ where the critical
    # bandwidth is approximately 380 Hz
    assert approx_equal(critical_bandwidths[relevant_pairs.tolist().index([0, 3, 1, 3])], 373.04659900888373)

    dissonance, gradient = dissonancereduction.dissonance_and_gradient(
        np.array(et_fundamentals[1:]), np.array(partials_pos), np.array(fixed_freq),
        np.array(critical_bandwidths), np.array(volume_factors), np.array(relevant_pairs))

    # The most dissonant note of an equal tempered major chord is the major third which is to sharp
    # -> the biggest value of the gradient is the one corresponding to the major third and the negative gradient is
    # pointing in the negative direction, corresponding to a down-tuning of the third
    assert max(abs(gradient)) == gradient[0]

    result = dissonancereduction.tune(np.array(et_fundamentals[1:]), np.array(fundamentals_vol[1:]),
                                      np.array(partials_pos), np.array(partials_vol),
                                      np.array(fixed_freq), np.array(fixed_vol))
    assert result['success']

    # The resulting chord is more similar to a just major chord than to a equal tempered major chord:
    assert not approx_equal([et_fundamentals[0]] + result['x'].tolist(), et_fundamentals, epsilon=0.001)
    assert approx_equal([et_fundamentals[0]] + result['x'].tolist(), ji_fundamentals, epsilon=0.001)
    
    
def test_zero_cases():
    ji_intervals = [1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8, 2]
    partials_vol_piano = np.array([3.7, 5.4, 1.2, 1.1, 0.95, 0.6, 0.5, 0.65, 0.001, 0.1, 0.2]) / 5.4

    # A major chord in closed position with added octave
    notes = [0, 4, 7, 12]
    et_fundamentals = [440 * 2**(i/12) for i in notes]  # equal tempered version of that chord
    ji_fundamentals = [440 * ji_intervals[i] for i in notes]  # just version
    fundamentals_vol = np.ones(len(notes))
    partials_pos = list(range(1, len(partials_vol_piano) + 1))
    partials_vol = partials_vol_piano

    # The partials of the tonic are used as fixed positions
    fixed_freq = [et_fundamentals[0] * p for p in partials_pos]
    fixed_vol = [fundamentals_vol[0] * v for v in partials_vol]

    dissonancereduction = Dissonancereduction()

    
    # We are only interested in the dissonance relative to the fundamentals
    # If there are no fundamentals, dissonance is 0
    relevant_pairs, critical_bandwidths, volume_factors = dissonancereduction.quasi_constants(
        np.array([]), np.array([]), np.array([]), np.array([]), np.array([]), np.array([]))
    assert len(relevant_pairs) == 0

    dissonance, gradient = dissonancereduction.dissonance_and_gradient(
        np.array([]), np.array([]), np.array([]),
        np.array([]), np.array([]), np.array([]))
    assert dissonance == 0
    assert len(gradient) == 0

    result = dissonancereduction.tune(np.array([]), np.array([]),
                                      np.array([]), np.array([]),
                                      np.array([]), np.array([]))
    assert len(result['x']) == 0

    # If there is only one fundamental and no fixed frequencies, dissonance is 0
    relevant_pairs, critical_bandwidths, volume_factors = dissonancereduction.quasi_constants(
        np.array([et_fundamentals[0]]), np.array([fundamentals_vol[0]]),
        np.array(partials_pos), np.array(partials_vol),
        np.array([]), np.array([]))
    assert len(relevant_pairs) == 0

    dissonance, gradient = dissonancereduction.dissonance_and_gradient(
        np.array([et_fundamentals[0]]), np.array(partials_pos), np.array([]),
        np.array([]), np.array([]), np.array([]))
    assert dissonance == 0
    assert gradient == np.array([0.])

    result = dissonancereduction.tune(np.array([et_fundamentals[0]]), np.array([fundamentals_vol[0]]),
                                      np.array(partials_pos), np.array(partials_vol),
                                      np.array([]), np.array([]))
    assert len(result['x']) == 1
    assert result['x'][0] == 440