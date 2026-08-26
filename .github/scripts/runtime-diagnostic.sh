#!/usr/bin/env bash
set -u

cd "$PROJECT_DIR" || exit 1

gradle :wrapper --gradle-version 8.9 --distribution-type bin >/dev/null 2>&1 || true
sed -i 's/\r$//' gradlew
chmod +x gradlew

mkdir -p "$GITHUB_WORKSPACE/runtime-evidence" "$GITHUB_WORKSPACE/final-apk"

PACKAGE=""
ACTIVITY=""

repair() {
  echo "[REPAIR] runtime recovery"
  if [ -n "$PACKAGE" ]; then
    adb shell am force-stop "$PACKAGE" 2>/dev/null || true
    adb uninstall "$PACKAGE" 2>/dev/null || true
  fi
  adb kill-server 2>/dev/null || true
  sleep 2
  adb start-server 2>/dev/null || true
}

wait_for_online_adb() {
  local i state
  for i in $(seq 1 120); do
    state="$(adb -s emulator-5554 get-state 2>/dev/null | tr -d '\r' || true)"
    if [ "$state" = "device" ]; then
      echo "ADB_READY attempt=$i"
      return 0
    fi
    sleep 2
done
  echo "ADB_NOT_READY"
  adb devices -l || true
  return 1
}

for ATTEMPT in $(seq 1 30); do
  echo "AUTONOMOUS ATTEMPT $ATTEMPT / 30"
  rm -rf app/build

  ./gradlew :app:assembleDebug --no-daemon --stacktrace > "$GITHUB_WORKSPACE/runtime-evidence/build-$ATTEMPT.log" 2>&1
  BUILD_RC=$?
  if [ "$BUILD_RC" -ne 0 ]; then
    echo "BUILD_FAIL attempt=$ATTEMPT"
    tail -n 120 "$GITHUB_WORKSPACE/runtime-evidence/build-$ATTEMPT.log" || true
    repair
    continue
  fi

  APK_FILE="$(find app/build/outputs/apk/debug -maxdepth 1 -type f -name '*.apk' -print -quit)"
  if [ ! -s "$APK_FILE" ]; then
    echo "APK_BUILD_OUTPUT_MISSING"
    repair
    continue
  fi

  PACKAGE="$(aapt dump badging "$APK_FILE" | sed "s/package: name='//;s/'.*//" | head -n1)"
  ACTIVITY="$(aapt dump badging "$APK_FILE" | sed "s/launchable-activity: name='//;s/'.*//" | head -n1)"
  echo "PACKAGE=$PACKAGE"
  echo "ACTIVITY=$ACTIVITY"

  if [ -z "$PACKAGE" ] || [ -z "$ACTIVITY" ]; then
    echo "APK_METADATA_INVALID"
    repair
    continue
  fi

  if ! wait_for_online_adb; then
    repair
    continue
  fi

  adb shell getprop sys.boot_completed > "$GITHUB_WORKSPACE/runtime-evidence/boot-$ATTEMPT.txt" 2>&1 || true
  adb logcat -c || true
  adb uninstall "$PACKAGE" >/dev/null 2>&1 || true

  adb install "$APK_FILE" > "$GITHUB_WORKSPACE/runtime-evidence/install-$ATTEMPT.log" 2>&1
  INSTALL_RC=$?
  if [ "$INSTALL_RC" -ne 0 ]; then
    echo "INSTALL_FAIL attempt=$ATTEMPT"
    cat "$GITHUB_WORKSPACE/runtime-evidence/install-$ATTEMPT.log" || true
    repair
    continue
  fi

  adb shell am force-stop "$PACKAGE" || true
  timeout 30s adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$GITHUB_WORKSPACE/runtime-evidence/start-$ATTEMPT.log" 2>&1
  START_RC=$?
  echo "START_RC=$START_RC"

  sleep 8
  adb logcat -d -v threadtime > "$GITHUB_WORKSPACE/runtime-evidence/logcat-$ATTEMPT.log" || true
  adb shell dumpsys activity activities > "$GITHUB_WORKSPACE/runtime-evidence/activity-$ATTEMPT.txt" 2>&1 || true
  adb shell dumpsys window windows > "$GITHUB_WORKSPACE/runtime-evidence/window-$ATTEMPT.txt" 2>&1 || true

  PID="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
  echo "PID=$PID"

  if [ "$START_RC" -ne 0 ] || [ -z "$PID" ]; then
    echo "RUNTIME_LAUNCH_FAILED attempt=$ATTEMPT"
    tail -n 300 "$GITHUB_WORKSPACE/runtime-evidence/logcat-$ATTEMPT.log" || true
    repair
    continue
  fi

  adb shell am force-stop "$PACKAGE" || true
  timeout 20s adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$GITHUB_WORKSPACE/runtime-evidence/restart-$ATTEMPT.log" 2>&1
  RESTART_RC=$?
  sleep 8
  PID2="$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"

  if [ "$RESTART_RC" -ne 0 ] || [ -z "$PID2" ]; then
    echo "RESTART_CRASH_CONFIRMED attempt=$ATTEMPT"
    tail -n 300 "$GITHUB_WORKSPACE/runtime-evidence/logcat-$ATTEMPT.log" || true
    repair
    continue
  fi

  echo "RUNTIME_STARTUP_SURVIVED"
  cp "$APK_FILE" "$GITHUB_WORKSPACE/final-apk/KUNAL-Universal-Video-debug.apk"
  echo "VERIFIED_APK_READY"
  exit 0
done

echo "ALL_AUTONOMOUS_ATTEMPTS_EXHAUSTED"
exit 1
