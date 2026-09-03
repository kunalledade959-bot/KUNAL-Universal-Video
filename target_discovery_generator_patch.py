#!/usr/bin/env python3
"""A1 target-discovery generator patch.

This file lives at repository root and is executed from the authoritative
self-healing gate. Resolve the generator from this file's directory instead
of relying on a fragile fixed parent depth. Fail closed if the generator is
not present, then replace the synchronous installed-app enumeration with the
launchable-target implementation.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
GEN = ROOT / "pro_repair_v3.py"
if not GEN.is_file():
    raise SystemExit(f"AUTHORITATIVE_GENERATOR_NOT_FOUND: {GEN}")

text = GEN.read_text(encoding="utf-8")

activity = '''package com.kunal.universalvideo
import android.app.Activity
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import java.util.UUID
import java.util.concurrent.Executors

class MainActivity:AppCompatActivity(){
 private lateinit var status:TextView
 private lateinit var spinner:Spinner
 private var bridge:LocalBridgeService?=null
 private var target=""
 private val targetExecutor=Executors.newSingleThreadExecutor()
 private val capture=registerForActivityResult(ActivityResultContracts.StartActivityForResult()){r->
  if(r.resultCode==Activity.RESULT_OK&&r.data!=null){
   val i=Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.START)
    .putExtra(ScreenCaptureService.CODE,r.resultCode).putExtra(ScreenCaptureService.DATA,r.data)
   if(Build.VERSION.SDK_INT>=26)startForegroundService(i)else startService(i)
   status.text="Recording started"
  }else status.text="Recording permission cancelled"
 }
 override fun onCreate(b:Bundle?){
  super.onCreate(b);setContentView(R.layout.activity_main)
  status=findViewById(R.id.status);spinner=findViewById(R.id.target)
  val p=getSharedPreferences("kuv",MODE_PRIVATE)
  val sid=p.getString("session_id",null)?:UUID.randomUUID().toString()
  p.edit().putString("session_id",sid).apply()
  spinner.isEnabled=false;status.text="Loading targets…";loadLaunchableTargets(p)
  spinner.setOnItemSelectedListener(object:android.widget.AdapterView.OnItemSelectedListener{
   override fun onNothingSelected(x:android.widget.AdapterView<*>?){ }
   override fun onItemSelected(x:android.widget.AdapterView<*>?,v:android.view.View?,pos:Int,id:Long){
    val pkg=v?.tag?.toString()?:return
    if(pkg.isNotBlank()&&pkg!=packageName){target=pkg;p.edit().putString("target_package",target).apply();UniversalAccessibilityService.targetPackage=target}
   }
  })
  findViewById<Button>(R.id.connect).setOnClickListener{if(target.isBlank())status.text="Select target APK"else{bridge?.connect(target);status.text="REAL SESSION CONNECTED • ${sid.take(8)}"}}
  findViewById<Button>(R.id.disconnect).setOnClickListener{bridge?.disconnect();status.text="Disconnected"}
  findViewById<Button>(R.id.permissions).setOnClickListener{startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}
  findViewById<Button>(R.id.openTarget).setOnClickListener{val i=packageManager.getLaunchIntentForPackage(target);if(i==null)status.text="Target cannot be launched"else{i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);startActivity(i);status.text="Target launched"}}
  findViewById<Button>(R.id.screenRecord).setOnClickListener{requestCapture()}
  bridge=LocalBridgeService(this,sid){m->runOnUiThread{status.text=m}};bridge?.start();status.text="Controller ready — loading targets"
 }
 private fun loadLaunchableTargets(p:android.content.SharedPreferences){
  targetExecutor.execute{
   val pm=packageManager
   val query=Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
   val rows=try{pm.queryIntentActivities(query,0)}catch(_:Throwable){emptyList()}
   val apps=rows.mapNotNull{r->
    val pkg=r.activityInfo?.packageName?:return@mapNotNull null
    if(pkg==packageName)return@mapNotNull null
    val label=try{r.loadLabel(pm).toString().ifBlank{pkg}}catch(_:Throwable){pkg}
    pkg to label
   }.distinctBy{it.first}.sortedBy{it.second.lowercase()}
   val saved=p.getString("target_package","")?:""
   runOnUiThread{
    if(isFinishing||isDestroyed)return@runOnUiThread
    val adapter=object:android.widget.ArrayAdapter<String>(this,android.R.layout.simple_spinner_item,apps.map{"${it.second}\n${it.first}"}){
     override fun getView(position:Int,convertView:android.view.View?,parent:android.view.ViewGroup):android.view.View{
      val v=super.getView(position,convertView,parent);v.tag=apps[position].first;return v
     }
    }
    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
    spinner.adapter=adapter;spinner.isEnabled=apps.isNotEmpty()
    val savedIndex=apps.indexOfFirst{it.first==saved}
    if(savedIndex>=0)spinner.setSelection(savedIndex)else if(apps.isNotEmpty())spinner.setSelection(0)
    status.text=if(apps.isEmpty())"No launchable target APK found"else"Controller ready — ${apps.size} target(s) available"
   }
  }
 }
 private fun requestCapture(){val m=getSystemService(MediaProjectionManager::class.java);capture.launch(m.createScreenCaptureIntent())}
 fun startRecordingFromBridge()=requestCapture()
 fun stopRecordingFromBridge()=startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))
 override fun onDestroy(){targetExecutor.shutdownNow();bridge?.stop();bridge=null;super.onDestroy()}
}'''

pattern = r"ACTIVITY=r'''\n.*?\n'''\nMANIFEST="
text, replaced = re.subn(
    pattern,
    lambda m: "ACTIVITY=r'''\n" + activity + "\n'''\nMANIFEST=",
    text,
    count=1,
    flags=re.S,
)
if replaced != 1:
    raise SystemExit("EMBEDDED_ACTIVITY_BLOCK_NOT_FOUND")

old = 'g("TARGET_DISCOVERY",all(x in a for x in ["getInstalledApplications","getLaunchIntentForPackage"]))'
new = 'g("TARGET_DISCOVERY",all(x in a for x in ["queryIntentActivities","CATEGORY_LAUNCHER","getLaunchIntentForPackage","targetExecutor"]))'
if old not in text:
    raise SystemExit("TARGET_DISCOVERY_STATIC_RULE_NOT_FOUND")
text = text.replace(old, new, 1)

# Generator-level integrity gate: no synchronous all-installed-app enumeration
# may survive in the authoritative generator.
if "getInstalledApplications" in text:
    raise SystemExit("FORBIDDEN_SYNC_INSTALLED_APPLICATION_ENUMERATION")
for token in ("queryIntentActivities", "CATEGORY_LAUNCHER", "targetExecutor", "getLaunchIntentForPackage"):
    if token not in text:
        raise SystemExit(f"TARGET_DISCOVERY_TOKEN_MISSING: {token}")

GEN.write_text(text, encoding="utf-8")
print("TARGET_DISCOVERY_A1_GENERATOR_FIX=PASS")
