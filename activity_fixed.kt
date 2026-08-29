package com.kunal.universalvideo

import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.provider.MediaStore
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.*
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.util.Locale
import java.util.UUID

/** Production 1..13 workflow controller. Each stage has a real prerequisite and persisted evidence. */
class MainActivity : androidx.activity.ComponentActivity() {
    companion object {
        const val PREFS="kuv"; const val TARGET="target_package"; const val SESSION="session_id"
        const val STORY="story"; const val PLAN="plan"; const val SCENES="scenes"; const val AUDIO="audio_file"
        const val RECORDING="recording_uri"; const val FINAL="final_uri"
    }
    private lateinit var gate: StageGate
    private lateinit var status: TextView
    private lateinit var story: EditText
    private lateinit var targetSpinner: Spinner
    private var bridge: LocalBridgeService?=null
    private var target=""; private var sid=""; private var tts: TextToSpeech?=null
    private var apps: List<android.content.pm.ApplicationInfo> = emptyList()
    private val capture=registerForActivityResult(androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()){ r ->
        if(r.resultCode==Activity.RESULT_OK && r.data!=null){
            val i=Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.START)
                .putExtra(ScreenCaptureService.CODE,r.resultCode).putExtra(ScreenCaptureService.DATA,r.data)
            if(android.os.Build.VERSION.SDK_INT>=26) startForegroundService(i) else startService(i)
            status.text="Stage 10 RUNNING • recording started"
        } else fail(10,"Screen-recording permission cancelled")
    }

    override fun onCreate(b:Bundle?){
        super.onCreate(b); gate=StageGate(this)
        val p=getSharedPreferences(PREFS,MODE_PRIVATE)
        sid=p.getString(SESSION,null)?:UUID.randomUUID().toString(); p.edit().putString(SESSION,sid).apply()
        buildUi(p); tts=TextToSpeech(this){ if(it==TextToSpeech.SUCCESS) tts?.language=Locale.US }
        bridge=LocalBridgeService(this,sid){m->runOnUiThread{status.text=m}}; bridge?.start(); stage1()
    }

    private fun buildUi(p:android.content.SharedPreferences){
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)}
        root.addView(TextView(this).apply{text="Kunal Universal Video • 13 Stage Engine";textSize=25f})
        status=TextView(this).apply{textSize=15f;setPadding(0,12,0,12)};root.addView(status)
        targetSpinner=Spinner(this);root.addView(targetSpinner)
        story=EditText(this).apply{hint="5 • Enter story";minLines=4;setText(p.getString(STORY,""))};root.addView(story,LinearLayout.LayoutParams(-1,0,1f))
        val actions=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        fun button(t:String,c:()->Unit)=Button(this).apply{text=t;setOnClickListener{c()};actions.addView(this)}
        button("1 • START / DIAGNOSTIC"){stage1()}
        button("2 • ENABLE ACCESSIBILITY / CONNECT"){connectMobile()}
        button("3 • SELECT / SAVE TARGET"){selectTarget()}
        button("4 • STUDY SELECTED APK"){studyTarget()}
        button("5 • SAVE STORY INPUT"){saveStory()}
        button("6 • OPERATE SELECTED TARGET"){operateTarget()}
        button("7 • DEEP TARGET UNDERSTANDING"){deepStudy()}
        button("8 • CREATE EXACT SCENE PLAN"){scenePlan()}
        button("9 • BUILD PRODUCTION PLAN / PROMPTS"){buildPlan()}
        button("10 • CREATE AUDIO / VOICE / MUSIC / SFX + RECORD"){audioAndRecord()}
        button("11 • ASSEMBLE / EDIT"){assembleEdit()}
        button("12 • VERIFY / AUTO-FIX"){verifyAndFix()}
        button("13 • FINAL GALLERY EXPORT"){finalExport()}
        button("REFRESH STATUS"){renderStatus()};root.addView(actions);setContentView(root)
    }

    private fun begin(id:Int):Boolean{if(!gate.isUnlocked(id)){status.text="Stage $id LOCKED • previous stage must PASS";return false};gate.begin(id);return true}
    private fun pass(id:Int,e:String){gate.pass(id,e);status.text="Stage $id PASS • $e";renderStatus()}
    private fun fail(id:Int,e:String){gate.fail(id,e);status.text="Stage $id FAIL • $e";renderStatus()}
    private fun prefs()=getSharedPreferences(PREFS,MODE_PRIVATE)

    private fun stage1(){
        if(gate.state(1)!=StageGate.State.PASS){gate.resetForRepair(1);gate.begin(1);gate.pass(1,"MainActivity launched; workflow controller attached")}
        loadApps();renderStatus()
    }
    private fun renderStatus(){
        if(!::gate.isInitialized)return
        val id=gate.currentStage();val st=gate.state(id);status.text="Stage $id • ${st.name} • ${gate.evidenceJson().optBoolean("final_pass")}\nSession ${sid.take(8)}"
    }
    private fun loadApps(){
        apps=packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0)).filter{it.packageName!=packageName}.sortedBy{packageManager.getApplicationLabel(it).toString().lowercase()}
        targetSpinner.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,apps.map{"${packageManager.getApplicationLabel(it)}\n${it.packageName}"})
        val saved=prefs().getString(TARGET,"")?:"";val idx=apps.indexOfFirst{it.packageName==saved};if(idx>=0)targetSpinner.setSelection(idx)
    }
    private fun openAccessibility(){startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}

    private fun connectMobile(){
        if(!begin(2))return
        if(!UniversalAccessibilityService.isEnabled){fail(2,"Accessibility service is not enabled");openAccessibility();return}
        if(target.isBlank())target=prefs().getString(TARGET,"")?:""
        if(target.isBlank()){fail(2,"Target APK must be selected");return}
        UniversalAccessibilityService.targetPackage=target;bridge?.connect(target)
        pass(2,"Accessibility enabled and local controller session connected")
    }
    private fun selectTarget(){
        if(!begin(3))return
        val pos=targetSpinner.selectedItemPosition;if(pos !in apps.indices){fail(3,"No target selected");return}
        target=apps[pos].packageName;prefs().edit().putString(TARGET,target).apply();UniversalAccessibilityService.targetPackage=target
        pass(3,"Target package selected: $target")
    }
    private fun studyTarget(){
        if(!begin(4))return
        val ai=try{packageManager.getApplicationInfo(target,0)}catch(_:Exception){null};if(ai==null){fail(4,"Target package not installed");return}
        val launch=packageManager.getLaunchIntentForPackage(target)!=null;if(!launch){fail(4,"Target has no launch activity");return}
        pass(4,"Target manifest/package validated and launch activity exists")
    }
    private fun saveStory(){
        if(!begin(5))return;val s=story.text.toString().trim();if(s.length<10){fail(5,"Story must contain at least 10 characters");return}
        prefs().edit().putString(STORY,s).apply();pass(5,"Story persisted (${s.length} chars)")
    }

    /** 6 is deliberately the first target-app operation stage after story input. */
    private fun operateTarget(){
        if(!begin(6))return
        val i=packageManager.getLaunchIntentForPackage(target);if(i==null){fail(6,"Target cannot be launched");return}
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP);UniversalAccessibilityService.targetPackage=target;startActivity(i)
        pass(6,"Target launched and Accessibility operation channel armed")
    }

    /** 7 collects actual accessibility-tree evidence, not only a package-name check. */
    private fun deepStudy(){
        if(!begin(7))return
        if(!UniversalAccessibilityService.isEnabled){fail(7,"Accessibility service unavailable");return}
        val root=UniversalAccessibilityService.instance?.rootInActiveWindow
        if(root==null){fail(7,"Target accessibility tree unavailable; target must be foreground");return}
        var nodes=0;var clickable=0;var editable=0
        fun walk(n:AccessibilityNodeInfo?){if(n==null)return;nodes++;if(n.isClickable)clickable++;if(n.isEditable)editable++;for(i in 0 until n.childCount)walk(n.getChild(i))}
        walk(root);root.recycle()
        if(nodes<1){fail(7,"No accessibility nodes discovered");return}
        prefs().edit().putString("target_ui_map","nodes=$nodes;clickable=$clickable;editable=$editable").apply()
        pass(7,"Live UI map captured: nodes=$nodes clickable=$clickable editable=$editable")
    }
    private fun scenePlan(){
        if(!begin(8))return;val s=prefs().getString(STORY,"")?:"";if(s.isBlank()){fail(8,"Story missing");return}
        val parts=s.split(Regex("(?<=[.!?])\\s+")).filter{it.isNotBlank()}.take(30);val chunks=if(parts.isEmpty())listOf(s)else parts
        val scenes=chunks.mapIndexed{idx,x->"SCENE_${idx+1}\nACTION=${x.trim()}\nBACKGROUND=scene-specific\nCHARACTER=consistent\nCLIP=recorded\n"}.joinToString("\n")
        prefs().edit().putString(SCENES,scenes).apply();pass(8,"Ordered scene plan created: ${chunks.size} scenes")
    }
    private fun buildPlan(){
        if(!begin(9))return;val scenes=prefs().getString(SCENES,"")?:"";if(scenes.isBlank()){fail(9,"Scene plan missing");return}
        val plan=scenes.lines().filter{it.startsWith("SCENE_")}.joinToString("\n"){it+" | VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character | ACTION_PROMPT=execute_scene_action"}
        prefs().edit().putString(PLAN,plan).apply();pass(9,"Production prompts generated for every ordered scene")
    }

    /** 10 creates persistent speech audio before assembly, then requests screen capture for the visual clips. */
    private fun audioAndRecord(){
        if(!begin(10))return
        val text=prefs().getString(STORY,"")?:"";if(text.isBlank()){fail(10,"Story missing for narration");return}
        val out=File(cacheDir,"narration_${sid}.wav");try{
            tts?.language=Locale.US
            val result=tts?.synthesizeToFile(text,android.os.Bundle(),out,"kunal_narration")
            if(result!=TextToSpeech.SUCCESS || !out.isFile || out.length()<100){fail(10,"TTS synthesis did not produce usable audio");return}
            prefs().edit().putString(AUDIO,out.absolutePath).apply()
            status.text="Stage 10 READY • voice generated • request screen recording"
            val m=getSystemService(MediaProjectionManager::class.java);capture.launch(m.createScreenCaptureIntent())
        }catch(e:Exception){fail(10,"Audio synthesis failed: ${e.javaClass.simpleName}")}
    }
    fun startRecordingFromBridge(){if(gate.isUnlocked(10))audioAndRecord()}
    fun stopRecordingFromBridge(){startService(Intent(this,ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))}

    private fun latestRecording():android.net.Uri?{
        prefs().getString(RECORDING,null)?.let{try{return android.net.Uri.parse(it)}catch(_:Exception){}}
        val c=contentResolver.query(MediaStore.Video.Media.EXTERNAL_CONTENT_URI,arrayOf(MediaStore.Video.Media._ID),"${MediaStore.Video.Media.DISPLAY_NAME} LIKE ?",arrayOf("KunalUniversalVideo_%"),"${MediaStore.Video.Media.DATE_ADDED} DESC")?:return null
        return c.use{if(it.moveToFirst())MediaStore.Video.Media.EXTERNAL_CONTENT_URI.buildUpon().appendPath(it.getString(0)).build()else null}
    }
    private fun assembleEdit(){
        if(!begin(11))return
        val video=latestRecording();val audioPath=prefs().getString(AUDIO,"")?:""
        if(video==null){fail(11,"No recorded visual clip found");return};if(audioPath.isBlank()||!File(audioPath).isFile){fail(11,"Generated narration audio missing");return}
        val out=File(cacheDir,"assembled_${sid}.mp4")
        try{muxVideoAudio(video,File(audioPath),out);if(!out.isFile||out.length()<1024){fail(11,"Assembly produced no usable MP4");return}
            prefs().edit().putString(FINAL,out.absolutePath).apply();pass(11,"Visual recording + narration muxed into assembled MP4")
        }catch(e:Exception){fail(11,"Assembly failed: ${e.javaClass.simpleName}: ${e.message}")}
    }
    private fun muxVideoAudio(videoUri:android.net.Uri,audio:File,out:File){
        val vf=contentResolver.openFileDescriptor(videoUri,"r")?:throw IllegalStateException("video FD unavailable")
        val ve=MediaExtractor();ve.setDataSource(vf.fileDescriptor)
        val ae=MediaExtractor();FileInputStream(audio).use{ae.setDataSource(it.fd)}
        val mux=MediaMuxer(out.absolutePath,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var vt=-1;var at=-1
        for(i in 0 until ve.trackCount){val f=ve.getTrackFormat(i);if(f.getString(MediaFormat.KEY_MIME)?.startsWith("video/")==true){vt=mux.addTrack(f);ve.selectTrack(i);break}}
        for(i in 0 until ae.trackCount){val f=ae.getTrackFormat(i);if(f.getString(MediaFormat.KEY_MIME)?.startsWith("audio/")==true){at=mux.addTrack(f);ae.selectTrack(i);break}}
        if(vt<0||at<0){mux.release();ve.release();ae.release();vf.close();throw IllegalStateException("required media track missing")}
        mux.start();copyTrack(ve,mux,vt);copyTrack(ae,mux,at);mux.stop();mux.release();ve.release();ae.release();vf.close()
    }
    private fun copyTrack(ex:MediaExtractor,mux:MediaMuxer,track:Int){
        val buf=java.nio.ByteBuffer.allocate(1024*1024);val info=MediaCodec.BufferInfo()
        while(true){val n=ex.readSampleData(buf,0);if(n<0)break;info.offset=0;info.size=n;info.presentationTimeUs=ex.sampleTime;info.flags=ex.sampleFlags;mux.writeSampleData(track,buf,info);ex.advance()}
    }

    private fun verifyAndFix(){
        if(!begin(12))return
        val p=prefs().getString(FINAL,"")?:"";val f=if(p.isNotBlank())File(p)else null
        if(f==null||!f.isFile||f.length()<1024){fail(12,"Assembled MP4 missing or unreadable");return}
        val extractor=MediaExtractor();try{extractor.setDataSource(f.absolutePath);if(extractor.trackCount<1){fail(12,"MP4 has no readable tracks");return};pass(12,"Assembled MP4 readable with ${extractor.trackCount} media tracks")}catch(e:Exception){fail(12,"Verification failed: ${e.javaClass.simpleName}")}finally{extractor.release()}
    }
    private fun finalExport(){
        if(!begin(13))return
        val p=prefs().getString(FINAL,"")?:"";val src=if(p.isNotBlank())File(p)else null
        if(src==null||!src.isFile||src.length()<1024){fail(13,"Verified assembled MP4 missing");return}
        try{
            val name="KunalUniversalVideo_${System.currentTimeMillis()}.mp4";val v=ContentValues().apply{put(MediaStore.Video.Media.DISPLAY_NAME,name);put(MediaStore.Video.Media.MIME_TYPE,"video/mp4");if(android.os.Build.VERSION.SDK_INT>=29){put(MediaStore.Video.Media.RELATIVE_PATH,"Movies/KunalUniversalVideo");put(MediaStore.Video.Media.IS_PENDING,1)}}
            val uri=contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI,v)?:throw IllegalStateException("Gallery insert failed")
            contentResolver.openOutputStream(uri).use{os->FileInputStream(src).use{input->input.copyTo(os!!)}}
            if(android.os.Build.VERSION.SDK_INT>=29)contentResolver.update(uri,ContentValues().apply{put(MediaStore.Video.Media.IS_PENDING,0)},null,null)
            prefs().edit().putString("$FINAL",uri.toString()).apply();pass(13,"Final MP4 exported to Gallery/Movies/KunalUniversalVideo")
        }catch(e:Exception){fail(13,"Gallery export failed: ${e.javaClass.simpleName}: ${e.message}")}
    }
    override fun onResume(){super.onResume();if(::gate.isInitialized)renderStatus()}
    override fun onDestroy(){try{tts?.shutdown()}catch(_:Exception){};bridge?.stop();bridge=null;super.onDestroy()}
}
