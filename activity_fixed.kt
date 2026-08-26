package com.kunal.universalvideo

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
    companion object { const val PREFS = "kuv"; const val TARGET = "target_package"; const val SESSION = "session_id" }
    private lateinit var status: TextView
    private var bridge: LocalBridgeService? = null
    private var target: String = ""
    private val capture = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val i = Intent(this, ScreenCaptureService::class.java)
                .setAction(ScreenCaptureService.START)
                .putExtra(ScreenCaptureService.CODE, result.resultCode)
                .putExtra(ScreenCaptureService.DATA, result.data)
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
            status.text = "Recording started"
        } else status.text = "Recording permission cancelled"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.status)
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val sid = prefs.getString(SESSION, null) ?: UUID.randomUUID().toString()
        prefs.edit().putString(SESSION, sid).apply()

        val apps = packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0))
            .filter { it.packageName != packageName }
            .sortedBy { packageManager.getApplicationLabel(it).toString().lowercase() }
        val spinner = findViewById<Spinner>(R.id.target)
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item,
            apps.map { "${packageManager.getApplicationLabel(it)}\n${it.packageName}" })
        spinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                if (position in apps.indices) {
                    target = apps[position].packageName
                    prefs.edit().putString(TARGET, target).apply()
                    UniversalAccessibilityService.targetPackage = target
                }
            }
        }
        findViewById<Button>(R.id.connect).setOnClickListener {
            if (target.isBlank()) status.text = "Select target APK"
            else { bridge?.connect(target); status.text = "REAL SESSION CONNECTED • ${sid.take(8)}" }
        }
        findViewById<Button>(R.id.disconnect).setOnClickListener { bridge?.disconnect(); status.text = "Disconnected" }
        findViewById<Button>(R.id.permissions).setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        findViewById<Button>(R.id.openTarget).setOnClickListener {
            val intent = packageManager.getLaunchIntentForPackage(target)
            if (intent == null) status.text = "Target cannot be launched"
            else { intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP); startActivity(intent); status.text = "Target launched" }
        }
        findViewById<Button>(R.id.screenRecord).setOnClickListener { requestCapture() }
        bridge = LocalBridgeService(this, sid) { message -> runOnUiThread { status.text = message } }
        bridge?.start()
        status.text = "Controller ready — bridge starting"
    }

    private fun requestCapture() {
        val manager = getSystemService(MediaProjectionManager::class.java)
        capture.launch(manager.createScreenCaptureIntent())
    }
    fun startRecordingFromBridge() = requestCapture()
    fun stopRecordingFromBridge() = startService(Intent(this, ScreenCaptureService::class.java).setAction(ScreenCaptureService.STOP))

    override fun onDestroy() {
        bridge?.stop()
        bridge = null
        super.onDestroy()
    }
}
