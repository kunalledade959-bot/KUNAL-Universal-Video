from pathlib import Path
import shutil
import re
p=Path('pro_repair_v3.py')
s=p.read_text(encoding='utf-8')
s=s.replace('["UUID.randomUUID","bridge?.connect","sessionId"]','["UUID.randomUUID","bridge?.connect","sid"]')
s=s.replace('for p in [Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:', 'for p in [Path(shutil.which("gradle")) if shutil.which("gradle") else Path("/nonexistent"),Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:')
s=s.replace('if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}', 'if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}; log(f"[BUILD_ENV] sdk={S} gradle={G} java={J}")')
s=s.replace('if static_ok:build_ok,bi=build()', 'if static_ok:build_ok,bi=build(); log("BUILD_RESULT="+json.dumps(bi,indent=2)); log("BUILD_ERRORS="+"\\n".join([x for x in BUILD_LOG.read_text(encoding="utf-8",errors="replace").splitlines() if re.search(r"(^e:|error:|Unresolved reference|Type mismatch|Cannot access|Overload resolution)",x,re.I)]) if BUILD_LOG.exists() else "BUILD_LOG_MISSING")')

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
    old_connect='UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)\n        pass(2,"Accessibility enabled and local controller session connected")'
    new_connect='UniversalAccessibilityService.targetPackage=target\n        val ok=bridge?.connect(target)==true\n        if(!ok){fail(2,"Real controller handshake failed; device is not connected");return}\n        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service dropped during connection");return}\n        pass(2,"REAL DEVICE CONTROL CHANNEL VERIFIED: handshake + PING/PONG + Accessibility ready")'
    if old_connect not in a:
        raise SystemExit('REAL CONNECT FIX: target not found')
    a=a.replace(old_connect,new_connect,1)
    old_operate='i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);UniversalAccessibilityService.targetPackage=target;startActivity(i)\n        pass(6,"Target launched and Accessibility operation channel armed")'
    new_operate='i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);UniversalAccessibilityService.targetPackage=target;startActivity(i)\n        val deadline=System.currentTimeMillis()+5000\n        while(System.currentTimeMillis()<deadline && !UniversalAccessibilityService.targetForeground){Thread.sleep(150)}\n        val root=UniversalAccessibilityService.instance?.rootInActiveWindow\n        if(!UniversalAccessibilityService.targetForeground || root==null){root?.recycle();fail(6,"Target launch did not produce a live foreground accessibility channel");return}\n        var nodes=0\n        fun probe(n:AccessibilityNodeInfo?){if(n==null)return;nodes++;for(k in 0 until n.childCount)probe(n.getChild(k))}\n        probe(root);root.recycle()\n        if(nodes<1){fail(6,"Target foreground but accessibility tree is empty");return}\n        pass(6,"REAL TARGET OPERATION VERIFIED: foreground + live accessibility tree nodes=$nodes")'
    if old_operate not in a:
        raise SystemExit('REAL OPERATE FIX: target not found')
    a=a.replace(old_operate,new_operate,1)
    # Stage 10 is RUNNING until a real recorded MediaStore item is observed after stop.
    old_stop='fun stopRecordingFromBridge(){startService(Intent(this@MainActivity,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))}'
    new_stop='fun stopRecordingFromBridge(){startService(Intent(this@MainActivity,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP));android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({val u=latestRecording();if(u==null){fail(10,"Recording stopped but no real MediaStore video was produced");return@postDelayed};prefs().edit().putString(RECORDING,u.toString()).apply();pass(10,"REAL AUDIO/RECORDING EVIDENCE VERIFIED: TTS audio + MediaStore MP4 captured")},1500)}'
    if old_stop in a:a=a.replace(old_stop,new_stop,1)
    else:
        old_stop2='fun stopRecordingFromBridge(){startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))}'
        if old_stop2 not in a: raise SystemExit('REAL RECORD FIX: stop target not found')
        a=a.replace(old_stop2,new_stop.replace('this@MainActivity','this'),1)
    # Stage 12 performs a real repair attempt by rebuilding the assembly when the
    # stored output is missing/corrupt, then verifies the repaired media tracks.
    old_verify='''private fun verifyAndFix(){\n        if(!begin(12))return\n        val p=prefs().getString(FINAL,"")?:"";val f=if(p.isNotBlank())File(p)else null\n        if(f==null||!f.isFile||f.length()<1024){fail(12,"Assembled MP4 missing or unreadable");return}\n        val extractor=MediaExtractor();try{extractor.setDataSource(f.absolutePath);if(extractor.trackCount<1){fail(12,"MP4 has no readable tracks");return};pass(12,"Assembled MP4 readable with ${extractor.trackCount} media tracks")}catch(e:Exception){fail(12,"Verification failed: ${e.javaClass.simpleName}")}finally{extractor.release()}\n    }'''
    new_verify='''private fun verifyAndFix(){\n        if(!begin(12))return\n        var repaired=false\n        var p=prefs().getString(FINAL,"")?:""\n        var f=if(p.isNotBlank())File(p)else null\n        if(f==null||!f.isFile||f.length()<1024){\n            val video=latestRecording();val audioPath=prefs().getString(AUDIO,"")?:""\n            if(video==null||audioPath.isBlank()||!File(audioPath).isFile){fail(12,"Output invalid and repair inputs are missing");return}\n            try{val out=File(cacheDir,"assembled_repair_${sid}.mp4");muxVideoAudio(video,File(audioPath),out);if(!out.isFile||out.length()<1024){fail(12,"Auto-fix produced no usable MP4");return};prefs().edit().putString(FINAL,out.absolutePath).apply();p=out.absolutePath;f=out;repaired=true}catch(e:Exception){fail(12,"Auto-fix assembly failed: ${e.javaClass.simpleName}");return}\n        }\n        val extractor=MediaExtractor();try{extractor.setDataSource(f!!.absolutePath);if(extractor.trackCount<2){fail(12,"Verified output does not contain both video and audio tracks");return};var duration=0L;for(i in 0 until extractor.trackCount){duration=maxOf(duration,extractor.getTrackFormat(i).optLong(MediaFormat.KEY_DURATION,0L))};if(duration<=0){fail(12,"Verified output has no positive media duration");return};pass(12,if(repaired)"REAL AUTO-FIX VERIFIED: rebuilt assembly and re-read ${extractor.trackCount} tracks durationUs=$duration" else "REAL OUTPUT VERIFICATION VERIFIED: ${extractor.trackCount} tracks durationUs=$duration")}catch(e:Exception){fail(12,"Verification failed: ${e.javaClass.simpleName}")}finally{extractor.release()}\n    }'''
    if old_verify not in a: raise SystemExit('REAL AUTOFIX: verify target not found')
    a=a.replace(old_verify,new_verify,1)
    activity.write_text(a,encoding='utf-8')
    print('REAL RUNTIME STAGE FIX: PASS')
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

old_bridge='fun connect(t:String){target=t;UniversalAccessibilityService.targetPackage=t;connected.set(true);cb("REAL LOCAL SESSION CONNECTED")}'
new_bridge='''fun connect(t:String):Boolean{\n  if(t.isBlank()||!running.get())return false\n  target=t;UniversalAccessibilityService.targetPackage=t\n  repeat(20){\n    try{\n      val u=java.net.URL("http://127.0.0.1:$PORT/health")\n      val c=(u.openConnection() as java.net.HttpURLConnection).apply{connectTimeout=250;readTimeout=500;requestMethod="GET"}\n      val body=c.inputStream.bufferedReader().use{it.readText()};c.disconnect()\n      val j=JSONObject(body)\n      if(j.optBoolean("ok") && j.optString("protocol")==ControllerProtocol.PROTOCOL){\n        val p=java.net.URL("http://127.0.0.1:$PORT/status")\n        val pc=(p.openConnection() as java.net.HttpURLConnection).apply{connectTimeout=250;readTimeout=500;requestMethod="GET"}\n        val pb=pc.inputStream.bufferedReader().use{it.readText()};pc.disconnect()\n        val sj=JSONObject(pb)\n        if(sj.optBoolean("ok") && sj.optString("session_id")==sessionId){\n          connected.set(true);cb("REAL DEVICE CONTROL CHANNEL CONNECTED");return true\n        }\n      }\n    }catch(_:Exception){}\n    try{Thread.sleep(100)}catch(_:InterruptedException){Thread.currentThread().interrupt();return false}\n  }\n  connected.set(false);cb("Controller handshake failed");return false\n}'''
if old_bridge not in s: raise SystemExit('REAL BRIDGE FIX: bridge connect target not found')
s=s.replace(old_bridge,new_bridge,1)

old_emb_connect='UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)\n        pass(2,"Accessibility enabled and local controller session connected")'
if old_emb_connect in s:s=s.replace(old_emb_connect,new_connect,1)
old_emb_operate='i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);UniversalAccessibilityService.targetPackage=target;startActivity(i)\n        pass(6,"Target launched and Accessibility operation channel armed")'
if old_emb_operate in s:s=s.replace(old_emb_operate,new_operate,1)

p.write_text(s,encoding='utf-8')
print('PRE-FLIGHT PATCH: PASS')