"""Whisper's words for a few short wavs, as JSON (the voice lock's second ear: autopick.py and voice_layin.py hold every take against the
script with two different recognizers, Whisper here and the CTC letters of ctcalign.py, since one family of recognizer judging its own
kind of error is biased (best-of-N reranking with mixed verifiers)). faster-whisper, word timestamps, no prompt (a prompt lets the
model write the expected word over a wrong sound).

  PIPE tools/voice/asr_words.py <wav> [<wav> ...] [--model small.en] [--json out.json]
      -> {"<wav>": {"text": "...", "words": [{"w", "start", "end", "p"}]}}"""
import argparse
import json
import os
import sys

# cuBLAS 12 / cuDNN 9 for ctranslate2 on the GPU (the voice is the critical path), found the way dj captions finds them (this venv's
# pip packages nvidia-cublas-cu12 / nvidia-cudnn-cu12 / nvidia-cuda-nvrtc-cu12), else a CUDA torch's own lib folder: the running
# env's, or the folders in ASR_CUDA_LIBS (os.pathsep-separated). A 45-s piece takes ~54 s on the CPU (int8, 2 threads) and ~7 s on a
# GPU (float16, 2.9 s of it the load), with the same words.
CUDA_LIBS = [d for d in os.environ.get("ASR_CUDA_LIBS", "").split(os.pathsep) if d]


def torch_lib():
    """The running env's torch/lib folder, if torch is installed (found without importing it)"""
    try:
        import importlib.util
        spec = importlib.util.find_spec("torch")
        if spec and spec.submodule_search_locations:
            return [os.path.join(list(spec.submodule_search_locations)[0], "lib")]
    except (ImportError, ValueError):
        pass
    return []


def cuda_dirs():
    out = []
    try:
        import nvidia
        out += [os.path.join(nvidia.__path__[0], sub, "bin") for sub in ("cublas", "cudnn", "cuda_nvrtc")]
    except ImportError:
        pass
    return out + torch_lib() + CUDA_LIBS


def model(name):
    """(WhisperModel, device): the GPU when ctranslate2 can use it (ASR_DEVICE=cpu forces the CPU), else the CPU on 4 threads"""
    from faster_whisper import WhisperModel
    if os.environ.get("ASR_DEVICE", "cuda") == "cuda":
        for d in reversed(cuda_dirs()):
            if os.path.isdir(d):
                if hasattr(os, "add_dll_directory"):   # Windows only; elsewhere the loader path is enough
                    os.add_dll_directory(d)
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        try:
            import numpy as np
            m = WhisperModel(name, device="cuda", compute_type="float16")
            list(m.transcribe(np.zeros(16000, np.float32), beam_size=1)[0])   # cuBLAS loads at the first encode: prove it here
            return m, "cuda"
        except Exception as e:      # no GPU (every Mac), no libraries, out of memory: the CPU
            print(f"asr_words: GPU not usable ({type(e).__name__}: {str(e)[:120]}); CPU", file=sys.stderr)
    return WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=4), "cpu"


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("wavs", nargs="+")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--json")
    a = ap.parse_args()
    m, dev = model(a.model)
    out = {}
    for w in a.wavs:
        segs, _ = m.transcribe(w, word_timestamps=True, beam_size=5, condition_on_previous_text=False, vad_filter=False)
        words = [{"w": x.word.strip(), "start": round(x.start, 3), "end": round(x.end, 3), "p": round(x.probability, 3)}
                 for s in segs for x in (s.words or [])]
        out[w] = {"text": " ".join(x["w"] for x in words), "words": words}
    s = json.dumps(out, ensure_ascii=False, indent=1)
    if a.json:
        open(a.json, "w", encoding="utf-8").write(s)
    print(s)


if __name__ == "__main__":
    main()
