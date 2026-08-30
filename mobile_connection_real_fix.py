#!/usr/bin/env python3
"""Patch the production generator so Mobile Connection is a real Android accessibility handshake.

The old generator treated a local bridge flag as a connection. This patch makes the generated
APK require the Android AccessibilityService to be actually bound before reporting connected.
It is intentionally idempotent and fails closed.
"""
from pathlib import Path
import re

P = Path("pro_repair_v3.py")
s = P.read_text(encoding="utf-8")

BRIDGE = r'''package com.kunal.universalvideo
import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.ServerSocket
import java.net.SocketException
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
class LocalBridgeService(private val context:Context,private val sessionId:String,private val cb:(String)->Unit){
 companion object{const val PORT=8765}
 private val running=AtomicBoolean(false);private val connected=AtomicBoolean(false);private var server:ServerSocket?=null;private var target="";private val pool=Executors.newCachedThreadPool()
 fun start(){if(!running.compareAndSet(false,true))return;pool.execute{try{server=ServerSocket(PORT,32,java.net.InetAddress.getByName("127.0.0.1"));cb("Bridge listening on 127.0.0.1:$PORT");while(running.get()){try{val s=server?.accept()?:break;pool.execute{handle(s)}}catch(_:SocketException){if(running.get())cb("Bridge socket error")}}}catch(e:Exception){cb("Bridge failed: ${e.javaClass.simpleName}")}}}
 /** Fail closed: Android must have actually bound our AccessibilityService. */
 fun connect(t:String):Boolean{
  if(!UniversalAccessibilityService.isEnabled || UniversalAccessibilityService.instance==null){connected.set(false);cb("REAL CONNECT FAIL • Accessibility service is not actually bound");return false}
  target=t.trim();if(target.isNotEmpty())UniversalAccessibilityService.targetPackage=target
  connected.set(true);cb("REAL DEVICE CONTROL CHANNEL CONNECTED");return true
 }
 fun disconnect(){connected.set(false);cb("Disconnected")}
 fun stop(){running.set(false);connected.set(false);try{server?.close()}catch(_:Exception){};pool.shutdownNow()}
 private fun handle(s:java.net.Socket){s.use{socket->val r=BufferedReader(InputStreamReader(socket.getInputStream()));val first=r.readLine()?:return;var n=0;while(true){val h=r.readLine()?:break;if(h.isEmpty())break;if(h.lowercase().startsWith("content-length:"))n=h.substringAfter(":").trim().toIntOrNull()?:0};val body=if(n>0)CharArray(n).let{r.read(it);String(it)}else"";val path=first.split(" ").getOrNull(1)?.substringBefore("?")?:"/";val response=route(path,body);val b=response.toByteArray(Charsets.UTF_8);val o=socket.getOutputStream();o.write(("HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ${b.size}\r\nConnection: close\r\n\r\n").toByteArray());o.write(b);o.flush()}}
 private fun route(path:String,body:String):String{if(path=="/health")return JSONObject(mapOf("ok" to true,"protocol" to ControllerProtocol.PROTOCOL,"session_id" to sessionId,"connected" to connected.get(),"target_package" to target)).toString();if(path=="/status")return JSONObject(mapOf("ok" to true,"session_id" to sessionId,"connected" to connected.get(),"target_package" to target,"accessibility" to UniversalAccessibilityService.isEnabled,"service_bound" to (UniversalAccessibilityService.instance!=null),"target_foreground" to UniversalAccessibilityService.targetForeground)).toString();val cmd=try{JSONObject(body).optString("command","").uppercase()}catch(_:Exception){""};return when(cmd){"PING"->if(UniversalAccessibilityService.isEnabled&&UniversalAccessibilityService.instance!=null)JSONObject(mapOf("ok" to true,"command" to "PONG","session_id" to sessionId)).toString()else JSONObject(mapOf("ok" to false,"error" to "Accessibility service not bound")).toString();"DISCONNECT"->{disconnect();JSONObject(mapOf("ok" to true)).toString()};"OPEN_TARGET"->JSONObject(mapOf("ok" to UniversalAccessibilityService.launchPackage(context,target),"target_package" to target)).toString();"STATUS"->route("/status","");"START_RECORD"->{(context as? MainActivity)?.startRecordingFromBridge();JSONObject(mapOf("ok" to true)).toString()};"STOP_RECORD"->{(context as? MainActivity)?.stopRecordingFromBridge();JSONObject(mapOf("ok" to true)).toString()};else->JSONObject(mapOf("ok" to false,"error" to "Unsupported command")).toString()}}
}
'''

ACTIVITY = r'''package com.kunal.universalvideo
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import java.util.UUID
class MainActivity:AppCompatActivity(){
 private lateinit var status:TextView;private var bridge:LocalBridgeService?=null;private var target="";private val capture=registerForActivityResult(ActivityResultContracts.StartActivityForResult()){r->if(r.resultCode==Activity.RESULT_OK&&r.data!=null){val i=Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.START).putExtra(ScreenCaptureService.CODE,r.resultCode).putExtra(ScreenCaptureService.DATA,r.data);if(Build.VERSION.SDK_INT>=26)startForegroundService(i)else startService(i);status.text="Recording started"}else status.text="Recording permission cancelled"}}
 override fun onCreate(b:Bundle?){super.onCreate(b);setContentView(R.layout.activity_main);status=findViewById(R.id.status);val p=getSharedPreferences("kuv",MODE_PRIVATE);val sid=p.getString("session_id",null)?:UUID.randomUUID().toString();p.edit().putString("session_id",sid).apply();val apps=packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0)).filter{it.packageName!=packageName}.sortedBy{packageManager.getApplicationLabel(it).toString().lowercase()};val sp=findViewById<Spinner>(R.id.target);sp.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,apps.map{"${packageManager.getApplicationLabel(it)}\n${it.packageName}"});sp.setOnItemSelectedListener(object:android.widget.AdapterView.OnItemSelectedListener{override fun onNothingSelected(x:android.widget.AdapterView<*>?){};override fun onItemSelected(x:android.widget.AdapterView<*>?,v:android.view.View?,pos:Int,id:Long){if(pos in apps.indices){target=apps[pos].packageName;p.edit().putString("target_package",target).apply();UniversalAccessibilityService.targetPackage=target}}});findViewById<Button>(R.id.connect).setOnClickListener{val ok=bridge?.connect(target)==true;if(ok)status.text="REAL DEVICE CONNECTED • ACCESSIBILITY BOUND • ${sid.take(8)}"else status.text="CONNECT FAIL • Enable Kunal Universal Video accessibility service"};findViewById<Button>(R.id.disconnect).setOnClickListener{bridge?.disconnect();status.text="Disconnected"};findViewById<Button>(R.id.permissions).setOnClickListener{startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))};findViewById<Button>(R.id.openTarget).setOnClickListener{val i=packageManager.getLaunchIntentForPackage(target);if(i==null)status.text="Target cannot be launched"else{i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);startActivity(i);status.text="Target launched"}};findViewById<Button>(R.id.screenRecord).setOnClickListener{requestCapture()};bridge=LocalBridgeService(this,sid){m->runOnUiThread{status.text=m}};bridge?.start();status.text="Controller ready • waiting for real accessibility service"}
 private fun requestCapture(){val m=getSystemService(MediaProjectionManager::class.java);capture.launch(m.createScreenCaptureIntent())}
 fun startRecordingFromBridge()=requestCapture()
 fun stopRecordingFromBridge()=startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))
 override fun onDestroy(){bridge?.stop();bridge=null;super.onDestroy()}
}
'''

def replace_block(name, next_name, new):
 global s
 pat = rf"{name}=r'''(?s:.*?)'''\n{next_name}="
 m = re.search(pat, s)
 if not m:
  raise SystemExit(f"cannot locate {name} block in pro_repair_v3.py")
 replacement = f"{name}=r'''{new.rstrip()}'''\n{next_name}="
 s = s[:m.start()] + replacement + s[m.end():]

replace_block("BRIDGE", "ACCESS", BRIDGE)
replace_block("ACTIVITY", "MANIFEST", ACTIVITY)
P.write_text(s, encoding="utf-8")
print("REAL_MOBILE_CONNECTION_PATCH=PASS")
