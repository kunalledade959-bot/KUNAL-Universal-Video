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
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-restart-ui.txt 2>&1 || fail "Production UI foreground recovery failed"
  sleep 10
  PID_RETRY="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  [ -n "$PID_RETRY" ] || fail "App process not alive during UI reachability retry"
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
