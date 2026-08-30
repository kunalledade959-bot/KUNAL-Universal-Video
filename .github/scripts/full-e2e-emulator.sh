#!/usr/bin/env bash
set -euo pipefail
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
PASS="e2e-PASS.txt"
FAIL="e2e-FAIL.txt"
LOG="e2e-log.txt"
rm -f "$PASS" "$FAIL" "$LOG" e2e-ui*.xml e2e-ui*.err e2e-logcat.txt
exec > >(tee "$LOG") 2>&1

fail(){ echo "E2E_FAIL: $1" | tee "$FAIL"; exit 1; }
[ -s "$APK" ] || fail "APK missing"

# Hosted API-35 emulators can stay offline long after boot_completed is exposed.
ADB_READY=0
for attempt in $(seq 1 120); do
  adb start-server >/dev/null 2>&1 || true
  STATE="$(adb get-state 2>/dev/null || true)"
  if [ "$STATE" = "device" ] && adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx '1'; then
    if adb shell cmd package list packages >/dev/null 2>&1; then ADB_READY=1; break; fi
  fi
  [ "$STATE" = "offline" ] && adb reconnect offline >/dev/null 2>&1 || true
  sleep 2
done
[ "$ADB_READY" -eq 1 ] || fail "ADB/package service did not become ready"

# Test-only Android dialog suppression. Never changes the production APK.
adb shell settings put global show_first_crash_dialog 0 >/dev/null 2>&1 || true
adb shell settings put global anr_show_background 0 >/dev/null 2>&1 || true
adb shell settings put global hide_error_dialogs 1 >/dev/null 2>&1 || true

adb install --no-streaming -r "$APK" >/dev/null || {
  adb reconnect offline >/dev/null 2>&1 || true
  sleep 5
  adb get-state 2>/dev/null | grep -qx 'device' || fail "ADB transport lost before APK install retry"
  adb shell cmd package list packages >/dev/null 2>&1 || fail "Package service unavailable before APK install retry"
  adb install --no-streaming -r "$APK" >/dev/null || fail "APK install failed"
}

adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb logcat -c
adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-start.txt 2>&1 || fail "MainActivity launch failed"
sleep 12
PID="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID" ] || fail "App process not alive"

# UI hierarchy is the source of truth. Do not fail merely because dumpsys uses
# a different Android-15 focus representation. If another system surface is on
# top, recover to Home and relaunch the production Activity, then inspect again.
dump_ui(){
  local out="$1" remote="/sdcard/kuv-ui.xml"
  rm -f "$out"
  for attempt in $(seq 1 10); do
    adb shell uiautomator dump "$remote" >/tmp/uiautomator-dump.txt 2>"${out}.err" || true
    adb pull "$remote" "$out" >/dev/null 2>&1 || true
    if [ -s "$out" ] && grep -q '<hierarchy' "$out"; then return 0; fi
    sleep 2
  done
  return 1
}

relaunch_production(){
  adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
  sleep 2
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-relaunch.txt 2>&1 || return 1
  sleep 12
  local p
  p="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  [ -n "$p" ]
}

# Initial production hierarchy. The package check is evidence-based.
dump_ui e2e-ui-top.xml || fail "Initial UI hierarchy dump failed"
if ! grep -q "package=\"$PKG\"" e2e-ui-top.xml; then
  echo "Initial hierarchy is not production UI; performing controlled relaunch."
  relaunch_production || fail "Production Activity relaunch failed"
  dump_ui e2e-ui-top.xml || fail "Initial UI hierarchy dump failed after relaunch"
  grep -q "package=\"$PKG\"" e2e-ui-top.xml || fail "Initial UI hierarchy is not production activity"
fi

for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || fail "Stage ${i} control missing from production UI"
done

echo "UI_TOP=PASS"

# One controlled scroll, then a second evidence-based hierarchy dump.
check_bottom(){
  adb shell input swipe 540 1650 540 300 1500 >/dev/null 2>&1 || return 1
  sleep 6
  dump_ui e2e-ui-bottom.xml || return 1
  grep -q "package=\"$PKG\"" e2e-ui-bottom.xml || return 1
  grep -Eq "12 •" e2e-ui-bottom.xml || return 1
  grep -Eq "13 •" e2e-ui-bottom.xml || return 1
}

if ! check_bottom; then
  echo "Bottom UI not verified; performing one controlled production relaunch."
  relaunch_production || fail "Production Activity recovery failed"
  dump_ui e2e-ui-top-recovery.xml || fail "Recovery UI hierarchy dump failed"
  grep -q "package=\"$PKG\"" e2e-ui-top-recovery.xml || fail "Recovery hierarchy is not production activity"
  for i in $(seq 1 11); do grep -Eq "${i} •" e2e-ui-top-recovery.xml || fail "Stage ${i} control missing after recovery"; done
  check_bottom || fail "Stage 12/13 controls not reachable in production UI"
fi

echo "UI_BOTTOM=PASS"

if adb shell settings get secure enabled_accessibility_services 2>/dev/null | grep -Fq "$PKG"; then
  echo "ACCESSIBILITY_PREEXISTING=1"
else
  echo "ACCESSIBILITY_PREEXISTING=0"
fi

# Clean restart test.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
sleep 3
adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-restart-ui.txt 2>&1 || fail "Restart launch failed"
sleep 8
PID2="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID2" ] || fail "App process not alive after restart"

adb logcat -d -t 4000 > e2e-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' e2e-logcat.txt; then
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
