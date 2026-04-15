# benchmark-grpc

Public gRPC Bazel benchmark runner for BoringCache vs GitHub Actions cache.

This repo exists separately from [`boringcache/benchmarks`](https://github.com/boringcache/benchmarks) so the benchmark keeps:

- one pinned upstream source commit
- isolated GitHub Actions cache usage
- one shared BoringCache workspace name: `boringcache/benchmarks`
- independent workflow history plus upstream-sync-driven benchmark runs and manual dispatches

## Source Model

- Upstream source lives in the pinned `upstream/` submodule.

Pinned upstream source:

- see committed `upstream/` submodule on `main`

## What It Measures

Each backend runs the same scenario set:

- `cold`
- `warm1`

The story this benchmark is meant to show is:

- speed on cold and warm paths
- storage footprint in each backend
- cache reuse through native Bazel remote cache behavior

## Token Model

This repo uses split BoringCache tokens as the standard CI shape:

- `BORINGCACHE_RESTORE_TOKEN` for read-only restore and proxy access
- `BORINGCACHE_SAVE_TOKEN` for trusted write paths
- `BORINGCACHE_API_TOKEN` only where a single bearer variable is still required for compatibility
