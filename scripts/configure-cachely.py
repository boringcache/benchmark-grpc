#!/usr/bin/env python3
"""Write Cachely's Bazel credentials from the environment or a local .env file."""

import os
import shlex
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    token = os.environ.get("CACHELY_TOKEN") or os.environ.get("cachely_token")
    if not token:
        for path in (ROOT / ".env", ROOT.parent / ".env"):
            if not path.is_file():
                continue
            for line in path.read_text().splitlines():
                key, separator, value = line.removeprefix("export ").partition("=")
                if separator and key.strip() in ("CACHELY_TOKEN", "cachely_token"):
                    try:
                        values = shlex.split(value, comments=True)
                    except ValueError:
                        raise SystemExit("Invalid Cachely token entry in .env") from None
                    if len(values) != 1:
                        raise SystemExit("Cachely token must be a single non-empty value")
                    token = values[0]
                    break
            if token:
                break

    if not token:
        raise SystemExit("Set CACHELY_TOKEN or add cachely_token to .env")
    if any(character.isspace() or character in '\\"' for character in token):
        raise SystemExit("Cachely token contains characters that cannot be used in a Bazel header")

    # Atomic replacement keeps credentials owner-only, including on later runs.
    with tempfile.NamedTemporaryFile(mode="w", dir=ROOT, delete=False) as handle:
        handle.write(f'build:cachely --remote_header="Authorization=Bearer {token}"\n')
        temporary_path = Path(handle.name)
    try:
        temporary_path.replace(ROOT / "user.bazelrc")
    finally:
        temporary_path.unlink(missing_ok=True)
    print("Configured Cachely credentials in gitignored user.bazelrc")


if __name__ == "__main__":
    main()
