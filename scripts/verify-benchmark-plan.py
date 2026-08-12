#!/usr/bin/env python3
"""Keep the gRPC benchmark bounded, build-only, and tied to upstream targets."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "./tools/bazel",
    "build",
    "--config=opt",
    "//examples/cpp/csm:csm_greeter_client",
    "//examples/cpp/csm:csm_greeter_server",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    try:
        plan = tomllib.loads((ROOT / ".boringcache.toml").read_text())
        command = plan["adapters"]["bazel"]["command"]
        require(command == EXPECTED, "Bazel plan changed")
        require(command[1] == "build", "benchmark must use bazel build")
        require(
            all(not target.startswith("//test") for target in command[3:]),
            "benchmark must not compile the upstream test tree",
        )
        csm_build = (ROOT / "upstream/examples/cpp/csm/BUILD").read_text()
        require('name = "csm_greeter_client"' in csm_build, "upstream client target changed")
        require('name = "csm_greeter_server"' in csm_build, "upstream server target changed")
        require('"//:grpc++_reflection"' in csm_build, "upstream reflection coverage changed")
        require('"//:grpcpp_csm_observability"' in csm_build, "upstream CSM coverage changed")
        require('"//examples/protos:helloworld_cc_grpc"' in csm_build, "upstream proto coverage changed")
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
        require("for attempt" not in runner, "runner must not add retries")
        for target in EXPECTED[3:]:
            require(target in runner, f"runner guard omits {target}")
        action = (ROOT / ".github/actions/grpc-bazel-benchmark/action.yml").read_text()
        require("start_port_server.py" not in action, "build-only benchmark must not start the test port server")
        require("sudo apt" not in action, "benchmark must not include test-suite package setup")
        require(action.count("working-directory: upstream") == 2, "cache setup must use the upstream Bazel workspace")
        for workflow_name, bounded_jobs in (
            ("grpc-bazel-benchmark.yml", 1),
            ("grpc-bazel-fresh-benchmark.yml", 2),
        ):
            workflow = (ROOT / ".github/workflows" / workflow_name).read_text()
            require("cancel-in-progress: true" in workflow, f"{workflow_name} must cancel stale runs")
            require("timeout-minutes: 300" not in workflow, f"{workflow_name} still allows five-hour jobs")
            require(
                workflow.count("timeout-minutes: 45") == bounded_jobs,
                f"{workflow_name} must give each build job a 45-minute bound",
            )
    except (KeyError, OSError, RuntimeError, tomllib.TOMLDecodeError) as error:
        print(f"gRPC benchmark plan mismatch: {error}", file=sys.stderr)
        return 1
    print("Verified bounded gRPC CSM client/server Bazel build plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
