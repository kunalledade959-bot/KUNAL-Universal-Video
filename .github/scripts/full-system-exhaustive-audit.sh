#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
REPORT="${ROOT}/FULL_SYSTEM_EXHAUSTIVE_AUDIT.txt"
ERRORS="${ROOT}/FULL_SYSTEM_EXHAUSTIVE_ERRORS.txt"
: > "$REPORT"
: > "$ERRORS"

TOTAL=0
FAILS=0
WARNS=0
PASSES=0

stamp(){ date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log(){ printf '[%s] %s\n' "$(stamp)" "$*" | tee -a "$REPORT"; }
pass(){ PASSES=$((PASSES+1)); TOTAL=$((TOTAL+1)); printf 'PASS | %s\n' "$*" | tee -a "$REPORT"; }
warn(){ WARNS=$((WARNS+1)); TOTAL=$((TOTAL+1)); printf 'WARN | %s\n' "$*" | tee -a "$REPORT"; }
fail(){ FAILS=$((FAILS+1)); TOTAL=$((TOTAL+1)); printf 'FAIL | %s\n' "$*" | tee -a "$REPORT" "$ERRORS"; }
section(){ printf '\n===== %s =====\n' "$*" | tee -a "$REPORT"; }

log "FULL SYSTEM EXHAUSTIVE AUDIT START"
log "This audit is non-blocking during collection: every check continues after failure."
log "Final verdict is calculated only after all sections finish."
log "Repository: $(basename "$ROOT")"
log "Commit: ${GITHUB_SHA:-unknown}"

section '01 REPOSITORY INVENTORY'
mapfile -t ALL_FILES < <(find "$ROOT" -type f -not -path '*/.git/*' | sort)
if ((${#ALL_FILES[@]} > 0)); then pass "repository contains ${#ALL_FILES[@]} files"; else fail "repository file inventory is empty"; fi
printf 'DIRECTORY TREE (depth <= 6)\n' >> "$REPORT"
find "$ROOT" -maxdepth 6 -not -path '*/.git*' -print | sed "s#^$ROOT##" | sort >> "$REPORT"

section '02 REQUIRED TOP-LEVEL / ENGINE FILES'
for f in \
  '.github/workflows/sequence-01.yml' \
  '.github/workflows/sequence-02.yml' \
  '.github/workflows/full-e2e-emulator.yml' \
  '.github/workflows/13-stage-adversarial-audit.yml' \
  '.github/workflows/daily-apk-health.yml' \
  '.github/scripts/sequence-stage-check.sh' \
  '.github/scripts/full-e2e-emulator.sh' \
  '.github/scripts/sequence-fault-matrix.sh'; do
  if [[ -f "$ROOT/$f" ]]; then pass "required file exists: $f"; else fail "required file missing: $f"; fi
done

section '03 FILE TYPE / SYNTAX INVENTORY'
for f in "${ALL_FILES[@]}"; do
  rel="${f#$ROOT/}"
  case "$rel" in
    *.sh) if bash -n "$f" 2>>"$ERRORS"; then pass "bash syntax: $rel"; else fail "bash syntax error: $rel"; fi ;;
    *.py) if python -m py_compile "$f" 2>>"$ERRORS"; then pass "python syntax: $rel"; else fail "python syntax error: $rel"; fi ;;
    *.yml|*.yaml) if python - "$f" >>"$REPORT" 2>>"$ERRORS" <<'PY'
import sys
try:
 import yaml
 with open(sys.argv[1], encoding='utf-8') as h: yaml.safe_load(h)
except ImportError:
 sys.exit(2)
PY
    then pass "YAML syntax: $rel"; else warn "YAML parser unavailable or syntax error: $rel"; fi ;;
  esac
done

section '04 WORKFLOW TRIGGER ISOLATION'
for f in "$ROOT"/.github/workflows/sequence-*.yml; do
  [[ -f "$f" ]] || continue
  rel="${f#$ROOT/}"
  if grep -Eq '^\s+push:' "$f"; then fail "sequence workflow has automatic push trigger: $rel"; else pass "sequence workflow is not push-triggered: $rel"; fi
done
for f in "$ROOT"/.github/workflows/full-e2e-emulator.yml "$ROOT"/.github/workflows/13-stage-adversarial-audit.yml "$ROOT"/.github/workflows/run-all-sequences.yml; do
  [[ -f "$f" ]] || continue
  rel="${f#$ROOT/}"
  if grep -Eq '^\s+push:' "$f"; then fail "large/integrated workflow still has push trigger: $rel"; else pass "large/integrated workflow has no push trigger: $rel"; fi
done

section '05 SEQUENCE COVERAGE 01..13'
for n in $(seq 1 13); do
  wf="$ROOT/.github/workflows/sequence-$(printf '%02d' "$n").yml"
  if [[ ! -f "$wf" ]]; then fail "Sequence $n workflow missing"; continue; fi
  if grep -Eq "Sequence 0*$n|sequence-$(printf '%02d' "$n")|sequence-stage-check.*$n" "$wf"; then pass "Sequence $n has identifiable workflow/check mapping"; else fail "Sequence $n workflow does not expose a recognizable stage mapping"; fi
done

section '06 SEQUENCE WORKFLOW DEPENDENCY DISCOVERY'
for f in "$ROOT"/.github/workflows/sequence-*.yml; do
  [[ -f "$f" ]] || continue
  rel="${f#$ROOT/}"
  printf '\n[%s]\n' "$rel" >> "$REPORT"
  grep -E '^\s*(run:|uses:|with:|path:|working-directory:)' "$f" >> "$REPORT" || true
  while read -r script; do
    [[ -z "$script" ]] && continue
    script="${script#./}"
    if [[ -f "$ROOT/$script" ]]; then pass "$rel references existing file $script"; else fail "$rel references missing file $script"; fi
  done < <(grep -Eo '\.github/[A-Za-z0-9_./-]+\.(sh|py|yml|yaml|kt)' "$f" | sort -u)
done

section '07 SOURCE REFERENCE / MISSING-FILE CHECKS'
for f in "${ALL_FILES[@]}"; do
  [[ "$f" == *.sh || "$f" == *.py ]] || continue
  rel="${f#$ROOT/}"
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    ref="${ref#./}"
    [[ "$ref" == *'${'* || "$ref" == *'$(' ]] && continue
    if [[ -e "$ROOT/$ref" ]]; then :; else warn "possible missing source reference in $rel -> $ref"; fi
  done < <(grep -Eo '(\.github/[A-Za-z0-9_./-]+\.(sh|py)|android/[A-Za-z0-9_./-]+\.(kt|java|xml))' "$f" | sort -u)
done

section '08 ANDROID STRUCTURE / MANIFEST / ACCESSIBILITY'
MANIFEST="$ROOT/android/app/src/main/AndroidManifest.xml"
if [[ -f "$MANIFEST" ]]; then
  pass 'AndroidManifest.xml exists'
  grep -Eq 'BIND_ACCESSIBILITY_SERVICE' "$MANIFEST" && pass 'Accessibility bind permission declared' || fail 'Accessibility bind permission missing'
  grep -Eq 'android.accessibilityservice.AccessibilityService' "$MANIFEST" && pass 'Accessibility service intent present' || fail 'Accessibility service intent missing'
  grep -Eq 'exported="(true|false)"' "$MANIFEST" && pass 'components declare exported state' || warn 'no explicit exported attribute found in manifest'
else
  fail 'AndroidManifest.xml missing'
fi

section '09 ANDROID SOURCE INVENTORY'
mapfile -t KT_FILES < <(find "$ROOT/android" -type f \( -name '*.kt' -o -name '*.java' -o -name '*.xml' \) 2>/dev/null | sort)
if ((${#KT_FILES[@]})); then pass "Android source inventory: ${#KT_FILES[@]} files"; else fail 'Android source tree has no Kotlin/Java/XML files'; fi
for f in "${KT_FILES[@]}"; do
  rel="${f#$ROOT/}"
  case "$f" in
    *.kt) if grep -Eq 'fun |class |object |interface ' "$f"; then pass "Kotlin source structurally readable: $rel"; else warn "Kotlin file has no obvious declarations: $rel"; fi ;;
  esac
done

section '10 STAGE CONTRACT INVENTORY'
for n in $(seq 1 13); do
  hits=$(grep -RInE "gate\.pass\($n|gate\.fail\($n|Stage[[:space:]_-]*$n|stage[[:space:]_-]*$n" "$ROOT/android" "$ROOT/.github" 2>/dev/null | wc -l | tr -d ' ')
  if ((hits > 0)); then pass "Stage $n has $hits source/check references"; else fail "Stage $n has no discoverable contract reference"; fi
done

section '11 MOBILE CONNECTION DEEP CONTRACT'
for pattern in \
  'AccessibilityService' \
  'onServiceConnected' \
  'onUnbind' \
  'connect(' \
  'disconnect(' \
  'PING' \
  'PONG' \
  '127\.0\.0\.1' \
  '8765' \
  'session'; do
  if grep -RInE "$pattern" "$ROOT/android" "$ROOT/.github/scripts" 2>/dev/null | head -n 5 >> "$REPORT"; then
    pass "mobile-connection evidence exists for pattern: $pattern"
  else
    fail "mobile-connection evidence missing for pattern: $pattern"
  fi
done

section '12 ERROR HANDLING / SILENT FAILURE AUDIT'
for f in "${ALL_FILES[@]}"; do
  [[ "$f" == *.sh || "$f" == *.py || "$f" == *.kt || "$f" == *.java ]] || continue
  rel="${f#$ROOT/}"
  if grep -Eq 'catch[[:space:]]*\([^)]*\)[[:space:]]*\{[[:space:]]*\}|except[[:space:]]*:[[:space:]]*$|2>/dev/null[[:space:]]*($|[|;&])' "$f"; then
    warn "possible silent error suppression needs review: $rel"
  fi
done

section '13 HARDCODED / ENVIRONMENT ASSUMPTION AUDIT'
grep -RInE '127\.0\.0\.1|localhost|8765|ANDROID_SERIAL|adb |emulator|API_LEVEL|Build.VERSION|SDK_INT' "$ROOT/android" "$ROOT/.github" 2>/dev/null | head -n 500 >> "$REPORT" || true
pass 'environment assumption inventory completed'

section '14 TEST ARTIFACT / EVIDENCE REQUIREMENTS'
for f in "$ROOT"/.github/workflows/*.yml; do
  [[ -f "$f" ]] || continue
  rel="${f#$ROOT/}"
  if grep -q 'actions/upload-artifact' "$f"; then pass "artifact upload configured: $rel"; else warn "no artifact upload detected: $rel"; fi
done

section '15 GLOBAL ERROR SIGNATURE SCAN'
PATTERN='FATAL EXCEPTION|ANR|NoSuchMethod|ClassNotFound|NoClassDefFound|NullPointerException|SecurityException|IllegalStateException|Timeout|timed out|Connection refused|Permission denied|MISSING|missing|FAIL|ERROR'
if grep -RInE "$PATTERN" "$ROOT/.github" "$ROOT/android" 2>/dev/null | head -n 1000 >> "$ERRORS"; then warn 'known error/failure signatures found in source or test definitions; see report/error file'; else pass 'no known error signatures found in inspected source/test definitions'; fi

section '16 COMPLETE SEQUENCE MATRIX'
for n in $(seq 1 13); do
  printf 'SEQUENCE %02d | workflow=%s | source_refs=%s | contract_hits=%s\n' \
    "$n" \
    "$(test -f "$ROOT/.github/workflows/sequence-$(printf '%02d' "$n").yml" && echo YES || echo NO)" \
    "$(grep -RIlE "Sequence 0*$n|sequence-$(printf '%02d' "$n")" "$ROOT/.github" "$ROOT/android" 2>/dev/null | wc -l | tr -d ' ')" \
    "$(grep -RInE "gate\.pass\($n|gate\.fail\($n|Stage[[:space:]_-]*$n" "$ROOT/.github" "$ROOT/android" 2>/dev/null | wc -l | tr -d ' ')" >> "$REPORT"
done

section '17 FINAL SUMMARY'
log "CHECKS_TOTAL=$TOTAL"
log "CHECKS_PASS=$PASSES"
log "CHECKS_WARN=$WARNS"
log "CHECKS_FAIL=$FAILS"
log "ERROR_FILE=$ERRORS"
if ((FAILS == 0)); then
  log 'FINAL_VERDICT=PASS_STATIC_EXHAUSTIVE'
else
  log 'FINAL_VERDICT=FAIL_STATIC_EXHAUSTIVE'
  log 'The audit intentionally completed every section before returning this verdict.'
fi
log 'FULL SYSTEM EXHAUSTIVE AUDIT END'

# Do not stop collection early. The final non-zero status is deliberate so CI cannot
# call a failing exhaustive audit green while still preserving the complete report.
if ((FAILS > 0)); then exit 1; fi
exit 0
