from adaptivetuning import Audioanalyzer
import numpy as np

def approx_equal(a, b, epsilon = 0.01):
    if isinstance(a, list):
        return all([approx_equal(a[i], b[i]) for i in range(len(a))])
    return abs((a - b) / (0.5 * (a + b))) < epsilon

def test_analyze_signal():
    audioanalyzer = Audioanalyzer()
    ts = np.linspace(0, 1, audioanalyzer.sample_rate)
    f = 440
    signal = np.sin(2 * np.pi * f * ts)
    freqs, amps = audioanalyzer.analyze_signal(signal)
    assert approx_equal(freqs[0], f)
    assert approx_equal(amps[0], 1)
