"""A crashing check is a flag, never a dead gate run (one check's crash must not lose every other check's results)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402


def test_crashed_flag_names_the_check_the_error_and_where():
    try:
        [][1]
    except Exception as e:  # noqa: BLE001
        fl = gate.crashed_flag("B2 fades", e)
    assert fl["check"] == "CHECK_CRASHED" and fl["key"] == "B2 fades"
    assert "IndexError" in fl["what"] and "test_gate_crash.py" in fl["what"]
    assert fl["at"] == 0 and fl["to"] == 0
