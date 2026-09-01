#!/usr/bin/env bash
set -euo pipefail

adb start-server

for i in $(seq 1 120); do
  state="$(adb -s emulator-5554 get-state 2>/dev/null || true)"
  if [[ "$state" == "device" ]]; then
    break
  fi
  sleep 2
done

test "$(adb -s emulator-5554 get-state)" == "device"

exec bash .github/scripts/full-e2e-emulator.sh
