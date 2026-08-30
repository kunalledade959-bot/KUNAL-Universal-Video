# KUNAL UNIVERSAL VIDEO — MASTER HANDOVER / LOCK FILE

> Purpose: This file is the single continuity checkpoint for the KUNAL Universal Video project. A new chat MUST read this file first and continue from the exact state below. Do not restart the project, replace the APK, unlock stages, or guess missing facts.

## 0. PROJECT IDENTITY
- Project: **KUNAL Universal Video**
- Repository: `kunalledade959-bot/KUNAL-Universal-Video`
- Branch: `main`
- Current verified repository HEAD at handover: `9b1f8528abcc1788ae5d067ddea90941c2741c47`
- Current HEAD message: `chore: run runtime watchdog hourly`
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
The repository currently contains these important workflows/scripts:
- `.github/workflows/daily-apk-health.yml`
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
- Head SHA: `9b1f8528abcc1788ae5d067ddea90941c2741c47`
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

## 8. EXACT NEXT ACTION TO RUN
### FIRST ACTION IN THE NEXT CHAT
Run **Daily APK Health Gate** manually from GitHub Actions using `workflow_dispatch`.

Reason: the previous run stopped at the golden-baseline verification step, so the actual full E2E gate and all 13 independent sequence gates were never launched by that run.

### AFTER THAT RUN
1. Inspect the new Daily APK Health Gate result.
2. If baseline verification passes, allow it to launch:
   - the full production E2E gate
   - all 13 independent sequence gates
3. Wait for the full E2E result.
4. Collect the latest results for Sequence 01..13 for the **current main SHA**.
5. Record each sequence as SUCCESS/FAILURE with its run ID.
6. Only after the evidence is green, continue to the next technical stage.
7. If baseline verification fails again, inspect the actual job logs/root cause before changing anything. Do not rebuild the APK merely because this gate failed.

## 9. 13 CI WORKFLOWS ARE INDEPENDENT
The repo contains:
- `sequence-01.yml`
- `sequence-02.yml`
- `sequence-03.yml`
- `sequence-04.yml`
- `sequence-05.yml`
- `sequence-06.yml`
- `sequence-07.yml`
- `sequence-08.yml`
- `sequence-09.yml`
- `sequence-10.yml`
- `sequence-11.yml`
- `sequence-12.yml`
- `sequence-13.yml`

Do not assume their result from the Daily Health Gate failure. The last failed Daily Health run skipped their launch.

## 10. CURRENT STATE SUMMARY
### LOCKED / PRESERVE
- 13-stage StageGate contract: **LOCKED**
- Working local installed/opened APK: **LOCKED / GOLDEN**
- Current main HEAD: `9b1f8528abcc1788ae5d067ddea90941c2741c47`
- Golden baseline: `d7a0dd6f730808568c68df678cce54c703494537`
- Existing CI scripts/workflows: preserve unless root-cause repair requires a change

### VERIFIED FACTS
- StageGate implementation is persistent and fail-closed.
- Exactly 13 stages exist in the established order above.
- Golden baseline commit exists and is reachable.
- Daily Health Gate run #2 exists and failed before E2E/sequence launch.

### NOT YET PROVEN BY THE LATEST DAILY RUN
- Full production E2E PASS
- Sequence 01 PASS
- Sequence 02 PASS
- Sequence 03 PASS
- Sequence 04 PASS
- Sequence 05 PASS
- Sequence 06 PASS
- Sequence 07 PASS
- Sequence 08 PASS
- Sequence 09 PASS
- Sequence 10 PASS
- Sequence 11 PASS
- Sequence 12 PASS
- Sequence 13 PASS

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
Start by reading this file and state:
1. Current HEAD = `9b1f8528abcc1788ae5d067ddea90941c2741c47`
2. Golden baseline = `d7a0dd6f730808568c68df678cce54c703494537`
3. APK = locked, do not replace
4. 13 stages = locked fail-closed pipeline
5. Last Daily Health run = `33300477176`, failed at baseline verification before E2E/13 sequence launch
6. NEXT = manually run **Daily APK Health Gate**, then inspect real evidence before any repair/rebuild

This is the checkpoint. Continue from here, not from scratch.
