# Todo

- filter_harmonic_relevant_pairs: in Dissonancereduction, implement a function that filters out relevent pairs that are probably not meant to be harmonic (e.g. passing tones) or are meant to be dissonant (small intervals like b2) and don't consider them during tuning. -> Results in more stable tuning less disturbed by things like passing tones hopefully?

  - eg if |f1-f2|/cbw > 0.25 the corresponding partials will repel each other -> two complex tones tones are nonharmonic if all partials repell? Or if some (weighted?) average is > 0.25?

  - Simplified version: try to merge all relevant harmonic pairs of partials, ignore anything else (like actual dissonance values), could be done using an efficient Stange-style algorithm maybe?


- offline version of everything:

  - calculate the tuning of a given set of notes

  - calculate something like a microtonal score that can be played later

  - record audio


- other output possibilities that are more stable than OSC?

  - ways to produce sound in Python directly?

  - communicate with a max for life instrument


- Produce sound examples