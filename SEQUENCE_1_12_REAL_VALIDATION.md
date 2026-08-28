# KUNAL Universal Video — Real 1→12 Validation Contract

## Rule
The production APK remains untouched until every stage below has a real execution result. A button existing, a method returning `true`, or a static check is not a PASS.

## Target
- ChromaToons package: `bhootiyadreamstv.moboapp.chromatoons`
- Control channel: Android Accessibility Service, user-enabled
- Recording: Android MediaProjection
- Output: MediaStore/Gallery

## PASS contract

1. **APK Startup / Self-Diagnostic**
   - Fresh install launches MainActivity.
   - Process remains alive for 10 seconds.
   - No fatal startup exception.
   - Evidence: logcat + stage evidence.

2. **Mobile Connection / Permissions**
   - User enables Accessibility.
   - Service reports connected.
   - Target package becomes foreground-observable.
   - Evidence: accessibility state + target foreground state.

3. **Target APK Selection**
   - ChromaToons is detected by exact package.
   - Selection persists across app restart.
   - Evidence: saved package + launch intent.

4. **Study Selected APK**
   - Launch ChromaToons.
   - Capture accessibility-node snapshot from the real target screen.
   - Identify stable controls by text/content-description/resource-id where available.
   - Evidence: non-empty node snapshot tied to target package.

5. **Story Input**
   - Accept a test story.
   - Persist it.
   - Reject empty/invalid input.
   - Evidence: persisted story and validation result.

6. **Production Plan / Prompts / Audio**
   - Convert the story into ordered scenes.
   - Each scene has characters, background/action intent, dialogue/narration and audio cue.
   - Generate/prepare the audio asset used by the target workflow, not merely a status message.
   - Evidence: machine-readable plan + playable audio asset.

7. **Deep Target-App Understanding**
   - Re-open target and capture its relevant UI states.
   - Map each required operation to a verified target control.
   - No guessed coordinates.
   - Evidence: target UI map with control identifiers and observed states.

8. **Exact Scene Plan**
   - Produce deterministic scene-by-scene action lists.
   - Each action references a verified target control/state.
   - Evidence: ordered executable action plan.

9. **Operate Selected Target APK**
   - Execute actions through Accessibility.
   - Verify after each critical action that the expected target state changed.
   - Must create at least one real test scene in ChromaToons.
   - Evidence: action log + before/after UI snapshots.

10. **Assemble / Edit**
    - Execute the required scene/animation/recording workflow in the target.
    - Produce a real video file, not just a screen-recording flag.
    - Evidence: MP4 metadata + non-zero duration/size.

11. **Verify / Auto-Fix**
    - Validate video readability, duration, dimensions and expected scene evidence.
    - If a recoverable operation fails, retry using the verified fallback.
    - Evidence: verification report with checks and fixes.

12. **Final Gallery Export**
    - Put the verified final video in Gallery/Movies/KunalUniversalVideo.
    - Re-query MediaStore and verify the exact output exists and is readable.
    - Evidence: content URI + file metadata.

## Current status

- Stage 1: PASS on the production APK's real device startup.
- Stage 2: PARTIAL. Accessibility permission is the current gate.
- Stage 3: PARTIAL.
- Stage 4: NOT VERIFIED against the real ChromaToons UI.
- Stage 5: IMPLEMENTED, requires end-to-end test.
- Stage 6: PARTIAL. Current code generates a textual plan and TTS cue; this is not yet a verified target-ready audio asset.
- Stage 7: NOT VERIFIED.
- Stage 8: PARTIAL.
- Stage 9: NOT VERIFIED end-to-end against ChromaToons.
- Stage 10: PARTIAL. MediaProjection recording exists; target-app scene creation is not proven.
- Stage 11: PARTIAL.
- Stage 12: PARTIAL.

## Gate to merge

`MERGE_ALLOWED = true` only when all 12 stages have real evidence on a physical Android device with ChromaToons installed and the same test story produces a readable final video in Gallery.
