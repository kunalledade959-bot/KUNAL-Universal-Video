from pathlib import Path
import shutil
import re
p=Path('pro_repair_v3.py')
s=p.read_text(encoding='utf-8')
s=s.replace('["UUID.randomUUID","bridge?.connect","sessionId"]','["UUID.randomUUID","bridge?.connect","sid"]')
s=s.replace('for p in [Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:', 'for p in [Path(shutil.which("gradle")) if shutil.which("gradle") else Path("/nonexistent"),Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:')
s=s.replace('if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}', 'if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}; log(f"[BUILD_ENV] sdk={S} gradle={G} java={J}")')
s=s.replace('if static_ok:build_ok,bi=build()', 'if static_ok:build_ok,bi=build(); log("BUILD_RESULT="+json.dumps(bi,indent=2)); log("BUILD_ERRORS="+"\\n".join([x for x in BUILD_LOG.read_text(encoding="utf-8",errors="replace").splitlines() if re.search(r"(^e:|error:|Unresolved reference|Type mismatch|Cannot access|Overload resolution)",x,re.I)]) if BUILD_LOG.exists() else "BUILD_LOG_MISSING")')
old='for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY)]:write(java/n,d)'
new='for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE)]:write(java/n,d)\n write(java/"MainActivity.kt",Path("activity_fixed.kt").read_text(encoding="utf-8"))'
if old not in s: raise SystemExit('ACTIVITY overlay target line not found')
s=s.replace(old,new,1)
old2='android=STAGE/"android-controller";write(android/"local.properties","sdk.dir="+str(S).replace("\\\\","/"));env=os.environ.copy()'
new2='android=STAGE/"android-controller"\n for stale in [android/"app/src/main/java/com/kunal/universalvideo/ControllerBridgeForegroundService.kt",android/"app/src/main/java/com/kunal/universalvideo/SelfRepairManager.kt"]:\n  try: stale.unlink()\n  except FileNotFoundError: pass\n write(android/"local.properties","sdk.dir="+str(S).replace("\\\\","/"));env=os.environ.copy()'
if old2 not in s: raise SystemExit('BUILD cleanup target line not found')
s=s.replace(old2,new2,1)
p.write_text(s,encoding='utf-8')
print('PRE-FLIGHT PATCH: PASS')
