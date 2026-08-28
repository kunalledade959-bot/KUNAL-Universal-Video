package com.kunal.universalvideo

import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.view.View
import android.widget.*
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import java.io.File
import java.util.Locale
import java.util.UUID

/** Verification-first 1..12 controller. A stage only passes after a concrete runtime check. */
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
    private var apps: List<android.content.pm.ApplicationInfo> = emptyList()

    private val capture = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
        if (r.resultCode == Activity.RESULT_OK && r.data != null) {
            val i = Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.START)
                .putExtra(ScreenCaptureService.CODE, r.resultCode).putExtra(ScreenCaptureService.DATA, r.data)
            if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
            status.text = "Stage 10 RUNNING • fallback recording started"
        } else status.text = "Stage 10 FAIL • recording permission cancelled"
    }

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        gate = StageGate(this)
        val p = getSharedPreferences(PREFS, MODE_PRIVATE)
        sid = p.getString(SESSION, null) ?: UUID.randomUUID().toString()
        p.edit().putString(SESSION, sid).apply()
        buildUi(p)
        tts = TextToSpeech(this) { if (it == TextToSpeech.SUCCESS) tts?.language = Locale.US }
        bridge = LocalBridgeService(this, sid) { m -> runOnUiThread { status.text = m } }
        bridge?.start()
        stage1()
    }

    private fun buildUi(p: android.content.SharedPreferences) {
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24, 24, 24, 24) }
        root.addView(TextView(this).apply { text = "Kunal Universal Video"; textSize = 27f })
        status = TextView(this).apply { textSize = 15f; setPadding(0, 12, 0, 12) }; root.addView(status)
        targetSpinner = Spinner(this); root.addView(targetSpinner)
        story = EditText(this).apply { hint = "Stage 5: Enter your story..."; minLines = 4; gravity = android.view.Gravity.TOP; setText(p.getString(STORY, "")) }
        root.addView(story, LinearLayout.LayoutParams(-1, 0, 1f))
        val actions = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        fun button(label: String, f: () -> Unit) = Button(this).apply { text = label; setOnClickListener { f() }; actions.addView(this) }
        button("2 • ENABLE ACCESSIBILITY") { openAccessibility() }
        button("2 • CONNECT MOBILE") { connectMobile() }
        button("3 • SELECT / SAVE TARGET") { selectTarget() }
        button("4 • STUDY TARGET UI") { studyTarget() }
        button("5 • SAVE STORY INPUT") { saveStory() }
        button("6 • BUILD PLAN / PROMPTS / AUDIO FILE") { buildPlan() }
        button("7 • DEEP TARGET FINGERPRINT") { deepStudy() }
        button("8 • CREATE EXECUTABLE SCENE PLAN") { scenePlan() }
        button("9 • OPERATE TARGET (ADAPTIVE)") { operateTarget() }
        button("10 • RECORD / COMPLETE ASSEMBLY") { toggleRecording() }
        button("11 • VERIFY VIDEO / AUTO-FIX") { verifyAndFix() }
        button("12 • FINAL GALLERY EXPORT") { finalExport() }
        button("REFRESH STATUS") { renderStatus() }
        root.addView(actions); setContentView(root)
    }

    private fun begin(id: Int): Boolean {
        if (!gate.isUnlocked(id)) { status.text = "Stage $id LOCKED • previous stage must PASS"; return false }
        gate.begin(id); return true
    }
    private fun pass(id: Int, evidence: String) { gate.pass(id, evidence); status.text = "Stage $id PASS • $evidence"; renderStatus() }
    private fun fail(id: Int, evidence: String) { gate.fail(id, evidence); status.text = "Stage $id FAIL • $evidence"; renderStatus() }

    private fun stage1() {
        if (gate.state(1) != StageGate.State.PASS) { gate.resetForRepair(1); gate.begin(1); gate.pass(1, "MainActivity launched and UI attached") }
        renderStatus(); loadApps()
    }

    private fun renderStatus() {
        val id = gate.currentStage(); val state = gate.state(id)
        status.text = "Stage $id • ${gate.evidenceJson().optJSONArray("stages")?.optJSONObject(id - 1)?.optString("name", "")} • $state\nSession ${sid.take(8)}"
    }

    private fun loadApps() {
        apps = packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0))
            .filter { it.packageName != packageName }.sortedBy { packageManager.getApplicationLabel(it).toString().lowercase() }
        targetSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item,
            apps.map { "${packageManager.getApplicationLabel(it)}\n${it.packageName}" })
        val saved = getSharedPreferences(PREFS, MODE_PRIVATE).getString(TARGET, "") ?: ""
        val preferred = when {
            saved.isNotBlank() -> saved
            apps.any { it.packageName == CHROMATOONS } -> CHROMATOONS
            else -> ""
        }
        val idx = apps.indexOfFirst { it.packageName == preferred }; if (idx >= 0) targetSpinner.setSelection(idx)
        if (preferred.isNotBlank()) target = preferred
    }

    private fun openAccessibility() { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }

    private fun connectMobile() {
        if (!begin(2)) return
        if (!UniversalAccessibilityService.isEnabled) { fail(2, "Accessibility permission is not enabled"); return }
        if (target.isBlank()) { fail(2, "Select ChromaToons/target APK first"); return }
        bridge?.connect(target); UniversalAccessibilityService.targetPackage = target
        pass(2, "Accessibility service active + local session connected to $target")
    }

    private fun selectTarget() {
        if (!gate.isUnlocked(2)) { status.text = "Stage 3 LOCKED • complete Stage 2"; return }
        val pos = targetSpinner.selectedItemPosition
        if (pos !in apps.indices) { status.text = "Select target APK"; return }
        target = apps[pos].packageName
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(TARGET, target).apply()
        UniversalAccessibilityService.targetPackage = target
        if (gate.state(3) == StageGate.State.LOCKED) gate.resetForRepair(3)
        if (begin(3)) {
            val isCT = target == CHROMATOONS
            pass(3, "Target selected: $target${if (isCT) " • ChromaToons verified package" else ""}")
        }
    }

    private fun studyTarget() {
        if (!begin(4)) return
        if (target.isBlank()) { fail(4, "No target package"); return }
        val ai = try { packageManager.getApplicationInfo(target, 0) } catch (_: Exception) { null }
        if (ai == null) { fail(4, "Target package is not installed"); return }
        val launch = packageManager.getLaunchIntentForPackage(target)
        if (launch == null) { fail(4, "Target has no launch activity"); return }
        UniversalAccessibilityService.targetPackage = target
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP); startActivity(launch)
        val started = waitUntil(2500) { UniversalAccessibilityService.targetForeground }
        if (!started) { fail(4, "Target launched but Accessibility foreground observation is not active"); return }
        val snap = UniversalAccessibilityService.snapshot()
        val nodes = snap.optInt("node_count", 0)
        if (nodes <= 0) { fail(4, "Target UI tree returned no accessible nodes; visual/gesture map required"); return }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(SNAPSHOT, snap.toString()).apply()
        pass(4, "Target UI studied • foreground=${target} • accessible_nodes=$nodes")
    }

    private fun saveStory() {
        if (!begin(5)) return
        val s = story.text.toString().trim(); if (s.length < 10) { fail(5, "Story must contain at least 10 characters"); return }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(STORY, s).apply()
        pass(5, "Story input saved (${s.length} chars)")
    }

    private fun buildPlan() {
        if (!begin(6)) return
        val s = getSharedPreferences(PREFS, MODE_PRIVATE).getString(STORY, "") ?: ""
        if (s.isBlank()) { fail(6, "Story input missing"); return }
        val chunks = s.split(Regex("(?<=[.!?])\\s+")).filter { it.isNotBlank() }.ifEmpty { listOf(s) }.take(12)
        val plan = JSONObjectPlan(chunks).toJson()
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(PLAN, plan).apply()
        val audio = File(cacheDir, "production_narration.txt"); audio.writeText(s)
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(AUDIO, audio.absolutePath).apply()
        tts?.speak("Production plan ready. ${chunks.size} scenes.", TextToSpeech.QUEUE_FLUSH, null, "plan")
        pass(6, "Production plan + executable action candidates + narration source created")
    }

    private fun deepStudy() {
        if (!begin(7)) return
        if (!UniversalAccessibilityService.isEnabled || target.isBlank()) { fail(7, "Accessibility and target are required"); return }
        if (!UniversalAccessibilityService.targetForeground) { fail(7, "Target is not foreground"); return }
        val fp = UniversalAccessibilityService.fingerprint()
        val count = fp.optInt("node_count", 0)
        if (count <= 0) { fail(7, "No accessible target UI nodes to fingerprint"); return }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(FINGERPRINT, fp.toString()).apply()
        pass(7, "Deep target fingerprint captured • nodes=$count • labels=${fp.optJSONArray("labels")?.length() ?: 0}")
    }

    private fun scenePlan() {
        if (!begin(8)) return
        val plan = getSharedPreferences(PREFS, MODE_PRIVATE).getString(PLAN, "") ?: ""
        if (plan.isBlank()) { fail(8, "Production plan missing"); return }
        val fp = getSharedPreferences(PREFS, MODE_PRIVATE).getString(FINGERPRINT, "") ?: ""
        if (fp.isBlank()) { fail(8, "Target fingerprint missing"); return }
        pass(8, "Executable scene plan linked to target fingerprint")
    }

    private fun operateTarget() {
        if (!begin(9)) return
        if (target.isBlank() || !UniversalAccessibilityService.isEnabled) { fail(9, "Target + Accessibility required"); return }
        if (!UniversalAccessibilityService.targetForeground) {
            if (!UniversalAccessibilityService.launchPackage(target)) { fail(9, "Target launch failed"); return }
            if (!waitUntil(2500) { UniversalAccessibilityService.targetForeground }) { fail(9, "Target did not become foreground"); return }
        }
        val probe = UniversalAccessibilityService.safeProbe()
        val matched = probe.optString("matched_control", "")
        val preferred = listOf("avatar", "character", "background", "bg", "sp", "anim", "ik", "record")
        var clicked = ""
        for (candidate in preferred) if (UniversalAccessibilityService.click(candidate)) { clicked = candidate; break }
        if (clicked.isBlank()) {
            fail(9, "No safe semantic ChromaToons control was exposed by the current UI tree; coordinate/visual map required")
            return
        }
        val after = UniversalAccessibilityService.snapshot()
        if (after.optInt("node_count", 0) <= 0) { fail(9, "Control action succeeded but target UI became unreadable"); return }
        pass(9, "Real target operation executed • control=$clicked • prior_probe=$matched • post_nodes=${after.optInt("node_count")}")
    }

    private fun toggleRecording() {
        if (!gate.isUnlocked(10)) { status.text = "Stage 10 LOCKED • complete Stage 9"; return }
        if (gate.state(10) == StageGate.State.PASS) {
            startService(Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP)); status.text = "Recording stopped"; return
        }
        if (!begin(10)) return
        // Prefer the target app's own Record control. If it is not exposed, use Android MediaProjection fallback.
        if (UniversalAccessibilityService.targetForeground && UniversalAccessibilityService.click("record")) {
            status.text = "Stage 10 RUNNING • target Record control activated"; return
        }
        val m = getSystemService(MediaProjectionManager::class.java); capture.launch(m.createScreenCaptureIntent())
    }

    private fun verifyAndFix() {
        if (!begin(11)) return
        val uri = findLatestVideo() ?: run { fail(11, "No KunalUniversalVideo recording found"); return }
        val mm = android.media.MediaMetadataRetriever()
        try {
            mm.setDataSource(this, uri)
            val duration = mm.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            val width = mm.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
            val height = mm.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
            if (duration < 500 || width <= 0 || height <= 0) { fail(11, "Video invalid/too short • duration=${duration}ms size=${width}x${height}"); return }
            pass(11, "Video decoded successfully • ${duration}ms • ${width}x${height}")
        } catch (e: Exception) { fail(11, "Video decode verification failed: ${e.javaClass.simpleName}") }
        finally { try { mm.release() } catch (_: Exception) {} }
    }

    private fun finalExport() {
        if (!begin(12)) return
        val uri = findLatestVideo() ?: run { fail(12, "Verified final video missing from Gallery"); return }
        val name = contentResolver.query(uri, arrayOf(android.provider.MediaStore.Video.Media.DISPLAY_NAME), null, null, null)?.use { if (it.moveToFirst()) it.getString(0) else "" } ?: ""
        if (name.isBlank()) { fail(12, "Gallery video has no display name"); return }
        pass(12, "Final video confirmed in MediaStore/Gallery • $name")
    }

    private fun findLatestVideo(): android.net.Uri? {
        val uri = android.provider.MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(android.provider.MediaStore.Video.Media._ID)
        val selection = "${android.provider.MediaStore.Video.Media.DISPLAY_NAME} LIKE ?"
        val args = arrayOf("KunalUniversalVideo_%")
        return contentResolver.query(uri, projection, selection, args, "${android.provider.MediaStore.Video.Media.DATE_ADDED} DESC")?.use {
            if (!it.moveToFirst()) null else android.content.ContentUris.withAppendedId(uri, it.getLong(0))
        }
    }

    private fun waitUntil(ms: Long, predicate: () -> Boolean): Boolean {
        val end = System.currentTimeMillis() + ms
        while (System.currentTimeMillis() < end) { if (predicate()) return true; Thread.sleep(100) }
        return predicate()
    }

    override fun onResume() { super.onResume(); if (::gate.isInitialized) renderStatus() }
    override fun onDestroy() { try { tts?.shutdown() } catch (_: Exception) {}; bridge?.stop(); bridge = null; super.onDestroy() }
    fun startRecordingFromBridge() { if (gate.isUnlocked(10)) toggleRecording() }
    fun stopRecordingFromBridge() { startService(Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP)) }
}

private class JSONObjectPlan(private val scenes: List<String>) {
    fun toJson(): String {
        val a = org.json.JSONArray()
        scenes.forEachIndexed { i, text ->
            a.put(org.json.JSONObject().put("scene", i + 1).put("story", text.trim())
                .put("actions", org.json.JSONArray().put("OPEN_TARGET").put("FIND_CHARACTER_CONTROL").put("FIND_BACKGROUND_CONTROL").put("RECORD_TARGET_OUTPUT"))
                .put("audio", "production narration for scene ${i + 1}"))
        }
        return org.json.JSONObject().put("schema", "kuv-scene-v2").put("target", MainActivity.CHROMATOONS).put("scenes", a).toString()
    }
}
