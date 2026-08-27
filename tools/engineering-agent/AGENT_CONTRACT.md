# KUNAL Universal Video — Autonomous Engineering Agent Contract

## Mission
Produce a genuinely working Android APK, not merely a successful build.

## Final acceptance gate
The APK is FINAL only when evidence proves:
1. APK installs.
2. APK launches and remains alive.
3. 1→12 sequence exists as a real locked state machine; stage N+1 cannot execute before stage N passes.
4. Every required function in stages 1–12 executes successfully.
5. Real Android permission/consent flows are handled honestly; no fake permission state.
6. Target APK selection and target interaction are real, not status-text placeholders.
7. Recording/assembly/render produces a playable ~2-minute MP4 for the first real test.
8. Gallery export succeeds and the resulting file is verified.
9. Restart/recovery is tested.
10. Runtime logs contain no fatal crash for the tested path.
11. Evidence artifacts are saved for each gate.

## Non-negotiable rules
- Never label static existence as runtime PASS.
- Never claim a function works without execution evidence.
- Never silently replace the authoritative source with an unrelated implementation.
- Never spend repeated CI runs on an unchanged failure.
- On failure: capture exact error, classify root cause, make one targeted repair, then retest.
- If a requirement is impossible under Android security/user-consent rules, report it instead of bypassing or faking it.
- Preserve the last known-good commit before risky changes.

## 12-block contract
01 Startup / Self-Diagnostic
02 Mobile Connection / Permissions
03 Target APK Selection
04 Study Selected APK
05 Story Input
06 Production Plan / Prompts / Audio
07 Deep Target-App Understanding
08 Exact Scene Plan
09 Operate Selected Target APK
10 Assemble / Edit
11 Verify / Auto-Fix
12 Final Gallery Export

## Required state-machine model
Use persistent stage state. A stage may be `LOCKED`, `READY`, `RUNNING`, `PASS`, or `FAIL`.
Only `PASS` of stage N may unlock N+1. Any failure keeps later stages locked until repair and re-verification.

## Evidence model
Each stage must emit machine-readable evidence containing stage id, timestamp, action, result, and relevant runtime/log/file evidence. Finalization is forbidden if any stage lacks PASS evidence.

## Repair loop
`inspect -> reproduce -> capture -> root-cause -> patch -> compile -> focused test -> full regression -> evidence`

## Current known gaps
The existing audit reports blocks 4, 6, 7, 8, 9, 10 and 11 as PARTIAL and real phone connection, target interaction, recording, merge/render, playable 2-minute MP4 and gallery result as runtime-unverified. Those are engineering work items, not PASS conditions.
