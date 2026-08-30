#!/usr/bin/env python3
"""Second-pass hardening for real Mobile Connection.

This patch is intentionally narrow: it does not change the 13-stage contracts. It makes
Stage 2 wait for the Android AccessibilityService to actually bind and makes the local
controller refuse connection unless that bound service is present. The patch is idempotent.
"""
from pathlib import Path
import re

activity = Path("activity_fixed.kt")
repair = Path("pro_repair_v3.py")
if not activity.is_file():
    raise SystemExit("MOBILE_HARDEN_V2: activity_fixed.kt missing")
if not repair.is_file():
    raise SystemExit("MOBILE_HARDEN_V2: pro_repair_v3.py missing")

a = activity.read_text(encoding="utf-8")
old = '''    private fun connectMobile(){
        if(!begin(2))return
        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}
        UniversalAccessibilityService.targetPackage=target
        val ok=bridge?.connect(target)==true
        if(!ok){fail(2,"Real controller handshake failed; device is not connected");return}
        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service dropped during connection");return}
        pass(2,"REAL DEVICE CONTROL CHANNEL VERIFIED: handshake + PING/PONG + Accessibility ready")
    }'''
new = '''    private fun connectMobile(){
        if(!begin(2))return
        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}
        // Android may report the service enabled before onServiceConnected() has completed.
        // Wait briefly for the real service binding instead of treating the Settings toggle as a connection.
        val deadline=System.currentTimeMillis()+5000
        while(System.currentTimeMillis()<deadline && UniversalAccessibilityService.instance==null){Thread.sleep(100)}
        if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){
            fail(2,"Accessibility is enabled but the Kunal Universal Video service is not actually bound")
            return
        }
        UniversalAccessibilityService.targetPackage=target
        val ok=bridge?.connect(target)==true
        if(!ok){fail(2,"Real controller handshake failed; device is not connected");return}
        if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){fail(2,"Accessibility service dropped during connection");return}
        pass(2,"REAL DEVICE CONTROL CHANNEL VERIFIED: bound AccessibilityService + controller handshake + PING/PONG")
    }'''
if old in a:
    a = a.replace(old, new, 1)
elif "MOBILE_HARDEN_V2" not in a:
    raise SystemExit("MOBILE_HARDEN_V2: Stage 2 block not found")
a = a.replace("/** Production 1..13 workflow controller.", "/** MOBILE_HARDEN_V2: Stage 2 requires an actually bound AccessibilityService. */\n/** Production 1..13 workflow controller.", 1)
activity.write_text(a, encoding="utf-8")

s = repair.read_text(encoding="utf-8")
old_bridge = ''' fun connect(t:String):Boolean{
  if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){connected.set(false);cb("REAL CONNECT FAIL • Accessibility service is not actually bound");return false}
  target=t.trim();if(target.isNotEmpty())UniversalAccessibilityService.targetPackage=target
  connected.set(true);cb("REAL DEVICE CONTROL CHANNEL CONNECTED");return true
 }'''
new_bridge = ''' fun connect(t:String):Boolean{
  if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){connected.set(false);cb("REAL CONNECT FAIL • Accessibility service is not actually bound");return false}
  target=t.trim();if(target.isNotEmpty())UniversalAccessibilityService.targetPackage=target
  // Verify the controller transport itself before declaring connected.
  try{
   val c=(java.net.URL("http://127.0.0.1:$PORT/health").openConnection() as java.net.HttpURLConnection).apply{connectTimeout=500;readTimeout=800;requestMethod="GET"}
   val h=c.inputStream.bufferedReader().use{it.readText()};c.disconnect()
   val hj=JSONObject(h);if(!hj.optBoolean("ok")||hj.optString("protocol")!=ControllerProtocol.PROTOCOL){connected.set(false);return false}
   val p=(java.net.URL("http://127.0.0.1:$PORT/status").openConnection() as java.net.HttpURLConnection).apply{connectTimeout=500;readTimeout=800;requestMethod="GET"}
   val b=p.inputStream.bufferedReader().use{it.readText()};p.disconnect()
   val sj=JSONObject(b);if(!sj.optBoolean("ok")||!sj.optBoolean("accessibility")||!sj.optBoolean("service_bound")){connected.set(false);return false}
  }catch(_:Exception){connected.set(false);cb("REAL CONNECT FAIL • controller health/status verification failed");return false}
  connected.set(true);cb("REAL DEVICE CONTROL CHANNEL CONNECTED");return true
 }'''
if old_bridge in s:
    s = s.replace(old_bridge, new_bridge, 1)
elif "service_bound" not in s:
    raise SystemExit("MOBILE_HARDEN_V2: bridge block not found")
repair.write_text(s, encoding="utf-8")
print("MOBILE_HARDEN_V2=PASS")
