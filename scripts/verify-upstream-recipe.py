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
        prerequisites = "sudo apt install -y build-essential autoconf libtool pkg-config cmake python3 python3-pip clang"
        port_server = "python3 tools/run_tests/start_port_server.py"
        require("sudo apt update" in upstream, "upstream prerequisite update changed")
        require(prerequisites in upstream, "upstream prerequisite install changed")
        require("python3 --version" in upstream, "upstream Python check changed")
        require(port_server in upstream, "upstream port-server command changed")
        require("tools/bazel build --config=opt //test/..." in upstream, "upstream Bazel command changed")
        preparation = (ROOT / "scripts/prepare-source.sh").read_text()
        require(".bazelrc" not in preparation, "benchmark must let upstream choose Bazel module mode")
        require(
            "grpc_python_deps.bzl" not in preparation,
            "benchmark must not patch upstream dependency sources",
        )
        runner = (ROOT / "scripts/run-grpc-bazel-build.sh").read_text()
        require("run-benchmark-plan.py\" bazel --print0" in runner, "runner bypasses the committed plan")
        require('cd "${repo_root}/upstream"' in runner, "runner must execute inside the Bazel workspace")
        require('"${plan[1]}"' in runner and '"${build_args[@]}"' in runner, "cache flags must follow the build command")
        require("for attempt" not in runner, "runner must not add non-upstream retries")
        action = (ROOT / ".github/actions/grpc-bazel-benchmark/action.yml").read_text()
        require("sudo apt update" in action, "benchmark omits the upstream prerequisite update")
        require(prerequisites in action, "benchmark omits the upstream prerequisite install")
        require("python3 --version" in action, "benchmark omits the upstream Python check")
        require(port_server in action, "benchmark omits the upstream port-server command")
        require(action.count("working-directory: upstream") == 3, "benchmark must use the upstream Bazel workspace")
    except (KeyError, OSError, RuntimeError, tomllib.TOMLDecodeError) as error:
        print(f"gRPC recipe mismatch: {error}", file=sys.stderr)
        return 1
    print("Verified gRPC //test/... Bazel plan against pinned upstream CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
