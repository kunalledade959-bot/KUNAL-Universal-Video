# KUNAL Universal Video - HANDOVER

## Purpose
This file is the authoritative handover for continuing the KUNAL Universal Video project after a chat/session reset. Read it before making any code or workflow change.

## Project
- Repository: `kunalledade959-bot/KUNAL-Universal-Video`
- Branch: `main`
- Android package: `com.kunal.universalvideo`
- Production APK expected by the final gate: `artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk`
- Master source used by the earlier production build process: `/kaggle/input/datasets/kunalledade/kunal-universal-video-master/KUNAL_UNIVERSAL_VIDEO_MASTER.py`

## NON-NEGOTIABLE ENGINEERING RULES
1. Do not guess. Inspect the real file, workflow, artifact, log, UI hierarchy, or crash evidence first.
2. Never claim PASS unless the relevant production evidence proves it.
3. Do not fix one visible symptom when several failures can share one root cause. Collect the complete evidence and make one consolidated root-cause fix.
4. Do not repeatedly patch the same layer blindly. If strategy A fails, revert/cleanly abandon it and use a materially different evidence-backed strategy B, then C only when justified.
5. Every change must be production-grade/A1. No temporary hacks, fake state, fake PASS markers, or lightweight substitutes.
6. Preserve already-verified working functionality. Do not rewrite app semantics merely to satisfy a bad test.
7. Keep unrelated systems untouched. One root cause/change set at a time, but include all directly related fixes in that same root-cause change.
8. Treat old failed/cancelled workflow runs as historical evidence only. Current verification must use the latest relevant commit/run group.
9. Multiple workflows can run in parallel for one commit. Report run groups/counts, not "one run" when several are expected.
10. The final test must exercise the real user-visible production flow, not only internal/unit checks.

## CURRENT VERIFIED HISTORY
Earlier production baseline was verified before the recent verification-infrastructure work:
- `a8dab7f10eb14c8888d9ff8cd01398aec4bbfcf2` was a locked production APK/full-E2E baseline.
- The app had previously passed the 13 independent sequences plus Run All Systems in the production verification path.

Later infrastructure/root-cause fixes included:
- `93c7101b8c24123ab8421699f5d6b5d1417337e4`: V4 repair was hardened so the canonical activity hardening was deterministic and no longer depended on a missing separate patch step.
- `379115a2c34e640a2cff2de19cb1f3538e631a31`: exposed `avdmanager` in the self-healing gate PATH.
- `478e46cbc5659d0517b7f77eed5621da80575b7a`: switched emulator acceleration from software emulation to hardware acceleration.
- `31303598f5aedc65602297767e6a5e80d28eb7b5a`: added strict `/dev/kvm` permission setup and fail-closed verification.

## RECENT ROOT-CAUSE FINDINGS
### Final Production User Flow XML failure
A final-flow run failed because Android UIAutomator output contained a trailing status line after the XML document. The test attempted to parse the entire output and got `ParseError: junk after document element`. The final-flow `dump_ui()` was changed to extract and validate exactly the `<hierarchy>...</hierarchy>` XML payload. This was an infrastructure/test parsing issue, not proof of an app UI defect.

### Stage 3 target persistence failure
A later final-flow run showed a target package in the production UI but reported that `target_package` was not persisted. Artifact evidence showed the production UI has an explicit Stage 3 button:
`3 • SELECT / SAVE TARGET`
The old test selected the Spinner row and immediately asserted persistence, which was semantically incorrect. The production app's `selectTarget()` performs persistence/connect work when the explicit Stage 3 action is used.

## LATEST CODE CHANGE
Latest relevant commit:
`93409bb48a5f75f1cbd02c8b4e22aefcc9c83e59`

Message:
`fix: validate explicit stage 3 target save in final flow`

The final production user-flow script now:
1. Detects the target-selection Spinner.
2. Opens the target popup.
3. Selects a real target package.
4. Verifies the selected target is reflected in the controller UI.
5. Detects the production Stage 3 `3 • SELECT / SAVE TARGET` button.
6. Validates that control is enabled and has valid bounds.
7. Taps the real Stage 3 save control.
8. Verifies `target_package` persistence in `shared_prefs/kuv.xml`.
9. Resolves and launches the real target app.
10. Verifies the target is actually foreground.
11. Restores the controller and verifies the selected target remains visible.

Do not remove the explicit Stage 3 action from the test. Do not change app semantics merely to bypass this test.

## REQUIRED NEXT VERIFICATION
After the latest commit, run/inspect the complete production verification chain. The important evidence is:
- APK build success and APK present.
- Install success.
- MainActivity launch success.
- App process remains alive.
- Initial production UI hierarchy is valid XML.
- Spinner and Stage 1 controls exist with valid bounds.
- Target popup contains a real target.
- Target selection is reflected in the controller.
- Stage 3 save control is present, enabled, clickable, and tapped.
- `shared_prefs/kuv.xml` contains the selected `target_package`.
- Target activity resolves and real target launch succeeds.
- Target is foreground.
- Controller returns successfully and retains the target state.
- All required production sequences, including the 13-stage/full-E2E gate, remain green.
- Final production user-flow gate passes with evidence.
- Crash/ANR logs do not show an app crash hidden behind a green UI check.

If any run fails, download/read its artifact first. Classify the failure as APP, TEST, BUILD, EMULATOR/INFRASTRUCTURE, or SYSTEM before changing code.

## FINAL USER-FLOW QUALITY BAR
The final gate is not allowed to pass merely because text exists in XML. It must prove real user-visible behavior:
- real controls,
- valid bounds,
- enabled/clickable state where applicable,
- actual input/tap,
- resulting state transition,
- persisted state,
- real target handoff,
- return to controller,
- no crash/ANR.

## WORKFLOW HYGIENE
There are many historical repeated runs visible in GitHub Actions, especially Autonomous APK Doctor and Final Production User Flow. They are historical noise and must not be used as the current truth. Do not create additional duplicate/manual runs unless they are necessary for verification. Do not weaken the production gates just to reduce red history.

If cleanup of historical Actions runs is required, use an authenticated GitHub capability that actually supports run deletion. Never claim old runs were deleted unless GitHub confirms deletion.

## DO NOT LOSE THESE ROOT-CAUSE LESSONS
- Missing `avdmanager` PATH was a shell infrastructure issue.
- `-accel off` caused severe emulator/SystemUI instability; hardware acceleration is required where KVM is available.
- Hardware acceleration then exposed `/dev/kvm` permissions; the gate now explicitly prepares and verifies KVM access and fails closed when unavailable.
- UIAutomator can append a status line outside the XML payload; parse only the canonical hierarchy document.
- Selecting a Spinner row is not the same as pressing the production Stage 3 save action. Tests must follow the real user flow.

## HANDOVER PROCEDURE FOR THE NEXT CHAT
1. Read this file completely.
2. Inspect the current `main` HEAD and compare it with the latest commit listed above.
3. Inspect current workflow files before running anything.
4. Identify the latest relevant run group for that HEAD.
5. Do not trust old red runs.
6. If a current run fails, inspect its artifact/log/UI evidence before editing anything.
7. Consolidate related root causes into the smallest correct production-grade change.
8. Verify the changed file after committing.
9. Re-run the complete relevant production gate.
10. Continue until the final production user-flow and required E2E gates are genuinely green.

## DEFINITION OF DONE
Done means the production APK is buildable/installable/launchable, the real user-visible target-selection/save/handoff flow passes, required 13-stage/full-E2E verification passes, crash/ANR evidence is clean for the tested flow, and no fake PASS or test-only bypass has been introduced.

## CURRENT STATUS
The latest code change is committed, but the post-`93409bb48a5f75f1cbd02c8b4e22aefcc9c83e59` complete verification result must be treated as the next authoritative checkpoint. Do not declare the project finally complete until that verification evidence is inspected.