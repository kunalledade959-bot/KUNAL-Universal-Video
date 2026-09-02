#!/usr/bin/env python3
from pathlib import Path
import re, json, hashlib, zipfile, sys
from collections import Counter

ROOT=Path.cwd(); OUT=ROOT/'TOP1_EXHAUSTIVE_13_STAGE_AUDIT.md'; JSONOUT=ROOT/'TOP1_EXHAUSTIVE_13_STAGE_AUDIT.json'; WORK=ROOT/'.top1-audit'
WORK.mkdir(exist_ok=True)
findings=[]; inspected=[]

def add(stage,severity,weakness,replacement,evidence,scope='SOURCE'):
    findings.append({'stage':stage,'severity':severity,'weakness':weakness,'top1_replacement':replacement,'evidence':evidence,'scope':scope})

def read(p):
    try:return p.read_text(encoding='utf-8',errors='replace')
    except:return ''

def all_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '.top1-audit' not in p.parts)

files=all_files()
for p in files:
    inspected.append(str(p.relative_to(ROOT)))

# Materialize packaged Android source if repository does not contain it.
archives=[ROOT/'KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip',ROOT/'KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT.zip']
for z in archives:
    if z.is_file():
        try:
            d=WORK/(z.stem+'-expanded'); d.mkdir(exist_ok=True)
            with zipfile.ZipFile(z) as zz: zz.extractall(d)
        except Exception as e:
            add(0,'CRITICAL','Packaged Android archive cannot be inspected','Repair archive integrity/extraction path before certification',f'{z.name}: {e}','PACKAGE')

# Combine source from root plus extracted package for inspection, de-duplicated by path/content hash.
scan_files=[]; seen=set()
for p in all_files()+list(WORK.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in {'.kt','.java','.xml','.py','.sh','.yml','.yaml','.gradle','.kts','.json','.properties','.md','.txt'}: continue
    try: h=hashlib.sha256(p.read_bytes()).hexdigest()
    except: continue
    if h in seen: continue
    seen.add(h); scan_files.append(p)

# Stage implementations are discovered in MainActivity wherever present.
activity_text='\n'.join(read(p) for p in scan_files if p.name=='activity_fixed.kt' or p.name=='MainActivity.kt')

def body(name):
    m=re.search(r'(?:private|public|internal)?\\s*fun\\s+'+re.escape(name)+r'\\s*\\([^)]*\\)\\s*(?::[^\\{]+)?\\{',activity_text)
    if not m:return ''
    i=m.end()-1; depth=0
    for j in range(i,len(activity_text)):
        if activity_text[j]=='{':depth+=1
        elif activity_text[j]=='}':
            depth-=1
            if depth==0:return activity_text[i+1:j]
    return ''

stage_specs={
1:('stage1','Startup/self-diagnostic','device/app health checks, deterministic startup recovery, persisted evidence'),
2:('connectMobile','Mobile connection/permissions','real bound controller session, authenticated/validated handshake, lifecycle and timeout recovery'),
3:('selectTarget','Target APK selection','installed + launchable + persistent selection + controller binding + identity proof'),
4:('studyTarget','Study selected APK','package metadata, activities/services/permissions and launchability evidence'),
5:('saveStory','Story input','durable write + read-back/hash + validation, no silent loss'),
6:('operateTarget','Operate selected target','non-blocking lifecycle-safe actions, bounded waits, real foreground/tree proof'),
7:('deepStudy','Deep target understanding','bounded structured accessibility snapshot with stable identifiers and limits'),
8:('scenePlan','Exact scene plan','lossless story segmentation, explicit scene fields, ordering and completeness'),
9:('buildPlan','Production plan/prompts','scene-specific prompts derived from all scene fields, no placeholders'),
10:('audioAndRecord','Audio/voice/music/SFX','provider abstraction, output quality/format validation, recording state machine and cancellation recovery'),
11:('assembleEdit','Assemble/edit','decoder/encoder compatible media pipeline, explicit track/format validation and guaranteed cleanup'),
12:('verifyAndFix','Verify/auto-fix','decode/playability, duration, streams, sync, integrity/hash and bounded repair loop'),
13:('finalExport','Final Gallery export','atomic MediaStore export, metadata, pending-row cleanup, read-back/discoverability verification')}

# Direct stage weaknesses and strongest replacement class.
for n,(fn,label,ideal) in stage_specs.items():
    b=body(fn)
    if not b:
        add(n,'CRITICAL',f'{fn} implementation not found','Replace with a dedicated StageController implementing '+ideal,'No matching function in current Activity sources')
        continue
    checks={
      1:[('getInstalledApplications','Startup does not verify the broader runtime environment','Startup Health Controller with explicit prerequisite probes and persisted diagnostic bundle'),('gate.begin','Stage gate is not necessarily entered before every startup transition','Single transactional StageRunner that owns begin/pass/fail')],
      2:[('127.0.0.1','Loopback transport alone does not prove a trusted real-device session','Authenticated session protocol with nonce/session binding, bounded request sizes, timeouts and lifecycle heartbeat'),('connect(','Connection must be stateful and independently health-checked','ConnectionStateMachine with CONNECTING/CONNECTED/DEGRADED/DISCONNECTED and watchdog')],
      3:[('getApplicationInfo','Selection proof is shallow','TargetIdentity object containing package/version/UID/launch component plus read-back persistence hash'),('getLaunchIntentForPackage','Launchability alone is insufficient target identity proof','ResolveInfo/component-level launch verification plus controller target handshake')],
      4:[('getApplicationInfo','APK study is only package-level','PackageInspector collecting package metadata, activities, services, permissions, exported components and version signature'),('getLaunchIntentForPackage','Study lacks runtime/UI behavior evidence','Controlled launch + bounded observation + structured study report')],
      5:[('.apply()','Critical story persistence is asynchronous and unverified','Atomic durable store with commit/read-back/hash before PASS'),('length<10','Minimum length is not semantic validation','StoryValidator with UTF-8 length, empty-section, normalization and deterministic hash')],
      6:[('Thread.sleep','Potential UI-thread blocking','Coroutine/Handler state machine with cancellable deadline and lifecycle owner'),('postDelayed','Delayed polling needs cancellation/lifecycle ownership','Lifecycle-aware foreground observer with timeout and cancellation token')],
      7:[('childCount','Unbounded tree traversal can exhaust time/memory','Bounded iterative tree walker with max nodes/depth/time and cycle-safe identity tracking'),('target_ui_map','Flat text map is not reproducible enough','Versioned JSON accessibility snapshot containing node path, class, bounds, text hash, actions and identifiers')],
      8:[('take(30)','Silent data loss for long stories','Lossless scene parser with explicit scene IDs and completeness assertion: input hash -> all text represented exactly once'),('BACKGROUND=scene-specific','Placeholder scene fields are not exact','Deterministic scene schema populated from story + target observations + production constraints')],
      9:[('VISUAL_PROMPT=','Generic placeholder prompts weaken production specificity','PromptCompiler that consumes every scene field and emits validated scene-specific visual/action/audio constraints'),('filter{it.startsWith("SCENE_")','Only scene headers may survive into production plan','Structured Scene objects serialized to versioned JSON, never parsed back from display strings')],
      10:[('TextToSpeech','System TTS is not a human-quality/provider-verified voice pipeline','VoiceProvider interface with provider metadata, format validation, quality gates and deterministic fallback'),('capture.launch','Permission callback alone does not prove recording started','RecordingStateMachine requiring recorder/service started + bytes/duration evidence before PASS'),('1500','Fixed sleep is not reliable completion proof','Completion future/callback with bounded timeout and actual MediaStore row validation')],
      11:[('MediaExtractor','WAV/container compatibility is not guaranteed by extension','Canonical intermediate audio container/codec selected by MediaCodec capability probing or compatible encoded source'),('MediaMuxer','Muxing must validate compatible tracks and guaranteed cleanup','MediaPipeline with format negotiation, try/finally resource ownership and post-mux decode probe')],
      12:[('trackCount','Track count does not prove playable media','Independent media verifier that decodes video/audio samples, checks duration, dimensions, timestamps, sync, EOF and corruption'),('MediaExtractor','Extractor metadata alone is insufficient','Decoder-backed verification + cryptographic integrity + bounded auto-fix loop with before/after evidence')],
      13:[('IS_PENDING','Pending MediaStore rows can remain after failure','Transactional export helper with delete-on-failure, metadata verification, read-back and visibility probe'),('openOutputStream','Writing bytes is not proof of Gallery discoverability','Insert -> copy -> fsync/close -> query metadata -> reopen/read sample -> clear pending -> re-query verification')]
    }
    for needle,w,repl in checks.get(n,[]):
        if needle in b or (n in (5,7,8,9,10,11,12,13) and needle in activity_text):
            add(n,'HIGH',w,repl,f'Observed implementation contains: {needle}')

# Global cross-cutting weaknesses, inspected across every text source.
alltext='\n'.join(read(p) for p in scan_files)
if '.apply()' in alltext:
    add(0,'HIGH','Asynchronous SharedPreferences writes appear in critical paths','Transactional repository abstraction with commit/read-back/hash for critical state','Found SharedPreferences.apply() in inspected source')
if 'catch (_: Exception)' in alltext or 'catch(Exception' in alltext:
    add(0,'MEDIUM','Broad exception swallowing can hide root causes','Typed error model with structured error codes and preserved cause/stack evidence','Broad catch patterns found in source','CROSS_CUTTING')
if 'TODO' in alltext or 'FIXME' in alltext:
    add(0,'MEDIUM','TODO/FIXME markers may indicate incomplete implementation','Zero-tolerance release gate that fails on unresolved TODO/FIXME in production paths','Marker detected','CROSS_CUTTING')
if 'sleep(' in alltext:
    add(0,'HIGH','Sleep-based synchronization exists in the project','Event-driven/lifecycle-aware synchronization with explicit deadlines','sleep(...) found','CROSS_CUTTING')
if 'take(30)' in alltext:
    add(0,'HIGH','Hard-coded truncation can discard user content','Lossless processing with completeness/hash assertion','take(30) found','CROSS_CUTTING')
if 'VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character' in alltext or 'ACTION_PROMPT=execute_scene_action' in alltext:
    add(0,'HIGH','Generic placeholder prompts exist in production planning','Schema-first PromptCompiler with per-scene semantic inputs and no placeholder release gate','Generic prompt literals detected','CROSS_CUTTING')

# Every stage must have explicit evidence, timeout/recovery, persistence, and a verifier.
for n,(fn,label,ideal) in stage_specs.items():
    b=body(fn)
    if b:
        if 'pass('+str(n) not in b and f'gate.pass({n}' not in b:
            add(n,'HIGH','No explicit stage PASS transition in local implementation','StageRunner transaction requiring verified evidence before PASS',f'{fn} body has no obvious pass({n})')
        if 'fail('+str(n) not in b and f'gate.fail({n}' not in b:
            add(n,'HIGH','No explicit stage FAIL transition in local implementation','StageRunner with mandatory failure outcome and durable reason',f'{fn} body has no obvious fail({n})')

# Rank exactly one top replacement per stage: highest-severity finding, then most architectural.
sev={'CRITICAL':3,'HIGH':2,'MEDIUM':1,'INFO':0}
top={}
for f in findings:
    if f['stage'] in range(1,14):
        old=top.get(f['stage'])
        if old is None or sev[f['severity']]>sev[old['severity']]: top[f['stage']]=f

# Generate report.
counts=Counter(f['severity'] for f in findings)
md=['# TOP-1 EXHAUSTIVE 13-STAGE AUDIT','',f'Generated from repository commit: {__import__("os").environ.get("GITHUB_SHA","unknown")}','',f'Files inspected: {len(inspected)} (plus de-duplicated packaged-source text files: {len(scan_files)})','', '## Rule','This run is AUDIT-ONLY. It makes no product-code repair and never converts static evidence into a runtime/physical-device PASS. Every finding is paired with exactly one strongest replacement architecture.', '', '## One best replacement per stage']
for n in range(1,14):
    f=top.get(n)
    if not f:
        md.append(f'### Stage {n} - {stage_specs[n][1]}\n- **No finding generated by current static rules.** This is not a runtime PASS.\n')
    else:
        md.append(f'### Stage {n} - {stage_specs[n][1]}\n- Severity: **{f["severity"]}**\n- Weakness: {f["weakness"]}\n- **TOP 1 replacement:** {f["top1_replacement"]}\n- Evidence: `{f["evidence"]}`\n')
md += ['## Cross-cutting findings']
for f in findings:
    if f['stage']==0: md.append(f'- **{f["severity"]}** {f["weakness"]} -> **{f["top1_replacement"]}** ({f["evidence"]})')
md += ['', '## All findings']
for f in findings: md.append(f'- Stage {f["stage"]} | {f["severity"]} | {f["weakness"]} | TOP1={f["top1_replacement"]} | {f["evidence"]}')
md += ['', '## Verdict', f'- Findings: {len(findings)}', f'- Severity counts: {dict(counts)}', '- **VERDICT: REPAIR_REQUIRED**' if any(f['severity'] in ('CRITICAL','HIGH') for f in findings) else '- **VERDICT: STATIC_REVIEW_NO_HIGH_FINDING**', '- Physical device proof: NOT PROVIDED by this audit.']
OUT.write_text('\n'.join(md)+'\n',encoding='utf-8')
JSONOUT.write_text(json.dumps({'schema':'KUV-TOP1-EXHAUSTIVE-v1','files_inspected':inspected,'scan_file_count':len(scan_files),'findings':findings,'top1_by_stage':top,'counts':dict(counts),'verdict':'REPAIR_REQUIRED' if any(f['severity'] in ('CRITICAL','HIGH') for f in findings) else 'STATIC_REVIEW_NO_HIGH_FINDING','physical_device_proof':False},indent=2,ensure_ascii=False),encoding='utf-8')
print(f'AUDIT_COMPLETE findings={len(findings)} files={len(scan_files)}')
for n in range(1,14):
    f=top.get(n)
    print(f'STAGE_{n}_TOP1={f["severity"] if f else "NONE"}|{f["top1_replacement"] if f else "NO_STATIC_FINDING"}')
print('VERDICT=REPAIR_REQUIRED' if any(f['severity'] in ('CRITICAL','HIGH') for f in findings) else 'VERDICT=STATIC_REVIEW_NO_HIGH_FINDING')
# Deliberately exit 0: audit collection must complete even when findings exist.
sys.exit(0)
