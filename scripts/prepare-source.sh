#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scenario="${1:-base}"

git -C "${repo_root}/upstream" reset --hard
git -C "${repo_root}/upstream" clean -fdx

case "${scenario}" in
  base|warm1)
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
append_bazelrc_line() {
  local line="$1"
  if ! grep -Fqx "$line" "$bazelrc_path" 2>/dev/null; then
    echo "$line" >> "$bazelrc_path"
  fi
}

stable_action_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
cc_path="$(command -v gcc-13 || command -v gcc)"
cxx_path="$(command -v g++-13 || command -v g++)"
ld_path="$(command -v ld)"

append_bazelrc_line 'common --enable_bzlmod=false'
append_bazelrc_line 'common --enable_workspace=true'
append_bazelrc_line 'build --incompatible_strict_action_env'
append_bazelrc_line "build --action_env=PATH=${stable_action_path}"
append_bazelrc_line "build --repo_env=CC=${cc_path}"
append_bazelrc_line "build --repo_env=CXX=${cxx_path}"
append_bazelrc_line "build --repo_env=LD=${ld_path}"

git -C "${repo_root}/upstream" status --short
