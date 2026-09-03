#!/usr/bin/env bash
set -euo pipefail
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
PASS="e2e-PASS.txt"
FAIL="e2e-FAIL.txt"
LOG="e2e-log.txt"
rm -f "$PASS" "$FAIL" "$LOG" e2e-ui*.xml e2e-ui*.err e2e-logcat.txt e2e-accessibility.txt
exec > >(tee "$LOG") 2>&1

fail(){ echo "E2E_FAIL: $1" | tee "$FAIL"; exit 1; }
[ -s "$APK" ] || fail "APK missing"

# The emulator runner normally waits for boot, but ADB can briefly remain
# offline after boot_completed. Treat ADB readiness as a first-class gate.
wait_for_adb_ready(){
  local timeout="${1:-180}"
  local end=$((SECONDS + timeout))
  local boot=""
  while (( SECONDS < end )); do
    if adb wait-for-device >/dev/null 2>&1; then
      boot="$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
      if [[ "$boot" == "1" ]] && adb shell 'echo KUV_ADB_READY' 2>/dev/null | grep -q 'KUV_ADB_READY'; then
        echo "ADB_READY=1"
        return 0
      fi
    fi
    sleep 2
  done
  echo "ADB readiness timeout"
  adb devices -l || true
  adb shell getprop sys.boot_completed 2>&1 || true
  adb shell getprop dev.bootcomplete 2>&1 || true
  return 1
}

adb_retry(){
  local attempts="${1:-30}"
  shift
  local i
  for ((i=1;i<=attempts;i++)); do
    if "$@"; then return 0; fi
    sleep 2
  done
  return 1
}

wait_for_adb_ready 180 || fail "ADB did not become fully ready"

adb_retry 30 adb install -r "$APK" >/dev/null || fail "APK install failed"
adb_retry 15 adb shell am force-stop "$PKG" || fail "Initial force-stop failed"
adb_retry 15 adb logcat -c || fail "Logcat clear failed"
adb_retry 15 adb shell am start -W -n "$PKG/.MainActivity" >/tmp/e2e-start.txt 2>&1 || fail "MainActivity launch failed"
sleep 4

PID=""
for _ in $(seq 1 15); do
  PID="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
  [[ -n "$PID" ]] && break
  sleep 2
done
[ -n "$PID" ] || fail "App process not alive"

# Verify the real production UI exposes all 13 numbered stage controls.
# UiAutomator may omit controls that are outside the current viewport, so test
# both the initial hierarchy and a scrolled-to-bottom hierarchy.
adb_retry 10 adb exec-out uiautomator dump /dev/tty > e2e-ui-top.xml 2>/tmp/e2e-ui-top-dump.err || fail "Initial UI dump failed"
[ -s e2e-ui-top.xml ] || fail "Initial UI dump produced empty XML"
for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || fail "Stage ${i} control missing from production UI"
done

# Scroll the production ScrollView through several positions and retain the
# last hierarchy. This proves stages 12 and 13 are reachable, not merely in source.
for n in 1 2 3 4 5; do
  adb_retry 10 adb shell input swipe 540 1650 540 350 500 >/dev/null 2>&1 || fail "UI scroll gesture failed"
  sleep 1
done
adb_retry 10 adb exec-out uiautomator dump /dev/tty > e2e-ui-bottom.xml 2>/tmp/e2e-ui-bottom-dump.err || fail "Bottom UI dump failed"
[ -s e2e-ui-bottom.xml ] || fail "Bottom UI dump produced empty XML"
grep -Eq "12 •" e2e-ui-bottom.xml || fail "Stage 12 control not reachable in production UI"
grep -Eq "13 •" e2e-ui-bottom.xml || fail "Stage 13 control not reachable in production UI"

# Query accessibility state only after ADB has been proven ready, and retry the
# query because Android settings can still transiently reject the first shell.
adb_retry 10 adb shell settings get secure enabled_accessibility_services >e2e-accessibility.txt 2>&1 || fail "Accessibility state query failed"
if grep -Fq "$PKG" e2e-accessibility.txt; then
  echo "ACCESSIBILITY_PREEXISTING=1"
else
  echo "ACCESSIBILITY_PREEXISTING=0"
fi

# Restart test: prove the production controller survives a clean stop/start cycle.
adb_retry 15 adb shell am force-stop "$PKG" || fail "Restart force-stop failed"
sleep 2
adb_retry 15 adb shell am start -W -n "$PKG/.MainActivity" >/dev/null 2>&1 || fail "Restart launch failed"
sleep 4
PID2=""
for _ in $(seq 1 15); do
  PID2="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
  [[ -n "$PID2" ]] && break
  sleep 2
done
[ -n "$PID2" ] || fail "App process not alive after restart"

adb_retry 10 adb logcat -d -t 3000 > e2e-logcat.txt || fail "Logcat capture failed"
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' e2e-logcat.txt; then
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\nADB_READINESS=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
