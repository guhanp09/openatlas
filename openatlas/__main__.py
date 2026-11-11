import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="OpenAtlas multilingual search product lab")
    parser.add_argument("command", choices=["evaluate", "serve"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "evaluate":
        from .evaluate import evaluate

        result = evaluate(args.root)
        print(json.dumps(result, indent=2))
    else:
        from .server import serve

        serve(args.root, args.port)


if __name__ == "__main__":
    main()
