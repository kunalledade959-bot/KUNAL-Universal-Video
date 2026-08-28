package com.kunal.universalvideo

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

/** Adaptive target-app controller. It learns the current accessibility tree before acting. */
object TargetControlEngine {
    private const val MAX_NODES = 500

    data class NodeRef(
        val text: String,
        val desc: String,
        val viewId: String,
        val cls: String,
        val clickable: Boolean,
        val editable: Boolean,
        val bounds: Rect
    )

    fun snapshot(service: AccessibilityService): JSONObject {
        val root = service.rootInActiveWindow
        val out = JSONArray()
        if (root != null) walk(root, out)
        return JSONObject().put("ok", root != null).put("package", root?.packageName?.toString() ?: "")
            .put("node_count", out.length()).put("nodes", out)
    }

    private fun walk(node: AccessibilityNodeInfo, out: JSONArray) {
        if (out.length() >= MAX_NODES) return
        val r = Rect(); node.getBoundsInScreen(r)
        out.put(JSONObject()
            .put("text", node.text?.toString() ?: "")
            .put("desc", node.contentDescription?.toString() ?: "")
            .put("view_id", node.viewIdResourceName ?: "")
            .put("class", node.className?.toString() ?: "")
            .put("clickable", node.isClickable)
            .put("editable", node.isEditable)
            .put("enabled", node.isEnabled)
            .put("visible", node.isVisibleToUser)
            .put("bounds", JSONObject().put("l", r.left).put("t", r.top).put("r", r.right).put("b", r.bottom)))
        for (i in 0 until node.childCount) node.getChild(i)?.let { child -> walk(child, out); child.recycle() }
    }

    fun fingerprint(service: AccessibilityService): JSONObject {
        val snap = snapshot(service)
        val labels = JSONArray()
        val nodes = snap.optJSONArray("nodes") ?: JSONArray()
        for (i in 0 until nodes.length()) {
            val n = nodes.getJSONObject(i)
            val label = listOf(n.optString("text"), n.optString("desc"), n.optString("view_id"))
                .firstOrNull { it.isNotBlank() } ?: continue
            labels.put(label)
        }
        return JSONObject().put("package", snap.optString("package"))
            .put("node_count", snap.optInt("node_count"))
            .put("labels", labels)
    }

    fun click(service: AccessibilityService, query: String): Boolean {
        val root = service.rootInActiveWindow ?: return false
        val q = query.trim().lowercase()
        return find(root) { n -> matches(n, q) }?.let { performClick(it) } ?: false
    }

    fun setText(service: AccessibilityService, query: String, value: String): Boolean {
        val root = service.rootInActiveWindow ?: return false
        val q = query.trim().lowercase()
        val node = find(root) { n -> matches(n, q) && n.isEditable } ?: find(root) { n -> n.isEditable }
            ?: return false
        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, value) }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    fun scroll(service: AccessibilityService, forward: Boolean): Boolean {
        val root = service.rootInActiveWindow ?: return false
        val node = find(root) { it.isScrollable } ?: return false
        return node.performAction(if (forward) AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
    }

    fun back(service: AccessibilityService): Boolean = service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK)

    fun tap(service: AccessibilityService, x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        return service.dispatchGesture(
            GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, 60)).build(),
            null, null
        )
    }

    fun safeProbe(service: AccessibilityService): JSONObject {
        val snap = snapshot(service)
        val nodes = snap.optJSONArray("nodes") ?: JSONArray()
        val preferred = listOf("add", "avatar", "character", "background", "bg", "sp", "record", "anim", "ik")
        var matched = ""
        for (key in preferred) {
            for (i in 0 until nodes.length()) {
                val n = nodes.getJSONObject(i)
                val label = (n.optString("text") + " " + n.optString("desc") + " " + n.optString("view_id")).lowercase()
                if (n.optBoolean("clickable") && label.contains(key)) { matched = key; break }
            }
            if (matched.isNotBlank()) break
        }
        return JSONObject().put("node_count", nodes.length()).put("matched_control", matched)
    }

    private fun matches(n: AccessibilityNodeInfo, q: String): Boolean {
        val all = listOf(n.text?.toString(), n.contentDescription?.toString(), n.viewIdResourceName, n.className?.toString())
            .filterNotNull().joinToString(" ").lowercase()
        return all.contains(q)
    }

    private fun find(node: AccessibilityNodeInfo, predicate: (AccessibilityNodeInfo) -> Boolean): AccessibilityNodeInfo? {
        if (predicate(node)) return node
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val hit = find(child, predicate)
            if (hit != null) return hit
            child.recycle()
        }
        return null
    }

    private fun performClick(node: AccessibilityNodeInfo): Boolean {
        if (node.isClickable && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
        var p = node.parent
        while (p != null) {
            if (p.isClickable && p.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            p = p.parent
        }
        val r = Rect(); node.getBoundsInScreen(r)
        val service = UniversalAccessibilityService.instance ?: return false
        return tap(service, r.centerX().toFloat(), r.centerY().toFloat())
    }
}
