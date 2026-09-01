# Production Hardening Plan

This file is the verification contract for the final 1..13 workflow.

## PASS policy

A stage may report PASS only from observed runtime evidence. Source presence, a button click, a function return, a file-exists check, or a build result is not sufficient.

## Required evidence classes

1. Static source contract
2. Build/install/launch evidence
3. Runtime behavior evidence
4. Artifact integrity evidence
5. Physical-device evidence where Android hardware behavior is required
6. End-to-end evidence for the complete 1..13 chain

## Zero-tolerance defects

- silent data truncation
- fake or premature PASS
- main-thread blocking waits
- unbounded accessibility traversal
- unchecked stale state
- unchecked partial artifacts
- missing resource cleanup
- missing persistence read-back
- media validation based only on track count
- gallery export without post-write verification
- fallback providers silently masquerading as the required provider
- target selection used before target validation

## Sequence contract

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

## Engineering rule

When one check fails, preserve the failure evidence and continue independent static analysis/checks. Never convert an unverified result into PASS. A final production claim requires every mandatory evidence class to pass.
