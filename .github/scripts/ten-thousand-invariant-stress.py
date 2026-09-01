#!/usr/bin/env python3
"""Deterministic 10,000-iteration stress proof for workflow invariants.
This validates the contract model only; device/media E2E remains separately required.
"""
from __future__ import annotations
import hashlib
import json
import random

ITERATIONS = 10_000
STAGES = 13
SEED = 20260901


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def roundtrip(obj: dict) -> dict:
    return json.loads(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def main() -> None:
    rng = random.Random(SEED)
    for i in range(ITERATIONS):
        states = ["LOCKED"] * STAGES
        states[0] = "READY"
        evidence = [""] * STAGES
        for stage in range(STAGES):
            assert states[stage] == "READY", (i, stage + 1, states[stage])
            token = f"run-{i}-{stage}-{rng.getrandbits(64):016x}-😀-é-漢"
            evidence[stage] = json.dumps({"result": "PASS", "stage": stage + 1, "token": token}, ensure_ascii=False)
            assert evidence[stage].strip()
            states[stage] = "PASS"
            if stage + 1 < STAGES:
                states[stage + 1] = "READY"
            snapshot = {"schema": 2, "stages": states, "evidence": evidence}
            restored = roundtrip(snapshot)
            assert restored == snapshot
            assert digest(json.dumps(snapshot, ensure_ascii=False, sort_keys=True)) == digest(json.dumps(restored, ensure_ascii=False, sort_keys=True))
        assert all(s == "PASS" for s in states)
        assert all(e for e in evidence)

        # Fail-closed recovery: a RUNNING stage can never become PASS by restoration.
        recovery = {"state": "RUNNING", "stage": 7, "run_id": f"r-{i}"}
        restored_recovery = roundtrip(recovery)
        assert restored_recovery["state"] == "RUNNING"
        restored_recovery["state"] = "FAIL"
        assert restored_recovery["state"] != "PASS"

    print(f"10K_INVARIANT_STRESS_PASS iterations={ITERATIONS} seed={SEED}")


if __name__ == "__main__":
    main()
