#!/usr/bin/env python3
"""Deterministic Stage-2 hardening. No fake connection state.

The patch is intentionally shape-tolerant at the method boundary because the
progressive UI layer may insert a stage comment between connectMobile() and
selectTarget(). It remains idempotent and fail-closed.
"""
from pathlib import Path
import re

activity = Path("activity_fixed.kt")
repair = Path("pro_repair_v3.py")
if not activity.is_file() or not repair.is_file():
    raise SystemExit("MOBILE_HARDEN_V2: required source missing")

a = activity.read_text(encoding="utf-8")

new = '''    private fun connectMobile(){
        if(!begin(2))return
        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}
        status.text="Stage 2 CHECKING • waiting for actual AccessibilityService binding"
        Thread{
            val deadline=System.currentTimeMillis()+8000
            while(System.currentTimeMillis()<deadline && UniversalAccessibilityService.instance==null){Thread.sleep(100)}
            if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){
                runOnUiThread{fail(2,"Accessibility is enabled but the Kunal Universal Video service is not actually bound")}
                return@Thread
            }
            UniversalAccessibilityService.targetPackage=target
            val ok=bridge?.connect(target)==true
            runOnUiThread{
                if(!ok){fail(2,"Real controller health/status/PING-PONG verification failed; device is not connected");return@runOnUiThread}
                if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){fail(2,"Accessibility service dropped during connection");return@runOnUiThread}
                pass(2,"REAL DEVICE CONTROL CHANNEL VERIFIED: bound AccessibilityService + controller health/status + PING/PONG")
            }
        }.start()
    }
'''

# Replace only the Stage-2 method body. Do not depend on comments between stages.
pat = re.compile(r"(?ms)^    private fun connectMobile\(\)\{.*?^    \}(?=\s*/\*\* Stage 3|\s*private fun selectTarget)")
match = pat.search(a)
if match:
    a = a[:match.start()] + new.rstrip() + a[match.end():]
elif "MOBILE_HARDEN_V2: Stage 2 is asynchronous" in a and "REAL DEVICE CONTROL CHANNEL VERIFIED: bound AccessibilityService + controller health/status + PING/PONG" in a:
    pass
else:
    raise SystemExit("MOBILE_HARDEN_V2: Stage 2 method boundary not found")

if "MOBILE_HARDEN_V2: Stage 2 is asynchronous" not in a:
    a = a.replace("/** Production 1..13 workflow controller.", "/** MOBILE_HARDEN_V2: Stage 2 is asynchronous so service binding can complete. */\n/** Production 1..13 workflow controller.", 1)
activity.write_text(a, encoding="utf-8")

s = repair.read_text(encoding="utf-8")
bridge_pat = re.compile(r"(?ms)(^\s*fun\s+connect\s*\(\s*t\s*:\s*String\s*\)\s*(?::\s*Boolean)?\s*\{).*?(^\s*fun\s+disconnect\s*\()")
bridge_new = ''' fun connect(t:String):Boolean{
  if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){connected.set(false);cb("REAL CONNECT FAIL • AccessibilityService not actually bound");return false}
  target=t.trim();if(target.isNotEmpty())UniversalAccessibilityService.targetPackage=target
  return try{
   val h=(java.net.URL("http://127.0.0.1:$PORT/health").openConnection() as java.net.HttpURLConnection).apply{connectTimeout=700;readTimeout=1000;requestMethod="GET"}
   val hb=h.inputStream.bufferedReader().use{it.readText()};h.disconnect();val hj=JSONObject(hb)
   if(!hj.optBoolean("ok")||hj.optString("protocol")!=ControllerProtocol.PROTOCOL||hj.optString("session_id")!=sessionId){connected.set(false);return false}
   val p=(java.net.URL("http://127.0.0.1:$PORT/status").openConnection() as java.net.HttpURLConnection).apply{connectTimeout=700;readTimeout=1000;requestMethod="GET"}
   val pb=p.inputStream.bufferedReader().use{it.readText()};p.disconnect();val pj=JSONObject(pb)
   if(!pj.optBoolean("ok")||!pj.optBoolean("accessibility")||!pj.optBoolean("service_bound")||pj.optString("session_id")!=sessionId){connected.set(false);return false}
   val ping=(java.net.URL("http://127.0.0.1:$PORT").openConnection() as java.net.HttpURLConnection).apply{connectTimeout=700;readTimeout=1000;requestMethod="POST";doOutput=true;setRequestProperty("Content-Type","application/json")}
   ping.outputStream.use{it.write(JSONObject(mapOf("command" to ControllerProtocol.PING,"session_id" to sessionId,"target_package" to target)).toString().toByteArray(Charsets.UTF_8))}
   val pong=ping.inputStream.bufferedReader().use{it.readText()};ping.disconnect();val pj2=JSONObject(pong)
   if(!pj2.optBoolean("ok")||pj2.optString("command")!="PONG"||pj2.optString("session_id")!=sessionId){connected.set(false);return false}
   connected.set(true);cb("REAL DEVICE CONTROL CHANNEL CONNECTED • HEALTH + STATUS + PING/PONG");true
  }catch(_:Exception){connected.set(false);cb("REAL CONNECT FAIL • controller handshake verification failed");false}
 }
'''
s2, n = bridge_pat.subn(bridge_new + r'\2', s, count=1)
if n != 1:
    raise SystemExit("MOBILE_HARDEN_V2: embedded bridge connect() block not found")
s = s2
if '"service_bound" to (UniversalAccessibilityService.instance!=null)' not in s:
    s = s.replace('"accessibility" to UniversalAccessibilityService.isEnabled,"target_foreground"', '"accessibility" to UniversalAccessibilityService.isEnabled,"service_bound" to (UniversalAccessibilityService.instance!=null),"target_foreground"', 1)
repair.write_text(s, encoding="utf-8")
print("MOBILE_HARDEN_V2=PASS")
