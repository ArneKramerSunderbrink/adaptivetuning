import mido
import time

#todo doku
class Midiprocessing():
    """Midiprocessing class. Reads from midi file or midi port.
    """
    
    def __init__(self, note_on_callback=None, note_off_callback=None, stop_callback=None, max_notes=None,
                 audiogenerator=None, port_name=None):
        if audiogenerator is not None:
            self.register_audiogenerator(audiogenerator)
        else:
            if note_on_callback is None:
                note_on_callback = lambda pitch, amp: None
            if note_off_callback is None:
                note_off_callback = lambda pitch: None
            if stop_callback is None:
                stop_callback = lambda: None
            self.note_on_callback = note_on_callback
            self.note_off_callback = note_off_callback
            self.stop_callback = stop_callback
        
        self.port_name = port_name
        self.max_notes = max_notes  # to not infinitely block when used in a single thread environment
        self._stop_flag = True  # internal stop flag to signal when max notes is reached
    
    def register_audiogenerator(self, audiogenerator):
        self.note_on_callback = audiogenerator.note_on
        self.note_off_callback = audiogenerator.note_off
        self.stop_callback = audiogenerator.stop_all
    
    def read_file(self, file_name):
        self.file = mido.MidiFile(file_name)
    
    def play_file(self, file_name=None, stop_event=None):
        if file_name is not None:
            self.read_file(file_name)
        
        if self.file is None:
            print("Read file first...")
            return
        
        self.nr_notes_played = 0
        self._stop_flag = False
        
        for msg in self.file:
            # we have to wait at most 0.1 s until stop_event is checked,
            # even if there are big gaps between messages in the midi file
            t = msg.time
            while t > 0.1:
                if self._stop_flag or (stop_event is not None and stop_event.is_set()): break
                t -= 0.1
                time.sleep(0.1)
            if self._stop_flag or (stop_event is not None and stop_event.is_set()): break
            time.sleep(t)
            
            self.handle_message(msg)
        
        self.stop()
        
    def play_port(self, stop_event=None):
        if self.port_name is None:
            port_names = self.get_port_names()
            if len(port_names) > 0:
                self.port_name = port_names[0]
            else:
                print("Couldn't find a midi input...")
                return
        
        self.nr_notes_played = 0
        self._stop_flag = False
        
        # I often got Error
        # MidiInCore::initialize: error creating OS-X MIDI client object (-50).
        # on the second execution, maybe it was because the automatic cleanup after
        # of the with-expression: with mido.open_input('MPK mini') as midi_in:...
        # somehow didn't work so I'm doing that manually now...
        in_port = None
        try:
            in_port = mido.open_input(self.port_name)
            while not self._stop_flag and (stop_event is None or not stop_event.is_set()):
                for msg in in_port.iter_pending():  # non-blocking
                    self.handle_message(msg)
        finally:
            if in_port is not None:
                in_port.close()
                self.stop()

    def handle_message(self, msg):
        if msg.type == 'note_on':
            if self.max_notes is not None:
                self.nr_notes_played += 1
                if self.nr_notes_played > self.max_notes:
                    self.stop()
                    return
            self.note_on_callback(msg.note, float(msg.velocity) / 127)
        elif msg.type == 'note_off':
            self.note_off_callback(msg.note)
            
    def stop(self):
        self._stop_flag = True
        self.stop_callback()
    
    def get_port_names(self):
        return mido.get_input_names()
    