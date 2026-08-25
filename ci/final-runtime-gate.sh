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
for i in $(seq 1 60); do
  if [ "$(adb get-state 2>/dev/null || true)" = device ]; then
    break
  fi
  sleep 2
done

test "$(adb get-state)" = device
adb shell getprop sys.boot_completed | grep -q 1
adb shell pm uninstall "$PKG" >/dev/null 2>&1 || true
adb logcat -c

adb install "$APK" > "$OUT/install.txt" 2>&1
grep -q '^Success' "$OUT/install.txt"

echo "$SERVICE" > "$OUT/service.txt"
adb shell settings put secure enabled_accessibility_services "$SERVICE"
adb shell settings put secure accessibility_enabled 1

adb shell cmd package resolve-activity --brief "$PKG" > "$OUT/resolve.txt" 2>&1
grep -q "$ACT" "$OUT/resolve.txt"

adb shell am start -W -n "$PKG/$ACT" > "$OUT/start-1.txt" 2>&1
grep -q 'Status: ok' "$OUT/start-1.txt"
sleep 10

adb shell pidof "$PKG" > "$OUT/pid-1.txt"
test -s "$OUT/pid-1.txt"

adb shell uiautomator dump /sdcard/kunal-ui.xml > "$OUT/uiautomator-dump.txt" 2>&1
adb shell cat /sdcard/kunal-ui.xml > "$OUT/ui.xml" 2>&1
test -s "$OUT/ui.xml"
grep -q 'hierarchy' "$OUT/ui.xml"

adb shell dumpsys accessibility > "$OUT/accessibility.txt" 2>&1
grep -q 'UniversalAccessibilityService' "$OUT/accessibility.txt"

adb shell dumpsys package "$PKG" > "$OUT/package.txt" 2>&1
grep -q 'UniversalAccessibilityService' "$OUT/package.txt"

adb shell am force-stop "$PKG"
adb shell am start -W -n "$PKG/$ACT" > "$OUT/start-2.txt" 2>&1
grep -q 'Status: ok' "$OUT/start-2.txt"
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
