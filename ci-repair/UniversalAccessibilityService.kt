@file:Suppress("DEPRECATION")

package com.kunal.universalvideo

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicLong

/**
 * Runtime-safe accessibility controller.
 *
 * The accessibility callback is on the service's main thread, so expensive
 * evidence/learning work is rate-limited and moved to a single worker.
 */
class UniversalAccessibilityService : AccessibilityService() {

    companion object {
        @Volatile var instance: UniversalAccessibilityService? = null
        @Volatile var targetPackage: String = ""
        @Volatile var targetForeground: Boolean = false
        @Volatile var isEnabled: Boolean = false

        fun launchPackage(context: Context, packageName: String): Boolean {
            val intent = context.packageManager.getLaunchIntentForPackage(packageName)
                ?: return false
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            context.startActivity(intent)
            return true
        }

        fun clickText(text: String): Boolean = instance?.clickTextInternal(text) ?: false
        fun setFocusedText(text: String): Boolean = instance?.setTextInternal(text) ?: false
    }

    private val worker = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "KunalAccessibilityWorker").apply { isDaemon = true }
    }
    private val lastEvidenceAt = AtomicLong(0L)

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        isEnabled = true

        // Provider discovery is not part of service connection critical path.
        worker.execute {
            runCatching {
                AudioAssetIntelligence.discoverInstalledProviders(applicationContext)
            }
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        val target = targetPackage
        val isTarget = target.isNotBlank() && packageName == target
        targetForeground = isTarget

        // Do not inspect every system/launcher event. This was a major source
        // of startup pressure because the old implementation performed three
        // expensive operations for every accessibility event.
        if (!isTarget) return

        val now = SystemClock.uptimeMillis()
        val previous = lastEvidenceAt.get()
        if (now - previous < 300L || !lastEvidenceAt.compareAndSet(previous, now)) return

        val root = snapshotRoot() ?: return
        worker.execute {
            runCatching {
                TargetGuideManager.captureUiEvidence(applicationContext, root)
            }
            runCatching {
                AutonomousWorkflowLearner.discover(applicationContext, packageName, root)
            }
        }
    }

    private fun snapshotRoot(): AccessibilityNodeInfo? {
        val root = rootInActiveWindow ?: return null
        return AccessibilityNodeInfo.obtain(root)
    }

    override fun onInterrupt() {
        targetForeground = false
    }

    override fun onDestroy() {
        targetForeground = false
        isEnabled = false
        instance = null
        worker.shutdownNow()
        super.onDestroy()
    }

    private fun clickTextInternal(text: String): Boolean {
        val root = rootInActiveWindow ?: return false
        for (node in root.findAccessibilityNodeInfosByText(text)) {
            if (node.isClickable) return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            var parent = node.parent
            while (parent != null) {
                if (parent.isClickable) return parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                parent = parent.parent
            }
        }
        return false
    }

    private fun setTextInternal(text: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return false
        val arguments = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
        }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
    }
}
