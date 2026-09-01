#!/usr/bin/env python3
"""Non-blocking repository inventory for safe, evidence-first repairs.
Never modifies source files. Findings are recorded; the audit itself exits 0."""
from __future__ import annotations
import hashlib, json, re, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
OUT = ROOT / "PRE_REPAIR_EXHAUSTIVE_REPORT.md"
SKIP = {".git", ".gradle", "build", ".idea", "node_modules"}
TEXT_EXT = {".kt", ".java", ".xml", ".gradle", ".kts", ".py", ".sh", ".yml", ".yaml", ".json", ".md", ".properties", ".txt"}

def safe_text(p: Path):
    try: return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e: return f"<READ_ERROR: {e}>"

def sha(p: Path):
    h=hashlib.sha256()
    try:
        with p.open("rb") as f:
            for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
        return h.hexdigest()
    except Exception: return "READ_ERROR"

def run(cmd):
    try:
        r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=30)
        return r.returncode,(r.stdout+r.stderr).strip()
    except Exception as e: return 99,str(e)

files=[]
for p in ROOT.rglob("*"):
    if not p.is_file() or any(part in SKIP for part in p.parts): continue
    rel=p.relative_to(ROOT).as_posix()
    files.append((rel,p))
files.sort()

report=[]
report += ["# PRE-REPAIR EXHAUSTIVE INVENTORY", "", f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "", "This audit is read-only. It does not repair or modify production source.", ""]
report += ["## Repository inventory", "", f"Files discovered: **{len(files)}**", ""]
report += ["| File | Bytes | SHA-256 |", "|---|---:|---|"]
for rel,p in files:
    try: size=p.stat().st_size
    except Exception: size=-1
    report.append(f"| `{rel}` | {size} | `{sha(p)}` |")

# Android/source inventories
report += ["", "## Android/source inventory", ""]
for kind, pattern in [("Kotlin", "*.kt"),("Java", "*.java"),("Manifest", "**/AndroidManifest.xml"),("Gradle", "*.gradle"),("Gradle Kotlin", "*.gradle.kts"),("XML", "*.xml"),("Workflows", ".github/workflows/*.yml")]:
    found=sorted({p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern) if p.is_file()})
    report += [f"### {kind} ({len(found)})", ""] + [f"- `{x}`" for x in found] + [""]

# Workflow trigger map and accidental auto-run detection
report += ["## Workflow trigger map", "", "| Workflow | push | dispatch |", "|---|---|---|"]
for rel,p in files:
    if rel.startswith(".github/workflows/") and rel.endswith((".yml",".yaml")):
        t=safe_text(p)
        push="yes" if re.search(r"(?m)^\s*push\s*:",t) else "no"
        dispatch="yes" if re.search(r"(?m)^\s*workflow_dispatch\s*:",t) else "no"
        report.append(f"| `{rel}` | {push} | {dispatch} |")
report += [""]

# References to local files, conservative and evidence-only.
known={rel for rel,_ in files}
missing=[]
for rel,p in files:
    if p.suffix.lower() not in TEXT_EXT: continue
    t=safe_text(p)
    refs=re.findall(r"(?:bash|python3|python|source|uses:|path:|file:|include\s+)[ \t:=\"']+([A-Za-z0-9_./${}-]+)",t)
    for ref in refs:
        ref=ref.replace("${{ github.workspace }}/","").replace("${GITHUB_WORKSPACE}/","")
        if ref.startswith("${") or "://" in ref: continue
        if ref.startswith("./"): ref=ref[2:]
        if ref in known: continue
        if ref.endswith((".kt",".java",".py",".sh",".yml",".yaml",".xml",".gradle",".kts")):
            missing.append((rel,ref))
report += ["## Referenced local files not found", ""]
if missing:
    report += [f"Potential missing references: **{len(missing)}**", ""] + [f"- `{src}` references missing `{ref}`" for src,ref in sorted(set(missing))]
else: report += ["None detected by the conservative reference scan."]
report += [""]

# Suspicious implementation markers, never treated as proof of a bug.
susp=[]
for rel,p in files:
    if p.suffix.lower() not in TEXT_EXT: continue
    t=safe_text(p)
    for n,line in enumerate(t.splitlines(),1):
        if re.search(r"TODO|FIXME|HACK|XXX|throw NotImplemented|return null\s*//",line,re.I):
            susp.append((rel,n,line.strip()[:180]))
report += ["## Suspicious markers requiring review", ""]
report += [f"Markers found: **{len(susp)}**", ""]
report += [f"- `{r}:{n}` `{line}`" for r,n,line in susp[:500]]

# Syntax sanity for Python scripts; failures become findings, not harness failures.
report += ["", "## Python syntax checks", ""]
for rel,p in files:
    if p.suffix==".py":
        code,out=run(["python3","-m","py_compile",str(p)])
        report.append(f"- `{rel}`: **{'PASS' if code==0 else 'FAIL'}**" + (f" — `{out[-300:]}`" if code else ""))

# Git state evidence
code,out=run(["git","status","--short"])
report += ["", "## Git working-tree evidence", "", "```text", out or "CLEAN", "```", ""]

# Machine-readable summary embedded at end.
summary={"files":len(files),"missing_references":len(set(missing)),"suspicious_markers":len(susp),"generated_utc":datetime.now(timezone.utc).isoformat()}
report += ["## Machine summary", "", "```json", json.dumps(summary,indent=2), "```", ""]
OUT.write_text("\n".join(report),encoding="utf-8")
print(f"WROTE {OUT}")
print(json.dumps(summary))
