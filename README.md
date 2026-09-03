# BoringCache gRPC benchmark

This repository contains the BoringCache benchmark for gRPC.

Benchmark workflows are in [`.github/workflows/`](.github/workflows/), with configuration in [`.boringcache.toml`](.boringcache.toml).

## Workload

The benchmark runs one optimized Bazel build of gRPC's upstream CSM client and
server examples:

- `//examples/cpp/csm:csm_greeter_client`
- `//examples/cpp/csm:csm_greeter_server`

This is a compact production-shaped graph covering gRPC C++, generated
protobuf/gRPC code, reflection and admin services, CSM observability, Abseil,
and OpenTelemetry/Prometheus. It does not run tests or compile `//test/...`.

Keeping the graph fixed makes cold-versus-warm cache timings repeatable and
keeps every provider comparison bounded. Rolling builds time out after 45
minutes; fresh cold/warm comparisons get 90 minutes because uncached GitHub
Actions and BuildBuddy builds can exceed the rolling bound. A newer run on the
same ref cancels an older in-progress run.
