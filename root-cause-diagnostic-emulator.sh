#!/usr/bin/env bash
set +e
mkdir -p diagnostic
exec > diagnostic/emulator-run.log 2>&1

INSTALL_EXIT=99
LAUNCH_EXIT=99
APP_PID=""
MAIN_FOCUS=""
UI_DUMP_EXIT=99

record_boundary() {
  {
    echo "INSTALL_EXIT=$INSTALL_EXIT"
    echo "LAUNCH_EXIT=$LAUNCH_EXIT"
    echo "APP_PID=${APP_PID:-NONE}"
    echo "MAIN_FOCUS=${MAIN_FOCUS:-NONE}"
    echo "UI_DUMP_EXIT=$UI_DUMP_EXIT"
  } > diagnostic/boundary-results.txt
}

fail_with_evidence() {
  record_boundary
  exit 1
}

echo "=== emulator ready ==="
adb devices -l
adb wait-for-device
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell settings get global animator_duration_scale
adb shell settings put global bluetooth_on 0 || true
adb shell svc bluetooth disable || true
adb shell am force-stop com.android.bluetooth || true

echo "=== install ==="
if test -s artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk; then
  adb install -r artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk
  INSTALL_EXIT=$?
else
  echo "APK_MISSING_BEFORE_INSTALL=1"
  INSTALL_EXIT=98
fi
echo "install_exit=$INSTALL_EXIT"

echo "=== package ==="
adb shell dumpsys package com.kunal.universalvideo > diagnostic/package.txt

echo "=== launch ==="
if [ "$INSTALL_EXIT" -eq 0 ]; then
  adb shell am force-stop com.kunal.universalvideo
  adb shell pm clear com.kunal.universalvideo
  adb shell monkey -p com.kunal.universalvideo -c android.intent.category.LAUNCHER 1
  LAUNCH_EXIT=$?
fi
echo "launch_exit=$LAUNCH_EXIT"
sleep 8

echo "=== focus ==="
adb shell dumpsys activity activities | tee diagnostic/activity-focus.txt | grep -E 'mResumedActivity|mFocusedApp' || true
adb shell dumpsys window windows | tee diagnostic/window-focus.txt | grep -E 'mCurrentFocus|mFocusedApp' || true
MAIN_FOCUS=$(cat diagnostic/activity-focus.txt diagnostic/window-focus.txt 2>/dev/null | grep -E 'com.kunal.universalvideo/.MainActivity|com.kunal.universalvideo.*MainActivity' | head -1)
echo "main_focus=${MAIN_FOCUS:-NONE}"

echo "=== process ==="
APP_PID=$(adb shell pidof com.kunal.universalvideo 2>/dev/null | tr -d '\r\n')
echo "app_pid=${APP_PID:-NONE}"

echo "=== UI hierarchy ==="
adb shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1
UI_DUMP_EXIT=$?
echo "ui_dump_exit=$UI_DUMP_EXIT"
adb shell cat /sdcard/window.xml > diagnostic/ui-hierarchy.xml 2>&1 || true

echo "=== screenshot ==="
adb exec-out screencap -p > diagnostic/screenshot.png

echo "=== crash/anr ==="
adb logcat -d -v threadtime | grep -E 'FATAL EXCEPTION|ANR in|Application Not Responding|DeadSystemException|system_server|com.android.systemui|com.android.bluetooth|com.kunal.universalvideo' > diagnostic/relevant-logcat.txt || true
adb logcat -d -v threadtime > diagnostic/full-logcat.txt

echo "=== final state ==="
adb shell dumpsys activity activities > diagnostic/activity.txt
adb shell dumpsys window windows > diagnostic/window.txt
adb shell dumpsys meminfo com.kunal.universalvideo > diagnostic/meminfo.txt 2>&1 || true

record_boundary

if [ "$INSTALL_EXIT" -ne 0 ] || [ "$LAUNCH_EXIT" -ne 0 ] || [ -z "$APP_PID" ] || [ -z "$MAIN_FOCUS" ] || [ "$UI_DUMP_EXIT" -ne 0 ]; then
  exit 1
fi

exit 0
