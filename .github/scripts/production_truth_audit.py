#!/usr/bin/env python3
"""Complete static audit for the canonical 13-stage production contract.

The audit collects every finding, prints the complete report, and only then
returns non-zero. Static PASS is never promoted to runtime/device PASS.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "production_truth_contract.json"
ACTIVITY = ROOT / "activity_fixed.kt"
GATE = ROOT / "stage_gate.kt"
REPAIR = ROOT / "pro_repair_v3.py"

errors: list[str] = []
findings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)


def values_of(group):
    if isinstance(group, dict):
        return list(group.values())
    if isinstance(group, list):
        return group
    if isinstance(group, str):
        return [group]
    return []

try:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    contract = {}
    error(f"contract parse failed: {type(exc).__name__}: {exc}")

activity = ACTIVITY.read_text(encoding="utf-8") if ACTIVITY.is_file() else ""
gate = GATE.read_text(encoding="utf-8") if GATE.is_file() else ""
repair = REPAIR.read_text(encoding="utf-8") if REPAIR.is_file() else ""
if not ACTIVITY.is_file(): error("activity_fixed.kt missing")
if not GATE.is_file(): error("stage_gate.kt missing")
if not REPAIR.is_file(): error("pro_repair_v3.py missing")

if contract.get("schema") != 2: error("contract schema must be 2")
if contract.get("app_id") != "com.kunal.universalvideo": error("contract app_id mismatch")
if contract.get("stage_count") != 13: error("contract stage_count is not 13")
stages = contract.get("stages", [])
if len(stages) != 13 or [x.get("id") for x in stages] != list(range(1,14)):
    error("contract stage IDs are not exactly 1..13")

names = [x.get("name", "") for x in stages]
buttons = [x.get("button", "") for x in stages]
if len(set(names)) != 13: error("duplicate stage names detected")
if len(set(buttons)) != 13: error("duplicate button labels detected")
for s in stages:
    if not isinstance(s.get("name"), str) or not s["name"].strip(): error(f"stage {s.get('id')} has empty name")
    if not isinstance(s.get("button"), str) or not s["button"].strip(): error(f"stage {s.get('id')} has empty button")

vocab = contract.get("vocabulary", {})
required_groups = {"APP_NAME", "STATUS_MESSAGES", "ERROR_MESSAGES", "SCENE_FIELDS", "AUDIO_LABELS", "EXPORT_METADATA", "PROMPT_FIELDS", "MATERIAL_RULES"}
for g in sorted(required_groups - set(vocab)): error(f"missing vocabulary group: {g}")
for group_name, group in vocab.items():
    vals = values_of(group)
    if not vals: error(f"empty vocabulary group: {group_name}")
    for value in vals:
        if not isinstance(value, str) or not value.strip(): error(f"empty vocabulary value in {group_name}")
        if any(token in value.upper() for token in ("TODO", "FIXME", "PLACEHOLDER")):
            error(f"placeholder vocabulary value in {group_name}: {value!r}")

# The generated authority must be present and must own all 13 stage labels.
if "object ProductionTruth" not in activity: error("ProductionTruth authority missing from APK source")
if activity.count("ProductionTruth.button(") != 13: error("APK UI does not contain exactly 13 registry-bound button references")
if "ProductionTruth.stageNames" not in gate: error("StageGate is not bound to ProductionTruth.stageNames")
if "DO NOT EDIT MANUALLY" not in activity: error("generated authority marker missing")

# Real Stage-2 connection invariants. These are source-level prerequisites for
# physical-device verification, never a substitute for that verification.
stage2_requirements = {
    "stage2_async_binding_wait": "UniversalAccessibilityService.instance==null",
    "stage2_binding_timeout": "System.currentTimeMillis()+8000",
    "stage2_health_endpoint": '"/health"',
    "stage2_status_endpoint": '"/status"',
    "stage2_ping_protocol": "ControllerProtocol.PING",
    "stage2_pong_protocol": '"PONG"',
    "stage2_session_binding": 'session_id",
    "stage2_service_bound_status": '"service_bound"',
}
for name, needle in stage2_requirements.items():
    if needle not in activity and needle not in repair:
        error(f"Stage 2 handshake invariant missing: {name}")

# Truth-control invariants.
for symbol in ("resetForRepair", "invalidateDownstream", "validEvidence", "commit()", 'put("sha256"', 'put("run_id"', "State.RUNNING"):
    if symbol not in gate: error(f"StageGate missing truth-control symbol: {symbol}")
if '"final_pass"' not in gate: error("StageGate does not expose final_pass")

# Known unsafe shortcuts are hard failures. The report still collects all of them.
shortcuts = {
    "silent_scene_truncation": r"\.take\(30\)",
    "generic_prompt_replacement": r"VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character",
    "fixed_recording_wait": r"postDelayed\(\{.*?latestRecording\(\).*?\},1500\)",
    "unbounded_tree_walk": r"for\(\w+ in 0 until n\.childCount\)probe\(n\.getChild",
    "unbounded_deep_walk": r"for\(i in 0 until n\.childCount\)walk\(n\.getChild",
    "non_durable_story_write": r"putString\(STORY,s\)\.apply\(\)",
}
for name, pattern in shortcuts.items():
    if re.search(pattern, activity, re.DOTALL):
        findings.append(name)
        error(f"unsafe shortcut present: {name}")

# Explicitly reject a fake evidence path that can mark PASS without the gate.
for match in re.finditer(r"state\s*=\s*StageGate\.State\.PASS", activity):
    error(f"direct PASS state mutation at source offset {match.start()}")

report = {
    "contract": str(CONTRACT.relative_to(ROOT)),
    "authority": "ProductionTruth",
    "errors": errors,
    "unsafe_shortcuts": findings,
    "static_contract_pass": not errors,
    "runtime_pass": False,
    "real_device_pass": False,
    "release_pass": False,
    "note": "Static PASS is not runtime PASS. Real-device evidence is mandatory before release."
}
print(json.dumps(report, indent=2, ensure_ascii=False))
raise SystemExit(1 if errors else 0)
