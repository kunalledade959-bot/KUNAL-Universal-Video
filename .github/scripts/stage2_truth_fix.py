#!/usr/bin/env python3
"""Deterministic Stage-2 production-truth repair cell.

Closes the Run #37 blocker without replacing the tested 13-stage app. The
repair is fail-closed: expected source fragments must exist before mutation.
"""
from pathlib import Path

ACTIVITY = Path("activity_fixed.kt")
REPAIR = Path("pro_repair_v3.py")


def require(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"STAGE2_FIX: missing {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise SystemExit(f"STAGE2_FIX: empty {path}")
    return text

activity = require(ACTIVITY)
repair = require(REPAIR)
changed = []

# The UI-side Stage 2 contract must expose an explicit 8-second binding
# deadline. The bridge performs the actual handshake; this deadline is the
# caller-side invariant audited by the independent truth cell.
old_activity = '''        val ok=bridge?.connect("")==true
        if(!ok){fail(2,"Real controller handshake failed; accessibility service is not actually bound");return}
        if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){fail(2,"Accessibility binding disappeared during connection");return}'''
new_activity = '''        val stage2BindingDeadline=System.currentTimeMillis()+8000L
        val ok=bridge?.connect("")==true
        if(!ok || System.currentTimeMillis()>stage2BindingDeadline){
            fail(2,"Real controller handshake failed or exceeded the 8s binding deadline; accessibility service is not actually bound");return
        }
        if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null || System.currentTimeMillis()>stage2BindingDeadline){
            fail(2,"Accessibility binding is not live within the Stage 2 binding deadline");return
        }'''
if old_activity in activity:
    activity = activity.replace(old_activity, new_activity, 1)
    changed.append("activity Stage-2 deadline")
elif "stage2BindingDeadline=System.currentTimeMillis()+8000L" not in activity:
    raise SystemExit("STAGE2_FIX: Stage-2 activity boundary missing; refusing partial patch")

# The generator is the source that can overwrite Android output. Therefore the
# same handshake/deadline must exist there, not merely in the checked-in APK UI.
old_bridge = ''' fun connect(t:String){target=t;UniversalAccessibilityService.targetPackage=t;connected.set(true);cb("REAL LOCAL SESSION CONNECTED")}'''
new_bridge = ''' fun connect(t:String):Boolean{
  if(!running.get())return false
  val stage2BindingDeadline=System.currentTimeMillis()+8000L
  target=t;UniversalAccessibilityService.targetPackage=t
  while(System.currentTimeMillis()<stage2BindingDeadline){
    try{
      if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){Thread.sleep(100);continue}
      val h=java.net.URL("http://127.0.0.1:$PORT/health")
      val hc=(h.openConnection() as java.net.HttpURLConnection).apply{connectTimeout=250;readTimeout=500;requestMethod="GET"}
      val hj=JSONObject(hc.inputStream.bufferedReader().use{it.readText()});hc.disconnect()
      if(!hj.optBoolean("ok") || hj.optString("protocol")!=ControllerProtocol.PROTOCOL || hj.optString("session_id")!=sessionId){Thread.sleep(100);continue}
      val p=java.net.URL("http://127.0.0.1:$PORT/status")
      val pc=(p.openConnection() as java.net.HttpURLConnection).apply{connectTimeout=250;readTimeout=500;requestMethod="GET"}
      val sj=JSONObject(pc.inputStream.bufferedReader().use{it.readText()});pc.disconnect()
      if(!sj.optBoolean("ok") || sj.optString("session_id")!=sessionId || !sj.optBoolean("accessibility") || !sj.optBoolean("service_bound")){Thread.sleep(100);continue}
      val ps=java.net.URL("http://127.0.0.1:$PORT/status")
      val sc=(ps.openConnection() as java.net.HttpURLConnection).apply{connectTimeout=250;readTimeout=500;requestMethod="POST";doOutput=true;setRequestProperty("Content-Type","application/json")}
      sc.outputStream.use{it.write(JSONObject(mapOf("command" to ControllerProtocol.PING,"session_id" to sessionId,"target_package" to t)).toString().toByteArray(Charsets.UTF_8))}
      val pj=JSONObject(sc.inputStream.bufferedReader().use{it.readText()});sc.disconnect()
      if(pj.optBoolean("ok") && pj.optString("command")==ControllerProtocol.PONG && pj.optString("session_id")==sessionId){
        connected.set(true);cb("REAL DEVICE CONTROL CHANNEL CONNECTED • HEALTH/STATUS/PING-PONG VERIFIED");return true
      }
    }catch(_:Exception){}
    try{Thread.sleep(100)}catch(_:InterruptedException){Thread.currentThread().interrupt();break}
  }
  connected.set(false);cb("Controller handshake failed before 8s Stage-2 binding deadline");return false
}'''
if old_bridge in repair:
    repair = repair.replace(old_bridge, new_bridge, 1)
    changed.append("generator LocalBridge 8s handshake")
elif "stage2BindingDeadline=System.currentTimeMillis()+8000L" not in repair:
    raise SystemExit("STAGE2_FIX: generator bridge boundary missing; refusing partial patch")

# Status must expose service_bound because Stage 2 proof depends on real
# AccessibilityService binding, not merely an enabled setting.
old_status = '"accessibility" to UniversalAccessibilityService.isEnabled,"target_foreground"'
new_status = '"accessibility" to UniversalAccessibilityService.isEnabled,"service_bound" to (UniversalAccessibilityService.instance!=null),"target_foreground"'
if old_status in repair:
    repair = repair.replace(old_status, new_status, 1)
    changed.append("generator service_bound status")

ACTIVITY.write_text(activity.rstrip() + "\n", encoding="utf-8")
REPAIR.write_text(repair.rstrip() + "\n", encoding="utf-8")

# Final source checks are deliberately explicit and fail closed.
source = activity + "\n" + repair
needles = [
    "stage2BindingDeadline=System.currentTimeMillis()+8000L",
    "connect(t:String):Boolean",
    "/health",
    "/status",
    "ControllerProtocol.PING",
    "ControllerProtocol.PONG",
    "session_id",
    "service_bound",
    "UniversalAccessibilityService.instance==null",
]
missing = [x for x in needles if x not in source]
if missing:
    raise SystemExit("STAGE2_FIX: verification failed; missing: " + ", ".join(missing))
print("STAGE2_FIX: PASS")
print("CHANGED=" + (", ".join(changed) if changed else "ALREADY_CLEAN"))
print("STAGE2_BINDING_TIMEOUT_MS=8000")
print("STAGE2_HANDSHAKE=HEALTH+STATUS+SERVICE_BOUND+PING/PONG+SESSION")
