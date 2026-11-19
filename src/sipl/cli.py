import argparse
import dataclasses
import json
from pathlib import Path
from .parser import parse, ParseError
from .interpreter import Interpreter, ExecutionError
from .trace import trace_ast


def main():
    ap = argparse.ArgumentParser(prog="sipl")
    ap.add_argument("command", choices=["parse", "check", "run", "trace"])
    ap.add_argument("file", type=Path)
    ap.add_argument("--var", action="append", default=[], metavar="NAME=INTEGER",
                    help="initial variable value; repeat as needed")
    ap.add_argument("--max-steps", type=int, default=10000)
    args = ap.parse_args()
    try:
        tree = parse(args.file.read_text(encoding="utf-8"))
        if args.command == "check":
            print("Syntax OK")
        elif args.command == "parse":
            print(json.dumps(dataclasses.asdict(tree), ensure_ascii=False, indent=2))
        else:
            state = {}
            for item in args.var:
                name, sep, value = item.partition("=")
                if not sep or not name.isidentifier():
                    raise ValueError(f"invalid --var {item!r}: expected NAME=INTEGER")
                state[name] = int(value)
            if args.command == "trace":
                output = dataclasses.asdict(trace_ast(tree, state, args.max_steps))
            else:
                output = dataclasses.asdict(Interpreter(state, args.max_steps).run(tree))
            print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    except (ParseError, ExecutionError, OSError, ValueError) as exc:
        ap.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
