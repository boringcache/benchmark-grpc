# benchmark-grpc

Public gRPC Bazel benchmark runner for BoringCache vs GitHub Actions cache and BuildBuddy Cache.

This repo exists separately from [`boringcache/benchmarks`](https://github.com/boringcache/benchmarks) so the benchmark keeps:

- one pinned upstream source commit
- isolated GitHub Actions cache usage
- one per-repo BoringCache workspace name: `boringcache/benchmark-grpc`
- independent workflow history plus upstream-sync-driven benchmark runs and manual dispatches

## Source Model

- Upstream source lives in the pinned `upstream/` submodule.

Pinned upstream source:

- see committed `upstream/` submodule on `main`

## What It Measures

Fresh lane runs a no-prior-cache cold build plus one warm rerun for each backend:

- `cold`
- `warm1`

Rolling lane records the upstream commit build as-is after each upstream sync against the prior rolling cache and intentionally skips `warm1`.

The story this benchmark is meant to show is:

- speed on fresh cold and warm paths
- commit-build behavior on normal upstream syncs in the rolling lane
- storage footprint in each backend
- cache reuse through Bazel's documented cache surfaces: BoringCache uses
  `--remote_cache`; actions/cache persists only the directory passed to
  `--disk_cache`; BuildBuddy Cache uses Bazel `--remote_cache` against
  `grpcs://remote.buildbuddy.io`

## Token Model

This repo uses split BoringCache tokens as the standard CI shape:

- `BORINGCACHE_RESTORE_TOKEN` for read-only restore and proxy access
- `BORINGCACHE_SAVE_TOKEN` for trusted write paths
- `BUILDBUDDY_API_KEY` for the BuildBuddy Cache lane
