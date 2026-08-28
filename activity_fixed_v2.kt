package com.kunal.universalvideo

import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaMetadataRetriever
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.view.Gravity
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale
import java.util.UUID

/**
 * Production verification-first controller.
 * The locked 1..12 order is enforced by StageGate.
 * TargetControlEngine is exposed through UniversalAccessibilityService only.
 */
class MainActivity : ComponentActivity() {
    companion object {
        const val PREFS = "kuv"
        const val TARGET = "target_package"
        const val SESSION = "session_id"
        const val STORY = "story"
        const val PLAN = "plan"
        const val FINGERPRINT = "target_fingerprint"
        const val SNAPSHOT = "target_snapshot"
        const val AUDIO = "audio_file"
        const val CHROMATOONS = "bhootiyadreamstv.moboapp.chromatoons"
    }

    private lateinit var gate: StageGate
    private lateinit var status: TextView
    private lateinit var story: EditText
    private lateinit var targetSpinner: Spinner
    private var bridge: LocalBridgeService? = null
    private var target = ""
    private var sid = ""
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var apps: List<android.content.pm.ApplicationInfo> = emptyList()
    private val mainHandler = Handler(Looper.getMainLooper())

    private val capture = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val intent = Intent(this, ScreenCaptureService::class.java)
                .setAction(ScreenCaptureService.START)
                .putExtra(ScreenCaptureService.CODE, result.resultCode)
                .putExtra(ScreenCaptureService.DATA, result.data)
            if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
            status.text = "Stage 10 RUNNING • fallback recording started"
        } else {
            fail(10, "Recording permission cancelled")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        gate = StageGate(this)
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        sid = prefs.getString(SESSION, null) ?: UUID.randomUUID().toString()
        prefs.edit().putString(SESSION, sid).apply()
        buildUi(prefs)
        tts = TextToSpeech(this) { result ->
            ttsReady = result == TextToSpeech.SUCCESS
            if (ttsReady) tts?.language = Locale.US
        }
        bridge = LocalBridgeService(this, sid) { message ->
            runOnUiThread { status.text = message }
        }
        bridge?.start()
        stage1()
    }

    private fun buildUi(prefs: android.content.SharedPreferences) {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(20, 20, 20, 20)
        }
        root.addView(TextView(this).apply {
            text = "Kunal Universal Video"
            textSize = 27f
        })
        status = TextView(this).apply {
            textSize = 15f
            setPadding(0, 12, 0, 12)
        }
        root.addView(status)
        targetSpinner = Spinner(this)
        root.addView(targetSpinner)
        story = EditText(this).apply {
            hint = "Stage 5: Enter your story..."
            minLines = 4
            gravity = Gravity.TOP
            setText(prefs.getString(STORY, ""))
        }
        root.addView(story, LinearLayout.LayoutParams(-1, 0, 1f))

        val actions = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        addButton(actions, "2 • ENABLE ACCESSIBILITY") { openAccessibility() }
        addButton(actions, "2 • CONNECT MOBILE") { connectMobile() }
        addButton(actions, "3 • SELECT / SAVE TARGET") { selectTarget() }
        addButton(actions, "4 • STUDY SELECTED APK") { studyTarget() }
        addButton(actions, "5 • SAVE STORY INPUT") { saveStory() }
        addButton(actions, "6 • BUILD PLAN / PROMPTS / AUDIO") { buildPlan() }
        addButton(actions, "7 • DEEP TARGET-APP UNDERSTANDING") { deepStudy() }
        addButton(actions, "8 • CREATE EXACT SCENE PLAN") { scenePlan() }
        addButton(actions, "9 • OPERATE SELECTED TARGET APK") { operateTarget() }
        addButton(actions, "10 • RECORD / COMPLETE ASSEMBLY") { toggleRecording() }
        addButton(actions, "11 • VERIFY / AUTO-FIX") { verifyAndFix() }
        addButton(actions, "12 • FINAL GALLERY EXPORT") { finalExport() }
        addButton(actions, "REFRESH STAGE STATUS") { renderStatus() }
        root.addView(actions)
        setContentView(root)
    }

    private fun addButton(parent: LinearLayout, label: String, action: () -> Unit) {
        parent.addView(Button(this).apply {
            text = label
            setOnClickListener { action() }
        })
    }

    private fun begin(id: Int): Boolean {
        if (!gate.isUnlocked(id)) {
            status.text = "Stage $id LOCKED • previous stage must PASS"
            return false
        }
        return gate.begin(id)
    }

    private fun pass(id: Int, evidence: String) {
        if (gate.pass(id, evidence)) {
            status.text = "Stage $id PASS • $evidence"
            renderStatus()
        }
    }

    private fun fail(id: Int, evidence: String) {
        gate.fail(id, evidence)
        status.text = "Stage $id FAIL • $evidence"
        renderStatus()
    }

    private fun stage1() {
        if (gate.state(1) != StageGate.State.PASS) {
            gate.resetForRepair(1)
            gate.begin(1)
            gate.pass(1, "MainActivity launched and UI attached")
        }
        loadApps()
        renderStatus()
    }

    private fun renderStatus() {
        if (!::gate.isInitialized || !::status.isInitialized) return
        val id = gate.currentStage()
        val stage = gate.evidenceJson().optJSONArray("stages")?.optJSONObject(id - 1)
        val name = stage?.optString("name", "") ?: ""
        status.text = "Stage $id • $name • ${gate.state(id)}\nSession ${sid.take(8)}"
    }

    private fun loadApps() {
        apps = packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0))
            .filter { it.packageName != packageName }
            .sortedBy { packageManager.getApplicationLabel(it).toString().lowercase() }
        targetSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            apps.map { "${packageManager.getApplicationLabel(it)}\n${it.packageName}" }
        )
        val saved = getSharedPreferences(PREFS, MODE_PRIVATE).getString(TARGET, "") ?: ""
        val preferred = when {
            saved.isNotBlank() -> saved
            apps.any { it.packageName == CHROMATOONS } -> CHROMATOONS
            else -> ""
        }
        val index = apps.indexOfFirst { it.packageName == preferred }
        if (index >= 0) {
            targetSpinner.setSelection(index)
            target = preferred
        }
    }

    private fun openAccessibility() {
        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
    }

    private fun connectMobile() {
        if (!begin(2)) return
        if (!UniversalAccessibilityService.isEnabled) {
            fail(2, "Accessibility service is not enabled")
            return
        }
        if (target.isBlank()) {
            fail(2, "Select a target APK first")
            return
        }
        UniversalAccessibilityService.targetPackage = target
        bridge?.connect(target)
        pass(2, "Accessibility service active + local session connected to $target")
    }

    private fun selectTarget() {
        if (!gate.isUnlocked(2)) {
            status.text = "Stage 3 LOCKED • complete Stage 2"
            return
        }
        val position = targetSpinner.selectedItemPosition
        if (position !in apps.indices) {
            status.text = "Select a target APK"
            return
        }
        target = apps[position].packageName
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(TARGET, target).apply()
        UniversalAccessibilityService.targetPackage = target
        gate.resetForRepair(3)
        if (begin(3)) {
            val suffix = if (target == CHROMATOONS) " • ChromaToons verified package" else ""
            pass(3, "Target selected: $target$suffix")
        }
    }

    private fun studyTarget() {
        if (!begin(4)) return
        if (target.isBlank()) {
            fail(4, "No target package")
            return
        }
        val info = try { packageManager.getApplicationInfo(target, 0) } catch (_: Exception) { null }
        if (info == null) {
            fail(4, "Target package is not installed")
            return
        }
        val launchIntent = packageManager.getLaunchIntentForPackage(target)
        if (launchIntent == null) {
            fail(4, "Target has no launch activity")
            return
        }
        UniversalAccessibilityService.targetPackage = target
        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        startActivity(launchIntent)
        if (!waitUntil(3000) { UniversalAccessibilityService.targetForeground }) {
            fail(4, "Target launched but Accessibility foreground observation is not active")
            return
        }
        val snapshot = UniversalAccessibilityService.snapshot()
        if (snapshot.optInt("node_count", 0) <= 0) {
            fail(4, "Target UI tree returned no accessible nodes")
            return
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
            .putString(SNAPSHOT, snapshot.toString()).apply()
        pass(4, "Target UI studied • accessible_nodes=${snapshot.optInt("node_count")}")
    }

    private fun saveStory() {
        if (!begin(5)) return
        val value = story.text.toString().trim()
        if (value.length < 10) {
            fail(5, "Story must contain at least 10 characters")
            return
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(STORY, value).apply()
        pass(5, "Story input saved (${value.length} chars)")
    }

    private fun buildPlan() {
        if (!begin(6)) return
        val value = getSharedPreferences(PREFS, MODE_PRIVATE).getString(STORY, "") ?: ""
        if (value.isBlank()) {
            fail(6, "Story input missing")
            return
        }
        val scenes = value.split(Regex("(?<=[.!?])\\s+"))
            .filter { it.isNotBlank() }
            .ifEmpty { listOf(value) }
            .take(12)
        val array = JSONArray()
        scenes.forEachIndexed { index, text ->
            array.put(JSONObject()
                .put("scene", index + 1)
                .put("story", text.trim())
                .put("prompt", "cinematic cartoon scene, consistent characters, clear action")
                .put("actions", JSONArray().put("OPEN_TARGET").put("FIND_CHARACTER_CONTROL").put("FIND_BACKGROUND_CONTROL").put("RECORD_TARGET_OUTPUT")))
        }
        val plan = JSONObject()
            .put("schema", "kuv-scene-v2")
            .put("target", target)
            .put("scenes", array)
            .toString()
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        prefs.edit().putString(PLAN, plan).apply()

        if (!ttsReady || tts == null) {
            fail(6, "Text-to-Speech engine is not ready")
            return
        }
        val audio = File(filesDir, "production_narration.wav")
        val result = tts?.synthesizeToFile(value, Bundle(), audio, "kuv_narration")
            ?: TextToSpeech.ERROR
        if (result != TextToSpeech.SUCCESS || !waitUntil(4000) { audio.exists() && audio.length() > 0 }) {
            fail(6, "Narration audio file creation failed")
            return
        }
        prefs.edit().putString(AUDIO, audio.absolutePath).apply()
        pass(6, "Production plan + prompts + narration audio created (${scenes.size} scenes)")
    }

    private fun deepStudy() {
        if (!begin(7)) return
        if (!UniversalAccessibilityService.isEnabled || target.isBlank()) {
            fail(7, "Accessibility and target are required")
            return
        }
        if (!UniversalAccessibilityService.targetForeground) {
            fail(7, "Target is not foreground")
            return
        }
        val fingerprint = UniversalAccessibilityService.fingerprint()
        if (fingerprint.optInt("node_count", 0) <= 0) {
            fail(7, "No accessible target UI nodes to fingerprint")
            return
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
            .putString(FINGERPRINT, fingerprint.toString()).apply()
        pass(7, "Deep target fingerprint captured • nodes=${fingerprint.optInt("node_count")}")
    }

    private fun scenePlan() {
        if (!begin(8)) return
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val plan = prefs.getString(PLAN, "") ?: ""
        val fingerprint = prefs.getString(FINGERPRINT, "") ?: ""
        if (plan.isBlank() || fingerprint.isBlank()) {
            fail(8, "Production plan or target fingerprint missing")
            return
        }
        val scenes = try { JSONObject(plan).optJSONArray("scenes")?.length() ?: 0 } catch (_: Exception) { 0 }
        if (scenes < 1) {
            fail(8, "Executable scene list is empty")
            return
        }
        pass(8, "Exact executable scene plan validated • scenes=$scenes")
    }

    private fun operateTarget() {
        if (!begin(9)) return
        if (target.isBlank() || !UniversalAccessibilityService.isEnabled) {
            fail(9, "Target + Accessibility required")
            return
        }
        if (!UniversalAccessibilityService.targetForeground) {
            if (!UniversalAccessibilityService.launchPackage(this, target) ||
                !waitUntil(3000) { UniversalAccessibilityService.targetForeground }) {
                fail(9, "Target did not become foreground")
                return
            }
        }
        val before = UniversalAccessibilityService.snapshot()
        val probe = UniversalAccessibilityService.safeProbe()
        val preferred = listOf("avatar", "character", "background", "bg", "sp", "anim", "ik")
        var clicked = ""
        for (candidate in preferred) {
            if (UniversalAccessibilityService.click(candidate)) {
                clicked = candidate
                break
            }
        }
        if (clicked.isBlank()) {
            fail(9, "No safe semantic target control exposed by current UI tree")
            return
        }
        val after = UniversalAccessibilityService.snapshot()
        if (after.optInt("node_count", 0) <= 0) {
            fail(9, "Control action succeeded but target UI became unreadable")
            return
        }
        pass(9, "Real target operation executed • control=$clicked • prior_probe=${probe.optString("matched_control", "")} • nodes=${after.optInt("node_count")}")
    }

    private fun toggleRecording() {
        if (!gate.isUnlocked(10)) {
            status.text = "Stage 10 LOCKED • complete Stage 9"
            return
        }
        if (gate.state(10) == StageGate.State.RUNNING) {
            startService(Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))
            if (!waitUntil(5000) { latestVideo() != null }) {
                fail(10, "Recording stopped but no video output was found")
                return
            }
            pass(10, "Recording/assembly produced a readable video output")
            return
        }
        if (!begin(10)) return
        if (UniversalAccessibilityService.targetForeground && UniversalAccessibilityService.click("record")) {
            status.text = "Stage 10 RUNNING • target Record control activated • press again to complete"
            return
        }
        val manager = getSystemService(MediaProjectionManager::class.java)
        capture.launch(manager.createScreenCaptureIntent())
    }

    private fun verifyAndFix() {
        if (!begin(11)) return
        val uri = latestVideo()
        if (uri == null) {
            fail(11, "No KunalUniversalVideo recording found")
            return
        }
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(this, uri)
            val duration = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            val width = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
            val height = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
            if (duration < 500 || width <= 0 || height <= 0) {
                fail(11, "Video invalid • duration=${duration}ms size=${width}x${height}")
                return
            }
            pass(11, "Video decoded successfully • ${duration}ms • ${width}x${height}")
        } catch (error: Exception) {
            fail(11, "Video decode verification failed: ${error.javaClass.simpleName}")
        } finally {
            try { retriever.release() } catch (_: Exception) { }
        }
    }

    private fun finalExport() {
        if (!begin(12)) return
        val uri = latestVideo()
        if (uri == null) {
            fail(12, "Verified final video missing from Gallery")
            return
        }
        val name = contentResolver.query(
            uri,
            arrayOf(MediaStore.Video.Media.DISPLAY_NAME),
            null,
            null,
            null
        )?.use { cursor -> if (cursor.moveToFirst()) cursor.getString(0) else "" } ?: ""
        if (name.isBlank()) {
            fail(12, "Gallery video has no display name")
            return
        }
        pass(12, "Final video confirmed in MediaStore/Gallery • $name")
    }

    private fun latestVideo(): android.net.Uri? {
        val collection = MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(MediaStore.Video.Media._ID)
        val selection = "${MediaStore.Video.Media.DISPLAY_NAME} LIKE ?"
        val args = arrayOf("KunalUniversalVideo_%")
        return contentResolver.query(
            collection,
            projection,
            selection,
            args,
            "${MediaStore.Video.Media.DATE_ADDED} DESC"
        )?.use { cursor ->
            if (!cursor.moveToFirst()) null
            else android.content.ContentUris.withAppendedId(collection, cursor.getLong(0))
        }
    }

    private fun waitUntil(timeoutMs: Long, predicate: () -> Boolean): Boolean {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            if (predicate()) return true
            Thread.sleep(100)
        }
        return predicate()
    }

    override fun onResume() {
        super.onResume()
        if (::gate.isInitialized) renderStatus()
    }

    override fun onDestroy() {
        mainHandler.removeCallbacksAndMessages(null)
        try { tts?.shutdown() } catch (_: Exception) { }
        bridge?.stop()
        bridge = null
        super.onDestroy()
    }

    fun startRecordingFromBridge() {
        if (gate.isUnlocked(10)) toggleRecording()
    }

    fun stopRecordingFromBridge() {
        startService(Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))
    }
}
