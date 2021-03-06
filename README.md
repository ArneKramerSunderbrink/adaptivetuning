# adaptivetuning

## What is adaptivetuning?
adaptivetuning is a python package that offers methods to experiment with adaptive tuning guided by dissonance reduction.

An object of the Tuner class takes a precomposed piece of music in form of a midi file or a live performance in form of a midi stream on the one hand, and some recording of environmental noise in form of an audio file or an audio stream on the other hand, analyses the environmental noise for pronounced frequencies and plays back the midi data at frequencies that, while staying true to the original musical material, are fine tuned to minimize the inner-musical dissonance as well as the dissonance between the music and the pronounced frequencies in the environmental noise.

This system (version 1.0) was part of the bachelor thesis I did in 2019. You can find it in the thesis folder. Have a look if you are interessted in the theoretical motivation behind the tuning algorithm, in particular the beating theory of dissonance.

Beyond this very specific application there are methods that will be usefull when experimenting with nonstandard tuning in general. In particular we have
* A Scale class that provides many methods to conveniently define different kinds of scales.
* A simple microtonal polyphnoc additive synthesizer: The Audiogenerator class. It tunes its tone according to a Scale object.
* A Midiprocessing class to control the Audiogenerator with a midi keyboard or play midi files.
* A Dissonancereduction class provides methods to compare the dissonance of different chords according to the beating theory of dissonance. And an optimization algorithm that can finetune a given set of complex tones to reduce its dissonance.


## Instalation
Clone the master branch and from inside the adaptivetuning directory install via 
```bash
pip install -e .
```

## Usage
An introduction on how to use adaptivetuning is available in the examples folder. You will find a ipython notebook with a short introduction to every class of the library.

## Supershort examples to get you hyped:


### Scale
The Bohlen-Pierce scale - A stretched scale (octave = 3) with 13 pitches per octave:

    intervals = [1, 27/25, 25/21, 9/7, 7/5, 75/49, 5/3, 9/5, 49/25, 15/7, 7/3, 63/25, 25/9]
    s = Scale(reference_pitch='C4', reference_frequency=260,
                  pitches_per_octave=13, octave_interval=3)
    s.tune_all_by_interval(intervals)
    s[60]  # yields 260 Hz
    s[73]  # one 'octave' higher, yields 780 Hz

### Audiogenerator
Let's make a pad-style synth with stretched overtones and stretch the scale accordingly:

    import sc3nb
    sc = sc3nb.startup()
    a = Audiogenerator(sc=sc)
    a.attack_time = 1
    a.decay_time = 1
    a.sustain_level = 0.9
    a.release_time = 2
    a.partials_pos = {'method': 'harmonic', 'nr_partials': 6, 'octave': 2.5}
    a.partials_amp = [0.6**i for i in range(6)]
    a.scale.octave_interval = 2.5
    a.scale.tune_all_equal_temperament()  # 12TET with streched octave
    a.note_on('C4', 1)
    a.note_on('E4', 1)
    a.note_on('G4', 1)
    a.note_off('C4')
    a.note_off('E4')
    a.note_off('G4')

### Midiprocessing
Let's hear the first two bars of Bach's 'Jesu meine Freude' with a stretched timbre and a stretched scale!

    m = Midiprocessing()
    m.register_audiogenerator(a)
    m.max_notes = 30
    m.read_file("midi_files/BWV_0227.mid")
    m.play_file()

## Troubleshooting

On a Mac, you might get the following problems with the sc3nb library:

### sc3nb is not able to find the sclang executable

I.e.

    sc = sc3nb.startup()

returns
    
    FileNotFoundError: Unable to find sclang executable

Solution: You can add your sclang path as an argument:

    sc = sc3nb.startup(sclangpath="/Applications/SuperCollider/SuperCollider.app/Contents/MacOS/")

Or add ```/Applications/SuperCollider/SuperCollider.app/Contents/MacOS/```
to you ```$PATH``` system-variable.

### sc3nb throws timeout when booting the SC-server

If you just try again, it usually starts successfully on the second or third try. Most of the time I just wrote my self a small loop to do that for me:

    while True:
        try:
            sc = sc3nb.startup()  # sometimes throws timeout
            break
        except TimeoutError as e:
            print(e)
            print("retry...")
    print("Startup successful")

This creates a new SC-server on every try though, only the one that is opened last is needed, the others can be closed manually. 