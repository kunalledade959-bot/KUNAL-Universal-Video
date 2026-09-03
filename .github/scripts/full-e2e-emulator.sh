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
  timeout 30s adb shell dumpsys window windows > e2e-diagnostics-windows.txt 2>&1 || true
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

recover_systemui_anr(){
  local windows=""
  windows="$(timeout 30s adb shell dumpsys window windows 2>/dev/null || true)"
  if grep -Fq 'Application Not Responding: com.android.systemui' <<<"$windows" || \
     grep -Fq 'System UI isn\x27t responding' <<<"$windows"; then
    echo "SYSTEMUI_ANR_DETECTED=1"
    printf '%s\n' "$windows" > e2e-systemui-anr-windows.txt
    timeout 30s adb shell am force-stop com.android.systemui >/dev/null 2>&1 || true
    sleep 5
    adb_retry 6 shell 'echo KUV_SYSTEMUI_RECOVERED' >/dev/null 2>&1 || true
    echo "SYSTEMUI_ANR_RECOVERY_ATTEMPTED=1"
    return 0
  fi
  return 1
}

# A successful adb command is not enough for UIAutomator. It can return exit 0
# with a diagnostic string such as "Killed" when the UiAutomation service dies.
# Treat only a structurally valid hierarchy as a UI observation. This prevents
# infrastructure output from being misclassified as a missing app control.
dump_ui(){
  local output="$1"
  local error_file="${output%.xml}.err"
  local remote="/sdcard/kunal-ui-${RANDOM}-${RANDOM}.xml"
  local attempt
  rm -f "$output" "$error_file"
  for attempt in 1 2 3 4; do
    rm -f "$output" "$error_file"
    if timeout 35s adb shell "uiautomator dump --compressed '$remote'" >"$error_file" 2>&1; then
      if timeout 20s adb shell "cat '$remote'" >"$output" 2>>"$error_file" && \
         [ -s "$output" ] && \
         grep -Eq '^<\?xml|<hierarchy' "$output" && \
         grep -Fq '<hierarchy' "$output"; then
        timeout 10s adb shell "rm -f '$remote'" >/dev/null 2>&1 || true
        return 0
      fi
    fi
    timeout 10s adb shell "rm -f '$remote'" >/dev/null 2>&1 || true
    if recover_systemui_anr; then
      sleep 4
    else
      sleep 2
    fi
  done
  return 1
}

wait_for_adb_ready 300 || fail "ADB did not become fully ready"

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

recover_systemui_anr || true
sleep 2

# Verify the real production UI exposes all 13 numbered stage controls.
# UiAutomator may omit controls outside the current viewport, so test both the
# initial hierarchy and a scrolled-to-bottom hierarchy.
if ! dump_ui e2e-ui-top.xml; then
  capture_diagnostics
  fail "Initial UI hierarchy could not be obtained from UiAutomation"
fi

if grep -Fq 'System UI isn\x27t responding' e2e-ui-top.xml || \
   grep -Fq 'Application Not Responding: com.android.systemui' e2e-ui-top.xml; then
  capture_diagnostics
  echo 'E2E_FAIL: SystemUI remained unhealthy during production UI observation' | tee "$FAIL"
  exit 1
fi

for i in $(seq 1 11); do
  grep -Eq "${i} •" e2e-ui-top.xml || {
    if recover_systemui_anr; then
      sleep 4
      dump_ui e2e-ui-top.xml || true
    fi
    grep -Eq "${i} •" e2e-ui-top.xml || { capture_diagnostics; fail "Stage ${i} control missing from production UI"; }
  }
done

for _ in $(seq 1 5); do
  adb_retry 6 shell input swipe 540 1650 540 350 500 >/dev/null 2>&1 || { capture_diagnostics; fail "UI scroll gesture failed"; }
  sleep 1
done

if ! dump_ui e2e-ui-bottom.xml; then
  capture_diagnostics
  fail "Bottom UI hierarchy could not be obtained from UiAutomation"
fi

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
