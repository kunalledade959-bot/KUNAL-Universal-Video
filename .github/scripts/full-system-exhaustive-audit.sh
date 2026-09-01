#!/usr/bin/env bash
set -u
set -o pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec bash "$SCRIPT_DIR/full-system-exhaustive-audit-v2.sh" "$@"
