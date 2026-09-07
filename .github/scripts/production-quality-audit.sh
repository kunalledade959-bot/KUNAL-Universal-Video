#!/usr/bin/env bash
# KUNAL Universal Video: deterministic pre-change quality firewall.
# Static contract PASS is never a runtime certification. Runtime gates must still
# prove the actual APK on a clean emulator.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail(){ echo "QUALITY_AUDIT_FAIL: $1"; exit 1; }
pass(){ echo "QUALITY_AUDIT_PASS: $1"; }

for f in \
  activity_fixed.kt \
  stage_gate.kt \
  pro_repair_v4.py \
  .github/scripts/self-healing-gate.sh \
  .github/scripts/full-e2e-emulator.sh \
  .github/scripts/final-production-user-flow.sh \
  .github/scripts/failure-intelligence.sh \
  .github/scripts/failure-intelligence-test.sh; do
  [[ -s "$f" ]] || fail "required file missing or empty: $f"
done

# The production workflow must remain a strict 1..13 fail-closed chain.
grep -Fq 'Production 1..13 workflow controller' activity_fixed.kt || fail 'canonical 1..13 controller marker missing'
for n in $(seq 1 13); do
  grep -Eq "${n} •" activity_fixed.kt || fail "stage ${n} production UI contract missing"
done
for method in stage1 connectMobile selectTarget studyTarget saveStory operateTarget deepStudy scenePlan buildPlan audioAndRecord assembleEdit verifyAndFix finalExport; do
  grep -Eq "private fun ${method}\\(" activity_fixed.kt || fail "stage handler missing: $method"
done

# StageGate invariants: no later stage may begin without the previous PASS,
# and PASS requires non-empty evidence.
grep -Fq 'stages[id - 2].state == State.PASS' stage_gate.kt || fail 'previous-stage PASS prerequisite missing'
grep -Fq 'evidence.isBlank()' stage_gate.kt || fail 'non-empty PASS evidence invariant missing'
grep -Fq 'State.RUNNING' stage_gate.kt || fail 'RUNNING recovery contract missing'
grep -Fq 'STAGE_GATE_PERSISTENCE_FAILED' stage_gate.kt || fail 'durable persistence failure contract missing'

# Production builder must be deterministic and must reject unsafe source forms.
for token in queryIntentActivities 'Intent.CATEGORY_LAUNCHER' getLaunchIntentForPackage mainHandler runOnUiThread; do
  grep -Fq "$token" pro_repair_v4.py || fail "V4 builder contract missing: $token"
done
grep -Fq 'FORBIDDEN_SYNC_INSTALLED_APPLICATION_ENUMERATION' pro_repair_v4.py || fail 'V4 forbidden-enumeration guard missing'
grep -Fq 'PRO_REPAIR_V4_CANONICAL_ACTIVITY_HARDENED=PASS' pro_repair_v4.py || fail 'V4 deterministic build marker missing'

# Runtime gates must require the real artifact and explicit evidence. These are
# source contracts only, not substitutes for running the APK.
grep -Fq 'FULL_E2E_EMULATOR_GATE_PASS' .github/scripts/full-e2e-emulator.sh || fail 'full E2E PASS marker missing'
grep -Fq 'FINAL_PRODUCTION_USER_FLOW_PASS' .github/scripts/final-production-user-flow.sh || fail 'final production PASS marker missing'
grep -Fq 'TARGET_PERSISTENCE=PASS' .github/scripts/final-production-user-flow.sh || fail 'target persistence gate missing'

# Do not allow common bypass language into production gate files.
if grep -RInE --exclude-dir=.git --exclude='*.apk' '(SKIP CHECK|ALLOW FAIL|DISABLE CHECK|TEMP_FIX|ignore failure|continue-on-error:[[:space:]]*true)' \
  .github/scripts .github/workflows *.py *.kt *.xml 2>/dev/null; then
  fail 'zero-bypass token found'
fi

# Failure intelligence must be present and explicitly fail closed.
grep -Fq 'CERTIFICATION=FAIL_REQUIRES_VERIFICATION' .github/scripts/failure-intelligence.sh || fail 'failure intelligence fail-closed certification missing'
grep -Fq 'UNKNOWN' .github/scripts/failure-intelligence.sh || fail 'unknown failure classification missing'

# The classifier itself is executable as a deterministic contract test. This
# checks the repair-routing vocabulary without requiring an emulator.
bash .github/scripts/failure-intelligence-test.sh | tee quality-failure-intelligence-test.log
grep -Fq 'FAILURE_INTELLIGENCE_TEST_PASS' quality-failure-intelligence-test.log || fail 'failure intelligence self-test did not PASS'

# Important boundary: current final-user-flow is deliberately only a Stage 2→3
# handoff proof. Never label it as full 13-stage certification in static code.
if grep -Fq 'Stage 2 → Stage 3 → target handoff flow' .github/workflows/ultra-pro-coding-lock.yml; then
  pass 'current production handoff scope explicitly identified as Stage 2→3'
else
  fail 'production handoff scope marker changed without audit update'
fi

pass '13-stage source contracts present'
pass 'fail-closed StageGate invariants present'
pass 'deterministic V4 build contracts present'
pass 'runtime evidence gates present'
echo 'QUALITY_AUDIT_CERTIFICATION=STATIC_CONTRACTS_PASS_RUNTIME_CERTIFICATION_REQUIRED'
