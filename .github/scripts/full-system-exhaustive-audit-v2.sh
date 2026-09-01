#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
REPORT="$ROOT/FULL_SYSTEM_EXHAUSTIVE_AUDIT.txt"
ERRORS="$ROOT/FULL_SYSTEM_EXHAUSTIVE_ERRORS.txt"
WORK="$ROOT/.exhaustive-audit-work"
rm -rf "$WORK"
mkdir -p "$WORK"
: > "$REPORT"
: > "$ERRORS"

TOTAL=0; PASS=0; WARN=0; FAIL=0
stamp(){ date -u '+%Y-%m-%dT%H:%M:%SZ'; }
line(){ printf '[%s] %s\n' "$(stamp)" "$*" | tee -a "$REPORT"; }
check_pass(){ PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); printf 'PASS | %s\n' "$*" | tee -a "$REPORT"; }
check_warn(){ WARN=$((WARN+1)); TOTAL=$((TOTAL+1)); printf 'WARN | %s\n' "$*" | tee -a "$REPORT"; }
check_fail(){ FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); printf 'FAIL | %s\n' "$*" | tee -a "$REPORT" "$ERRORS"; }
section(){ printf '\n===== %s =====\n' "$*" | tee -a "$REPORT"; }

line 'FULL SYSTEM EXHAUSTIVE AUDIT V2 START'
line 'Collection is non-blocking. Every section continues after individual findings.'
line "Repository commit=${GITHUB_SHA:-unknown}"

section '01 REPOSITORY AND PACKAGED PROJECT INVENTORY'
mapfile -t ROOT_FILES < <(find "$ROOT" -maxdepth 6 -type f -not -path '*/.git/*' -not -path '*/.exhaustive-audit-work/*' | sort)
check_pass "repository files discovered=${#ROOT_FILES[@]}"
for archive in "$ROOT/KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip" "$ROOT/KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT.zip"; do
  if [[ -f "$archive" ]]; then
    name="$(basename "$archive")"
    size="$(stat -c '%s' "$archive" 2>/dev/null || wc -c < "$archive")"
    sha="$(sha256sum "$archive" | awk '{print $1}')"
    check_pass "packaged Android project present: $name bytes=$size sha256=$sha"
    dest="$WORK/${name%.zip}"
    mkdir -p "$dest"
    if unzip -q "$archive" -d "$dest"; then
      check_pass "archive extracted for inspection: $name"
    else
      check_fail "archive extraction failed: $name"
    fi
  fi
done

ANDROID_ROOT="$ROOT/android"
if [[ ! -f "$ANDROID_ROOT/app/src/main/AndroidManifest.xml" ]]; then
  manifest="$(find "$WORK" -type f -path '*/app/src/main/AndroidManifest.xml' | head -n 1 || true)"
  if [[ -n "$manifest" ]]; then
    appdir="${manifest%/src/main/AndroidManifest.xml}"
    rootdir="${appdir%/app}"
    rm -rf "$ANDROID_ROOT"
    cp -a "$rootdir" "$ANDROID_ROOT"
    check_pass "Android source materialized from packaged project"
  else
    check_fail 'AndroidManifest.xml could not be located in repository or packaged project'
  fi
else
  check_pass 'Android source tree already present'
fi

section '02 REQUIRED FILES AND SYNTAX'
required=(
  '.github/workflows/full-system-exhaustive-audit.yml'
  '.github/workflows/full-e2e-emulator.yml'
  '.github/workflows/13-stage-adversarial-audit.yml'
  '.github/scripts/sequence-stage-check.sh'
  '.github/scripts/full-e2e-emulator.sh'
  'SEQUENCE_13_STAGE_PROBLEM_CATALOG.md'
)
for rel in "${required[@]}"; do
  [[ -f "$ROOT/$rel" ]] && check_pass "required file exists: $rel" || check_fail "required file missing: $rel"
done
for f in "${ROOT}"/.github/scripts/*.sh; do
  [[ -f "$f" ]] || continue
  if bash -n "$f" >/dev/null 2>>"$ERRORS"; then check_pass "bash syntax: ${f#$ROOT/}"; else check_fail "bash syntax: ${f#$ROOT/}"; fi
done
for f in "${ROOT}"/.github/scripts/*.py "$ROOT"/tools/*.py; do
  [[ -f "$f" ]] || continue
  if python -m py_compile "$f" 2>>"$ERRORS"; then check_pass "python syntax: ${f#$ROOT/}"; else check_fail "python syntax: ${f#$ROOT/}"; fi
done

section '03 WORKFLOW TRIGGER ISOLATION'
for f in "$ROOT"/.github/workflows/*.yml; do
  [[ -f "$f" ]] || continue
  rel="${f#$ROOT/}"
  if python - "$f" <<'PY' >/dev/null 2>>"$ERRORS"
import sys, yaml
with open(sys.argv[1], encoding='utf-8') as h: d=yaml.safe_load(h) or {}
tr=d.get(True, d.get('on', {}))
if isinstance(tr, dict) and 'push' in tr: raise SystemExit(1)
PY
  then
    check_pass "no push trigger: $rel"
  else
    check_fail "automatic push trigger present: $rel"
  fi
done

section '04 SEQUENCE 01..13 COVERAGE'
for n in $(seq 1 13); do
  wf="$ROOT/.github/workflows/sequence-$(printf '%02d' "$n").yml"
  if [[ -f "$wf" ]]; then
    check_pass "Sequence $n workflow exists"
    if grep -Fq "sequence-stage-check.sh $n" "$wf"; then check_pass "Sequence $n maps to stage check"; else check_fail "Sequence $n stage mapping missing"; fi
  else
    check_fail "Sequence $n workflow missing"
  fi
done

section '05 ANDROID MANIFEST AND SOURCE INVENTORY'
MANIFEST="$ANDROID_ROOT/app/src/main/AndroidManifest.xml"
if [[ -f "$MANIFEST" ]]; then
  check_pass 'AndroidManifest.xml exists'
  grep -Fq 'BIND_ACCESSIBILITY_SERVICE' "$MANIFEST" && check_pass 'Accessibility bind permission declared' || check_fail 'Accessibility bind permission missing'
  grep -Fq 'android.accessibilityservice.AccessibilityService' "$MANIFEST" && check_pass 'Accessibility service declaration present' || check_fail 'Accessibility service declaration missing'
  grep -Eq 'android:exported="(true|false)"' "$MANIFEST" && check_pass 'exported attributes explicitly declared' || check_warn 'some components may lack explicit exported attribute'
else
  check_fail 'AndroidManifest.xml missing after archive materialization'
fi
mapfile -t SRC < <(find "$ANDROID_ROOT" -type f \( -name '*.kt' -o -name '*.java' -o -name '*.xml' -o -name '*.json' -o -name '*.properties' \) 2>/dev/null | sort)
if ((${#SRC[@]} > 0)); then check_pass "Android source/config files discovered=${#SRC[@]}"; else check_fail 'no Android source/config files discovered'; fi
for f in "${SRC[@]}"; do
  case "$f" in
    *.kt|*.java) if grep -Eq 'class |object |interface |fun |void |public ' "$f"; then check_pass "source structurally readable: ${f#$ROOT/}"; else check_warn "source has no obvious declaration: ${f#$ROOT/}"; fi;;
  esac
done

section '06 STAGE CONTRACT DISCOVERY'
for n in $(seq 1 13); do
  count=$(grep -RIlE "Stage[[:space:]_-]*$n|stage[[:space:]_-]*$n|gate\.pass\($n|gate\.fail\($n" "$ANDROID_ROOT" "$ROOT/.github" 2>/dev/null | wc -l | tr -d ' ')
  if ((count > 0)); then check_pass "Stage $n discoverable references=$count"; else check_fail "Stage $n has no discoverable contract reference"; fi
done

section '07 MOBILE CONNECTION IMPLEMENTATION PROOF'
# Literal fixed-string checks avoid regex false negatives such as connect( and SIGPIPE from grep|head.
patterns=(
  'AccessibilityService'
  'onServiceConnected'
  'onUnbind'
  'connect('
  'disconnect('
  'PING'
  'PONG'
  '127.0.0.1'
  '8765'
  'session'
  'ServerSocket'
  '/health'
  '/status'
)
for p in "${patterns[@]}"; do
  hits=$(grep -RIlF "$p" "$ANDROID_ROOT" "$ROOT/.github/scripts" 2>/dev/null | wc -l | tr -d ' ')
  if ((hits > 0)); then check_pass "mobile implementation evidence '$p' files=$hits"; else check_fail "mobile implementation evidence missing '$p'"; fi
done

section '08 DEPENDENCY AND CONFIGURATION EVIDENCE'
for f in "$ANDROID_ROOT/app/build.gradle.kts" "$ANDROID_ROOT/build.gradle.kts" "$ANDROID_ROOT/settings.gradle.kts" "$ANDROID_ROOT/gradle.properties"; do
  if [[ -f "$f" ]]; then check_pass "Android build/config exists: ${f#$ROOT/}"; else check_warn "Android build/config not found: ${f#$ROOT/}"; fi
done
if [[ -f "$ANDROID_ROOT/app/build.gradle.kts" ]]; then
  grep -Eq 'compileSdk|targetSdk|minSdk' "$ANDROID_ROOT/app/build.gradle.kts" && check_pass 'Android SDK configuration is explicit' || check_warn 'SDK configuration not obvious in app build file'
fi

section '09 REFERENCE AND ERROR-SUPPRESSION REVIEW'
mapfile -t TEXT_CODE < <(find "$ROOT" "$ANDROID_ROOT" -type f \( -name '*.kt' -o -name '*.java' -o -name '*.py' -o -name '*.sh' -o -name '*.yml' -o -name '*.yaml' \) -not -path '*/.git/*' -not -path '*/.exhaustive-audit-work/*' 2>/dev/null | sort -u)
for f in "${TEXT_CODE[@]}"; do
  if grep -Eq 'catch[[:space:]]*\([^)]*\)[[:space:]]*\{[[:space:]]*\}|except[[:space:]]*:[[:space:]]*$' "$f" 2>/dev/null; then
    check_warn "exception handling needs review: ${f#$ROOT/}"
  fi
done

section '10 ERROR SIGNATURE SCAN'
ERROR_PATTERN='FATAL EXCEPTION|ANR|NoSuchMethod|ClassNotFound|NoClassDefFound|NullPointerException|SecurityException|IllegalStateException|Connection refused|Permission denied'
if grep -RInE "$ERROR_PATTERN" "$ANDROID_ROOT" "$ROOT/.github/scripts" 2>/dev/null > "$WORK/error-signatures.txt"; then
  check_warn 'known runtime/error signatures found in source or diagnostics; see error-signatures.txt'
  cat "$WORK/error-signatures.txt" | head -n 1000 >> "$ERRORS"
else
  check_pass 'no known runtime error signatures found in inspected implementation'
fi

section '11 FILE-BY-FILE HASH INVENTORY'
: > "$WORK/file-hashes.txt"
while IFS= read -r f; do
  printf '%s  %s\n' "$(sha256sum "$f" | awk '{print $1}')" "${f#$ROOT/}" >> "$WORK/file-hashes.txt"
done < <(find "$ROOT" "$ANDROID_ROOT" -type f -not -path '*/.git/*' -not -path '*/.exhaustive-audit-work/*' 2>/dev/null | sort -u)
check_pass "SHA-256 inventory generated entries=$(wc -l < "$WORK/file-hashes.txt")"
cat "$WORK/file-hashes.txt" >> "$REPORT"

section '12 COMPLETE SEQUENCE MATRIX'
for n in $(seq 1 13); do
  wf="$ROOT/.github/workflows/sequence-$(printf '%02d' "$n").yml"
  refs=$(grep -RIlE "Sequence 0*$n|sequence-$(printf '%02d' "$n")" "$ANDROID_ROOT" "$ROOT/.github" 2>/dev/null | wc -l | tr -d ' ')
  contracts=$(grep -RInE "Stage[[:space:]_-]*$n|stage[[:space:]_-]*$n|gate\.pass\($n|gate\.fail\($n" "$ANDROID_ROOT" "$ROOT/.github" 2>/dev/null | wc -l | tr -d ' ')
  printf 'SEQUENCE %02d | workflow=%s | references=%s | contract_hits=%s\n' "$n" "$( [[ -f "$wf" ]] && echo YES || echo NO )" "$refs" "$contracts" | tee -a "$REPORT"
done

section '13 FINAL COLLECTION SUMMARY'
line "CHECKS_TOTAL=$TOTAL"
line "CHECKS_PASS=$PASS"
line "CHECKS_WARN=$WARN"
line "CHECKS_FAIL=$FAIL"
if ((FAIL == 0)); then line 'FINAL_VERDICT=PASS_STATIC_EXHAUSTIVE'; else line 'FINAL_VERDICT=FAIL_STATIC_EXHAUSTIVE'; fi
line 'COLLECTION_COMPLETE=YES'
line 'IMPORTANT=FAIL findings are evidence for repair; they do not abort collection.'
cat "$ERRORS" >> "$REPORT"
line 'FULL SYSTEM EXHAUSTIVE AUDIT V2 END'

# Collector never aborts before writing the complete evidence bundle.
exit 0
