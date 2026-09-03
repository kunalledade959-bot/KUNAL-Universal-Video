#!/usr/bin/env bash
# KUNAL Universal Video: one-shot production repair cell.
# Goal: collect the complete failure picture once, repair all evidence-backed
# root causes in one agent pass, then prove the result with the authoritative gate.
# Never weakens tests and never writes PASS itself.
set -u -o pipefail

ROOT="$(pwd)"
EVIDENCE="$ROOT/ai-evidence/one-shot"
mkdir -p "$EVIDENCE"

log(){ printf '[ONE-SHOT] %s\n' "$*" | tee -a "$EVIDENCE/one-shot.log"; }
fail(){ log "FAIL: $*"; exit 1; }

log "Starting complete diagnostic snapshot."
git status --short > "$EVIDENCE/git-status-before.txt" 2>&1 || true
git diff --check > "$EVIDENCE/git-diff-check-before.txt" 2>&1 || true
git log -1 --format='%H%n%s' > "$EVIDENCE/head.txt" 2>&1 || true

# Collect the latest triggering evidence when present. The script is also usable
# manually, so every diagnostic command is best-effort and non-fatal here.
for f in \
  e2e-FAIL.txt e2e-PASS.txt e2e-start.txt e2e-log.txt e2e-install.txt \
  e2e-ui-top.xml e2e-diagnostics-crash.txt e2e-diagnostics-logcat.txt \
  e2e-diagnostics-activity.txt e2e-diagnostics-package.txt \
  e2e-diagnostics-boot.txt e2e-diagnostics-devices.txt \
  e2e-emulator-failure.txt e2e-boot-log.txt avd-create.log; do
  [[ -f "$f" ]] && cp -f "$f" "$EVIDENCE/$(basename "$f")" || true
done

if command -v adb >/dev/null 2>&1; then
  adb devices -l > "$EVIDENCE/adb-devices.txt" 2>&1 || true
  adb shell getprop sys.boot_completed > "$EVIDENCE/boot-completed.txt" 2>&1 || true
  adb shell dumpsys activity activities > "$EVIDENCE/activity.txt" 2>&1 || true
  adb shell dumpsys window windows > "$EVIDENCE/windows.txt" 2>&1 || true
  adb logcat -d -t 2500 > "$EVIDENCE/logcat.txt" 2>&1 || true
fi

log "Running deterministic source/build preflight before AI repair."
python3 preflight_patch.py > "$EVIDENCE/preflight.log" 2>&1 || true
python3 constructor_lifecycle_patch.py > "$EVIDENCE/constructor-patch.log" 2>&1 || true
python3 stage11_hardening_v2.py > "$EVIDENCE/stage11-patch.log" 2>&1 || true

git diff --check > "$EVIDENCE/git-diff-check-pre-agent.txt" 2>&1 || true
git status --short > "$EVIDENCE/git-status-pre-agent.txt" 2>&1 || true

if ! command -v copilot >/dev/null 2>&1; then
  fail "Copilot CLI is unavailable. The deterministic diagnostics were still collected."
fi

log "Starting ONE comprehensive repair pass."
set +e
copilot --autopilot --yolo --max-autopilot-continues 24 -p "
You are the senior production Android repair engineer for KUNAL Universal Video.
This is ONE comprehensive repair pass, not a trial-and-error patch loop.

PRIMARY OBJECTIVE:
Inspect the COMPLETE accumulated evidence first, build a root-cause map, then repair ALL
proven root causes that can be fixed safely in this pass. Do not stop at the first symptom.
After repairing, run practical static/build checks. The repository must remain production-grade.

READ IN THIS ORDER:
1. Every file under ai-evidence/one-shot/.
2. Any ai-evidence from the triggering run if present.
3. Current git diff/status and latest commit.
4. KUNAL_UNIVERSAL_VIDEO_ANDROID_PROJECT_FIXED.zip and all production build/repair scripts.
5. .github/scripts/self-healing-gate.sh and full-e2e-emulator.sh.
6. The Android source, especially MainActivity, StageGate, controller/accessibility,
   MediaProjection, TTS/audio, assembly, verification and gallery export paths.

ROOT-CAUSE RULES:
- Separate infrastructure/emulator/SystemUI failures from Android app failures.
- Separate UI-observation failures from real app behavior failures.
- Group correlated symptoms under their first proven root cause.
- Never repair a symptom caused by an unhealthy emulator as if it were an app bug.
- If the evidence proves multiple independent defects, fix all of them in this pass.
- If a defect is not proven, do not guess or make speculative changes.

QUALITY BAR:
- Production-grade only.
- Never weaken, skip, delete, bypass, or fake an assertion.
- Never manufacture e2e-PASS.txt.
- Never make the gate easier merely to obtain PASS.
- Preserve com.kunal.universalvideo and the intended 13-stage architecture.
- Preserve target-app control, accessibility, MediaProjection, TTS/audio, video assembly,
  verification and gallery export.
- Prefer the smallest correct changes with deterministic/idempotent behavior.
- Do not touch secrets or credentials.
- CI/workflow changes are allowed only when evidence proves the defect is in CI/infrastructure.

IMPORTANT CURRENT FAILURE CLASSIFICATION:
If the evidence contains SystemUI ANR, emulator health failure, ADB instability, or similar,
repair the emulator/gate health handling first. Do NOT blindly change Stage-1 UI because a
broken SystemUI can make an otherwise RESUMED app hierarchy unreadable.

AUTONOMOUS FALLBACK:
If the AI service reports quota/rate-limit/unavailable instead of performing the repair,
write that exact reason to ai-evidence/one-shot/agent-failure.txt and exit nonzero. Do not
pretend the repair happened.

Before finishing, write ai-evidence/one-shot/repair.md containing:
- root causes found
- files changed
- why each change is correct
- checks executed and their results
- remaining blockers, if any
" > "$EVIDENCE/copilot.log" 2>&1
AGENT_STATUS=$?
set -e

printf '%s\n' "$AGENT_STATUS" > "$EVIDENCE/agent-exit-code.txt"

git diff --check > "$EVIDENCE/git-diff-check-after-agent.txt" 2>&1 || true
git status --short > "$EVIDENCE/git-status-after-agent.txt" 2>&1 || true

if [[ "$AGENT_STATUS" != "0" ]]; then
  log "Repair agent failed with exit code $AGENT_STATUS. No PASS will be claimed."
  exit 20
fi

log "Running the authoritative production + emulator + full E2E gate."
rm -f e2e-PASS.txt
set +e
bash .github/scripts/self-healing-gate.sh > "$EVIDENCE/final-gate.log" 2>&1
GATE_STATUS=$?
set -e
printf '%s\n' "$GATE_STATUS" > "$EVIDENCE/final-gate-exit-code.txt"

for f in e2e-PASS.txt e2e-FAIL.txt e2e-start.txt e2e-log.txt e2e-crash-logcat.txt e2e-ui-top.xml e2e-emulator-failure.txt e2e-boot-log.txt; do
  [[ -f "$f" ]] && cp -f "$f" "$EVIDENCE/$(basename "$f")" || true
done

git diff --check > "$EVIDENCE/final-git-diff-check.txt" 2>&1 || true
git status --short > "$EVIDENCE/final-git-status.txt" 2>&1 || true

if [[ "$GATE_STATUS" == "0" && -f e2e-PASS.txt ]] && grep -q 'PASS' e2e-PASS.txt; then
  log "ONE_SHOT_PRODUCTION_REPAIR_PASS"
  exit 0
fi

log "ONE_SHOT_PRODUCTION_REPAIR_FAIL: authoritative gate did not produce verified PASS."
exit 30
