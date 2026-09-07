#!/usr/bin/env bash
# Deterministic one-run failure packet. Never guesses a root cause.
set -u
OUT="forensic/EXACT_FAILURE.md"
mkdir -p forensic
{
  echo '# EXACT FAILURE PACK'
  echo
  echo "COMMIT=$(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
  echo "UTC=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo
  echo '## FIRST FAILING BOUNDARY'
  boundary='UNVERIFIED'
  if [[ -s forensic/static-audit.txt ]] && ! grep -Fq 'STATIC_AUDIT_EXIT=0' forensic/static-audit.txt; then boundary='STATIC_AUDIT'; fi
  if [[ "$boundary" == UNVERIFIED && -s forensic/build.txt ]] && { ! grep -Fq 'BUILDER_EXIT=0' forensic/build.txt || ! grep -Fq 'APK_PRESENT=0' forensic/build.txt || ! grep -Fq 'REPORT_PRESENT=0' forensic/build.txt; }; then boundary='PRODUCTION_BUILD'; fi
  if [[ "$boundary" == UNVERIFIED && -s forensic/emulator.log ]] && ! grep -Fq 'sys.boot_completed' forensic/emulator.log 2>/dev/null; then :; fi
  if [[ "$boundary" == UNVERIFIED && -s forensic/e2e-console.txt ]] && grep -Fq 'E2E_EXIT=' forensic/e2e-console.txt && ! grep -Fq 'E2E_EXIT=0' forensic/e2e-console.txt; then boundary='FULL_E2E'; fi
  if [[ "$boundary" == UNVERIFIED && -s forensic/final-flow-console.txt ]] && grep -Fq 'FINAL_FLOW_EXIT=' forensic/final-flow-console.txt && ! grep -Fq 'FINAL_FLOW_EXIT=0' forensic/final-flow-console.txt; then boundary='FINAL_PRODUCTION_USER_FLOW'; fi
  if [[ "$boundary" == UNVERIFIED && -s final-user-flow-evidence/FAIL.txt ]]; then boundary='FINAL_PRODUCTION_USER_FLOW'; fi
  echo "BOUNDARY=$boundary"
  echo
  echo '## EXACT OBSERVED FAILURE'
  case "$boundary" in
    STATIC_AUDIT)
      grep -E '^(SHELL|PYTHON|MISSING|STAGE_[0-9]+_EXIT|STATIC_AUDIT_EXIT|NO_CONTINUE_ON_ERROR|RESULT=FAIL|REASON=|SOURCE_CONTRACT_MISSING|OVERLAID_BUILD_INPUT_CONTRACT_MISSING)' forensic/static-audit.txt 2>/dev/null || true
      ;;
    PRODUCTION_BUILD)
      grep -E '^(===|.*_exit=|.*_EXIT=|APK_PRESENT=|REPORT_PRESENT=)' forensic/build.txt 2>/dev/null || true
      echo '--- build error candidates ---'
      grep -E -i 'error:|exception|failed|failure|cannot|unresolved|duplicate|manifest merger|resource.*not found' forensic/build.txt 2>/dev/null | tail -n 120 || true
      ;;
    FULL_E2E)
      grep -E 'E2E_FAIL:|E2E_EXIT=|SELF_HEAL_|SYSTEMUI_|KVM_|EMULATOR_|ADB_|APP_PID|NO_FATAL' forensic/e2e-console.txt 2>/dev/null | tail -n 160 || true
      grep -E -i 'FATAL EXCEPTION|ANR in|Application Not Responding|DeadSystemException|Fatal signal' forensic/e2e-console.txt e2e-logcat.txt 2>/dev/null | tail -n 120 || true
      ;;
    FINAL_PRODUCTION_USER_FLOW)
      cat final-user-flow-evidence/FAIL.txt 2>/dev/null || true
      cat final-user-flow-evidence/root-cause-classification.txt 2>/dev/null || true
      cat final-user-flow-evidence/stage2-result.txt 2>/dev/null || true
      cat final-user-flow-evidence/stage3-save-result.txt 2>/dev/null || true
      echo '--- failure assertions ---'
      grep -E 'FINAL_USER_FLOW_FAIL:|TARGET=|EXPECTED_SERVICE=|ACTUAL_SERVICES=|STAGE2_ACCESSIBILITY_STATE=' final-user-flow-evidence/*.txt final-user-flow-evidence/*.log 2>/dev/null | tail -n 160 || true
      ;;
    *)
      echo 'No deterministic failure artifact was produced. This run is UNVERIFIED, not PASS.'
      ;;
  esac
  echo
  echo '## EVIDENCE FINGERPRINTS'
  find forensic final-user-flow-evidence -maxdepth 1 -type f -print0 2>/dev/null | sort -z | xargs -0 -r sha256sum
  echo
  echo '## SOURCE CONTRACT SNAPSHOT'
  for p in UniversalAccessibilityService StageGate MediaProjection TextToSpeech targetSpinner connectMobile selectTarget audioAndRecord assembleEdit verifyAndFix finalExport; do
    if grep -RIn --exclude-dir=.git --exclude-dir=build --exclude-dir=.gradle --exclude-dir=forensic -m1 -F "$p" . >/tmp/forensic-hit 2>/dev/null; then head -n 1 /tmp/forensic-hit; else echo "MISSING_SOURCE_SYMBOL=$p"; fi
done
  echo
  echo '## REPAIR RULE'
  echo 'Repair only the first failing boundary shown above. Do not change later stages, weaken assertions, bypass checks, or convert UNVERIFIED/INFRA FAILURE into PASS.'
  echo 'The exact observed error and evidence fingerprint are the contract for the next repair.'
} > "$OUT"
cat "$OUT"
