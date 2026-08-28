package com.kunal.universalvideo

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

/**
 * Fail-closed scene operator for the validation branch.
 * It never claims a scene action succeeded merely because a click was dispatched.
 */
object SceneExecutionEngine {
    data class TargetControl(
        val key: String,
        val text: String,
        val description: String,
        val viewId: String,
        val bounds: Rect,
        val clickable: Boolean,
        val enabled: Boolean
    )

    fun discover(service: AccessibilityService): JSONObject {
        val root = service.rootInActiveWindow ?: return JSONObject()
            .put("ok", false).put("error", "NO_ACTIVE_WINDOW")
        val controls = JSONArray()
        walk(root, controls)
        return JSONObject()
            .put("ok", true)
            .put("package", root.packageName?.toString() ?: "")
            .put("control_count", controls.length())
            .put("controls", controls)
    }

    fun requireControl(service: AccessibilityService, aliases: List<String>): TargetControl? {
        val root = service.rootInActiveWindow ?: return null
        val wanted = aliases.map { normalize(it) }
        return find(root) { node ->
            if (!node.isVisibleToUser || !node.isEnabled) return@find false
            val values = listOf(node.text, node.contentDescription, node.viewIdResourceName)
                .filterNotNull().map { normalize(it.toString()) }
            values.any { value -> wanted.any { alias -> value == alias || value.contains(alias) } }
        }?.let { node ->
            val r = Rect(); node.getBoundsInScreen(r)
            TargetControl(
                key = wanted.firstOrNull() ?: "",
                text = node.text?.toString() ?: "",
                description = node.contentDescription?.toString() ?: "",
                viewId = node.viewIdResourceName ?: "",
                bounds = r,
                clickable = node.isClickable,
                enabled = node.isEnabled
            )
        }
    }

    fun clickAndVerify(service: AccessibilityService, aliases: List<String>, timeoutMs: Long = 2000): JSONObject {
        val before = discover(service)
        val control = requireControl(service, aliases)
            ?: return JSONObject().put("ok", false).put("error", "CONTROL_NOT_FOUND")
                .put("aliases", JSONArray(aliases))
        val root = service.rootInActiveWindow ?: return JSONObject().put("ok", false).put("error", "NO_ACTIVE_WINDOW")
        val node = find(root) { n ->
            n.text?.toString() == control.text &&
                n.contentDescription?.toString() == control.description &&
                (n.viewIdResourceName ?: "") == control.viewId
        } ?: return JSONObject().put("ok", false).put("error", "CONTROL_STALE")
        val dispatched = performClick(node, service)
        if (!dispatched) return JSONObject().put("ok", false).put("error", "ACTION_REJECTED")
        val deadline = System.currentTimeMillis() + timeoutMs
        var after = discover(service)
        while (System.currentTimeMillis() < deadline) {
            if (after.toString() != before.toString()) {
                return JSONObject().put("ok", true).put("dispatched", true)
                    .put("verified_change", true).put("control", controlJson(control))
                    .put("before", before).put("after", after)
            }
            Thread.sleep(100)
            after = discover(service)
        }
        return JSONObject().put("ok", false).put("error", "NO_OBSERVED_STATE_CHANGE")
            .put("dispatched", true).put("verified_change", false)
            .put("control", controlJson(control)).put("before", before).put("after", after)
    }

    private fun performClick(node: AccessibilityNodeInfo, service: AccessibilityService): Boolean {
        if (node.isClickable && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
        var parent = node.parent
        while (parent != null) {
            if (parent.isClickable && parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            parent = parent.parent
        }
        return false
    }

    private fun walk(node: AccessibilityNodeInfo, out: JSONArray) {
        if (out.length() >= 1000) return
        if (node.isVisibleToUser && node.isEnabled) {
            val r = Rect(); node.getBoundsInScreen(r)
            out.put(JSONObject()
                .put("text", node.text?.toString() ?: "")
                .put("description", node.contentDescription?.toString() ?: "")
                .put("view_id", node.viewIdResourceName ?: "")
                .put("class", node.className?.toString() ?: "")
                .put("clickable", node.isClickable)
                .put("editable", node.isEditable)
                .put("scrollable", node.isScrollable)
                .put("bounds", JSONObject().put("l", r.left).put("t", r.top).put("r", r.right).put("b", r.bottom)))
        }
        for (i in 0 until node.childCount) node.getChild(i)?.let { child -> walk(child, out); child.recycle() }
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

    private fun normalize(value: String): String = value.trim().lowercase().replace(Regex("\\s+"), " ")

    private fun controlJson(c: TargetControl) = JSONObject()
        .put("key", c.key).put("text", c.text).put("description", c.description)
        .put("view_id", c.viewId).put("clickable", c.clickable).put("enabled", c.enabled)
        .put("bounds", JSONObject().put("l", c.bounds.left).put("t", c.bounds.top).put("r", c.bounds.right).put("b", c.bounds.bottom))
}
