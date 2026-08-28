# KUNAL Universal Video — 1→12 Engineering Audit

This branch is intentionally isolated from `main`. The currently working APK on `main` is not modified by this audit.

## Locked sequence

1. APK Startup / Self-Diagnostic
2. Mobile Connection / Permissions
3. Target APK Selection
4. Study Selected APK
5. Story Input
6. Story → Production Plan / Prompts / Audio
7. Deep Target-App Understanding
8. Exact Scene Plan
9. Operate Selected Target APK
10. Assemble / Edit
11. Verify / Auto-Fix
12. Final Gallery Export

## Evidence-based current implementation

- Stage 1: **REAL / verified on device and emulator.** Current APK launches and the real phone screenshot confirms the app opens.
- Stage 2: **REAL / partially implemented.** Accessibility settings flow and local bridge exist. The current UI correctly blocks connection until Accessibility is enabled.
- Stage 3: **REAL / partially implemented.** Installed-app enumeration and target-package persistence exist, plus target launch support.
- Stage 4: **NOT yet a real implementation.** The current `StageGate` only tracks state; there is no complete target-app study artifact pipeline.
- Stage 5: **NOT yet a real implementation.** No dedicated story editor/storage/validation pipeline is present in the current startup activity.
- Stage 6: **NOT yet a real implementation.** No complete production-plan, prompt, and audio-generation pipeline is present.
- Stage 7: **NOT yet a real implementation.** Accessibility service can observe the target foreground package, but a durable deep-understanding model/artifact is not implemented.
- Stage 8: **NOT yet a real implementation.** No complete scene-plan authoring/validation engine is present.
- Stage 9: **PARTIALLY REAL.** Accessibility click/text operations, target launch, and bridge commands exist, but generic target-app operation is not yet proven end-to-end.
- Stage 10: **PARTIALLY REAL.** Screen recording to MP4 exists. A complete multi-scene assembly/edit pipeline is not yet proven.
- Stage 11: **NOT yet a complete real implementation.** Static/build checks exist, but product-level video verification and deterministic auto-fix are incomplete.
- Stage 12: **PARTIALLY REAL.** Screen capture uses MediaStore and writes MP4 into the Movies/KunalUniversalVideo collection, but final-gallery export of a verified assembled result is not yet proven end-to-end.

## Gate policy

A stage is not PASS merely because `StageGate` can store `PASS`. A stage must produce a concrete artifact/evidence record and pass its functional test. Later stages remain locked until the immediately previous stage has a verified PASS.

## Integration rule

Do not merge this branch into `main` until every stage has a reproducible functional test and evidence. The existing APK on `main` remains untouched during this isolated implementation effort.
