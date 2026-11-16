"""qa_devices.py: the device count. A passed prototype is a level, never devices to copy: a graphic device that works once (round
chips of cropped screenshots, a grid of face icons, an emoji slide) spreads into dozens of the film's graphics when a builder copies what
was praised instead of the quality standard behind it, and a template that spreads anyway is stopped by this check, not by a promise.

From the code: every shot of the film (the shot entries of the composition's module and every file of the video's code it imports,
subfolders included: `shot(...)`, `{at: ..., el: ...}`, the `ft(...)`/`page(...)` shot helpers; a Run's pieces `{at, el}` are
appearances of their own) and its MAIN PICTURE: "clip", "still", or the graphic component the shot is (its helpers inlined: `ft(...)` is
a Foot, `SPLIT` its SplitPair, `(d) => <Step>{rack12(d, t)}</Step>` the rack's graphic; camera, ground and stamp wrappers looked through:
Cam, Step, Grounds, Stamped, Enter, Lands; grounds, credits and labels skipped: Stage, Ground, Credit, Tag, Stamp, Lit, MarkBox; a
video's own picture pieces, one full picture with only labels beside it, are clips or stills: FtA, StA, Calm, FootC). One device under
its range copies' names (RecA, RecB, RecC). Its time is its anchor (w/b0/we on the video's words.json, the bites' gaps added as the
timing helper does).

What it flags:
  DEVICE_SPREAD  one graphic component as the main picture of more than CAP (6) appearances of the film without a written reason. An
                 appearance is a run of consecutive shots with the same main component (a graphic cut into camera steps, Cam / Step,
                 is one appearance); a `// device: <why this line needs this device>` line in the comment above any of its shots lets
                 that appearance pass. The list names every appearance, so a builder sees the devices the film already leans on.
  ROUND_CROP     a shot whose picture is a round crop of a screenshot: kit3 Still's `icons={...}`, or a component that draws a picture
                 inside a circle (an <Img> with borderRadius 50% or half its side, a circle-clipped box holding a picture, a face icon's
                 data-gate="icon"), or one that uses such a component (Chip, PlacedIcon, a row or grid of them, a face over a clip). Flagged
                 outright, whatever the count, unless the words under the shot name a lead (video.toml [gate] leads: the people the film
                 is about; none by default) AND the shot says `// device: portrait <why>` (portraits of the leads only where a portrait
                 is truly the idea, clean, big, centred), or it says `// device: passed <the creator's words>` (a piece the creator
                 passed as it is).
  STAMP_PHRASE   a stamp (a Stamp* element or a shot's `stamp: {...}` data, with its words in the code) whose words carry no number,
                 multiplier or record, or ask a question: the stamp is a passage's headline claim, never text repeating the voice or a
                 question card, unless `// stamp: <why it is the headline claim>` sits in the 4 lines above it.

  PIPE tools/motion/qa_devices.py <video> [--src <code dir>] [--list] [--cap 6]
      --list   every shot with its time, its main picture and its file:line (the devices the film uses so far, for a builder's brief)
  exit 1 on a flag. In the gate: B23 (gate.py, every `pipe.py <video> gate` of a long video); gate_allow.json applies as to every check,
  but a reason belongs in the code (`// device: ...`), where the next builder reads it.

PROOF: the end of this file.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import PUBLIC, TOOLS  # noqa: E402
CAP = 6
FPS = 60
LEADS = ()   # the people the film is about: video.toml [gate] leads

# ----------------------------------------------------------------------------------------------------------- what a component is
CLIPS = {"Foot", "FootC", "Clip", "LClip", "VClip", "SpeedRamp", "Burst", "OffthreadVideo", "Video", "ZoomClip", "Ft", "Bite",
         "Footage"}
STILLS = {"Still", "Calm", "StampStill", "Img", "img", "Picture", "Pic", "St", "LinStill"}
PICTURE_PIECES = {"TagShot", "StampShot", "TypedShot", "Run"}   # a picture (or a run of them) with the house label, stamp or typing on it
STRUCT = {"AbsoluteFill", "Sequence", "Series", "Freeze", "Loop", "Fragment", "", "Provider", "Suspense", "Audio", "OffthreadVideoInner"}
WRAPS = {"Grounds", "Step", "Cam", "Stamped", "Enter", "Lands", "Hold", "XBlur", "Fade", "Delayed", "Shift", "Inner"}
OVERLAYS = {"Credit", "Stage", "Ground", "Tag", "Label", "Kicker", "Lit", "Stamp", "StampOut", "MarkBox", "Veil", "TypedLine", "Glow",
            "Vignette", "EdgesIn", "FootShade", "LiftFilter", "Pending", "BiteSubs", "Subs", "Caption"}

ENTRY = re.compile(r"^\s*(?:return\s+)?(?:shot|ft2?|page|parts)\(|\{at:\s*.+?,\s*el:")
AT_EL = re.compile(r"\{at:\s*.+?,\s*el:")


def in_attribute(text, pos):
    """is this `{at: ..., el: ...}` a piece handed to a component (`<Run pieces={[{at: 0, el: ...}]} />`) rather than a shot of the
    shots array (a list of entries, or `return [{at: a0, el: ...}]`): its innermost open bracket sits in a JSX attribute"""
    depth, k = 0, pos - 1
    while k >= 0:
        c = text[k]
        if c in ")]}":
            depth += 1
        elif c in "([{":
            if depth == 0:
                before = text[max(0, k - 3):k].replace(" ", "").replace("\n", "")
                return before.endswith("={") or (c == "{" and before.endswith("="))
            depth -= 1
        k -= 1
    return False
TOP = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:const|let|var|function\*?|class|async\s+function)\s+([A-Za-z_$][\w$]*)", re.M)
STMT = re.compile(r"^(?:export|import|const|let|var|function|async|class|type|interface|enum|declare)\b", re.M)
REGEX_BEFORE = set("(,=:[!&|?{};+-*%<>~^")


# ================================================================================================================= a small TSX reader
def _skip_string(s, i):
    q, i = s[i], i + 1
    while i < len(s) and s[i] != q and s[i] != "\n":
        i += 2 if s[i] == "\\" else 1
    return i + 1


def _prev_sig(s, i):
    k = i - 1
    while k >= 0 and s[k] in " \t\r\n":
        k -= 1
    return s[k] if k >= 0 else ""


def _skip_regex(s, i):
    """from a regex literal's opening slash to past its flags (character classes kept whole)"""
    i, cls = i + 1, False
    while i < len(s) and s[i] != "\n":
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            cls = True
        elif c == "]":
            cls = False
        elif c == "/" and not cls:
            i += 1
            while i < len(s) and (s[i].isalnum()):
                i += 1
            return i
        i += 1
    return i


def strip_comments(s):
    """the code with // and /* */ comments blanked (newlines kept, so line numbers hold), strings, templates and regexes left whole"""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "'\"":
            j = _skip_string(s, i)
            out.append(s[i:j])
            i = j
        elif c == "`":
            j = i + 1
            while j < n and s[j] != "`":
                j += 2 if s[j] == "\\" else 1
            out.append(s[i:j + 1])
            i = j + 1
        elif s.startswith("//", i):
            j = s.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in s[i:j]))
            i = j
        elif c == "/" and _prev_sig(s, i) in REGEX_BEFORE | {""}:
            j = _skip_regex(s, i)
            out.append(s[i:j])
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


class El:
    """a JSX element: its name, where it starts, its attributes' text, its children (elements and the refs of its {expressions}), what
    its attribute expressions hold, and the code file it is written in (set when a forest is expanded)"""
    __slots__ = ("name", "pos", "attrs", "kids", "props", "file")

    def __init__(self, name, pos):
        self.name, self.pos, self.attrs, self.kids, self.props, self.file = name, pos, "", [], [], None


class Ref:
    """an identifier in an expression (a call `name(` or a bare name): a helper to inline if the video's code defines one"""
    __slots__ = ("name", "pos", "call")

    def __init__(self, name, pos, call):
        self.name, self.pos, self.call = name, pos, call


def _jsx_start(s, i):
    nxt = s[i + 1] if i + 1 < len(s) else ""
    if not (nxt.isalpha() or nxt == ">"):
        return False
    p = _prev_sig(s, i)
    if p == "" or p in "([{,?:=>&|!};":
        return True
    return bool(re.search(r"\breturn\s*$", s[max(0, i - 12):i]))


def scan_js(s, i):
    """an expression from i up to its unmatched closing bracket: [El | Ref] in order, and the index of that bracket"""
    nodes, depth, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "'\"":
            i = _skip_string(s, i)
        elif c == "`":
            i += 1
            while i < n and s[i] != "`":
                if s[i] == "\\":
                    i += 2
                    continue
                if s.startswith("${", i):
                    sub, i = scan_js(s, i + 2)
                    nodes += sub
                i += 1
            i += 1
        elif c in "([{":
            depth += 1
            i += 1
        elif c in ")]}":
            if depth == 0:
                return nodes, i
            depth -= 1
            i += 1
        elif c == "<" and _jsx_start(s, i):
            el, i = parse_el(s, i)
            nodes.append(el)
        elif c == "/" and _prev_sig(s, i) in REGEX_BEFORE:
            i = _skip_regex(s, i)
        elif c.isalpha() or c in "_$":
            j = i
            while j < n and (s[j].isalnum() or s[j] in "_$"):
                j += 1
            if i == 0 or s[i - 1] != ".":
                k = j
                while k < n and s[k] in " \t":
                    k += 1
                nodes.append(Ref(s[i:j], i, k < n and s[k] == "("))
            i = j
        else:
            i += 1
    return nodes, i


def parse_el(s, i):
    """a JSX element at '<' -> (El, the index after it)"""
    n, j = len(s), i + 1
    if j < n and s[j] == ">":
        el, j = El("", i), j + 1
    else:
        k = j
        while k < n and (s[k].isalnum() or s[k] in "_$.:-"):
            k += 1
        el, j = El(s[j:k], i), k
        a0 = j
        while j < n:
            while j < n and s[j] in " \t\r\n":
                j += 1
            if s.startswith("/>", j):
                el.attrs = s[a0:j]
                return el, j + 2
            if j >= n or s[j] == ">":
                el.attrs = s[a0:j]
                j += 1
                break
            if s[j] == "{":                                        # a spread {...props}
                sub, k = scan_js(s, j + 1)
                el.props += sub
                j = k + 1
                continue
            k = j
            while k < n and (s[k].isalnum() or s[k] in "_$:-"):
                k += 1
            if k == j:                                             # not an attribute: give up on this tag's attributes
                j += 1
                continue
            j = k
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j < n and s[j] == "=":
                j += 1
                while j < n and s[j] in " \t\r\n":
                    j += 1
                if j < n and s[j] in "'\"":
                    j = _skip_string(s, j)
                elif j < n and s[j] == "{":
                    sub, k = scan_js(s, j + 1)
                    el.props += sub
                    j = k + 1
                elif j < n and s[j] == "<":
                    sub, j = parse_el(s, j)
                    el.props.append(sub)
    while j < n:                                                   # the children, up to its closing tag
        if s.startswith("</", j):
            k = s.find(">", j)
            return el, (n if k < 0 else k + 1)
        c = s[j]
        if c == "<" and j + 1 < n and (s[j + 1].isalpha() or s[j + 1] == ">"):
            sub, j = parse_el(s, j)
            el.kids.append(sub)
        elif c == "{":
            sub, k = scan_js(s, j + 1)
            el.kids += sub
            j = k + 1
        else:
            j += 1
    return el, j


def walk(nodes):
    """every element in a forest, depth first (children and attribute expressions)"""
    for x in nodes:
        if isinstance(x, El):
            yield x
            yield from walk(x.kids)
            yield from walk(x.props)


def walk_own(nodes):
    """a shot's own elements: as walk(), but a run's pieces (`<Run pieces={[...]}>`) are left to the pieces' own entries"""
    for x in nodes:
        if isinstance(x, El):
            yield x
            yield from walk_own(x.kids)
            if base(x.name) not in PICTURE_PIECES:
                yield from walk_own(x.props)


def base(name):
    return name.rsplit(".", 1)[-1]


# ============================================================================================================ the code's definitions
class Code:
    """the video's code files (its src folder and every subfolder) and their top-level definitions"""

    def __init__(self, src):
        self.src = Path(src)
        self.files = sorted(p for p in self.src.rglob("*.ts*") if p.suffix in (".ts", ".tsx"))
        self.text, self.clean, self.defs, self.imports = {}, {}, defaultdict(list), defaultdict(dict)
        for f in self.files:
            t = f.read_text(encoding="utf-8", errors="replace")
            c = strip_comments(t)
            self.text[f], self.clean[f] = t, c
            cuts = sorted({m.start() for m in STMT.finditer(c)} | {len(c)})
            for m in TOP.finditer(c):
                end = next((x for x in cuts if x > m.start()), len(c))
                self.defs[m.group(1)].append((f, m.start(), end))
        for f in self.files:                                        # what each file imports from the video's own code
            for m in re.finditer(r"^import\s+(?:type\s+)?\{([^}]*)\}\s+from\s+['\"](\.{1,2}/[^'\"]+)['\"]", self.clean[f], re.M):
                tgt = (f.parent / m.group(2)).resolve()
                hit = next((c for c in (tgt.with_suffix(".tsx"), tgt.with_suffix(".ts"), tgt / "index.tsx", tgt / "index.ts")
                            if c in self.clean), None)
                for x in m.group(1).split(","):
                    if x.strip():
                        name, _, local = x.strip().partition(" as ")
                        self.imports[f][(local or name).strip()] = (hit, name.strip())
        self._forest = {}

    def rel(self, f):
        return f.relative_to(self.src).as_posix() if f else "?"

    def lineno(self, f, pos):
        return self.clean[f].count("\n", 0, pos) + 1

    def definition(self, name, f=None):
        """the definition file f means by a name: its own, or the one it imports from the video's code (None: a kit's, or unknown)"""
        ds = self.defs.get(name) or []
        if f is None:
            return ds[0] if ds else None
        own = next((d for d in ds if d[0] == f), None)
        if own:
            return own
        imp = self.imports.get(f, {}).get(name)
        if imp and imp[0] is not None:
            return next((d for d in self.defs.get(imp[1], []) if d[0] == imp[0]), None)
        return None

    def text_of(self, d):
        return self.clean[d[0]][d[1]:d[2]]

    def forest_of(self, name, f=None):
        """a definition's elements and refs (its text after the declaration's `=` or its function head), and its file"""
        d = self.definition(name, f)
        if not d:
            return None, None
        key = (d[0], d[1])
        if key not in self._forest:
            body = self.text_of(d)
            k = body.find("=") if not re.match(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function", body) else body.find("(")
            nodes, _ = scan_js(body[k + 1:] + ")" * 8, 0) if k >= 0 else ([], 0)
            self._forest[key] = nodes
        return self._forest[key], d[0]


def expand(code, nodes, f, depth=0, seen=frozenset()):
    """the elements of a forest with every helper it names inlined: a ref to a lower-case or ALL-CAPS definition of the video's code
    (`ft`, `st`, `SPLIT`, `rack12`) is replaced by that definition's own elements; each element knows the file it is written in"""
    out = []
    for x in nodes:
        if isinstance(x, El):
            e = El(x.name, x.pos)
            e.attrs, e.file = x.attrs, x.file or f
            e.kids = expand(code, x.kids, f, depth, seen)
            e.props = expand(code, x.props, f, depth, seen)
            out.append(e)
        elif isinstance(x, Ref) and depth < 5 and x.name not in seen and (x.name[:1].islower() or (x.name.isupper() and len(x.name) > 1)):
            sub, g = code.forest_of(x.name, f)
            if sub:
                out += expand(code, sub, g, depth + 1, seen | {x.name})
        elif isinstance(x, Ref) and x.call and x.name[:1].isupper() and not x.name.isupper() and x.name not in JS_CALLS:
            e = El(x.name, x.pos)                                    # a component called as a function (`Ft('c12', d, {...})`)
            e.file = f
            out.append(e)
    return out


JS_CALLS = {"Math", "Number", "String", "Boolean", "Object", "Array", "JSON", "Promise", "Date", "Set", "Map", "Symbol", "Error", "RegExp",
            "BigInt", "Intl", "Reflect", "Proxy", "Record", "Partial", "Required", "Readonly", "Pick", "Omit", "React"}


# ================================================================================================================= round crops
RADIUS = re.compile(r"borderRadius:\s*(['\"`]?)([^,}'\"`]+)\1")
PIC_LIT = re.compile(r"""['"`]([^'"`\n]*?\.(?:png|jpe?g|webp|gif))['"`]""", re.I)
# the source's own interface (its round status icons, a round progress dial), emoji and logos are drawn round as they are: no crop; a face,
# a chip or any other picture file is a crop. data/ui_picture_names.json adds the name parts of the source's own interface pictures
_UI_EXTRA = HERE / "data" / "ui_picture_names.json"
UI_NAMES = re.compile("|".join([r"_ic_", "emoji", "logo", "badge"] + [re.escape(x) for x in (
    json.loads(_UI_EXTRA.read_text(encoding="utf-8")) if _UI_EXTRA.exists() else [])]), re.I)
JS_WORDS = {"url", "staticFile", "I", "C", "M", "true", "false", "null", "undefined", "Math", "const", "return", "new", "as", "string"}


def _dim(attrs, key):
    m = re.search(rf"\b{key}:\s*([^,}}]+)", attrs)
    return re.sub(r"\s+", "", m.group(1)) if m else None


def round_radius(attrs):
    """does this element's style make it a circle"""
    if re.search(r"clipPath:\s*['\"`]circle\(|WebkitClipPath:\s*['\"`]circle\(", attrs):
        return True
    for m in RADIUS.finditer(attrs):
        v = m.group(2).strip()
        if v in ("50%", "100%") or re.fullmatch(r"\d{3,}", v) and int(v) >= 999:
            return True
        w, h = _dim(attrs, "width"), _dim(attrs, "height")
        half = re.fullmatch(r"(.+?)\s*/\s*2", v)
        if half and w and w == h and re.sub(r"\s+", "", half.group(1)) == w:
            return True
        if re.fullmatch(r"\d+(?:\.\d+)?", v) and w and w == h and re.fullmatch(r"\d+(?:\.\d+)?", w) and abs(float(w) - 2 * float(v)) < 1.01:
            return True
    return False


def attr(el, name):
    """the text of one attribute's value (`name={...}` or `name="..."`), or None"""
    m = re.search(rf"(?<![\w$-]){re.escape(name)}=", el.attrs)
    if not m:
        return None
    i = m.end()
    s = el.attrs
    if i < len(s) and s[i] in "'\"":
        return s[i:_skip_string(s, i)]
    if i < len(s) and s[i] == "{":
        depth, j = 0, i
        while j < len(s):
            c = s[j]
            if c in "'\"":
                j = _skip_string(s, j)
                continue
            depth += c in "([{"
            depth -= c in ")]}"
            j += 1
            if depth == 0:
                break
        return s[i:j]
    return None


def round_how(el):
    """how this element draws a picture inside a circle, and the expression that names the picture: (how, picture expression) or None"""
    gate_icon = bool(re.search(r"data-gate=['\"{]*['\"]icon['\"]", el.attrs))
    rnd = round_radius(el.attrs)
    if not (gate_icon or rnd):
        return None
    if base(el.name) in ("Img", "img"):
        return ("a face icon (data-gate=\"icon\")" if gate_icon else "an <Img> with a round border radius"), attr(el, "src") or ""
    bg = re.search(r"background(?:Image)?:\s*(`[^`]*url\([^`]*`|['\"][^'\"]*url\([^'\"]*['\"])", el.attrs)
    if rnd and bg:
        return "a round box with a background picture", bg.group(1)
    kid = next((x for x in walk(el.kids) if base(x.name) in ("Img", "img")), None)
    if kid is not None and (gate_icon or re.search(r"overflow:\s*['\"`]hidden", el.attrs)):
        return ("a face icon (data-gate=\"icon\")" if gate_icon else "a round box clipping a picture"), attr(kid, "src") or ""
    return None


def pictures_in(code, text, f, depth=0, seen=frozenset()):
    """the picture files an expression names: its literals, and those of the video's constants and helpers it names (ICONS.cup, ICON_A,
    I('x.jpg'), a template `e_ic_${n}.png`)"""
    out = set(PIC_LIT.findall(text))
    if depth < 3:
        for name in set(re.findall(r"\b([A-Za-z_]\w*)\b", text)) - JS_WORDS - seen:
            d = code.definition(name, f)
            if d and (name.isupper() or name[:1].islower() or name.startswith(("ICON", "PFP"))):
                out |= pictures_in(code, code.text_of(d), d[0], depth + 1, seen | {name})
    return out


MEDIA = PUBLIC                        # every composition's pictures (the per-video public dirs link into it)
ICON_PX = 96                          # a picture file this small (its longest side) is an interface icon (those are ~60 px)
_SIZES, _INDEX = {}, {}


def pic_px(name):
    """the longest side of a picture file the code names (looked up under MEDIA by its path, else by its name in the video folders'
    img/), or None"""
    name = name.replace("\\", "/")
    if name in _SIZES:
        return _SIZES[name]
    p = MEDIA / name
    if not p.is_file():
        if not _INDEX:
            for d in MEDIA.glob("*/img"):
                for q in d.rglob("*"):
                    _INDEX.setdefault(q.name, q)
        p = _INDEX.get(Path(name).name)
    px = None
    if p and p.is_file():
        try:
            from PIL import Image
            with Image.open(p) as im:
                px = max(im.size)
        except Exception:  # noqa: BLE001
            px = None
    _SIZES[name] = px
    return px


def verdict(pics):
    """'crop' when any picture is a screenshot's crop (a face, a chip, any picture file), 'ui' when all are the source's own interface
    (by name: UI_NAMES; or a file under ICON_PX: a 58-px interface icon saved under any name), emoji or logos, None when none is named"""
    if not pics:
        return None

    def ui(p):
        if UI_NAMES.search(Path(p).name):
            return True
        px = pic_px(p) if "${" not in p else None
        return px is not None and px <= ICON_PX
    return "ui" if all(ui(p) for p in pics) else "crop"


def params_of(text):
    """a component's props as it destructures them: ({d, cup, chart}) => ..."""
    m = re.search(r"=\s*\(\s*\{([^}]*)\}", text)
    return {re.split(r"[=:\s]", x.strip())[0] for x in m.group(1).split(",") if x.strip()} if m else set()


KIT_ROUND = {"Still": {"icons": [("kit3 Still's icons={...} (round profile pictures)", None)]}}   # the kit's pieces that crop pictures given
COND = re.compile(r"\b([A-Za-z_]\w*)\s*===\s*['\"]([\w-]+)['\"]")


def condition(text, pos):
    """the switch a round crop is drawn under, when it is drawn only for one value of a prop or a data field: the nearest `x === 'v'`
    before it whose branch still holds it (`{mode === 'grid' ? <Face/> : null}`, `if (L.k === 'face') { ... }`): (x, v) or None"""
    for m in reversed(list(COND.finditer(text, 0, pos))):
        j = m.end()
        while j < pos and text[j] in " \t\r\n":
            j += 1
        if j < pos and text[j] == ")":                              # an if: its block follows
            j += 1
            while j < pos and text[j] in " \t\r\n":
                j += 1
            if j >= pos or text[j] != "{":
                continue
            j += 1
        depth, k = 0, j
        while k < pos:
            c = text[k]
            if c in "'\"":
                k = _skip_string(text, k)
                continue
            depth += c in "([{"
            depth -= c in ")]}"
            if depth < 0:
                break
            k += 1
        if depth >= 0 and k >= pos:
            return (m.group(1), m.group(2))
    return None


def entry_text(code, key):
    """the text of an object entry keyed `key` anywhere in the video's code (CONFIG.chart_zoom: the layers a shot's id selects)"""
    cache = code.__dict__.setdefault("_entries", {})
    if key not in cache:
        cache[key] = _entry_text(code, key)
    return cache[key]


def _entry_text(code, key):
    out = []
    for f in code.files:
        c = code.clean[f]
        for m in re.finditer(rf"^([ \t]*)['\"]?{re.escape(key)}['\"]?[ \t]*:", c, re.M):
            ind = len(m.group(1))
            nxt = re.compile(rf"^[ \t]{{0,{ind}}}['\"]?[\w$]+['\"]?[ \t]*:|^[ \t]{{0,{max(0, ind - 1)}}}[}}\]]", re.M).search(c, m.end())
            out.append(c[m.start():(nxt.start() if nxt else m.end() + 4000)][:6000])
    return "\n".join(out)


def met(need, text):
    """is every switch (x, v) of a need set to v in this text (`x="v"`, `x={'v'}`, `x: 'v'`)"""
    return all(re.search(rf"(?<![\w$]){re.escape(x)}\s*[:=]\s*\{{?\s*['\"]{re.escape(v)}['\"]", text) for x, v in (need or ()))


class Round:
    """which components of the video's code draw a round crop of a picture: {definition: {"crop": [(why, switch)], "props": {prop:
    [(why, switch)]}}}. "props": the circle shows a picture the component is given (the shot's own value decides: an interface icon is no crop);
    a switch (x, v): only when x is v (a chart's layers of kind 'face', a search view's mode 'grid'), decided by the shot's own attributes or
    the entry they select (`id="chart_zoom"` -> CONFIG.chart_zoom)"""

    def __init__(self, code):
        self.code, self.info, self.uses = code, {}, {}
        for name, ds in code.defs.items():
            if not name[:1].isupper():
                continue
            for d in ds:
                f, a, _ = d
                text = code.text_of(d)
                nodes, _ = scan_js(text + ")" * 8, 0)
                for x in walk(nodes):
                    x.file = f
                els = list(walk(nodes))
                params = params_of(text)
                info = {"crop": [], "props": defaultdict(list)}
                for e in els:
                    rh = round_how(e)
                    if not rh:
                        continue
                    how, expr = rh
                    where = f"{how} at {code.rel(f)}:{code.lineno(f, a + e.pos)}"
                    cond = condition(text, e.pos)
                    need = (cond,) if cond else ()
                    v = verdict(pictures_in(code, expr, f))
                    ids = set(re.findall(r"\b([A-Za-z_]\w*)\b", expr)) - JS_WORDS
                    props = {x for x in ids if x in params}
                    for x in ids - params:                           # a loop's item: the list it runs over (`tiles.map((c, i) =>`)
                        loop = [mm.group(1) for mm in re.finditer(rf"\b(\w+)\.map\(\s*\(?\s*{re.escape(x)}\b", text[:e.pos])]
                        if loop and loop[-1] in params:
                            props.add(loop[-1])
                    if "face icon" in how or v == "crop" or (v is None and not props):
                        info["crop"].append((where, need))
                    elif v is None:
                        for p in props:
                            info["props"][p].append((where, need))
                self.info[d] = info
                self.uses[d] = [(e, code.definition(base(e.name), f)) for e in els if e.name[:1].isupper()]
        grew = True
        while grew:                                                  # through the components each one uses, prop by prop
            grew = False
            for d, us in self.uses.items():
                info, text = self.info[d], code.text_of(d)
                params = params_of(text)
                for e, d2 in us:
                    sub = self.info.get(d2) if d2 else ({"crop": [], "props": KIT_ROUND[base(e.name)]} if base(e.name) in KIT_ROUND else None)
                    if not sub or d2 == d:
                        continue
                    nm = base(e.name)
                    site = condition(text, e.pos)                    # the use itself under a switch (`{mode === 'two' ? <Round/> : null}`)
                    for why, need in sub["crop"]:
                        nd = self._carry(e, need)
                        if nd == "off":
                            continue
                        item = (f"through {nm} ({why})", ((site,) if site else ()) + nd)
                        if item not in info["crop"]:
                            info["crop"].append(item)
                            grew = True
                    for p, items in list(sub["props"].items()):
                        val = attr(e, p)
                        if val is None:
                            continue
                        v = verdict(pictures_in(code, val, d[0]))
                        mine = (set(re.findall(r"\b([A-Za-z_]\w*)\b", val)) - JS_WORDS) & params
                        for why, need in items:
                            nd = self._carry(e, need)
                            if nd == "off" or v == "ui":
                                continue
                            item = (f"through {nm}'s {p} ({why})", ((site,) if site else ()) + nd)
                            if v == "crop" or not mine:
                                if item not in info["crop"]:
                                    info["crop"].append(item)
                                    grew = True
                            else:
                                for q in mine:
                                    if item not in info["props"][q]:
                                        info["props"][q].append(item)
                                        grew = True

    @staticmethod
    def _carry(e, need):
        """a sub-component's switches seen from the element that uses it: one set by a literal there is met (dropped) or not (the whole
        crop is "off"); the rest are carried up"""
        out = []
        for x, v in need or ():
            if re.search(rf"(?<![\w$]){re.escape(x)}\s*=\s*\{{?\s*['\"]", e.attrs):
                if not met(((x, v),), e.attrs):
                    return "off"
            else:
                out.append((x, v))
        return tuple(out)

    def shot(self, els):
        """why a shot's elements draw a round crop of a picture (the first reason), or None"""
        code = self.code
        for e in els:
            n = base(e.name)
            rh = round_how(e)
            if rh and ("face icon" in rh[0] or verdict(pictures_in(code, rh[1], e.file)) != "ui"):
                return f"{rh[0]} in the shot's own code"
            d = code.definition(n, e.file) if n[:1].isupper() else None
            info = self.info.get(d) if d else ({"crop": [], "props": KIT_ROUND[n]} if n in KIT_ROUND else None)
            if not info:
                continue
            data = []

            def ok(need):
                if not need:
                    return True
                if not data:                                        # the shot's own attributes and the entries they name
                    data.append(e.attrs + "\n" + "\n".join(entry_text(code, k) for k in set(re.findall(r"['\"]([\w-]{3,})['\"]", e.attrs))))
                return met(need, data[0])

            def said(need):
                return "".join(f" (its {x} '{v}')" for x, v in need or ())
            for why, need in info["crop"]:
                if ok(need):
                    return f"{n}: {why}{said(need)}"
            for p, items in info["props"].items():
                val = attr(e, p)
                if val is None or re.fullmatch(r"\{\s*(?:\[\s*\]|undefined)\s*\}", val):
                    continue
                if verdict(pictures_in(code, val, e.file)) == "ui":
                    continue
                for why, need in items:
                    if ok(need):
                        return f"{n}'s {p}: {why}{said(need)}"
        return None


# ================================================================================================================ the main picture
def has_clip_prop(el):
    return bool(re.search(r"\b(?:clip|clips|n)=", el.attrs)) or any(isinstance(x, El) and base(x.name) in CLIPS for x in walk(el.props))


LABELS = re.compile(r"Label|Tag|Name|Credit|Caption|Corner|Stamp|Title|Kicker|Lit|Mark|Subs")


def inside_map(text, pos):
    """is this position inside the callback of a `.map(` (an element drawn once per item: a row, a grid)"""
    for m in reversed(list(re.finditer(r"\.map\(", text[:pos]))):
        depth, k = 0, m.end()
        while k < pos:
            c = text[k]
            if c in "'\"":
                k = _skip_string(text, k)
                continue
            depth += c in "([{"
            depth -= c in ")]}"
            if depth < 0:
                break
            k += 1
        if k >= pos and depth >= 0:
            return True
    return False


def picture_pieces(code):
    """{definition: 'clip' | 'still'} for the video's own picture pieces, by what they draw: exactly one picture (a clip, a still or
    another picture piece), not once per item of a list, with only labels, credits and wrappers beside it and at most one box (FtA,
    FtB, StA, Calm, FootC, ZoomClip, Bite). A split screen (two pictures), a row of emoji or a graphic with its own parts is
    no picture piece: it is a device"""
    out, todo = {}, []
    for name, ds in code.defs.items():
        if name[:1].isupper():
            todo += [(name, d) for d in ds]
    fill = re.compile(r"width:\s*['\"]100%['\"].*height:\s*['\"]100%['\"]|height:\s*['\"]100%['\"].*width:\s*['\"]100%['\"]", re.S)
    grew = True
    while grew:
        grew = False
        for name, d in todo:
            if d in out:
                continue
            text = code.text_of(d)
            nodes, _ = scan_js(text + ")" * 8, 0)
            parent = {}

            def link(xs, p):
                for x in xs:
                    if isinstance(x, El):
                        parent[id(x)] = p
                        link(x.kids, x)
                        link(x.props, x)
            link(nodes, None)
            els = list(walk(nodes))
            if any(round_radius(e.attrs) or "data-gate" in e.attrs and "icon" in e.attrs for e in els):
                continue                                            # a circle is never a plain picture
            pics, other, boxes = [], False, 0
            for e in els:
                n = base(e.name)
                if n in ("Img", "img"):                             # a raw picture: a piece only when it fills an AbsoluteFill
                    p = parent.get(id(e))
                    if fill.search(e.attrs) and (p is None or base(p.name) in ("AbsoluteFill", "")):
                        pics.append(("still", e))
                    else:
                        other = True
                    continue
                if e.name[:1].islower():
                    boxes += 1
                    continue
                sub = code.definition(n, d[0])
                if n in CLIPS or (sub and out.get(sub) == "clip"):
                    pics.append(("clip", e))
                elif n in STILLS or (sub and out.get(sub) == "still"):
                    pics.append(("still", e))
                elif n in PICTURE_PIECES:
                    pics.append(("clip" if has_clip_prop(e) else "still", e))
                elif not (n in STRUCT or n in WRAPS or n in OVERLAYS or LABELS.search(n)):
                    other = True
            if len(pics) == 1 and not other and boxes <= 1 and not inside_map(text, pics[0][1].pos):
                out[d] = pics[0][0]
                grew = True
    return out


def main_of(nodes, code=None):
    """(kind, component) of a forest's main picture: ('clip'|'still', name) or ('device', name), or None. Remotion's own Loop or Series
    is structure; a component of the same name in the video's code (a Loop diagram) is a graphic"""
    for e in nodes:
        if not isinstance(e, El):
            continue
        n = base(e.name)
        if e.name[:1].islower() and n != "img":                    # a DOM box: what it holds
            m = main_of(e.kids, code)
            if m:
                return m
            continue
        if (n in STRUCT and not (code and e.file and code.definition(n, e.file))) or n in WRAPS:
            m = main_of(e.kids, code)
            if m:
                return m
            continue
        if n in OVERLAYS:                                           # a ground or a label: what it holds, if anything (Stage with a Row)
            m = main_of(e.kids, code)
            if m:
                return m
            continue
        if n in CLIPS:
            return ("clip", n)
        if n in STILLS:
            return ("still", n)
        if n in PICTURE_PIECES:
            return ("clip" if has_clip_prop(e) else "still", n)
        piece = code.pieces.get(code.definition(n, e.file)) if code is not None and getattr(code, "pieces", None) else None
        if piece:                                                   # the video's own picture piece (FtA, Calm)
            return (piece, n)
        m = main_of(e.kids, code)                                   # a graphic holding the picture as its children is a wrapper
        if m:
            return m
        return ("device", n)
    return None


# ======================================================================================================================= the words
def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "").replace("'", ""))


class Words:
    """the anchors' timeline as the timing helper reads it: words.json (the whole script's placeholder in ph/ while the voice covers part of it),
    every word after a bite moved by the bite (inserts*.json with an `at`, BITE_TOL 0.25 s before it)"""

    def __init__(self, src, beats_needed=()):
        src = Path(src)
        wp, pp = src / "words.json", src / "ph" / "words.json"
        words = json.loads(wp.read_text(encoding="utf-8")) if wp.exists() else []
        have = {x["beat"] for x in words}
        self.placeholder = bool(pp.exists() and beats_needed and not set(beats_needed) <= have)
        if self.placeholder:
            words = json.loads(pp.read_text(encoding="utf-8"))
        ins = []
        if not self.placeholder:
            for p in sorted(src.glob("inserts*.json")):
                try:
                    ins += [x for x in json.loads(p.read_text(encoding="utf-8")) if isinstance(x.get("at"), (int, float))]
                except (ValueError, AttributeError):
                    pass
        self.bites = ins

        def shifted(t):
            return t + sum(x["dur"] for x in ins if t >= x["at"] - 0.25)
        self.words = [{**x, "start": shifted(x["start"]), "end": shifted(x["end"])} for x in words]
        self.by_beat = defaultdict(list)
        for i, x in enumerate(self.words):
            self.by_beat[x["beat"]].append(i)

    def w(self, beat, phrase, off=0.0, nth=0):
        toks = [t for t in (norm(p) for p in phrase.split()) if t]
        seen = 0
        for i in self.by_beat.get(beat, []):
            if all(i + k < len(self.words) and self.words[i + k]["beat"] == beat and norm(self.words[i + k]["w"]) == tk for k, tk in enumerate(toks)):
                if seen == nth:
                    return self.words[i]["start"] + off
                seen += 1
        return self.b0(beat)

    def we(self, beat, phrase, off=0.0, nth=0):
        st = self.w(beat, phrase, 0, nth)
        toks = [t for t in (norm(p) for p in phrase.split()) if t]
        i = next((k for k in self.by_beat.get(beat, []) if abs(self.words[k]["start"] - st) < 1e-6), None)
        if i is None or i + len(toks) - 1 >= len(self.words):
            return st + off
        return self.words[i + len(toks) - 1]["end"] + off

    def b0(self, beat, off=0.0):
        ix = self.by_beat.get(beat)
        return self.words[ix[0]]["start"] + off if ix else None

    def bend(self, beat):
        ix = self.by_beat.get(beat)
        return self.words[ix[-1]]["end"] if ix else None

    def said(self, t0, t1):
        """the sentences said under a shot (from t0 to t1), whole"""
        if t0 is None:
            return ""
        idx = [i for i, x in enumerate(self.words) if t0 - 0.05 <= x["start"] < max(t1, t0 + 0.3)]
        if not idx:
            idx = [min(range(len(self.words)), key=lambda i: abs(self.words[i]["start"] - t0))] if self.words else []
        if not idx:
            return ""
        a, b = idx[0], idx[-1]
        while a > 0 and not re.search(r"[.?!]$", self.words[a - 1]["w"]) and self.words[a - 1]["beat"] == self.words[a]["beat"]:
            a -= 1
        while b + 1 < len(self.words) and not re.search(r"[.?!]$", self.words[b]["w"]) and self.words[b + 1]["beat"] == self.words[b]["beat"]:
            b += 1
        return " ".join(x["w"] for x in self.words[a:b + 1])


ANCHOR = re.compile(r"""\b(w|we|b0|bEnd)\(\s*['"](S\d+[a-z]?)['"](?:\s*,\s*(['"])(.*?)\3)?(?:\s*,\s*(-?\d+(?:\.\d+)?))?(?:\s*,\s*(\d+))?\s*\)"""
                    r"""(\s*[-+]\s*\d+(?:\.\d+)?)?""")


def anchor_time(words, text):
    """the time of a shot's first argument (its first w/we/b0 call and a plain offset after it), and its beat"""
    m = ANCHOR.search(text)
    if not m:
        return None, None
    fn, beat, _, phrase, off, nth, tail = m.groups()
    off = float(off) if off else 0.0
    if fn == "b0":
        t = words.b0(beat, off)
    elif fn == "bEnd":
        t = words.bend(beat)
    elif fn == "we":
        t = words.we(beat, phrase or "", off, int(nth or 0))
    else:
        t = words.w(beat, phrase or "", off, int(nth or 0))
    if t is not None and tail:
        t += float(tail.replace(" ", ""))
    return t, beat


# ===================================================================================================================== the shots
def first_arg(s):
    depth, q = 0, None
    for i, c in enumerate(s):
        if q:
            q = None if c == q else q
        elif c in "'\"`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return s[:i]
            depth -= 1
        elif c == "," and depth == 0:
            return s[:i]
    return s


def _comment_above(lines, i):
    k, com = i - 1, []
    while k >= 0 and lines[k].strip().startswith("//"):
        com.insert(0, lines[k].strip().lstrip("/ ").strip())
        k -= 1
    return com


def _map_count(lines, i):
    """`...[a, b, c].map((n, k) => { ... return shot(...) })`: the list's length and the line it starts on, else (1, None)"""
    for k in range(i - 1, max(-1, i - 6), -1):
        m = re.match(r"^\s*\.\.\.\s*\[(.*)\]\s*\.map\(", lines[k])
        if m:
            depth, parts = 0, 1
            for c in m.group(1):
                depth += c in "([{"
                depth -= c in ")]}"
                parts += c == "," and depth == 0
            return parts, k
    return 1, None


def film_files(code, module):
    """the code files the composition is built from: its module and every file of the video's code it imports, all the way down
    (another composition in the same folder, a prototype beside the film, is not the film)"""
    start = code.src / module if module else None
    if not start or start not in code.clean:
        return [f for f in code.files if f.suffix == ".tsx"]
    seen, todo = set(), [start]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        todo += [t for t, _ in code.imports.get(f, {}).values() if t is not None and t not in seen]
    return [f for f in code.files if f in seen and f.suffix == ".tsx"]


def shots(code, words=None, module=None):
    """every shot entry: {file, line, t, beat, main: (kind, name), round: why or None, device: reason or None, n: shots it makes}"""
    rnd = Round(code)
    code.pieces = picture_pieces(code)
    out = []
    for f in film_files(code, module):
        lines, clean = code.text[f].splitlines(), code.clean[f].splitlines()
        starts = [0]
        for ln in clean:
            starts.append(starts[-1] + len(ln) + 1)
        whole = code.clean[f]
        idx = [i for i, ln in enumerate(clean) if ENTRY.search(ln) and not ln.lstrip().startswith(("const ", "export const ", "function "))
               and not (not re.match(r"^\s*(?:return\s+)?(?:shot|ft2?|page|parts)\(", ln)
                        and in_attribute(whole, starts[i] + AT_EL.search(ln).start()))]
        for n, i in enumerate(idx):
            j = idx[n + 1] if n + 1 < len(idx) else min(len(lines), i + 60)
            body = "\n".join(clean[i:j])
            m = re.search(r"(?:shot|ft2?|page|parts)\(|\{at:\s*", body)
            args = body[m.end():] if m else body
            # from the helper's own name: a shot-making helper (`ft(at, 'clip', credit)` = shot(at, <FtC/>)) is inlined too
            nodes, _ = scan_js((body[m.start():] if m and not body[m.start()] == "{" else args) + ")" * 8, 0)
            forest = expand(code, nodes, f)
            main = main_of(forest, code) or ("?", "?")
            emoji = emoji_graphic(code, f, body, main)
            why = rnd.shot(list(walk_own(forest)))
            com = _comment_above(lines, i)
            cnt, mline = _map_count(lines, i)
            if mline is not None and not com:
                com = _comment_above(lines, mline)
            dev = next((c.split(":", 1)[1].strip() for c in com if c.lower().startswith("device:")), None)
            t, beat = anchor_time(words, first_arg(args)) if words else (None, None)
            if t is None and words:
                t, beat = anchor_time(words, body)
            out.append({"file": code.rel(f), "line": i + 1, "t": t, "beat": beat, "main": main, "round": why, "device": dev, "n": cnt,
                        "anchor": lines[i].strip()[:100], "emoji": emoji})
            # a run of pieces inside the shot (`<Run pieces={[{at: 0, el: (L) => <EmojiRow .../>}, {at: p, img: ...}]} />`): each piece
            # that is an element of its own is an appearance of its own (its time the shot's, in order), with the comment above it
            for k in range(i, j):
                for pm in AT_EL.finditer(clean[k]):
                    if not in_attribute(whole, starts[k] + pm.start()):
                        continue
                    sub = "\n".join(clean[k:j])[pm.start():]
                    pn, _ = scan_js(sub[1:] + ")" * 8, 0)        # the piece object's inside, up to its closing brace
                    pf = expand(code, pn, f)
                    pmain = main_of(pf, code)
                    if not pmain:
                        continue
                    pcom = _comment_above(lines, k) if pm.start() <= len(clean[k]) - len(clean[k].lstrip()) else []
                    out.append({"file": code.rel(f), "line": k + 1, "t": None if t is None else t + 1e-4 * (k - i + 1), "beat": beat,
                                "main": pmain, "round": rnd.shot(list(walk(pf))), "n": 1, "anchor": lines[i].strip()[:100], "piece": True,
                                "emoji": emoji_graphic(code, f, sub[:4000], pmain),
                                "device": next((c.split(":", 1)[1].strip() for c in pcom if c.lower().startswith("device:")), None) or dev})
    # film order: by time (code order where no time is known, kept after the shot before it)
    last = 0.0
    for s in out:
        if s["t"] is None:
            s["t"] = last
        last = s["t"]
    out.sort(key=lambda s: s["t"])
    return out


def device_key(name):
    """one device under its range copies' names: a trailing range letter or number goes (RecA, RecB, RecC are one card;
    ChartB the chart), as the audit's names drop the bundler's digits"""
    return re.sub(r"(?<=[a-z])[A-F]$", "", re.sub(r"(?<=[A-Za-z])\d+$", "", name)) or name


def runs_of(shs):
    """appearances: runs of consecutive shots with the same main picture"""
    runs = []
    for s in shs:
        if runs and (runs[-1][0]["main"][0], device_key(runs[-1][0]["main"][1])) == (s["main"][0], device_key(s["main"][1])):
            runs[-1].append(s)
        else:
            runs.append([s])
    return runs


def emoji_graphic(code, f, text, main):
    """a shot that draws emoji pictures (emoji_*.png), named in the shot's own text or in its main component's definition, whatever
    the main picture's kind (a Scene, a soft real ground with emoji props, reads as a picture piece; an emoji floating over a clip is the
    same pattern)"""
    try:
        if any("emoji_" in p for p in pictures_in(code, text, f)):
            return True
        d = code.definition(main[1], f)
        return bool(d and any("emoji_" in p for p in pictures_in(code, code.text_of(d), d[0])))
    except Exception:
        return False


EMOJI_DEVICE = "EmojiGraphic"


def devices(shs):
    """{device: [appearances]} for the graphic components among the shots' main pictures; every graphic built with emoji pictures
    counts as one device, EmojiGraphic, whatever its component (emoji-with-label slides on dark or blurred grounds spread under a dozen
    component names: counted as one device, they show as the one habit they are)"""
    by = defaultdict(list)
    for r in runs_of(shs):
        if any(s.get("emoji") for s in r):
            by[EMOJI_DEVICE].append(r)
        elif r[0]["main"][0] == "device":
            by[device_key(r[0]["main"][1])].append(r)
    return by


def dev_name(key, rs):
    names = sorted({s["main"][1] for r in rs for s in r})
    return key if names == [key] else f"{key} ({', '.join(names)})"


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}" if t is not None else "?"


def check(code, words, cap=CAP, leads=LEADS, module=None):
    shs = shots(code, words, module)
    flags = []
    for k, s in enumerate(shs):
        s["end"] = shs[k + 1]["t"] if k + 1 < len(shs) else s["t"] + 3.0
    for dev, rs in sorted(devices(shs).items()):
        free = [r for r in rs if not any(s["device"] for s in r)]
        if len(free) > cap:
            at = free[cap][0]
            listing = ", ".join(f"{mmss(r[0]['t'])} ({r[0]['file']}:{r[0]['line']}{f', {len(r)} shots' if len(r) > 1 else ''})" for r in free[:40])
            flags.append({"check": "DEVICE_SPREAD", "key": dev, "t": at["t"], "to": free[-1][-1]["end"],
                          "what": f"{dev_name(dev, rs)} is the main picture of {sum(len(r) for r in rs)} shots in {len(rs)} appearances, {len(free)} of them without a "
                                  f"`// device:` reason (more than {cap}): {listing}{' ...' if len(free) > 40 else ''}. A device must not become the "
                                  f"film's default: rebuild appearances as the clip that shows the words or another idea, or write "
                                  f"`// device: <why this line needs it>` above a shot that must be this device"
                                  + (". Graphics built of emoji (an emoji with a label on a dark or blurred ground, a row or chain of them) read "
                                     "as a slide deck of loose pictures, not professional digital animation; an emoji belongs inside a piece "
                                     "built from real material, the line's own footage comes first" if dev == EMOJI_DEVICE else "")})
    lead_res = [re.compile(rf"\b{re.escape(x.lower())}", re.I) for x in leads]
    bad = []
    for s in shs:
        if not s["round"]:
            continue
        said = words.said(s["t"], s["end"]) if words else ""
        portrait = bool(s["device"]) and s["device"].lower().startswith("portrait")
        # a lead named: the approved portraits of the leads serve every portrait of them in the film, so one lead's portrait (a marker
        # on a diagram) passes where the words name a lead; the reason line is the builder's. The shot's whole beat counts, so a "them"
        # whose names the beat already said passes ("Both of them trained for years ... and only one of them made the team")
        beat_said = " ".join(words.words[i]["w"] for i in words.by_beat.get(s.get("beat"), [])) if words else ""
        both = any(r.search(said) or r.search(beat_said) for r in lead_res)
        # `// device: passed <the creator's words>`: a piece the creator passed as it is
        passed = bool(s["device"]) and s["device"].lower().startswith("passed")
        s["said"], s["exempt"] = said, (portrait and both) or passed
        if not s["exempt"]:
            bad.append(s)
    for r in runs_of(bad):
        s = r[0]
        why_not = ("its `// device: portrait` line is there, but the words under it name neither lead"
                   if s["device"] and s["device"].lower().startswith("portrait") else
                   "allowed only where the words name the people it shows (video.toml [gate] leads) and the shot says `// device: portrait <why>`")
        m = ANCHOR.search(s["anchor"])
        flags.append({"check": "ROUND_CROP", "key": f"{s['file']}:{s['line']}", "t": s["t"], "to": r[-1]["end"],
                      "what": f"{s['file']}:{s['line']} ({s['main'][1]}{f', {len(r)} shots' if len(r) > 1 else ''}"
                              f"{', ' + m.group(0) if m else ''}) draws a round crop of a picture as the shot's idea: {s['round']}. Circles of "
                              f"cropped screenshots are out (they read as filler and spread into a template): show the clip that shows it, "
                              f"real cut-outs or a built demonstration; {why_not}"})
    flags += stamp_flags(code, shs)
    return shs, flags


# STAMP_PHRASE (left alone, stamps spread from numbers to phrases: "YOUR CHOICES COUNT", "BUILT FOR REPLAYS", "WHAT COMES FIRST?"): the
# house stamp is a passage's headline claim, a number said as a statement ("50 designs" said as a statement gets its stamp), a
# multiplier or a record ("3x FASTER"); a phrase the voice just says is text repeating the voice (standard/LONG_FORM.md: no text that
# repeats the voice), a question is a text card.
STAMP_TAG = re.compile(r"<(Stamp\w*)\b((?:[^>{}]|\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})*)>", re.S)
STAMP_OBJ = re.compile(r"\bstamp\s*:\s*\{((?:[^{}]|\{[^{}]*\})*)\}", re.S)
CLAIM = re.compile(r"\d|\b(?:hundreds?|thousands?|millions?|billions?|dozens?|double|twice|triple|half|tenth|first|biggest|largest|most|"
                   r"record|every|all|no\s+one|nothing|never\s+before)\b", re.I)


def stamp_flags(code, shs):
    """every stamp with literal words in the film's code (a kit's stamp element, a shot's `stamp: {...}` data) whose words carry no number,
    multiplier or record, or ask a question, without `// stamp: <why it is the passage's headline claim>` in the 4 lines above it"""
    try:
        from codefiles import code_files
        film = set(code_files(code.src, (".ts", ".tsx")))
    except Exception:
        film = set(code.files)
    out = []
    for f in code.files:
        if f not in film:
            continue
        raw, clean = code.text[f], code.clean[f]
        for rx in (STAMP_TAG, STAMP_OBJ):
            for m in rx.finditer(clean):
                body = m.group(2) if rx is STAMP_TAG else m.group(1)
                lead = re.search(r"""\blead\s*[:=]\s*\{?\s*(['"`])([^'"`]*)\1""", body)
                text = re.search(r"""\btext\s*[:=]\s*\{?\s*(['"`])([^'"`]*)\1""", body)
                words = " ".join(x.group(2) for x in (lead, text) if x).strip()
                if not words:
                    continue                                            # a kit passing its data through (text={p.stamp.text})
                line = code.lineno(f, m.start())
                above = raw.splitlines()[max(0, line - 5):line]
                if any(re.search(r"//\s*stamp\s*:", x, re.I) for x in above):
                    continue
                question = "?" in words
                if CLAIM.search(words) and not question:
                    continue
                shot = None
                for s in shs:
                    if s["file"] == code.rel(f) and s["line"] <= line and s["t"] is not None:
                        shot = s
                t = shot["t"] if shot else None
                out.append({"check": "STAMP_PHRASE", "key": f"{code.rel(f)}:{words}", "t": t, "to": (t or 0) + 2.0,
                            "what": f"{code.rel(f)}:{line} stamps \"{words}\": "
                                    f"{'a question is a text card' if question else 'no number, multiplier or record in it'}. The house stamp "
                                    f"is a passage's headline claim (a number said as a statement, a multiplier, a record); a phrase the "
                                    f"voice just says is text repeating the voice: the picture shows it instead, or `// stamp: <why it is the "
                                    f"passage's headline claim>` above it"})
    return out


def video_words(v, code):
    beats = set()
    for f in code.files:
        beats |= set(re.findall(r"\b(?:w|we|b0|bEnd)\(\s*['\"](S\d+[a-z]?)['\"]", code.clean[f]))
    return Words(code.src, beats)


def gate_flags(v):
    """for gate.py (B23 DEVICES): the flags as the gate's own dicts (at = frame)"""
    code = Code(HERE / "src" / v.src)
    words = video_words(v, code)
    leads = tuple((v.section("gate") or {}).get("leads", LEADS)) if hasattr(v, "section") else LEADS
    _, flags = check(code, words, leads=leads, module=getattr(v, "module", None))
    out = []
    for fl in flags:
        at = int(round((fl["t"] or 0) * FPS))
        out.append({"check": fl["check"], "key": fl["key"], "at": at, "to": int(round((fl.get("to") or fl["t"] or 0) * FPS)), "what": fl["what"]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--src", help="the composition's code folder (default: video.toml's src under tools/motion/src)")
    ap.add_argument("--list", action="store_true", help="every shot with its time, main picture and place in the code")
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--json", help="write the shots and the flags here")
    a = ap.parse_args()
    sys.path.insert(0, str(TOOLS / "pipeline"))
    from common import Video, find_video   # noqa: E402
    v = Video(find_video(a.video))
    code = Code(Path(a.src) if a.src else HERE / "src" / v.src)
    words = video_words(v, code)
    leads = tuple((v.section("gate") or {}).get("leads", LEADS))
    shs, flags = check(code, words, a.cap, leads, v.module)
    if a.list:
        for s in shs:
            print(f"  {mmss(s['t']):>9s}  {s['main'][0]:6s} {s['main'][1]:22s} {s['file']}:{s['line']}{' x' + str(s['n']) if s['n'] > 1 else ''}"
                  f"{'  ROUND: ' + s['round'][:90] if s['round'] else ''}{'  device: ' + s['device'][:60] if s['device'] else ''}")
    kinds = defaultdict(int)
    for s in shs:
        kinds[s["main"][0]] += s["n"]
    print(f"{v.slug} ({code.src}): {sum(s['n'] for s in shs)} shots from {len(shs)} code entries in {len(code.files)} files"
          f"{' (the placeholder words)' if words.placeholder else ''}: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items(), key=lambda x: -x[1])))
    print("devices by appearances (shots; appearances with a `// device:` reason):")
    for dev, rs in sorted(devices(shs).items(), key=lambda x: -len(x[1])):
        print(f"  {len(rs):3d}  {dev_name(dev, rs):30s} ({sum(len(r) for r in rs)} shots; {sum(1 for r in rs if any(s['device'] for s in r))} with a reason)"
              f"{'  ROUND' if any(s['round'] for r in rs for s in r) else ''}")
    rs = [s for s in shs if s["round"]]
    print(f"round crops: {len(rs)} shots ({sum(1 for s in rs if s.get('exempt'))} portraits of the leads with `// device: portrait`, or passed pieces)")
    for fl in flags:
        print(f"{fl['check']:14s} {mmss(fl['t'])}  {fl['what']}")
    print(f"{len(flags)} flag(s)")
    if a.json:
        Path(a.json).write_text(json.dumps({"shots": shs, "flags": flags}, indent=1, default=str), encoding="utf-8")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())


# PROOF (scratch copies, the builders' files untouched):
#  A full long film's code (1,054 shots from 1,049 code entries; 1,048 of them start within one frame of a shot of the audit's shots
#    json: the anchors are read as the timing helper reads them): 71 flags. ROUND_CROP 67 (89 shots), every circle a hand-made review of
#    the film had noted among them. Against a hand-made read of every shot: 72 of its 80 round-crop rows flagged; the 8 left are not
#    round (square or rounded tiles, cards, an interface icon); the 10 flags outside its rows are shots the review itself named.
#    Passed by design: an interface's round status icons (a 58-px icon among them), a diagram's shots without a 'face' layer, a view
#    outside the modes that draw circles. DEVICE_SPREAD 4 (a diagram 26 appearances, a lens 11, a profile 7, a lift 7).
#  The reasons, on a copy: `// device: portrait ...` above two shots whose words name both leads passes both; above one whose words
#    name neither it stays flagged; `// device: ...` above a device's 10 appearances takes its DEVICE_SPREAD out.
#  Another range layout ({at, el} entries, ft()/st() helpers, FtA/StA pieces): 237 shots, 1 flag: Rec (RecA, RecB, RecC), its card,
#    31 appearances.
