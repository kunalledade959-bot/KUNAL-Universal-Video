#!/usr/bin/env python3
"""KUNAL Universal Video - exhaustive, non-crashing diagnostic cell.

This cell is DISCOVERY ONLY. It never repairs source code. Every stage is isolated:
a failing command, parser, timeout, or missing environment is recorded and the
next reachable stage continues. Runtime failures are captured from logcat.
"""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, sys, time, traceback

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"COMPLETE_ERROR_DISCOVERY"
OUT.mkdir(exist_ok=True)
REPORT=OUT/"MASTER_ERROR_REPORT.json"
TEXT=OUT/"MASTER_ERROR_REPORT.txt"
ERRORS=[]; STAGES=[]

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name, text):
    p=OUT/name; p.write_text(str(text),encoding="utf-8",errors="replace"); return str(p)
def record(stage,status,detail="",evidence="",**extra):
    item={"stage":stage,"status":status,"detail":str(detail),"evidence":evidence,"time":stamp(),**extra}
    STAGES.append(item)
    if status in {"FAIL","ERROR","BLOCKED"}:
        ERRORS.append(item)
    print(f"[{status}] {stage}: {detail}",flush=True)

def run_cmd(stage,cmd,timeout=300,env=None):
    try:
        r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace",timeout=timeout)
        out=r.stdout
        ev=save(re.sub(r"[^A-Za-z0-9_.-]","_",stage)+".log",out)
        record(stage,"PASS" if r.returncode==0 else "FAIL",f"returncode={r.returncode}",ev,command=cmd,returncode=r.returncode)
        return r.returncode,out
    except subprocess.TimeoutExpired as e:
        out=(e.stdout or "")+("\n[TIMEOUT]\n")+(e.stderr or "")
        ev=save(re.sub(r"[^A-Za-z0-9_.-]","_",stage)+"_TIMEOUT.log",out)
        record(stage,"FAIL","timeout",ev,command=cmd)
        return 124,out
    except Exception as e:
        ev=save(re.sub(r"[^A-Za-z0-9_.-]","_",stage)+"_EXCEPTION.log",traceback.format_exc())
        record(stage,"ERROR",repr(e),ev,command=cmd)
        return 999,""

def capture_error_signatures(text,source):
    patterns=[r"FATAL EXCEPTION[^\n]*",r"AndroidRuntime[^\n]*",r"Unable to start activity[^\n]*",r"Process: [^\n]*",r"ANR in [^\n]*",r"Caused by: [^\n]*",r"Exception[^\n]*",r"Error[^\n]*"]
    found=[]
    for pat in patterns:
        found += re.findall(pat,text,re.I)
    if found:
        p=save(source+"_SIGNATURES.txt","\n".join(dict.fromkeys(found)))
        record(source+" exact runtime signatures","FAIL",f"captured {len(dict.fromkeys(found))} signatures",p)
    else: record(source+" exact runtime signatures","PASS","no matching crash signatures in captured log")

# 1 Startup / self diagnostic
record("1. APK Startup / Self-Diagnostic","PASS","diagnostic engine started; no repair performed")

# 2 environment / permissions / mobile connection evidence
run_cmd("2. Environment and device connection",["bash","-lc","(command -v adb || true); (adb devices -l || true); (adb shell getprop ro.product.model || true); (adb shell getprop ro.build.version.release || true)"],120)

# 3 target APK selection evidence
apk_candidates=list(ROOT.rglob("*.apk"))
if apk_candidates:
    record("3. Target APK Selection","PASS",f"found {len(apk_candidates)} APK candidate(s)",save("apk_candidates.txt","\n".join(map(str,apk_candidates))))
else: record("3. Target APK Selection","BLOCKED","no APK candidate available in workspace")

# 4 study selected APK
if apk_candidates:
    a=apk_candidates[-1]
    try:
        record("4. Study Selected APK","PASS",f"selected {a.name}",save("selected_apk_sha256.txt",hashlib.sha256(a.read_bytes()).hexdigest()))
    except Exception as e: record("4. Study Selected APK","ERROR",repr(e),save("study_exception.txt",traceback.format_exc()))
else: record("4. Study Selected APK","BLOCKED","depends on stage 3",)

# 5 story input/static input inventory
try:
    names=[p.name for p in ROOT.iterdir()]
    record("5. Story Input","PASS","workspace inventory captured",save("workspace_inventory.txt","\n".join(sorted(names))))
except Exception as e: record("5. Story Input","ERROR",repr(e),save("story_exception.txt",traceback.format_exc()))

# 6 production-plan/prompts/audio inventory
try:
    matches=[]
    for pat in ("*story*","*prompt*","*audio*","*production*","*plan*"):
        matches.extend(ROOT.rglob(pat))
    record("6. Story → Production Plan / Prompts / Audio","PASS",f"inventory captured: {len(set(matches))} matching paths",save("production_inventory.txt","\n".join(map(str,sorted(set(matches))))))
except Exception as e: record("6. Story → Production Plan / Prompts / Audio","ERROR",repr(e),save("production_exception.txt",traceback.format_exc()))

# 7 deep target-app understanding / manifest/resource static evidence
try:
    candidates=[p for p in ROOT.rglob("AndroidManifest.xml")]
    text="\n\n".join(f"=== {p} ===\n{p.read_text(encoding='utf-8',errors='replace')}" for p in candidates)
    record("7. Deep Target-App Understanding","PASS",f"captured {len(candidates)} manifest(s)",save("manifests.txt",text))
except Exception as e: record("7. Deep Target-App Understanding","ERROR",repr(e),save("target_understanding_exception.txt",traceback.format_exc()))

# 8 exact scene plan inventory
try:
    scene=[]
    for p in ROOT.rglob("*"):
        if p.is_file() and any(k in p.name.lower() for k in ("scene","timeline","story","sequence")):
            scene.append(str(p))
    record("8. Exact Scene Plan","PASS",f"captured {len(scene)} candidate files",save("scene_candidates.txt","\n".join(scene)))
except Exception as e: record("8. Exact Scene Plan","ERROR",repr(e),save("scene_exception.txt",traceback.format_exc()))

# 9 operate selected target APK: install + launch + FULL logcat, never stop the diagnostic cell
if apk_candidates:
    a=apk_candidates[-1]
    rc,_=run_cmd("9a. Install selected APK",["adb","install","-r",str(a)],180)
    if rc==0:
        run_cmd("9b. Clear app data",["adb","shell","pm","clear","com.kunal.universalvideo"],60)
        run_cmd("9c. Clear logcat",["adb","logcat","-c"],30)
        run_cmd("9d. Launch MainActivity",["adb","shell","am","start","-W","-n","com.kunal.universalvideo/.MainActivity"],120)
        time.sleep(3)
        _,log=run_cmd("9e. Full launch logcat",["adb","logcat","-d","-v","threadtime"],120)
        capture_error_signatures(log,"9e launch")
        run_cmd("9f. Process state after launch",["adb","shell","pidof","com.kunal.universalvideo"],30)
    else: record("9. Operate Selected Target APK","BLOCKED","install failed; launch skipped but diagnostic continues")
else: record("9. Operate Selected Target APK","BLOCKED","no APK to install")

# 10 assemble/edit static and build evidence (build is a probe, not a repair)
gradlew=ROOT/"KUNAL_UNIVERSAL_VIDEO/android-controller/gradlew"
if gradlew.exists():
    run_cmd("10. Assemble / Edit - clean build probe",[str(gradlew),"clean","assembleDebug","--stacktrace","--info"],1800)
else: record("10. Assemble / Edit","BLOCKED","gradlew not found at expected project path")

# 11 verify/auto-fix status: discovery only; collect existing logs, DO NOT mutate source
try:
    logs=[]
    for p in ROOT.rglob("*.log"):
        logs.append(str(p))
    for p in ROOT.rglob("*.json"):
        if "report" in p.name.lower() or "error" in p.name.lower(): logs.append(str(p))
    record("11. Verify / Auto-Fix","PASS","discovery-only mode: existing evidence inventory captured; no source mutation",save("verification_evidence_inventory.txt","\n".join(sorted(set(logs)))))
except Exception as e: record("11. Verify / Auto-Fix","ERROR",repr(e),save("verify_exception.txt",traceback.format_exc()))

# 12 final gallery export evidence inventory
try:
    media=[]
    for ext in ("*.mp4","*.mov","*.mkv","*.webm"):
        media.extend(ROOT.rglob(ext))
    record("12. Final Gallery Export","PASS",f"captured {len(media)} media artifact candidate(s)",save("gallery_media_candidates.txt","\n".join(map(str,media))))
except Exception as e: record("12. Final Gallery Export","ERROR",repr(e),save("gallery_exception.txt",traceback.format_exc()))

report={"generated_at":stamp(),"mode":"DISCOVERY_ONLY_NON_CRASHING","stages":STAGES,"errors":ERRORS,"error_count":len(ERRORS)}
REPORT.write_text(json.dumps(report,indent=2),encoding="utf-8")
lines=["KUNAL UNIVERSAL VIDEO - COMPLETE ERROR DISCOVERY",f"Generated: {report['generated_at']}",f"Recorded failures/errors: {len(ERRORS)}","", "STAGE RESULTS"]
for x in STAGES: lines.append(f"[{x['status']}] {x['stage']} :: {x['detail']} :: {x.get('evidence','')}")
lines += ["","CONFIRMED FAILURE/ERROR RECORDS"]
for i,x in enumerate(ERRORS,1): lines.append(f"ERROR #{i}: {x['stage']} :: {x['detail']} :: {x.get('evidence','')}")
TEXT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"DISCOVERY COMPLETE: {REPORT}",flush=True)
print(f"Recorded failures/errors: {len(ERRORS)}",flush=True)
