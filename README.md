# benchmark-grpc

Public gRPC Bazel benchmark runner for BoringCache vs GitHub Actions cache, BuildBuddy Cache, and Depot Cache.

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
  `grpcs://remote.buildbuddy.io`; Depot Cache uses Bazel `--remote_cache`
  against `https://cache.depot.dev`

## Token Model

This repo uses split BoringCache tokens as the standard CI shape:

- `BORINGCACHE_RESTORE_TOKEN` for read-only restore and proxy access
- `BORINGCACHE_SAVE_TOKEN` for trusted write paths
- `BORINGCACHE_API_TOKEN` only where a single bearer variable is still required for compatibility
- `BUILDBUDDY_API_KEY` for the BuildBuddy Cache lane
- `DEPOT_TOKEN` for the Depot Cache lane
- optional `DEPOT_ORG_ID` when using a user token that belongs to multiple Depot organizations

Depot fresh runs use a per-run Bazel `--action_env` scope to keep cold/warm samples isolated. Rolling runs use the stable rolling cache scope for the branch.

Depot rolling runs do not use the per-run scope and do not purge, so they measure normal cross-commit cache reuse.
