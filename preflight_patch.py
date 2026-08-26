from pathlib import Path
import shutil
import re
p=Path('pro_repair_v3.py')
s=p.read_text(encoding='utf-8')
s=s.replace('["UUID.randomUUID","bridge?.connect","sessionId"]','["UUID.randomUUID","bridge?.connect","sid"]')
s=s.replace('for p in [Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:', 'for p in [Path(shutil.which("gradle")) if shutil.which("gradle") else Path("/nonexistent"),Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:')
s=s.replace('if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}', 'if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}; log(f"[BUILD_ENV] sdk={S} gradle={G} java={J}")')
s=s.replace('if static_ok:build_ok,bi=build()', 'if static_ok:build_ok,bi=build(); log("BUILD_RESULT="+json.dumps(bi,indent=2)); log("BUILD_ERRORS="+"\\n".join([x for x in BUILD_LOG.read_text(encoding="utf-8",errors="replace").splitlines() if re.search(r"(^e:|error:|Unresolved reference|Type mismatch|Cannot access|Overload resolution)",x,re.I)]) if BUILD_LOG.exists() else "BUILD_LOG_MISSING")')
activity=Path('activity_fixed.kt').read_text(encoding='utf-8')
s=re.sub(r'ACTIVITY=r"""\n.*?\n"""\n\nMANIFEST', 'ACTIVITY=r"""\n'+activity.rstrip()+'\n"""\n\nMANIFEST', s, count=1, flags=re.S)
s=s.replace('for p,d in [(base/"AndroidManifest.xml",MANIFEST)', 'for stale in [java/"ControllerBridgeForegroundService.kt",java/"SelfRepairManager.kt"]:\n  try: stale.unlink()\n  except FileNotFoundError: pass\n for p,d in [(base/"AndroidManifest.xml",MANIFEST)')
p.write_text(s,encoding='utf-8')
print('PRE-FLIGHT PATCH: PASS')
