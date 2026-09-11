# Cachely setup

The gRPC benchmark uses [Cachely's Bazel HTTP cache](https://cachely.dev/docs/bazel)
at `https://remote.cachely.dev`. It runs the same pinned gRPC source and
optimized CSM greeter client/server build plan as the other providers.

Set the GitHub Actions repository secret `CACHELY_TOKEN` for CI. Locally, set
`CACHELY_TOKEN` or add `cachely_token=...` to `.env` in this repository or its
parent directory. Environment variables take precedence over files.

The build script calls `scripts/configure-cachely.py` to generate
`user.bazelrc` with owner-only permissions. Both `.env` and `user.bazelrc` are
ignored by Git. The generated file is replaced on each Cachely invocation;
keep other local Bazel settings elsewhere.

To run the existing benchmark locally with Cachely reads enabled:

```sh
BAZEL_CACHE_STRATEGY=cachely \
BAZEL_OUTPUT_USER_ROOT=/tmp/grpc-cachely/output-root \
BAZEL_OUTPUT_BASE=/tmp/grpc-cachely/output-base \
./scripts/run-grpc-bazel-build.sh
```

Use the harness's usual prerequisites, including Bash with `mapfile`,
Python 3.11 or later, and the upstream gRPC build dependencies. The source
submodule must be initialized before a local build.
All providers use the [shared Linux Bazel settings](comparison.md), including
the compiler paths and `toplevel` output-download policy.

Local uploads default to disabled. Trusted CI publishing phases set
`CACHELY_REMOTE_UPLOAD_LOCAL_RESULTS=true`, which selects `cachely-ci`.
The fresh cold phase also sets `CACHELY_REMOTE_ACCEPT_CACHED=false` so it
cannot reuse an older remote result. The dependent warm job uses a new runner,
reads the remote cache, and disables uploads. Pull requests skip the Cachely
pair because the configured token can write.

Cachely uses the token's shared workspace, without a per-run server namespace.
Disabling reads makes the cold build execute locally; it does not empty the
remote cache or isolate stored bytes. Inspect native cache-hit evidence before
treating a warm timing as a cache-reuse measurement. The Cachely fresh artifact
is named `benchmark-grpc-bazel-cachely-fresh` (with any requested benchmark
suffix). The rolling workflow deliberately excludes Cachely so the
token-backed fresh comparison stays separate from the normal rolling
comparison.
