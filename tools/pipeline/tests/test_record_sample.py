"""tools/voice/record_sample.py: the page is served only with its token, anything but a WAV is refused, a WAV is saved and the
recorder ends with SAVED <path> (the line the chat waits on)."""
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "voice" / "record_sample.py"


def wav(n=4800, sr=48000):
    data = struct.pack(f"<{n}h", *([1000, -1000] * (n // 2)))
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


def status(url, body=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, method="POST" if body is not None else "GET"), timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_the_recorder_saves_a_wav_and_ends(tmp_path):
    p = subprocess.Popen([sys.executable, str(TOOL), "--no-open", "--out-dir", str(tmp_path), "--name", "t"],
                         stdout=subprocess.PIPE, text=True)
    try:
        first = p.stdout.readline().strip()
        assert first.startswith("RECORDER http://127.0.0.1:")
        url = first.split(" ", 1)[1]
        base, token = url.split("/?t=")
        code, page = status(url)
        assert code == 200 and b"Record your voice" in page and b"Last summer" in page
        assert status(base + "/?t=wrong")[0] == 404
        assert status(base + "/save?t=wrong", wav())[0] == 404
        assert status(base + "/save?t=" + token, b"not audio")[0] == 400
        code, body = status(base + "/save?t=" + token, wav())
        assert code == 200 and b"t_" in body
        out, _ = p.communicate(timeout=20)
        assert p.returncode == 0 and out.strip().startswith("SAVED ")
        saved = Path(out.strip().split(" ", 1)[1])
        assert saved.parent == tmp_path and saved.read_bytes() == wav()
    finally:
        if p.poll() is None:
            p.kill()


def test_clone_voice_sends_the_name_and_each_file(tmp_path, monkeypatch):
    sys.path.insert(0, str(TOOL.parents[1]))
    import importlib.util
    spec = importlib.util.spec_from_file_location("clone_voice", TOOL.parent / "clone_voice.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sent = {}

    class R:
        status_code = 200

        @staticmethod
        def json():
            return {"voice_id": "abc123", "requires_verification": False}

    def post(url, headers, data, files, timeout):
        sent.update(url=url, key=headers["xi-api-key"], data=data, names=[(k, v[0]) for k, v in files])
        return R()
    monkeypatch.setattr(m, "elevenlabs_key", lambda: "sk_test")
    monkeypatch.setattr(m.httpx, "post", post)
    a, b = tmp_path / "me.wav", tmp_path / "me_rebuilt.wav"
    a.write_bytes(wav())
    b.write_bytes(wav())
    assert m.clone("Me", [a, b])["voice_id"] == "abc123"
    assert sent["url"] == "https://api.elevenlabs.io/v1/voices/add" and sent["key"] == "sk_test"
    assert sent["data"]["name"] == "Me" and sent["names"] == [("files", "me.wav"), ("files", "me_rebuilt.wav")]
