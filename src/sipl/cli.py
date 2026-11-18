import argparse
import dataclasses
import json
from pathlib import Path
from .parser import parse, ParseError

def main():
    ap = argparse.ArgumentParser(prog="sipl")
    ap.add_argument("command", choices=["parse", "check"])
    ap.add_argument("file", type=Path)
    args = ap.parse_args()
    try:
        tree = parse(args.file.read_text(encoding="utf-8"))
        if args.command == "check":
            print("Syntax OK")
        else:
            print(json.dumps(dataclasses.asdict(tree), ensure_ascii=False, indent=2))
    except (ParseError, OSError) as exc:
        ap.exit(1, f"{exc}\n")

if __name__ == "__main__":
    main()
