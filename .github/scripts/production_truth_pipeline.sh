#!/usr/bin/env bash
# Do not use set -e here. Every independent truth check must finish and print its
# complete log before the pipeline returns its final status.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
LOG_DIR="$ROOT/production-truth-logs"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/00-combined.log"
TOTAL=0
FAILED=0

run_step() {
  local name="$1"; shift
  TOTAL=$((TOTAL + 1))
  local safe
  safe="$(printf '%s' "$name" | tr ' /' '__' | tr -cd '[:alnum:]_.-')"
  local log="$LOG_DIR/${TOTAL}-${safe}.log"
  echo
  echo "============================================================"
  echo "PRODUCTION TRUTH CELL ${TOTAL}: ${name}"
  echo "============================================================"
  {
    echo "CELL=${TOTAL}"
    echo "NAME=${name}"
    echo "COMMAND=$*"
    echo "START=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
  } | tee "$log" -a "$LOG_DIR/00-combined.log"

  set +e
  "$@" 2>&1 | tee -a "$log" "$LOG_DIR/00-combined.log"
  local rc=${PIPESTATUS[0]}
  set -e

  {
    echo
    echo "END=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "EXIT_CODE=${rc}"
  } | tee -a "$log" "$LOG_DIR/00-combined.log"

  if [[ "$rc" -ne 0 ]]; then
    FAILED=$((FAILED + 1))
    echo "CELL ${TOTAL} RESULT=FAIL exit=${rc}"
  else
    echo "CELL ${TOTAL} RESULT=PASS"
  fi
  return 0
}

# Transform the source first. The top-1 exhaustive cell must audit the FINAL
# generated/patched source, not the pre-codegen template. It also repairs the
# remaining known contract/runtime defects before the independent audit cells.
run_step "contract-codegen" python3 .github/scripts/production_truth_codegen.py
run_step "production-truth-patch" python3 .github/scripts/production_truth_patch.py
run_step "production-truth-runtime-fix" python3 .github/scripts/production_truth_runtime_fix.py
run_step "top1-exhaustive-repair-and-audit" python3 .github/scripts/top1_exhaustive_truth_cell.py
run_step "production-truth-audit" python3 .github/scripts/production_truth_audit.py

# Independent source invariants continue even if a mutation step failed.
run_step "kotlin-source-integrity" bash -c '
  set -u
  rc=0
  test -s activity_fixed.kt || { echo "ERROR: activity_fixed.kt missing/empty"; rc=1; }
  test -s stage_gate.kt || { echo "ERROR: stage_gate.kt missing/empty"; rc=1; }
  grep -Fq "object ProductionTruth" activity_fixed.kt || { echo "ERROR: ProductionTruth object missing"; rc=1; }
  grep -Fq "ProductionTruth.button(13)" activity_fixed.kt || { echo "ERROR: stage 13 button is not registry-bound"; rc=1; }
  grep -Fq "ProductionTruth.stageNames" stage_gate.kt || { echo "ERROR: StageGate is not registry-bound"; rc=1; }
  if grep -Fq ".take(30)" activity_fixed.kt; then echo "ERROR: silent scene truncation remains"; rc=1; fi
  if grep -Fq "VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character" activity_fixed.kt; then echo "ERROR: generic prompt replacement remains"; rc=1; fi
  if grep -Fq "},1500)" activity_fixed.kt; then echo "ERROR: fixed 1500ms recording wait remains"; rc=1; fi
  exit "$rc"
'

run_step "contract-json-validation" python3 -c '
import json
from pathlib import Path
p=Path("production_truth_contract.json")
o=json.loads(p.read_text(encoding="utf-8"))
assert o["schema"] == 2
assert o["stage_count"] == 13
assert [s["id"] for s in o["stages"]] == list(range(1,14))
assert len({s["name"] for s in o["stages"]}) == 13
assert len({s["button"] for s in o["stages"]}) == 13
for group, values in o["vocabulary"].items():
    vals=list(values.values()) if isinstance(values,dict) else (values if isinstance(values,list) else [values])
    assert all(isinstance(v,str) and v.strip() for v in vals), group
    assert not any(any(t in v.upper() for t in ("TODO","FIXME","PLACEHOLDER")) for v in vals), group
print("CONTRACT_JSON_PASS")
'

{
  echo
  echo "============================================================"
  echo "PRODUCTION TRUTH PIPELINE FINAL"
  echo "cells_total=${TOTAL}"
  echo "cells_failed=${FAILED}"
  echo "full_log=${LOG_DIR}/00-combined.log"
  echo "============================================================"
} | tee -a "$LOG_DIR/00-combined.log"

echo
cat "$LOG_DIR/00-combined.log"

if [[ "$FAILED" -ne 0 ]]; then
  exit 1
fi
exit 0
