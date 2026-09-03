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
        if (!valid(id) || !isUnlocked(id)) return false
        val current = stages[id - 1].state
        if (current == State.PASS || current == State.RUNNING || current == State.FAIL) return false
        if (id > 1 && current != State.READY) return false
        stages[id - 1].state = State.RUNNING
        persist()
        return true
    }

    @Synchronized fun pass(id: Int, evidence: String): Boolean {
        if (!valid(id) || stages[id - 1].state != State.RUNNING || evidence.isBlank()) return false
        stages[id - 1].state = State.PASS
        stages[id - 1].evidence = evidence
        if (id < 13) {
            stages[id].state = State.READY
            stages[id].evidence = ""
        }
        persist()
        return true
    }

    @Synchronized fun fail(id: Int, evidence: String) {
        if (!valid(id)) return
        stages[id - 1].state = State.FAIL
        stages[id - 1].evidence = evidence.ifBlank { "Stage failed without evidence" }
        if (id < 13) for (n in id + 1..13) {
            stages[n - 1].state = State.LOCKED
            stages[n - 1].evidence = ""
        }
        persist()
    }

    @Synchronized fun resetForRepair(id: Int): Boolean {
        if (!valid(id)) return false
        if (id > 1 && stages[id - 2].state != State.PASS) return false
        val current = stages[id - 1].state
        // Stage 1 has no predecessor, so its FAIL state is also repairable.
        if (current != State.FAIL && !(id == 1 && current == State.LOCKED)) return false
        stages[id - 1].state = State.READY
        stages[id - 1].evidence = ""
        persist()
        return true
    }

    @Synchronized fun evidenceJson(): JSONObject {
        val a = JSONArray()
        stages.forEach {
            a.put(JSONObject().put("stage", it.id).put("name", it.name).put("state", it.state.name).put("evidence", it.evidence))
        }
        return JSONObject().put("current_stage", currentStage()).put("final_pass", stages.all { it.state == State.PASS }).put("stages", a)
    }

    private fun persist() { prefs.edit().putString("state", evidenceJson().toString()).apply() }

    private fun resetAllLocked() {
        stages.forEach { it.state = State.LOCKED; it.evidence = "" }
    }

    private fun restore() {
        val raw = prefs.getString("state", null) ?: return
        try {
            val a = JSONObject(raw).getJSONArray("stages")
            if (a.length() != 13) throw IllegalStateException("stage_count")
            for (i in 0 until 13) {
                val o = a.getJSONObject(i)
                if (o.optInt("stage", -1) != i + 1) throw IllegalStateException("stage_order")
                stages[i].state = State.valueOf(o.optString("state", "LOCKED"))
                stages[i].evidence = o.optString("evidence", "")
            }
            var previousPassed = true
            for (i in 0 until 13) {
                val st = stages[i].state
                if (st == State.PASS && (!previousPassed || stages[i].evidence.isBlank())) throw IllegalStateException("invalid_pass_chain")
                if (st == State.READY && !previousPassed) throw IllegalStateException("invalid_ready_chain")
                if (st == State.RUNNING) {
                    if (!previousPassed) throw IllegalStateException("invalid_running_chain")
                    stages[i].state = State.FAIL
                    stages[i].evidence = "Interrupted while RUNNING; manual repair required"
                    for (n in i + 1 until 13) {
                        stages[n].state = State.LOCKED
                        stages[n].evidence = ""
                    }
                    break
                }
                if (st == State.FAIL) {
                    for (n in i + 1 until 13) {
                        stages[n].state = State.LOCKED
                        stages[n].evidence = ""
                    }
                    break
                }
                previousPassed = st == State.PASS
            }
        } catch (_: Exception) {
            resetAllLocked()
        }
    }
}
