from pathlib import Path
import os
import re
import shutil


def replace_once(text, old, new, label):
    if old in text:
        text = text.replace(old, new, 1)
        print(f"{label}: APPLIED")
    else:
        print(f"{label}: ALREADY_APPLIED_OR_NOT_REQUIRED")
    return text


p = Path("pro_repair_v3.py")
s = p.read_text(encoding="utf-8")

s = replace_once(
    s,
    '["UUID.randomUUID","bridge?.connect","sessionId"]',
    '["UUID.randomUUID","bridge?.connect","sid"]',
    "SESSION_SYMBOL_FIX",
)
s = replace_once(
    s,
    'for p in [Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:',
    'for p in [Path(shutil.which("gradle")) if shutil.which("gradle") else Path("/nonexistent"),Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:',
    "GRADLE_DISCOVERY_FIX",
)
s = replace_once(
    s,
    'if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}',
    'if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}; log(f"[BUILD_ENV] sdk={S} gradle={G} java={J}")',
    "BUILD_ENV_LOGGING_FIX",
)
s = replace_once(
    s,
    'if static_ok:build_ok,bi=build()',
    'if static_ok:build_ok,bi=build(); log("BUILD_RESULT="+json.dumps(bi,indent=2)); log("BUILD_ERRORS="+"\\n".join([x for x in BUILD_LOG.read_text(encoding="utf-8",errors="replace").splitlines() if re.search(r"(^e:|error:|Unresolved reference|Type mismatch|Cannot access|Overload resolution)",x,re.I)]) if BUILD_LOG.exists() else "BUILD_LOG_MISSING")',
    "BUILD_ERROR_LOGGING_FIX",
)

activity = Path("activity_fixed.kt")
if not activity.is_file():
    raise SystemExit("PRE-FLIGHT: activity_fixed.kt missing")
a = activity.read_text(encoding="utf-8")

# Keep this preflight backward-compatible with older source snapshots, while
# allowing the hardened activity source to be the canonical input directly.
a = replace_once(a, 'root.addView(story,LinearLayout.LayoutParams(-1,0,1f))', 'root.addView(story,LinearLayout.LayoutParams(-1,180))', "UI_STORY_HEIGHT")
a = replace_once(a, 'button("REFRESH STATUS"){renderStatus()};root.addView(actions);setContentView(root)', 'button("REFRESH STATUS"){renderStatus()};val scroll=ScrollView(this);scroll.isFillViewport=true;scroll.addView(actions);root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f));setContentView(root)', "UI_ACTION_SCROLL")

a = replace_once(
    a,
    '''        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}\n        if(target.isBlank())target=prefs().getString(TARGET,"")?:""\n        if(target.isBlank()){fail(2,"Target APK must be selected");return}\n        UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)\n        pass(2,"Accessibility enabled and local controller session connected")''',
    '''        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}\n        pass(2,"Accessibility enabled and local controller session ready")''',
    "STAGE2_ORDER_FIX",
)
a = replace_once(
    a,
    '''        target=apps[pos].packageName;prefs().edit().putString(TARGET,target).apply();UniversalAccessibilityService.targetPackage=target\n        pass(3,"Target package selected: $target")''',
    '''        target=apps[pos].packageName;prefs().edit().putString(TARGET,target).apply();UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)\n        pass(3,"Target package selected and local controller session connected: $target")''',
    "STAGE3_CONNECTION_FIX",
)

# Legacy Stage 10 source snapshots are upgraded if encountered. The current
# hardened activity already contains this contract, so these replacements are
# intentionally idempotent.
a = replace_once(
    a,
    '''    private fun audioAndRecord(){\n        if(!begin(10))return\n        val text=prefs().getString(STORY,"")?:"";if(text.isBlank()){fail(10,"Story missing for narration");return}\n        val out=File(cacheDir,"narration_${sid}.wav");try{''',
    '''    private fun audioAndRecord(){\n        if(!begin(10))return\n        prefs().edit().remove(RECORDING).putLong("recording_start",System.currentTimeMillis()/1000L).apply()\n        val text=prefs().getString(STORY,"")?:"";if(text.isBlank()){fail(10,"Story missing for narration");return}\n        val out=File(cacheDir,"narration_${sid}.wav");try{''',
    "STAGE10_FRESHNESS_START",
)
a = replace_once(
    a,
    '''    fun startRecordingFromBridge(){if(gate.isUnlocked(10))audioAndRecord()}\n    fun stopRecordingFromBridge(){startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))}\n\n    private fun latestRecording():android.net.Uri?{''',
    '''    fun startRecordingFromBridge(){if(gate.isUnlocked(10))audioAndRecord()}\n    fun stopRecordingFromBridge(){\n        if(gate.state(10)!=StageGate.State.RUNNING)return\n        startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))\n        waitForRecordingCompletion(0)\n    }\n    private fun waitForRecordingCompletion(attempt:Int){\n        if(gate.state(10)!=StageGate.State.RUNNING)return\n        val uri=latestRecording()\n        if(uri!=null){prefs().edit().putString(RECORDING,uri.toString()).apply();pass(10,"Screen recording finalized: $uri");return}\n        if(attempt>=20){fail(10,"Recording stop completed but no new finalized MediaStore video was found");return}\n        android.os.Handler(mainLooper).postDelayed({waitForRecordingCompletion(attempt+1)},500L)\n    }\n\n    private fun latestRecording():android.net.Uri?{''',
    "STAGE10_FINALIZATION_FIX",
)
a = replace_once(
    a,
    '''"${MediaStore.Video.Media.DISPLAY_NAME} LIKE ?",arrayOf("KunalUniversalVideo_%"),"${MediaStore.Video.Media.DATE_ADDED} DESC"''',
    '''"${MediaStore.Video.Media.DISPLAY_NAME} LIKE ? AND ${MediaStore.Video.Media.DATE_ADDED} >= ?",arrayOf("KunalUniversalVideo_%",(prefs().getLong("recording_start",0L)).toString()),"${MediaStore.Video.Media.DATE_ADDED} DESC"''',
    "STAGE10_FRESHNESS_QUERY",
)
activity.write_text(a, encoding="utf-8")

old = 'for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY)]:write(java/n,d)'
new = 'for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE)]:write(java/n,d)\n write(java/"MainActivity.kt",Path("activity_fixed.kt").read_text(encoding="utf-8"))\n write(java/"StageGate.kt",Path("stage_gate.kt").read_text(encoding="utf-8"))'
s = replace_once(s, old, new, "PRODUCTION_ACTIVITY_GATE_OVERLAY")

old2 = 'android=STAGE/"android-controller";write(android/"local.properties","sdk.dir="+str(S).replace("\\\\","/"));env=os.environ.copy()'
new2 = 'android=STAGE/"android-controller"\n for stale in [android/"app/src/main/java/com/kunal/universalvideo/ControllerBridgeForegroundService.kt",android/"app/src/main/java/com/kunal/universalvideo/SelfRepairManager.kt"]:\n  try: stale.unlink()\n  except FileNotFoundError: pass\n write(android/"local.properties","sdk.dir="+str(S).replace("\\\\","/"));env=os.environ.copy()'
s = replace_once(s, old2, new2, "STALE_SOURCE_CLEANUP")

p.write_text(s, encoding="utf-8")
print("PRE-FLIGHT PATCH: PASS")
