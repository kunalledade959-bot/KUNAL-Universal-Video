package com.kunal.universalvideo

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import java.util.UUID
import java.io.File

class MainActivity : AppCompatActivity() {

    fun saveFinishedVideoToGallery(videoPath:String, displayName:String="Kunal_Video") {
        val result=GalleryExporter.saveMp4(this,File(videoPath),displayName)
        status.text=if(result.ok) "Video saved to Gallery" else "Gallery save failed: ${result.message}"
    }


    companion object { const val PREFS = "kuv"; const val TARGET = "target_package"; const val SESSION = "session_id" }
    private lateinit var status: TextView
    private var bridge: LocalBridgeService? = null
    private var target = ""
    private var sessionId = ""

    private val captureLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val intent = Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.START)
                .putExtra(ScreenCaptureService.CODE, result.resultCode).putExtra(ScreenCaptureService.DATA, result.data)
            try {
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
                status.text = "Recording start requested"
            } catch (e: Exception) { status.text = "Recording start failed: ${e.message ?: e.javaClass.simpleName}" }
        } else status.text = "Recording permission cancelled"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        val capabilityAudit = CapabilityManager.audit(this)
        val missingRequired = capabilityAudit.filter { it.required && it.state != "GRANTED" && it.state != "CONFIGURED" }

        status = findViewById(R.id.status)
        if (missingRequired.isNotEmpty()) {
            status.text = "Setup required: " + missingRequired.joinToString(", ") { it.label }
        }
        val errorOverlay = findViewById<android.view.View>(R.id.errorOverlay)
        val errorDetails = findViewById<android.widget.TextView>(R.id.errorDetails)
        val repairCodeInput = findViewById<android.widget.EditText>(R.id.repairCodeInput)
        val repairCodeButton = findViewById<android.widget.Button>(R.id.repairCodeButton)
        val retryRepairButton = findViewById<android.widget.Button>(R.id.retryRepairButton)

        fun showRepairScreen(health: SelfRepairManager.Health) {
            errorOverlay.visibility = android.view.View.VISIBLE
            errorDetails.text = buildString {
                append("Self-check could not complete safely.\n\n")
                append("Issues:\n")
                health.issues.forEach { append("• ").append(it).append('\n') }
                if (health.repairedItems.isNotEmpty()) {
                    append("\nRepairs attempted:\n")
                    health.repairedItems.forEach { append("• ").append(it).append('\n') }
                }
                append("\nOnly predefined repair codes are accepted. Arbitrary code execution is disabled.")
            }
        }

        repairCodeButton.setOnClickListener {
            val result = SelfRepairManager.applyRepairCode(this, repairCodeInput.text?.toString().orEmpty())
            if (result.ok) {
                errorOverlay.visibility = android.view.View.GONE
                status.text = "Repair completed — self-check passed"
            } else {
                errorDetails.text = "REPAIR FAILED\n\n" +
                    result.issues.joinToString("\n") { "• $it" } +
                    "\n\nOnly predefined repair codes are supported."
            }
        }

        retryRepairButton.setOnClickListener {
            val result = SelfRepairManager.initialize(this)
            if (result.ok) {
                errorOverlay.visibility = android.view.View.GONE
                status.text = "Self-check passed"
            } else {
                showRepairScreen(result)
            }
        }


        // Capability checks run before normal operation; Android special-consent flows remain user-controlled.
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            CapabilityManager.requestNotifications(this)
        }
        val selfHeal = SelfRepairManager.initialize(this)
        if (selfHeal.ok) {
            status.text = if (selfHeal.repaired) {
                "Self-repair completed — controller starting"
            } else {
                "Self-check passed — controller starting"
            }
        } else {
            showRepairScreen(selfHeal)
        }
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        sessionId = prefs.getString(SESSION, null) ?: UUID.randomUUID().toString().also { prefs.edit().putString(SESSION, it).apply() }
        target = prefs.getString(TARGET, "") ?: ""
        UniversalAccessibilityService.targetPackage = target
        loadApps(prefs)

        findViewById<Button>(R.id.connect).setOnClickListener {
            val health = SelfRepairManager.initialize(this)
            if (!health.ok) {
                status.text = "Self-check blocked connect: ${health.issues.joinToString("; ")}"
            } else if (target.isBlank()) status.text = "Select target APK first"
            else if (bridge?.prepareTarget(target) == true) status.text = "Bridge ready: ${bridge?.localAddress()}:${LocalBridgeService.PORT} — pair with code ${bridge?.currentPairingCode()}"
            else status.text = "Selected target cannot be launched"
        }
        findViewById<Button>(R.id.disconnect).setOnClickListener { bridge?.disconnect(); status.text = "Disconnected" }
        findViewById<Button>(R.id.permissions).setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        findViewById<Button>(R.id.openTarget).setOnClickListener { if (target.isBlank()) status.text = "Select target APK first" else if (UniversalAccessibilityService.launchPackage(this, target)) status.text = "Target launched" else status.text = "Target cannot be launched" }
        findViewById<Button>(R.id.screenRecord).setOnClickListener { requestCapture() }
        findViewById<Button>(R.id.stopRecord).setOnClickListener { stopRecordingFromBridge() }

        bridge = BridgeHolder.start(this, sessionId) { message -> runOnUiThread { status.text = message } }
        try {
            val intent = Intent(this, ControllerBridgeForegroundService::class.java).setAction(ControllerBridgeForegroundService.START)
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
        } catch (e: Exception) {
            status.text = "Bridge foreground start failed: ${e.message ?: e.javaClass.simpleName}"
        }
        status.text = "Bridge started — waiting for pairing :${LocalBridgeService.PORT}"
        handleIntent(intent)
    }

    private fun loadApps(prefs: android.content.SharedPreferences) {
        val spinner = findViewById<Spinner>(R.id.target)
        val apps = packageManager.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0)
            .map { it.activityInfo.packageName }.filter { it != packageName }.distinct().sortedBy { label(it).lowercase() }
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, apps.map { "${label(it)}\n$it" })
        val saved = apps.indexOf(target)
        if (saved >= 0) spinner.setSelection(saved)
        spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                if (position in apps.indices) { target = apps[position]; prefs.edit().putString(TARGET, target).apply(); UniversalAccessibilityService.targetPackage = target; status.text = "Target selected: $target" }
            }
        }
    }
    private fun label(pkg: String): String = try { packageManager.getApplicationLabel(packageManager.getApplicationInfo(pkg, 0)).toString() } catch (_: Exception) { pkg }
    private fun handleIntent(intent: Intent?) { if (intent?.scheme == "kunalcontroller") status.text = "Connect request received — choose target, then pair from the controller UI" }
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); handleIntent(intent) }
    private fun requestCapture() { val manager = getSystemService(android.media.projection.MediaProjectionManager::class.java); captureLauncher.launch(manager.createScreenCaptureIntent()) }
    fun startRecordingFromBridge() { runOnUiThread { status.text = "Recording requires the phone's screen-capture permission" } }
    fun stopRecordingFromBridge() {
        if (ScreenCaptureService.stopCurrent()) status.text = "Stopping recording"
        else status.text = "No active recording session"
    }
    override fun onDestroy() {
        bridge = null
        super.onDestroy()
    }
}
