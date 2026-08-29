#!/usr/bin/env bash
set -euo pipefail
STAGE="$1"
ZIP="KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip"
case "$STAGE" in
1) fn='stage1'; label='Startup / Self-Diagnostic';;
2) fn='connectMobile'; label='Mobile Connection / Permissions';;
3) fn='selectTarget'; label='Target APK Selection';;
4) fn='studyTarget'; label='Study Selected APK';;
5) fn='saveStory'; label='Story Input';;
6) fn='operateTarget'; label='Operate Selected Target APK';;
7) fn='deepStudy'; label='Deep Target-App Understanding';;
8) fn='scenePlan'; label='Exact Scene Plan';;
9) fn='buildPlan'; label='Production Plan / Prompts';;
10) fn='audioAndRecord'; label='Audio / Voice / Music / Sound Effects';;
11) fn='assembleEdit'; label='Assemble / Edit';;
12) fn='verifyAndFix'; label='Verify / Auto-Fix';;
13) fn='finalExport'; label='Final Gallery Export';;
*) echo "UNKNOWN_STAGE=$STAGE"; exit 2;;
esac

test -s "$ZIP"
test -s activity_fixed.kt

grep -Eq "private fun ${fn}\\(" activity_fixed.kt

grep -Eq "if\(!begin\(${STAGE}\)\)return" activity_fixed.kt

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"
mapfile -t sources < <(find "$TMP" -type f \( -name '*.kt' -o -name '*.kts' -o -name '*.xml' \) -print)
test "${#sources[@]}" -gt 0
found=0
for f in "${sources[@]}"; do
  if grep -Eq "${fn}|StageGate|com\.kunal\.universalvideo" "$f"; then found=1; break; fi
done
test "$found" -eq 1
printf 'STAGE_%02d_STATIC_CONTRACT_PASS %s\n' "$STAGE" "$label"
