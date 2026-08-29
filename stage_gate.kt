package com.kunal.universalvideo

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Persistent, fail-closed 1..13 workflow gate. */
class StageGate(context: Context) {
    enum class State { LOCKED, READY, RUNNING, PASS, FAIL }
    data class Stage(val id: Int, val name: String, var state: State = State.LOCKED, var evidence: String = "")

    private val prefs = context.getSharedPreferences("kuv_stage_gate", Context.MODE_PRIVATE)
    private val stages = arrayOf(
        "Startup / Self-Diagnostic",
        "Mobile Connection / Permissions",
        "Target APK Selection",
        "Study Selected APK",
        "Story Input",
        "Operate Selected Target APK",
        "Deep Target-App Understanding",
        "Exact Scene Plan",
        "Production Plan / Prompts",
        "Audio / Voice / Music / Sound Effects",
        "Assemble / Edit",
        "Verify / Auto-Fix",
        "Final Gallery Export"
    ).mapIndexed { i, n -> Stage(i + 1, n) }.toMutableList()

    init { restore() }
    private fun valid(id: Int) = id in 1..13

    @Synchronized fun state(id: Int): State = if (valid(id)) stages[id - 1].state else State.LOCKED
    @Synchronized fun currentStage(): Int = stages.indexOfFirst { it.state != State.PASS }.let { if (it < 0) 13 else it + 1 }
    @Synchronized fun isUnlocked(id: Int): Boolean = valid(id) && (id == 1 || stages[id - 2].state == State.PASS)

    @Synchronized fun begin(id: Int): Boolean {
        if (!isUnlocked(id)) return false
        stages[id - 1].state = State.RUNNING
        persist()
        return true
    }

    @Synchronized fun pass(id: Int, evidence: String): Boolean {
        if (!valid(id) || stages[id - 1].state != State.RUNNING) return false
        stages[id - 1].state = State.PASS
        stages[id - 1].evidence = evidence
        if (id < 13) stages[id].state = State.READY
        persist()
        return true
    }

    @Synchronized fun fail(id: Int, evidence: String) {
        if (!valid(id)) return
        stages[id - 1].state = State.FAIL
        stages[id - 1].evidence = evidence
        if (id < 13) for (n in id + 1..13) { stages[n - 1].state = State.LOCKED; stages[n - 1].evidence = "" }
        persist()
    }

    @Synchronized fun resetForRepair(id: Int): Boolean {
        if (!valid(id)) return false
        if (id > 1 && stages[id - 2].state != State.PASS) return false
        stages[id - 1].state = State.READY
        stages[id - 1].evidence = ""
        persist()
        return true
    }

    @Synchronized fun evidenceJson(): JSONObject {
        val a = JSONArray()
        stages.forEach { a.put(JSONObject().put("stage", it.id).put("name", it.name).put("state", it.state.name).put("evidence", it.evidence)) }
        return JSONObject().put("current_stage", currentStage()).put("final_pass", stages.all { it.state == State.PASS }).put("stages", a)
    }

    private fun persist() { prefs.edit().putString("state", evidenceJson().toString()).apply() }

    private fun restore() {
        val raw = prefs.getString("state", null) ?: return
        try {
            val a = JSONObject(raw).getJSONArray("stages")
            for (i in 0 until minOf(13, a.length())) {
                val o = a.getJSONObject(i)
                stages[i].state = State.valueOf(o.optString("state", "LOCKED"))
                stages[i].evidence = o.optString("evidence", "")
            }
        } catch (_: Exception) {
            stages.forEach { it.state = State.LOCKED; it.evidence = "" }
        }
    }
}
