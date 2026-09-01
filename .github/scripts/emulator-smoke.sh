#!/usr/bin/env bash
set -euo pipefail

APK="artifact/KUNAL-Universal-Video_PRO_V3.apk"
[ -s "$APK" ] || APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
[ -s "$APK" ] || { echo "APK_MISSING"; exit 1; }

ADB="$(command -v adb)"
EMULATOR="$(command -v emulator)"
ADB_TIMEOUT=90
DEVICE="emulator-5554"

cleanup() {
  set +e
  "$ADB" devices -l > adb-devices.txt 2>&1 || true
  "$ADB" -s "$DEVICE" emu kill >/dev/null 2>&1 || true
  if [ -n "${EMU_PID:-}" ]; then
    kill "$EMU_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

adb_cmd() {
  timeout --signal=KILL "$ADB_TIMEOUT" "$ADB" "$@"
}

echo "Starting dedicated Android emulator smoke environment."

adb_cmd start-server >/dev/null

AVD_NAME="kunal-smoke"
AVD_PATH="${ANDROID_AVD_HOME:-$HOME/.android/avd}/${AVD_NAME}.avd"
if [ ! -d "$AVD_PATH" ]; then
  RESOLVED_AVD_PATH="$(avdmanager list avd 2>/dev/null | awk -v name="$AVD_NAME" '
    $0 ~ "Name: " name {found=1; next}
    found && /Path: / {sub(/^.*Path: /, ""); print; exit}
  ')"
  if [ -n "$RESOLVED_AVD_PATH" ] && [ -d "$RESOLVED_AVD_PATH" ]; then
    AVD_PATH="$RESOLVED_AVD_PATH"
  fi
fi
[ -d "$AVD_PATH" ] || {
  echo "AVD_MISSING=$AVD_PATH"
  echo "ANDROID_AVD_HOME=${ANDROID_AVD_HOME:-<unset>}"
  avdmanager list avd || true
  exit 1
}

# Keep the emulator and avdmanager on the same discovered AVD home.
AVD_HOME_DIR="$(dirname "$AVD_PATH")"
export ANDROID_AVD_HOME="$AVD_HOME_DIR"
echo "Using AVD_PATH=$AVD_PATH"
echo "Using ANDROID_AVD_HOME=$ANDROID_AVD_HOME"

rm -f emulator.log emulator-logcat.txt emulator-restart-logcat.txt adb-devices.txt

"$EMULATOR" \
  -avd "$AVD_NAME" \
  -port 5554 \
  -no-window \
  -no-audio \
  -no-boot-anim \
  -no-snapshot \
  -no-metrics \
  -gpu swiftshader_indirect \
  -accel off \
  -wipe-data \
  >emulator.log 2>&1 &
EMU_PID=$!

echo "Waiting for Android device/framework..."
READY=0
for i in $(seq 1 360); do
  state="$(timeout --signal=KILL 10 "$ADB" -s "$DEVICE" get-state 2>/dev/null | tr -d '\r' || true)"
  if [ "$state" = "device" ]; then
    boot="$(timeout --signal=KILL 10 "$ADB" -s "$DEVICE" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [ "$boot" = "1" ]; then
      if timeout --signal=KILL 15 "$ADB" -s "$DEVICE" shell cmd package list packages >/dev/null 2>&1; then
        READY=1
        break
      fi
    fi
  else
    timeout --signal=KILL 10 "$ADB" reconnect offline >/dev/null 2>&1 || true
  fi
  if ! kill -0 "$EMU_PID" >/dev/null 2>&1; then
    echo "EMULATOR_PROCESS_EXITED"
    tail -n 120 emulator.log || true
    exit 1
  fi
  sleep 2
done

[ "$READY" = "1" ] || {
  echo "EMULATOR_READY_TIMEOUT"
  "$ADB" devices -l || true
  tail -n 160 emulator.log || true
  exit 1
}

echo "ANDROID_READY_PASS"
sleep 5

run_retry() {
  local label="$1"; shift
  local attempt rc
  for attempt in 1 2 3 4; do
    echo "ADB_${label}_ATTEMPT=${attempt}"
    set +e
    timeout --signal=KILL "$ADB_TIMEOUT" "$ADB" -s "$DEVICE" "$@"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
      return 0
    fi
    echo "ADB_${label}_FAILED rc=${rc}"
    timeout --signal=KILL 10 "$ADB" reconnect offline >/dev/null 2>&1 || true
    sleep 4
  done
  return 1
}

run_retry INSTALL install -r "$APK"
run_retry FORCE_STOP shell am force-stop com.kunal.universalvideo
run_retry LOGCAT_CLEAR logcat -c
run_retry START shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5

PID="$(timeout --signal=KILL 20 "$ADB" -s "$DEVICE" shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID" ] || { echo "START_FAILED_NO_PID"; exit 1; }

run_retry PACKAGE_DUMP shell dumpsys package com.kunal.universalvideo >/dev/null
timeout --signal=KILL 30 "$ADB" -s "$DEVICE" logcat -d -t 1500 > emulator-logcat.txt 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-logcat.txt; then
  echo "APP_CRASH_EVIDENCE_FOUND"
  exit 1
fi
echo "START_PASS pid=$PID"

run_retry RESTART_FORCE_STOP shell am force-stop com.kunal.universalvideo
sleep 2
run_retry RESTART_START shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID2="$(timeout --signal=KILL 20 "$ADB" -s "$DEVICE" shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID2" ] || { echo "RESTART_FAILED_NO_PID"; exit 1; }
timeout --signal=KILL 30 "$ADB" -s "$DEVICE" logcat -d -t 1500 > emulator-restart-logcat.txt 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-restart-logcat.txt; then
  echo "RESTART_CRASH_EVIDENCE_FOUND"
  exit 1
fi

echo "RESTART_PASS pid=$PID2"
echo "EMULATOR_SMOKE_PASS"