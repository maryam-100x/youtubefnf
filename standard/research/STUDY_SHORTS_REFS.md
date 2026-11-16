# Study: top reference Shorts, measured

*Nine top Shorts, each picked as the reference for one quality (sound effects, zooms, motion, music timing, assets), measured with
`EDIT tools/qa/measure_edit.py <video> <out dir>` (PySceneDetect ContentDetector, threshold 27) and a study pass for camera motion,
speech, stems and sound events (method below). Dense 4-fps sheets were read by eye. Then ten more top Shorts were measured the same
way. The Shorts are not named here: each is described by its kind and what it was studied for. All numbers are measured by us.*

## The numbers
| Short (kind) | Studied for | Views | Length | Cuts a minute | Median shot | Shots < 1 s | Holds >= 4 s | Loudness (momentary median) |
|---|---|---|---|---|---|---|---|---|
| A: a speed test, narrated | sound effects and zooms (the top one for both) | ~5M | 28 s | 26 | 1.27 s | 23% | 1 (the timer run, 10.5 s) | -15.6 |
| B: an animal story, narrated | sound-effect use | ~12M | 18 s | 37 | 1.45 s | 17% | 0 | -21.2 |
| C: a recorded phone call, edited | animations, effects and music timing | | 52 s | 49 | 0.87 s | 53% | 1 | -6.6 |
| D: a recap of a long live broadcast | overall quality | | 51 s | 55 | 0.67 s | 67% | 1 | -8.9 |
| E: a "what if it were made in an earlier era" remake, music-led | music timing | ~4M | 24 s | 34 | 1.97 s | 27% | 0 | -14.6 |
| F: a news story told with articles, posts and designed assets | images and assets combined with animations and effects (articles, posts; a clean, designed look) | ~2M | 47 s | 26 | 1.53 s | 24% | 3 | -8.5 |
| G: a backstory explainer | motion (smooth panning, zooming, cutting, animations: the top one for motion) | ~13M | 32 s | 43 | 1.40 s | 25% | 0 | -14.6 |
| H: a historical-figure explainer | motion, animations, transitions | | 46 s | 26 | 1.33 s | 38% | 5 | -27.3 |
| I: a narrated reaction story | studied in the same batch as A | | 80 s | 31 | 1.48 s | 21% | 4 | -15.9 |

Hard cuts only; their zooms and pop-ins add picture changes the cut count doesn't see. Loudness varies wildly (-6.6 to -27.3): there
is no standard among them, and a voice chain mastered to -14 LUFS (`standard/SOUND_AND_VOICE.md`) sits inside the spread.

## What the frames show
**A (the reference for sound effects and zooms), read at 4 fps:**
- Frame 0 is a motion-blur whip into the first shot, the first caption word already on screen.
- Captions: one word at a time, big, bold yellow with a dark outline, dead centre, changing on every word.
- **Instant punch-ins on the word:** on "acceleration" the frame jumps to the speedometer (no ease), back out on the next phrase.
- **Pop-ins for a beat (0.5-1 s):** the subject's own list card, a Google search bar ("Google says that it..."), a spec card with the
  real numbers; each slides or snaps in, then away.
- **The measurement as the picture:** a live overlay timer (0-100: 03.31) runs with the speedometer; the number turns red when it hits.
- Blur-whip transitions between sections (0:11.75, 0:17.0).
- The camera never stops: every shot is moving.

**F (the reference for images and assets with animations), read at 4 fps:**
- Split screen: the picture on top, a talking head below. For a faceless channel the top half is the whole frame.
- The ideas as designed pictures: the subject's official poster with an arrow sliding to the point, a news outlet's headline with "nightmare"
  highlighted, a black "?" silhouette for "nobody knows who", a reward poster with a big number, the person's real photo with a name
  tag, the news clip of the event, a reaction meme. Each holds 1-3 s and changes on the word.

## The study pass's numbers (camera, speech, stems)
The method: cuts from two detectors merged, plus optical-flow camera motion (the share of frames where the camera moves); faster-whisper
word times (words a minute, the first word's time, gaps over 0.3 s); demucs to split the voice from the rest, then onsets in the rest
and the music's beat grid, each cut tested against both with a 150-ms window and against chance (the same cut count placed at random).

| Short | Cuts/min (both detectors) | Camera moving | wpm | First word | Gaps > 0.3 s | Voice over the rest | Cuts with a sound event within 150 ms (chance) | Cuts on the beat (chance) |
|---|---|---|---|---|---|---|---|---|
| A | 23.9 | 57% | 215 | 0.0 s | 0 | -0.2 LU (bed as loud as the voice) | 45% (31%) | 36% (21%) |
| B | 37.1 | 45% | 247 | 0.0 s | 0 | +11.2 LU | 36% (22%) | 9% (15%) |
| C | 38.2 | 61% | 225 | 0.0 s | 13 (the call's own pauses) | +6.0 LU | 36% (20%) | 30% (31%) |
| F | 28.3 | 17% (stills and assets) | 182 | 0.0 s | 7 | +20.0 LU | 55% (36%) | 59% (33%) |
| G | 45.1 | **84%** | 232 | 0.0 s | 0 | +10.6 LU | 38% (42%) | 46% (34%) |
| H | 32.5 | 68% | 205 | 0.92 s (a clip first) | 9 | +11.1 LU | 12% (18%) | 20% (29%) |
| E | 56.6 | 38% | music-led | 0.0 s | 5 | music-led | 13% (10%) | 26% (33%) |
| I | 30.8 | 71% | 210 | 0.0 s | 6 | +12.1 LU | 37% (36%) | 27% (17%) |
| D | 52.8 | 76% | recap of a broadcast | 0.0 s | 12 | +3.4 LU | 27% (32%) | 7% (15%) |

**What it says:**
- **The voice starts on frame 0 in 8 of 9** (the ninth opens on a clip whose own sound is the hook). Narrated ones run **205-247 wpm**
  with no gap over 0.3 s in three of them (A, B, G): talking constantly is measured, not taste.
- **The camera is moving in most frames** (median 61%; G, the reference for motion, 84%). F's 17% is the exception that proves the
  rule: its stills are designed assets that pop and slide, so the motion is in the graphics, not the camera.
- **The voice sits 10-12 LU over the rest in the narrated ones** (B, G, H, I); F 20 LU; A is the outlier with the bed as loud as the
  voice.
- **Sound on cuts:** in the two studied for effects and assets (A, F) a cut carries a sound event well above chance (45% vs 31%, 55%
  vs 36%); in the others it's at chance. So sounds follow visible events (a pop-in, a punch-in, a hero word), and a plain cut doesn't
  need one (an earlier batch of news Shorts showed the same).
- The study pass's "events a minute" (20-94) counts every onset in the non-voice stem, music hits included, so it is not an effects
  count. The effects count per minute needs the dense sheets plus listening windows; an earlier hand count found 8-15 a minute in
  news-type Shorts.

## The second set (10 more top Shorts, measured the same way)

| Short (kind) | Views | Length | Cuts a min | Shot median / p90 | Camera moving | Words a min | Gaps > 0.3 s |
|---|---|---|---|---|---|---|---|
| J: a narrated news story | ~60M | 50.6 s | 35.6 | 1.40 / 2.47 s | 63% | 214 | 6 |
| K: a narrated explainer | ~8M | 41.9 s | 22.9 | 2.07 / 4.23 s | 49% | 243 | 5 |
| L: a "what the early versions looked like" history | ~5M | 41.5 s | 24.6 | 0.97 / 5.67 s | 71% | 196 | 5 |
| M: a how-to tip | ~3M | 24.9 s | 24.1 | 1.78 / 2.93 s | 30% | 223 | 4 |
| N: an interview clip with commentary | ~2M | 16.0 s | 30.0 | 1.62 / 2.80 s | 81% | 183 | 0 |
| O: a three-point list of improvements | ~1.4M | 28.2 s | 63.9 | 0.90 / 1.63 s | 81% | 250 | 0 |
| P: a long backstory explainer | ~0.9M | 68.9 s | 70.5 | 0.77 / 1.73 s | 62% | 211 | 4 |
| Q: an opinion take on a character | ~0.6M | 28.2 s | 36.1 | 1.48 / 2.28 s | 86% | 249 | 2 |
| R, S: two narrated reaction stories | - | 28.9 / 74.0 s | 35.3 / 44.6 | 1.27 / 1.04 s | 75-79% | 152 / 208 | 6 / 5 |

**What it adds to the first set:** the first word is on frame 0 in all ten; the cut rate spreads 23-71 a minute (median ~35) with the
shot median 0.8-2.1 s, so "a new picture every 0.5-2.2 s" holds; the camera moves in 30-86% of frames (a held shot still drifts);
150-250 words a minute.
