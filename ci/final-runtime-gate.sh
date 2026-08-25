#!/usr/bin/env bash
set -euo pipefail

PKG='com.kunal.universalvideo'
ACT='com.kunal.universalvideo.MainActivity'
SERVICE="$PKG/com.kunal.universalvideo.UniversalAccessibilityService"
OUT="$GITHUB_WORKSPACE/runtime-final-gate"
APK="${APK_FILE:?APK_FILE is not set}"

rm -rf "$OUT"
mkdir -p "$OUT"
printf 'OUT=%s\nAPK=%s\n' "$OUT" "$APK"
test -s "$APK"

adb wait-for-device
for i in $(seq 1 90); do
  if [ "$(adb get-state 2>/dev/null || true)" = device ]; then
    break
  fi
  sleep 2
done

test "$(adb get-state)" = device
adb shell getprop sys.boot_completed | grep -q 1
adb shell pm uninstall "$PKG" >/dev/null 2>&1 || true
adb logcat -c

# Android package verification can time out on hosted emulator runners.
# Disable ADB/package verification for this isolated CI emulator and use a
# non-streamed install so the package verifier does not block installation.
adb shell settings put global package_verifier_enable 0 || true
adb shell settings put global verifier_verify_adb_installs 0 || true
adb shell settings put global package_verifier_user_consent -1 || true

if ! adb install --no-streaming "$APK" > "$OUT/install.txt" 2>&1; then
  echo 'FIRST INSTALL FAILED; RETRYING AFTER ADB RESET' | tee -a "$OUT/install.txt"
  adb kill-server || true
  adb start-server
  adb wait-for-device
  for i in $(seq 1 60); do
    if [ "$(adb get-state 2>/dev/null || true)" = device ]; then break; fi
    sleep 2
  done
  adb shell settings put global package_verifier_enable 0 || true
  adb shell settings put global verifier_verify_adb_installs 0 || true
  adb install --no-streaming "$APK" >> "$OUT/install.txt" 2>&1
fi

grep -q '^Success' "$OUT/install.txt"

echo "$SERVICE" > "$OUT/service.txt"
adb shell settings put secure enabled_accessibility_services "$SERVICE"
adb shell settings put secure accessibility_enabled 1

adb shell cmd package resolve-activity --brief "$PKG" > "$OUT/resolve.txt" 2>&1
# resolve-activity commonly prints either the fully-qualified activity or
# the package-relative form (com.example/.MainActivity). Accept both.
grep -Eq '(^|/)MainActivity$' "$OUT/resolve.txt"

# Keep launch diagnostics even when am start or the status assertion fails.
# The previous gate stopped here without preserving start/logcat evidence.
set +e
adb shell am start -W -n "$PKG/$ACT" > "$OUT/start-1.txt" 2>&1
START_RC=$?
set -e
if [ "$START_RC" -ne 0 ] || ! grep -q 'Status: ok' "$OUT/start-1.txt"; then
  echo "START_1_FAILED rc=$START_RC" | tee "$OUT/start-1-failure.txt"
  adb shell dumpsys package "$PKG" > "$OUT/package-start-1.txt" 2>&1 || true
  adb shell dumpsys activity activities > "$OUT/activity-start-1.txt" 2>&1 || true
  adb logcat -d -v threadtime > "$OUT/logcat-start-1.txt" 2>&1 || true
  grep -E 'AndroidRuntime|FATAL EXCEPTION|Unable to start activity|Caused by:|MainActivity|SecurityException|Exception' "$OUT/logcat-start-1.txt" | tail -n 250 || true
  exit 1
fi
sleep 10

adb shell pidof "$PKG" > "$OUT/pid-1.txt" 2>&1
if ! test -s "$OUT/pid-1.txt"; then
  echo 'PID_1_FAILED' | tee "$OUT/pid-1-failure.txt"
  adb shell dumpsys activity activities > "$OUT/activity-pid-1.txt" 2>&1 || true
  adb logcat -d -v threadtime > "$OUT/logcat-pid-1.txt" 2>&1 || true
  exit 1
fi

adb shell uiautomator dump /sdcard/kunal-ui.xml > "$OUT/uiautomator-dump.txt" 2>&1
adb shell cat /sdcard/kunal-ui.xml > "$OUT/ui.xml" 2>&1
test -s "$OUT/ui.xml"
grep -q 'hierarchy' "$OUT/ui.xml"

adb shell dumpsys accessibility > "$OUT/accessibility.txt" 2>&1
grep -q 'UniversalAccessibilityService' "$OUT/accessibility.txt"

adb shell dumpsys package "$PKG" > "$OUT/package.txt" 2>&1
grep -q 'UniversalAccessibilityService' "$OUT/package.txt"

adb shell am force-stop "$PKG"
set +e
adb shell am start -W -n "$PKG/$ACT" > "$OUT/start-2.txt" 2>&1
START2_RC=$?
set -e
if [ "$START2_RC" -ne 0 ] || ! grep -q 'Status: ok' "$OUT/start-2.txt"; then
  echo "START_2_FAILED rc=$START2_RC" | tee "$OUT/start-2-failure.txt"
  adb logcat -d -v threadtime > "$OUT/logcat-start-2.txt" 2>&1 || true
  exit 1
fi
sleep 5
adb shell pidof "$PKG" > "$OUT/pid-2.txt"
test -s "$OUT/pid-2.txt"

adb logcat -d -v threadtime > "$OUT/logcat.txt" 2>&1
if grep -Eq 'FATAL EXCEPTION: main|Unable to start activity ComponentInfo\{com\.kunal\.universalvideo/com\.kunal\.universalvideo\.MainActivity\}|Process: com\.kunal\.universalvideo.*FATAL EXCEPTION' "$OUT/logcat.txt"; then
  echo 'FINAL MOBILE GATE: FAIL'
  grep -E 'AndroidRuntime|FATAL EXCEPTION|Unable to start activity|Caused by:|MainActivity' "$OUT/logcat.txt" | tail -n 250 || true
  exit 1
fi

echo 'FINAL MOBILE GATE: PASS'
echo 'INSTALL=PASS'
echo 'LAUNCH=PASS'
echo 'UI_RENDER=PASS'
echo 'ACCESSIBILITY_SERVICE=PASS'
echo 'RESTART=PASS'
echo 'CRASH_SCAN=PASS'
