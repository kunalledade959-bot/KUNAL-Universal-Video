#!/usr/bin/env bash
set -u
mkdir -p "$GITHUB_WORKSPACE/runtime-evidence" "$GITHUB_WORKSPACE/final-apk"
APK_FILE="$GITHUB_WORKSPACE/built-apk/KUNAL-Universal-Video-debug.apk"
[ -s "$APK_FILE" ] || { echo PREBUILT_APK_MISSING; exit 20; }
AAPT="$(command -v aapt || true)"
[ -n "$AAPT" ] || AAPT="$(find "${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/opt/android-sdk}}/build-tools" -type f -name aapt -perm -111 -print -quit 2>/dev/null || true)"
[ -n "$AAPT" ] || { echo AAPT_MISSING; exit 21; }
BADGING="$GITHUB_WORKSPACE/runtime-evidence/badging.txt"
"$AAPT" dump badging "$APK_FILE" > "$BADGING" 2>&1 || { cat "$BADGING"; echo APK_BADGING_FAILED; exit 22; }
PACKAGE="$(sed -n "s/^package: name='\([^']*\)'.*/\1/p" "$BADGING" | head -n1)"
ACTIVITY="$(sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" "$BADGING" | head -n1)"
echo "PACKAGE=$PACKAGE"; echo "ACTIVITY=$ACTIVITY"
[ -n "$PACKAGE" ] && [ -n "$ACTIVITY" ] || { echo APK_METADATA_INVALID; exit 23; }
for i in $(seq 1 120); do
  state="$(adb -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)"
  [ "$state" = device ] && break
  sleep 2
done
[ "$(adb -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)" = device ] || { adb devices -l || true; echo ADB_NOT_READY; exit 30; }
adb devices -l > "$GITHUB_WORKSPACE/runtime-evidence/adb.txt" 2>&1 || true
adb shell getprop sys.boot_completed > "$GITHUB_WORKSPACE/runtime-evidence/boot.txt" 2>&1 || true
adb logcat -c || true
adb uninstall "$PACKAGE" >/dev/null 2>&1 || true
adb install "$APK_FILE" > "$GITHUB_WORKSPACE/runtime-evidence/install.log" 2>&1 || { cat "$GITHUB_WORKSPACE/runtime-evidence/install.log"; echo INSTALL_FAIL; exit 31; }
echo INSTALL_PASS
launch_and_verify() {
  local label="$1"; local i pid focused; local launch_log="$GITHUB_WORKSPACE/runtime-evidence/${label,,}.log"; local logcat_file="$GITHUB_WORKSPACE/runtime-evidence/${label,,}-logcat.txt"
  timeout 60s adb shell am start -n "$PACKAGE/$ACTIVITY" > "$launch_log" 2>&1 || true
  for i in $(seq 1 120); do
    adb logcat -d -v threadtime > "$logcat_file" 2>&1 || true
    # Only treat an error as app-specific when the evidence names our package/process.
    if grep -E "$PACKAGE" "$logcat_file" | grep -Eq 'FATAL EXCEPTION|ANR in|Fatal signal [0-9]+ \(SIG'; then
      echo "${label}_APP_CRASH_EVIDENCE_FOUND"; tail -n 300 "$logcat_file"; return 1
    fi
    pid="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
    focused="$(adb shell dumpsys activity activities 2>/dev/null | grep -E 'mResumedActivity|mCurrentFocus' | grep -m1 "$PACKAGE" || true)"
    if [ -n "$focused" ] || [ -n "$pid" ]; then echo "${label}_RUNNING pid=${pid:-unknown}"; return 0; fi
    sleep 2
  done
  echo "${label}_LAUNCH_TIMEOUT"; tail -n 300 "$logcat_file"; return 1
}
launch_and_verify START || { echo RUNTIME_LAUNCH_FAILED; exit 32; }
echo START_PASS
adb shell am force-stop "$PACKAGE" >/dev/null 2>&1 || true
sleep 2
launch_and_verify RESTART || { echo RESTART_CRASH_CONFIRMED; exit 33; }
echo RESTART_PASS
cp "$APK_FILE" "$GITHUB_WORKSPACE/final-apk/KUNAL-Universal-Video-debug.apk"
echo VERIFIED_STARTUP_APK_READY
exit 0
