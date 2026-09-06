#!/usr/bin/env bash
# KUNAL Universal Video: deterministic failure classifier.
# This never converts an unknown failure into PASS. It emits a stable class,
# affected boundary, and the repository's known repair path when one exists.
set -u -o pipefail

LOG="${1:-}"
if [[ -z "$LOG" || ! -f "$LOG" ]]; then
  echo "FAILURE_INTELLIGENCE=INPUT_ERROR"
  echo "REPAIR_ACTION=Provide a real evidence log file"
  exit 2
fi

text="$(cat -- "$LOG" 2>/dev/null || true)"
class="UNKNOWN"
boundary="UNKNOWN"
action="COLLECT_EXACT_EVIDENCE_AND_DO_NOT_GUESS"

if grep -Eiq 'Application Not Responding|DeadSystemException|system_server.*ANR|System UI isn.t responding' <<<"$text"; then
  class="SYSTEM_ANR"
  boundary="SYSTEM"
  action="Inspect SystemUI/system_server evidence; do not classify as app crash without package-scoped crash evidence"
elif grep -Eiq 'FATAL EXCEPTION|AndroidRuntime|Process: com\.kunal\.universalvideo|Fatal signal' <<<"$text"; then
  class="APP_CRASH"
  boundary="RUNTIME"
  action="Inspect package-scoped stack trace and first application frame; compare against known startup/sha256 fixes"
elif grep -Eiq 'BUILD FAILED|Compilation error|e: .*\.kt:|AAPT2.*error|Could not resolve' <<<"$text"; then
  class="BUILD_FAILURE"
  boundary="BUILD"
  action="Use the exact compiler/AAPT dependency error; preserve the verified Gradle/JVM17 contract"
elif grep -Eiq 'INSTALL_FAILED|INSTALL_EXIT=[1-9]|adb.*install.*failed' <<<"$text"; then
  class="INSTALL_FAILURE"
  boundary="INSTALL"
  action="Repair ADB/install readiness only; do not change application logic until install is proven"
elif grep -Eiq 'device offline|adb.*offline|no devices/emulators found|unauthorized' <<<"$text"; then
  class="ADB_INFRASTRUCTURE"
  boundary="EMULATOR/ADB"
  action="Repair emulator/ADB readiness; use the existing resilient ADB gate"
elif grep -Eiq 'sdkmanager|licenses|cmdline-tools|platforms;android-35|build-tools;35\.0\.0' <<<"$text"; then
  class="SDK_PROVISIONING"
  boundary="SDK"
  action="Use the atomic SDK license pipeline and deterministic Android 35 component provisioning"
elif grep -Eiq 'UIAutomator|hierarchy.*xml|XML.*parse|UI_DUMP' <<<"$text"; then
  class="UI_CAPTURE"
  boundary="UI_CAPTURE"
  action="Validate pure UIAutomator XML before stage assertions; reject malformed/empty hierarchy"
elif grep -Eiq 'Accessibility|UniversalAccessibilityService|ACCESSIBILITY_SERVICE|not registered' <<<"$text"; then
  class="ACCESSIBILITY"
  boundary="STAGE_2"
  action="Verify the canonical fully-qualified service registration and use Stage 3 READY as the Stage 2 completion contract"
elif grep -Eiq 'target_package|No target|SELECT / SAVE TARGET|Stage 3' <<<"$text"; then
  class="TARGET_SELECTION"
  boundary="STAGE_3"
  action="Verify Stage 2 completed first, target spinner has a valid launcher target, then verify persisted target_package"
elif grep -Eiq 'recording|MediaProjection|TTS|Text-to-speech|narration' <<<"$text"; then
  class="MEDIA_CAPTURE_AUDIO"
  boundary="STAGE_10"
  action="Require fresh finalized recording and usable narration before Stage 10 PASS"
elif grep -Eiq 'AAC|MediaMuxer|MediaExtractor|non-monotonic|missing required video/audio' <<<"$text"; then
  class="MEDIA_ASSEMBLY"
  boundary="STAGE_11"
  action="Validate both media tracks, timestamps, muxer finalization, and output size before Stage 11 PASS"
fi

printf 'FAILURE_INTELLIGENCE_CLASS=%s\n' "$class"
printf 'FAILURE_INTELLIGENCE_BOUNDARY=%s\n' "$boundary"
printf 'REPAIR_ACTION=%s\n' "$action"
if [[ "$class" == "UNKNOWN" ]]; then
  printf 'CERTIFICATION=UNVERIFIED\n'
  printf 'IMPORTANT=Unknown failures are never auto-promoted to PASS.\n'
else
  printf 'CERTIFICATION=FAIL_REQUIRES_VERIFICATION\n'
fi
