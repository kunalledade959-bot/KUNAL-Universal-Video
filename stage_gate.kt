package com.kunal.universalvideo

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.util.UUID

/**
 * Production truth authority for the 13-stage workflow.
 *
 * Invariants:
 * - only the unlocked stage can run;
 * - PASS requires non-empty evidence and a valid run transition;
 * - repairing an upstream stage invalidates every downstream result;
 * - process death can never turn RUNNING into PASS;
 * - persisted evidence is schema checked and hash checked on restore;
 * - every committed transition is written synchronously before success is returned.
 */
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

    companion object {
        private const val PREFS = "kuv_stage_gate"
        private const val KEY_STATE = "state"
        private const val SCHEMA = 3
        private const val MAX_EVIDENCE = 8192
    }

    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val stages = arrayOf(
        "Startup / Self-Diagnostic", "Mobile Connection / Permissions", "Target APK Selection",
        "Study Selected APK", "Story Input", "Operate Selected Target APK",
        "Deep Target-App Understanding", "Exact Scene Plan", "Production Plan / Prompts",
        "Audio / Voice / Music / Sound Effects", "Assemble / Edit", "Verify / Auto-Fix",
        "Final Gallery Export"
    ).mapIndexed { i, n -> Stage(i + 1, n) }.toMutableList()

    init { restore() }

    private fun valid(id: Int) = id in 1..13

    @Synchronized fun state(id: Int): State =
        if (valid(id)) stages[id - 1].state else State.LOCKED

    @Synchronized fun currentStage(): Int =
        stages.indexOfFirst { it.state != State.PASS }.let { if (it < 0) 13 else it + 1 }

    @Synchronized fun isUnlocked(id: Int): Boolean =
        valid(id) && (id == 1 || stages[id - 2].state == State.PASS)

    @Synchronized fun begin(id: Int): Boolean {
        if (!isUnlocked(id)) return false
        val s = stages[id - 1]
        if (s.state == State.RUNNING) return false
        s.state = State.RUNNING
        s.startedAt = System.currentTimeMillis()
        s.finishedAt = 0L
        s.runId = UUID.randomUUID().toString()
        s.evidence = evidence(s.runId, "RUNNING", "stage_started", "Stage $id entered RUNNING")
        return persist()
    }

    @Synchronized fun pass(id: Int, message: String): Boolean {
        if (!valid(id) || stages[id - 1].state != State.RUNNING || message.isBlank()) return false
        val s = stages[id - 1]
        val runId = s.runId
        val proof = evidence(runId, "PASS", "runtime_observed", message)
        if (!validEvidence(proof, runId, "PASS")) return false
        s.state = State.PASS
        s.finishedAt = System.currentTimeMillis()
        s.evidence = proof
        if (id < 13 && stages[id].state == State.LOCKED) stages[id].state = State.READY
        return persist()
    }

    @Synchronized fun fail(id: Int, message: String) {
        if (!valid(id)) return
        val s = stages[id - 1]
        val runId = if (s.runId.isBlank()) UUID.randomUUID().toString() else s.runId
        s.state = State.FAIL
        s.finishedAt = System.currentTimeMillis()
        s.runId = runId
        s.evidence = evidence(runId, "FAIL", "runtime_observed_failure", message.ifBlank { "unspecified failure" })
        invalidateDownstream(id)
        persist()
    }

    /**
     * Reset for repair and invalidate every dependent result. This is deliberately
     * stronger than the old implementation: no stale downstream PASS survives repair.
     */
    @Synchronized fun resetForRepair(id: Int): Boolean {
        if (!valid(id)) return false
        if (id > 1 && stages[id - 2].state != State.PASS) return false
        invalidateDownstream(id)
        val s = stages[id - 1]
        s.state = State.READY
        s.evidence = ""
        s.startedAt = 0L
        s.finishedAt = 0L
        s.runId = ""
        return persist()
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
            .put("schema", SCHEMA)
            .put("current_stage", currentStage())
            .put("final_pass", stages.all { it.state == State.PASS && validEvidence(it.evidence, it.runId, "PASS") })
            .put("stages", a)
    }

    private fun evidence(runId: String, result: String, type: String, message: String): String {
        val body = JSONObject()
            .put("schema", SCHEMA)
            .put("result", result)
            .put("type", type)
            .put("message", message.take(MAX_EVIDENCE))
            .put("timestamp", System.currentTimeMillis())
            .put("run_id", runId)
        body.put("sha256", sha256(body.toString()))
        return body.toString()
    }

    private fun validEvidence(raw: String, expectedRunId: String, expectedResult: String): Boolean {
        if (raw.isBlank() || raw.length > MAX_EVIDENCE) return false
        return try {
            val o = JSONObject(raw)
            if (o.optInt("schema", -1) != SCHEMA) return false
            if (o.optString("result") != expectedResult) return false
            if (o.optString("run_id") != expectedRunId) return false
            if (o.optString("message").isBlank()) return false
            val supplied = o.optString("sha256")
            if (supplied.isBlank()) return false
            o.remove("sha256")
            supplied == sha256(o.toString())
        } catch (_: Exception) { false }
    }

    private fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(it) }

    private fun invalidateDownstream(id: Int) {
        if (id >= 13) return
        for (n in id + 1..13) {
            stages[n - 1].state = State.LOCKED
            stages[n - 1].evidence = ""
            stages[n - 1].startedAt = 0L
            stages[n - 1].finishedAt = 0L
            stages[n - 1].runId = ""
        }
    }

    private fun persist(): Boolean =
        prefs.edit().putString(KEY_STATE, evidenceJson().toString()).commit()

    private fun clearAll() {
        stages.forEach {
            it.state = State.LOCKED
            it.evidence = ""
            it.startedAt = 0L
            it.finishedAt = 0L
            it.runId = ""
        }
    }

    private fun restore() {
        val raw = prefs.getString(KEY_STATE, null) ?: return
        try {
            val root = JSONObject(raw)
            if (root.optInt("schema", -1) != SCHEMA) throw IllegalStateException("unsupported stage-gate schema")
            val a = root.getJSONArray("stages")
            if (a.length() != 13) throw IllegalStateException("stage count mismatch")

            for (i in 0 until 13) {
                val o = a.getJSONObject(i)
                if (o.optInt("stage", -1) != i + 1) throw IllegalStateException("stage ordering mismatch")
                val state = State.valueOf(o.optString("state", "LOCKED"))
                val runId = o.optString("run_id", "")
                val storedEvidence = o.optString("evidence", "")
                if (state == State.PASS && !validEvidence(storedEvidence, runId, "PASS")) {
                    throw IllegalStateException("invalid PASS evidence at stage ${i + 1}")
                }
                stages[i].state = if (state == State.RUNNING) State.FAIL else state
                stages[i].runId = runId
                stages[i].evidence = if (state == State.RUNNING) {
                    evidence(runId.ifBlank { UUID.randomUUID().toString() }, "FAIL", "process_recovery", "Stage was RUNNING when the previous process ended")
                } else storedEvidence
                stages[i].startedAt = o.optLong("started_at", 0L)
                stages[i].finishedAt = o.optLong("finished_at", 0L)
            }

            // Rebuild the sequential invariant. No stage may remain PASS after a broken predecessor.
            var predecessorPass = true
            for (i in 0 until 13) {
                val s = stages[i]
                if (!predecessorPass || (s.state == State.PASS && !validEvidence(s.evidence, s.runId, "PASS"))) {
                    s.state = State.LOCKED
                    s.evidence = ""
                    s.startedAt = 0L
                    s.finishedAt = 0L
                    s.runId = ""
                    predecessorPass = false
                } else {
                    predecessorPass = s.state == State.PASS
                }
            }
            persist()
        } catch (_: Exception) {
            clearAll()
            persist()
        }
    }
}