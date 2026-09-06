# KUNAL Universal Video Failure Playbook

This repository uses evidence-first recovery. A failure is never considered solved because a commit exists. The repair must be present in `main`, active in the production build path, and verified by the affected runtime gate.

## Certification states

- `PASS`: the required gate actually executed and produced its required evidence.
- `FAIL_REQUIRES_VERIFICATION`: a deterministic failure was observed; repair is not certified until the affected gate passes again.
- `UNVERIFIED`: evidence is missing, ambiguous, or the failure is unknown. Never convert this state into PASS.
- `INFRA_FAILURE`: the test environment failed before the application boundary could be evaluated.

## Known repair map

| Failure class | Primary boundary | Known repository repair |
|---|---|---|
| Runtime shell/retry | CI | `b2fd829` |
| Runtime diagnostic shell | CI | `833cfd3`, `4840cd9`, `cabb97b` |
| Real-device startup crash | Runtime | `45240aa` |
| False crash evidence | Runtime diagnostics | `076e483` |
| SHA256 verification crash | Build/verification | `7fdc8d7` |
| Persistent stage gate | Workflow | `724a302` |
| Stage 1 repair dead-end | Stage 1 | `27d9d6b` |
| Target discovery UI blocking | Stage 3 | `ceba6ee`, `414bbb2`, `d1936e0` |
| MainActivity Handler lifecycle | Runtime | `21cd1a9`, `2272091`, `aca96c9`, `93c7101` |
| Emulator/ADB instability | Infrastructure | `e0cfd5d`, `e62ed3f`, `478e46`, `313035` |
| Bluetooth emulator crash | Infrastructure | `a2e304e`, `edce232` |
| SystemUI ANR | Infrastructure | `cd2af78` |
| UIAutomator capture/parsing | Test boundary | `c01facf`, `c406581`, `6d660bb` |
| Accessibility service matcher | Stage 2 | `bb1f7f0` |
| Stage 2 completion contract | Stage 2 | `d755e87` |
| Stage 3 target persistence | Stage 3 | `a19757c`, plus Stage 2 sequencing fixes |
| Stage 10 recording finalization | Stage 10 | `426d1fd`, `55fef96` |
| Stage 11 media assembly/AAC | Stage 11 | `3041226`, `7bbb12f`, `a27d49a`, `43ea054`, `6a49758` |
| Android SDK provisioning | CI | `9f021f5`, `d6fefa8`, `5fa4a14`, `ecaadd2`, `63af3c`, `840327` |

## Recovery rule

1. Capture the exact first failing boundary.
2. Run `.github/scripts/failure-intelligence.sh <evidence-log>`.
3. If the signature is known, inspect the mapped repair and current production build overlay.
4. Apply the smallest root-cause fix.
5. Run static checks.
6. Build the canonical production APK.
7. Re-run the affected runtime gate and the full end-to-end gate.
8. Review evidence, including app-scoped crash/ANR evidence.
9. Only then certify PASS.

## Non-negotiable protections

- Never skip a stage to make a test green.
- Never weaken an assertion to accommodate a failing implementation.
- Never treat a CI timeout, SDK failure, ADB failure, or malformed UI capture as an application PASS.
- Never treat generic `system_server` noise as an app crash without package-scoped evidence.
- Never silently swallow a production discovery failure and report an empty successful result.
- Preserve the 13-stage dependency chain and real AccessibilityService, MediaProjection, TTS/audio, assembly, verification, and gallery/export behavior.
- Unknown failures remain `UNVERIFIED` until reproduced and diagnosed.

## Future-proofing

The playbook is intentionally deterministic. It is not an oracle and cannot guarantee that an arbitrary future Android, Gradle, emulator, or application defect will have a prewritten fix. Its purpose is to make known failure classes immediately actionable while forcing unknown failures through the same evidence-first diagnostic path instead of allowing guesswork to become production code.
