package com.kunal.universalvideo

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.util.UUID

/** Persistent, fail-closed 1..13 workflow gate with durable structured evidence. */
class StageGate(context: Context) {
    enum class State { LOCKED, READY, RUNNING, PASS, FAIL }
    data class Stage(
        val id: Int,
        val name: String,
        var state: State = State.LOCKED,
        var evidence: String = "",
        var startedAt: Long = 0L,
        var finishedAt: Long = 0L,
        var runId: String = ""
    )

    private val prefs = context.getSharedPreferences("kuv_stage_gate", Context.MODE_PRIVATE)
    private val stages = arrayOf(
        "Startup / Self-Diagnostic", "Mobile Connection / Permissions", "Target APK Selection",
        "Study Selected APK", "Story Input", "Operate Selected Target APK",
        "Deep Target-App Understanding", "Exact Scene Plan", "Production Plan / Prompts",
        "Audio / Voice / Music / Sound Effects", "Assemble / Edit", "Verify / Auto-Fix",
        "Final Gallery Export"
    ).mapIndexed { i, n -> Stage(i + 1, n) }.toMutableList()

    init { restore() }
    private fun valid(id: Int) = id in 1..13

    @Synchronized fun state(id: Int): State = if (valid(id)) stages[id - 1].state else State.LOCKED
    @Synchronized fun currentStage(): Int = stages.indexOfFirst { it.state != State.PASS }.let { if (it < 0) 13 else it + 1 }
    @Synchronized fun isUnlocked(id: Int): Boolean = valid(id) && (id == 1 || stages[id - 2].state == State.PASS)

    @Synchronized fun begin(id: Int): Boolean {
        if (!isUnlocked(id)) return false
        val s = stages[id - 1]
        s.state = State.RUNNING
        s.startedAt = System.currentTimeMillis()
        s.finishedAt = 0L
        s.runId = UUID.randomUUID().toString()
        s.evidence = evidence("RUNNING", "stage_started", "")
        persist()
        return true
    }

    @Synchronized fun pass(id: Int, evidence: String): Boolean {
        if (!valid(id) || stages[id - 1].state != State.RUNNING || evidence.isBlank()) return false
        val s = stages[id - 1]
        s.state = State.PASS
        s.finishedAt = System.currentTimeMillis()
        s.evidence = evidence("PASS", "runtime_observed", evidence)
        if (id < 13) stages[id].state = State.READY
        persist()
        return true
    }

    @Synchronized fun fail(id: Int, evidence: String) {
        if (!valid(id)) return
        val s = stages[id - 1]
        s.state = State.FAIL
        s.finishedAt = System.currentTimeMillis()
        s.evidence = evidence("FAIL", "runtime_observed_failure", evidence.ifBlank { "unspecified failure" })
        if (id < 13) for (n in id + 1..13) {
            stages[n - 1].state = State.LOCKED
            stages[n - 1].evidence = ""
            stages[n - 1].startedAt = 0L
            stages[n - 1].finishedAt = 0L
            stages[n - 1].runId = ""
        }
        persist()
    }

    @Synchronized fun resetForRepair(id: Int): Boolean {
        if (!valid(id)) return false
        if (id > 1 && stages[id - 2].state != State.PASS) return false
        val s = stages[id - 1]
        s.state = State.READY
        s.evidence = ""
        s.startedAt = 0L
        s.finishedAt = 0L
        s.runId = ""
        persist()
        return true
    }

    @Synchronized fun evidenceJson(): JSONObject {
        val a = JSONArray()
        stages.forEach { s ->
            a.put(JSONObject()
                .put("stage", s.id)
                .put("name", s.name)
                .put("state", s.state.name)
                .put("evidence", s.evidence)
                .put("started_at", s.startedAt)
                .put("finished_at", s.finishedAt)
                .put("run_id", s.runId))
        }
        return JSONObject()
            .put("schema", 2)
            .put("current_stage", currentStage())
            .put("final_pass", stages.all { it.state == State.PASS && it.evidence.isNotBlank() })
            .put("stages", a)
    }

    private fun evidence(result: String, type: String, message: String): String {
        val body = JSONObject()
            .put("result", result)
            .put("type", type)
            .put("message", message)
            .put("timestamp", System.currentTimeMillis())
            .put("run_id", stages.firstOrNull { it.state == State.RUNNING }?.runId ?: "")
        body.put("sha256", sha256(body.toString()))
        return body.toString()
    }

    private fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

    private fun persist() {
        // commit() makes the stage transition durable before callers receive success.
        prefs.edit().putString("state", evidenceJson().toString()).commit()
    }

    private fun restore() {
        val raw = prefs.getString("state", null) ?: return
        try {
            val root = JSONObject(raw)
            val a = root.getJSONArray("stages")
            for (i in 0 until minOf(13, a.length())) {
                val o = a.getJSONObject(i)
                val state = State.valueOf(o.optString("state", "LOCKED"))
                // A process death cannot prove a RUNNING stage completed. Re-open it as FAIL.
                stages[i].state = if (state == State.RUNNING) State.FAIL else state
                stages[i].evidence = if (state == State.RUNNING) evidence("FAIL", "process_recovery", "Stage was RUNNING when the previous process ended") else o.optString("evidence", "")
                stages[i].startedAt = o.optLong("started_at", 0L)
                stages[i].finishedAt = o.optLong("finished_at", 0L)
                stages[i].runId = o.optString("run_id", "")
            }
            // Enforce the invariant again after deserialization.
            for (i in 1 until 13) if (stages[i - 1].state != State.PASS) {
                for (j in i until 13) if (stages[j].state == State.PASS || stages[j].state == State.READY) {
                    stages[j].state = State.LOCKED
                    stages[j].evidence = ""
                }
                break
            }
        } catch (_: Exception) {
            stages.forEach { it.state = State.LOCKED; it.evidence = ""; it.startedAt = 0L; it.finishedAt = 0L; it.runId = "" }
            persist()
        }
    }
}