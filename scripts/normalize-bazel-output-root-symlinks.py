#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "roots",
        nargs="+",
        help="Bazel cache paths to normalize before archiving",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    converted = 0
    external: list[tuple[Path, str, Path]] = []

    for raw_root in args.roots:
        root = Path(raw_root).resolve(strict=False)
        if not root.exists():
            print(f"Bazel cache path does not exist: {root}")
            continue

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
                external.append((path, target, root))

    if external:
        print(
            f"Found {len(external)} absolute symlink(s) that point outside their cache path; refusing to cache unsafe Bazel state.",
            file=sys.stderr,
        )
        for path, target, root in external[:25]:
            print(f"{path} -> {target} (cache path: {root})", file=sys.stderr)
        if len(external) > 25:
            print(f"... {len(external) - 25} more", file=sys.stderr)
        return 1

    print(f"Normalized {converted} Bazel cache absolute symlink(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
