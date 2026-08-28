package com.kunal.universalvideo

import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

/**
 * ChromaToons target adapter used only in the sequence-validation branch.
 * It never assumes a fixed coordinate. It resolves visible controls through
 * text/content-description/resource-id and records what was actually found.
 */
object ChromaToonsAdapter {
    const val PACKAGE = "bhootiyadreamstv.moboapp.chromatoons"

    data class NodeRef(
        val text: String,
        val description: String,
        val viewId: String,
        val clickable: Boolean,
        val enabled: Boolean,
        val className: String
    )

    fun isTargetForeground(): Boolean =
        UniversalAccessibilityService.targetPackage == PACKAGE &&
            UniversalAccessibilityService.targetForeground

    fun launch(): Boolean =
        UniversalAccessibilityService.instance?.let {
            UniversalAccessibilityService.launchPackage(it, PACKAGE)
        } ?: false

    fun snapshot(): JSONObject {
        val root = UniversalAccessibilityService.instance?.rootInActiveWindow
            ?: return JSONObject().put("ok", false).put("error", "NO_ACTIVE_WINDOW")
        val nodes = JSONArray()
        walk(root, nodes)
        return JSONObject()
            .put("ok", true)
            .put("package", root.packageName?.toString() ?: "")
            .put("nodes", nodes)
    }

    fun click(vararg labels: String): JSONObject {
        val root = UniversalAccessibilityService.instance?.rootInActiveWindow
            ?: return JSONObject().put("ok", false).put("error", "NO_ACTIVE_WINDOW")
        for (label in labels) {
            val nodes = root.findAccessibilityNodeInfosByText(label)
            for (n in nodes) {
                if (n.isEnabled && performClick(n)) {
                    return JSONObject().put("ok", true).put("matched", label)
                }
            }
        }
        return JSONObject().put("ok", false).put("error", "CONTROL_NOT_FOUND")
            .put("labels", JSONArray(labels.toList()))
    }

    fun setText(text: String): JSONObject {
        val ok = UniversalAccessibilityService.setFocusedText(text)
        return JSONObject().put("ok", ok).put("text_length", text.length)
    }

    fun execute(actions: JSONArray): JSONObject {
        val results = JSONArray()
        var all = true
        for (i in 0 until actions.length()) {
            val a = actions.optJSONObject(i) ?: continue
            when (a.optString("type")) {
                "click" -> {
                    val labels = a.optJSONArray("labels") ?: JSONArray()
                    val candidates = Array(labels.length()) { j -> labels.optString(j) }
                    val r = click(*candidates)
                    results.put(r)
                    all = all && r.optBoolean("ok")
                }
                "text" -> {
                    val r = setText(a.optString("value"))
                    results.put(r)
                    all = all && r.optBoolean("ok")
                }
                "wait" -> {
                    Thread.sleep(a.optLong("ms", 500).coerceIn(0, 5000))
                    results.put(JSONObject().put("ok", true).put("wait_ms", a.optLong("ms", 500)))
                }
                else -> {
                    results.put(JSONObject().put("ok", false).put("error", "UNKNOWN_ACTION"))
                    all = false
                }
            }
        }
        return JSONObject().put("ok", all).put("results", results)
    }

    private fun performClick(node: AccessibilityNodeInfo): Boolean {
        if (node.isClickable) return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        var p = node.parent
        while (p != null) {
            if (p.isEnabled && p.isClickable) return p.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            p = p.parent
        }
        return false
    }

    private fun walk(node: AccessibilityNodeInfo, out: JSONArray) {
        out.put(JSONObject()
            .put("text", node.text?.toString() ?: "")
            .put("description", node.contentDescription?.toString() ?: "")
            .put("view_id", node.viewIdResourceName ?: "")
            .put("clickable", node.isClickable)
            .put("enabled", node.isEnabled)
            .put("class", node.className?.toString() ?: ""))
        for (i in 0 until node.childCount) node.getChild(i)?.let { walk(it, out) }
    }
}
