# videos/_template

A video's repo folder (`videos/<id>-<slug>/`): its script, its settings (`video.toml`, from `tools/pipeline/video.example.toml`), its
notes and its cue sheet. Its media (build, renders, exports) live under the media root, `MEDIA/videos/<id>-<slug>/`.

## clips

Every clip a video plays is cut by ONE file, `tools/motion/prep<id>.py`, copied from `tools/motion/prep_template.py`. Nothing else cuts
footage, and the composition never plays a source file directly: it plays the cut clips.

**The CLIPS list** is the whole cut: `name: (source, in s, out s, filter)`, one shot per entry.
- The name is `s<beat>_<what>`: the beat it plays on and what it shows (`s07_city_traffic`, `s03_launch_stage`), so a clip's
  file says at once where it sits and what it is (`standard/LONG_FORM.md`, method step 8).
- The source is a file under `FOOTAGE/sources` (or a full path), named once at the top of the file with a comment saying where it came
  from (who made it, its title, its resolution and frame rate).
- The comment after each entry says which words it plays on (`S07 "the bridge"`) and the source shot it sits inside
  (`shot 2.90-6.40`), read off a frame sheet of the source. Pick every span on the frame sheet, never from a guessed time.
- The filter is `""` (cover-scaled to 1920x1080), `KEEP` (the source's own picture, e.g. a 4K source the edit zooms into) or an ffmpeg
  filter that runs before the cover scale. A clip plays whole: a crop is the exception, and its line says why.

**Each span sits inside one shot of its source**, with a few frames to spare at each end: a span that crosses the source's own cut
shows a sliver of another shot for a frame or two, and a span that opens or closes inside a fade reads as a flash frame.

**The encode** is fixed in the template (`ENC`): 1920x1080, the source's own frame rate, x264 CRF 15 medium, a keyframe every 15
frames, no B-frames, no audio. Clips go to `PUBLIC/v<id>/clips/<name>.mp4`; a clip whose entry is unchanged is kept on the next run.

**What the run writes besides the clips:**
- `tools/motion/src/clipdurs.json`: each clip's last frame and rate (shared by every prep, written under a lock), so the gate and the
  static audit know where every file ends;
- `tools/motion/prep<id>_clips.json`: the gate's manifest (name -> [source, in, out]); point `video.toml` `[gate] clips_json` at it.

**`--check`** runs after every cut and must come back with 0 flags before the gate:
- `CUT`: a camera cut inside the cut clip (a clip that holds its source's own cuts by design is named in `CUTS_OK` with the count);
- `EDGE`: a cut in the source within 0.5 s inside the span's in or out point (the `[audit]` edge and scene values);
- `FADE`: a fade or dissolve at either edge (`tools/motion/qa_fades.py`);
- `FREEZE`: a held stretch inside a clip (`tools/motion/qa_midfreeze.py`).

```
PIPE tools/motion/prep12.py --check            # cut what changed, then check every clip
PIPE tools/motion/prep12.py --only s07_city_traffic --check
```

Keep the prep's top level free of side effects (all work under `main()`): `qa_fades.py` and the gate import it to read `CLIPS` and `DL`.
The cuts run under the heavy-job ticket (`tools/pipeline/heavy.py`), so decoding big sources waits its turn beside a render.
