"""Rebuild the caption cues and chunks from the caption words (dj's own group() and config), after cuts that moved only the words;
rewrites captions.srt / chunks.srt, so the subtitles never run late behind words a gap cut moved.

  cd tools && PIPE voice/captions_regroup.py ../videos/<video>"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj.core import Ctx, load_config  # noqa: E402
from dj.__main__ import video_config  # noqa: E402
from dj.captions import group, write_srt, PUNCT_BREAK  # noqa: E402

vid = sys.argv[1]
cfg = load_config(None, [*video_config(vid)])
ctx = Ctx(vid, cfg)
c = cfg['captions']
p = ctx.build / 'captions' / 'words.json'
D = json.loads(p.read_text(encoding='utf-8'))
old = D['cues']
D['cues'] = group(D['words'], 99, c['max_chars'], 6.0, '.?!…')
D['chunks'] = group(D['words'], c['chunk_words'], c['chunk_chars'], 2.5, PUNCT_BREAK)
p.write_text(json.dumps(D, indent=1, ensure_ascii=False), encoding='utf-8')
write_srt(ctx.path('captions', 'captions.srt'), D['cues'])
write_srt(ctx.path('captions', 'chunks.srt'), D['chunks'])
same = sum(1 for a, b in zip(old, D['cues']) if a['text'] == b['text'])
print(f"{len(D['cues'])} cues ({len(old)} before, {same} same text in order), {len(D['chunks'])} chunks")
