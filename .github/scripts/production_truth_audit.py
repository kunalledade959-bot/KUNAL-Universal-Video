#!/usr/bin/env python3
"""Fail-closed static audit for the canonical 13-stage production contract.

This audit intentionally does not claim runtime PASS. It verifies that the source
contains the canonical stage surface and that known unsafe shortcuts are visible
for engineering remediation instead of silently becoming release evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "production_truth_contract.json"
ACTIVITY = ROOT / "activity_fixed.kt"
GATE = ROOT / "stage_gate.kt"

errors: list[str] = []
blockers: list[str] = []

if not CONTRACT.is_file():
    errors.append("production_truth_contract.json missing")
if not ACTIVITY.is_file():
    errors.append("activity_fixed.kt missing")
if not GATE.is_file():
    errors.append("stage_gate.kt missing")

if not errors:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    activity = ACTIVITY.read_text(encoding="utf-8")
    gate = GATE.read_text(encoding="utf-8")

    if contract.get("stage_count") != 13:
        errors.append("contract stage_count is not 13")

    stages = contract.get("stages", [])
    if len(stages) != 13 or [x.get("id") for x in stages] != list(range(1, 14)):
        errors.append("contract stage IDs are not exactly 1..13")

    for s in stages:
        button = s["button"]
        if button not in activity:
            errors.append(f"missing canonical button: {button}")

    required_gate_symbols = [
        "resetForRepair", "invalidateDownstream", "validEvidence", "commit()",
        'put("sha256"', 'put("run_id"', 'State.RUNNING'
    ]
    for symbol in required_gate_symbols:
        if symbol not in gate:
            errors.append(f"StageGate missing truth-control symbol: {symbol}")

    # These are hard blockers until the production implementation replaces them.
    known_shortcuts = {
        "silent_scene_truncation": r"\.take\(30\)",
        "generic_prompt_replacement": r"VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character",
        "fixed_recording_wait": r"postDelayed\(\{.*?latestRecording\(\).*?\},1500\)",
        "unbounded_tree_walk": r"for\(\w+ in 0 until n\.childCount\)probe\(n\.getChild",
        "unbounded_deep_walk": r"for\(i in 0 until n\.childCount\)walk\(n\.getChild",
        "non_durable_story_write": r"putString\(STORY,s\)\.apply\(\)",
    }
    for name, pattern in known_shortcuts.items():
        if re.search(pattern, activity, re.DOTALL):
            blockers.append(name)

    # Plain PASS calls are allowed only through the gate, but a runtime evidence
    # message must not be mistaken for artifact proof by this static audit.
    if '"final_pass"' not in gate:
        errors.append("StageGate does not expose final_pass")

report = {
    "contract": str(CONTRACT.relative_to(ROOT)),
    "errors": errors,
    "known_runtime_blockers": blockers,
    "static_contract_pass": not errors,
    "release_pass": False,
    "note": "Static contract PASS is not runtime PASS. Known blockers must be removed and 13 independent E2E + real-device evidence must pass before release."
}
print(json.dumps(report, indent=2, ensure_ascii=False))

# Contract structure errors are hard failures. Known runtime blockers are emitted
# as explicit evidence but do not terminate this inventory job, so independent
# remediation/testing can continue in later CI jobs.
raise SystemExit(1 if errors else 0)
