#!/usr/bin/env bash
set -uo pipefail
STAGE="$1"
ZIP="KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip"
SRC="activity_fixed.kt"

case "$STAGE" in
1) fn='stage1'; label='Startup / Self-Diagnostic'; checks=("gate=StageGate(this)" "UUID.randomUUID()" "gate.pass(1,");;
2) fn='connectMobile'; label='Mobile Connection / Permissions'; checks=("UniversalAccessibilityService.isEnabled" "bridge?.connect(target)" "fail(2,");;
3) fn='selectTarget'; label='Target APK Selection'; checks=("targetSpinner.selectedItemPosition" "putString(TARGET,target)" "UniversalAccessibilityService.targetPackage=target");;
4) fn='studyTarget'; label='Study Selected APK'; checks=("getApplicationInfo(target,0)" "getLaunchIntentForPackage(target)" "launch");;
5) fn='saveStory'; label='Story Input'; checks=("s.length<10" "putString(STORY,s)" "pass(5,");;
6) fn='operateTarget'; label='Operate Selected Target APK'; checks=("getLaunchIntentForPackage(target)" "startActivity(i)" "pass(6,");;
7) fn='deepStudy'; label='Deep Target-App Understanding'; checks=("rootInActiveWindow" "AccessibilityNodeInfo" "target_ui_map" "pass(7,");;
8) fn='scenePlan'; label='Exact Scene Plan'; checks=("SCENE_" "ACTION=" "putString(SCENES,scenes)" "pass(8,");;
9) fn='buildPlan'; label='Production Plan / Prompts'; checks=("VISUAL_PROMPT=" "ACTION_PROMPT=" "putString(PLAN,plan)" "pass(9,");;
10) fn='audioAndRecord'; label='Audio / Voice / Music / Sound Effects'; checks=("synthesizeToFile" "MediaProjectionManager" "AUDIO" "ScreenCaptureService.START");;
11) fn='assembleEdit'; label='Assemble / Edit'; checks=("MediaMuxer" "muxVideoAudio" "latestRecording()" "putString(FINAL,out.absolutePath)");;
12) fn='verifyAndFix'; label='Verify / Auto-Fix'; checks=("MediaExtractor" "trackCount" "pass(12,");;
13) fn='finalExport'; label='Final Gallery Export'; checks=("MediaStore.Video.Media.EXTERNAL_CONTENT_URI" "IS_PENDING" "openOutputStream" "pass(13,");;
*) echo "RESULT=FAIL"; echo "REASON=UNKNOWN_STAGE_$STAGE"; exit 2;;
esac

fail(){ echo "RESULT=FAIL"; echo "STAGE=$STAGE"; echo "LABEL=$label"; echo "REASON=$1"; exit 1; }

[ -s "$SRC" ] || fail "SOURCE_FILE_MISSING:$SRC"
[ -s "$ZIP" ] || fail "PACKAGE_FILE_MISSING:$ZIP"
grep -Eq "private fun ${fn}\\(" "$SRC" || fail "FUNCTION_MISSING:$fn"

if [ "$STAGE" -gt 1 ]; then
grep -Eq "if\\(!begin\\(${STAGE}\\)\\)return" "$SRC" || fail "STAGE_GATE_MISSING:$STAGE"
fi

for p in "${checks[@]}"; do
grep -Fq "$p" "$SRC" || fail "SOURCE_CONTRACT_MISSING:$p"
done

if grep -Eiq 'TODO|FIXME|NotImplemented|UnsupportedOperationException' "$SRC"; then
fail "PLACEHOLDER_OR_UNIMPLEMENTED_CODE_FOUND"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP" || fail "PACKAGE_UNZIP_FAILED"
mapfile -t sources < <(find "$TMP" -type f \( -name '*.kt' -o -name '*.kts' -o -name '*.xml' \) -print)
[ "${#sources[@]}" -gt 0 ] || fail "PACKAGE_HAS_NO_KOTLIN_OR_XML_SOURCES"

for p in "${checks[@]}"; do
found=0
for f in "${sources[@]}"; do
if grep -Fq "$p" "$f"; then found=1; break; fi
done
[ "$found" -eq 1 ] || fail "PACKAGE_CONTRACT_MISSING:$p"
done

echo "RESULT=PASS"
echo "STAGE_${STAGE}_DEEP_CONTRACT_PASS $label"
echo "SOURCE_AND_PACKAGED_PROJECT_CONTRACTS=PASS"