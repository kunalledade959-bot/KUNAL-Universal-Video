#!/usr/bin/env bash
set -euo pipefail

APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
PASS="e2e-PASS.txt"
FAIL="e2e-FAIL.txt"
LOG="e2e-log.txt"

rm -f "$PASS" "$FAIL" "$LOG" e2e-ui*.xml e2e-ui*.err e2e-logcat.txt \
  e2e-accessibility.txt e2e-install.txt e2e-start.txt e2e-diagnostics-*.txt
exec > >(tee "$LOG") 2>&1

fail(){
  local reason="$1"
  echo "E2E_FAIL: $reason" | tee "$FAIL"
  exit 1
}

[ -s "$APK" ] || fail "APK missing"

# Every ADB operation is time-bounded. Emulator/ADB occasionally reports booted
# while the daemon is still unhealthy, so an unbounded shell call must never be
# allowed to stall the whole E2E job.
adb_once(){
  timeout 30s adb "$@"
}

adb_retry(){
  local attempts="${1:-10}"
  shift
  local i
  for ((i=1; i<=attempts; i++)); do
    if adb_once "$@"; then
      return 0
    fi
    sleep 2
  done
  return 1
}

capture_diagnostics(){
  echo "=== E2E DIAGNOSTICS ==="
  timeout 20s adb devices -l > e2e-diagnostics-devices.txt 2>&1 || true
  timeout 20s adb shell getprop sys.boot_completed > e2e-diagnostics-boot.txt 2>&1 || true
  timeout 20s adb shell getprop dev.bootcomplete >> e2e-diagnostics-boot.txt 2>&1 || true
  timeout 30s adb shell dumpsys package "$PKG" > e2e-diagnostics-package.txt 2>&1 || true
  timeout 30s adb shell dumpsys activity activities > e2e-diagnostics-activity.txt 2>&1 || true
  timeout 30s adb logcat -d -b crash > e2e-diagnostics-crash.txt 2>&1 || true
  timeout 30s adb logcat -d -t 1000 > e2e-diagnostics-logcat.txt 2>&1 || true
  echo "=== END E2E DIAGNOSTICS ==="
}

wait_for_adb_ready(){
  local ready_timeout="${1:-300}"
  local end=$((SECONDS + ready_timeout))
  local boot=""
  while (( SECONDS < end )); do
    if timeout 20s adb wait-for-device >/dev/null 2>&1; then
      boot="$(timeout 20s adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
      if [[ "$boot" == "1" ]] && timeout 20s adb shell 'echo KUV_ADB_READY' 2>/dev/null | grep -q 'KUV_ADB_READY'; then
        # Second health check prevents a transiently responding daemon from
        # being mistaken for a stable connection.
        if timeout 20s adb get-state 2>/dev/null | grep -q '^device$' && \
           timeout 20s adb shell 'echo KUV_ADB_HEALTHY' 2>/dev/null | grep -q 'KUV_ADB_HEALTHY'; then
          echo "ADB_READY=1"
          return 0
        fi
      fi
    fi
    sleep 2
  done
  echo "ADB readiness timeout after ${ready_timeout}s"
  capture_diagnostics
  return 1
}

wait_for_adb_ready 300 || fail "ADB did not become fully ready"

# Install with bounded retries and retain the actual installer output.
if ! adb_retry 8 install -r "$APK" >e2e-install.txt 2>&1; then
  capture_diagnostics
  fail "APK install failed"
fi

adb_retry 8 shell am force-stop "$PKG" || { capture_diagnostics; fail "Initial force-stop failed"; }
adb_retry 8 logcat -c || { capture_diagnostics; fail "Logcat clear failed"; }

if ! adb_retry 8 shell am start -W -n "$PKG/.MainActivity" >e2e-start.txt 2>&1; then
  capture_diagnostics
  fail "MainActivity launch failed"
fi
sleep 4

PID=""
for _ in $(seq 1 20); do
  PID="$(timeout 15s adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
  [[ -n "$PID" ]] && break
  sleep 2
done
if [[ -z "$PID" ]]; then
  capture_diagnostics
  fail "App process not alive"
fi
echo "APP_PID=$PID"

# Verify the real production UI exposes all 13 numbered stage controls.
# UiAutomator may omit controls outside the current viewport, so test both the
# initial hierarchy and a scrolled-to-bottom hierarchy.
if ! timeout 30s adb exec-out uiautomator dump /dev/tty >e2e-ui-top.xml 2>e2e-ui-top.err; then
  capture_diagnostics
  fail "Initial UI dump failed"
fi
[ -s e2e-ui-top.xml ] || { capture_diagnostics; fail "Initial UI dump produced empty XML"; }
for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || { capture_diagnostics; fail "Stage ${i} control missing from production UI"; }
done

for _ in $(seq 1 5); do
  adb_retry 6 shell input swipe 540 1650 540 350 500 >/dev/null 2>&1 || { capture_diagnostics; fail "UI scroll gesture failed"; }
  sleep 1
done
if ! timeout 30s adb exec-out uiautomator dump /dev/tty >e2e-ui-bottom.xml 2>e2e-ui-bottom.err; then
  capture_diagnostics
  fail "Bottom UI dump failed"
fi
[ -s e2e-ui-bottom.xml ] || { capture_diagnostics; fail "Bottom UI dump produced empty XML"; }
grep -Eq "12 •" e2e-ui-bottom.xml || { capture_diagnostics; fail "Stage 12 control not reachable in production UI"; }
grep -Eq "13 •" e2e-ui-bottom.xml || { capture_diagnostics; fail "Stage 13 control not reachable in production UI"; }

adb_retry 6 shell settings get secure enabled_accessibility_services >e2e-accessibility.txt 2>&1 || {
  capture_diagnostics
  fail "Accessibility state query failed"
}
if grep -Fq "$PKG" e2e-accessibility.txt; then
  echo "ACCESSIBILITY_PREEXISTING=1"
else
  echo "ACCESSIBILITY_PREEXISTING=0"
fi

# Restart test: prove the production controller survives a clean stop/start cycle.
adb_retry 8 shell am force-stop "$PKG" || { capture_diagnostics; fail "Restart force-stop failed"; }
sleep 2
if ! adb_retry 8 shell am start -W -n "$PKG/.MainActivity" >e2e-restart-start.txt 2>&1; then
  capture_diagnostics
  fail "Restart launch failed"
fi
sleep 4

PID2=""
for _ in $(seq 1 20); do
  PID2="$(timeout 15s adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
  [[ -n "$PID2" ]] && break
  sleep 2
done
if [[ -z "$PID2" ]]; then
  capture_diagnostics
  fail "App process not alive after restart"
fi
echo "APP_PID_AFTER_RESTART=$PID2"

if ! timeout 30s adb logcat -d -t 3000 >e2e-logcat.txt; then
  capture_diagnostics
  fail "Logcat capture failed"
fi
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' e2e-logcat.txt; then
  capture_diagnostics
  fail "Fatal crash evidence found"
fi

printf 'FULL_E2E_EMULATOR_GATE_PASS\nUI_13_STAGE_CONTROLS=PASS\nRESTART=PASS\nNO_FATAL_CRASH=PASS\nADB_READINESS=PASS\n' > "$PASS"
echo "FULL E2E GATE PASS"
