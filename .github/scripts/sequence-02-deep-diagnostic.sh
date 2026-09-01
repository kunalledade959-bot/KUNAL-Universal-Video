#!/usr/bin/env bash
set -u

PKG="com.kunal.universalvideo"
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
REPORT="sequence-02-deep-diagnostic.txt"
LOGCAT="sequence-02-logcat.txt"
UI="sequence-02-ui.xml"
: > "$REPORT"
: > "$LOGCAT"

pass(){ printf 'PASS|%s|%s\n' "$1" "$2" | tee -a "$REPORT"; }
fail(){ printf 'FAIL|%s|%s\n' "$1" "$2" | tee -a "$REPORT"; }
info(){ printf 'INFO|%s|%s\n' "$1" "$2" | tee -a "$REPORT"; }
check(){ if "$@" >/dev/null 2>&1; then pass "$1" "ok"; else fail "$1" "failed"; fi; }

printf 'SEQUENCE_02_DEEP_DIAGNOSTIC_V1\n' | tee -a "$REPORT"
info "timestamp" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
info "package" "$PKG"

# Source/build evidence. This script never edits source files.
[ -s "$APK" ] && pass "APK_PRESENT" "$APK" || fail "APK_PRESENT" "missing"
if [ -s "$APK" ]; then
  sha256sum "$APK" | tee -a "$REPORT"
fi

# Device transport and package-manager health.
check "ADB_DEVICE" adb get-state
check "BOOT_COMPLETED" bash -c "test \"\$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\\r')\" = 1"
check "PACKAGE_MANAGER" adb shell cmd package list packages
check "APP_INSTALLED" adb shell pm path "$PKG"
check "MAIN_ACTIVITY_RESOLVES" adb shell cmd package resolve-activity --brief "$PKG/.MainActivity"

# Manifest/service declarations and runtime service discovery.
if adb shell dumpsys package "$PKG" > sequence-02-package-dumpsys.txt 2>&1; then
  grep -q "UniversalAccessibilityService" sequence-02-package-dumpsys.txt && pass "ACCESSIBILITY_SERVICE_DECLARED" "found" || fail "ACCESSIBILITY_SERVICE_DECLARED" "not found"
  grep -q "android.accessibilityservice.AccessibilityService" sequence-02-package-dumpsys.txt && pass "ACCESSIBILITY_INTENT_DECLARED" "found" || fail "ACCESSIBILITY_INTENT_DECLARED" "not found"
  grep -q "BIND_ACCESSIBILITY_SERVICE" sequence-02-package-dumpsys.txt && pass "BIND_ACCESSIBILITY_PERMISSION" "found" || fail "BIND_ACCESSIBILITY_PERMISSION" "not found"
else
  fail "PACKAGE_DUMPSYS" "unavailable"
fi

# Accessibility state: enabled, installed service, and actual bound service.
ENABLED="$(adb shell settings get secure enabled_accessibility_services 2>/dev/null | tr -d '\r' || true)"
info "ENABLED_ACCESSIBILITY_SERVICES" "$ENABLED"
echo "$ENABLED" | grep -Fq "$PKG" && pass "ACCESSIBILITY_ENABLED_FOR_APP" "package present" || fail "ACCESSIBILITY_ENABLED_FOR_APP" "package absent"

adb shell dumpsys accessibility > sequence-02-accessibility.txt 2>&1 || true
grep -Fq "$PKG" sequence-02-accessibility.txt && pass "ACCESSIBILITY_RUNTIME_SERVICE_VISIBLE" "package visible" || fail "ACCESSIBILITY_RUNTIME_SERVICE_VISIBLE" "package not visible"
grep -Fq "UniversalAccessibilityService" sequence-02-accessibility.txt && pass "ACCESSIBILITY_RUNTIME_CLASS_VISIBLE" "class visible" || fail "ACCESSIBILITY_RUNTIME_CLASS_VISIBLE" "class not visible"

# Launch production app and collect fresh runtime evidence.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb logcat -c >/dev/null 2>&1 || true
adb shell am start -W -n "$PKG/.MainActivity" > sequence-02-launch.txt 2>&1
sleep 8
adb shell uiautomator dump /sdcard/sequence-02-ui.xml >/dev/null 2>&1 || true
adb pull /sdcard/sequence-02-ui.xml "$UI" >/dev/null 2>&1 || true
[ -s "$UI" ] && pass "UI_HIERARCHY" "captured" || fail "UI_HIERARCHY" "missing"

PID="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID" ] && pass "APP_PROCESS_ALIVE" "$PID" || fail "APP_PROCESS_ALIVE" "no pid"

# Verify the actual Stage-2 control and visible diagnostic status.
if [ -s "$UI" ]; then
  grep -q '2 • ENABLE ACCESSIBILITY / CONNECT' "$UI" && pass "STAGE_02_CONTROL_VISIBLE" "found" || fail "STAGE_02_CONTROL_VISIBLE" "missing"
  grep -q 'Stage 2' "$UI" && pass "STAGE_02_STATUS_VISIBLE" "found" || info "STAGE_02_STATUS_VISIBLE" "not found in current hierarchy"
fi

# Inspect app-side runtime flags from logcat where available.
adb logcat -d -t 6000 > "$LOGCAT" 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\.kunal\.universalvideo.*has died' "$LOGCAT"; then
  fail "FATAL_CRASH" "fatal exception evidence found"
else
  pass "FATAL_CRASH" "none found"
fi

# Bridge socket check from the device itself. This is deliberately diagnostic:
# a listening socket alone is NOT accepted as a successful mobile connection.
adb shell "(command -v toybox >/dev/null 2>&1 && toybox nc -z 127.0.0.1 8765)" >/dev/null 2>&1 && pass "BRIDGE_PORT_8765" "reachable" || info "BRIDGE_PORT_8765" "not reachable via device nc"

# If the APK exposes a local HTTP health endpoint, query it from the device.
HEALTH="$(adb shell 'toybox wget -qO- http://127.0.0.1:8765/health 2>/dev/null || true' | tr -d '\r')"
if [ -n "$HEALTH" ]; then
  pass "BRIDGE_HEALTH_ENDPOINT" "$HEALTH"
  echo "$HEALTH" | grep -q 'kunal-video-v1' && pass "BRIDGE_PROTOCOL" "kunal-video-v1" || fail "BRIDGE_PROTOCOL" "unexpected protocol"
  echo "$HEALTH" | grep -q 'session_id' && pass "BRIDGE_SESSION_ID" "present" || fail "BRIDGE_SESSION_ID" "missing"
else
  info "BRIDGE_HEALTH_ENDPOINT" "no response"
fi

# Produce a compact final verdict. Any hard FAIL means the diagnostic is not a
# false PASS and the next step must be root-cause repair, not APK delivery.
if grep -q '^FAIL|' "$REPORT"; then
  echo 'SEQUENCE_02_DEEP_DIAGNOSTIC=FAIL' | tee -a "$REPORT"
  exit 1
fi

echo 'SEQUENCE_02_DEEP_DIAGNOSTIC=PASS' | tee -a "$REPORT"
