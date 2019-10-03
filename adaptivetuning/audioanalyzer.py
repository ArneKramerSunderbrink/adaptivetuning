import numpy as np
import scipy.signal
import pyaudio
import wave
import time

# todo
# doku

# there are many possible upgrades here: start reading a file from a certain point, read a file offline, have a
# real silent playback without output, not with zero-output... etc

class Audioanalyzer:
    """
    Attributes temporarily needed and created when reading a file:
    self._nr_channels, self._wave_file, self._format
    """
    
    def __init__(self, sample_rate=44100, low_cut=20, high_cut=18000, downsample=8, blocksize=2**15,
                 prominence_threshold=0.015, max_nr_peaks=10, result_callback=None,
                 silent=True):
        """INIT: TODODOKU
        
        Parameters
        ----------
        sample_rate: int
            The sample rate of the signal to be analyzed. (Default value = 44100)
        low_cut: int
            The lowest frequency (in Hz) to be included in the analyzis. (Default value = 20)
        high_cut: int
            The highest frequency (in Hz) to be included in the analyzis. (Default value = 18000)
        prominence_threshold: float
            Minimal prominence of peaks (see scipy.signal.find_peaks). (Default value = 0.015)
            
        TODO downsample, blocksize, it is strongly recommended to use the default values unless you
        know what your doing - the results on fft computation time and accuracy can be quite unpredictable...
        downsample musst be an integer! downsample = n means take every nth sample
        prominence_threshold = 0 to not filter
        max_nr_peaks = None to get all detected peaks
        resultcallback...
            
        """
        if result_callback is None:
            result_callback = lambda peaks_freq, peaks_amp: None
        self.result_callback = result_callback
        
        self.sample_rate = sample_rate
        self.low_cut = low_cut
        self.high_cut = high_cut
        self.downsample = downsample
        self.blocksize = blocksize
        self.prominence_threshold = prominence_threshold
        self.max_nr_peaks = max_nr_peaks
        
        self.silent = silent
        
    def analyze_signal(self, signal):
        """Finds prominent frequencies in a given Signal.

        Parameters
        ----------
        signal: np.array
            The signal to be analyzed

        Returns
        -------
        peaks_freq: list of floats
            A list of the approximated frequencies of the ten most prominent peaks, sorted by prominence.
        peaks_amp: list of floats
            A list of the approximated volumes of the ten most prominent peaks, sorted by prominence.
        """
        
        # Downsample
        signal = signal[::self.downsample].astype(np.float32)

        # normalize
        signal -= np.mean(signal)
        max_amp = np.max(np.abs(signal))
        if max_amp == 0:
            self.result_callback([], [])
            return [], []
        signal /= max_amp

        # how to translate frequency to spectrum-index
        nr_samples = signal.size
        index_to_freq_factor = self.sample_rate / self.downsample / nr_samples
        low_i = int(self.low_cut / index_to_freq_factor)
        high_i = int(self.high_cut / index_to_freq_factor)
        
        # FFT
        spectrum = np.abs(np.fft.rfft(signal)[low_i:high_i]) / nr_samples * 2

        #find peaks
        peaks, properties = scipy.signal.find_peaks(spectrum, prominence=self.prominence_threshold)
        prominences = properties['prominences']
        most_prominent = peaks[sorted(range(prominences.size), key=lambda i: - prominences[i])[:self.max_nr_peaks]]
        peaks_amp = max_amp * spectrum[most_prominent]  # denormalized
        peaks_freq = (most_prominent + low_i) * index_to_freq_factor
        
        self.result_callback(peaks_freq, peaks_amp)
        
        return peaks_freq, peaks_amp
    
    def _file_callback(self, in_data, frame_count, time_info, status):
        data = self._wave_file.readframes(frame_count)
        
        signal = np.copy(np.frombuffer(data, self._format))
        
        # play back a zero array if silent
        if self.silent:
            data = np.zeros_like(signal).tobytes()
        
        # we only analyze full blocks
        if len(signal) != self.blocksize * self._nr_channels:
            return data, pyaudio.paContinue
        
        signal = np.copy(signal)  # frombuffer yields read only, so we need a copy
        
        # if it's not mono, use only the first channel
        if self._nr_channels > 1:
            signal = signal.reshape((self.blocksize, self._nr_channels))[:,0]
        
        # this is my hacky method of translating sample values into reasonable amplitude values
        if self._format == np.float32:
            signal = signal / np.finfo(self._format).max * 20
        else:
            signal = signal / np.iinfo(self._format).max * 20
        
        self.analyze_signal(signal)
        
        return data, pyaudio.paContinue
    
    def analyze_file(self, file, max_duration=None, stop_event=None):
        """
        file: str
            Path to file to be played.
        max_duration: float
            Maximal duration for wich the file will be played.
            If None it plays the whole file if it's not stopped via stop_event. (Default = None)
        stop_event: threading.Event
            ...TODO
            
        """
        self._wave_file = wave.open(file, 'rb')
        p = pyaudio.PyAudio()
        
        self._format = Audioanalyzer.pa_to_np_format(p.get_format_from_width(self._wave_file.getsampwidth()))
        self._nr_channels = self._wave_file.getnchannels()

        stream = p.open(format=p.get_format_from_width(self._wave_file.getsampwidth()),
                        channels=self._nr_channels,
                        rate=self._wave_file.getframerate(),
                        output=True,
                        frames_per_buffer=self.blocksize,
                        stream_callback=self._file_callback)
        stream.start_stream()

        # Wait for audio to finish or duration to end or to be stopped via event
        t = max_duration
        while stream.is_active() and (stop_event is None or not stop_event.is_set()):
            if t is not None:
                if t < 0: break
                t -= 0.1
            time.sleep(0.1)
        
        stream.stop_stream()
        stream.close()
        self._wave_file.close()
        p.terminate()
    
    def _record_callback(self, in_data, frame_count, time_info, status):
        signal = np.copy(np.frombuffer(in_data, self._format))
        
        # we only analyze full blocks
        if len(signal) != self.blocksize:
            return data, pyaudio.paContinue
        
        signal = np.copy(signal)  # frombuffer yields read only, so we need a copy
        
        # this is my hacky method of translating sample values into reasonable amplitude values
        if self._format == np.float32:
            signal = signal / np.finfo(self._format).max * 20
        else:
            signal = signal / np.iinfo(self._format).max * 20
        
        self.analyze_signal(signal)
        
        return in_data, pyaudio.paContinue
    
    def analyze_record(self, max_duration=None, stop_event=None):
        p = pyaudio.PyAudio()
        
        self._format = Audioanalyzer.pa_to_np_format(p.get_format_from_width(2))

        stream = p.open(format=p.get_format_from_width(2),
                        channels=1,
                        rate=self.sample_rate,
                        input=True,
                        output=not self.silent,
                        frames_per_buffer=self.blocksize,
                        stream_callback=self._record_callback)
        stream.start_stream()

        # Wait for audio to finish or duration to end or to be stopped via event
        t = max_duration
        while stream.is_active() and (stop_event is None or not stop_event.is_set()):
            if t is not None:
                if t < 0: break
                t -= 0.1
            time.sleep(0.1)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    def pa_to_np_format(pa_format):
        return {
            1: np.float32,
            2: np.int32,
            #4: np.int24, there is no 24 bit int type in np
            8: np.int16,
            16: np.int8,
            32: np.uint8
        }[pa_format]
        