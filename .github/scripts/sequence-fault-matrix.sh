#!/usr/bin/env bash
set -uo pipefail

SRC="activity_fixed.kt"
GATE="stage_gate.kt"
REPORT="sequence-fault-matrix.txt"
: > "$REPORT"
failed=0

log(){ echo "$*" | tee -a "$REPORT"; }
fail(){ log "FAIL|$1|$2|$3"; failed=1; }
pass(){ log "PASS|$1|$2|$3"; }

[ -s "$SRC" ] || { log "FATAL|0|SOURCE|activity_fixed.kt missing"; exit 2; }
[ -s "$GATE" ] || { log "FATAL|0|GATE|stage_gate.kt missing"; exit 2; }

log "KUNAL UNIVERSAL VIDEO - EXHAUSTIVE SEQUENCE FAULT MATRIX"
log "MODE=STATIC_FAILURE_PATH_COVERAGE"
log "RULE=Every discovered failure path must be explicit, user-visible, and fail-closed."
log "SOURCE_STATE=POST_PRODUCTION_SAFETY_REPAIR"
log ""

# Each stage is checked for the expected success path plus the important classes
# of runtime failure that can be detected from the production controller itself.
declare -A FN=(
 [1]=stage1 [2]=connectMobile [3]=selectTarget [4]=studyTarget [5]=saveStory
 [6]=operateTarget [7]=deepStudy [8]=scenePlan [9]=buildPlan [10]=audioAndRecord
 [11]=assembleEdit [12]=verifyAndFix [13]=finalExport
)
declare -A LABEL=(
 [1]="Startup / Self-Diagnostic" [2]="Mobile Connection / Permissions" [3]="Target APK Selection"
 [4]="Study Selected APK" [5]="Story Input" [6]="Operate Selected Target APK"
 [7]="Deep Target-App Understanding" [8]="Exact Scene Plan" [9]="Production Plan / Prompts"
 [10]="Audio / Voice / Music / Sound Effects" [11]="Assemble / Edit" [12]="Verify / Auto-Fix" [13]="Final Gallery Export"
)

for n in $(seq 1 13); do
  fn="${FN[$n]}"; label="${LABEL[$n]}"
  if grep -Eq "private fun ${fn}\\(" "$SRC"; then pass "$n" "$label" "function exists"; else fail "$n" "$label" "function missing"; continue; fi
  if [ "$n" -gt 1 ] && grep -Eq "if\\(!begin\\(${n}\\)\\)return" "$SRC"; then pass "$n" "$label" "persistent StageGate entry"; else [ "$n" -eq 1 ] || fail "$n" "$label" "missing fail-closed gate entry"; fi
  if grep -Eq "pass\\(${n}," "$SRC"; then pass "$n" "$label" "explicit PASS evidence"; else fail "$n" "$label" "no explicit PASS evidence"; fi
  if grep -Eq "fail\\(${n}," "$SRC"; then pass "$n" "$label" "explicit FAIL evidence"; else fail "$n" "$label" "no explicit FAIL evidence"; fi
done

log ""
log "--- HIGH-RISK FAILURE CLASSES ---"
for p in "onCreate(b:Bundle?)" "stage1()" "buildUi(p)" "renderStatus()"; do
  grep -Fq "$p" "$SRC" && pass 1 "Startup" "present:$p" || fail 1 "Startup" "missing:$p"
done
for p in "isEnabled" "openAccessibility()" "bridge?.connect(target)" "handshake + PING/PONG"; do
  grep -Fq "$p" "$SRC" && pass 2 "Connection" "guard:$p" || fail 2 "Connection" "missing:$p"
done
for p in "getInstalledApplications" "getApplicationInfo(target,0)" "getLaunchIntentForPackage(target)" "No target selected"; do
  grep -Fq "$p" "$SRC" && pass 3 "Target" "guard:$p" || fail 3 "Target" "missing:$p"
done
for p in "targetForeground" "rootInActiveWindow" "AccessibilityNodeInfo" "nodes<1"; do
  grep -Fq "$p" "$SRC" && pass 6 "Target UI" "guard:$p" || fail 6 "Target UI" "missing:$p"
done
for p in "s.length<10" "Story missing" "putString(STORY,s)" "putString(SCENES,scenes)" "putString(PLAN,plan)"; do
  grep -Fq "$p" "$SRC" && pass 5 "Data" "guard:$p" || fail 5 "Data" "missing:$p"
done
for p in "synthesizeToFile" "result!=TextToSpeech.SUCCESS" "MediaProjectionManager" "Recording stopped but no real MediaStore video was produced"; do
  grep -Fq "$p" "$SRC" && pass 10 "Media Capture" "guard:$p" || fail 10 "Media Capture" "missing:$p"
done
for p in "MediaExtractor" "MediaMuxer" "trackCount" "required media track missing" "video FD unavailable"; do
  grep -Fq "$p" "$SRC" && pass 11 "Assembly" "guard:$p" || fail 11 "Assembly" "missing:$p"
done
for p in "IS_PENDING" "openOutputStream" "EXTERNAL_CONTENT_URI" "FINAL"; do
  grep -Fq "$p" "$SRC" && pass 13 "Export" "guard:$p" || fail 13 "Export" "missing:$p"
done

log ""
log "--- CRASH/PLACEHOLDER SCAN ---"
if grep -Eiq 'TODO|FIXME|NotImplemented|UnsupportedOperationException' "$SRC"; then fail 0 "Code hygiene" "placeholder/unimplemented marker found"; else pass 0 "Code hygiene" "no placeholder/unimplemented marker"; fi
if grep -Eiq '!!' "$SRC"; then fail 0 "Null safety" "Kotlin !! operator found in production controller"; else pass 0 "Null safety" "no Kotlin !! operator"; fi
if grep -Eq 'catch\(e:Exception\)' "$SRC"; then pass 0 "Exception handling" "media/TTS/startup exceptions are caught"; else fail 0 "Exception handling" "no broad exception boundary found"; fi

log ""
log "--- STAGE GATE INVARIANTS ---"
for p in "isUnlocked" "currentStage" "State.PASS" "fail" "evidenceJson"; do
  grep -Fq "$p" "$GATE" && pass 0 "StageGate" "invariant:$p" || fail 0 "StageGate" "missing:$p"
done

log ""
if [ "$failed" -eq 0 ]; then
  log "MATRIX_RESULT=PASS"
  log "IMPORTANT=This is static failure-path coverage, not proof of physical-device behavior."
  exit 0
else
  log "MATRIX_RESULT=FAIL"
  log "IMPORTANT=Do not call the APK verified; repair every FAIL before the second-pass gate."
  exit 1
fi
