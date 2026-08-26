#!/usr/bin/env bash
set -u

mkdir -p "$GITHUB_WORKSPACE/runtime-evidence" "$GITHUB_WORKSPACE/final-apk"
APK_FILE="$GITHUB_WORKSPACE/built-apk/KUNAL-Universal-Video-debug.apk"

if [ ! -s "$APK_FILE" ]; then
  echo "PREBUILT_APK_MISSING"
  exit 20
fi

# The build job already passed. Runtime gate must never rebuild or mutate source.
# Validate APK metadata before install; a metadata failure is a runtime-input problem, not a reason to reboot repeatedly.
AAPT="$(command -v aapt || true)"
if [ -z "$AAPT" ]; then
  echo "AAPT_MISSING"
  exit 21
fi

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

set +e
timeout 30s adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$GITHUB_WORKSPACE/runtime-evidence/start.log" 2>&1
START_RC=$?
set -e
sleep 8
adb logcat -d -v threadtime > "$GITHUB_WORKSPACE/runtime-evidence/logcat.log" || true
PID="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
echo "START_RC=$START_RC PID=$PID"

if [ "$START_RC" -ne 0 ] || [ -z "$PID" ]; then
  echo "RUNTIME_LAUNCH_FAILED"
  tail -n 300 "$GITHUB_WORKSPACE/runtime-evidence/logcat.log" || true
  exit 32
fi

set +e
adb shell am force-stop "$PACKAGE" >/dev/null 2>&1
adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$GITHUB_WORKSPACE/runtime-evidence/restart.log" 2>&1
RESTART_RC=$?
set -e
sleep 8
PID2="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
echo "RESTART_RC=$RESTART_RC PID2=$PID2"

if [ "$RESTART_RC" -ne 0 ] || [ -z "$PID2" ]; then
  echo "RESTART_CRASH_CONFIRMED"
  adb logcat -d -v threadtime > "$GITHUB_WORKSPACE/runtime-evidence/restart-logcat.log" || true
  exit 33
fi

cp "$APK_FILE" "$GITHUB_WORKSPACE/final-apk/KUNAL-Universal-Video-debug.apk"
echo "VERIFIED_STARTUP_APK_READY"
exit 0
