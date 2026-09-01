#!/usr/bin/env bash
set -euo pipefail

# Resolve the APK from the downloaded artifact instead of relying on a fragile filename.
mapfile -t APKS < <(find artifact -type f -name '*.apk' -size +1k -print | sort)
if [ "${#APKS[@]}" -ne 1 ]; then
  echo "APK_RESOLUTION_FAILED count=${#APKS[@]}"
  printf 'APK_CANDIDATE=%s\n' "${APKS[@]}"
  find artifact -maxdepth 3 -type f -print | sort || true
  exit 1
fi
APK="${APKS[0]}"
echo "APK_RESOLVED=$APK"

ADB="$(command -v adb || true)"
EMULATOR="$(command -v emulator || true)"
[ -x "$ADB" ] || { echo "ADB_MISSING"; exit 1; }
[ -x "$EMULATOR" ] || { echo "EMULATOR_MISSING"; exit 1; }
ADB_TIMEOUT=90
DEVICE="emulator-5554"

cleanup() {
  set +e
  "$ADB" devices -l > adb-devices.txt 2>&1 || true
  "$ADB" -s "$DEVICE" emu kill >/dev/null 2>&1 || true
  if [ -n "${EMU_PID:-}" ]; then kill "$EMU_PID" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT

echo "Starting dedicated Android emulator smoke environment."
set +e
"$ADB" kill-server >/tmp/adb-kill.log 2>&1
"$ADB" start-server >/tmp/adb-start.log 2>&1
ADB_START_RC=$?
set -e
if [ "$ADB_START_RC" -ne 0 ]; then
  echo "ADB_START_FAILED rc=$ADB_START_RC"
  cat /tmp/adb-start.log || true
  cat /tmp/adb-kill.log || true
  exit 1
fi
cat /tmp/adb-start.log || true

AVD_NAME="kunal-smoke"
AVD_PATH="${AVD_CONFIG:-}"
AVD_PATH="${AVD_PATH%/config.ini}"
if [ -z "$AVD_PATH" ] || [ ! -d "$AVD_PATH" ]; then
  AVD_PATH="$(avdmanager list avd 2>/dev/null | awk -v name="$AVD_NAME" '$0 ~ "Name: " name {found=1; next} found && /Path: / {sub(/^.*Path: /, ""); print; exit}')"
fi
[ -d "$AVD_PATH" ] || { echo "AVD_MISSING=$AVD_PATH"; avdmanager list avd || true; exit 1; }
export ANDROID_AVD_HOME="$(dirname "$AVD_PATH")"
echo "Using AVD_PATH=$AVD_PATH"

rm -f emulator.log emulator-logcat.txt emulator-restart-logcat.txt adb-devices.txt
"$EMULATOR" -avd "$AVD_NAME" -port 5554 -no-window -no-audio -no-boot-anim -no-snapshot -no-metrics -gpu swiftshader_indirect -accel off -wipe-data >emulator.log 2>&1 &
EMU_PID=$!

echo "Waiting for Android device/framework..."
READY=0
for i in $(seq 1 360); do
  state="$(timeout --signal=KILL 10 "$ADB" -s "$DEVICE" get-state 2>/dev/null | tr -d '\r' || true)"
  if [ "$state" = "device" ]; then
    boot="$(timeout --signal=KILL 10 "$ADB" -s "$DEVICE" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [ "$boot" = "1" ] && timeout --signal=KILL 15 "$ADB" -s "$DEVICE" shell cmd package list packages >/dev/null 2>&1; then READY=1; break; fi
  else
    timeout --signal=KILL 10 "$ADB" reconnect offline >/dev/null 2>&1 || true
  fi
  if ! kill -0 "$EMU_PID" >/dev/null 2>&1; then echo "EMULATOR_PROCESS_EXITED"; tail -n 160 emulator.log || true; exit 1; fi
  sleep 2
done
[ "$READY" = "1" ] || { echo "EMULATOR_READY_TIMEOUT"; "$ADB" devices -l || true; tail -n 160 emulator.log || true; exit 1; }
echo "ANDROID_READY_PASS"

run_retry() {
  local label="$1"; shift; local attempt rc
  for attempt in 1 2 3 4; do
    echo "ADB_${label}_ATTEMPT=$attempt"
    set +e; timeout --signal=KILL "$ADB_TIMEOUT" "$ADB" -s "$DEVICE" "$@"; rc=$?; set -e
    if [ "$rc" -eq 0 ]; then return 0; fi
    echo "ADB_${label}_FAILED rc=$rc"; timeout --signal=KILL 10 "$ADB" reconnect offline >/dev/null 2>&1 || true; sleep 4
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
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-logcat.txt; then echo "APP_CRASH_EVIDENCE_FOUND"; exit 1; fi
echo "START_PASS pid=$PID"
run_retry RESTART_FORCE_STOP shell am force-stop com.kunal.universalvideo
sleep 2
run_retry RESTART_START shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID2="$(timeout --signal=KILL 20 "$ADB" -s "$DEVICE" shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID2" ] || { echo "RESTART_FAILED_NO_PID"; exit 1; }
timeout --signal=KILL 30 "$ADB" -s "$DEVICE" logcat -d -t 1500 > emulator-restart-logcat.txt 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-restart-logcat.txt; then echo "RESTART_CRASH_EVIDENCE_FOUND"; exit 1; fi
echo "RESTART_PASS pid=$PID2"
echo "EMULATOR_SMOKE_PASS"
