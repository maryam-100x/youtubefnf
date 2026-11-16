"""After a voice_edit cut: move every caption word, cue and chunk after the cut by the frames removed (a word that straddles the cut
ends at it), rewrite the two srt files and sign the new narration, so the captions match without a new Whisper pass.

  PIPE tools/voice/captions_shift.py <build dir> <cut start s> <frames>

The cut start and frames are what `voice_edit.py cut` prints. Then tools/motion/sync_words.py."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj.core import file_sig  # noqa: E402
from dj.captions import write_srt  # noqa: E402

__import__("voice_lock").guard_argv(__file__)  # the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by voice_layin.py
B, c1, n = Path(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
d = n / 60
D = json.loads((B / 'captions/words.json').read_text(encoding='utf-8'))
moved = 0
for key in ('words', 'cues', 'chunks'):
    for x in D[key]:
        if x['start'] >= c1:
            x['start'] = round(x['start'] - d, 4); x['end'] = round(x['end'] - d, 4); moved += key == 'words'
        elif x['end'] > c1:
            x['end'] = round(c1 if key == 'words' else x['end'] - d, 4)
D['narration_sig'] = file_sig(B / 'voice/narration.wav')
(B / 'captions/words.json').write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding='utf-8')
write_srt(B / 'captions/captions.srt', D['cues'])
write_srt(B / 'captions/chunks.srt', D['chunks'])
print(f'{moved} words moved {d:.3f} s earlier from {c1}')
