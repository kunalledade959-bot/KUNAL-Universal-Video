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

ADB_READY=0
for attempt in $(seq 1 120); do
  adb start-server >/dev/null 2>&1 || true
  state="$(adb get-state 2>/dev/null || true)"
  if [ "$state" = "device" ] && adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx '1'; then
    if adb shell cmd package list packages >/dev/null 2>&1; then ADB_READY=1; break; fi
  fi
  [ "$state" = "offline" ] && adb reconnect offline >/dev/null 2>&1 || true
  sleep 2
done
[ "$ADB_READY" -eq 1 ] || fail "ADB/package service did not become ready"

adb install --no-streaming -r "$APK" >/dev/null || fail "APK install failed"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb logcat -c
adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-start.txt 2>&1 || fail "MainActivity launch failed"
sleep 12
PID="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID" ] || fail "App process not alive"

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

recover_system_ui(){
  local xml="/tmp/system-ui-recovery.xml"
  for attempt in $(seq 1 24); do
    if dump_ui "$xml"; then
      if is_production_ui "$xml"; then return 0; fi
      if system_ui_anr "$xml"; then
        echo "SYSTEM_UI_ANR_DETECTED attempt=$attempt"
        adb shell input tap 540 1059 >/dev/null 2>&1 || true
        sleep 4
        continue
      fi
    fi
    sleep 2
done
  return 1
}

ensure_production_foreground(){
  local xml="$1"
  dump_ui "$xml" || return 1
  if is_production_ui "$xml"; then return 0; fi
  if system_ui_anr "$xml"; then
    recover_system_ui || return 1
  else
    adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
    sleep 2
    adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
    adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-relaunch.txt 2>&1 || return 1
    sleep 10
    recover_system_ui || true
  fi
  dump_ui "$xml" || return 1
  is_production_ui "$xml"
}

ensure_production_foreground e2e-ui-top.xml || fail "Production Activity not visible after launch/recovery"
for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || fail "Stage ${i} control missing from production UI"
done
echo "UI_TOP=PASS"

# Traverse the actual scroll container instead of assuming one swipe reaches
# stages 12/13. Each iteration records a fresh hierarchy. This avoids both
# false failures from a short swipe and false passes from stale XML.
BOTTOM_PASS=0
for attempt in $(seq 1 10); do
  ensure_production_foreground e2e-ui-scroll-${attempt}.xml || fail "Production UI lost during scroll attempt ${attempt}"
  xml="e2e-ui-scroll-${attempt}.xml"
  if grep -Eq "12 •" "$xml" && grep -Eq "13 •" "$xml"; then
    BOTTOM_PASS=1
    cp "$xml" e2e-ui-bottom.xml
    break
  fi
  adb shell input swipe 540 1680 540 260 900 >/dev/null 2>&1 || fail "Scroll input failed"
  sleep 4
done
[ "$BOTTOM_PASS" -eq 1 ] || fail "Stage 12/13 controls not reachable after 10 controlled scroll attempts"
echo "UI_BOTTOM=PASS"

ACCESSIBILITY_STATE="$(adb shell settings get secure enabled_accessibility_services 2>/dev/null | tr -d '\r' || true)"
if printf '%s' "$ACCESSIBILITY_STATE" | grep -Fq "$PKG"; then
  echo "ACCESSIBILITY_PREEXISTING=1"
else
  echo "ACCESSIBILITY_PREEXISTING=0"
fi

# Clean restart must return to production UI and keep the process alive.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
sleep 3
adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-restart-ui.txt 2>&1 || fail "Restart launch failed"
sleep 10
ensure_production_foreground e2e-ui-restart.xml || fail "Production Activity not visible after restart"
PID2="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID2" ] || fail "App process not alive after restart"

aadb_logcat="e2e-logcat.txt"
adb logcat -d -t 4000 > "$aadb_logcat"
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' "$aadb_logcat"; then
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
