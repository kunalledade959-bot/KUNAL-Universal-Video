# KUNAL UNIVERSAL VIDEO — MASTER HANDOVER / LOCK FILE

> This is the single continuity checkpoint. Read it first in every new chat. Preserve verified work, do not guess, and do not rebuild/replace the locked APK without evidence.

## PROJECT
- Repo: `kunalledade959-bot/KUNAL-Universal-Video`
- Branch: `main`
- Working principle: verification-first; no fake PASS; preserve locked assets.
- Authoritative master source: `/kaggle/input/datasets/kunalledade/kunal-universal-video-master/KUNAL_UNIVERSAL_VIDEO_MASTER.py`

## 13-STAGE LOCKED SYSTEM
The production Android controller already contains the 13-stage flow and persistent fail-closed StageGate.

1. Startup / Self-Diagnostic
2. Mobile Connection / Permissions
3. Target APK Selection
4. Study Selected APK
5. Story Input
6. Operate Selected Target APK
7. Deep Target-App Understanding
8. Exact Scene Plan
9. Production Plan / Prompts
10. Audio / Voice / Music / Sound Effects
11. Assemble / Edit
12. Verify / Auto-Fix
13. Final Gallery Export

`stage_gate.kt` is the persistent lock. A later stage cannot run unless the previous stage has PASS. Never manually unlock or reset to hide failures.

## CRITICAL CLARIFICATION: THE 13 SEQUENCES ARE ALREADY IN THE PRODUCTION BUILD PATH
The 13 independent E2E sequence workflows are verification gates for the same 13-stage production implementation. They are NOT 13 separate APK modules that need to be copied into the APK one-by-one.

The actual production integration is already wired as follows:
- `activity_fixed.kt` contains the production `MainActivity` 1..13 controller.
- `stage_gate.kt` contains the persistent 1..13 StageGate.
- `preflight_patch.py` patches the production build script so it writes `activity_fixed.kt` into the Android project's `MainActivity.kt` and writes `stage_gate.kt` into `StageGate.kt` before compilation.
- Therefore the final APK build path already implants the locked 13-stage implementation into the Android project.
- `sequence-stage-check.sh` independently checks the same 13 stage contracts and overlays `activity_fixed.kt` into the project copy used for contract verification.
- Do NOT create a second set of sequence implementations or duplicate them into the APK. That would risk divergence from the tested source.

## LOCKED APK
- The previously built/local APK was installed and opened successfully on the Android device in the established workflow.
- Treat that APK as GOLDEN/LOCKED.
- Do not casually replace it.
- A new APK may only replace the golden APK after a deliberate production build and evidence-based verification.
- Repository ZIP archives are source/project archives, not proof of the exact installed APK binary/hash.

## EXISTING 13 E2E VERIFICATION
The repository has `sequence-01.yml` through `sequence-13.yml` and the screenshot/history showed the independent sequence E2E batch producing green PASS results for the tested baseline commit `d7a0dd6f730808568c68df678cce54c703494537`.

Important: a later Daily APK Health Gate failure must NOT be interpreted as a failure of those previously green sequence tests. The later health run stopped at baseline verification before launching them.

## GOLDEN BASELINE
- SHA: `d7a0dd6f730808568c68df678cce54c703494537`
- Commit message: `test: launch all 13 independent sequence E2E runs`
- Do not change this baseline merely to make CI green.

## RECENT HEALTH GATE STATE
- Daily APK Health Gate run: `33300477176` (#2)
- Result: FAILURE
- Job: `daily-health`
- Failure: `Verify golden baseline reference`
- Full E2E and Sequence 01..13 launches were skipped by that run.

## UNIFIED VERIFICATION WORKFLOW
A manual-only orchestration workflow exists:
`.github/workflows/locked-production-verification.yml`

It dispatches the existing Full E2E gate and Sequence 01..13 gates while keeping each result separately attributable. It does not modify/unlock the sequence implementations or APK.

## CURRENT ACTUAL TASK
The misunderstanding about “implanting 13 sequences” is resolved: **the integration is already present in the production build path.**

The next real task is NOT to duplicate sequence code. The next task is to produce/verify a final APK from the existing integrated production source, while preserving the golden APK until the new build is actually verified.

Preferred sequence:
1. Preserve the golden/local APK.
2. Run the existing production APK build workflow (`Build KUNAL Universal Video APK`) from GitHub Actions.
3. Verify the APK artifact and SHA/report.
4. Verify that the build used the `activity_fixed.kt` + `stage_gate.kt` overlay.
5. Only after build evidence is good, run the required final verification.
6. Never call the final APK “verified” from static source checks alone.

## DO NOT
- Do not recreate the 13 sequences.
- Do not manually unlock StageGate.
- Do not replace the golden APK just because a CI orchestration/health check failed.
- Do not infer PASS from skipped/unrun tests.
- Do not invent APK hashes or device results.
- Do not modify the locked sequence definitions unless a real root-cause repair requires it.

## NEW-CHAT CONTINUATION
Start by reading this HANDOVER.md and checking the current `main` HEAD.
Then state:
- 13-stage implementation = already integrated in production build path and LOCKED
- StageGate = persistent/fail-closed
- Golden APK = LOCKED
- 13 independent E2E sequences = already tested as separate verification gates
- Daily Health #2 failure = baseline verification only; not evidence that the 13 sequences failed
- NEXT = build/verify the final integrated APK, without duplicating the sequence code

Continue from this checkpoint, not from scratch.
