import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def matches(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and matches(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(
            matches(a, b) for a, b in zip(expected, actual))
    return expected == actual


def ast_shape(node):
    if isinstance(node, list):
        return [ast_shape(x) for x in node]
    if not isinstance(node, dict):
        return node
    keys = set(node) - {"span"}
    if "statements" in keys:
        typ = "Block"
    elif "then_branch" in keys:
        typ = "If"
    elif "body" in keys:
        typ = "While"
    elif "name" in keys and "value" in keys:
        typ = "Assign"
    elif "op" in keys and "left" in keys:
        typ = "Binary"
    elif "op" in keys and "operand" in keys:
        typ = "Unary"
    elif "name" in keys:
        typ = "Variable"
    elif "value" in keys:
        typ = "Number"
    else:
        typ = "Skip"
    return {"type": typ, **{k: ast_shape(v) for k, v in node.items() if k != "span"}}


def run_case(case, command):
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "input.sipl"
        source.write_text(case["source"], encoding="utf-8")
        mode = "parse" if case["mode"] == "ast" else "run"
        args = [*command, mode, str(source), "--json"]
        for key, value in case.get("initial", {}).items():
            args += ["--var", f"{key}={value}"]
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, f"invalid JSON response: {result.stdout!r}; stderr={result.stderr!r}"
    if case["mode"] == "error":
        expected = case["expect"]
        good = (result.returncode == expected["exit_code"] and response.get("ok") is False
                and response.get("error", {}).get("type") == expected["type"])
    elif case["mode"] == "ast":
        good = (result.returncode == 0 and response.get("ok") is True and
                matches(case["expect"]["shape"], ast_shape(response["data"]["ast"])))
    else:
        good = (result.returncode == 0 and response.get("ok") is True and
                matches(case["expect"], response.get("data")))
    return good, f"exit={result.returncode}, response={response}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="SIPL black-box conformance suite")
    parser.add_argument("--command", nargs="+", default=[sys.executable, "-m", "sipl.cli"],
                        help="CLI command to test, e.g. --command sipl")
    args = parser.parse_args(argv)
    cases = sorted(Path(__file__).parent.glob("*.json"))
    failures = 0
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        ok, detail = run_case(case, args.command)
        print(f"{'PASS' if ok else 'FAIL'} {case['id']}")
        if not ok:
            failures += 1
            print("  " + detail)
    print(f"{len(cases)-failures}/{len(cases)} passed")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
