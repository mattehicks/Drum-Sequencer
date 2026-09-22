# D20 Instrument Library

Kit files for the D20 Synth Workbench (V2/index.html).

## How to load
- **Import Instruments** button -> pick a kit file. Replaces the instrument rack only; sequencer, patterns, and rows are untouched.
- **Load Project** also accepts these files, but Import Instruments is the intended path for swapping sounds mid-session.

## Kits
| File | Kit | Character |
|---|---|---|
| kit-808-classic.json | 808 Classic | Long sine kick (80->45 Hz, 0.7 s), snappy snare, 587 Hz/1.48 cowbell, open-hat + hi/lo tom clones |
| kit-909-punch.json | 909 Punch | Clicky driven kick (click 0.5, drive 0.35), 4-burst clap, bright 8 kHz hats |
| kit-trap-modern.json | Trap Modern | Full-length sub kick to 28 Hz, 30 ms hats for rolls, KS as 82 Hz bass pluck |
| kit-acoustic-room.json | Acoustic Room | Short kick with beater click, buzzy 2.4 kHz snare noise, three toms, 3 s dark crash |
| kit-industrial.json | Industrial | Drive 0.9 kick, detuned 160/210 Hz beating snare, chaos map at r=4.0 |
| kit-dub-lofi.json | Dub Lo-fi | 70->41 Hz kick, dark 1.2 kHz snare noise, 3.2 s low wash, 65 Hz KS bass |
| kit-latin-perc.json | Latin Percussion | Surdo, timbale, shaker hat, hi/lo campana clones, conga toms |
| kit-minimal-glitch.json | Minimal Glitch | Everything <=120 ms: thump, rim, tick hat, 1 kHz ping, 500 Hz blip |

## File format
```json
{ "format": "d20-synth-project", "version": 1, "name": "...", "voices": [ ... ] }
```
Each voice: `id`, `name`, `key`, `isClone`, `clonedFrom`, `params`. Stock ids (kick, snare, hihat, cymbal, clap, cowbell, tom, ks, chaos, click1, click2) must all be present -- the importer rebuilds the whole rack from the file, so a partial file drops the missing voices. Clones may use any unique id and reference a stock `clonedFrom`; they inherit that voice's trigger and param schema.

All param values are within the slider ranges defined in index.html (validated at generation time by build_win.py in this folder's parent).

## Extending the library
Copy any kit file, rename it, edit `params`. Ranges per voice are in the VOICES array in index.html (VOICES definition). Or edit build_win.py (one level up) and re-run it -- it validates every param against the engine's ranges before writing.
