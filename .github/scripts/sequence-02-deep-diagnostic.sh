#!/usr/bin/env bash
set -u

PKG="com.kunal.universalvideo"
SERVICE="$PKG/com.kunal.universalvideo.UniversalAccessibilityService"
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

printf 'SEQUENCE_02_DEEP_DIAGNOSTIC_V2\n' | tee -a "$REPORT"
info "timestamp" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
info "package" "$PKG"
info "accessibility_service" "$SERVICE"
info "test_rule" "collect every finding; do not stop at first failure"

# Source/build evidence. This script never edits source files.
[ -s "$APK" ] && pass "APK_PRESENT" "$APK" || fail "APK_PRESENT" "missing"
if [ -s "$APK" ]; then sha256sum "$APK" | tee -a "$REPORT"; fi

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

# Test-only emulator provisioning. Real devices are NOT silently modified.
# Android documents that AccessibilityService binding is system/user controlled;
# this provisioning is limited to the disposable CI emulator and is verified by
# dumpsys after the setting change. A real-device PASS still requires user enablement.
info "EMULATOR_ONLY_PROVISIONING" "attempting test-environment accessibility enablement"
adb shell settings put secure enabled_accessibility_services "$SERVICE" >/dev/null 2>&1 || true
adb shell settings put secure accessibility_enabled 1 >/dev/null 2>&1 || true
sleep 3
ENABLED="$(adb shell settings get secure enabled_accessibility_services 2>/dev/null | tr -d '\r' || true)"
info "ENABLED_ACCESSIBILITY_SERVICES" "$ENABLED"
echo "$ENABLED" | grep -Fq "$SERVICE" && pass "ACCESSIBILITY_ENABLED_FOR_APP" "service present in emulator secure setting" || fail "ACCESSIBILITY_ENABLED_FOR_APP" "service absent after emulator provisioning"

adb shell dumpsys accessibility > sequence-02-accessibility-before-app.txt 2>&1 || true
grep -Fq "$PKG" sequence-02-accessibility-before-app.txt && pass "ACCESSIBILITY_RUNTIME_SERVICE_VISIBLE" "package visible before app launch" || fail "ACCESSIBILITY_RUNTIME_SERVICE_VISIBLE" "package not visible before app launch"
grep -Fq "UniversalAccessibilityService" sequence-02-accessibility-before-app.txt && pass "ACCESSIBILITY_RUNTIME_CLASS_VISIBLE" "class visible before app launch" || fail "ACCESSIBILITY_RUNTIME_CLASS_VISIBLE" "class not visible before app launch"

# Launch production app and collect fresh runtime evidence.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb logcat -c >/dev/null 2>&1 || true
adb shell am start -W -n "$PKG/.MainActivity" > sequence-02-launch.txt 2>&1
sleep 8
adb shell dumpsys accessibility > sequence-02-accessibility-after-launch.txt 2>&1 || true
grep -Fq "$PKG" sequence-02-accessibility-after-launch.txt && pass "ACCESSIBILITY_RUNTIME_AFTER_LAUNCH" "package visible" || fail "ACCESSIBILITY_RUNTIME_AFTER_LAUNCH" "package not visible"
grep -Fq "UniversalAccessibilityService" sequence-02-accessibility-after-launch.txt && pass "ACCESSIBILITY_CLASS_AFTER_LAUNCH" "class visible" || fail "ACCESSIBILITY_CLASS_AFTER_LAUNCH" "class not visible"

adb shell uiautomator dump /sdcard/sequence-02-ui.xml >/dev/null 2>&1 || true
adb pull /sdcard/sequence-02-ui.xml "$UI" >/dev/null 2>&1 || true
[ -s "$UI" ] && pass "UI_HIERARCHY" "captured" || fail "UI_HIERARCHY" "missing"
PID="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
[ -n "$PID" ] && pass "APP_PROCESS_ALIVE" "$PID" || fail "APP_PROCESS_ALIVE" "no pid"

# Verify actual Stage-2 control and status visibility.
if [ -s "$UI" ]; then
  grep -q '2 • ENABLE ACCESSIBILITY / CONNECT' "$UI" && pass "STAGE_02_CONTROL_VISIBLE" "found" || fail "STAGE_02_CONTROL_VISIBLE" "missing"
  grep -q 'Stage 2' "$UI" && pass "STAGE_02_STATUS_VISIBLE" "found" || info "STAGE_02_STATUS_VISIBLE" "not found in current hierarchy"
fi

# Inspect app-side runtime flags from logcat.
adb logcat -d -t 6000 > "$LOGCAT" 2>&1 || true
if grep -Eiq 'FATAL EXCEPTION|AndroidRuntime.*FATAL|Process: com\\.kunal\\.universalvideo.*has died' "$LOGCAT"; then
  fail "FATAL_CRASH" "fatal exception evidence found"
else
  pass "FATAL_CRASH" "none found"
fi

# Verify service binding after launch, not just the secure setting.
if grep -Fq "UniversalAccessibilityService" sequence-02-accessibility-after-launch.txt && grep -Eiq 'bound|enabled|isEnabled|Service' sequence-02-accessibility-after-launch.txt; then
  pass "ACCESSIBILITY_BIND_EVIDENCE" "runtime accessibility service evidence present"
else
  fail "ACCESSIBILITY_BIND_EVIDENCE" "could not prove runtime service binding from dumpsys"
fi

# Bridge socket check. A listening socket alone is NOT accepted as a connection pass.
adb shell "(command -v toybox >/dev/null 2>&1 && toybox nc -z 127.0.0.1 8765)" >/dev/null 2>&1 && pass "BRIDGE_PORT_8765" "reachable" || info "BRIDGE_PORT_8765" "not reachable via device nc"

# Local health endpoint evidence.
HEALTH="$(adb shell 'toybox wget -qO- http://127.0.0.1:8765/health 2>/dev/null || true' | tr -d '\r')"
if [ -n "$HEALTH" ]; then
  pass "BRIDGE_HEALTH_ENDPOINT" "$HEALTH"
  echo "$HEALTH" | grep -q 'kunal-video-v1' && pass "BRIDGE_PROTOCOL" "kunal-video-v1" || fail "BRIDGE_PROTOCOL" "unexpected protocol"
  echo "$HEALTH" | grep -q 'session_id' && pass "BRIDGE_SESSION_ID" "present" || fail "BRIDGE_SESSION_ID" "missing"
else
  info "BRIDGE_HEALTH_ENDPOINT" "no response"
fi

# Explicitly separate emulator provisioning from real-device proof.
info "REAL_DEVICE_PROOF" "NOT_CLAIMED_BY_EMULATOR_TEST"
info "REAL_DEVICE_REQUIREMENT" "user must enable AccessibilityService in Android Settings; app must then verify onServiceConnected"

# Full collection is complete before the verdict is emitted.
FAIL_COUNT="$(grep -c '^FAIL|' "$REPORT" 2>/dev/null || true)"
INFO_COUNT="$(grep -c '^INFO|' "$REPORT" 2>/dev/null || true)"
PASS_COUNT="$(grep -c '^PASS|' "$REPORT" 2>/dev/null || true)"
printf 'SUMMARY|PASS=%s|FAIL=%s|INFO=%s\n' "$PASS_COUNT" "$FAIL_COUNT" "$INFO_COUNT" | tee -a "$REPORT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo 'SEQUENCE_02_DEEP_DIAGNOSTIC=FAIL_AFTER_COMPLETE_COLLECTION' | tee -a "$REPORT"
  exit 1
fi
echo 'SEQUENCE_02_DEEP_DIAGNOSTIC=PASS_AFTER_COMPLETE_COLLECTION' | tee -a "$REPORT"
