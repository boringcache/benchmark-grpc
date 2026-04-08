#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scenario="${1:-base}"

git -C "${repo_root}/upstream" reset --hard
git -C "${repo_root}/upstream" clean -fdx

case "${scenario}" in
  base|warm1|warm2|layer_miss)
    ;;
  stale-low)
    git -C "${repo_root}/upstream" apply "${repo_root}/scenarios/stale-low.patch"
    ;;
  stale-mid)
    git -C "${repo_root}/upstream" apply "${repo_root}/scenarios/stale-mid.patch"
    ;;
  stale-high)
    git -C "${repo_root}/upstream" apply "${repo_root}/scenarios/stale-high.patch"
    ;;
  *)
    echo "Unknown scenario: ${scenario}" >&2
    exit 1
    ;;
esac

REPO_ROOT="${repo_root}" python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["REPO_ROOT"]) / "upstream/bazel/grpc_python_deps.bzl"
text = path.read_text()
old = '            url = "https://github.com/bazel-contrib/rules_python/releases/download/1.6.3/rules_python-1.6.3.tar.gz",'
new = '''            urls = [
                "https://github.com/bazel-contrib/rules_python/releases/download/1.6.3/rules_python-1.6.3.tar.gz",
                "https://github.com/bazel-contrib/rules_python/archive/refs/tags/1.6.3.tar.gz",
            ],'''
if old in text:
    path.write_text(text.replace(old, new, 1))
PY

bazelrc_path="${HOME}/.bazelrc"
if ! grep -Fq 'common --enable_bzlmod=false' "$bazelrc_path" 2>/dev/null; then
  echo 'common --enable_bzlmod=false' >> "$bazelrc_path"
fi
if ! grep -Fq 'common --enable_workspace=true' "$bazelrc_path" 2>/dev/null; then
  echo 'common --enable_workspace=true' >> "$bazelrc_path"
fi

git -C "${repo_root}/upstream" status --short
