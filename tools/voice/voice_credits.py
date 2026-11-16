"""ElevenLabs credits left this period: checked before a voicing run. The key is read only inside dj.tts.elevenlabs_key() (a file in
the media root's secrets/) and never printed.

  PIPE tools/voice/voice_credits.py"""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj.tts import elevenlabs_key  # noqa: E402

req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": elevenlabs_key()})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.load(r)
used, limit = d.get("character_count", 0), d.get("character_limit", 0)
print(f"ElevenLabs: {limit - used:,} credits left of {limit:,} this period (tier: {d.get('tier')}; resets {d.get('next_character_count_reset_unix')})")
# printed with every reading, so no chat or agent turns a low balance into a question or a blocker
print("With auto top-up on in the ElevenLabs account, the number is for knowing: a low balance is never a blocker. A quota error is "
      "first a top-up on its way: keep working, re-check this every few minutes for 30+ min, retry the same request; only a balance "
      "still empty after that goes to the creator, with the times checked.")
