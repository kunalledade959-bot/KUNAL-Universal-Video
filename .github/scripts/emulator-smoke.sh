#!/usr/bin/env bash
set -euo pipefail
APK="artifact/KUNAL-Universal-Video_PRO_V3.apk"
[ -s "$APK" ] || APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
[ -s "$APK" ]

ADB_TIMEOUT=15
adb_cmd() { timeout "$ADB_TIMEOUT" adb "$@"; }

# The previous probe could wait indefinitely when ADB reported offline. Keep
# every probe bounded and allow the runner's emulator to recover from offline.
echo "Waiting for Android device/framework..."
READY=0
for i in $(seq 1 180); do
  adb_cmd reconnect offline >/dev/null 2>&1 || true
  state="$(adb_cmd get-state 2>/dev/null | tr -d '\r' || true)"
  boot="$(adb_cmd shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [ "$state" = "device" ] && [ "$boot" = "1" ]; then
    if adb_cmd shell cmd package list packages >/dev/null 2>&1; then
      READY=1
      break
    fi
  fi
  sleep 2
done
[ "$READY" = "1" ] || { echo "EMULATOR_READY_TIMEOUT"; exit 1; }

state="$(adb_cmd get-state 2>/dev/null | tr -d '\r' || true)"
boot="$(adb_cmd shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
[ "$state" = "device" ]
[ "$boot" = "1" ]
adb_cmd shell cmd package list packages >/dev/null

echo "Android framework ready."
adb_cmd install -r "$APK"
adb_cmd shell am force-stop com.kunal.universalvideo
adb_cmd logcat -c
adb_cmd shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID="$(adb_cmd shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID" ]
adb_cmd shell dumpsys package com.kunal.universalvideo >/dev/null
adb_cmd logcat -d -t 1000 > emulator-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-logcat.txt; then
  echo "APP_CRASH_EVIDENCE_FOUND"
  exit 1
fi

echo "START_PASS pid=$PID"
adb_cmd shell am force-stop com.kunal.universalvideo
sleep 2
adb_cmd shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID2="$(adb_cmd shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID2" ]
adb_cmd logcat -d -t 1000 > emulator-restart-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-restart-logcat.txt; then
  echo "RESTART_CRASH_EVIDENCE_FOUND"
  exit 1
fi

echo "RESTART_PASS pid=$PID2"
