#!/usr/bin/env python3
"""Fail-closed registry for repository-native top-1 production components."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELECTED = {
    "canonical_contract": "production_truth_contract.json",
    "authority_codegen": ".github/scripts/production_truth_codegen.py",
    "top1_repair_audit": ".github/scripts/top1_exhaustive_truth_cell.py",
    "independent_audit": ".github/scripts/production_truth_audit.py",
    "runtime_matrix": "13_STAGE_RUNTIME_TEST_MATRIX.md",
    "micro_component_contract": "PROVEN_TOP1_MICRO_COMPONENT_CONTRACT.md",
    "stage_problem_catalog": "SEQUENCE_13_STAGE_PROBLEM_CATALOG.md",
    "production_pipeline": ".github/scripts/production_truth_pipeline.sh",
    "apk_source": "activity_fixed.kt",
    "gate_source": "stage_gate.kt",
}
errors=[]; checks=[]
def check(name, ok, detail=""):
    checks.append({"name":name,"result":"PASS" if ok else "FAIL",**({"detail":detail} if detail else {})})
    if not ok: errors.append(name + (": "+detail if detail else ""))
for role, rel in SELECTED.items(): check(f"component:{role}",(ROOT/rel).is_file(),rel)
try: contract=json.loads((ROOT/SELECTED["canonical_contract"]).read_text(encoding="utf-8")); check("contract:parse",True)
except Exception as e: contract={}; check("contract:parse",False,f"{type(e).__name__}: {e}")
stages=contract.get("stages",[]) if isinstance(contract,dict) else []
check("contract:13-stages",contract.get("stage_count")==13 and [s.get("id") for s in stages]==list(range(1,14)))
check("contract:app-id",contract.get("app_id")=="com.kunal.universalvideo")
activity=(ROOT/"activity_fixed.kt").read_text(encoding="utf-8",errors="replace") if (ROOT/"activity_fixed.kt").is_file() else ""
gate=(ROOT/"stage_gate.kt").read_text(encoding="utf-8",errors="replace") if (ROOT/"stage_gate.kt").is_file() else ""
pipeline=(ROOT/SELECTED["production_pipeline"]).read_text(encoding="utf-8",errors="replace") if (ROOT/SELECTED["production_pipeline"]).is_file() else ""
check("authority:ProductionTruth","object ProductionTruth" in activity)
check("authority:13-buttons",activity.count("ProductionTruth.button(")==13,str(activity.count("ProductionTruth.button(")))
check("authority:StageGate","ProductionTruth.stageNames" in gate)
check("safety:no-scene-truncation",".take(30)" not in activity)
check("safety:no-generic-prompt","VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character" not in activity)
# Only reject the legacy Stage-10 stop implementation. Other 1500ms values,
# such as target-operation polling, are independent and must not be conflated.
stop_start=activity.find("    fun stopRecordingFromBridge(){")
stop_end=activity.find("\n\n    private fun latestRecording",stop_start)
stop_block=activity[stop_start:stop_end] if stop_start>=0 and stop_end>stop_start else ""
check("safety:no-fixed-recording-wait", "},1500)" not in stop_block)
check("safety:recording-finalization-polling","waitForRecordingFinalization" in stop_block and "System.currentTimeMillis()+10000L" in stop_block)
check("pipeline:top1-cell","top1-exhaustive-repair-and-audit" in pipeline)
check("pipeline:independent-audit","production-truth-audit" in pipeline)
report={"status":"PASS" if not errors else "FAIL","selected":SELECTED,"checks":checks,"reference_policy":{"verified_baseline_branch":"LOCKED-APK-RUN50-VERIFIED","use":"reference only; never overwrite hardened production source"}}
print(json.dumps(report,indent=2,ensure_ascii=False))
raise SystemExit(1 if errors else 0)
