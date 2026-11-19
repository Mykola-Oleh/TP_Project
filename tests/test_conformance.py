import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_black_box_conformance():
    result = subprocess.run([sys.executable, str(ROOT / "conformance/run_suite.py")],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

def test_conformance_schema():
    for path in (ROOT / "conformance").glob("*.json"):
        case = json.loads(path.read_text(encoding="utf-8"))
        assert {"id", "source", "mode", "initial", "expect"} <= case.keys()
