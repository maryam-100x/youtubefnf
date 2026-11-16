"""ElevenLabs pronunciation dictionaries from names.json (the voice lock's name tests, standard/VOICE_LOCK.md Research 3).
An alias rule swaps a written name for what the voice should read ("Saoirse Nguyen" -> "Sersha Win") on ElevenLabs' side; a phoneme
rule gives it IPA (eleven_v4/v3/flash_v2 only). A dictionary is used only by requests that name it (span_takes.py --dict ID:VERSION,
or [tts.elevenlabs] pronunciation_dictionaries); it changes nothing else on the account. The key only through dj.tts.elevenlabs_key().

  PIPE tools/voice/eleven_dict.py create --name <name> --alias "Saoirse Nguyen" "Thibault" ...
      (alias = names.json's "say" for each)        [--phoneme "Saoirse=ˈsɪɹʃə" ...]
  PIPE tools/voice/eleven_dict.py list
  PIPE tools/voice/eleven_dict.py archive <id>      (PATCH archived=true: ElevenLabs has no delete for dictionaries)"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE.parent))
from paths import TOOLS  # noqa: E402
from dj.tts import elevenlabs_key  # noqa: E402

API = "https://api.elevenlabs.io/v1/pronunciation-dictionaries"
NAMES = TOOLS / "sound" / "names.json"


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"xi-api-key": elevenlabs_key(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs {e.code}: {e.read().decode(errors='replace')[:600]}")


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["create", "list", "archive"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--alias", nargs="*", default=[])
    ap.add_argument("--phoneme", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "list":
        d = call("GET", API + "?page_size=100")
        for x in d.get("pronunciation_dictionaries", []):
            print(x["id"], x.get("latest_version_id"), x.get("name"))
        return
    if a.cmd == "archive":
        if not a.id:
            raise SystemExit("give the id")
        d = call("PATCH", f"{API}/{a.id}", {"archived": True})
        print(f"archived {d.get('id', a.id)} {d.get('name', '')}")
        return
    T = json.loads(NAMES.read_text(encoding="utf-8")).get("names", {})
    rules = []
    for n in a.alias:
        if n not in T:
            raise SystemExit(f"'{n}' is not in {NAMES} (add it with its \"say\" first)")
        say = T[n]["say"]
        rules.append({"type": "alias", "string_to_replace": n, "alias": say, "case_sensitive": True, "word_boundaries": True})
    for spec in a.phoneme:
        n, ph = spec.split("=", 1)
        rules.append({"type": "phoneme", "string_to_replace": n, "phoneme": ph, "alphabet": "ipa", "case_sensitive": True,
                      "word_boundaries": True})
    if not rules or not a.name:
        raise SystemExit("create needs --name and at least one --alias or --phoneme")
    d = call("POST", API + "/add-from-rules", {"name": a.name, "rules": rules,
                                                "description": "voice lock: names said the American way (names.json)"})
    print(json.dumps({"id": d["id"], "version": d["version_id"], "rules": len(rules)}))


if __name__ == "__main__":
    main()
