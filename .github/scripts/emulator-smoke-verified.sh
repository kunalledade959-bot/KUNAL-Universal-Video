#!/usr/bin/env bash
set -euo pipefail
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
[ -s "$APK" ]
rm -f emulator-smoke-PASS.txt emulator-smoke-FAIL.txt

echo "Waiting for Android device/framework..."
for i in $(seq 1 120); do
  state="$(adb get-state 2>/dev/null || true)"
  boot="$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [ "$state" = "device" ] && [ "$boot" = "1" ] && adb shell cmd package list packages >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
[ "$(adb get-state 2>/dev/null | tr -d '\r')" = "device" ]
[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]
adb shell cmd package list packages >/dev/null 2>&1

echo "Android framework ready."
adb install -r "$APK"
adb shell am force-stop com.kunal.universalvideo
adb logcat -c
adb shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID="$(adb shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID" ]
adb shell dumpsys package com.kunal.universalvideo >/dev/null
adb logcat -d -t 1000 > emulator-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-logcat.txt; then
  echo "APP_CRASH_EVIDENCE_FOUND" | tee emulator-smoke-FAIL.txt
  exit 1
fi

echo "START_PASS pid=$PID"
adb shell am force-stop com.kunal.universalvideo
sleep 2
adb shell am start -W -n com.kunal.universalvideo/.MainActivity
sleep 5
PID2="$(adb shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID2" ]
adb logcat -d -t 1000 > emulator-restart-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' emulator-restart-logcat.txt; then
  echo "RESTART_CRASH_EVIDENCE_FOUND" | tee emulator-smoke-FAIL.txt
  exit 1
fi

echo "RESTART_PASS pid=$PID2"
printf 'EMULATOR_SMOKE_PASS\nSTART_PASS pid=%s\nRESTART_PASS pid=%s\n' "$PID" "$PID2" > emulator-smoke-PASS.txt
