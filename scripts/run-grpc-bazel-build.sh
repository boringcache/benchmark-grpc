#!/usr/bin/env bash
set -euo pipefail

strategy="${BAZEL_CACHE_STRATEGY:?BAZEL_CACHE_STRATEGY must be set}"
output_root="${BAZEL_OUTPUT_USER_ROOT:?BAZEL_OUTPUT_USER_ROOT must be set}"
output_base="${BAZEL_OUTPUT_BASE:?BAZEL_OUTPUT_BASE must be set}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mapfile -d '' plan < <(python3 "${repo_root}/scripts/run-benchmark-plan.py" bazel --print0)

if [[ "${plan[*]}" != "./tools/bazel build --config=opt //test/..." ]]; then
  echo "Unexpected gRPC Bazel benchmark plan: ${plan[*]}" >&2
  exit 2
fi

startup_args=(
  "--output_user_root=${output_root}"
  "--output_base=${output_base}"
)
build_args=()

case "$strategy" in
  actions-cache)
    disk_cache="${BAZEL_DISK_CACHE:?BAZEL_DISK_CACHE must be set}"
    mkdir -p "$disk_cache"
    build_args+=("--disk_cache=${disk_cache}")
    ;;
  buildbuddy)
    api_key="${BUILDBUDDY_API_KEY:?BUILDBUDDY_API_KEY must be set}"
    instance="${BUILDBUDDY_REMOTE_INSTANCE_NAME:?BUILDBUDDY_REMOTE_INSTANCE_NAME must be set}"
    build_args+=(
      "--bes_results_url=https://app.buildbuddy.io/invocation/"
      "--bes_backend=grpcs://remote.buildbuddy.io"
      "--remote_cache=grpcs://remote.buildbuddy.io"
      "--remote_timeout=10m"
      "--remote_instance_name=${instance}"
      "--remote_header=x-buildbuddy-api-key=${api_key}"
    )
    if [[ "${BUILDBUDDY_REMOTE_UPLOAD_LOCAL_RESULTS:-true}" == "false" ]]; then
      build_args+=("--remote_upload_local_results=false")
    fi
    ;;
  boringcache)
    ;;
  *)
    echo "Unknown Bazel cache strategy: ${strategy}" >&2
    exit 2
    ;;
esac

cd "${repo_root}/upstream"
exec "${plan[0]}" \
  "${startup_args[@]}" \
  "${plan[1]}" \
  "${build_args[@]}" \
  "${plan[@]:2}"
