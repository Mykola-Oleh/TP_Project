"""CLI integration tests via actual subprocesses, not mocked function calls."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "sipl.cli", *map(str, args)],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def test_check_text():
    p = cli("check", "examples/power.sipl")
    assert p.returncode == 0 and p.stdout.strip() == "Syntax OK"


def test_check_json():
    p = cli("check", "examples/power.sipl", "--json")
    d = json.loads(p.stdout)
    assert p.returncode == 0 and d == {
        "schema_version": "1.0", "command": "check", "ok": True,
        "data": {"valid": True}, "error": None}


def test_parse_json():
    p = cli("parse", "examples/power.sipl", "--json")
    d = json.loads(p.stdout)
    assert p.returncode == 0 and d["data"]["ast"]["statements"]


def test_run_text_backward_compatible():
    p = cli("run", "examples/power.sipl", "--var", "X=2", "--var", "Y=5")
    assert p.returncode == 0 and json.loads(p.stdout)["state"]["R"] == 32


def test_run_json():
    p = cli("run", "examples/power.sipl", "--json", "--var", "X=2", "--var", "Y=5")
    d = json.loads(p.stdout)
    assert p.returncode == 0 and d["data"]["state"]["R"] == 32
    assert d["data"]["steps"] == 17


def test_trace_json():
    p = cli("trace", "examples/power.sipl", "--json", "--var", "X=2", "--var", "Y=5")
    d = json.loads(p.stdout)
    assert p.returncode == 0 and d["data"]["result"]["state"]["R"] == 32
    assert d["data"]["events"][-1]["event"] == "ExecutionFinished"


def test_syntax_error(tmp_path):
    file = tmp_path / "bad.sipl"
    file.write_text("begin X := end", encoding="utf-8")
    p = cli("check", file, "--json")
    d = json.loads(p.stdout)
    assert p.returncode == 3 and d["error"]["type"] == "SyntaxError"
    assert d["error"]["location"]["line"] == 1


def test_runtime_error(tmp_path):
    file = tmp_path / "bad.sipl"
    file.write_text("begin X := Y end", encoding="utf-8")
    p = cli("run", file, "--json")
    d = json.loads(p.stdout)
    assert p.returncode == 4 and d["error"]["type"] == "RuntimeError"
    assert d["error"]["location"]["line"] == 1


def test_missing_file():
    p = cli("check", "missing_file.sipl", "--json")
    assert p.returncode == 2 and json.loads(p.stdout)["error"]["type"] == "InputError"


def test_invalid_var():
    p = cli("run", "examples/power.sipl", "--var", "X=bad", "--json")
    assert p.returncode == 2 and json.loads(p.stdout)["error"]["type"] == "InputError"


def test_invalid_step_limit():
    p = cli("run", "examples/power.sipl", "--max-steps", "0", "--json")
    assert p.returncode == 2


def test_step_limit_error():
    p = cli("run", "examples/power.sipl", "--var", "X=2", "--var", "Y=5",
            "--max-steps", "1", "--json")
    assert p.returncode == 4 and json.loads(p.stdout)["error"]["type"] == "RuntimeError"


def test_text_error_to_stderr():
    p = cli("check", "missing_file.sipl")
    assert p.returncode == 2 and not p.stdout and p.stderr
