# The sounds and the bar of music made in code: the evidence

*Why each sound of the kit (`standard/MUSIC.md`, section 5) won, how it was checked, what was tried and not kept, and what the example
film measured. The method's own numbers, measured with its tools on Windows 11 (a laptop CPU) in November 2026. Read with
`standard/MUSIC.md`; where they differ, the standard wins.*

## How the sounds were chosen

Role patches were bulk-measured alone (`music.py audition`, 1,615 patches, ~8 minutes in 8 processes), then each part was picked
**in context** (`music.py pick`): every candidate playing its real part of a real 25-s bed at the part's fixed level with the other
parts, through the bus, scored by the stand-in ear (value = PQ + CE + CU less spectrum penalties). Two picking runs (run A: a 25-s
excerpt with pulse, drive, pad and sub; run B: another with pad, pulse, sub and drone), then a re-pick of the pulse inside the
voice-band bar. Later re-measurements with the same tools matched the logs (centroids within 15 Hz, band shares within 0.2 points).

## The kit: file checks

Every sound is a patch from the library every Surge XT 1.3.4 install ships (`SurgeXTData/patches_factory/` or `patches_3rdparty/`);
the MD5 confirms the same file.

| Layer | Library path | MD5 | Bytes |
|---|---|---|---|
| pad | `patches_3rdparty/Kyurumi/Pads/Neverending.fxp` | `8b330c226dacc0ad641dd9f746d6a4cd` | 63,356 |
| pulse | `patches_factory/Plucks/Diamonds.fxp` | `cd3199eefd82d78dea57e10e9d5a2fcc` | 26,519 |
| pulse2 | `patches_3rdparty/John Valentine/Sequences/Crockett's Seq Filter Bass.fxp` | `a7119de7dd276c9d9bca7abd3365d845` | 40,297 |
| sub | `patches_3rdparty/Vospi/Basses/Floored.fxp` | `f6fbc61958667b79498500ea0fdcddf1` | 32,627 |
| subB | `patches_3rdparty/Vospi/Basses/I Can Kinda Be Chordish.fxp` | `958d6aa2e023774419cf5262ce15af44` | 27,162 |
| drive | `patches_factory/Basses/FM Bass 1.fxp` | `970be575d36cc34e06b21f46838892ea` | 35,333 |
| drone | `patches_3rdparty/Xenofish/Pads/Fireflies.fxp` | `7d922ce41a2995e37bc2f317be663cce` | 27,532 |
| hit | `patches_3rdparty/A.Liv/Basses/Bonsai 808.fxp` | `45ffda00857c3b94bf21942084b21383` | 214,711 |

## Why each won

| Layer | Why |
|---|---|
| pad: Neverending | Won **both** in-context runs: run A value 22.97 (PQ 7.88, CE 7.18, CU 7.91; bed voice band 0.26%) over Pads/Bright 22.78 and Pads/Pad 2 MW 22.77 (28 pads tried); run B 21.65 over Pads/Bright 21.53 (Bright put the bed at 1.37% in the voice band). Alone: centroid 352-367 Hz, pitch clarity 0.57, stereo width 0.67 |
| pulse: Diamonds, an octave down | Run B's winner Slowboat/Plucks/Little Pluck (23.75) and Diamonds as written (23.54) both put the bed over the 1.2% voice-band bar (1.39%, 1.29%); Diamonds `@-12` scored 23.39 (PQ 7.97, CE 7.53, CU 7.89) at 0.21%: the best inside the bar. Alone: pitch clarity 0.69, 99.0% under 1 kHz, 0.18-0.19% in 1-4 kHz. In tune at the written note (the -12 is a register choice) |
| pulse2: Crockett's Seq Filter Bass | Won run A's pulse round, 22.215 (PQ 7.66, CE 6.86, CU 7.79) over Kinsey Dulcet/Plucks/No Frills Harp Pluck 22.08 (28 tried). Alone: centroid 358-365 Hz, 99.9% under 1 kHz, 0.12-0.13% in 1-4 kHz. A sequencer patch: its own step pattern moves between octaves |
| sub: Floored | Won run A's sub round, 23.41 (PQ 8.06, CE 7.36, CU 7.99) over Emu/Basses/Soft Plucks 23.22 (16 tried). Alone: 97.3% of its energy under 80 Hz, no added tones. It sounds an octave under the written note (written A3: all its energy at 110 Hz, a near-pure sine), hence +12 |
| subB: I Can Kinda Be Chordish | Won run B's sub round, 23.62 (PQ 8.15, CE 7.45, CU 8.02) over Giana Brotherz/Basses/Deep Jungler 23.60 and A.Liv/Basses/Dynamo Square 23.59 (16 tried). 99.4% under 80 Hz; exactly an octave under the written note, no added tones |
| drive: FM Bass 1 | Won run A's drive round, 22.63 (PQ 7.69, CE 7.12, CU 7.82) over Basses/Square Bass 22.59 and Luna/Basses/Chonky Analog Bass 1 22.57 (19 tried). Centroid 73 Hz, 66% under 80 Hz. It carries a strong sub-octave: written A2, the written pitch strongest and the octave below 5 dB under it; written A3, the octave below strongest. The beds write its roots within a fifth of D2 (MIDI 32-43), untransposed |
| drone: Fireflies | Run B's drone round was a tie (Vincent Zauhar/Winds/Another Flute 23.73, Pads/Sawteeth 23.73, Fireflies 23.72); Fireflies kept because a pad holds a minute naturally. 100% under 1 kHz, 0.0% in 1-4 kHz, a slow swell (attack 4.4-6.6 s); in tune |
| hit: Bonsai 808 | Chosen for a reason first: it **follows the note** (an octave under the written one on every note tried, no added tones, 100% under 1 kHz), where the timpani patches play one fixed pitch out of the key. In context (8 hits within 0.53-0.61 of each other over two runs) the taiko scored first both times, but it sounds two octaves under (~27 Hz for a written A2: below what phone and laptop speakers play). The stand-in ear barely hears what one hit changes; the 808 stays for following the note |

**Tried and not kept:** Pads/Bright and Pads/Pad 2 MW (pad; Bright brighter in the voice band); Slowboat/Plucks/Little Pluck (pulse:
the highest value, but 1.39% in the voice band); Kinsey Dulcet/Plucks/No Frills Harp Pluck (pulse); Basses/Square Bass, Luna/Basses/
Chonky Analog Bass 1 (drive); Emu/Basses/Soft Plucks, Basses/FM Bass 5, Basses/Sub 3 (sub); Giana Brotherz/Basses/Deep Jungler,
A.Liv/Basses/Dynamo Square (subB); Vincent Zauhar/Winds/Another Flute, Pads/Sawteeth (drone, tied). A bass with a tritone and a major
third in every note was refused at the added-tone check; a timpani was replaced by the 808.

## The bar's source

Five licensed stock-library background beds that passed a listening test under a narration (99-129 bpm, minor and major keys) gave
the reference numbers (`standard/MUSIC.md`, section 7). Two centroid definitions are in use: the reference range (417-764 Hz) is the
median **frame** centroid; the pick penalty and the band numbers use the **power-weighted** centroid of the whole bed, which reads much
lower on the same audio (written beds ~140-350 Hz), so the centroid penalty past 760 Hz rarely fires; the voice-band penalty is the
one that bites.

## The example film, as first measured

The method's own run of its example (before this repository's two changes: beds that end exactly where the next begins, and no bed
hits on narration words): every anchor 0.0 ms off, every hit 0.0 ms off, for both voices; every bed at the bar.

| Voice | Bed | Segment tempos (bpm) | Joints | PQ / CE / CU | % < 1 kHz | % 1-4 kHz |
|---|---|---|---|---|---|---|
| 1 | O (A minor) | 94.0, 87.8, 92.1 | 6.6%, 4.9% | 7.99 / 7.54 / 7.99 | 99.66 | 0.31 |
| 1 | G (D minor) | 98.8, 98.7 | 0.1% | 7.84 / 7.24 / 7.90 | 99.85 | 0.15 |
| 1 | S (G minor) | 105.5, 105.4 | 0.1% | 7.68 / 7.49 / 7.89 | 99.88 | 0.11 |
| 1 | E (A minor, home) | 92.9, 92.9 | 0.1% | 8.10 / 7.71 / 7.96 | 99.67 | 0.31 |
| 2 (12% slower) | O | 99.8, 103.0, 98.0 | 3.2%, 4.8% | 7.98 / 7.51 / 7.94 | 99.71 | 0.25 |
| 2 | G | 98.5, 100.5 | 2.1% | 7.89 / 7.35 / 7.93 | 99.86 | 0.14 |
| 2 | S | 106.1, 104.6 | 1.4% | 7.64 / 7.51 / 7.88 | 99.88 | 0.11 |
| 2 | E | 98.3, 96.7 | 1.7% | 8.09 / 7.68 / 7.96 | 99.65 | 0.33 |

Under a stand-in voice at 22 dB under: voice minus music during speech 24.5-26.4 dB per bed; the level step at bed changes -0.3 to
-1.9 dB (the next bed enters lighter, its pad fading in from -4 dB); -14.0 LUFS, peak -1.2 dBFS; mono-safe. Bed O read 2.84 onsets a
second and a 2.9-dB 8-s range, calmer than the reference beds (4.1-6.5, 4-12 dB). A full render with the judge took 225 s (voice 1)
and 294 s (voice 2), each including Surge's first start.

## Changes this repository made to the method

- **Beds never overlap:** each bed ends exactly at the next bed's first downbeat (the method let the open ring 1.6 s into the first
  chapter, and every bed 0.3 s into the next), so the house rule "never two beds at once" holds; `selftest` and `code_beds` refuse an
  overlap.
- **No bed hits on narration words:** the statement drop is the house bass drop in the cue sheet (one sound per moment); the bed
  keeps the room for it. The close's hit on the last word's end stays.
- **A part's level is measured where its notes sound,** never over the silence between them (the method's measure over the first to
  the last note let two hits 20 s apart play ~5 dB louder than one).
- **Every note ends inside its render** (a note left on rang into the next patch), and a note that began before a bed's start keeps
  only its part after it.
- **`pick` lets the bar decide first** (a candidate over the voice band loses to every one inside it), as the method's notes said.
- **One mixer:** the beds go under the voice through `tools/sound/score.py` (`code_beds`), not a second mixer; the method's numbers
  (22 dB under, a 6-dB duck, a 4-dB carve at 900-4500 Hz, -14 LUFS) are the house mix's own.
- **A Short's bed can loop** (`Bed(loop=True)`: its tail laid over its start).

## The example film, as this repository renders it

Rendered on Windows 11 (a desktop CPU, two threads for the judge) with this repository's code, after the changes above: every anchor
0.0 ms off and every event 0.0 ms off, for both voices; **every bed at the bar**; about 2 minutes a voice with the judge.

| Voice | Bed | Segment tempos (bpm) | Joints | PQ / CE / CU | worst PQ window | % < 1 kHz | % 1-4 kHz | onsets/s | 8-s range (dB) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | O (A minor) | 94.0, 87.8, 92.1 | 6.6%, 4.9% | 8.02 / 7.59 / 7.99 | 7.96 | 99.53 | 0.43 | 2.85 | 3.7 |
| 1 | G (D minor) | 98.8, 98.7 | 0.1% | 7.80 / 7.25 / 7.88 | 7.75 | 99.85 | 0.14 | 4.19 | 3.2 |
| 1 | S (G minor) | 105.5, 105.4 | 0.1% | 7.72 / 7.54 / 7.89 | 7.55 | 99.80 | 0.19 | 3.62 | 6.9 |
| 1 | E (A minor, home) | 92.9, 92.9 | 0.1% | 8.07 / 7.67 / 7.97 | 7.98 | 99.65 | 0.33 | 1.43 | 25.1 (the ring-out) |
| 2 | O | 99.8, 103.0, 98.0 | 3.2%, 4.8% | 8.00 / 7.56 / 7.97 | 7.95 | 99.57 | 0.38 | 2.95 | 5.9 |
| 2 | G | 98.5, 100.5 | 2.1% | 7.91 / 7.41 / 7.91 | 7.83 | 99.87 | 0.13 | 4.31 | 7.1 |
| 2 | S | 106.1, 104.6 | 1.4% | 7.70 / 7.51 / 7.88 | 7.62 | 99.79 | 0.20 | 3.81 | 11.0 |
| 2 | E | 98.3, 96.7 | 1.7% | 8.09 / 7.69 / 7.96 | 7.99 | 99.65 | 0.33 | 1.41 | 10.4 |

Voice 1's beds through the cue sheet (`code_beds`) and `score.py` under a stand-in voice, at the template's mix settings: voice minus
music during speech 21.5-22.5 dB per bed; the level at each switch -0.0, +0.5, +0.4 dB; no overlap, no silence outside the designed
ones, mono-safe, -14.0 LUFS. Two faults the first test runs found, both fixed in the example and the standard: a 0.55-s silence after
the room for a drop (the pad dipped to -30 dB took its own reverb tail with it: now `until()` stops the notes and lets the tail ring,
and the drone swells in from the word), and bed S under the bar on one render (PQ 7.57; a second render of the same notes measured
7.67): rebalanced from its stems, pad +2 and sub -1, its worst window 7.43 -> 7.63.
