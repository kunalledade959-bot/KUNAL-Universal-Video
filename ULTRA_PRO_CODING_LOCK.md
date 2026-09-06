# KUNAL Universal Video — Ultra Pro Coding Lock

**Status: LOCKED**

This repository is operated under a verification-first production rule.

## Non-negotiable rules

1. **No guessing.** A fix must be based on observed source, logs, test output, or reproducible behavior.
2. **No fake PASS.** A PASS is valid only when the required test actually executed and produced the required evidence.
3. **No unverified production code.** A code change is not production-ready until its applicable static, build, runtime, and E2E gates pass.
4. **First proven failure wins.** Diagnose the earliest proven failing boundary before changing later layers.
5. **Test the test.** A failing matcher, stale assertion, skipped job, or missing evidence is a test/infrastructure defect, not automatically an app defect.
6. **Preserve working architecture.** Do not casually replace the locked 13-stage StageGate, AccessibilityService, MediaProjection, TTS/audio/video assembly, or existing E2E contracts.
7. **Evidence is mandatory.** Every failure must retain the exact command exit code, relevant log lines, UI/state dumps, and artifact needed to reproduce/classify it.
8. **No weakening gates.** Do not delete, skip, loosen, hide, or downgrade an assertion merely to obtain PASS.
9. **External knowledge before implementation.** When a problem depends on current platform/tooling behavior, verify it against authoritative current documentation and project evidence before coding.
10. **Latest SHA verification.** A prior commit's green result never certifies a newer commit.
11. **Physical-device boundary remains explicit.** Emulator PASS does not silently become physical-phone PASS.
12. **Failure remains failure.** If any required gate fails, the change stays uncertified until the root cause is corrected and the relevant gate is rerun.

## Required verification order

`Inspect → Research authoritative behavior when relevant → Reproduce → Capture evidence → Classify boundary → Minimal root-cause fix → Static checks → Build → Runtime/E2E → Re-run affected gates → Evidence review → Certification`

## Certification vocabulary

- **PASS:** required test executed successfully with evidence.
- **FAIL:** required test executed and found a defect.
- **INFRA FAILURE:** test could not execute because the environment/tooling failed; this is not a PASS.
- **UNVERIFIED:** required evidence is missing or the test did not actually execute.

Never convert `FAIL`, `INFRA FAILURE`, or `UNVERIFIED` into `PASS`.

## Required merge protection

The repository should require the dedicated **Ultra Pro Coding Lock** status check on `main`, with the branch required to be up to date before merge and bypass disabled where repository administration permits. GitHub documents required status checks and protected branches as the enforcement mechanism for preventing unverified changes from merging.

This file is a repository policy. GitHub branch/ruleset administration is a separate repository setting and must be verified independently.
