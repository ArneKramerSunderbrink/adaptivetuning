import numpy as np
import matplotlib.pyplot as plt
import threading
import time
import pickle
from .scale import Scale
from .audiogenerator import Audiogenerator
from .midiprocessing import Midiprocessing
from .audioanalyzer import Audioanalyzer
from .dissonancereduction import Dissonancereduction


def plot_session_log(session_log, save_to_file=False):
    if len(session_log['tunings']) == 0:
        print("No tunings to plot.")
        return
    
    dissonancereduction = Dissonancereduction()
    scale_et = Scale()
    scale_ji = Scale(reference_pitch='C4', reference_frequency=scale_et['C4'])
    scale_ji.tune_all_by_interval_in_cents(Scale.tunings_in_cents['Natural (JI)'])

    times = list(session_log['tunings'].keys())

    et_freqs = [scale_et[session_log['tunings'][t]['pitches']] for t in times]
    et_times, et_freqs = zip(*[(times[i], f) for i in range(len(times)) for f in et_freqs[i]])
    tuned_freqs = [session_log['tunings'][t]['tuned_fundamentals'] for t in times]
    tuned_times, tuned_freqs = zip(*[(times[i], f) for i in range(len(times)) for f in tuned_freqs[i]])
    fixed_freqs = [session_log['tunings'][t]['fixed_freq'] for t in times]
    if not all([len(f) == 0 for f in fixed_freqs]):
        fixed_times, fixed_freqs = zip(*[(times[i], f) for i in range(len(times)) for f in fixed_freqs[i]])
    else:
        fixed_times, fixed_freqs = (), ()

    tuned_diss = [dissonancereduction.single_dissonance_and_gradient(
        session_log['tunings'][t]['tuned_fundamentals'],
        session_log['tunings'][t]['fundamentals_amp'],
        session_log['tunings'][t]['partials_pos'],
        session_log['tunings'][t]['partials_amp'],
        session_log['tunings'][t]['fixed_freq'],
        session_log['tunings'][t]['partials_amp']
    )[0] for t in times]

    et_diss = [dissonancereduction.single_dissonance_and_gradient(
        scale_et[session_log['tunings'][t]['pitches']],
        session_log['tunings'][t]['fundamentals_amp'],
        session_log['tunings'][t]['partials_pos'],
        session_log['tunings'][t]['partials_amp'],
        session_log['tunings'][t]['fixed_freq'],
        session_log['tunings'][t]['partials_amp']
    )[0] for t in times]
    
    ji_diss = [dissonancereduction.single_dissonance_and_gradient(
        scale_ji[session_log['tunings'][t]['pitches']],
        session_log['tunings'][t]['fundamentals_amp'],
        session_log['tunings'][t]['partials_pos'],
        session_log['tunings'][t]['partials_amp'],
        session_log['tunings'][t]['fixed_freq'],
        session_log['tunings'][t]['partials_amp']
    )[0] for t in times]
    
    fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    # Remove horizontal space between axes
    fig.subplots_adjust(hspace=0)
    ax1 = axs[0]
    ax2 = axs[1]

    ax1.semilogy(et_times, et_freqs, 'x', label='12TET frequencies')
    ax1.semilogy(tuned_times, tuned_freqs, '.', label='Tuned frequencies')
    ax1.semilogy(fixed_times, fixed_freqs, '_k', label='Fixed frequencies')

    ax2.step(times, et_diss, where='post', label='12TET dissonance')
    ax2.step(times, tuned_diss, where='post', label='Tuned dissonance')
    ax2.step(times, ji_diss, where='post', label='JI dissonance')

    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)

    max_freq = max(et_freqs + tuned_freqs + fixed_freqs)
    min_freq = min(et_freqs + tuned_freqs + fixed_freqs)
    max_diss = max(et_diss + ji_diss + tuned_diss)
    min_diss = min(et_diss + ji_diss + tuned_diss)
    ax1.set_ylim(min_freq * 0.98, max_freq * 1.02)
    ax2.set_ylim(min_diss * 0.98, max_diss * 1.02)

    if max_freq / min_freq < 3:  # sonst wirds zu eng
        yticks_pitches = list(filter(lambda p: scale_et[p] >= min_freq * 0.9
                                               and scale_et[p] <= max_freq * 1.1,
                                     range(128)))

        ax1.set_yticks(scale_et[yticks_pitches])
        ax1.set_yticklabels([Scale.pitch_to_pitchname(p) for p in yticks_pitches])
        ax1.set_yticks([], 'minor')

    ax2.set_yticks([0])

    ax1.grid(True)
    ax2.grid(True)
    ax1.set_ylabel('Frequencies')
    ax1.set_title('Tuning Session')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel("Dissonance")
    fig.set_size_inches(6.4, 4.8 * 1.5, forward=True)
    if save_to_file:
        pass
        fig.savefig(session_log['name'] + '_plot.png', bbox_inches='tight')
    else:
        plt.show()



#todo
# doku
# tuning for different timbres

# aufräumen nach der session mit jiajun und thomas:
# _midi_lock sollte besser audiogenerator_lock heißen
# macht er eig mist wenn man ihn startet obwohl kein midi keyboard angeschlossen ist?

class Tuner:
    
    class LockedBool:
        def __init__(self):
            self.lock = threading.Lock()
            self.val = False
        
        def set(self, val=True):
            self.lock.acquire()
            self.val = val
            self.lock.release()
        
        def is_set(self):
            self.lock.acquire()
            if self.val:
                self.lock.release()
                return True
            else:
                self.lock.release()
                return False
        
        # if val is true, set val to False and return true, if val is false just return false
        def check_true_set_false(self):
            self.lock.acquire()
            if self.val:
                self.val = False
                self.lock.release()
                return True
            else:
                self.lock.release()
                return False
    
    def __init__(self, sc=None, tuning_interval=0.3, audio_lag=0.3, safe_session_log=False):
        # tuner will tune immediately every noteon but at least every tuning_interval seconds
        self.tuning_interval = tuning_interval
        # time between midi in and note sounding / time the tuner has to tune
        self.audio_lag = audio_lag
        self.safe_session_log = safe_session_log
        self.session_log = dict()
        
        self._stop_signal = threading.Event()
        self._stop_signal.set()
        self._stop_tuning_signal = threading.Event()
        self._stop_tuning_signal.set()
        self._tuning_requested = Tuner.LockedBool()
        self._midi_lock = threading.Lock()
        self._audio_lock = threading.Lock()
        
        self.midiprocessing = Midiprocessing(
            note_on_callback=self.midi_note_on_callback,
            note_off_callback=self.midi_note_off_callback,
            stop_callback=self.midi_stop_callbackack
        )
        self._midi_handler_threads = dict()
        
        self.audioanalyzer = Audioanalyzer(result_callback=self.audio_analyzer_callback, silent=False)
        self.fixed_freq = []
        self.fixed_amp = []
        
        self.audiogenerator = Audiogenerator(sc)
        
        self.dissonancereduction = Dissonancereduction(relative_bounds=None, method='CG')

    def test_amplitude_threshold(self):
        # play reference tone (sine 1khz) at amplitude threshold for two second, you should barely be able to her it
        # if its to loud or to quiet change the self.dissonancereduction.amplitude_threshold 
        self.audiogenerator.sc.cmd('{SinOsc.ar(1000,0,' + str(self.dissonancereduction.amplitude_threshold) + ')!2}.play')
        time.sleep(2)
        self.audiogenerator.sc.cmd('s.freeAll')
    
    def tune_loop(self):
        timer = self.tuning_interval
        while not self._stop_signal.is_set():
            timer -= 0.01
            
            if (timer <= 0 or self._tuning_requested.check_true_set_false()) \
                and (not self._stop_tuning_signal.is_set()):
                # get running synth
                pitches = []
                fundamentals_freq = []
                fundamentals_amp = []
                #partials_pos = []
                #partials_amp = []
                self._midi_lock.acquire()
                for pitch in self.audiogenerator.keys:
                    if self.audiogenerator.keys[pitch] is not None \
                            and self.audiogenerator.keys[pitch].currently_running:
                        pitches.append(pitch)
                        #fundamentals_freq.append(self.audiogenerator.keys[pitch].frequency)  ## immer vom letzten Ergebnis
                        fundamentals_freq.append(440 * 2**((pitch - 69) / 12))  ## test immer von 12tet aus tunen
                        fundamentals_amp.append(self.audiogenerator.keys[pitch].amplitude)
                        #partials_pos.append(self.audiogenerator.keys[pitch].partials_pos)
                        #partials_amp.append(self.audiogenerator.keys[pitch].partials_amp)
                
                # currently dissonancereduction.tune assumes all complex tones to have the same timbre
                partials_pos = self.audiogenerator.partials_pos
                partials_amp = self.audiogenerator.partials_amp
                    
                self._midi_lock.release()
                
                if len(pitches) == 0:
                    timer = self.tuning_interval
                    continue

                # get fixed freqs
                self._audio_lock.acquire()
                fixed_freq = self.fixed_freq
                fixed_amp = self.fixed_amp
                self._audio_lock.release()

                # tune
                tuned_fundamentals = self.dissonancereduction.tune(
                    np.array(fundamentals_freq), np.array(fundamentals_amp),
                    np.array(partials_pos), np.array(partials_amp),
                    np.array(fixed_freq), np.array(fixed_amp)
                )['x']
                
                if not self._stop_tuning_signal.is_set():
                    #print(tuned_fundamentals)

                    if self.safe_session_log:
                        self.session_log['tunings'][time.time() - self._start_time] = {
                            'pitches': pitches,
                            'fundamentals_freq': fundamentals_freq,
                            'fundamentals_amp': fundamentals_amp,
                            'partials_pos': partials_pos,
                            'partials_amp': partials_amp,
                            'fixed_freq': fixed_freq,
                            'fixed_amp': fixed_amp,
                            'tuned_fundamentals': tuned_fundamentals
                        }

                    # update running synth (if running change freq)
                    self._midi_lock.acquire()
                    for i in range(len(pitches)):
                        pitch = pitches[i]
                        frequency = tuned_fundamentals[i]
                        self.audiogenerator.note_change_freq(pitch, frequency)

                    # for synth in synths: change freq
                    self._midi_lock.release()

                # set timer to tuning interval
                timer = self.tuning_interval
            else:
                time.sleep(0.01)
    
    def midi_note_on_callback(self, pitch, amp):
        midi_handler_thread = threading.Thread(target=self.midi_note_on_handler, args=(pitch, amp))
        midi_handler_thread.start()
        self._midi_handler_threads[midi_handler_thread.ident] = midi_handler_thread
        self.del_dead_handlers()
    
    def midi_note_on_handler(self, pitch, amp):
        self._midi_lock.acquire()
        self.audiogenerator.register_note_on(pitch, amp)
        self._midi_lock.release()
        
        self._tuning_requested.set()
        
        time.sleep(self.audio_lag)
        
        self._midi_lock.acquire()
        self.audiogenerator.play_note_on(pitch)
        self._midi_lock.release()
    
    def midi_note_off_callback(self, pitch):
        midi_handler_thread = threading.Thread(target=self.midi_note_off_handler, args=(pitch,))
        midi_handler_thread.start()
        self._midi_handler_threads[midi_handler_thread.ident] = midi_handler_thread
        self.del_dead_handlers()
    
    def midi_note_off_handler(self, pitch):
        self._midi_lock.acquire()
        self.audiogenerator.register_note_off(pitch)
        self._midi_lock.release()
        
        time.sleep(self.audio_lag)
        
        self._midi_lock.acquire()
        self.audiogenerator.play_note_off(pitch)
        self._midi_lock.release()
    
    def midi_stop_callbackack(self):
        midi_handler_thread = threading.Thread(target=self.midi_stop_handler)
        midi_handler_thread.start()
        self._midi_handler_threads[midi_handler_thread.ident] = midi_handler_thread
        self.del_dead_handlers()
    
    def midi_stop_handler(self):
        self._midi_lock.acquire()
        self.audiogenerator.register_stop_all()
        self._midi_lock.release()
        
        time.sleep(self.audio_lag)
        
        self._midi_lock.acquire()
        self.audiogenerator.play_stop_all()
        self._midi_lock.release()
    
    def audio_analyzer_callback(self, peaks_freq, peaks_amp):
        self._audio_lock.acquire()
        self.fixed_freq = peaks_freq
        self.fixed_amp = peaks_amp
        self._audio_lock.release()
    
    def del_dead_handlers(self):
        for k in [k for k in self._midi_handler_threads if not self._midi_handler_threads[k].is_alive()]:
            del self._midi_handler_threads[k]
    
    def start(self, midi_file=None, fixed_audio=False):
        # set up everything, create threads
        self._tuner_thread = threading.Thread(target=self.tune_loop, args=())
        
        if midi_file is None:
            self._midi_thread = threading.Thread(
                target=lambda: self.midiprocessing.play_port(self._stop_signal)
            )
        else:
            self.midiprocessing.read_file(midi_file)
            self._midi_thread = threading.Thread(
                target=lambda: self.midiprocessing.play_file(stop_event=self._stop_signal)
            )
        
        if isinstance(fixed_audio, bool) and fixed_audio: # record
            self._audio_thread = self._audio_thread = threading.Thread(
                target=lambda: self.audioanalyzer.analyze_record(stop_event=self._stop_signal)
            )
        elif isinstance(fixed_audio, str): # play file
            self._audio_thread = threading.Thread(
                target=lambda: self.audioanalyzer.analyze_file(fixed_audio, stop_event=self._stop_signal)
            )
        else:
            self._audio_thread = None
        
        self._stop_signal.clear()
        self._stop_tuning_signal.clear()
        if self.safe_session_log:
            self.init_session_log()
            self._start_time = time.time()
        self.fixed_freq = []
        self.fixed_amp = []
        
        #start threads
        self._tuner_thread.start()
        self._midi_thread.start()
        if self._audio_thread is not None:
            self._audio_thread.start()
        
        # loop checking for inputs, if exit, exit
        inp = None
        while inp != 'exit':
            inp = input("Type 'a' for adaptive tuning, 'et' for 12TET, 'ji' for just intonation,"
                        + " or 'exit' to exit: ")
            
            if inp == 'a':
                self._stop_tuning_signal.clear()
                self._tuning_requested.set()
                
            if inp == 'et':
                self._stop_tuning_signal.set()
                self.audiogenerator.scale.reference_pitch = 'A4'
                self.audiogenerator.scale.reference_frequency = 440
                self.audiogenerator.scale.tune_all_equal_temperament()
                
            if inp == 'ji':
                self._stop_tuning_signal.set()
                self.audiogenerator.scale.reference_pitch = 'C4'
                self.audiogenerator.scale.reference_frequency = 261.63
                self.audiogenerator.scale.tune_all_by_interval_in_cents(Scale.tunings_in_cents['Natural (JI)'])
        
        self.stop()
    
    def stop(self):
        if not self._stop_signal.is_set():
            self._stop_signal.set()

            # join threads
            self._tuner_thread.join()
            self._midi_thread.join()
            if self._audio_thread is not None:
                self._audio_thread.join()
            for t in self._midi_handler_threads:
                self._midi_handler_threads[t].join()
            self.del_dead_handlers()

            self.audiogenerator.stop_all()
    
    def init_session_log(self):
        self.session_log = {
            'name': 'tuning_session_log_' + time.asctime().replace(' ', '_'),
            'tuner params': {
                # Tuner parameters
                'tuning_interval': self.tuning_interval,
                'audio_lag': self.audio_lag,
                # Dissonancereduction parameters
                'method': self.dissonancereduction.method,
                'relative_bounds': self.dissonancereduction.relative_bounds,
                'max_iterations': self.dissonancereduction.max_iterations
            },
            'tunings': dict()
        }
    
    def write_session_log_to_file(self, filename=None):
        if self.session_log != dict():
            if filename is None:
                filename = self.session_log['name']
            with open(filename + ".pkl","wb") as file:
                pickle.dump(self.session_log,file)