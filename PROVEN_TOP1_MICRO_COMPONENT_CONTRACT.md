# PROVEN TOP-1 MICRO-COMPONENT CONTRACT

## Status
LOCKED production rule for Sequences 01-13.

## Non-negotiable rule
Every single implementation element used by a sequence must be individually inventoried and reviewed. No minimum-size exception exists. A two-word expression, constant, helper, API call, configuration value, permission, dependency, file path, protocol token, UI element, retry, timeout, parser, codec, serializer, or fallback is still a component and must be accounted for.

## Selection rule
For every component:
1. Inventory the exact implementation currently used.
2. Identify credible alternatives where alternatives exist.
3. Compare official support, maintenance status, Android/API compatibility, correctness, security, determinism, failure behavior, resource use, testability, and production evidence.
4. Reject deprecated, experimental, abandoned, undocumented, incompatible, or weaker candidates when a stronger proven candidate exists.
5. Select the highest-ranked candidate supported by evidence.
6. Do not call a candidate TOP-1 merely because it is popular or convenient.

## Proof rule
A component is PROVEN only when the repository has reproducible evidence appropriate to that component. Static inspection alone cannot prove runtime behavior. Runtime behavior cannot prove physical-device behavior. Emulator evidence cannot be relabeled as real-device evidence.

Evidence classes:
- STATIC: source/build/config contract verified.
- BUILD: compiler/package/artifact verification.
- RUNTIME: deterministic execution evidence.
- DEVICE: physical Android-device evidence.
- E2E: complete chain evidence.

## Gate rule
A sequence may PASS only when every component in its declared inventory has an acceptable proof record and the sequence's own runtime acceptance checks pass. If even one used component is UNPROVEN, the sequence remains FAIL/UNVERIFIED and the next sequence remains unavailable.

## UI rule
Only the current unlocked sequence action is visible. After a genuine PASS, the next sequence is revealed. A future sequence must not be exposed as an actionable option before its predecessor passes.

## Failure rule
No fail-fast diagnostic cell for the 13-sequence audit. Collect every finding, continue through the remaining checks, and write one complete evidence report. A failed check must include component, exact condition, observed result, severity, root-cause evidence when available, and repair/retest status.

## Anti-false-PASS rules
- Green CI is not a physical-device PASS.
- Build success is not feature success.
- Emulator success is not physical-device success.
- API availability is not functional proof.
- A UI label is not feature proof.
- A fallback is not equivalent to the requested primary capability.
- A numeric confidence percentage must not be invented.

## Sequence coverage
01 Startup / Self-Diagnostic
02 Mobile Connection / Permissions
03 Target APK Selection
04 Study Selected APK
05 Story Input
06 Operate Selected Target APK
07 Deep Target-App Understanding
08 Exact Scene Plan
09 Production Plan / Prompts
10 Audio / Voice / Music / Sound Effects
11 Assemble / Edit
12 Verify / Auto-Fix
13 Final Gallery Export

## Required final evidence
The final audit must produce one machine-readable report containing every discovered component, selected candidate, alternatives considered, proof class, proof result, failures, repairs, retests, and final sequence verdicts. No sequence may be marked FINAL PASS while any used component is missing from that inventory.
