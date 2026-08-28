#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parent
STAGE=ROOT/'KUNAL_UNIVERSAL_VIDEO_PRO_V3_STAGE/android-controller'
APK_OUT=ROOT/'KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk'
REPORT=ROOT/'KUNAL_UNIVERSAL_VIDEO_PRO_V3_REPORT.json'
BUILD_LOG=ROOT/'KUNAL_UNIVERSAL_VIDEO_PRO_V3_BUILD.log'
PACKAGE='com.kunal.universalvideo'; MAIN='com.kunal.universalvideo.MainActivity'
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s.rstrip()+'\n',encoding='utf-8')
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''): h.update(c)
 return h.hexdigest()
for name in ('ControllerBridgeForegroundService.kt','SelfRepairManager.kt'):
 p=STAGE/'app/src/main/java/com/kunal/universalvideo'/name
 if p.exists(): p.unlink()
activity='''package com.kunal.universalvideo
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
class MainActivity : AppCompatActivity() {
 private lateinit var status: TextView
 private var bridge: LocalBridgeService? = null
 private var target: String = ""
 private val capture = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
  if (result.resultCode == Activity.RESULT_OK && result.data != null) {
   val intent = Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.START).putExtra(ScreenCaptureService.CODE,result.resultCode).putExtra(ScreenCaptureService.DATA,result.data)
   if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
   status.text = "Recording started"
  } else { status.text = "Recording permission cancelled" }
 }
 override fun onCreate(savedInstanceState: Bundle?) {
  super.onCreate(savedInstanceState); setContentView(R.layout.activity_main); status=findViewById(R.id.status)
  val prefs=getSharedPreferences("kuv",MODE_PRIVATE); val sid=prefs.getString("session_id",null) ?: UUID.randomUUID().toString(); prefs.edit().putString("session_id",sid).apply()
  val apps=packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0)).filter{it.packageName!=packageName}.sortedBy{packageManager.getApplicationLabel(it).toString().lowercase()}
  val spinner=findViewById<Spinner>(R.id.target); spinner.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,apps.map{"${packageManager.getApplicationLabel(it)}\\n${it.packageName}"})
  spinner.setOnItemSelectedListener(object:android.widget.AdapterView.OnItemSelectedListener{
   override fun onNothingSelected(parent:android.widget.AdapterView<*>?) {}
   override fun onItemSelected(parent:android.widget.AdapterView<*>?,view:android.view.View?,position:Int,id:Long){if(position in apps.indices){target=apps[position].packageName;prefs.edit().putString("target_package",target).apply();UniversalAccessibilityService.targetPackage=target}}
  })
  findViewById<Button>(R.id.connect).setOnClickListener{if(target.isBlank())status.text="Select target APK"else{bridge?.connect(target);status.text="REAL SESSION CONNECTED • ${sid.take(8)}"}}
  findViewById<Button>(R.id.disconnect).setOnClickListener{bridge?.disconnect();status.text="Disconnected"}
  findViewById<Button>(R.id.permissions).setOnClickListener{startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}
  findViewById<Button>(R.id.openTarget).setOnClickListener{val intent=packageManager.getLaunchIntentForPackage(target);if(intent==null)status.text="Target cannot be launched"else{intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);startActivity(intent);status.text="Target launched"}}
  findViewById<Button>(R.id.screenRecord).setOnClickListener{requestCapture()}
  bridge=LocalBridgeService(this,sid){message->runOnUiThread{status.text=message}}; bridge?.start(); status.text="Controller ready — bridge starting"
 }
 private fun requestCapture(){val manager=getSystemService(MediaProjectionManager::class.java);capture.launch(manager.createScreenCaptureIntent())}
 fun startRecordingFromBridge(){requestCapture()}
 fun stopRecordingFromBridge(){startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))}
 override fun onDestroy(){bridge?.stop();bridge=null;super.onDestroy()}
}
'''
write(STAGE/'app/src/main/java/com/kunal/universalvideo/MainActivity.kt',activity)
gradle=Path(os.environ.get('GRADLE_BIN','/usr/local/bin/gradle'))
if not gradle.is_file():
 for x in ('/usr/bin/gradle','/usr/local/bin/gradle'):
  if Path(x).is_file(): gradle=Path(x); break
if not gradle.is_file(): raise SystemExit('GRADLE_NOT_FOUND')
p=subprocess.run([str(gradle),'--no-daemon','--stacktrace','--console=plain','clean','assembleDebug'],cwd=STAGE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',timeout=1800)
BUILD_LOG.write_text(p.stdout,encoding='utf-8')
if p.returncode!=0: raise SystemExit(p.returncode)
apks=sorted(STAGE.rglob('*.apk'),key=lambda x:x.stat().st_mtime,reverse=True)
if not apks: raise SystemExit('APK_NOT_FOUND')
apk=apks[0]; sdk=Path(os.environ.get('ANDROID_SDK_ROOT','/usr/local/lib/android/sdk')); aapt=None
for d in sorted((sdk/'build-tools').glob('*'),reverse=True):
 if (d/'aapt').is_file(): aapt=d/'aapt'; break
if not aapt: raise SystemExit('AAPT_NOT_FOUND')
bad=subprocess.run([str(aapt),'dump','badging',str(apk)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace').stdout
pm=re.search(r"package: name='([^']+)'",bad); lm=re.search(r"launchable-activity: name='([^']+)'",bad)
package_ok=bool(pm and pm.group(1)==PACKAGE); launcher_ok=bool(lm and lm.group(1)==MAIN); zip_ok=False
try:
 with zipfile.ZipFile(apk) as z: zip_ok=z.testzip() is None and 'AndroidManifest.xml' in z.namelist() and any(x.endswith('.dex') for x in z.namelist())
except Exception: pass
if not(package_ok and launcher_ok and zip_ok): raise SystemExit('APK_VALIDATION_FAILED')
shutil.copy2(apk,APK_OUT)
REPORT.write_text(json.dumps({'status':'STATIC_AND_BUILD_VERIFIED','repair':'post_compile_repair','apk':str(APK_OUT),'apk_sha256':sha256(APK_OUT),'package_ok':package_ok,'launcher_ok':launcher_ok,'zip_integrity':zip_ok,'runtime_status':{'phone_connection':'UNVERIFIED','accessibility':'UNVERIFIED','target_foreground':'UNVERIFIED','ping_pong':'UNVERIFIED','recording':'UNVERIFIED','two_minute_video':'UNVERIFIED','playback':'UNVERIFIED','gallery':'UNVERIFIED'}},indent=2),encoding='utf-8')
print('[PASS] POST-COMPILE REPAIR BUILD VERIFIED')
print('[PASS] APK SHA256',sha256(APK_OUT))
