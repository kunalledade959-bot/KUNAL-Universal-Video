#!/usr/bin/env python3
"""Deterministically wire the checked-in production Activity and StageGate into V3."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
builder = ROOT / "pro_repair_v3.py"
activity = ROOT / "activity_fixed.kt"
stage_gate = ROOT / "stage_gate.kt"

for p in (builder, activity, stage_gate):
    if not p.is_file():
        raise SystemExit(f"PROD_WIRING: missing {p.name}")

s = builder.read_text(encoding="utf-8")
a = activity.read_text(encoding="utf-8").strip()
g = stage_gate.read_text(encoding="utf-8").strip()

# Replace only the embedded Activity literal. This is deliberately boundary-based
# because earlier hardening passes may rewrite the surrounding builder text.
start = s.find("ACTIVITY=r'''\n")
if start < 0:
    start = s.find("ACTIVITY=r'''")
if start < 0:
    raise SystemExit("PROD_WIRING: ACTIVITY literal start not found")
body_start = s.find("\n", start) + 1
end = s.find("'''\nMANIFEST=", body_start)
if end < 0:
    raise SystemExit("PROD_WIRING: ACTIVITY literal end not found")
replacement = "ACTIVITY=r'''\n" + a + "\n'''\nMANIFEST="
s = s[:start] + replacement + s[end + len("'''\nMANIFEST="):]

# Add the locked StageGate literal once, immediately before MANIFEST.
if "STAGE_GATE=r'''" not in s:
    marker = "MANIFEST=r'''"
    idx = s.find(marker)
    if idx < 0:
        raise SystemExit("PROD_WIRING: MANIFEST marker not found")
    s = s[:idx] + "STAGE_GATE=r'''\n" + g + "\n'''\n" + s[idx:]

# Earlier hardening passes are allowed to rewrite the reconstruction loop, so
# do not match one brittle string. Parse the Python builder and find the loop
# whose file map contains MainActivity.kt <- ACTIVITY, then append StageGate.kt
# to that same reconstruction list. This survives formatting and hardening
# changes while modifying only the intended generation list.
if '"StageGate.kt",STAGE_GATE' not in s:
    try:
        tree = ast.parse(s)
    except SyntaxError as e:
        raise SystemExit(f"PROD_WIRING: builder AST invalid after patching: {e}")

    target_list = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.iter, (ast.List, ast.Tuple)):
            continue
        for item in node.iter.elts:
            if not isinstance(item, (ast.Tuple, ast.List)) or len(item.elts) < 2:
                continue
            first, second = item.elts[0], item.elts[1]
            if (isinstance(first, ast.Constant) and first.value == "MainActivity.kt"
                    and isinstance(second, ast.Name) and second.id == "ACTIVITY"):
                target_list = node.iter
                break
        if target_list is not None:
            break

    if target_list is None:
        raise SystemExit("PROD_WIRING: reconstruction Activity mapping not found")

    lines = s.splitlines(keepends=True)
    line_no = target_list.end_lineno - 1
    end_col = target_list.end_col_offset
    line = lines[line_no]
    close_index = end_col - 1
    if close_index < 0 or close_index >= len(line) or line[close_index] != ']':
        raise SystemExit("PROD_WIRING: reconstruction list boundary invalid")
    lines[line_no] = line[:close_index] + ',("StageGate.kt",STAGE_GATE)' + line[close_index:]
    s = ''.join(lines)

builder.write_text(s, encoding="utf-8")
print("PROD_WIRING=PASS")
