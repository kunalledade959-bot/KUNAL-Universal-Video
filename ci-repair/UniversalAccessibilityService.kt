package com.kunal.universalvideo

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class UniversalAccessibilityService : AccessibilityService() {

    companion object {
        @Volatile
        var instance: UniversalAccessibilityService? = null

        @Volatile
        var targetPackage: String = ""

        @Volatile
        var targetForeground: Boolean = false

        @Volatile
        var isEnabled: Boolean = false

        fun launchPackage(context: Context, packageName: String): Boolean {
            val intent = context.packageManager.getLaunchIntentForPackage(packageName)
                ?: return false
            intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP
            )
            context.startActivity(intent)
            return true
        }

        fun clickText(text: String): Boolean =
            instance?.clickTextInternal(text) ?: false

        fun setFocusedText(text: String): Boolean =
            instance?.setTextInternal(text) ?: false
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        isEnabled = true
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return

        targetForeground =
            targetPackage.isNotBlank() && packageName == targetPackage

        runCatching {
            TargetGuideManager.captureUiEvidence(
                applicationContext,
                rootInActiveWindow
            )
        }

        runCatching {
            AutonomousWorkflowLearner.discover(
                applicationContext,
                packageName,
                rootInActiveWindow
            )
        }

        runCatching {
            AudioAssetIntelligence.discoverInstalledProviders(
                applicationContext
            )
        }
    }

    override fun onInterrupt() {
        targetForeground = false
    }

    override fun onDestroy() {
        targetForeground = false
        isEnabled = false
        instance = null
        super.onDestroy()
    }

    private fun clickTextInternal(text: String): Boolean {
        val root = rootInActiveWindow ?: return false

        for (node in root.findAccessibilityNodeInfosByText(text)) {
            if (node.isClickable) {
                return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            }

            var parent = node.parent
            while (parent != null) {
                if (parent.isClickable) {
                    return parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                }
                parent = parent.parent
            }
        }

        return false
    }

    private fun setTextInternal(text: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return false

        val arguments = Bundle()
        arguments.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            text
        )

        return node.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            arguments
        )
    }
}
