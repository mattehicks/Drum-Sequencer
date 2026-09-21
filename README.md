# D20 Synth Tools

Central codebase for D20 drum/percussion synthesis experiments. Standalone from the
D20 firmware itself (ESP32 is already loaded with platform + drumset-loading duties) --
this is where synthesis algorithms and tooling get prototyped and learned before any
hardware integration decision is made.

## base1

First snapshot, tagged `base1`. Contents:

- `browser/index.html` -- D20 Synth Workbench: a single-file Web Audio API tool with
  nine drum/percussion voices (kick, snare, hi-hat, cymbal, clap, cowbell, tom,
  Karplus-Strong pluck via AudioWorklet, chaos-map percussion), each with live
  parameter controls and an inline "Theory" panel explaining the algorithm and math.
  Includes an oscilloscope, a log-frequency spectrum analyzer, and a scrolling
  spectrogram, all reading off the master bus. Open the file directly in a browser
  (Chrome/Edge recommended for full AudioWorklet support) -- no build step, no
  dependencies, no server required.

## Architecture

Every voice follows the same three-stage structure used in analog drum synthesis:
a **source** (oscillator, noise, or chaos generator), a **shaping stage** (filter
and/or envelope), and a **mixer bus**. What separates a kick from a cymbal is the
source and filter, not the structure.

Techniques covered so far: exponential pitch-swept oscillators (kick/tom), detuned
oscillator + bandpass noise (snare), inharmonic square-oscillator banks (hi-hat/
cowbell -- the classic 808/909 technique), modal synthesis via parallel resonant
bandpass filters (cymbal), noise-burst trains + synthetic convolution reverb (clap),
Karplus-Strong digital waveguide synthesis (KS Pluck, real sample-level DSP in an
AudioWorklet), and a logistic-map chaotic noise source (Chaos Perc).

## Roadmap / porting notes

- Next baselines (base2, base3, ...) will likely add: a step sequencer, velocity-to-
  parameter mapping, and a Python/numpy mirror for filter-response and spectral
  analysis work that's easier with scipy than in-browser.
- If/when a companion synthesis chip is chosen for D20, the Web Audio node graphs here
  map fairly directly onto a Teensy Audio Library patch (if Teensy 4.x), or could be
  ported via Faust (write DSP once, generate C++ for both a PC test harness and the
  embedded target) regardless of chip. The Karplus-Strong voice is already written as
  raw sample-level DSP for exactly this reason -- it's close to a direct C port.
- D20's current trigger/velocity input format hasn't been cross-checked against this
  tool's parameter set yet.

## Status

base1 committed. Not yet wired into the D20 firmware.

## Workflow

Starting this session: every iteration (prompt/response) that changes a file in this
repo gets an automatic local commit, so history stays granular without asking each
time. Edits are written straight to this file on disk (no intermediate "delivered
file" step) -- you'll see the git commit, not a repeated file card. This only
commits locally -- nothing is pushed to GitHub automatically. Push manually via
GitHub Desktop or `gh repo create/push` (see top of this file) whenever you want a
snapshot public/backed up.
