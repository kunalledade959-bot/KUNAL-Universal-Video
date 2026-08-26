#!/usr/bin/env bash
set -u

mkdir -p "$GITHUB_WORKSPACE/runtime-evidence" "$GITHUB_WORKSPACE/final-apk"
APK_FILE="$GITHUB_WORKSPACE/built-apk/KUNAL-Universal-Video-debug.apk"

if [ ! -s "$APK_FILE" ]; then
  echo "PREBUILT_APK_MISSING"
  exit 20
fi

# Build has already passed. Runtime validates only the produced APK.
AAPT="$(command -v aapt || true)"
if [ -z "$AAPT" ] && [ -n "${ANDROID_SDK_ROOT:-}" ]; then
  AAPT="$(find "$ANDROID_SDK_ROOT/build-tools" -type f -name aapt -perm -111 -print -quit 2>/dev/null || true)"
fi
if [ -z "$AAPT" ] && [ -n "${ANDROID_HOME:-}" ]; then
  AAPT="$(find "$ANDROID_HOME/build-tools" -type f -name aapt -perm -111 -print -quit 2>/dev/null || true)"
fi
if [ -z "$AAPT" ]; then
  echo "AAPT_MISSING"
  exit 21
fi

echo "AAPT=$AAPT"
BADGING="$GITHUB_WORKSPACE/runtime-evidence/badging.txt"
set +e
"$AAPT" dump badging "$APK_FILE" > "$BADGING" 2>&1
AAPT_RC=$?
set -e
cat "$BADGING"
if [ "$AAPT_RC" -ne 0 ]; then
  echo "APK_BADGING_FAILED rc=$AAPT_RC"
  exit 22
fi

PACKAGE="$(sed -n "s/^package: name='\([^']*\)'.*/\1/p" "$BADGING" | head -n1)"
ACTIVITY="$(sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" "$BADGING" | head -n1)"
echo "PACKAGE=$PACKAGE"
echo "ACTIVITY=$ACTIVITY"
if [ -z "$PACKAGE" ] || [ -z "$ACTIVITY" ]; then
  echo "APK_METADATA_INVALID"
  exit 23
fi

wait_for_online_adb() {
  local i state
  for i in $(seq 1 120); do
    state="$(adb -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)"
    if [ "$state" = "device" ]; then
      echo "ADB_READY attempt=$i"
      return 0
    fi
    echo "ADB_WAIT attempt=$i state=${state:-unknown}"
    sleep 2
  done
  echo "ADB_NOT_READY"
  adb devices -l || true
  return 1
}

if ! wait_for_online_adb; then
  exit 30
fi

adb shell getprop sys.boot_completed > "$GITHUB_WORKSPACE/runtime-evidence/boot.txt" 2>&1 || true
adb devices -l > "$GITHUB_WORKSPACE/runtime-evidence/adb.txt" 2>&1 || true
adb logcat -c || true
adb uninstall "$PACKAGE" >/dev/null 2>&1 || true

set +e
adb install "$APK_FILE" > "$GITHUB_WORKSPACE/runtime-evidence/install.log" 2>&1
INSTALL_RC=$?
set -e
if [ "$INSTALL_RC" -ne 0 ]; then
  echo "INSTALL_FAIL rc=$INSTALL_RC"
  cat "$GITHUB_WORKSPACE/runtime-evidence/install.log" || true
  exit 31
fi

echo "INSTALL_PASS"

launch_and_verify() {
  local label="$1"
  local launch_log="$2"
  local logcat_file="$3"
  local pid=""
  local resumed=""
  local i

  # Do not use `am start -W`. Software-emulated GitHub runners can be very slow.
  # Give the shell command enough time, then independently poll for the process/activity.
  set +e
  timeout 60s adb shell am start -n "$PACKAGE/$ACTIVITY" > "$launch_log" 2>&1
  local start_rc=$?
  set -e
  echo "${label}_START_RC=$start_rc"

  # Up to 4 minutes of patient polling. A timeout alone is never treated as a crash.
  for i in $(seq 1 120); do
    adb logcat -d -v threadtime > "$logcat_file" 2>&1 || true

    # Only definitive crash/ANR signatures fail the gate. Generic `Process:` lines are not errors.
    if grep -Eq 'FATAL EXCEPTION|ANR in|Fatal signal [0-9]+ \(SIG' "$logcat_file"; then
      echo "${label}_CRASH_EVIDENCE_FOUND"
      tail -n 300 "$logcat_file" || true
      return 1
    fi

    pid="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
    resumed="$(adb shell dumpsys activity activities 2>/dev/null | grep -m1 -F "$PACKAGE" || true)"
    if [ -n "$pid" ] || printf '%s' "$resumed" | grep -q "$PACKAGE"; then
      echo "${label}_RUNNING pid=${pid:-unknown}"
      return 0
    fi
    sleep 2
  done

  echo "${label}_LAUNCH_TIMEOUT"
  echo "No definitive crash was observed, but the app did not become observable within the extended startup window."
  tail -n 300 "$logcat_file" || true
  return 1
}

if ! launch_and_verify "START" "$GITHUB_WORKSPACE/runtime-evidence/start.log" "$GITHUB_WORKSPACE/runtime-evidence/logcat.log"; then
  echo "RUNTIME_LAUNCH_FAILED"
  exit 32
fi

echo "START_PASS"
adb shell am force-stop "$PACKAGE" >/dev/null 2>&1 || true
sleep 2

if ! launch_and_verify "RESTART" "$GITHUB_WORKSPACE/runtime-evidence/restart.log" "$GITHUB_WORKSPACE/runtime-evidence/restart-logcat.log"; then
  echo "RESTART_CRASH_CONFIRMED"
  exit 33
fi

echo "RESTART_PASS"
cp "$APK_FILE" "$GITHUB_WORKSPACE/final-apk/KUNAL-Universal-Video-debug.apk"
echo "VERIFIED_STARTUP_APK_READY"
exit 0
