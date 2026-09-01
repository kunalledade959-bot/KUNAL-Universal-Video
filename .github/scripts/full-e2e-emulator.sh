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

# Hosted API-35 emulators can expose boot_completed while ADB/package services
# are still unavailable. Wait for the complete device state, not just boot.
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

# Test-only settings. They do not modify the production APK.
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

# UI hierarchy is the runtime source of truth. Android's System UI can show
# its own ANR dialog on slow software emulators even while the production app
# is healthy. Recovery must wait for that dialog to disappear before judging
# the production hierarchy.
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

is_production_ui(){
  local xml="$1"
  grep -q "package=\"$PKG\"" "$xml" && grep -q "Kunal Universal Video" "$xml"
}

system_ui_anr(){
  local xml="$1"
  grep -Fq "System UI isn't responding" "$xml"
}

wait_out_system_ui_anr(){
  local xml="/tmp/system-ui-recovery.xml"
  for attempt in $(seq 1 18); do
    if ! dump_ui "$xml"; then
      sleep 3
      continue
    fi
    if is_production_ui "$xml"; then
      echo "SYSTEM_UI_RECOVERY=PASS"
      return 0
    fi
    if system_ui_anr "$xml"; then
      echo "SYSTEM_UI_ANR_DETECTED=1 attempt=$attempt"
      # Stable Pixel 2 dialog bounds: Wait button is the lower half of the
      # dialog. Repeat Wait rather than falsely treating the dialog as app UI.
      adb shell input tap 540 1059 >/dev/null 2>&1 || true
      sleep 5
      continue
    fi
    sleep 3
  done
  return 1
}

relaunch_production(){
  adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
  sleep 2
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-relaunch.txt 2>&1 || return 1
  sleep 10

  # Do not stop after one ANR tap. Keep recovering until the actual production
  # hierarchy is visible or the bounded recovery window is exhausted.
  if ! wait_out_system_ui_anr; then
    # One final explicit foreground request handles a launcher/system-ui race.
    adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-relaunch-final.txt 2>&1 || true
    sleep 8
    wait_out_system_ui_anr || return 1
  fi

  local p
  p="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  [ -n "$p" ] || return 1
  adb shell dumpsys activity activities 2>/dev/null | grep -Fq "$PKG" || return 1
  return 0
}

# Initial production hierarchy.
dump_ui e2e-ui-top.xml || fail "Initial UI hierarchy dump failed"
if ! is_production_ui e2e-ui-top.xml; then
  if system_ui_anr e2e-ui-top.xml; then
    echo "Initial System UI ANR detected; entering bounded recovery."
  else
    echo "Initial hierarchy is not production UI; performing controlled relaunch."
  fi
  relaunch_production || fail "Production Activity relaunch failed"
  dump_ui e2e-ui-top.xml || fail "Initial UI hierarchy dump failed after relaunch"
  is_production_ui e2e-ui-top.xml || fail "Initial UI hierarchy is not production activity"
fi

for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || fail "Stage ${i} control missing from production UI"
done

echo "UI_TOP=PASS"

# One controlled scroll. If System UI ANR appears during the scroll, recover
# first and then perform the same evidence check again.
check_bottom_once(){
  adb shell input swipe 540 1650 540 300 1500 >/dev/null 2>&1 || return 1
  sleep 6
  dump_ui e2e-ui-bottom.xml || return 1
  if system_ui_anr e2e-ui-bottom.xml; then
    echo "BOTTOM_SYSTEM_UI_ANR=1"
    return 2
  fi
  is_production_ui e2e-ui-bottom.xml || return 1
  grep -Eq "12 •" e2e-ui-bottom.xml || return 1
  grep -Eq "13 •" e2e-ui-bottom.xml || return 1
  return 0
}

check_bottom(){
  local rc
  check_bottom_once && return 0
  rc=$?
  if [ "$rc" -eq 2 ]; then
    echo "Bottom UI hit System UI ANR; recovering without declaring production failure."
    wait_out_system_ui_anr || return 1
  fi
  # After recovery the app may be back at the top. Re-issue the controlled
  # scroll and require fresh stage 12/13 evidence.
  check_bottom_once
}

if ! check_bottom; then
  echo "Bottom UI not verified; performing one controlled production relaunch."
  relaunch_production || fail "Production Activity recovery failed"
  dump_ui e2e-ui-top-recovery.xml || fail "Recovery UI hierarchy dump failed"
  is_production_ui e2e-ui-top-recovery.xml || fail "Recovery hierarchy is not production activity"
  for i in $(seq 1 11); do
    grep -Eq "${i} •" e2e-ui-top-recovery.xml || fail "Stage ${i} control missing after recovery"
  done
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
if ! wait_out_system_ui_anr; then
  # A restart without a System UI dialog still needs a live production process.
  PID2="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  [ -n "$PID2" ] || fail "App process not alive after restart"
else
  PID2="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  [ -n "$PID2" ] || fail "App process not alive after restart recovery"
fi

adb logcat -d -t 4000 > e2e-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' e2e-logcat.txt; then
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
