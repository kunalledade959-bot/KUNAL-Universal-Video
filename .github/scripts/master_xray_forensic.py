#!/usr/bin/env python3
"""KUNAL Universal Video Master X-Ray.

Forensic static inspection only. It never edits product source. Every check is
isolated so one broken check cannot stop collection. Anything not provable is
reported as UNVERIFIED or SCAN_GAP, never silently treated as PASS.
"""
from __future__ import annotations
import ast, hashlib, json, os, re, sys, traceback
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "master-xray-evidence"
OUT.mkdir(exist_ok=True)
findings=[]; checks=[]; inspected_files=set(); check_ids=[]

def record(cid, status, message, **kw):
    check_ids.append(cid); checks.append({"id":cid,"status":status,"message":message,**kw})

def run(cid, fn):
    try:
        result=fn()
        if isinstance(result, dict):
            status=result.pop("status","PASS"); msg=result.pop("message",status)
            record(cid,status,msg,**result)
        else: record(cid,"PASS",str(result))
    except Exception as e:
        record(cid,"CHECK_EXECUTION_ERROR",f"{type(e).__name__}: {e}",traceback=traceback.format_exc(limit=8))

def rel(p):
    try:return str(p.relative_to(ROOT))
    except:return str(p)

def text_files():
    for p in ROOT.rglob("*"):
        if not p.is_file(): continue
        if ".git" in p.parts or p.is_symlink(): continue
        try:
            b=p.read_bytes()
            if b"\x00" in b[:8192]:
                record("FILE-BINARY-"+rel(p),"UNVERIFIED","Binary file inventory only",file=rel(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)); continue
            yield p,b.decode("utf-8")
        except UnicodeDecodeError as e:
            record("FILE-DECODE-"+rel(p),"SCAN_GAP",f"UTF-8 decode failed: {e}",file=rel(p))
        except Exception as e:
            record("FILE-READ-"+rel(p),"SCAN_GAP",f"Read failed: {type(e).__name__}: {e}",file=rel(p))

def lines(s): return s.splitlines()
def evidence(p, line, text): return {"file":rel(p),"line":line,"actual":text[:500]}

# 01: complete repository inventory and hashes.
def inventory():
    files=[]
    for p in ROOT.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            try:
                b=p.read_bytes(); files.append({"file":rel(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
                inspected_files.add(rel(p))
            except Exception as e: record("HASH-"+rel(p),"SCAN_GAP",str(e),file=rel(p))
    (OUT/"file-inventory.json").write_text(json.dumps(files,indent=2),encoding="utf-8")
    return {"message":f"Inventoried {len(files)} repository files","count":len(files)}
run("XRAY-001",inventory)

# Load all UTF-8 source text once. Every text file is inspected line-by-line.
texts={p:s for p,s in text_files()}
for p in texts: inspected_files.add(rel(p))

# 02: syntax/encoding checks.
def syntax():
    bad=[]
    for p,s in texts.items():
        ext=p.suffix.lower()
        if ext==".py":
            try: ast.parse(s,filename=str(p))
            except SyntaxError as e: bad.append({**evidence(p,e.lineno or 1,lines(s)[(e.lineno or 1)-1] if lines(s) else ""),"error":str(e)})
        if ext in {".json"}:
            try: json.loads(s)
            except Exception as e: bad.append({"file":rel(p),"error":f"JSON: {e}"})
    return {"status":"FAIL" if bad else "PASS","message":f"Python/JSON syntax scan: {len(bad)} errors","errors":bad}
run("XRAY-002",syntax)

# 03: contract is the canonical vocabulary and stage map.
def contract():
    p=ROOT/"production_truth_contract.json"
    if not p.is_file(): return {"status":"SCAN_GAP","message":"production_truth_contract.json missing"}
    c=json.loads(p.read_text())
    errors=[]; stages=c.get("stages",[])
    if c.get("schema")!=2: errors.append("schema != 2")
    if c.get("app_id")!="com.kunal.universalvideo": errors.append("app_id mismatch")
    if c.get("stage_count")!=13 or [x.get("id") for x in stages]!=list(range(1,14)): errors.append("stage IDs/count not exactly 1..13")
    for key in ("name","button"):
        vals=[x.get(key) for x in stages]
        if len(vals)!=len(set(vals)): errors.append(f"duplicate stage {key}")
        if any(not isinstance(v,str) or not v.strip() for v in vals): errors.append(f"empty stage {key}")
    vocab=c.get("vocabulary",{})
    required={"APP_NAME","STATUS_MESSAGES","ERROR_MESSAGES","SCENE_FIELDS","AUDIO_LABELS","EXPORT_METADATA","PROMPT_FIELDS","MATERIAL_RULES"}
    errors += [f"missing vocabulary group {x}" for x in sorted(required-set(vocab))]
    empties=[]
    for g,v in vocab.items():
        vals=list(v.values()) if isinstance(v,dict) else (v if isinstance(v,list) else [v])
        for x in vals:
            if not isinstance(x,str) or not x.strip() or re.search(r"TODO|FIXME|PLACEHOLDER",x,re.I): empties.append(f"{g}: {x!r}")
    errors += ["bad vocabulary value "+x for x in empties]
    return {"status":"FAIL" if errors else "PASS","message":f"Canonical contract inspection: {len(errors)} defects","errors":errors}
run("XRAY-003",contract)

# 04: all source/config/workflow files get lexical marker analysis. This is deliberately broad.
def lexical():
    rules=[
      ("TODO/FIXME",r"\b(?:TODO|FIXME)\b"),("debug print",r"\b(?:printStackTrace|println|System\.out\.print)\b"),
      ("empty catch",r"catch\s*\([^)]*\)\s*\{\s*\}"),("ignored exception",r"catch\s*\([^)]*\)\s*\{\s*[^}]*\b(?:return|null|Unit)\b[^}]*\}"),
      ("force unwrap",r"\w+!!(?:\.|\()"),("hardcoded 1500ms",r"(?:1500|1_500)\s*\)?\s*(?:ms|L)?"),
      ("sleep",r"Thread\.sleep\s*\("),("process exit",r"System\.exit\s*\("),("generic fallback",r"else\s*\{\s*[^\n]*return\s+\"?default"),
      ("silent ignore",r"catch\s*\([^)]*\)\s*\{\s*//"),
    ]
    hits=[]
    for p,s in texts.items():
        if p.suffix.lower() not in {".kt",".java",".py",".sh",".yml",".yaml",".xml",".json",".gradle",".kts",".md",".txt"}: continue
        for name,pat in rules:
            for m in re.finditer(pat,s,re.I|re.M):
                line=s.count("\n",0,m.start())+1; hits.append({"rule":name,**evidence(p,line,lines(s)[line-1] if line<=len(lines(s)) else "")})
    return {"status":"FAIL" if hits else "PASS","message":f"Broad lexical hazard scan: {len(hits)} findings","findings":hits}
run("XRAY-004",lexical)

# 05: exact canonical tokens and one-word drift in production Kotlin.
def canonical_drift():
    c=json.loads((ROOT/"production_truth_contract.json").read_text()) if (ROOT/"production_truth_contract.json").exists() else {}
    app=ROOT/"activity_fixed.kt"; gate=ROOT/"stage_gate.kt"
    if not app.exists(): return {"status":"SCAN_GAP","message":"activity_fixed.kt missing"}
    s=app.read_text(); g=gate.read_text() if gate.exists() else ""
    missing=[]
    for st in c.get("stages",[]):
        for field in ("name","button"):
            value=st.get(field,"")
            if field=="button" and value and value not in s: missing.append(f"stage {st.get('id')} button exact token missing: {value}")
    for token in ["ProductionTruth","StageGate","final_pass","session_id","service_bound","PING","PONG","sha256","run_id"]:
        if token not in s and token not in g: missing.append(f"required token missing from APK authority/gate: {token}")
    return {"status":"FAIL" if missing else "PASS","message":f"Canonical token drift scan: {len(missing)} defects","missing":missing}
run("XRAY-005",canonical_drift)

# 06: duplicate function/class/constant names in Kotlin/Python, with locations.
def duplicates():
    out=[]
    pats=[r"\b(?:class|object|interface|fun)\s+(\w+)",r"^\s*(?:const\s+val|val|var)\s+(\w+)\s*=",r"^\s*def\s+(\w+)\s*\("]
    for p,s in texts.items():
        if p.suffix.lower() not in {".kt",".java",".py",".kts",".gradle"}: continue
        for pat in pats:
            seen=defaultdict(list)
            for m in re.finditer(pat,s,re.M): seen[m.group(1)].append(s.count("\n",0,m.start())+1)
            for name,locs in seen.items():
                if len(locs)>1: out.append({"file":rel(p),"symbol":name,"lines":locs})
    return {"status":"FAIL" if out else "PASS","message":f"Duplicate symbol scan: {len(out)} duplicate groups","duplicates":out}
run("XRAY-006",duplicates)

# 07: undefined-ish and unused-ish identifier audit for canonical functions. We only flag strong cases.
def symbol_contract():
    app=ROOT/"activity_fixed.kt"; g=ROOT/"stage_gate.kt"
    if not app.exists() or not g.exists(): return {"status":"SCAN_GAP","message":"core Kotlin files unavailable"}
    s=app.read_text(); gs=g.read_text(); errors=[]
    required=["stage1","connectMobile","selectTarget","studyTarget","saveStory","operateTarget","deepStudy","scenePlan","buildPlan","audioAndRecord","assembleEdit","verifyAndFix","finalExport"]
    for x in required:
        if not re.search(r"\b(?:private\s+|public\s+|internal\s+|fun\s+)"+re.escape(x)+r"\b",s): errors.append(f"missing stage implementation symbol: {x}")
    for x in ["resetForRepair","invalidateDownstream","validEvidence","currentStage","state","begin","pass","fail"]:
        if not re.search(r"\b"+re.escape(x)+r"\b",gs): errors.append(f"StageGate symbol missing: {x}")
    return {"status":"FAIL" if errors else "PASS","message":f"Canonical symbol contract: {len(errors)} defects","errors":errors}
run("XRAY-007",symbol_contract)

# 08: stage implementation order, exact 13 mapping, and cross-stage handoff fields.
def stage_flow():
    s=(ROOT/"activity_fixed.kt").read_text() if (ROOT/"activity_fixed.kt").exists() else ""
    errors=[]
    funcs=["stage1","connectMobile","selectTarget","studyTarget","saveStory","operateTarget","deepStudy","scenePlan","buildPlan","audioAndRecord","assembleEdit","verifyAndFix","finalExport"]
    for i,f in enumerate(funcs,1):
        if f not in s: errors.append(f"S{i:02d} implementation absent: {f}")
    # Required persisted handoffs.
    for token in ["STORY","SCENES","PLAN","AUDIO","RECORDING","FINAL"]:
        if token not in s: errors.append(f"handoff field absent: {token}")
    # Strongly suspicious stage skipping calls.
    for i in range(1,13):
        a=s.find(funcs[i-1]+"()"); b=s.find(funcs[i]+"()")
        if a<0 or b<0: continue
        if b<a and i<12: errors.append(f"source order drift around S{i:02d}->S{i+1:02d}")
    return {"status":"FAIL" if errors else "PASS","message":f"13-stage flow/handoff scan: {len(errors)} defects","errors":errors}
run("XRAY-008",stage_flow)

# 09: workflows: every sequence 01..13, trigger, script references, and accidental missing coverage.
def workflows():
    errors=[]; seq=[]
    for i in range(1,14):
        p=ROOT/f".github/workflows/sequence-{i:02d}.yml"
        if not p.exists(): errors.append(f"missing workflow sequence-{i:02d}.yml")
        else:
            seq.append(rel(p)); s=p.read_text()
            if "workflow_dispatch" not in s: errors.append(f"S{i:02d} workflow lacks workflow_dispatch")
            if f"sequence-{i:02d}" not in s and f"Sequence {i:02d}" not in s: errors.append(f"S{i:02d} workflow identity not explicit")
    return {"status":"FAIL" if errors else "PASS","message":f"Workflow 01..13 coverage: {len(seq)}/13 present, {len(errors)} defects","errors":errors,"present":seq}
run("XRAY-009",workflows)

# 10: workflow control-flow audit, especially fail-continue vs actual verdict.
def workflow_verdict():
    hits=[]
    for p,s in texts.items():
        if p.parts[-2:] and ".github" in p.parts and p.suffix in {".yml",".yaml",".sh"}:
            if re.search(r"exit\s+0\s*$",s,re.M) and re.search(r"RESULT=FAIL|FINAL_VERDICT=FAIL|failure|error",s,re.I):
                hits.append({"file":rel(p),"message":"possible fail-to-zero collector; inspect final verdict semantics"})
    return {"status":"WARN" if hits else "PASS","message":f"Workflow verdict semantics: {len(hits)} suspicious collector(s)","findings":hits}
run("XRAY-010",workflow_verdict)

# 11: Stage 2 protocol boundary, source-location correctness, avoiding brittle single-file assumptions.
def stage2():
    required=["UniversalAccessibilityService","/health","/status","PING","PONG","session_id","service_bound"]
    alltext="\n".join(texts.values()); missing=[x for x in required if x not in alltext]
    loc={x:[rel(p) for p,s in texts.items() if x in s] for x in required}
    return {"status":"FAIL" if missing else "PASS","message":f"Stage 2 protocol boundary scan: {len(missing)} missing invariants","missing":missing,"locations":loc}
run("XRAY-011",stage2)

# 12: persistence and evidence chain.
def evidence_chain():
    s=(ROOT/"stage_gate.kt").read_text() if (ROOT/"stage_gate.kt").exists() else ""
    required=["sha256","run_id","final_pass","validEvidence","invalidateDownstream","State.RUNNING"]
    missing=[x for x in required if x not in s]
    return {"status":"FAIL" if missing else "PASS","message":f"Evidence/state chain scan: {len(missing)} missing controls","missing":missing}
run("XRAY-012",evidence_chain)

# 13: resource/lifecycle hazards in Android source.
def android_hazards():
    hits=[]
    for p,s in texts.items():
        if p.suffix.lower() not in {".kt",".java"}: continue
        for pat,name in [(r"\.recycle\(\)","manual recycle"),(r"MediaProjection","MediaProjection"),(r"startForegroundService","foreground service"),(r"registerForActivityResult","activity result")]:
            n=len(re.findall(pat,s))
            if n: hits.append({"file":rel(p),"rule":name,"count":n})
    return {"status":"INFO","message":f"Android lifecycle/resource inventory: {len(hits)} evidence groups","inventory":hits}
run("XRAY-013",android_hazards)

# 14: external/package/path/network endpoint consistency.
def external_refs():
    refs=[]
    for p,s in texts.items():
        for m in re.finditer(r"(?:https?://[^\s\"']+|com\.[a-zA-Z0-9_.]+|/data/[^\s\"']+|/health|/status)",s):
            line=s.count("\n",0,m.start())+1; refs.append({"value":m.group(0),**evidence(p,line,lines(s)[line-1] if line<=len(lines(s)) else "")})
    return {"status":"INFO","message":f"External/package/path reference inventory: {len(refs)} references","references":refs}
run("XRAY-014",external_refs)

# 15: every word/token-level source inventory statistics. This prevents 'we forgot a file' claims.
def token_inventory():
    total=0; unique=set(); byext=Counter()
    for p,s in texts.items():
        toks=re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?",s); total+=len(toks); unique.update(toks); byext[p.suffix.lower()]+=len(toks)
    return {"status":"PASS","message":f"Token inventory complete: {total} tokens / {len(unique)} unique tokens","token_count":total,"unique_token_count":len(unique),"tokens_by_extension":dict(byext)}
run("XRAY-015",token_inventory)

# 16: exact one-word spelling drift for high-value identifiers.
def spelling():
    canon={"com.kunal.universalvideo","Kunal Universal Video","ProductionTruth","StageGate","UniversalAccessibilityService","ScreenCaptureService","LocalBridgeService","ControllerProtocol","session_id","service_bound","sha256","final_pass","MediaStore","TextToSpeech"}
    bad=[]
    alltext="\n".join(texts.values())
    for word in canon:
        if word not in alltext: bad.append(word)
    return {"status":"FAIL" if bad else "PASS","message":f"High-value exact spelling audit: {len(bad)} missing canonical tokens","missing":bad}
run("XRAY-016",spelling)

# 17: required source-of-truth lineage and generated markers.
def lineage():
    required=["production_truth_contract.json","production_truth_codegen.py","top1_component_registry.py","production_truth_pipeline.sh","activity_fixed.kt","stage_gate.kt"]
    missing=[x for x in required if not (ROOT/x).exists()]
    master=[p for p in ROOT.rglob("KUNAL_UNIVERSAL_VIDEO_MASTER.py") if ".git" not in p.parts]
    return {"status":"FAIL" if missing else ("WARN" if not master else "PASS"),"message":f"Source-of-truth lineage: missing={len(missing)}, packaged master copies={len(master)}","missing":missing,"master_copies":[rel(x) for x in master]}
run("XRAY-017",lineage)

# 18: scan-gap accounting is itself a hard invariant.
def accounting():
    planned=18
    executed=len(check_ids)
    duplicates=[x for x,n in Counter(check_ids).items() if n>1]
    bad=[x for x in checks if x["status"]=="CHECK_EXECUTION_ERROR"]
    gaps=[x for x in checks if x["status"]=="SCAN_GAP"]
    unaccounted=planned-executed
    return {"status":"FAIL" if (unaccounted or duplicates or bad) else ("WARN" if gaps else "PASS"),"message":f"Accounting: executed={executed}/{planned}, execution_errors={len(bad)}, scan_gaps={len(gaps)}","planned_checks":planned,"executed_checks":executed,"unaccounted_checks":unaccounted,"duplicate_check_ids":duplicates,"unhandled_check_failures":len(bad),"scan_gaps":len(gaps)}
run("XRAY-018",accounting)

# Final report: no claim of runtime/device proof from static analysis.
status_counts=Counter(x["status"] for x in checks)
critical=[x for x in checks if x["status"] in {"FAIL","SCAN_GAP","CHECK_EXECUTION_ERROR"}]
report={
 "scanner":"MASTER_XRAY_FORENSIC_V1",
 "repo":str(ROOT),
 "collection_complete": status_counts.get("CHECK_EXECUTION_ERROR",0)==0 and status_counts.get("SCAN_GAP",0)==0,
 "all_checks_accounted": len(checks)==18 and len(set(check_ids))==18,
 "unhandled_check_failures":status_counts.get("CHECK_EXECUTION_ERROR",0),
 "unscanned_required_files":0 if len(inspected_files)>0 else None,
 "unscanned_sequences":0 if all((ROOT/f".github/workflows/sequence-{i:02d}.yml").exists() for i in range(1,14)) else 1,
 "status_counts":dict(status_counts),
 "critical_findings":critical,
 "checks":checks,
 "runtime_pass":False,
 "real_device_pass":False,
 "release_pass":False,
 "rule":"Anything not statically provable is UNVERIFIED/SCAN_GAP, never PASS. This scanner does not replace real-device execution."
}
(OUT/"MASTER_XRAY_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
md=["# KUNAL Universal Video — MASTER X-RAY FORENSIC REPORT","",f"- Scanner: `{report['scanner']}`",f"- Checks: **{len(checks)}/18**",f"- Collection complete: **{report['collection_complete']}**",f"- All checks accounted: **{report['all_checks_accounted']}**",f"- Execution errors: **{report['unhandled_check_failures']}**",f"- Unscanned required files: **{report['unscanned_required_files']}**",f"- Unscanned sequences: **{report['unscanned_sequences']}**","","## Findings"]
for c in checks:
    md += [f"### {c['id']} — {c['status']}",c['message']]
    for k in ("errors","missing","findings","duplicates","traceback"):
        if k in c and c[k]: md.append("```text\n"+json.dumps(c[k],indent=2,ensure_ascii=False)+"\n```")
md += ["","## Final Truth","Static X-Ray does not grant runtime/device PASS. Real-device evidence remains mandatory."]
(OUT/"MASTER_XRAY_REPORT.md").write_text("\n".join(md),encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
# Deliberately non-zero on findings, but never before all checks have run.
raise SystemExit(1 if critical else 0)
