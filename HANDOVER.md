# KUNAL UNIVERSAL VIDEO — MASTER HANDOVER / LOCK FILE

> Purpose: This file is the single continuity checkpoint for the KUNAL Universal Video project. A new chat MUST read this file first and continue from the exact state below. Do not restart the project, replace the APK, unlock stages, or guess missing facts.

## 0. PROJECT IDENTITY
- Project: **KUNAL Universal Video**
- Repository: `kunalledade959-bot/KUNAL-Universal-Video`
- Branch: `main`
- Current HEAD after this handover update: see GitHub commit history for the latest commit.
- Working principle: verification-first, no guessing/tukka, preserve working code, never fake PASS.

## 1. AUTHORITATIVE SOURCE / DO NOT REPLACE
- Authoritative master source used for the project is the user's established master source:
  `/kaggle/input/datasets/kunalledade/kunal-universal-video-master/KUNAL_UNIVERSAL_VIDEO_MASTER.py`
- The GitHub repository is the continuity/build/test repository.
- Do NOT create a new project/app/repository unless explicitly instructed.
- Do NOT replace working architecture merely to make a test green.

## 2. 13-STAGE LOCKED SYSTEM
The app has a persistent fail-closed StageGate with exactly 13 stages. A stage can only unlock after the previous stage is PASS. A FAIL locks all later stages. This behavior is implemented in `stage_gate.kt` and must be preserved.

### Locked sequence order
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

### LOCK RULES
- Never mark a stage PASS without real evidence.
- Never unlock a later stage manually just to continue a test.
- Never delete/reset the StageGate state to hide a failure.
- If a stage fails, repair the root cause, then use the intended repair/reset path and re-verify.
- The 13 sequences are independent CI gates, but they represent the same 1..13 stage contract.

## 3. APK LOCK STATE
- The working/local APK was previously built, installed on the Android device, and opened successfully in the established project workflow.
- Treat that working local APK as **LOCKED / GOLDEN** unless a new APK is produced only after a complete verified gate.
- Do NOT casually rebuild, replace, or publish a new APK because a CI gate failed.
- The GitHub repo currently contains Android project archives:
  - `KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT.zip`
  - `KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip`
- These repository ZIP archives are source/project archives, not proof of the exact local installed APK binary.
- The exact local APK binary/hash is not currently represented by a verified GitHub file in this handover. Do not invent an APK hash.

## 4. MOBILE / TARGET-APP BOUNDARY
- The important real-world blocker is the real mobile/target-app connection infrastructure, not blindly rebuilding the APK.
- Human/device-only actions must remain explicit. Do not bypass Android permissions, CAPTCHA, account security, or target-app protections.
- First real production-style test target established for the project: a **2-minute video**.
- The intended flow is to operate a selected target APK through the locked 13-stage pipeline, then assemble/edit, verify/auto-fix, and export to Gallery.

## 5. CURRENT CI TEST INFRASTRUCTURE
Important workflows/scripts include:
- `.github/workflows/daily-apk-health.yml`
- `.github/workflows/locked-production-verification.yml` **NEW UNIFIED GATE**
- `.github/workflows/full-e2e-emulator.yml`
- `.github/workflows/run-all-sequences.yml`
- `.github/workflows/verified-emulator.yml`
- `.github/workflows/e2e-pre-mobile.yml`
- `.github/workflows/runtime-diagnostic.yml`
- `.github/workflows/runtime-watchdog.yml`
- `.github/workflows/sequence-01.yml` through `.github/workflows/sequence-13.yml`
- `.github/scripts/full-e2e-emulator.sh`
- `.github/scripts/sequence-stage-check.sh`
- `.github/scripts/emulator-smoke.sh`
- `.github/scripts/emulator-smoke-verified.sh`
- `.github/scripts/runtime-diagnostic.sh`

## 6. GOLDEN BASELINE LOCK
The Daily APK Health Gate currently defines this golden baseline:
- `GOLDEN_BASELINE_SHA = d7a0dd6f730808568c68df678cce54c703494537`
- That commit is real/reachable and has message:
  `test: launch all 13 independent sequence E2E runs`
- The baseline commit was verified as an existing GitHub commit during this handover.
- Do NOT silently change the golden baseline just to make the health workflow pass.

## 7. LATEST DAILY APK HEALTH RESULT
Latest manually dispatched Daily APK Health Gate:
- Run: `33300477176`
- Run number: `2`
- Head SHA at that run: `9b1f8528abcc1788ae5d067ddea90941c2741c47`
- Result: **FAILURE**
- Job: `daily-health`
- Job ID: `99227557838`

### Exact failure point
The run failed at:
- Step 2: **Verify golden baseline reference**
- Steps after that were skipped:
  - Launch full production E2E gate
  - Launch 13 independent sequence gates
  - Wait for full E2E gate
  - Collect latest independent sequence results

The health report/repair-alert steps completed as designed.

### Important interpretation
This failure does **NOT** prove that the APK or any of the 13 sequences failed. The run stopped before launching them. Do not report the 13 sequences as PASS or FAIL from this run.

## 8. UNIFIED PRODUCTION VERIFICATION GATE
A new workflow has now been added:
- `.github/workflows/locked-production-verification.yml`
- It is **manual only** (`workflow_dispatch`).
- It does NOT modify or unlock the 13 sequence definitions.
- It does NOT replace the locked APK.
- It dispatches the existing `full-e2e-emulator.yml` plus `sequence-01.yml` through `sequence-13.yml`.
- It keeps the 13 sequence results independent and records each run ID/result.
- It fails closed if the Full E2E gate fails or any sequence does not complete successfully.
- It uploads `locked-sequence-results.txt` as the unified evidence artifact.
- It explicitly states that a failed unified verification does not authorize APK replacement or sequence unlock.

### Why this is the requested merge
The existing **13 independent sequence verification** and the existing **full production E2E / crash-path verification** are now orchestrated by one master gate while remaining separate underneath. One button starts the verification batch; results stay separately attributable.

### Important limitation
This unified workflow is an orchestration/verification layer. It does not magically make the APK mathematically “crash-proof.” A PASS means the defined automated gates completed successfully for that run. Real-device behavior still requires real-device evidence.

## 9. EXACT NEXT ACTION
From GitHub Actions:
1. Open **Locked Production Verification Gate**.
2. Press **Run workflow** on `main`.
3. Let the workflow dispatch the existing Full E2E and all 13 independent sequence workflows.
4. Do not touch the APK or unlock any sequence while it runs.
5. After completion, inspect the unified artifact and the individual run results.
6. Only after actual evidence is green should we consider the verification baseline complete.

If the gate fails, diagnose the exact failed component. Do not rebuild the APK just because orchestration failed.

## 10. CURRENT STATE SUMMARY
### LOCKED / PRESERVE
- 13-stage StageGate contract: **LOCKED**
- Working local installed/opened APK: **LOCKED / GOLDEN**
- Golden baseline: `d7a0dd6f730808568c68df678cce54c703494537`
- Existing sequence workflows: **PRESERVE**

### VERIFIED FACTS
- StageGate implementation is persistent and fail-closed.
- Exactly 13 stages exist in the established order above.
- Golden baseline commit exists and is reachable.
- Daily Health Gate run #2 failed before E2E/sequence launch.
- Unified orchestration workflow has been added without altering the sequence workflow definitions.

### NOT YET PROVEN BY THE NEW UNIFIED GATE
- Full production E2E PASS for the unified run
- Sequence 01 PASS through Sequence 13 PASS for the unified run

## 11. DO NOT DO THESE THINGS
- Do not create a replacement app.
- Do not rebuild/replace the locked local APK without a verified reason.
- Do not unlock stages manually.
- Do not call a skipped test PASS.
- Do not call an unrun sequence PASS.
- Do not infer emulator success from source-code existence.
- Do not change the golden baseline just to satisfy CI.
- Do not hide failures by resetting state.
- Do not invent APK hashes, device results, target-app behavior, or successful exports.
- Do not claim full E2E until actual evidence exists.

## 12. CONTINUATION COMMAND FOR A NEW CHAT
Start by reading this file and then verify the current `main` HEAD.

State the following before taking action:
1. 13-stage pipeline = locked
2. APK = locked/golden
3. Golden baseline = `d7a0dd6f730808568c68df678cce54c703494537`
4. Last Daily Health run = `33300477176`, failed at baseline verification before E2E/sequence launch
5. New unified gate = `.github/workflows/locked-production-verification.yml`
6. NEXT = manually run **Locked Production Verification Gate**, then inspect actual evidence.

This is the checkpoint. Continue from here, not from scratch.
