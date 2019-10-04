import mido
import time

class Midiprocessing():
    """Midiprocessing class. Reads from midi file or midi port and hands messages to given callback funcions.
    
    Attributes
    ----------
    note_on_callback : function
        Function that gets called when receiving a note-on message.
        If None is given, note_on_callback = lambda pitch, amp: None
        (Default value = None)
    note_off_callback : function
        Function that gets called when receiving a note-off message.
        If None is given, note_off_callback = lambda pitch: None
        (Default value = None)
    stop_callback : function
        Function that gets called when stopping the midiprocessing.
        If None is given, stop_callback = lambda: None
        (Default value = None)
    max_notes : int
        If max_notes is not None, a maximum of max_notes note-on messages will be received before stopping the processing.
        This is meant for easy testing in a single thread when we don't want to block the thread infinitely.
        (Default value = None)
    port_name : str
        Name of the midiport as given by get_port_names. (Default value = None)
    file : mido.midifiles.midifiles.MidiFile
        mido Midi file.
    """
    
    def __init__(self, note_on_callback=None, note_off_callback=None, stop_callback=None, max_notes=None,
                 audiogenerator=None, port_name=None):
        """__init__ method
        
        Parameters
        ----------
        note_on_callback : function
            Function that gets called when receiving a note-on message.
            If None is given, note_on_callback = lambda pitch, amp: None
            (Default value = None)
        note_off_callback : function
            Function that gets called when receiving a note-off message.
            If None is given, note_off_callback = lambda pitch: None
            (Default value = None)
        stop_callback : function
            Function that gets called when stopping the midiprocessing.
            If None is given, stop_callback = lambda: None
            (Default value = None)
        max_notes : int
            If max_notes is not None, a maximum of max_notes note-on messages will be received before stopping the processing.
            This is meant for easy testing in a single thread when we don't want to block the thread infinitely.
            (Default value = None)
        audiogenerator : adaptivetuning.Audiogenerator
            If audiogenerator is not None, the callback functions are connected to the corresponding methods of the 
            audiogenerator: note_on, note_off, stop_all (Default value = None)
        """
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
        """ Connect the callback functions of midiprocessing to the corresponding methods of the audiogenerator.
        Namely: note_on, note_off, stop_all
        
        Parameters
        ----------
        audiogenerator : adaptivetuning.Audiogenerator
            The audiogenerator to connect to midiprocessing.
        """
        self.note_on_callback = audiogenerator.note_on
        self.note_off_callback = audiogenerator.note_off
        self.stop_callback = audiogenerator.stop_all
    
    def read_file(self, file_name):
        """Reads a midi file and stores it as a mido file ready to play with play_file.

        Parameters
        ----------
        file_name : str
            Path to the midi file.
        """
        self.file = mido.MidiFile(file_name)
    
    def play_file(self, file_name=None, stop_event=None):
        """Plays a midi file.

        Parameters
        ----------
        file_name : str
            If None, play the midi file stored in self.file. Else read_file(file_name) and then play.
        stop_event : threading.Event
            When stop_event.is_set(), the midiprocessing will stop.
        """
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
        self.stop_callback()
        
    def play_port(self, stop_event=None):
        """Plays messages from a midi port.
        If port_name is None, tries to search for one with get_port_names and takes the first one.

        Parameters
        ----------
        stop_event : threading.Event
            When stop_event.is_set(), the midiprocessing will stop.
        """
        
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
        # I think it only happens using jupyter notebook
        # In the end that was not the problem, it is some known mac driver problem
        # there is a really strange workaround: Running the app Mini Monitor in the
        # background prevents the error.
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
                self.stop_callback()

    def handle_message(self, msg):
        """Takes a midi message and calls the corresponding callback.
        
        Parameters
        ----------
        msg : mido.messages.messages.Message
            mido message.
        """
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
        """Stop midiprocessing."""
        self._stop_flag = True
    
    def get_port_names(self):
        """Get names of available midi ports.
        
        Returns
        -------
        list of str
            A list of midi port names
        """
        return mido.get_input_names()
    