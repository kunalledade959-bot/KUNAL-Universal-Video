package com.kunal.universalvideo

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Persistent, fail-closed 1..12 stage gate. Later stages cannot unlock until the
 * immediately preceding stage has a recorded PASS. */
class StageGate(context: Context) {
    enum class State { LOCKED, READY, RUNNING, PASS, FAIL }
    data class Stage(val id: Int, val name: String, var state: State = State.LOCKED, var evidence: String = "")

    private val prefs = context.getSharedPreferences("kuv_stage_gate", Context.MODE_PRIVATE)
    private val stages = arrayOf(
        "Startup / Self-Diagnostic", "Mobile Connection / Permissions", "Target APK Selection",
        "Study Selected APK", "Story Input", "Production Plan / Prompts / Audio",
        "Deep Target-App Understanding", "Exact Scene Plan", "Operate Selected Target APK",
        "Assemble / Edit", "Verify / Auto-Fix", "Final Gallery Export"
    ).mapIndexed { i, n -> Stage(i + 1, n) }.toMutableList()

    init { restore() }

    @Synchronized fun state(id: Int): State = stages[id - 1].state
    @Synchronized fun currentStage(): Int = stages.indexOfFirst { it.state != State.PASS }.let { if (it < 0) 12 else it + 1 }
    @Synchronized fun isUnlocked(id: Int): Boolean = id == 1 || stages[id - 2].state == State.PASS

    @Synchronized fun begin(id: Int): Boolean {
        if (!isUnlocked(id)) return false
        stages[id - 1].state = State.RUNNING
        persist()
        return true
    }

    @Synchronized fun pass(id: Int, evidence: String): Boolean {
        if (id !in 1..12 || stages[id - 1].state != State.RUNNING) return false
        stages[id - 1].state = State.PASS
        stages[id - 1].evidence = evidence
        if (id < 12) stages[id].state = State.READY
        persist()
        return true
    }

    @Synchronized fun fail(id: Int, evidence: String) {
        if (id !in 1..12) return
        stages[id - 1].state = State.FAIL
        stages[id - 1].evidence = evidence
        for (n in id + 1..12) { stages[n - 1].state = State.LOCKED; stages[n - 1].evidence = "" }
        persist()
    }

    @Synchronized fun resetForRepair(id: Int): Boolean {
        if (id !in 1..12) return false
        if (id > 1 && stages[id - 2].state != State.PASS) return false
        stages[id - 1].state = State.READY
        persist()
        return true
    }

    @Synchronized fun evidenceJson(): JSONObject {
        val a = JSONArray()
        stages.forEach { a.put(JSONObject().put("stage", it.id).put("name", it.name).put("state", it.state.name).put("evidence", it.evidence)) }
        return JSONObject().put("current_stage", currentStage()).put("final_pass", stages.all { it.state == State.PASS }).put("stages", a)
    }

    private fun persist() {
        prefs.edit().putString("state", evidenceJson().toString()).apply()
    }
    private fun restore() {
        val raw = prefs.getString("state", null) ?: return
        try {
            val a = JSONObject(raw).getJSONArray("stages")
            for (i in 0 until minOf(12, a.length())) {
                val o = a.getJSONObject(i)
                stages[i].state = State.valueOf(o.optString("state", "LOCKED"))
                stages[i].evidence = o.optString("evidence", "")
            }
        } catch (_: Exception) {
            stages.forEach { it.state = State.LOCKED; it.evidence = "" }
        }
    }
}
