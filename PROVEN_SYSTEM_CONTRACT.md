# KUNAL Universal Video — Proven System Contract

## Purpose
The production app must behave as a gated 13-stage pipeline. A stage is not considered successful because a button exists, code executed, an emulator started, or a value was assumed. A stage passes only when its required evidence is collected from the real operation being tested.

## Non-negotiable rules
1. **Strict sequential gate:** Stage N+1 remains LOCKED until Stage N has a verified PASS.
2. **No false PASS:** no success state may be written from intent, construction, or an unchecked callback.
3. **No misleading CONNECTED:** mobile connection requires live controller health, matching session, Accessibility service enabled/bound, and target-channel evidence.
4. **Visible prerequisites only:** the UI shows the action that is currently possible. Future actions are disabled/locked rather than presented as if usable.
5. **One stage, one run:** a stage diagnostic is independent. A failure must produce an evidence report and must not silently trigger duplicate copies of other stage tests.
6. **Failure is data:** a failed stage must collect exact error, exception, relevant state, timestamps, identifiers, logs, and missing prerequisites before returning FAIL.
7. **Continue diagnostics without advancing the production gate:** exhaustive audit may inspect all 13 stages in one diagnostic run, but it must not mark later production stages PASS when an earlier prerequisite failed.
8. **Complete report:** every exhaustive run produces one machine-readable report plus a human-readable summary artifact.
9. **No invented capabilities:** if a feature depends on an external engine, device permission, service, model, or credential that is unavailable, the stage reports the exact dependency instead of pretending it works.
10. **Real-device distinction:** emulator/static/build PASS is never presented as real-phone PASS. Real-device PASS requires real-device evidence.
11. **Regression protection:** every repair must be followed by targeted verification, then the relevant 13-stage regression audit before release.
12. **Concurrency discipline:** production verification is a single logical run. Duplicate workflow triggers must not create competing production-verification runs.

## UI contract
At any moment the user should see:
- Current stage and state: `LOCKED / READY / RUNNING / PASS / FAIL`.
- Exactly what prerequisite is missing when a stage is locked.
- A concise live evidence status for the current stage.
- A detailed diagnostics/report action after failure.
- Only the next valid production action should be enabled.

Example:
- Stage 2 FAIL -> Stage 3..13 remain LOCKED.
- Stage 2 PASS -> Stage 3 becomes READY and target selector becomes available.
- Stage 3 PASS -> Stage 4 becomes READY.

## 13-stage evidence contract
### 1. Startup / Self-Diagnostic
Must verify application process, required components, package manager access, storage/runtime prerequisites, and controller initialization.

### 2. Mobile Connection / Permissions
Must verify the actual device channel, controller health, session identity, Accessibility service enabled and runtime-bound, and a real handshake. A local boolean is insufficient.

### 3. Target APK Selection
Must present a real installed-app list, allow one target selection, persist its package identity, and verify the package is installed and launchable before PASS.

### 4. Study Selected APK
Must inspect the selected target's package/manifest/launch information and collect evidence needed by later stages. No generic placeholder study is accepted.

### 5. Story Input
Must validate and persist the actual story input, including length/content checks and a recoverable evidence record.

### 6. Operate Selected Target
Must launch the actual selected target and prove that the live target is foreground and its accessibility/UI channel is usable before PASS.

### 7. Deep Target Understanding
Must collect actual target UI/accessibility evidence, not merely package-name evidence. Store a reproducible target map/report.

### 8. Exact Scene Plan
Must transform the validated story/target information into an ordered, deterministic scene plan. Every scene needs explicit inputs and outputs.

### 9. Production Plan / Prompts
Every planned scene must have validated production instructions. Invalid or incomplete media instructions must fail before rendering.

### 10. Audio / Voice / Music / SFX + Record
Must verify every generated asset before PASS: narration audio exists, is decodable/usable, recording exists, and requested music/SFX assets are present and valid. **Android system TTS is not automatically accepted as "real human" voice.** A human-like voice requirement requires a verified high-quality speech engine/provider and a successful synthesis artifact. If no such provider is configured/available, report `VOICE_PROVIDER_UNAVAILABLE` instead of silently falling back to robotic/system TTS.

### 11. Assemble / Edit
Must validate all input media, track compatibility, duration/format constraints, successful mux/render output, and output readability before PASS.

### 12. Verify / Auto-Fix
Must verify the assembled output against required invariants and produce exact failure evidence. Auto-fix is allowed only when the fix itself can be verified; otherwise remain FAIL.

### 13. Final Gallery Export
Must verify the final artifact exists, is readable, is discoverable in the intended gallery/media store, and has a stable integrity hash/metadata record before PASS.

## Evidence model
Each stage result should contain at minimum:
- run/session ID
- stage number/name
- start/end timestamp
- PASS/FAIL/LOCKED state
- exact checks performed
- exact observed values
- error type/message when applicable
- missing prerequisite(s)
- artifact paths/URIs when applicable
- SHA-256 for important generated artifacts
- device/emulator distinction
- repair/change identifier when applicable

## Release rule
A release candidate may be called **production-verified** only when all 13 stages have PASS evidence and the final artifact has been verified on the intended real device. Build success, emulator success, static audit success, or a green GitHub workflow alone does not satisfy this rule.
