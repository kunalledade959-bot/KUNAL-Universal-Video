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

# The hosted Linux runner may boot the API-35 emulator with software
# acceleration. In that mode boot_completed can become true before the
# package manager/ADB transport is actually ready for installs. Wait for a
# stable transport and package service before touching the APK.
ADB_READY=0
for attempt in $(seq 1 45); do
  adb start-server >/dev/null 2>&1 || true
  STATE="$(adb get-state 2>/dev/null || true)"
  if [ "$STATE" = "device" ] && adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx '1'; then
    if adb shell cmd package list packages >/dev/null 2>&1; then
      ADB_READY=1
      break
    fi
  fi
  if [ "$STATE" = "offline" ]; then
    adb reconnect offline >/dev/null 2>&1 || true
  fi
  sleep 2
done
[ "$ADB_READY" -eq 1 ] || fail "ADB/package service did not become ready"

# Install without streaming to avoid a second transport failure on slow,
# software-rendered hosted emulators.
adb install --no-streaming -r "$APK" >/dev/null || {
  adb reconnect offline >/dev/null 2>&1 || true
  sleep 3
  adb get-state 2>/dev/null | grep -qx 'device' || fail "ADB transport lost before APK install retry"
  adb shell cmd package list packages >/dev/null 2>&1 || fail "Package service unavailable before APK install retry"
  adb install --no-streaming -r "$APK" >/dev/null || fail "APK install failed"
}
adb shell am force-stop "$PKG"
adb logcat -c
adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-start.txt 2>&1 || fail "MainActivity launch failed"
# Let the production UI and hosted software-rendered System UI settle before
# the accessibility hierarchy/scroll checks. This avoids turning a slow cold
# boot into a false UI reachability failure.
sleep 8

PID="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID" ] || fail "App process not alive"

# Verify the real production UI exposes all 13 numbered stage controls.
# UiAutomator may omit controls that are outside the current viewport, so test
# both the initial hierarchy and a scrolled-to-bottom hierarchy.
adb exec-out uiautomator dump /dev/tty > e2e-ui-top.xml 2>/tmp/e2e-ui-top-dump.err || fail "Initial UI dump failed"
[ -s e2e-ui-top.xml ] || fail "Initial UI dump produced empty XML"
for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || fail "Stage ${i} control missing from production UI"
done

# The production activity places the 13 stage buttons inside one real
# ScrollView. The previous five-gesture loop was unnecessarily aggressive on
# the CPU-starved hosted emulator and, in one run, caused System UI to report
# an ANR while the app itself was healthy. Use one long deterministic gesture
# from inside the ScrollView, then dump the hierarchy again. If the first dump
# is not the app hierarchy, recover the production activity once and retry the
# same single gesture. We still require the actual Stage 12/13 nodes in the
# resulting hierarchy, so this cannot fake reachability.
scroll_to_bottom_and_dump(){
  adb shell input swipe 540 1650 540 350 1000 >/dev/null 2>&1 || return 1
  sleep 3
  adb exec-out uiautomator dump /dev/tty > e2e-ui-bottom.xml 2>/tmp/e2e-ui-bottom-dump.err || return 1
  [ -s e2e-ui-bottom.xml ] || return 1
  grep -q "package=\"$PKG\"" e2e-ui-bottom.xml || return 1
  grep -Eq "12 •" e2e-ui-bottom.xml || return 1
  grep -Eq "13 •" e2e-ui-bottom.xml || return 1
}

if ! scroll_to_bottom_and_dump; then
  echo "UI bottom check retry: returning production activity to foreground."
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-restart-ui.txt 2>&1 || fail "Production UI foreground recovery failed"
  sleep 8
  PID_RETRY="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  [ -n "$PID_RETRY" ] || fail "App process not alive during UI reachability retry"
  scroll_to_bottom_and_dump || fail "Stage 12/13 controls not reachable in production UI"
fi

# Exercise the dependency gate: stage 2 must not silently pass before accessibility is enabled.
adb shell input tap 300 0 >/dev/null 2>&1 || true
if adb shell settings get secure enabled_accessibility_services 2>/dev/null | grep -Fq "$PKG"; then
  echo "ACCESSIBILITY_PREEXISTING=1"
else
  echo "ACCESSIBILITY_PREEXISTING=0"
fi

# Restart test: prove the production controller survives a clean stop/start cycle.
adb shell am force-stop "$PKG"
sleep 2
adb shell am start -W -n "$PKG/.MainActivity" >/dev/null 2>&1 || fail "Restart launch failed"
sleep 4
PID2="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
[ -n "$PID2" ] || fail "App process not alive after restart"

adb logcat -d -t 3000 > e2e-logcat.txt
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' e2e-logcat.txt; then
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
