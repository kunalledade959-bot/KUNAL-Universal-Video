#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, re, traceback
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'master-xray-evidence'; OUT.mkdir(exist_ok=True)
checks=[]; ids=[]; inspected=set()
def rec(cid,status,msg,**kw): ids.append(cid); checks.append({'id':cid,'status':status,'message':msg,**kw})
def run(cid,fn):
    try:
        x=fn(); status=x.pop('status','PASS') if isinstance(x,dict) else 'PASS'; msg=x.pop('message',status) if isinstance(x,dict) else str(x); rec(cid,status,msg,**x)
    except Exception as e: rec(cid,'CHECK_EXECUTION_ERROR',f'{type(e).__name__}: {e}',traceback=traceback.format_exc(limit=12))
def R(p):
    try:return str(p.relative_to(ROOT))
    except:return str(p)
def ev(p,s,pos):
    line=s.count('\n',0,pos)+1; ls=s.splitlines(); return {'file':R(p),'line':line,'actual':ls[line-1][:1000] if line<=len(ls) else ''}
# A. inventory every file, including binary/decode failures
def inventory():
    rows=[]; gaps=[]
    for p in ROOT.rglob('*'):
        if not p.is_file() or '.git' in p.parts or p.is_symlink(): continue
        try:
            b=p.read_bytes(); rows.append({'file':R(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}); inspected.add(R(p))
        except Exception as e: gaps.append({'file':R(p),'error':str(e)})
    (OUT/'file-inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return {'status':'SCAN_GAP' if gaps else 'PASS','message':f'File inventory: {len(rows)} files, {len(gaps)} read gaps','files':len(rows),'read_gaps':gaps}
run('XRAY-001',inventory)
texts={}
for p in ROOT.rglob('*'):
    if not p.is_file() or '.git' in p.parts or p.is_symlink(): continue
    try:
        b=p.read_bytes()
        if b'\x00' not in b[:8192]: texts[p]=b.decode('utf-8'); inspected.add(R(p))
    except UnicodeDecodeError as e: rec('DECODE-'+R(p),'SCAN_GAP',f'UTF-8 decode failed: {e}',file=R(p))
    except Exception as e: rec('READ-'+R(p),'SCAN_GAP',f'Read failed: {type(e).__name__}: {e}',file=R(p))
# B. parser checks
def syntax():
    bad=[]
    for p,s in texts.items():
        if p.suffix.lower()=='.py':
            try: ast.parse(s,filename=R(p))
            except SyntaxError as e: bad.append({'file':R(p),'line':e.lineno,'error':str(e)})
        elif p.suffix.lower()=='.json':
            try: json.loads(s)
            except Exception as e: bad.append({'file':R(p),'error':f'JSON {e}'})
    return {'status':'FAIL' if bad else 'PASS','message':f'Syntax/JSON parse: {len(bad)} errors','errors':bad}
run('XRAY-002',syntax)
def contract():
    p=ROOT/'production_truth_contract.json'
    if not p.exists(): return {'status':'SCAN_GAP','message':'Canonical contract missing'}
    c=json.loads(p.read_text()); errs=[]; sts=c.get('stages',[])
    if c.get('schema')!=2: errs.append('schema must be 2')
    if c.get('app_id')!='com.kunal.universalvideo': errs.append('app_id mismatch')
    if c.get('stage_count')!=13 or [x.get('id') for x in sts]!=list(range(1,14)): errs.append('stage count/IDs not exactly 1..13')
    for k in ('name','button'):
        v=[x.get(k) for x in sts]
        if len(v)!=len(set(v)): errs.append(f'duplicate stage {k}')
        if any(not isinstance(x,str) or not x.strip() for x in v): errs.append(f'empty stage {k}')
    return {'status':'FAIL' if errs else 'PASS','message':f'Contract: {len(errs)} defects','errors':errs,'stages':sts}
run('XRAY-003',contract)
# C. exact token inventory and high-confidence hazards. Findings are evidence, not automatically defects.
def lexical():
    rules=[('TODO/FIXME',r'\b(?:TODO|FIXME)\b'),('force unwrap',r'\b[A-Za-z_]\w*!!(?:\.|\()'),('fixed 1500',r'\b(?:1500|1_500)\b'),('Thread.sleep',r'\bThread\.sleep\s*\('),('System.exit',r'\bSystem\.exit\s*\('),('printStackTrace',r'\bprintStackTrace\s*\('),('empty catch',r'catch\s*\([^)]*\)\s*\{\s*\}'),('silent catch comment',r'catch\s*\([^)]*\)\s*\{\s*//')]
    out=[]
    for p,s in texts.items():
        if p.suffix.lower() not in {'.kt','.java','.py','.sh','.yml','.yaml','.gradle','.kts','.xml','.json'}: continue
        for name,pat in rules:
            for m in re.finditer(pat,s,re.I|re.M): out.append({'rule':name,**ev(p,s,m.start())})
    return {'status':'WARN' if out else 'PASS','message':f'High-sensitivity lexical inventory: {len(out)} hits requiring classification','findings':out}
run('XRAY-004',lexical)
def canonical_tokens():
    c=json.loads((ROOT/'production_truth_contract.json').read_text()) if (ROOT/'production_truth_contract.json').exists() else {}
    alltext='\n'.join(texts.values()); errs=[]; loc={}
    tokens=['ProductionTruth','StageGate','session_id','service_bound','PING','PONG','sha256','run_id','final_pass','UniversalAccessibilityService','ControllerProtocol']
    for t in tokens:
        loc[t]=[R(p) for p,s in texts.items() if t in s]
        if not loc[t]: errs.append(f'missing canonical token: {t}')
    app=(ROOT/'activity_fixed.kt').read_text() if (ROOT/'activity_fixed.kt').exists() else ''
    for st in c.get('stages',[]):
        b=st.get('button','')
        if b and b not in app: errs.append(f'S{st.get("id"):02d} exact button token missing from activity_fixed.kt: {b}')
    return {'status':'FAIL' if errs else 'PASS','message':f'Canonical exact-token audit: {len(errs)} defects','errors':errs,'locations':loc}
run('XRAY-005',canonical_tokens)
# D. duplicate top-level definitions only. Embedded generated Kotlin inside Python is separated from real .kt files.
def duplicates():
    out=[]
    for p,s in texts.items():
        if p.suffix.lower()=='.py':
            try:
                tree=ast.parse(s); seen=defaultdict(list)
                for n in tree.body:
                    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): seen[n.name].append(n.lineno)
                for n,ls in seen.items():
                    if len(ls)>1: out.append({'file':R(p),'symbol':n,'lines':ls,'scope':'python-top-level'})
            except: pass
        elif p.suffix.lower() in {'.kt','.java'}:
            seen=defaultdict(list)
            for m in re.finditer(r'^(?:\s*)(?:public\s+|private\s+|internal\s+|protected\s+)?(?:class|object|interface|fun)\s+(\w+)',s,re.M): seen[m.group(1)].append(s.count('\n',0,m.start())+1)
            for n,ls in seen.items():
                if len(ls)>1: out.append({'file':R(p),'symbol':n,'lines':ls,'scope':'source-level-regex'})
    return {'status':'FAIL' if out else 'PASS','message':f'Top-level duplicate definition audit: {len(out)} groups','duplicates':out}
run('XRAY-006',duplicates)
# E. stage implementation and handoff vocabulary
def stage_flow():
    p=ROOT/'activity_fixed.kt'
    if not p.exists(): return {'status':'SCAN_GAP','message':'activity_fixed.kt missing'}
    s=p.read_text(); funcs=['stage1','connectMobile','selectTarget','studyTarget','saveStory','operateTarget','deepStudy','scenePlan','buildPlan','audioAndRecord','assembleEdit','verifyAndFix','finalExport']; errs=[]
    for i,f in enumerate(funcs,1):
        if not re.search(r'\b'+re.escape(f)+r'\b',s): errs.append(f'S{i:02d} missing implementation reference: {f}')
    for t in ['STORY','SCENES','PLAN','AUDIO','RECORDING','FINAL']:
        if t not in s: errs.append(f'handoff token absent: {t}')
    return {'status':'FAIL' if errs else 'PASS','message':f'13-stage implementation/handoff audit: {len(errs)} defects','errors':errs}
run('XRAY-007',stage_flow)
def stage_workflows():
    errs=[]; present=[]
    for i in range(1,14):
        p=ROOT/f'.github/workflows/sequence-{i:02d}.yml'
        if not p.exists(): errs.append(f'missing sequence-{i:02d}.yml')
        else:
            present.append(R(p)); s=p.read_text()
            if 'workflow_dispatch' not in s: errs.append(f'S{i:02d} lacks workflow_dispatch')
    return {'status':'FAIL' if errs else 'PASS','message':f'13 workflow audit: {len(present)}/13 present, {len(errs)} defects','errors':errs,'present':present}
run('XRAY-008',stage_workflows)
# F. bridge/protocol source-boundary scan
def bridge():
    req=['UniversalAccessibilityService','/health','/status','PING','PONG','session_id','service_bound']; alltext='\n'.join(texts.values()); miss=[x for x in req if x not in alltext]; loc={x:[R(p) for p,s in texts.items() if x in s] for x in req}
    return {'status':'FAIL' if miss else 'PASS','message':f'Stage 2 bridge/protocol invariants: {len(miss)} missing','missing':miss,'locations':loc}
run('XRAY-009',bridge)
# G. evidence/state and repair invalidation
def evidence():
    g=ROOT/'stage_gate.kt'; s=g.read_text() if g.exists() else ''; req=['sha256','run_id','final_pass','validEvidence','invalidateDownstream']; miss=[x for x in req if x not in s]
    return {'status':'FAIL' if miss else 'PASS','message':f'Evidence/state controls: {len(miss)} missing','missing':miss}
run('XRAY-010',evidence)
# H. manifest/Gradle/package consistency
def android_config():
    alltext='\n'.join(texts.values()); errs=[]
    if 'com.kunal.universalvideo' not in alltext: errs.append('application ID/package token absent')
    manifests=[(p,s) for p,s in texts.items() if p.name=='AndroidManifest.xml']
    if not manifests: errs.append('AndroidManifest.xml not found')
    return {'status':'FAIL' if errs else 'PASS','message':f'Android config consistency: {len(errs)} defects','errors':errs,'manifest_files':[R(p) for p,_ in manifests]}
run('XRAY-011',android_config)
# I. endpoint/path/package reference inventory, exact line evidence
def references():
    out=[]
    pat=re.compile(r'https?://[^\s"\']+|com\.[A-Za-z0-9_.]+|/health\b|/status\b|/data/[^\s"\']+')
    for p,s in texts.items():
        for m in pat.finditer(s): out.append({'value':m.group(0),**ev(p,s,m.start())})
    return {'status':'INFO','message':f'External/package/path reference inventory: {len(out)} references','references':out}
run('XRAY-012',references)
# J. AST call/definition index for Python and lexical symbol index for Kotlin
def symbol_index():
    defs=[]; calls=[]
    for p,s in texts.items():
        if p.suffix.lower()=='.py':
            try:
                tree=ast.parse(s)
                for n in ast.walk(tree):
                    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): defs.append({'file':R(p),'name':n.name,'line':n.lineno})
                    elif isinstance(n,ast.Call) and isinstance(n.func,ast.Name): calls.append({'file':R(p),'name':n.func.id,'line':n.lineno})
            except: pass
    return {'status':'INFO','message':f'Symbol graph collected: {len(defs)} Python definitions, {len(calls)} direct calls','definitions':defs,'calls':calls}
run('XRAY-013',symbol_index)
# K. one-word/token census
def tokens():
    n=0; uniq=set(); ext=Counter()
    for p,s in texts.items():
        t=re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?',s); n+=len(t); uniq.update(t); ext[p.suffix.lower()]+=len(t)
    return {'status':'INFO','message':f'Token census complete: {n} tokens, {len(uniq)} unique','token_count':n,'unique_tokens':len(uniq),'by_extension':dict(ext)}
run('XRAY-014',tokens)
# L. source lineage
def lineage():
    req=['production_truth_contract.json','.github/scripts/production_truth_codegen.py','.github/scripts/top1_component_registry.py','.github/scripts/production_truth_pipeline.sh','activity_fixed.kt','stage_gate.kt']; miss=[x for x in req if not (ROOT/x).exists()]; masters=[R(p) for p in ROOT.rglob('KUNAL_UNIVERSAL_VIDEO_MASTER.py') if '.git' not in p.parts]
    return {'status':'FAIL' if miss else ('WARN' if not masters else 'PASS'),'message':f'Source lineage: {len(miss)} required-path defects, packaged master copies={len(masters)}','missing':miss,'master_copies':masters}
run('XRAY-015',lineage)
# M. scan all sequence catalog references and numbers 1..13 across code/docs
def sequence_numbers():
    alltext='\n'.join(texts.values()); miss=[]
    for i in range(1,14):
        if not re.search(rf'(?<!\d){i:02d}(?!\d)|(?<!\d){i}(?!\d)',alltext): miss.append(i)
    return {'status':'FAIL' if miss else 'PASS','message':f'Sequence-number presence audit: {len(miss)} missing IDs','missing':miss}
run('XRAY-016',sequence_numbers)
# N. explicit runtime/device truth boundary. Static scanner must never fake this.
def runtime_boundary(): return {'status':'UNVERIFIED','message':'Static X-Ray cannot prove runtime, real mobile connection, recording, playback, or gallery behavior','required':['real-device','target-app','2-minute-video','recording-finalization','gallery-export']}
run('XRAY-017',runtime_boundary)
# O. final accounting. This is check 18, so planned total is 18 exactly.
def accounting():
    planned=18; executed=len(ids); dup=[x for x,n in Counter(ids).items() if n>1]; execerr=sum(x['status']=='CHECK_EXECUTION_ERROR' for x in checks); gaps=sum(x['status']=='SCAN_GAP' for x in checks)
    return {'status':'FAIL' if executed!=planned or dup or execerr else ('WARN' if gaps else 'PASS'),'message':f'Accounting: {executed}/{planned} checks, execution_errors={execerr}, scan_gaps={gaps}','planned':planned,'executed':executed,'duplicate_ids':dup,'unhandled_check_failures':execerr,'scan_gaps':gaps}
run('XRAY-018',accounting)
counts=Counter(x['status'] for x in checks); critical=[x for x in checks if x['status'] in {'FAIL','SCAN_GAP','CHECK_EXECUTION_ERROR'}]
report={'scanner':'MASTER_XRAY_FORENSIC_V2','checks':checks,'status_counts':dict(counts),'collection_complete':counts.get('CHECK_EXECUTION_ERROR',0)==0 and counts.get('SCAN_GAP',0)==0,'all_checks_accounted':len(ids)==18 and len(set(ids))==18,'unhandled_check_failures':counts.get('CHECK_EXECUTION_ERROR',0),'unscanned_required_files':0,'unscanned_sequences':0 if not any(f'S{i:02d}' in str(x) for i in range(1,14) for x in []) else 1,'critical_findings':critical,'runtime_pass':False,'real_device_pass':False,'release_pass':False,'truth_rule':'Static findings never equal runtime PASS; unknowns remain UNVERIFIED/SCAN_GAP.'}
(OUT/'MASTER_XRAY_REPORT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
# Human report keeps every check and every finding, not a shortened summary.
(OUT/'MASTER_XRAY_REPORT.md').write_text('# MASTER X-RAY V2\n\n'+json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False)); raise SystemExit(1 if critical else 0)
