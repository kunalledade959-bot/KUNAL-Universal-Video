#!/usr/bin/env python3
"""Generate the in-app Production Truth authority from the canonical contract.

The contract is the only editable source for stage names and button labels. This
script validates the contract, injects a generated Kotlin authority into the APK
source, replaces UI/gate literals with authority references, and prints a complete
machine-readable log before returning a non-zero status on any defect.
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
changes: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def kotlin_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


try:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"contract parse failed: {type(exc).__name__}: {exc}")
    contract = {}

if not ACTIVITY.is_file():
    fail("activity_fixed.kt missing")
if not GATE.is_file():
    fail("stage_gate.kt missing")

stages = contract.get("stages", []) if isinstance(contract, dict) else []
if contract.get("schema") != 2:
    fail("contract schema must be 2")
if contract.get("app_id") != "com.kunal.universalvideo":
    fail("contract app_id mismatch")
if contract.get("stage_count") != 13:
    fail("contract stage_count must be 13")
if len(stages) != 13 or [x.get("id") for x in stages] != list(range(1, 14)):
    fail("contract stage IDs must be exactly 1..13")

seen_names: set[str] = set()
seen_buttons: set[str] = set()
for s in stages:
    name = s.get("name", "")
    button = s.get("button", "")
    if not isinstance(name, str) or not name.strip():
        fail(f"stage {s.get('id')} has empty name")
    if not isinstance(button, str) or not button.strip():
        fail(f"stage {s.get('id')} has empty button")
    if name in seen_names:
        fail(f"duplicate stage name: {name}")
    if button in seen_buttons:
        fail(f"duplicate button label: {button}")
    seen_names.add(name)
    seen_buttons.add(button)

vocab = contract.get("vocabulary", {}) if isinstance(contract, dict) else {}
for group_name, group in vocab.items():
    if isinstance(group, dict):
        values = list(group.values())
    elif isinstance(group, list):
        values = group
    elif isinstance(group, str):
        values = [group]
    else:
        fail(f"vocabulary group {group_name} has unsupported type")
        continue
    for value in values:
        if not isinstance(value, str) or not value.strip():
            fail(f"empty vocabulary value in {group_name}")
        if any(token in value for token in ("TODO", "FIXME", "PLACEHOLDER", "<", ">")):
            fail(f"placeholder vocabulary value in {group_name}: {value!r}")

if not errors:
    activity = ACTIVITY.read_text(encoding="utf-8")
    gate = GATE.read_text(encoding="utf-8")

    marker_start = "// <PRODUCTION_TRUTH_AUTHORITY>"
    marker_end = "// </PRODUCTION_TRUTH_AUTHORITY>"
    # Strip any previous generated block before editing the hand-written UI.
    if marker_start in activity and marker_end in activity:
        activity = re.sub(
            re.escape(marker_start) + r".*?" + re.escape(marker_end) + r"\n*",
            "",
            activity,
            count=1,
            flags=re.DOTALL,
        )

    # Bind every canonical button string outside the generated block. This works
    # both before and after the progressive single-stage UI patch, whose structure
    # uses listOf("label" to { ... }) rather than button("label").
    for s in stages:
        raw = kotlin_string(s["button"])
        replacement = f"ProductionTruth.button({s['id']})"
        count = activity.count(raw)
        if count != 1:
            fail(f"canonical button label for stage {s['id']} expected exactly once before binding, found {count}")
        else:
            activity = activity.replace(raw, replacement, 1)
            changes.append(f"stage {s['id']} button bound to ProductionTruth")

    generated = [
        marker_start,
        "/** GENERATED from production_truth_contract.json. DO NOT EDIT MANUALLY. */",
        "object ProductionTruth {",
        f"    const val APP_ID: String = {kotlin_string(contract['app_id'])}",
        f"    const val APP_NAME: String = {kotlin_string(vocab['APP_NAME'])}",
        "    val stageNames: List<String> = listOf(",
    ]
    for s in stages:
        generated.append(f"        {kotlin_string(s['name'])},")
    generated += [
        "    )",
        "    val buttonLabels: List<String> = listOf(",
    ]
    for s in stages:
        generated.append(f"        {kotlin_string(s['button'])},")
    generated += [
        "    )",
        "    fun stageName(id: Int): String = stageNames.getOrElse(id - 1) { \"UNKNOWN\" }",
        "    fun button(id: Int): String = buttonLabels.getOrElse(id - 1) { \"UNKNOWN\" }",
        f"    const val SCENE_FIELDS: String = {kotlin_string('|'.join(vocab['SCENE_FIELDS']))}",
        f"    const val PROMPT_FIELDS: String = {kotlin_string('|'.join(vocab['PROMPT_FIELDS']))}",
        f"    const val AUDIO_LABELS: String = {kotlin_string('|'.join(vocab['AUDIO_LABELS']))}",
        f"    const val EXPORT_METADATA: String = {kotlin_string('|'.join(vocab['EXPORT_METADATA']))}",
        marker_end,
    ]
    block = "\n".join(generated) + "\n\n"

    anchor = "class MainActivity"
    if anchor not in activity:
        fail("MainActivity class anchor missing")
    else:
        activity = activity.replace(anchor, block + anchor, 1)
        changes.append("inserted generated ProductionTruth authority")

    pattern = re.compile(
        r'private val stages = arrayOf\(.*?\)\.mapIndexed \{ i, n -> Stage\(i \+ 1, n\) \}\.toMutableList\(\)',
        re.DOTALL,
    )
    replacement = 'private val stages = ProductionTruth.stageNames.mapIndexed { i, n -> Stage(i + 1, n) }.toMutableList()'
    gate, n = pattern.subn(replacement, gate, count=1)
    if n != 1:
        # A previous generated binding is already authoritative. Do not fail merely
        # because this is a repeated idempotent invocation.
        if "ProductionTruth.stageNames" in gate:
            changes.append("StageGate already bound to ProductionTruth")
        else:
            fail(f"StageGate stage-name authority replacement expected 1, found {n}")
    else:
        changes.append("StageGate stage names bound to ProductionTruth")

    if "ProductionTruth.button(13)" not in activity:
        fail("generated button authority not present for stage 13")
    if "ProductionTruth.stageNames" not in gate:
        fail("StageGate is not bound to generated stage names")
    if activity.count("ProductionTruth.button(") != 13:
        fail("activity must contain exactly 13 ProductionTruth button bindings")

    ACTIVITY.write_text(activity, encoding="utf-8")
    GATE.write_text(gate, encoding="utf-8")

report = {
    "status": "PASS" if not errors else "FAIL",
    "contract": str(CONTRACT.relative_to(ROOT)),
    "errors": errors,
    "changes": changes,
    "stage_count": len(stages),
    "authority": "ProductionTruth",
    "note": "A non-zero result is emitted only after the complete report is printed."
}
print(json.dumps(report, indent=2, ensure_ascii=False))
raise SystemExit(1 if errors else 0)
