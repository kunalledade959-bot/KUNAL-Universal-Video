#!/usr/bin/env python3
"""Adversarial audit of the production 13-stage controller.

This is intentionally a discovery gate, not a fake runtime PASS. It inventories
reachable failure conditions, prerequisite ordering, persistence, lifecycle,
external-service boundaries, and places where a stage can become RUNNING without
an observable completion/timeout. Physical-device-only behavior is marked
PHYSICAL_ONLY rather than guessed.
"""
from pathlib import Path
import re, json, sys

SRC=Path('activity_fixed.kt')
OUT=Path('13-stage-adversarial-audit.json')
if not SRC.is_file():
    print('SOURCE_MISSING'); sys.exit(2)
s=SRC.read_text(encoding='utf-8')

stages={
1:('stage1',['PackageManager','loadApps','gate.begin(1)']),
2:('connectMobile',['isEnabled','bridge?.connect','openAccessibility','targetPackage']),
3:('selectTarget',['selectedItemPosition','putString(TARGET','targetPackage']),
4:('studyTarget',['getApplicationInfo','getLaunchIntentForPackage']),
5:('saveStory',['story.text','putString(STORY','length<10']),
6:('operateTarget',['startActivity','targetForeground','rootInActiveWindow']),
7:('deepStudy',['rootInActiveWindow','clickable','editable','putString("target_ui_map"']),
8:('scenePlan',['putString(SCENES','split','take(30)']),
9:('buildPlan',['putString(PLAN','SCENE_','VISUAL_PROMPT']),
10:('audioAndRecord',['synthesizeToFile','createScreenCaptureIntent','MediaProjection','MediaStore']),
11:('assembleEdit',['MediaExtractor','MediaMuxer','copyTrack','putString(FINAL']),
12:('verifyAndFix',['MediaExtractor','trackCount','FINAL']),
13:('finalExport',['MediaStore','IS_PENDING','openOutputStream','putString("$FINAL'])
}

# Extract each function body by balanced braces. This avoids brittle text matching
# and lets the report point to the exact implementation currently in the repo.
def function_body(name):
    m=re.search(r'private fun '+re.escape(name)+r'\([^)]*\)\s*(?::[^\{]+)?\{',s)
    if not m:return ''
    i=m.end()-1; depth=0
    for j in range(i,len(s)):
        if s[j]=='{': depth+=1
        elif s[j]=='}':
            depth-=1
            if depth==0:return s[i+1:j]
    return ''

issues=[]
results=[]

def add(stage,severity,kind,title,evidence,physical=False):
    results.append({'stage':stage,'severity':severity,'kind':kind,'title':title,'evidence':evidence,'verification':'PHYSICAL_ONLY' if physical else 'STATIC_REVIEW'})

# Stage-local inventory
for n,(fn,needles) in stages.items():
    body=function_body(fn)
    if not body:
        add(n,'CRITICAL','MISSING_IMPLEMENTATION',f'{fn} implementation missing','function not found')
        continue
    for needle in needles:
        if needle not in body:
            add(n,'HIGH','EXPECTED_CONTRACT_MISSING',f'Missing expected contract: {needle}',f'{fn} does not contain {needle}')

# Explicit branch/failure inventory. Every fail() becomes a named scenario.
for m in re.finditer(r'fail\((\d+),\s*"([^"]+)',s):
    add(int(m.group(1)),'INFO','EXPLICIT_FAILURE_PATH','Explicit failure path',m.group(2))

# Cross-stage prerequisite/order adversarial checks.
# The UI exposes stage 2 before stage 3, but connectMobile uses target before
# selectTarget establishes it. This is a real ordering hazard, not a test failure.
b2=function_body('connectMobile')
b3=function_body('selectTarget')
if 'targetPackage=target' in b2 and 'target=' not in b2:
    add(2,'CRITICAL','ORDERING_HAZARD','Stage 2 uses target before Stage 3 selects it','connectMobile assigns targetPackage from target; target is assigned in selectTarget (stage 3)')
if 'bridge?.connect(target)' in b2:
    add(2,'HIGH','EMPTY_TARGET_HAZARD','Handshake may be attempted with empty target','bridge?.connect(target) occurs before stage 3 target selection')

# Stage 10 can remain RUNNING if the user cancels/never completes projection;
# there is no explicit timeout in the Activity controller.
b10=function_body('audioAndRecord')
if 'capture.launch' in b10 and 'timeout' not in b10.lower():
    add(10,'HIGH','HANG_RISK','Screen-capture permission has no explicit timeout/cancellation recovery','capture.launch(createScreenCaptureIntent()) with callback-only completion')
# The callback starts recording, but the controller does not prove the recording
# has actually started before reporting RUNNING.
if 'status.text="Stage 10 RUNNING' in s:
    add(10,'HIGH','PREMATURE_SUCCESS','Stage 10 reports RUNNING immediately after starting service','status updated after startForegroundService; actual capture is verified only later')

# Stage 11 media compatibility and resource lifecycle hazards.
b11=function_body('assembleEdit')
if 'FileInputStream(audio)' in b11 and 'MediaExtractor' in b11:
    add(11,'HIGH','MEDIA_CONTAINER_RISK','Audio is synthesized as WAV but passed through MediaExtractor','audio output is narration_*.wav; mux path uses MediaExtractor on that file')
if 'mux.stop();mux.release()' in b11 and 'finally' not in b11:
    add(11,'MEDIUM','RESOURCE_CLEANUP_RISK','MediaMuxer/Extractor resources are not protected by finally on all exceptions','muxVideoAudio performs manual cleanup only on selected error branches')

# Stage 13 partial-write risk: if copy fails, inserted pending item may remain.
b13=function_body('finalExport')
if 'IS_PENDING' in b13 and 'catch' in b13:
    add(13,'HIGH','PARTIAL_EXPORT_RISK','Gallery export failure can leave a pending MediaStore row','IS_PENDING is cleared only after successful copy; catch does not explicitly delete/reset the row')

# Persistence integrity: SharedPreferences.apply() is asynchronous.
if '.apply()' in s:
    add(0,'MEDIUM','PERSISTENCE_RACE','Critical evidence uses asynchronous SharedPreferences.apply()','stage state/data can be persisted asynchronously before immediate dependent work')

# Lifecycle / threading hazard: stage 6 blocks the UI thread while polling.
b6=function_body('operateTarget')
if 'Thread.sleep(150)' in b6:
    add(6,'HIGH','UI_THREAD_BLOCK','Accessibility foreground wait blocks Activity main thread','Thread.sleep is executed directly inside operateTarget')

# Accessibility tree recursion can hit very deep/large trees without a node cap.
for n,fn in [(6,'operateTarget'),(7,'deepStudy')]:
    b=function_body(fn)
    if 'childCount' in b and 'for(' in b:
        add(n,'MEDIUM','TREE_SIZE_RISK','Accessibility tree traversal has no depth/node safety cap','recursive traversal follows all child nodes')

# Stage 8 truncates a story at 30 sentence chunks, silently discarding the rest.
b8=function_body('scenePlan')
if 'take(30)' in b8:
    add(8,'HIGH','DATA_LOSS','Scene planning silently truncates stories after 30 chunks','filter(...).take(30)')

# Stage 9 depends on scenes but only emits one prompt line per scene header.
b9=function_body('buildPlan')
if 'filter{it.startsWith("SCENE_")}' in b9:
    add(9,'MEDIUM','PLAN_LOSS','Production plan retains only SCENE header lines and discards scene action/background fields','buildPlan filters scene text to SCENE_ lines')

# Stage 12 verifies track count only, not duration, decodability, synchronization,
# playable video stream, or actual gallery-readable output.
b12=function_body('verifyAndFix')
for term,title in [('trackCount','only checks track count'),('duration','does not verify duration'),('sample','does not decode media samples')]:
    if term not in b12:
        add(12,'HIGH','WEAK_VERIFICATION',title,'Stage 12 lacks '+term+' validation')

# Physical-only boundary. Do not claim this can be proven in hosted CI.
add(2,'CRITICAL','PHYSICAL_ONLY','Real physical Accessibility service/device transport cannot be proven by hosted emulator','Requires the actual Android device, enabled service, OEM settings, and live transport',True)
add(10,'CRITICAL','PHYSICAL_ONLY','Real microphone/screen-capture/OEM behavior cannot be proven on hosted emulator alone','Requires physical Android capture behavior',True)
add(13,'HIGH','PHYSICAL_ONLY','Actual user Gallery visibility on the target phone requires physical-device verification','Hosted emulator is not the user device',True)

# Summarize all functions and every explicit fail path.
report={
 'schema':'KUV-13-STAGE-ADVERSARIAL-AUDIT-v1',
 'source_sha_hint':'current main activity_fixed.kt',
 'stage_count':13,
 'stage_functions':{str(k):v[0] for k,v in stages.items()},
 'findings':results,
 'counts':{},
 'verdict':'FAIL_REVIEW_REQUIRED' if any(x['severity'] in ('CRITICAL','HIGH') for x in results) else 'PASS_STATIC_ONLY',
 'physical_device_proof':False,
 'note':'This report deliberately distinguishes static/runtime-harness findings from physical-device-only proof. It must never be used as a claim that the phone is verified.'
}
from collections import Counter
report['counts']=dict(Counter(x['severity'] for x in results))
OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('AUDIT_RESULT='+report['verdict'])
print('FINDINGS='+str(len(results)))
for x in results:
    if x['severity'] in ('CRITICAL','HIGH'):
        print(f"{x['severity']}|STAGE {x['stage']}|{x['kind']}|{x['title']}")
sys.exit(1 if report['verdict']=='FAIL_REVIEW_REQUIRED' else 0)
