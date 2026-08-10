#!/usr/bin/env python3
"""Fail when the committed gRPC plan drifts from its pinned upstream CI script."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ["./tools/bazel", "build", "--config=opt", "//test/..."]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    try:
        plan = tomllib.loads((ROOT / ".boringcache.toml").read_text())
        require(plan["adapters"]["bazel"]["command"] == EXPECTED, "Bazel plan changed")
        upstream = (ROOT / "upstream/tools/internal_ci/linux/aws/grpc_aws_experiment_remote.sh").read_text()
        require("tools/bazel build --config=opt //test/..." in upstream, "upstream Bazel command changed")
        runner = (ROOT / "scripts/run-grpc-bazel-build.sh").read_text()
        require("run-benchmark-plan.py\" bazel --print0" in runner, "runner bypasses the committed plan")
        require("for attempt" not in runner, "runner must not add non-upstream retries")
    except (KeyError, OSError, RuntimeError, tomllib.TOMLDecodeError) as error:
        print(f"gRPC recipe mismatch: {error}", file=sys.stderr)
        return 1
    print("Verified gRPC //test/... Bazel plan against pinned upstream CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
