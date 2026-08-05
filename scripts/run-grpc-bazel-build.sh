#!/usr/bin/env bash
set -euo pipefail

strategy="${BAZEL_CACHE_STRATEGY:?BAZEL_CACHE_STRATEGY must be set}"
output_root="${BAZEL_OUTPUT_USER_ROOT:?BAZEL_OUTPUT_USER_ROOT must be set}"
output_base="${BAZEL_OUTPUT_BASE:?BAZEL_OUTPUT_BASE must be set}"
target="${BAZEL_TARGET:?BAZEL_TARGET must be set}"

args=(
  "--output_user_root=${output_root}"
  "--output_base=${output_base}"
  build
)

case "$strategy" in
  actions-cache)
    disk_cache="${BAZEL_DISK_CACHE:?BAZEL_DISK_CACHE must be set}"
    mkdir -p "$disk_cache"
    args+=("--disk_cache=${disk_cache}")
    ;;
  buildbuddy)
    api_key="${BUILDBUDDY_API_KEY:?BUILDBUDDY_API_KEY must be set}"
    instance="${BUILDBUDDY_REMOTE_INSTANCE_NAME:?BUILDBUDDY_REMOTE_INSTANCE_NAME must be set}"
    args+=(
      "--bes_results_url=https://app.buildbuddy.io/invocation/"
      "--bes_backend=grpcs://remote.buildbuddy.io"
      "--remote_cache=grpcs://remote.buildbuddy.io"
      "--remote_timeout=10m"
      "--remote_instance_name=${instance}"
      "--remote_header=x-buildbuddy-api-key=${api_key}"
    )
    if [[ "${BUILDBUDDY_REMOTE_UPLOAD_LOCAL_RESULTS:-true}" == "false" ]]; then
      args+=("--remote_upload_local_results=false")
    fi
    ;;
  boringcache)
    ;;
  *)
    echo "Unknown Bazel cache strategy: ${strategy}" >&2
    exit 2
    ;;
esac

args+=("$target")

for attempt in 1 2 3; do
  if (cd upstream && ./tools/bazel "${args[@]}"); then
    exit 0
  fi
  if [[ "$attempt" -eq 3 ]]; then
    echo "Bazel build failed after ${attempt} attempts" >&2
    exit 1
  fi
  echo "Bazel build failed (attempt ${attempt}/3); retrying..." >&2
  sleep 5
done
