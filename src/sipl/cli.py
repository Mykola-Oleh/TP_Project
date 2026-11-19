"""Stable CLI and JSON protocol for the SIPL toolkit."""
import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path

from .interpreter import ExecutionError, Interpreter
from .parser import ParseError, parse
from .trace import trace_ast

SCHEMA_VERSION = "1.0"
EXIT_SUCCESS = 0
EXIT_INPUT = 2
EXIT_SYNTAX = 3
EXIT_RUNTIME = 4
EXIT_INTERNAL = 5
_VAR_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z", re.ASCII)


def _parser():
    ap = argparse.ArgumentParser(prog="sipl", description="SIPL language toolkit")
    ap.add_argument("command", choices=["parse", "check", "run", "trace"])
    ap.add_argument("file", type=Path, help="UTF-8 SIPL source file")
    ap.add_argument("--json", action="store_true", dest="json_mode",
                    help="stable machine-readable JSON response")
    ap.add_argument("--var", action="append", default=[], metavar="NAME=INTEGER",
                    help="initial variable; repeat for multiple variables")
    ap.add_argument("--max-steps", type=int, default=10000,
                    help="maximum execution steps (default: 10000)")
    return ap


def _initial_state(items):
    state = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep or not _VAR_NAME.fullmatch(name):
            raise ValueError(f"invalid --var {item!r}: expected NAME=INTEGER")
        try:
            state[name] = int(value)
        except ValueError as exc:
            raise ValueError(f"invalid integer in --var {item!r}") from exc
    return state


def _response(command, ok, *, data=None, error=None):
    return {"schema_version": SCHEMA_VERSION, "command": command,
            "ok": ok, "data": data if ok else None,
            "error": error if not ok else None}


def _error(kind, message, location=None):
    return {"type": kind, "message": message,
            "location": (dataclasses.asdict(location) if location is not None else None)}


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.max_steps <= 0:
            raise ValueError("--max-steps must be positive")
        state = _initial_state(args.var)
        source = args.file.read_text(encoding="utf-8")
        tree = parse(source)
        if args.command == "check":
            data = {"valid": True}
            legacy = "Syntax OK"
        elif args.command == "parse":
            data = {"ast": dataclasses.asdict(tree)}
            legacy = json.dumps(data["ast"], ensure_ascii=False, indent=2)
        elif args.command == "run":
            data = dataclasses.asdict(Interpreter(state, args.max_steps).run(tree))
            legacy = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            data = dataclasses.asdict(trace_ast(tree, state, args.max_steps))
            legacy = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        if args.json_mode:
            print(json.dumps(_response(args.command, True, data=data), ensure_ascii=False))
        else:
            print(legacy)
        return EXIT_SUCCESS
    except ParseError as exc:
        code, kind, location, message = EXIT_SYNTAX, "SyntaxError", None, str(exc)
        # ParseError exposes start position; end is not known for invalid syntax.
        location = {"line": exc.line, "column": exc.column}
    except (OSError, UnicodeError, ValueError) as exc:
        code, kind, location, message = EXIT_INPUT, "InputError", None, str(exc)
    except ExecutionError as exc:
        code, kind, location, message = EXIT_RUNTIME, "RuntimeError", exc.location, str(exc)
    if args.json_mode:
        error = _error(kind, message, location) if not isinstance(location, dict) else {
            "type": kind, "message": message, "location": location}
        print(json.dumps(_response(args.command, False, error=error), ensure_ascii=False))
    else:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
