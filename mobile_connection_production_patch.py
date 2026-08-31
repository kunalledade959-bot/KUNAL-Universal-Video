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

# Wire the checked-in Activity into the builder using stable literal boundaries.
start = s.find("ACTIVITY=r'''\n")
if start < 0:
    start = s.find("ACTIVITY=r'''")
if start < 0:
    raise SystemExit("PROD_WIRING: ACTIVITY literal start not found")
body_start = s.find("\n", start) + 1
end = s.find("'''\nMANIFEST=", body_start)
if end < 0:
    raise SystemExit("PROD_WIRING: ACTIVITY literal end not found")
s = s[:start] + "ACTIVITY=r'''\n" + a + "\n'''\nMANIFEST=" + s[end + len("'''\nMANIFEST="):]

# Wire StageGate exactly once before MANIFEST. If an earlier pass already added
# it, remove that old literal first so this operation remains deterministic.
while "STAGE_GATE=r'''" in s:
    st = s.find("STAGE_GATE=r'''\n")
    if st < 0:
        break
    sb = s.find("\n", st) + 1
    se = s.find("'''\nMANIFEST=", sb)
    if se < 0:
        raise SystemExit("PROD_WIRING: existing STAGE_GATE literal is malformed")
    s = s[:st] + s[se + len("'''\n"):]
marker = "MANIFEST=r'''"
idx = s.find(marker)
if idx < 0:
    raise SystemExit("PROD_WIRING: MANIFEST marker not found")
s = s[:idx] + "STAGE_GATE=r'''\n" + g + "\n'''\n" + s[idx:]

# The previous failures came from trying to identify one exact reconstruction
# line after other hardening scripts had rewritten it. Replace the complete
# reconstruct() function instead. Its boundaries are stable function names,
# and its implementation writes the authoritative Activity + StageGate files
# directly, so no formatting-sensitive loop matching remains.
r0 = s.find("def reconstruct():")
r1 = s.find("\ndef verify():", r0 + 1)
if r0 < 0 or r1 < 0:
    raise SystemExit("PROD_WIRING: reconstruct/verify function boundaries not found")

reconstruct = '''def reconstruct():
    shutil.rmtree(STAGE,ignore_errors=True);STAGE.mkdir(parents=True)
    if MASTER.is_file():
        mt=read(MASTER);ast.parse(mt);m=fmap(mt)
        if not isinstance(m,dict) or len(m)<10:raise RuntimeError("MASTER FILE MAP INVALID")
        for rel,data in m.items():write(STAGE/rel,str(data))
        log(f"[PASS] SOURCE MASTER {MASTER}")
    elif SOURCE_ZIP.is_file():
        with zipfile.ZipFile(SOURCE_ZIP) as z:
            if z.testzip():raise RuntimeError("SOURCE ZIP CRC/INTEGRITY FAILURE")
            z.extractall(STAGE)
        roots=[]
        for marker in STAGE.rglob("settings.gradle.kts"):
            r=marker.parent
            if (r/"app/build.gradle.kts").is_file() and (r/"app/src/main/AndroidManifest.xml").is_file():roots.append(r)
        if roots and roots[0] != STAGE/"android-controller":
            root=roots[0];dst=STAGE/"android-controller"
            if not dst.exists():shutil.copytree(root,dst)
        log(f"[PASS] SOURCE ZIP {SOURCE_ZIP}")
    else:raise RuntimeError("AUTHORITATIVE MASTER/PROJECT ZIP NOT FOUND")

    base=STAGE/"android-controller/app/src/main"
    java=base/"java/com/kunal/universalvideo";res=base/"res"
    for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY),("StageGate.kt",STAGE_GATE)]:
        write(java/n,d)
    for p,d in [(base/"AndroidManifest.xml",MANIFEST),(res/"xml/accessibility_service_config.xml",ACCESS_XML),(res/"layout/activity_main.xml",LAYOUT),(res/"values/strings.xml",STRINGS),(res/"values/styles.xml",STYLES),(STAGE/"android-controller/app/build.gradle.kts",APP_GRADLE),(STAGE/"android-controller/build.gradle.kts",ROOT_GRADLE),(STAGE/"android-controller/settings.gradle.kts",SETTINGS),(STAGE/"android-controller/gradle.properties",PROPS)]:
        write(p,d)
    for p in res.rglob("*.xml"):normxml(p)
'''
s = s[:r0] + reconstruct + s[r1:]

# Verify the modified builder before committing it. This catches malformed
# Python source in this patch itself instead of discovering it in CI.
import ast
try:
    ast.parse(s)
except SyntaxError as e:
    raise SystemExit(f"PROD_WIRING: builder AST invalid after wiring: {e}")

builder.write_text(s, encoding="utf-8")
print("PROD_WIRING=PASS")
