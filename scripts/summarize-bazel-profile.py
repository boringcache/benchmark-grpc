#!/usr/bin/env python3
import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BUILD_SUMMARY_RE = re.compile(
    r"INFO: Elapsed time: (?P<elapsed>[0-9.]+)s, Critical Path: (?P<critical>[0-9.]+)s"
)
PROCESS_SUMMARY_RE = re.compile(
    r"INFO: (?P<total>[0-9,]+) processes: (?P<details>.+)\."
)
DETAIL_RE = re.compile(r"(?P<count>[0-9,]+) (?P<label>remote cache hit|internal|processwrapper-sandbox)")
FOR_TOOL_RE = re.compile(r"(?P<name>(?:Compiling|Linking|Generating|Creating) .+?) \[for tool\]")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--build-log", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--phase", required=True)
    return parser.parse_args()


def load_profile(profile_path: Path):
    with gzip.open(profile_path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def parse_build_log(log_path: Path):
    summary = {
        "elapsed_time_seconds": None,
        "critical_path_seconds": None,
        "total_processes": None,
        "remote_cache_hit_count": None,
        "internal_count": None,
        "processwrapper_sandbox_count": None,
    }
    for_tool_names = Counter()
    toolchain_probe_hits = Counter()

    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if (match := BUILD_SUMMARY_RE.search(line)):
                summary["elapsed_time_seconds"] = float(match.group("elapsed"))
                summary["critical_path_seconds"] = float(match.group("critical"))
            elif (match := PROCESS_SUMMARY_RE.search(line)):
                summary["total_processes"] = int(match.group("total").replace(",", ""))
                for detail_match in DETAIL_RE.finditer(match.group("details")):
                    label = detail_match.group("label").replace(" ", "_").replace("-", "_")
                    summary[f"{label}_count"] = int(detail_match.group("count").replace(",", ""))

            if (tool_match := FOR_TOOL_RE.search(line)):
                for_tool_names[tool_match.group("name")] += 1

            lowered = line.lower()
            if "local_config_cc" in lowered:
                toolchain_probe_hits["local_config_cc"] += 1
            if "generate_system_module_map" in lowered:
                toolchain_probe_hits["generate_system_module_map"] += 1
            if "remotejdk" in lowered or "remote_jdk" in lowered:
                toolchain_probe_hits["remotejdk"] += 1

    return summary, for_tool_names, toolchain_probe_hits


def seconds(total_microseconds):
    return round(total_microseconds / 1_000_000.0, 3)


def top_entries(counter_map, limit=10):
    rows = []
    for name, payload in sorted(
        counter_map.items(),
        key=lambda item: (-item[1]["duration_us"], item[0]),
    )[:limit]:
        rows.append(
            {
                "name": name,
                "seconds": seconds(payload["duration_us"]),
                "count": payload["count"],
            }
        )
    return rows


def summarize_profile(profile_data, for_tool_names):
    trace_events = profile_data.get("traceEvents", [])

    remote = {
        "action_cache_check_seconds": 0.0,
        "output_download_seconds": 0.0,
        "download_overhead_seconds": 0.0,
        "execution_setup_seconds": 0.0,
    }
    setup = {
        "repository_fetch_seconds": 0.0,
        "starlark_repository_seconds": 0.0,
        "package_creation_seconds": 0.0,
        "toolchain_probe_seconds": 0.0,
    }
    for_tool = {
        "seconds": 0.0,
        "count": 0,
        "top_actions": [],
    }
    local_actions = defaultdict(lambda: {"duration_us": 0, "count": 0})
    for_tool_actions = defaultdict(lambda: {"duration_us": 0, "count": 0})

    toolchain_keywords = ("remotejdk", "remote_jdk", "local_config_cc", "toolchain")

    for event in trace_events:
        category = str(event.get("cat", ""))
        name = str(event.get("name", ""))
        duration_us = int(event.get("dur", 0) or 0)
        lowered = f"{category} {name}".lower()

        if category == "remote action cache check":
            remote["action_cache_check_seconds"] += duration_us / 1_000_000.0
        elif category == "remote output download":
            remote["output_download_seconds"] += duration_us / 1_000_000.0
        elif category == "general information" and name in {"Remote.download", "Remote.parseActionResultMetadata"}:
            remote["download_overhead_seconds"] += duration_us / 1_000_000.0
        elif category == "Remote execution setup":
            remote["execution_setup_seconds"] += duration_us / 1_000_000.0

        if category == "Fetching repository":
            setup["repository_fetch_seconds"] += duration_us / 1_000_000.0
        elif category == "Starlark repository function call":
            setup["starlark_repository_seconds"] += duration_us / 1_000_000.0
        elif category == "package creation" and any(keyword in lowered for keyword in toolchain_keywords):
            setup["package_creation_seconds"] += duration_us / 1_000_000.0
        elif category == "Starlark repository function call" and any(keyword in lowered for keyword in toolchain_keywords):
            setup["toolchain_probe_seconds"] += duration_us / 1_000_000.0

        if category != "action processing":
            continue

        payload = local_actions[name]
        payload["duration_us"] += duration_us
        payload["count"] += 1

        if name in for_tool_names:
            for_tool["seconds"] += duration_us / 1_000_000.0
            for_tool["count"] += 1
            for_tool_payload = for_tool_actions[name]
            for_tool_payload["duration_us"] += duration_us
            for_tool_payload["count"] += 1

    for_tool["seconds"] = round(for_tool["seconds"], 3)
    for_tool["top_actions"] = top_entries(for_tool_actions)

    setup["total_seconds"] = round(
        setup["repository_fetch_seconds"]
        + setup["starlark_repository_seconds"]
        + setup["package_creation_seconds"]
        + setup["toolchain_probe_seconds"],
        3,
    )
    remote["total_seconds"] = round(
        remote["action_cache_check_seconds"]
        + remote["output_download_seconds"]
        + remote["download_overhead_seconds"]
        + remote["execution_setup_seconds"],
        3,
    )

    top_local = top_entries(
        {
            name: payload
            for name, payload in local_actions.items()
            if name not in for_tool_names
        },
        limit=15,
    )

    return remote, setup, for_tool, top_local


def write_outputs(output_dir: Path, phase: str, payload):
    json_path = output_dir / "bazel-miss-summary.json"
    md_path = output_dir / "bazel-miss-summary.md"

    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    build = payload["build_summary"]
    remote = payload["remote_cache"]
    setup = payload["repository_and_toolchain_setup"]
    for_tool = payload["for_tool_actions"]

    lines = [
        f"## Bazel miss summary ({phase})",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Elapsed time | {build.get('elapsed_time_seconds', 'n/a')}s |",
        f"| Critical path | {build.get('critical_path_seconds', 'n/a')}s |",
        f"| Remote cache hits | {build.get('remote_cache_hit_count', 'n/a')} |",
        f"| Internal actions | {build.get('internal_count', 'n/a')} |",
        f"| processwrapper-sandbox actions | {build.get('processwrapper-sandbox_count', 'n/a')} |",
        f"| Remote cache check time | {remote['action_cache_check_seconds']}s |",
        f"| Remote output download time | {remote['output_download_seconds']}s |",
        f"| Remote download overhead | {remote['download_overhead_seconds']}s |",
        f"| Remote execution setup time | {remote['execution_setup_seconds']}s |",
        f"| Repository/toolchain setup time | {setup['total_seconds']}s |",
        f"| [for tool] action time | {for_tool['seconds']}s |",
        f"| [for tool] action count | {for_tool['count']} |",
        "",
        "### Dominant local actions",
        "",
    ]

    for action in payload["top_local_actions"]:
        lines.append(f"- `{action['name']}`: {action['seconds']}s across {action['count']} events")

    if payload["for_tool_actions"]["top_actions"]:
        lines.extend(["", "### Dominant [for tool] actions", ""])
        for action in payload["for_tool_actions"]["top_actions"]:
            lines.append(f"- `{action['name']}`: {action['seconds']}s across {action['count']} events")

    if payload["toolchain_probe_log_hits"]:
        lines.extend(["", "### Toolchain probe log hits", ""])
        for name, count in payload["toolchain_probe_log_hits"].items():
            lines.append(f"- `{name}`: {count}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    profile_path = Path(args.profile)
    build_log_path = Path(args.build_log)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile_data = load_profile(profile_path)
    build_summary, for_tool_names, toolchain_probe_hits = parse_build_log(build_log_path)
    remote, setup, for_tool, top_local = summarize_profile(profile_data, for_tool_names)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "profile_path": str(profile_path),
        "build_log_path": str(build_log_path),
        "build_summary": build_summary,
        "remote_cache": remote,
        "repository_and_toolchain_setup": setup,
        "for_tool_actions": {
            "seconds": for_tool["seconds"],
            "count": for_tool["count"],
            "names_from_build_log": for_tool_names.most_common(),
            "top_actions": for_tool["top_actions"],
        },
        "toolchain_probe_log_hits": dict(toolchain_probe_hits),
        "top_local_actions": top_local,
    }
    write_outputs(output_dir, args.phase, payload)


if __name__ == "__main__":
    main()
