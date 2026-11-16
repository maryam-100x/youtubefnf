"""brand.py: the creator's accent colour for the Python tools, read from the one place every graphic takes it from.

tools/motion/src/brand.ts holds one plain line `export const BRAND = '#RRGGBB';` (the setup writes the creator's colour there). The
Python tools that draw marks, outlines or highlights (automark.py, spotmask.py, the review boards) read it here, so a colour change is
one edit. There is no fallback colour: a missing or unreadable line stops the tool with the fix to make.

  from brand import BRAND_HEX, BRAND_RGB, BRAND_BGR      (from a script in tools/motion/)
"""
import re
from pathlib import Path

BRAND_TS = Path(__file__).resolve().parent / "src" / "brand.ts"
FIX = "set the accent in tools/motion/src/brand.ts (setup): one line export const BRAND = '#RRGGBB';"


def brand_hex():
    try:
        text = BRAND_TS.read_text(encoding="utf-8")
    except OSError:
        raise SystemExit(f"brand.py: {BRAND_TS} is missing: {FIX}")
    m = re.search(r"^\s*export\s+const\s+BRAND\s*=\s*['\"](#[0-9A-Fa-f]{6})['\"]\s*;?", text, re.M)
    if not m:
        raise SystemExit(f"brand.py: no BRAND colour line in {BRAND_TS}: {FIX}")
    return m.group(1).upper()


BRAND_HEX = brand_hex()
BRAND_RGB = tuple(int(BRAND_HEX[i:i + 2], 16) for i in (1, 3, 5))
BRAND_BGR = BRAND_RGB[::-1]

if __name__ == "__main__":
    print(BRAND_HEX, BRAND_RGB, "from", BRAND_TS)
