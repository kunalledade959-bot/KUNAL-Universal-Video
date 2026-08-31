# KUNAL Universal Video — 13-Stage Problem Catalog

Purpose: enumerate, stage-by-stage, the failure conditions that must be considered before calling the production APK working on a physical Android phone.

This is a **failure catalog**, not a claim that every item has already happened. `STATIC` means the current source/CI can detect it. `DEVICE` means it requires a real Android device/runtime. `BOTH` means source guards plus device execution are required.

## Stage 1 — START / DIAGNOSTIC
1. Activity fails to create — BOTH
2. StageGate cannot enter RUNNING — STATIC
3. Installed-app discovery returns empty — STATIC
4. PackageManager throws/returns unusable data — BOTH
5. UI construction fails — BOTH
6. SharedPreferences/session persistence fails — BOTH
7. Session ID is not persisted — STATIC/BOTH
8. TTS initialization fails or never reaches SUCCESS — BOTH
9. Local bridge initialization/start fails — BOTH
10. Controller status rendering crashes or stays stale — BOTH
11. Process dies after launch — DEVICE
12. Android startup/lifecycle recreation loses controller state — DEVICE

## Stage 2 — ENABLE ACCESSIBILITY / CONNECT
1. Accessibility service disabled — STATIC/BOTH
2. Settings screen cannot be opened — DEVICE
3. Accessibility service enabled but not actually bound — DEVICE
4. Service disconnects during handshake — DEVICE
5. Target package is empty/wrong when handshake begins — BOTH
6. Local bridge is null/not started — STATIC
7. Bridge connect returns false — STATIC/BOTH
8. PING/PONG handshake fails — STATIC/BOTH
9. Accessibility state drops after successful handshake — STATIC/BOTH
10. Binder/service dies between checks — DEVICE
11. Device security/OS policy blocks accessibility operation — DEVICE
12. App reports connection success without real transport evidence — STATIC

## Stage 3 — SELECT / SAVE TARGET
1. Installed-app list is empty — STATIC/BOTH
2. Spinner has invalid position — STATIC
3. No target selected — STATIC
4. Target package is stale/uninstalled — BOTH
5. Selected package is actually the controller app — STATIC
6. Target package cannot be persisted — BOTH
7. Saved target cannot be restored after restart — DEVICE
8. Accessibility target package is not updated — STATIC
9. Target changes while later stages use old package — DEVICE
10. User selects a non-launchable package — BOTH

## Stage 4 — STUDY SELECTED APK
1. Target package is not installed — STATIC/BOTH
2. PackageManager application-info lookup fails — BOTH
3. Target has no launch activity — STATIC/BOTH
4. Manifest/package metadata is incomplete — DEVICE
5. Launch intent exists but launch fails — DEVICE
6. Target package has multiple activities and wrong entry point — DEVICE
7. Target is disabled/restricted — DEVICE
8. Target requires authentication before usable UI — DEVICE
9. Target immediately crashes on launch — DEVICE
10. Study stage passes from package metadata without proving runtime target usability — STATIC

## Stage 5 — SAVE STORY INPUT
1. Story is blank — STATIC
2. Story shorter than minimum length — STATIC
3. Story text is not persisted — BOTH
4. Saved story disappears after process restart — DEVICE
5. Unicode/emoji text is corrupted — DEVICE
6. Very large story causes UI/memory pressure — DEVICE
7. Story contains unsupported/control characters — DEVICE
8. Story is saved but later stage reads stale value — BOTH
9. Story field is not editable/visible — DEVICE
10. Concurrent UI update loses user input — DEVICE

## Stage 6 — OPERATE SELECTED TARGET
1. Target launch intent is missing — STATIC
2. Target launch fails — DEVICE
3. Target does not become foreground — BOTH
4. Accessibility service instance is unavailable — BOTH
5. Root accessibility window is null — BOTH
6. Accessibility tree is empty — BOTH
7. Accessibility tree exists but is stale — DEVICE
8. Target uses a UI surface inaccessible to the service — DEVICE
9. Target package changes while operating — DEVICE
10. Target crashes/ANRs during operation — DEVICE
11. Click/input action is rejected by target — DEVICE
12. Controller reports PASS without an actual target interaction — STATIC

## Stage 7 — DEEP TARGET UNDERSTANDING
1. Accessibility service disabled/dropped — BOTH
2. Target UI tree unavailable — BOTH
3. Zero nodes discovered — STATIC/BOTH
4. Node traversal throws on changing UI — DEVICE
5. Clickable controls are not exposed — DEVICE
6. Editable fields are not exposed — DEVICE
7. UI changes while traversal is running — DEVICE
8. Root window belongs to wrong package — DEVICE
9. Captured UI map is not persisted — BOTH
10. Captured map is stale after target navigation — DEVICE
11. Target uses WebView/custom rendering with incomplete accessibility semantics — DEVICE
12. Sensitive/permission dialogs hide the expected UI — DEVICE

## Stage 8 — CREATE EXACT SCENE PLAN
1. Story missing — STATIC
2. Story cannot be read from persistence — BOTH
3. Sentence splitting produces zero scenes — STATIC
4. Excessively long story exceeds intended scene count — STATIC
5. Scene ordering is wrong — STATIC
6. Scene text becomes empty — STATIC
7. Scene plan is not persisted — BOTH
8. Required scene fields are missing — STATIC
9. Special characters break scene serialization — STATIC
10. Scene plan is stale after story edit — DEVICE/BOTH

## Stage 9 — BUILD PRODUCTION PLAN / PROMPTS
1. Scene plan missing — STATIC
2. No scenes detected — STATIC
3. Prompt generated for only part of the scene list — STATIC
4. Prompt order differs from scene order — STATIC
5. Visual prompt missing — STATIC
6. Action prompt missing — STATIC
7. Plan is not persisted — BOTH
8. Story/scene edits leave stale prompts — DEVICE/BOTH
9. Prompt data contains malformed separators/newlines — STATIC
10. Downstream media stage cannot map output to scene — BOTH

## Stage 10 — AUDIO / VOICE / MUSIC / SFX + RECORD
1. Story missing for narration — STATIC
2. TTS object is null — STATIC/BOTH
3. TTS initialization never reaches SUCCESS — DEVICE
4. TTS language setup fails — DEVICE
5. TTS synthesis returns failure — BOTH
6. WAV file is absent/too small — STATIC/BOTH
7. Narration path is not persisted — BOTH
8. MediaProjection permission is cancelled — STATIC/BOTH
9. Screen-recording service fails to start — DEVICE
10. Recording stops without MediaStore MP4 — STATIC/BOTH
11. Recording URI is stale/invalid — BOTH
12. Video is produced but has unusable/empty media tracks — BOTH
13. Microphone/audio routing is unavailable — DEVICE
14. Long recording hits memory/storage/time limits — DEVICE
15. Screen capture records wrong surface — DEVICE
16. User/system permission dialog interrupts recording — DEVICE

## Stage 11 — ASSEMBLE / EDIT
1. No recorded visual clip — STATIC/BOTH
2. Narration audio file missing — STATIC/BOTH
3. Video file descriptor unavailable — STATIC/BOTH
4. MediaExtractor cannot open video — BOTH
5. MediaExtractor cannot open audio — BOTH
6. No video track — STATIC/BOTH
7. No audio track — STATIC/BOTH
8. Unsupported codec/container — DEVICE/BOTH
9. Corrupt sample data — DEVICE
10. MediaMuxer addTrack fails — DEVICE
11. MediaMuxer start/stop fails — DEVICE
12. Output MP4 missing/too small — STATIC/BOTH
13. Output path/storage becomes unavailable — DEVICE
14. Audio/video timestamps are invalid or badly aligned — DEVICE
15. Very large media causes memory/storage pressure — DEVICE

## Stage 12 — VERIFY / AUTO-FIX
1. Stage 11 did not PASS — STATIC
2. Final/assembled path missing — STATIC
3. Output file disappeared between checks — DEVICE
4. Output is not readable media — DEVICE
5. Video duration is zero/invalid — DEVICE
6. Audio track is absent — DEVICE
7. Video track is absent — DEVICE
8. Auto-fix changes output but does not re-verify — STATIC
9. Auto-fix loops forever — STATIC/BOTH
10. Verification reports PASS from metadata only — STATIC
11. Verification result is not persisted — BOTH
12. Crash during verification — DEVICE

## Stage 13 — FINAL GALLERY EXPORT
1. Stage 12 did not PASS — STATIC
2. Final media URI/path missing — STATIC
3. MediaStore insert fails — DEVICE
4. Output stream cannot be opened — BOTH
5. IS_PENDING transaction is not finalized — DEVICE
6. Exported item is not visible in Gallery — DEVICE
7. Exported item has wrong MIME/container — DEVICE
8. Exported item is zero/too small — STATIC/BOTH
9. Existing file/name collision causes incorrect result — DEVICE
10. Storage is full — DEVICE
11. Scoped-storage/OS policy rejects write — DEVICE
12. Process dies during export — DEVICE
13. Export succeeds but URI is not persisted — BOTH
14. Final PASS is reported before Gallery visibility is verified — STATIC

## Cross-stage failures that must also be tested
- Stage unlock state becomes inconsistent after process death.
- Stage PASS is persisted without corresponding evidence.
- Stage FAIL is overwritten by a later accidental PASS.
- App restart loses current stage/evidence.
- Accessibility disconnect occurs after Stage 2 but later stages continue.
- Target app is backgrounded while an operation assumes foreground state.
- Android permission dialogs steal focus.
- System UI ANR/dialog obscures production UI.
- Device screen locks or rotates during a stage.
- Low battery/power restrictions stop background recording/service.
- Low storage prevents audio/video/export creation.
- App is killed and recreated during a long operation.
- Duplicate callbacks execute the same stage twice.
- Double-tap starts duplicate recording/assembly jobs.
- Asynchronous callbacks arrive after a stage has already failed.
- Stale SharedPreferences values cause later stages to use old artifacts.
- File/URI exists but is unreadable.
- Media exists but has no valid track.
- A green CI result proves only the environment tested, not an arbitrary physical phone.

## Current verification boundary
The repository can statically verify many of these guards and can run emulator tests, but **physical-device-only items remain unproven until an actual Android device executes the production APK**. The correct verdict must therefore distinguish:

`STATIC PASS` → source/contract is guarded
`EMULATOR PASS` → hosted Android runtime passed
`REAL DEVICE PASS` → actual physical phone passed

Only the third category is sufficient to claim the real mobile connection and physical-device behavior are verified.
