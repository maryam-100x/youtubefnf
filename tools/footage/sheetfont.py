"""sheetfont.py: the fonts every contact sheet and strip draws with, on Windows and macOS alike: Arial (bold or regular) found by name in
the system's font folders (Pillow searches them), DejaVu where Arial is missing, Pillow's built-in font last, so a sheet never fails
for a font.

  from sheetfont import font; font(14) (bold), font(12, bold=False)"""
from PIL import ImageFont

_NAMES = {True: ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"), False: ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf")}
_CACHE = {}


def font(size, bold=True):
    k = (int(size), bool(bold))
    if k not in _CACHE:
        found = None
        for name in _NAMES[k[1]]:
            try:
                found = ImageFont.truetype(name, k[0])
                break
            except OSError:
                continue
        _CACHE[k] = found or ImageFont.load_default()
    return _CACHE[k]
