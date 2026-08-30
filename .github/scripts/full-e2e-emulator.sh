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

# Wait for both ADB transport and Android package manager. API-35 software
# emulators can report boot_completed before the device is actually usable.
ADB_READY=0
for attempt in $(seq 1 90); do
  adb start-server >/dev/null 2>&1 || true
  STATE="$(adb get-state 2>/dev/null || true)"
  if [ "$STATE" = "device" ] && adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx '1'; then
    if adb shell cmd package list packages >/dev/null 2>&1; then
      ADB_READY=1
      break
    fi
  fi
  if [ "$STATE" = "offline" ]; then adb reconnect offline >/dev/null 2>&1 || true; fi
  sleep 2
done
[ "$ADB_READY" -eq 1 ] || fail "ADB/package service did not become ready"

# Keep Android error dialogs from stealing the production UI gate on hosted
# emulator runs. This is test-environment configuration only and does not
# modify the application or its locked 13-stage production flow.
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
sleep 10

PID="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID" ] || fail "App process not alive"

# If Android System UI has an ANR/error surface in front of the app, return to
# Home and relaunch the production activity before judging the production UI.
# This prevents an emulator infrastructure fault from masquerading as a Stage
# 1/13 application regression.
recover_foreground(){
  local focus=""
  focus="$(adb shell dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus=|mFocusedApp=' | tail -n 2 || true)"
  if ! printf '%s\n' "$focus" | grep -Fq "$PKG"; then
    echo "Production activity not focused; performing controlled foreground recovery."
    adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
    sleep 2
    adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-foreground-recovery.txt 2>&1 || return 1
    sleep 8
  fi
  local current=""
  current="$(adb shell dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus=|mFocusedApp=' | tail -n 2 || true)"
  printf '%s\n' "$current" | grep -Fq "$PKG"
}

recover_foreground || fail "Production activity did not reach foreground after emulator UI recovery"

# Use a device-side UIAutomator dump file instead of exec-out /dev/tty. This is
# substantially more reliable when the software-rendered emulator is busy.
dump_ui(){
  local out="$1" remote="/sdcard/kuv-ui.xml"
  rm -f "$out"
  for attempt in $(seq 1 8); do
    adb shell uiautomator dump "$remote" >/tmp/uiautomator-dump.txt 2>"${out}.err" || true
    adb pull "$remote" "$out" >/dev/null 2>&1 || true
    if [ -s "$out" ] && grep -q '<hierarchy' "$out"; then return 0; fi
    sleep 2
  done
  return 1
}

# Initial hierarchy: stages 1..11 must be real controls in the production UI.
dump_ui e2e-ui-top.xml || fail "Initial UI hierarchy dump failed"
grep -q "package=\"$PKG\"" e2e-ui-top.xml || {
  recover_foreground || fail "Production activity lost foreground before initial UI verification"
  dump_ui e2e-ui-top.xml || fail "Initial UI hierarchy dump failed after foreground recovery"
  grep -q "package=\"$PKG\"" e2e-ui-top.xml || fail "Initial UI hierarchy is not production activity"
}
for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || fail "Stage ${i} control missing from production UI"
done

# Scroll only after the hierarchy is known to be the production Activity. One
# deterministic gesture plus a device-side dump avoids repeated UIAutomator
# process launches that can overwhelm a CPU-only hosted emulator.
scroll_and_check(){
  adb shell input swipe 540 1650 540 300 1500 >/dev/null 2>&1 || return 1
  sleep 5
  dump_ui e2e-ui-bottom.xml || return 1
  grep -q "package=\"$PKG\"" e2e-ui-bottom.xml || return 1
  grep -Eq "12 •" e2e-ui-bottom.xml || return 1
  grep -Eq "13 •" e2e-ui-bottom.xml || return 1
  return 0
}

if ! scroll_and_check; then
  echo "UI bottom check retry: returning production activity to foreground."
  recover_foreground || fail "Production UI foreground recovery failed"
  scroll_and_check || fail "Stage 12/13 controls not reachable in production UI"
fi

if adb shell settings get secure enabled_accessibility_services 2>/dev/null | grep -Fq "$PKG"; then
  echo "ACCESSIBILITY_PREEXISTING=1"
else
  echo "ACCESSIBILITY_PREEXISTING=0"
fi

# Restart test: production controller must survive a clean stop/start cycle.
adb shell am force-stop "$PKG"
sleep 3
adb shell am start -W -n "$PKG/.MainActivity" >/dev/null 2>&1 || fail "Restart launch failed"
sleep 6
PID2="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID2" ] || fail "App process not alive after restart"

adb logcat -d -t 4000 > e2e-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' e2e-logcat.txt; then
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
