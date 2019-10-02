from adaptivetuning import Midiprocessing

def test_playfile():
    #Play the first four notes of BWV 227
    midiprocessing = Midiprocessing(max_notes=4)
    note_ons = []
    note_offs = []
    stopped = []
    midiprocessing.note_on_callback = lambda pitch, amp: note_ons.append((pitch, amp))
    midiprocessing.note_off_callback = lambda pitch: note_offs.append(pitch)
    midiprocessing.stop_callback = lambda: stopped.append(True)
    midiprocessing.read_file("midi_files/BWV_0227.mid")
    midiprocessing.play_file()
    assert note_offs == [71, 67, 64, 52]
    assert note_ons == [(71, 0.7874015748031497), (67, 0.7874015748031497), 
                        (64, 0.7874015748031497), (52, 0.7874015748031497)]
    assert stopped[0]