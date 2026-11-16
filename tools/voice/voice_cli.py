"""Local voice-clone CLI for the pipeline's `command` engine (the fallback to ElevenLabs). Run it with the ENGINE's venv python:

  <engine venv python> tools/voice/voice_cli.py --engine chatterbox --voice <MEDIA>/voice/ref.wav --manifest m.json   (batch)
  <engine venv python> tools/voice/voice_cli.py --engine chatterbox --voice <MEDIA>/voice/ref.wav --text "Hi." --out a.wav

--voice is the reference clip; engines that need its exact transcript read it from the same path with .txt (ref.wav -> ref.txt).
Long text is split at sentence ends into chunks the engine handles well, rendered with a seed derived from the text (re-renders
are reproducible; a manifest entry's "retake": n gives take n instead), and joined with a short pause.
config/tts.toml: [tts.command] template = ["<venv python>", "<repo>/tools/voice/voice_cli.py", "--engine", "...", "--voice", "{voice}",
"--manifest", "{manifest}"] (batch mode: the model loads once per video).
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

GAP_S = 0.12  # pause between chunks of one beat


class Engine:
    max_chars = 300  # chunk size the engine handles without drift or memory spikes

    def __init__(self, ref_wav, ref_text):
        self.ref_wav, self.ref_text = str(ref_wav), ref_text

    def synth(self, text):  # -> (float32 mono array, sample rate)
        raise NotImplementedError


class Chatterbox(Engine):
    def __init__(self, *a):
        super().__init__(*a)
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        self.m = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")

    def synth(self, text):
        return self.m.generate(text, language_id="en", audio_prompt_path=self.ref_wav).squeeze(0).cpu().numpy(), self.m.sr


class Qwen3(Engine):
    def __init__(self, *a, size="1.7B"):
        super().__init__(*a)
        from qwen_tts import Qwen3TTSModel
        self.m = Qwen3TTSModel.from_pretrained(f"Qwen/Qwen3-TTS-12Hz-{size}-Base", device_map="cuda:0", dtype=torch.bfloat16,
                                               attn_implementation="sdpa")
        self.p = self.m.create_voice_clone_prompt(ref_audio=self.ref_wav, ref_text=self.ref_text, x_vector_only_mode=False)

    def synth(self, text):
        wavs, sr = self.m.generate_voice_clone(text=text, language="English", voice_clone_prompt=self.p)
        return wavs[0], sr


class VoxCPM(Engine):
    # Whole sections in one call (stitched pieces make audible tone jumps). 207 words / 60 s peaked at 7.06 GB allocated on an
    # 8 GB card; the pipeline's [tts] section_words keeps sections at that size. A Short with its loop tail is ~1250 characters,
    # and a split here would put a seam back in.
    max_chars = 1500

    def __init__(self, *a):
        super().__init__(*a)
        from voxcpm import VoxCPM as V
        self.m = V.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False)  # optimize needs Triton (none on Windows)

    def synth(self, text):
        return self.m.generate(text=text, prompt_wav_path=self.ref_wav, prompt_text=self.ref_text, reference_wav_path=self.ref_wav,
                               cfg_value=2.0, inference_timesteps=10), self.m.tts_model.sample_rate


class Dots(Engine):
    max_chars = 150  # reference (~9 s) + output must stay under 20.48 s to stay in the 6.5 GB memory bucket (dots README)

    def __init__(self, *a):
        super().__init__(*a)
        from dots_tts.runtime import DotsTtsRuntime
        self.m = DotsTtsRuntime.from_pretrained("dots-studio/dots.tts-soar", precision="bfloat16", optimize=False)

    def synth(self, text):
        r = self.m.generate(text=text, prompt_audio_path=self.ref_wav, prompt_text=self.ref_text, num_steps=10, guidance_scale=1.2)
        return r["audio"].float().cpu().squeeze().numpy(), r["sample_rate"]


ENGINES = {"chatterbox": Chatterbox, "qwen3": Qwen3, "voxcpm": VoxCPM, "dots": Dots}


def chunks(text, max_chars):
    """Sentence-sized pieces no longer than max_chars (a single long sentence is split at commas, then kept whole)."""
    out, cur = [], ""
    for s in re.split(r"(?<=[.?!…])\s+", text.strip()):
        parts = [s] if len(s) <= max_chars else re.split(r"(?<=,)\s+", s)
        for p in parts:
            if cur and len(cur) + 1 + len(p) > max_chars:
                out.append(cur)
                cur = p
            else:
                cur = f"{cur} {p}".strip()
    return out + ([cur] if cur else [])


def render(engine, text, retake=0):
    """retake n > 0 = another take of the same text (the pipeline asks for one when a take has a filler it can't cut)."""
    seed = int(hashlib.sha1(text.encode()).hexdigest()[:8], 16) + retake
    pieces, sr = [], None
    for c in chunks(text, engine.max_chars):
        torch.manual_seed(seed); np.random.seed(seed % 2**32)
        wav, sr = engine.synth(c)
        pieces += [np.asarray(wav, dtype=np.float32).reshape(-1), np.zeros(int(GAP_S * sr), dtype=np.float32)]
    return np.concatenate(pieces[:-1]), sr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=sorted(ENGINES), required=True)
    ap.add_argument("--voice", required=True, help="reference clip; its transcript sits next to it as .txt")
    ap.add_argument("--manifest", help='JSON list of {"text", "wav"} (the pipeline\'s batch mode)')
    ap.add_argument("--text"); ap.add_argument("--out")
    a = ap.parse_args()
    ref = Path(a.voice)
    ref_txt = ref.with_suffix(".txt")
    ref_text = ref_txt.read_text(encoding="utf-8").strip() if ref_txt.exists() else None
    if a.engine in ("qwen3", "voxcpm", "dots") and not ref_text:
        raise SystemExit(f"{a.engine} needs the reference transcript in {ref_txt}")
    jobs = json.loads(Path(a.manifest).read_text(encoding="utf-8")) if a.manifest else [{"text": a.text, "wav": a.out}]
    engine = ENGINES[a.engine](ref, ref_text)
    for j in jobs:
        wav, sr = render(engine, j["text"], j.get("retake", 0))
        sf.write(j["wav"], wav, sr, subtype="PCM_16")
        print(f"{Path(j['wav']).name}: {len(wav) / sr:.1f} s", flush=True)


if __name__ == "__main__":
    main()
