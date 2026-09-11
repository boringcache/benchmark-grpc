# Shared Bazel settings

Every provider runs the command in `.boringcache.toml` against the same pinned
gRPC source. The runner appends that command's build flags after provider
settings, so the shared policy overrides provider defaults, including settings
written to a Bazel rc file by an adapter. Each job prints this shared plan.

| Setting | Shared value | Effect |
| --- | --- | --- |
| Remote output downloads | `toplevel` | Download the requested client/server outputs and any inputs needed by local actions. |
| Asynchronous cache uploads | `false` | Wait for cache uploads during action execution. |
| Remote connection limit | `64` | Apply the same Bazel connection limit to each remote cache. |
| Remote timeout | `10m` | Apply the same Bazel timeout to each remote cache. |
| Action environment | Strict, with a fixed `PATH` for actions, host actions, and repository rules | Avoid inherited runner `PATH` differences. |
| Repository toolchain | `/usr/bin/gcc`, `/usr/bin/g++`, `/usr/bin/ld` | Select the same Linux compiler and linker paths. |

`--remote_download_minimal` is an alias for
`--remote_download_outputs=minimal`. It downloads remote outputs only when
local actions need them; even final target outputs may remain remote.
`toplevel` also downloads the explicitly requested target outputs. This is
Bazel 8.7's default, and the benchmark now sets it explicitly for every provider.
See the [Bazel 8.7 command-line reference](https://bazel.build/versions/8.7.0/reference/command-line-reference#flag--remote_download_outputs).

Local comparisons require the same Linux toolchain layout as CI. Provider
endpoints, authentication, cache scope, and phase-specific read/write policy
remain in provider setup. GitHub Actions Cache stores an archive of Bazel's
disk cache; BuildBuddy, BoringCache, and Cachely use remote-cache services.
Bazel's connection limit has protocol-specific behavior, so equal values do
not imply equal request concurrency across HTTP and gRPC.

Runs before this shared policy used BoringCache's `minimal` download setting
and normalized environment while the other providers inherited defaults.
Compare timings within a run using the same harness revision. A difference in
the `internal` process count alone does not establish a different compilation
workload, and these settings do not establish the cause of an earlier count
difference.
