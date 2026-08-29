#!/usr/bin/env bash
set -euo pipefail
APK="artifact/KUNAL-Universal-Video_PRO_V3.apk"
[ -s "$APK" ] || APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
[ -s "$APK" ] || { echo "APK_MISSING"; exit 1; }

ADB_TIMEOUT=60
adb_cmd() { timeout --signal=KILL "$ADB_TIMEOUT" adb "$@"; }

# Emulator can report offline while Android is still bringing ADB online.
echo "Waiting for Android device/framework..."
READY=0
for i in $(seq 1 180); do
  timeout --signal=KILL 8 adb reconnect offline >/dev/null 2>&1 || true
  state="$(timeout --signal=KILL 8 adb -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)"
  if [ "$state" = "device" ]; then
    boot="$(timeout --signal=KILL 8 adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [ "$boot" = "1" ] && timeout --signal=KILL 8 adb -s emulator-5554 shell cmd package list packages >/dev/null 2>&1; then
      READY=1
      break
    fi
  fi
  sleep 2
done
[ "$READY" = "1" ] || { echo "EMULATOR_READY_TIMEOUT"; adb devices -l || true; exit 1; }

echo "Android framework ready."

# Give the post-boot ADB transport a moment to settle before the APK transfer.
sleep 3

run_retry() {
  local label="$1"; shift
  local attempt rc
  for attempt in 1 2 3; do
    echo "ADB_${label}_ATTEMPT=${attempt}"
    set +e
    timeout --signal=KILL "$ADB_TIMEOUT" adb -s emulator-5554 "$@"
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then return 0; fi
    echo "ADB_${label}_FAILED rc=${rc}"
    timeout --signal=KILL 8 adb reconnect offline >/dev/null 2>&1 || true
    sleep 3
  done
  return 1
}

run_retry INSTALL install -r "$APK"
run_retry FORCE_STOP shell am force-stop com.kunal.universalvideo
run_retry LOGCAT_CLEAR logcat -c
run_retry START shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID="$(timeout --signal=KILL 15 adb -s emulator-5554 shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID" ] || { echo "START_FAILED_NO_PID"; exit 1; }
run_retry PACKAGE_DUMP shell dumpsys package com.kunal.universalvideo >/dev/null
timeout --signal=KILL 20 adb -s emulator-5554 logcat -d -t 1000 > emulator-logcat.txt 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-logcat.txt; then
  echo "APP_CRASH_EVIDENCE_FOUND"
  exit 1
fi
echo "START_PASS pid=$PID"

run_retry RESTART_FORCE_STOP shell am force-stop com.kunal.universalvideo
sleep 2
run_retry RESTART_START shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID2="$(timeout --signal=KILL 15 adb -s emulator-5554 shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID2" ] || { echo "RESTART_FAILED_NO_PID"; exit 1; }
timeout --signal=KILL 20 adb -s emulator-5554 logcat -d -t 1000 > emulator-restart-logcat.txt 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-restart-logcat.txt; then
  echo "RESTART_CRASH_EVIDENCE_FOUND"
  exit 1
fi

echo "RESTART_PASS pid=$PID2"
