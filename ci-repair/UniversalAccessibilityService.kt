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
        var targetPackage = ""

        @Volatile
        var targetForeground = false

        @Volatile
        var isEnabled = false

        fun launchPackage(c: Context, p: String): Boolean {
            val i = c.packageManager.getLaunchIntentForPackage(p) ?: return false
            i.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_CLEAR_TOP
            )
            c.startActivity(i)
            return true
        }

        fun clickText(t: String) =
            instance?.clickTextInternal(t) ?: false

        fun setFocusedText(t: String) =
            instance?.setTextInternal(t) ?: false
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        isEnabled = true
    }

    override fun onAccessibilityEvent(e: AccessibilityEvent?) {
        val p = e?.packageName?.toString() ?: return

        targetForeground =
            targetPackage.isNotBlank() && p == targetPackage

        runCatching {
            TargetGuideManager.captureUiEvidence(
                applicationContext,
                rootInActiveWindow
            )
        }

        runCatching {
            AutonomousWorkflowLearner.discover(
                applicationContext,
                p,
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

    private fun clickTextInternal(t: String): Boolean {
        val r = rootInActiveWindow ?: return false

        for (n in r.findAccessibilityNodeInfosByText(t)) {
            if (n.isClickable) {
                return n.performAction(
                    AccessibilityNodeInfo.ACTION_CLICK
                )
            }

            var p = n.parent
            while (p != null) {
                if (p.isClickable) {
                    return p.performAction(
                        AccessibilityNodeInfo.ACTION_CLICK
                    )
                }

                p = p.parent
            }
        }

        return false
    }

    private fun setTextInternal(t: String): Boolean {
        val r = rootInActiveWindow ?: return false

        val n = r.findFocus(
            AccessibilityNodeInfo.FOCUS_INPUT
        ) ?: return false

        val a = Bundle()
        a.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            t
        )

        return n.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            a
        )
    }
}
