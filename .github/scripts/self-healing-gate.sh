#!/usr/bin/env bash
# KUNAL Universal Video: single authoritative local gate used by autonomous repair.
# It must prove build + emulator boot + install + launch + full E2E. Never fake PASS.
set -euo pipefail

export ANDROID_HOME="${ANDROID_HOME:-/usr/local/lib/android/sdk}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"
export ANDROID_AVD_HOME="${ANDROID_AVD_HOME:-$HOME/.android/avd}"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

mkdir -p "$ANDROID_AVD_HOME"
rm -rf artifact
mkdir -p artifact

# Reproduce the production build path exactly.
python3 preflight_patch.py
python3 constructor_lifecycle_patch.py
python3 stage11_hardening_v2.py
python3 pro_repair_v3.py

test -s KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk
test -s KUNAL_UNIVERSAL_VIDEO_PRO_V3_REPORT.json
grep -q '"status": "STATIC_AND_BUILD_VERIFIED"' KUNAL_UNIVERSAL_VIDEO_PRO_V3_REPORT.json
cp KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk

echo 'SELF_HEAL_BUILD_PASS'

cleanup() {
  set +e
  adb -s emulator-5554 emu kill >/dev/null 2>&1 || true
  if [[ -n "${EMU_PID:-}" ]]; then
    kill "$EMU_PID" >/dev/null 2>&1 || true
    wait "$EMU_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

adb kill-server >/dev/null 2>&1 || true
adb start-server >/dev/null
rm -rf "$ANDROID_AVD_HOME/test.avd" "$ANDROID_AVD_HOME/test.ini"
printf 'no\n' | avdmanager create avd --force -n test --package 'system-images;android-35;default;x86_64' --device 'pixel_2' >avd-create.log 2>&1
printf 'hw.cpu.ncore=2\nhw.ramSize=2048\n' >> "$ANDROID_AVD_HOME/test.avd/config.ini"
test -f "$ANDROID_AVD_HOME/test.avd/config.ini"

echo 'Starting deterministic cold emulator.'
emulator -avd test -port 5554 -no-window -no-audio -no-boot-anim -no-snapshot -gpu swiftshader_indirect -accel off >e2e-emulator.log 2>&1 &
EMU_PID=$!
echo "$EMU_PID" > e2e-emulator.pid

boot_deadline=$((SECONDS + 900))
boot_seen=0
adb_restarts=0
while (( SECONDS < boot_deadline )); do
  if ! kill -0 "$EMU_PID" >/dev/null 2>&1; then
    echo 'EMULATOR_PROCESS_EXITED' > e2e-emulator-failure.txt
    tail -n 1200 e2e-emulator.log > e2e-boot-log.txt || true
    exit 40
  fi
  state="$(adb -s emulator-5554 get-state 2>/dev/null || true)"
  if [[ "$state" == "device" ]]; then
    boot="$(adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [[ "$boot" == "1" ]]; then boot_seen=1; break; fi
  elif [[ "$state" == "offline" && $adb_restarts -lt 3 ]]; then
    adb kill-server >/dev/null 2>&1 || true
    sleep 2
    adb start-server >/dev/null 2>&1 || true
    adb_restarts=$((adb_restarts + 1))
  fi
  sleep 3
done

if [[ "$boot_seen" != "1" ]]; then
  echo 'EMULATOR_BOOT_FAILURE' > e2e-emulator-failure.txt
  adb devices -l > e2e-boot-adb-devices.txt 2>&1 || true
  adb -s emulator-5554 shell getprop > e2e-boot-props.txt 2>&1 || true
  tail -n 1200 e2e-emulator.log > e2e-boot-log.txt || true
  exit 41
fi

echo 'SELF_HEAL_EMULATOR_BOOT_PASS' | tee e2e-emulator-ready.txt
adb -s emulator-5554 wait-for-device
adb -s emulator-5554 shell echo KUNAL_SELF_HEAL_ADB_READY | tee e2e-adb-ready.txt

# The full E2E script is the final runtime authority.
bash .github/scripts/full-e2e-emulator.sh

test -f e2e-PASS.txt
echo 'SELF_HEAL_FULL_E2E_PASS'
