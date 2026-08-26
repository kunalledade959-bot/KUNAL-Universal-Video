#!/usr/bin/env bash
set -u

cd "$PROJECT_DIR" || exit 1
mkdir -p "$GITHUB_WORKSPACE/runtime-evidence" "$GITHUB_WORKSPACE/final-apk"

# BUILD-FIRST: never boot an emulator until the APK has been produced and validated.
# Do not mutate source files during the verification run; repairs belong to the Doctor.

if [ ! -x ./gradlew ]; then
  echo "GRADLE_WRAPPER_MISSING"
  echo "Using provisioned Gradle instead of wasting emulator time."
  GRADLE_CMD="gradle"
else
  GRADLE_CMD="./gradlew"
fi

BUILD_LOG="$GITHUB_WORKSPACE/runtime-evidence/build.log"
set +e
"$GRADLE_CMD" :app:assembleDebug --no-daemon --stacktrace > "$BUILD_LOG" 2>&1
BUILD_RC=$?
set -e

if [ "$BUILD_RC" -ne 0 ]; then
  echo "BUILD_FAIL rc=$BUILD_RC"
  tail -n 220 "$BUILD_LOG" || true
  exit 20
fi

APK_FILE="$(find app/build/outputs/apk/debug -maxdepth 1 -type f -name '*.apk' -print -quit)"
if [ ! -s "$APK_FILE" ]; then
  echo "APK_BUILD_OUTPUT_MISSING"
  exit 21
fi

# Validate APK metadata before starting the expensive emulator.
PACKAGE="$(aapt dump badging "$APK_FILE" 2>/dev/null | sed "s/package: name='//;s/'.*//" | head -n1)"
ACTIVITY="$(aapt dump badging "$APK_FILE" 2>/dev/null | sed "s/launchable-activity: name='//;s/'.*//" | head -n1)"

echo "PACKAGE=$PACKAGE"
echo "ACTIVITY=$ACTIVITY"

if [ -z "$PACKAGE" ] || [ -z "$ACTIVITY" ]; then
  echo "APK_METADATA_INVALID"
  exit 22
fi

# From here onward the runner must already have a usable emulator.
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
timeout 20s adb shell am force-stop "$PACKAGE" >/dev/null 2>&1
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
