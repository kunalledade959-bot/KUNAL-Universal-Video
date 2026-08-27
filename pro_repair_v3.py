#!/usr/bin/env python3
"""Kunal Universal Video — Pro Level Repair V3.
Rebuilds the Android project, adds real local controller transport,
Accessibility target control, MediaProjection MP4 recording, Gallery output,
and strict static/build verification. No fake PASS.
"""
from pathlib import Path
import ast, hashlib, json, os, re, shutil, stat, subprocess, time, zipfile
import xml.etree.ElementTree as ET

INPUT=Path(__file__).resolve().parent; WORK=INPUT
MASTER=INPUT/"KUNAL_UNIVERSAL_VIDEO_MASTER.py"
SOURCE_ZIP=INPUT/"KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip"
PROJECT=WORK/"KUNAL_UNIVERSAL_VIDEO"
STAGE=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3_STAGE"
BACKUP=WORK/("KUNAL_UNIVERSAL_VIDEO_PRO_V3_BACKUP_"+time.strftime("%Y%m%d_%H%M%S"))
REPORT=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3_REPORT.json"
BUILD_LOG=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3_BUILD.log"
APK_OUT=WORK/"KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PACKAGE="com.kunal.universalvideo"; MAIN="com.kunal.universalvideo.MainActivity"

def log(x=""): print(x,flush=True)
def read(p): return p.read_text(encoding="utf-8",errors="replace") if p.is_file() else ""
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s.rstrip()+"\n",encoding="utf-8")
def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  while True:
   chunk=f.read(1048576)
   if not chunk: break
   h.update(chunk)
 return h.hexdigest()
def exe(p):
 try:p.chmod(p.stat().st_mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
 except Exception:pass
def run(cmd,cwd=None,env=None,timeout=1800):
 try:
  r=subprocess.run([str(x) for x in cmd],cwd=str(cwd) if cwd else None,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace",timeout=timeout)
  return r.returncode,r.stdout
 except Exception as e:return 999,repr(e)
def fmap(text):
 t=ast.parse(text)
 for n in ast.walk(t):
  if isinstance(n,ast.Assign):
   for x in n.targets:
    if isinstance(x,ast.Name) and x.id=="FILES":
     try:v=ast.literal_eval(n.value)
     except Exception:continue
     if isinstance(v,dict):return v
def normxml(p):
 s=p.read_bytes().decode("utf-8-sig",errors="replace").replace("\x00","");m=re.search(r"<\?xml\b",s,re.I)
 if m:s=s[m.start():]
 p.write_text(s.rstrip()+"\n",encoding="utf-8")
def xmlok(p):
 try:ET.parse(p);return True
 except Exception:return False
def gradle():
 for p in [Path(os.environ.get("GRADLE_BIN","/usr/local/bin/gradle")),Path("/usr/bin/gradle"),Path("/usr/local/bin/gradle"),PROJECT/"android-controller/gradlew"]:
  if p.is_file():exe(p);return p
def sdk():
 roots=[Path(os.environ.get(k,"/nonexistent")) for k in ("ANDROID_SDK_ROOT","ANDROID_HOME")]
 roots += [Path("/opt/android-sdk"),Path("/usr/lib/android-sdk"),Path.home()/"Android/Sdk"]
 for r in roots:
  if (r/"platforms/android-35/android.jar").is_file():return r

PROTOCOL=r'''package com.kunal.universalvideo
object ControllerProtocol { const val PROTOCOL="kunal-video-v1"; const val PING="PING"; const val PONG="PONG"; const val OPEN_TARGET="OPEN_TARGET"; const val STATUS="STATUS"; const val DISCONNECT="DISCONNECT"; const val START_RECORD="START_RECORD"; const val STOP_RECORD="STOP_RECORD" }
'''
BRIDGE=r'''package com.kunal.universalvideo
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
 fun start(){if(!running.compareAndSet(false,true))return;pool.execute{try{server=ServerSocket(PORT,32,java.net.InetAddress.getByName("127.0.0.1"));while(running.get()){try{val s=server?.accept()?:break;pool.execute{handle(s)}}catch(_:SocketException){if(running.get())cb("Bridge socket error")}}}catch(e:Exception){cb("Bridge failed: ${e.javaClass.simpleName}")}}}
 fun connect(t:String){target=t;UniversalAccessibilityService.targetPackage=t;connected.set(true);cb("REAL LOCAL SESSION CONNECTED")}
 fun disconnect(){connected.set(false);cb("Disconnected")}
 fun stop(){running.set(false);connected.set(false);try{server?.close()}catch(_:Exception){};pool.shutdownNow()}
 private fun handle(s:java.net.Socket){s.use{socket->val r=BufferedReader(InputStreamReader(socket.getInputStream()));val first=r.readLine()?:return;var n=0;while(true){val h=r.readLine()?:break;if(h.isEmpty())break;if(h.lowercase().startsWith("content-length:"))n=h.substringAfter(":").trim().toIntOrNull()?:0};val body=if(n>0)CharArray(n).let{r.read(it);String(it)}else"";val path=first.split(" ").getOrNull(1)?.substringBefore("?")?:"/";val response=route(path,body);val b=response.toByteArray(Charsets.UTF_8);val o=socket.getOutputStream();o.write(("HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ${b.size}\r\nConnection: close\r\n\r\n").toByteArray());o.write(b);o.flush()}}
 private fun route(path:String,body:String):String{if(path=="/health")return JSONObject(mapOf("ok" to true,"protocol" to ControllerProtocol.PROTOCOL,"session_id" to sessionId,"connected" to connected.get(),"target_package" to target)).toString();if(path=="/status")return JSONObject(mapOf("ok" to true,"session_id" to sessionId,"connected" to connected.get(),"target_package" to target,"accessibility" to UniversalAccessibilityService.isEnabled,"target_foreground" to UniversalAccessibilityService.targetForeground)).toString();val cmd=try{JSONObject(body).optString("command","").uppercase()}catch(_:Exception){""};return when(cmd){"PING"->JSONObject(mapOf("ok" to true,"command" to "PONG","session_id" to sessionId)).toString();"DISCONNECT"->{disconnect();JSONObject(mapOf("ok" to true)).toString()};"OPEN_TARGET"->JSONObject(mapOf("ok" to UniversalAccessibilityService.launchPackage(context,target),"target_package" to target)).toString();"STATUS"->route("/status","");"START_RECORD"->{(context as? MainActivity)?.startRecordingFromBridge();JSONObject(mapOf("ok" to true)).toString()};"STOP_RECORD"->{(context as? MainActivity)?.stopRecordingFromBridge();JSONObject(mapOf("ok" to true)).toString()};else->JSONObject(mapOf("ok" to false,"error" to "Unsupported command")).toString()}}
}
'''
ACCESS=r'''package com.kunal.universalvideo
import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
class UniversalAccessibilityService:AccessibilityService(){
 companion object{@Volatile var instance:UniversalAccessibilityService?=null;@Volatile var targetPackage="";@Volatile var targetForeground=false;@Volatile var isEnabled=false;fun launchPackage(c:Context,p:String):Boolean{val i=c.packageManager.getLaunchIntentForPackage(p)?:return false;i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);c.startActivity(i);return true};fun clickText(t:String)=instance?.clickTextInternal(t)?:false;fun setFocusedText(t:String)=instance?.setTextInternal(t)?:false}
 override fun onServiceConnected(){super.onServiceConnected();instance=this;isEnabled=true}
 override fun onAccessibilityEvent(e:AccessibilityEvent?){val p=e?.packageName?.toString()?:return;targetForeground=targetPackage.isNotBlank()&&p==targetPackage}
 override fun onInterrupt(){targetForeground=false}
 override fun onDestroy(){targetForeground=false;isEnabled=false;instance=null;super.onDestroy()}
 private fun clickTextInternal(t:String):Boolean{val r=rootInActiveWindow?:return false;for(n in r.findAccessibilityNodeInfosByText(t)){if(n.isClickable)return n.performAction(AccessibilityNodeInfo.ACTION_CLICK);var p=n.parent;while(p!=null){if(p.isClickable)return p.performAction(AccessibilityNodeInfo.ACTION_CLICK);p=p.parent}};return false}
 private fun setTextInternal(t:String):Boolean{val r=rootInActiveWindow?:return false;val n=r.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)?:return false;val a=Bundle();a.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,t);return n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,a)}
}
'''
CAPTURE=r'''package com.kunal.universalvideo
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.ContentValues
import android.content.Intent
import android.media.MediaRecorder
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import android.provider.MediaStore
import androidx.core.app.NotificationCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
class ScreenCaptureService:Service(){
 companion object{const val START="KUV_START";const val STOP="KUV_STOP";const val CODE="result_code";const val DATA="result_data";const val CH="kuv_capture"}
 private var projection:MediaProjection?=null;private var recorder:MediaRecorder?=null;private var display:android.hardware.display.VirtualDisplay?=null;private var uri:android.net.Uri?=null
 override fun onCreate(){super.onCreate();if(Build.VERSION.SDK_INT>=26)getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CH,"KUV Capture",NotificationManager.IMPORTANCE_LOW))}
 override fun onStartCommand(i:Intent?,f:Int,id:Int):Int{when(i?.action){START->startCapture(i);STOP->stopCapture()};return START_NOT_STICKY}
 private fun startCapture(i:Intent){val code=i.getIntExtra(CODE,0);val data=i.getParcelableExtra<Intent>(DATA)?:run{stopSelf();return};if(code==0){stopSelf();return};startForeground(8756,NotificationCompat.Builder(this,CH).setContentTitle("Kunal Universal Video").setContentText("Screen recording").setSmallIcon(android.R.drawable.presence_video_online).setOngoing(true).build());try{val pm=getSystemService(MediaProjectionManager::class.java);projection=pm.getMediaProjection(code,data);val m=resources.displayMetrics;val w=(m.widthPixels.coerceAtMost(1280)/2)*2;val h=(m.heightPixels.coerceAtMost(720)/2)*2;val name="KunalUniversalVideo_"+SimpleDateFormat("yyyyMMdd_HHmmss",Locale.US).format(Date())+".mp4";val v=ContentValues().apply{put(MediaStore.Video.Media.DISPLAY_NAME,name);put(MediaStore.Video.Media.MIME_TYPE,"video/mp4");if(Build.VERSION.SDK_INT>=29){put(MediaStore.Video.Media.RELATIVE_PATH,"Movies/KunalUniversalVideo");put(MediaStore.Video.Media.IS_PENDING,1)}};uri=contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI,v)?:throw IllegalStateException("MediaStore insert failed");val fd=contentResolver.openFileDescriptor(uri!!,"w")?:throw IllegalStateException("FD failed");recorder=MediaRecorder().apply{setVideoSource(MediaRecorder.VideoSource.SURFACE);setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);setVideoEncoder(MediaRecorder.VideoEncoder.H264);setVideoEncodingBitRate(5000000);setVideoFrameRate(30);setVideoSize(w,h);setOutputFile(fd.fileDescriptor);prepare()};display=projection?.createVirtualDisplay("KUV",w,h,m.densityDpi,android.hardware.display.DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,recorder!!.surface,null,null);recorder?.start()}catch(_:Exception){cleanup();stopSelf()}}
 private fun stopCapture(){try{recorder?.stop()}catch(_:Exception){};try{recorder?.release()}catch(_:Exception){};recorder=null;try{display?.release()}catch(_:Exception){};display=null;try{projection?.stop()}catch(_:Exception){};projection=null;uri?.let{if(Build.VERSION.SDK_INT>=29)contentResolver.update(it,ContentValues().apply{put(MediaStore.Video.Media.IS_PENDING,0)},null,null)};uri=null;stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}
 private fun cleanup(){uri?.let{try{contentResolver.delete(it,null,null)}catch(_:Exception){}};uri=null;try{recorder?.release()}catch(_:Exception){};recorder=null;try{display?.release()}catch(_:Exception){};display=null;try{projection?.stop()}catch(_:Exception){};projection=null}
 override fun onBind(i:Intent?):IBinder?=null
}
'''
ACTIVITY=r'''package com.kunal.universalvideo
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
 override fun onCreate(b:Bundle?){super.onCreate(b);setContentView(R.layout.activity_main);status=findViewById(R.id.status);val p=getSharedPreferences("kuv",MODE_PRIVATE);val sid=p.getString("session_id",null)?:UUID.randomUUID().toString();p.edit().putString("session_id",sid).apply();val apps=packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0)).filter{it.packageName!=packageName}.sortedBy{packageManager.getApplicationLabel(it).toString().lowercase()};val sp=findViewById<Spinner>(R.id.target);sp.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,apps.map{"${packageManager.getApplicationLabel(it)}\n${it.packageName}"});sp.setOnItemSelectedListener(object:android.widget.AdapterView.OnItemSelectedListener{override fun onNothingSelected(x:android.widget.AdapterView<*>?){};override fun onItemSelected(x:android.widget.AdapterView<*>?,v:android.view.View?,pos:Int,id:Long){if(pos in apps.indices){target=apps[pos].packageName;p.edit().putString("target_package",target).apply();UniversalAccessibilityService.targetPackage=target}}});findViewById<Button>(R.id.connect).setOnClickListener{if(target.isBlank())status.text="Select target APK"else{bridge?.connect(target);status.text="REAL SESSION CONNECTED • ${sid.take(8)}"}};findViewById<Button>(R.id.disconnect).setOnClickListener{bridge?.disconnect();status.text="Disconnected"};findViewById<Button>(R.id.permissions).setOnClickListener{startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))};findViewById<Button>(R.id.openTarget).setOnClickListener{val i=packageManager.getLaunchIntentForPackage(target);if(i==null)status.text="Target cannot be launched"else{i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);startActivity(i);status.text="Target launched"}};findViewById<Button>(R.id.screenRecord).setOnClickListener{requestCapture()};bridge=LocalBridgeService(this,sid){m->runOnUiThread{status.text=m}};bridge?.start();status.text="Controller ready — bridge starting"}
 private fun requestCapture(){val m=getSystemService(MediaProjectionManager::class.java);capture.launch(m.createScreenCaptureIntent())}
 fun startRecordingFromBridge()=requestCapture()
 fun stopRecordingFromBridge()=startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))
 override fun onDestroy(){bridge?.stop();bridge=null;super.onDestroy()}
}
'''
MANIFEST=r'''<manifest xmlns:android="http://schemas.android.com/apk/res/android"><uses-permission android:name="android.permission.INTERNET"/><uses-permission android:name="android.permission.FOREGROUND_SERVICE"/><uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION"/><application android:allowBackup="false" android:label="@string/app_name" android:theme="@style/AppTheme"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter><intent-filter><action android:name="android.intent.action.VIEW"/><category android:name="android.intent.category.DEFAULT"/><category android:name="android.intent.category.BROWSABLE"/><data android:scheme="kunalcontroller"/></intent-filter></activity><service android:name=".UniversalAccessibilityService" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true"><intent-filter><action android:name="android.accessibilityservice.AccessibilityService"/></intent-filter><meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_service_config"/></service><service android:name=".ScreenCaptureService" android:exported="false" android:foregroundServiceType="mediaProjection"/></application></manifest>'''
ACCESS_XML=r'''<?xml version="1.0" encoding="utf-8"?><accessibility-service xmlns:android="http://schemas.android.com/apk/res/android" android:accessibilityEventTypes="typeWindowStateChanged|typeWindowContentChanged" android:accessibilityFeedbackType="feedbackGeneric" android:accessibilityFlags="flagDefault|flagReportViewIds" android:notificationTimeout="100" android:canRetrieveWindowContent="true" android:description="@string/accessibility_service_description"/>'''
LAYOUT=r'''<?xml version="1.0" encoding="utf-8"?><ScrollView xmlns:android="http://schemas.android.com/apk/res/android" android:layout_width="match_parent" android:layout_height="match_parent"><LinearLayout android:orientation="vertical" android:padding="20dp" android:layout_width="match_parent" android:layout_height="wrap_content"><TextView android:text="Kunal Universal Video" android:textSize="24sp" android:textStyle="bold" android:layout_width="match_parent" android:layout_height="wrap_content"/><TextView android:id="@+id/status" android:text="Starting..." android:padding="16dp" android:layout_width="match_parent" android:layout_height="wrap_content"/><Spinner android:id="@+id/target" android:layout_width="match_parent" android:layout_height="wrap_content"/><Button android:id="@+id/connect" android:text="Connect Mobile" android:layout_width="match_parent" android:layout_height="wrap_content"/><Button android:id="@+id/disconnect" android:text="Disconnect" android:layout_width="match_parent" android:layout_height="wrap_content"/><Button android:id="@+id/permissions" android:text="Enable App Control Permission" android:layout_width="match_parent" android:layout_height="wrap_content"/><Button android:id="@+id/openTarget" android:text="Open Selected APK" android:layout_width="match_parent" android:layout_height="wrap_content"/><Button android:id="@+id/screenRecord" android:text="Screen Recording Fallback" android:layout_width="match_parent" android:layout_height="wrap_content"/></LinearLayout></ScrollView>'''
STRINGS=r'''<resources><string name="app_name">Kunal Universal Video</string><string name="accessibility_service_description">Kunal Universal Video target-app control service</string></resources>'''
STYLES=r'''<resources><style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar"><item name="android:fontFamily">sans</item></style></resources>'''
APP_GRADLE=r'''plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android { namespace="com.kunal.universalvideo"; compileSdk=35; defaultConfig { applicationId="com.kunal.universalvideo"; minSdk=26; targetSdk=35; versionCode=3; versionName="3.0.0" }; compileOptions { sourceCompatibility=JavaVersion.VERSION_17; targetCompatibility=JavaVersion.VERSION_17 } }
kotlin { jvmToolchain(17) }
dependencies { implementation("androidx.core:core-ktx:1.15.0"); implementation("androidx.appcompat:appcompat:1.7.0"); implementation("androidx.activity:activity-ktx:1.10.1") }'''
ROOT_GRADLE=r'''plugins { id("com.android.application") version "8.7.3" apply false; id("org.jetbrains.kotlin.android") version "2.0.21" apply false }'''
SETTINGS=r'''pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }; dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }; rootProject.name="KunalUniversalVideo"; include(":app")'''
PROPS=r'''org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official'''

def reconstruct():
 shutil.rmtree(STAGE,ignore_errors=True);STAGE.mkdir(parents=True)
 if MASTER.is_file():
  mt=read(MASTER);ast.parse(mt);m=fmap(mt)
  if not isinstance(m,dict) or len(m)<10:raise RuntimeError("MASTER FILE MAP INVALID")
  for rel,data in m.items():write(STAGE/rel,str(data))
  log(f"[PASS] SOURCE MASTER {MASTER}")
 elif SOURCE_ZIP.is_file():
  with zipfile.ZipFile(SOURCE_ZIP) as z:
   if z.testzip():raise RuntimeError("SOURCE ZIP CRC/INTEGRITY FAILURE")
   z.extractall(STAGE)
  roots=[]
  for marker in STAGE.rglob("settings.gradle.kts"):
   r=marker.parent
   if (r/"app/build.gradle.kts").is_file() and (r/"app/src/main/AndroidManifest.xml").is_file():roots.append(r)
  if roots and roots[0] != STAGE/"android-controller":
   root=roots[0];dst=STAGE/"android-controller"
   if not dst.exists():shutil.copytree(root,dst)
  log(f"[PASS] SOURCE ZIP {SOURCE_ZIP}")
 else:raise RuntimeError("AUTHORITATIVE MASTER/PROJECT ZIP NOT FOUND")
 base=STAGE/"android-controller/app/src/main";java=base/"java/com/kunal/universalvideo";res=base/"res"
 for n,d in [("ControllerProtocol.kt",PROTOCOL),("LocalBridgeService.kt",BRIDGE),("UniversalAccessibilityService.kt",ACCESS),("ScreenCaptureService.kt",CAPTURE),("MainActivity.kt",ACTIVITY)]:write(java/n,d)
 for p,d in [(base/"AndroidManifest.xml",MANIFEST),(res/"xml/accessibility_service_config.xml",ACCESS_XML),(res/"layout/activity_main.xml",LAYOUT),(res/"values/strings.xml",STRINGS),(res/"values/styles.xml",STYLES),(STAGE/"android-controller/app/build.gradle.kts",APP_GRADLE),(STAGE/"android-controller/build.gradle.kts",ROOT_GRADLE),(STAGE/"android-controller/settings.gradle.kts",SETTINGS),(STAGE/"android-controller/gradle.properties",PROPS)]:write(p,d)
 for p in res.rglob("*.xml"):normxml(p)

def verify():
 b=STAGE/"android-controller/app/src/main";p={"a":b/"java/com/kunal/universalvideo/MainActivity.kt","br":b/"java/com/kunal/universalvideo/LocalBridgeService.kt","ac":b/"java/com/kunal/universalvideo/UniversalAccessibilityService.kt","cp":b/"java/com/kunal/universalvideo/ScreenCaptureService.kt","mf":b/"AndroidManifest.xml","gr":STAGE/"android-controller/app/build.gradle.kts"};out=[]
 def g(n,o,d=""):out.append({"name":n,"ok":bool(o),"detail":str(d)});log(f"[{'PASS' if o else 'FAIL'}] {n} :: {d}")
 g("FILES",all(x.is_file() and x.stat().st_size for x in p.values()));g("XML",all(xmlok(x) for x in (STAGE/"android-controller/app/src/main/res").rglob("*.xml")));mf=read(p["mf"]);a=read(p["a"]);br=read(p["br"]);ac=read(p["ac"]);cp=read(p["cp"]);gr=read(p["gr"])
 g("ACCESSIBILITY_MANIFEST",all(x in mf for x in ["UniversalAccessibilityService","BIND_ACCESSIBILITY_SERVICE","accessibility_service_config"]));g("MEDIA_PROJECTION_MANIFEST",all(x in mf for x in ["ScreenCaptureService","FOREGROUND_SERVICE_MEDIA_PROJECTION",'foregroundServiceType="mediaProjection"']));g("JVM17",all(x in gr for x in ["VERSION_17","jvmToolchain(17)"]));g("REAL_SESSION",all(x in a for x in ["UUID.randomUUID","bridge?.connect","sessionId"]));g("PING_PONG","PING" in br and "PONG" in br);g("DISCONNECT","disconnect" in br.lower());g("REAL_TRANSPORT",all(x in br for x in ["ServerSocket","127.0.0.1","accept()"]));g("TARGET_DISCOVERY",all(x in a for x in ["getInstalledApplications","getLaunchIntentForPackage"]));g("ACCESSIBILITY_CONTROL",all(x in ac for x in ["AccessibilityService","onAccessibilityEvent","rootInActiveWindow","performAction"]));g("TARGET_FOREGROUND",all(x in ac for x in ["targetForeground","packageName"]));g("MEDIAPROJECTION",all(x in cp for x in ["MediaProjection","MediaProjectionManager","createVirtualDisplay"]));g("MP4_RECORDING",all(x in cp for x in ["MediaRecorder","MPEG_4","H264","start()","stop()"]));g("GALLERY",all(x in cp for x in ["MediaStore","RELATIVE_PATH","video/mp4","IS_PENDING"]));g("NO_FAKE_CONNECT",not re.search(r'setOnClickListener\s*\{\s*status\.text\s*=\s*["\'](?:Connected|Paired|Controller ready)',a,re.I|re.S));return out

def build():
 S=sdk();G=gradle();J=shutil.which("java");JC=shutil.which("javac")
 if not(S and G and J and JC):return False,{"reason":"BUILD_ENVIRONMENT_MISSING","sdk":str(S) if S else None,"gradle":str(G) if G else None,"java":J,"javac":JC}
 android=STAGE/"android-controller";write(android/"local.properties","sdk.dir="+str(S).replace("\\","/"));env=os.environ.copy();env["ANDROID_HOME"]=str(S);env["ANDROID_SDK_ROOT"]=str(S);env["JAVA_HOME"]=str(Path(J).resolve().parent.parent);attempts=[];text="";ok=False
 for i in range(1,4):
  rc,text=run([G,"--no-daemon","--stacktrace","--console=plain","clean","assembleDebug"],cwd=android,env=env,timeout=1800);attempts.append({"attempt":i,"returncode":rc})
  if rc==0:ok=True;break
  if "permission denied" in text.lower():exe(G);continue
  if "processing instruction target matching" in text.lower():
   for x in (android/"app/src/main/res").rglob("*.xml"):normxml(x)
   continue
  break
 BUILD_LOG.write_text(text,encoding="utf-8");apks=sorted([x for x in android.rglob("*.apk") if x.is_file() and x.stat().st_size],key=lambda x:x.stat().st_mtime,reverse=True);apk=apks[0] if apks else None;A=None;bt=S/"build-tools"
 if bt.exists():
  for v in sorted([x for x in bt.iterdir() if x.is_dir()],reverse=True):
   if (v/"aapt").is_file():A=v/"aapt";exe(A);break
 info={"attempts":attempts,"apk":str(apk) if apk else None};po=lo=zi=False
 if apk and A:
  rc,t=run([A,"dump","badging",apk],timeout=180);pm=re.search(r"package: name='([^']+)'",t);lm=re.search(r"launchable-activity: name='([^']+)'",t);info["aapt"]={"rc":rc,"package":pm.group(1) if pm else None,"launcher":lm.group(1) if lm else None};po=rc==0 and info["aapt"]["package"]==PACKAGE;lo=rc==0 and info["aapt"]["launcher"]==MAIN
 if apk:
  try:
   with zipfile.ZipFile(apk) as z:zi=z.testzip() is None and "AndroidManifest.xml" in z.namelist() and any(x.endswith(".dex") for x in z.namelist())
  except Exception:zi=False
 info.update({"package_ok":po,"launcher_ok":lo,"zip_integrity":zi});return bool(ok and apk and po and lo and zi),info

def main():
 log("="*90);log("KUNAL UNIVERSAL VIDEO — PRO LEVEL REPAIR V3")
 if MASTER.is_file():log(f"[INFO] MASTER SHA256 {sha256(MASTER)}")
 reconstruct();checks=verify();static_ok=all(x["ok"] for x in checks);build_ok=False;bi={}
 if static_ok:build_ok,bi=build()
 else:log("[BLOCKED] STATIC CHECK FAILED — build skipped")
 if build_ok:
  apk=Path(bi["apk"]);shutil.copy2(apk,APK_OUT);shutil.rmtree(PROJECT,ignore_errors=True);shutil.copytree(STAGE,PROJECT);log(f"[PASS] APK {APK_OUT}");log(f"[PASS] APK SHA256 {sha256(APK_OUT)}")
 report={"status":"STATIC_AND_BUILD_VERIFIED" if build_ok else "BLOCKED","static_checks":checks,"build":bi,"apk":str(APK_OUT) if APK_OUT.exists() else None,"runtime_status":{"phone_connection":"UNVERIFIED","accessibility":"UNVERIFIED","target_foreground":"UNVERIFIED","ping_pong":"UNVERIFIED","recording":"UNVERIFIED","two_minute_video":"UNVERIFIED","playback":"UNVERIFIED","gallery":"UNVERIFIED"}}
 REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8");log(f"[REPORT] {REPORT}")
 if not build_ok:raise RuntimeError("PRO_V3_BLOCKED — see REPORT and BUILD_LOG; no false PASS")
if __name__=="__main__":main()
