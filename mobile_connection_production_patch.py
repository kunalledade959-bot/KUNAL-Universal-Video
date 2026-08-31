#!/usr/bin/env python3
"""Deterministically wire the checked-in production Activity and StageGate into V3."""
from pathlib import Path

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

# Do not depend on regex escaping or whitespace. Locate the literal boundaries
# exactly as Python source text and replace only the embedded Activity block.
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

# Add StageGate literal once, immediately before MANIFEST.
if "STAGE_GATE=r'''" not in s:
    marker = "MANIFEST=r'''"
    idx = s.find(marker)
    if idx < 0:
        raise SystemExit("PROD_WIRING: MANIFEST marker not found")
    s = s[:idx] + "STAGE_GATE=r'''\n" + g + "\n'''\n" + s[idx:]

# Make reconstruction emit the locked StageGate implementation alongside the
# real transport/accessibility/media components.
old = 'for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY)]:write(java/n,d)'
new = 'for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY),("StageGate.kt",STAGE_GATE)]:write(java/n,d)'
if old in s:
    s = s.replace(old, new, 1)
elif '"StageGate.kt",STAGE_GATE' not in s:
    raise SystemExit("PROD_WIRING: reconstruction write block not found")

builder.write_text(s, encoding="utf-8")
print("PROD_WIRING=PASS")
