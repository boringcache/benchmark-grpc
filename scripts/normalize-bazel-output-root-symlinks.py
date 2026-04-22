#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Bazel output user root to normalize before caching")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve(strict=False)
    if not root.exists():
        print(f"Bazel output root does not exist: {root}")
        return 0

    converted = 0
    external: list[tuple[Path, str]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_symlink():
            continue

        target = os.readlink(path)
        if not os.path.isabs(target):
            continue

        target_path = Path(target).resolve(strict=False)
        if target_path.is_relative_to(root):
            relative_target = os.path.relpath(target_path, path.parent)
            path.unlink()
            path.symlink_to(relative_target)
            converted += 1
        else:
            external.append((path, target))

    if external:
        print(
            f"Found {len(external)} absolute symlink(s) that point outside {root}; refusing to cache unsafe Bazel output-root state.",
            file=sys.stderr,
        )
        for path, target in external[:25]:
            print(f"{path} -> {target}", file=sys.stderr)
        if len(external) > 25:
            print(f"... {len(external) - 25} more", file=sys.stderr)
        return 1

    print(f"Normalized {converted} Bazel output-root absolute symlink(s) under {root}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
