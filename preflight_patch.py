from pathlib import Path
import shutil
import re
p=Path('pro_repair_v3.py')
s=p.read_text(encoding='utf-8')
s=s.replace('["UUID.randomUUID","bridge?.connect","sessionId"]','["UUID.randomUUID","bridge?.connect","sid"]')
s=s.replace('for p in [Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:', 'for p in [Path(shutil.which("gradle")) if shutil.which("gradle") else Path("/nonexistent"),Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:')
s=s.replace('if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}', 'if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}; log(f"[BUILD_ENV] sdk={S} gradle={G} java={J}")')
s=s.replace('if static_ok:build_ok,bi=build()', 'if static_ok:build_ok,bi=build(); log("BUILD_RESULT="+json.dumps(bi,indent=2)); log("BUILD_ERRORS="+"\\n".join([x for x in BUILD_LOG.read_text(encoding="utf-8",errors="replace").splitlines() if re.search(r"(^e:|error:|Unresolved reference|Type mismatch|Cannot access|Overload resolution)",x,re.I)]) if BUILD_LOG.exists() else "BUILD_LOG_MISSING")')

# Patch the production UI source before pro_repair_v3.py copies activity_fixed.kt into the build.
# The previous layout gave the story editor weight=1, leaving the lower stage buttons outside
# the viewport. Keep all 13 controls in a ScrollView so the real UI hierarchy exposes them.
activity=Path('activity_fixed.kt')
if activity.is_file():
    a=activity.read_text(encoding='utf-8')
    old_story='root.addView(story,LinearLayout.LayoutParams(-1,0,1f))'
    new_story='root.addView(story,LinearLayout.LayoutParams(-1,180))'
    if old_story not in a:
        raise SystemExit('UI FIX: story layout target not found')
    a=a.replace(old_story,new_story,1)
    old_end='button("REFRESH STATUS"){renderStatus()};root.addView(actions);setContentView(root)'
    new_end='button("REFRESH STATUS"){renderStatus()};val scroll=ScrollView(this);scroll.isFillViewport=true;scroll.addView(actions);root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f));setContentView(root)'
    if old_end not in a:
        raise SystemExit('UI FIX: actions layout target not found')
    a=a.replace(old_end,new_end,1)

    # Stage order repair: Stage 2 owns mobile/accessibility readiness; Stage 3 owns target selection.
    # The old Stage 2 required a target before Stage 3 could run, making a clean first-run path impossible.
    old_order='''        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}\n        if(target.isBlank())target=prefs().getString(TARGET,"")?:""\n        if(target.isBlank()){fail(2,"Target APK must be selected");return}\n        UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)\n        pass(2,"Accessibility enabled and local controller session connected")'''
    new_order='''        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}\n        pass(2,"Accessibility enabled and local controller session ready")'''
    if old_order not in a:
        raise SystemExit('STAGE ORDER FIX: Stage 2 target dependency not found')
    a=a.replace(old_order,new_order,1)
    old_stage3='''        target=apps[pos].packageName;prefs().edit().putString(TARGET,target).apply();UniversalAccessibilityService.targetPackage=target\n        pass(3,"Target package selected: $target")'''
    new_stage3='''        target=apps[pos].packageName;prefs().edit().putString(TARGET,target).apply();UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)\n        pass(3,"Target package selected and local controller session connected: $target")'''
    if old_stage3 not in a:
        raise SystemExit('STAGE ORDER FIX: Stage 3 target connection point not found')
    a=a.replace(old_stage3,new_stage3,1)

    # Stage 10 completion repair: START is not PASS. The recording service finalizes asynchronously
    # after STOP, so poll for the real MediaStore recording and only then close Stage 10.
    old_record='''    private fun audioAndRecord(){\n        if(!begin(10))return\n        val text=prefs().getString(STORY,"")?:"";if(text.isBlank()){fail(10,"Story missing for narration");return}\n        val out=File(cacheDir,"narration_${sid}.wav");try{'''
    new_record='''    private fun audioAndRecord(){\n        if(!begin(10))return\n        prefs().edit().remove(RECORDING).apply()\n        val text=prefs().getString(STORY,"")?:"";if(text.isBlank()){fail(10,"Story missing for narration");return}\n        val out=File(cacheDir,"narration_${sid}.wav");try{'''
    if old_record not in a:
        raise SystemExit('STAGE 10 FIX: audio start target not found')
    a=a.replace(old_record,new_record,1)
    old_stop='''    fun startRecordingFromBridge(){if(gate.isUnlocked(10))audioAndRecord()}\n    fun stopRecordingFromBridge(){startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))}\n\n    private fun latestRecording():android.net.Uri?{'''
    new_stop='''    fun startRecordingFromBridge(){if(gate.isUnlocked(10))audioAndRecord()}\n    fun stopRecordingFromBridge(){\n        if(gate.state(10)!=StageGate.State.RUNNING)return\n        startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))\n        waitForRecordingCompletion(0)\n    }\n    private fun waitForRecordingCompletion(attempt:Int){\n        if(gate.state(10)!=StageGate.State.RUNNING)return\n        val uri=latestRecording()\n        if(uri!=null){\n            prefs().edit().putString(RECORDING,uri.toString()).apply()\n            pass(10,"Screen recording finalized: $uri")\n            return\n        }\n        if(attempt>=20){fail(10,"Recording stop completed but no finalized MediaStore video was found");return}\n        android.os.Handler(mainLooper).postDelayed({waitForRecordingCompletion(attempt+1)},500L)\n    }\n\n    private fun latestRecording():android.net.Uri?{'''
    if old_stop not in a:
        raise SystemExit('STAGE 10 FIX: recording stop target not found')
    a=a.replace(old_stop,new_stop,1)
    activity.write_text(a,encoding='utf-8')
    print('UI + STAGE ORDER + STAGE 10 FIX: PASS')
else:
    raise SystemExit('UI FIX: activity_fixed.kt missing')

old='for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY)]:write(java/n,d)'
new='for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE)]:write(java/n,d)\n write(java/"MainActivity.kt",Path("activity_fixed.kt").read_text(encoding="utf-8"))\n write(java/"StageGate.kt",Path("stage_gate.kt").read_text(encoding="utf-8"))'
if old not in s: raise SystemExit('ACTIVITY overlay target line not found')
s=s.replace(old,new,1)
old2='android=STAGE/"android-controller";write(android/"local.properties","sdk.dir="+str(S).replace("\\\\","/"));env=os.environ.copy()'
new2='android=STAGE/"android-controller"\n for stale in [android/"app/src/main/java/com/kunal/universalvideo/ControllerBridgeForegroundService.kt",android/"app/src/main/java/com/kunal/universalvideo/SelfRepairManager.kt"]:\n  try: stale.unlink()\n  except FileNotFoundError: pass\n write(android/"local.properties","sdk.dir="+str(S).replace("\\\\","/"));env=os.environ.copy()'
if old2 not in s: raise SystemExit('BUILD cleanup target line not found')
s=s.replace(old2,new2,1)
p.write_text(s,encoding='utf-8')
print('PRE-FLIGHT PATCH: PASS')
