import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chapters  # noqa: E402

WORDS = [{"w": "a", "start": 0.01, "beat": "S001"}, {"w": "b", "start": 28.9, "beat": "S004"}, {"w": "c", "start": 135.6, "beat": "S010"},
         {"w": "d", "start": 140.0, "beat": "S011"}]


def test_times_are_first_word_minus_half_a_second_floored():
    spec = [{"title": "Intro"}, {"title": "The price", "beat": "S004"}, {"title": "Your setup", "beat": "S010"}]
    assert chapters.compute(spec, WORDS, 200.0) == [(0.0, "Intro"), (28.0, "The price"), (135.0, "Your setup")]


def test_refuses_what_youtube_refuses():
    with pytest.raises(SystemExit, match="10 s"):
        chapters.compute([{"title": "Intro"}, {"title": "A", "beat": "S010"}, {"title": "B", "beat": "S011"}], WORDS, 200.0)
    with pytest.raises(SystemExit, match="at least 3"):
        chapters.compute([{"title": "Intro"}, {"title": "A", "beat": "S004"}], WORDS, 200.0)
    with pytest.raises(SystemExit, match="not in the film"):
        chapters.compute([{"title": "Intro"}, {"title": "A", "beat": "S004"}, {"title": "B", "beat": "S099"}], WORDS, 200.0)


def test_writes_between_the_markers_keeping_the_indent(tmp_path):
    p = tmp_path / "post.md"
    p.write_text("x\n    <!-- chapters -->\n    0:00 old\n    1:00 old\n    <!-- /chapters -->\ny\n", encoding="utf-8")
    assert chapters.write_post(p, [(0.0, "Intro"), (28.0, "The price"), (3725.0, "Late")])
    assert p.read_text(encoding="utf-8") == "x\n    <!-- chapters -->\n    0:00 Intro\n    0:28 The price\n    1:02:05 Late\n    <!-- /chapters -->\ny\n"
