#!/usr/bin/env bash
# Deterministic self-test for failure-intelligence.sh. No network, emulator, or
# application mutation is required. A classifier change must preserve these
# boundary mappings or intentionally update this contract and its evidence.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLASSIFIER="$ROOT/.github/scripts/failure-intelligence.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "FAILURE_INTELLIGENCE_TEST_FAIL: $1"; exit 1; }
expect(){
  local name="$1"; local input="$2"; local expected_class="$3"; local expected_boundary="$4"
  local out
  printf '%s\n' "$input" > "$TMP/input.log"
  out="$(bash "$CLASSIFIER" "$TMP/input.log")" || fail "$name classifier exited non-zero"
  grep -Fq "FAILURE_INTELLIGENCE_CLASS=$expected_class" <<<"$out" || fail "$name class mismatch: $out"
  grep -Fq "FAILURE_INTELLIGENCE_BOUNDARY=$expected_boundary" <<<"$out" || fail "$name boundary mismatch: $out"
  if [[ "$expected_class" == UNKNOWN ]]; then
    grep -Fq 'CERTIFICATION=UNVERIFIED' <<<"$out" || fail "$name unknown must remain unverified"
  else
    grep -Fq 'CERTIFICATION=FAIL_REQUIRES_VERIFICATION' <<<"$out" || fail "$name known failure must require verification"
  fi
}

[[ -s "$CLASSIFIER" ]] || fail 'classifier is missing or empty'
bash -n "$CLASSIFIER" || fail 'classifier syntax check failed'

expect systemui_anr 'Application Not Responding: com.android.systemui' SYSTEM_ANR SYSTEM
expect app_crash 'FATAL EXCEPTION: main Process: com.kunal.universalvideo' APP_CRASH RUNTIME
expect build 'e: MainActivity.kt:42: Compilation error' BUILD_FAILURE BUILD
expect install 'INSTALL_FAILED_VERSION_DOWNGRADE' INSTALL_FAILURE INSTALL
expect adb 'adb: device offline' ADB_INFRASTRUCTURE EMULATOR/ADB
expect sdk 'sdkmanager --install platforms;android-35' SDK_PROVISIONING SDK
expect ui 'UIAutomator UI_DUMP_EXIT=1 hierarchy XML parse failed' UI_CAPTURE UI_CAPTURE
expect accessibility 'UniversalAccessibilityService not registered' ACCESSIBILITY STAGE_2
expect target 'target_package missing after Stage 3 SELECT / SAVE TARGET' TARGET_SELECTION STAGE_3
expect media 'MediaProjection recording TTS narration failed' MEDIA_CAPTURE_AUDIO STAGE_10
expect assembly 'MediaMuxer non-monotonic media timestamps; AAC track missing' MEDIA_ASSEMBLY STAGE_11
expect unknown 'an entirely new failure signature with no known mapping' UNKNOWN UNKNOWN

printf 'FAILURE_INTELLIGENCE_TEST_PASS\n'
