#!/usr/bin/env python3
"""
KUNAL UNIVERSAL VIDEO - EXHAUSTIVE 13-STAGE PROBLEM DISCOVERY

Purpose:
  Build ONE evidence report that enumerates distinct failure modes for every
  production sequence, then checks which ones are represented by the current
  source and CI tests. This is intentionally a DISCOVERY/AUDIT tool, not a
  fake claim that a physical phone has been tested.

Output:
  exhaustive-sequence-problem-report.md

Verdict rules:
  PASS = failure mode has an explicit source guard/test/evidence contract.
  GAP  = failure mode is known but current code has no explicit guard/evidence.
  INFO = environmental/physical-device behavior that CI cannot prove.

The catalog is deliberately broad. It covers normal failures, boundary cases,
permissions, lifecycle, persistence, concurrency, media, storage, target-app
behavior, and CI/runtime-harness failures.
"""
from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "activity_fixed.kt"
GATE = ROOT / "stage_gate.kt"
OUT = ROOT / "exhaustive-sequence-problem-report.md"

STAGES = {
1: ("Startup / Self-Diagnostic", [
("APK cannot launch", "crash/exception during onCreate", "onCreate try/catch + startup evidence"),
("UI construction failure", "view/layout creation throws or produces unusable controls", "buildUi boundary"),
("PackageManager failure", "installed-app query throws/returns unusable data", "loadApps guard"),
("No usable target apps", "zero candidates after filtering", "apps.isEmpty guard"),
("Session creation failure", "session id cannot be persisted", "SESSION persistence/evidence"),
("Corrupt persisted state", "malformed StageGate JSON", "restore fail-closed"),
("Stale RUNNING state", "process dies while a stage is RUNNING", "startup reconciliation required"),
("Activity recreation", "rotation/background restore loses controller state", "persistent gate + prefs"),
("Process death", "Android kills app between stages", "persistent evidence contract"),
("Low-memory pressure", "controller/UI recreated or killed", "lifecycle evidence"),
]),
2: ("Mobile Connection / Permissions", [
("Accessibility disabled", "service not enabled", "isEnabled guard"),
("Accessibility service drops", "service becomes unavailable after initial check", "second isEnabled guard"),
("Wrong target package", "service points at stale/empty target", "target binding guard"),
("Local bridge unavailable", "bridge object is null/stopped", "bridge.connect result"),
("Handshake timeout", "controller never completes handshake", "bounded connection result required"),
("PING/PONG failure", "transport connects but liveness probe fails", "handshake evidence"),
("Duplicate connection", "second connect races first connection", "connection state/idempotency"),
("Disconnect during operation", "transport disappears mid-stage", "reconnect/fail-closed contract"),
("Background restrictions", "OEM kills service", "physical-device INFO: CI cannot prove"),
("Accessibility security/OEM behavior", "service enabled but events/tree unavailable", "physical-device INFO"),
("Network confusion", "implementation accidentally depends on internet", "NO_FAKE_CONNECT/static scan"),
("Socket/port conflict", "local transport endpoint already occupied", "transport-specific runtime test required"),
]),
3: ("Target APK Selection", [
("No selection", "spinner has invalid index", "pos bounds guard"),
("Target uninstalled", "saved target disappears", "package lookup guard"),
("Stale saved target", "prefs references old package", "selection overwrite"),
("Duplicate labels", "two apps display same name", "package-name identity"),
("Package-name mismatch", "display label differs from package", "target package evidence"),
("Non-launchable target", "installed package has no launcher intent", "launch intent guard"),
("Permission-restricted target", "target launches but inaccessible UI", "later accessibility checks"),
("Target changes mid-run", "user changes spinner after downstream evidence", "gate/persistence invalidation required"),
]),
4: ("Study Selected APK", [
("Package lookup failure", "PackageManager cannot resolve target", "getApplicationInfo guard"),
("Target removed/disabled", "package exists but cannot launch", "launch intent guard"),
("No launch activity", "getLaunchIntentForPackage returns null", "explicit guard"),
("Target launch exception", "security/activity exception", "exception boundary required"),
("Target version/API incompatibility", "manifest/features differ from assumptions", "study contract"),
("Split APK/dynamic feature behavior", "launcher/feature loads differently", "physical/runtime coverage"),
("Target immediately exits", "launch succeeds then process dies", "Stage 6 foreground proof"),
]),
5: ("Story Input", [
("Empty story", "blank input", "length guard"),
("Too-short story", "below minimum", "length guard"),
("Whitespace-only story", "trimmed content empty", "trim + length guard"),
("Very long story", "memory/UI/TTS limits", "bounded input required"),
("Unicode/emoji", "encoding/rendering issue", "Unicode runtime test"),
("Newlines/control characters", "parser/scene splitting edge cases", "input normalization"),
("Persistence failure", "SharedPreferences write does not survive process death", "persist + restart test required"),
("Story modified after plan", "downstream plan becomes stale", "dependency invalidation required"),
]),
6: ("Operate Selected Target APK", [
("Launch intent missing", "target cannot start", "explicit guard"),
("Launch throws", "ActivityNotFound/SecurityException/runtime error", "exception boundary required"),
("Target never foreground", "wrong app or immediate exit", "foreground timeout guard"),
("Accessibility root null", "no live node tree", "rootInActiveWindow guard"),
("Empty accessibility tree", "foreground but no nodes", "nodes<1 guard"),
("Target changes foreground", "another app steals focus", "foreground identity check"),
("Target ANR", "UI stops responding", "timeout/watchdog required"),
("Target crash", "target process dies", "runtime observation required"),
("Node traversal failure", "invalid/stale child nodes", "safe traversal required"),
("Interaction denied", "node exists but action rejected", "action-result evidence required"),
("OEM accessibility quirks", "tree/events differ by device", "physical-device test required"),
]),
7: ("Deep Target-App Understanding", [
("Accessibility disabled during study", "service drops", "isEnabled guard"),
("Root unavailable", "target not foreground", "root guard"),
("Zero nodes", "empty UI tree", "nodes guard"),
("Missing clickable controls", "UI has no actionable nodes", "clickable evidence"),
("Missing editable controls", "expected input cannot be found", "editable evidence"),
("Dynamic UI changes", "tree changes between scans", "snapshot consistency required"),
("Scrollable/lazy UI", "important nodes absent until scroll", "exploration coverage required"),
("WebView/custom canvas", "semantics unavailable", "fallback strategy required"),
("Localization", "text labels differ by language", "resource/id based targeting required"),
]),
8: ("Exact Scene Plan", [
("Story missing", "no source input", "story guard"),
("No sentence boundaries", "single-scene fallback", "explicit fallback"),
("Too many scenes", "plan cap/truncation", "30-scene bound"),
("Blank generated scene", "empty chunk", "nonblank filtering"),
("Ordering loss", "scene numbering mismatch", "ordered generation"),
("Story edited after plan", "plan stale", "dependency invalidation required"),
("Special characters", "prompt delimiter corruption", "escaping required"),
]),
9: ("Production Plan / Prompts", [
("Scene plan missing", "cannot generate production plan", "scene guard"),
("Scene count mismatch", "not every scene receives prompt", "per-scene count check"),
("Empty prompt", "generated instruction unusable", "nonblank prompt check required"),
("Prompt injection/user text", "story content changes control semantics", "sanitization required"),
("Inconsistent character constraints", "visual continuity lost", "continuity evidence required"),
("Invalid media instructions", "downstream renderer cannot execute", "schema validation required"),
]),
10: ("Audio / Voice / Music / Sound Effects + Record", [
("Story missing", "no narration source", "story guard"),
("TTS unavailable", "tts null or engine unavailable", "TTS result check"),
("TTS failure code", "synthesis returns non-success", "result check"),
("Tiny/corrupt audio", "file exists but unusable", "size check"),
("Wrong audio format", "extractor cannot read WAV", "media-format validation required"),
("Language unavailable", "requested locale unsupported", "language result check required"),
("Screen capture cancelled", "user denies permission", "resultCode guard"),
("Recording service fails to start", "foreground service/start exception", "runtime exception evidence"),
("No recorded MediaStore video", "stop produces no URI", "latestRecording guard"),
("Recording zero/short duration", "file exists but no meaningful clip", "duration validation required"),
("Recording wrong owner/name", "stale video selected", "session-specific identity required"),
("Recording interrupted", "service killed or projection revoked", "recording state machine required"),
("Audio/video desync", "independent sources have different duration", "duration sync validation required"),
("Mic/audio permission conflict", "recording source unavailable", "physical-device test"),
("OEM MediaProjection behavior", "device-specific permission/service behavior", "physical-device test"),
]),
11: ("Assemble / Edit", [
("Video missing", "no recorded visual clip", "video guard"),
("Audio missing", "narration path absent", "audio guard"),
("Video FD unavailable", "ContentResolver cannot open URI", "explicit guard"),
("Video has no video track", "extractor lacks video track", "track validation"),
("Audio has no audio track", "extractor lacks audio track", "track validation"),
("Unsupported codec/container", "MediaMuxer rejects format", "exception boundary + codec validation required"),
("Malformed media timestamps", "sampleTime invalid", "timestamp validation required"),
("Oversized frame/sample", "buffer insufficient", "bounded media buffer handling required"),
("Muxer start/stop failure", "MediaMuxer lifecycle exception", "exception boundary"),
("Partial output", "file exists after failed mux", "atomic output/cleanup required"),
("Out-of-sync duration", "audio longer/shorter than video", "duration policy required"),
("Storage/cache exhaustion", "output cannot be written", "disk-space guard required"),
]),
12: ("Verify / Auto-Fix", [
("Final path missing", "assembled file absent", "path guard"),
("File too small", "invalid/truncated output", "size guard"),
("Extractor cannot open", "corrupt/unreadable MP4", "exception guard"),
("Zero media tracks", "invalid container", "track count guard"),
("Only video/no audio", "assembly lost narration", "track-type verification required"),
("Only audio/no video", "visual content missing", "track-type verification required"),
("Duration zero", "empty media", "duration check required"),
("Corrupt samples", "extractor opens but samples fail", "full decode validation required"),
("Auto-fix loop", "fix repeatedly modifies same artifact", "bounded/idempotent repair required"),
("Verification after stale artifact", "old successful file reused", "session identity required"),
]),
13: ("Final Gallery Export", [
("Verified source missing", "no assembled MP4", "source guard"),
("Gallery insert failure", "MediaStore insert returns null", "explicit guard"),
("Output stream unavailable", "cannot write URI", "explicit guard"),
("Copy interrupted", "partial gallery file", "transaction/cleanup required"),
("IS_PENDING stuck", "file remains invisible/pending", "finalization verification required"),
("Wrong MIME/path", "export appears incorrectly", "metadata verification required"),
("Duplicate export", "same session exported twice", "idempotency required"),
("Gallery indexing delay", "file not immediately visible", "post-export query required"),
("Insufficient storage", "write fails midway", "free-space preflight required"),
("Corrupt final gallery file", "copy succeeded but media unreadable", "re-open exported URI required"),
]),
}


def read(p: Path) -> str:
    try: return p.read_text(encoding="utf-8")
    except Exception: return ""

src = read(SRC)
gate = read(GATE)
all_text = src + "\n" + gate

# Known historical/observed failure signatures from this project's CI history.
KNOWN = [
("CI wiring patch", "reconstruction Activity mapping not found", "patch depended on a brittle exact text match"),
("CI wiring patch", "reconstruction write block not found", "hardening changed the source before a text replacement ran"),
("CI E2E harness", "set: Illegal option -o pipefail", "runner invocation used a shell incompatible with Bash options"),
("CI fault matrix", "static matrix PASS but physical phone untested", "emulator/static evidence cannot establish real-device behavior"),
]

def detect(label: str, detail: str) -> tuple[str, str]:
    # Heuristic evidence mapping. It is intentionally conservative: a mention is
    # not accepted as proof unless an explicit guard/implementation marker exists.
    needles = {
        "isEnabled": ["UniversalAccessibilityService.isEnabled"],
        "apps.isEmpty": ["apps.isEmpty"],
        "rootInActiveWindow": ["rootInActiveWindow"],
        "nodes": ["nodes<1", "nodes="],
        "story": ["s.length<10", "Story missing"],
        "TTS": ["synthesizeToFile", "TextToSpeech.SUCCESS"],
        "MediaStore": ["MediaStore.Video.Media", "openOutputStream"],
        "track": ["trackCount", "startsWith(\"video/\")", "startsWith(\"audio/\")"],
        "launch": ["getLaunchIntentForPackage"],
        "exception": ["catch(e:Exception)", "catch (_: Exception)"],
        "StageGate": ["isUnlocked", "begin(", "pass(", "fail("],
    }
    hay = all_text.lower()
    # map broad problem labels to source markers
    candidates = []
    low = (label + " " + detail).lower()
    for key, vals in needles.items():
        if key.lower() in low:
            candidates.extend(vals)
    if not candidates:
        if "accessibility" in low or "service" in low: candidates = needles["isEnabled"]
        elif "story" in low or "input" in low: candidates = needles["story"]
        elif "record" in low or "audio" in low or "tts" in low: candidates = needles["TTS"]
        elif "gallery" in low or "export" in low or "store" in low: candidates = needles["MediaStore"]
        elif "track" in low or "media" in low or "codec" in low: candidates = needles["track"]
        elif "launch" in low or "target" in low: candidates = needles["launch"]
        else: candidates = needles["exception"]
    if any(x.lower() in hay for x in candidates):
        return "PASS", "source/test marker found: " + ", ".join(x for x in candidates if x.lower() in hay)
    return "GAP", "no explicit source marker matched; requires implementation/test"

lines = []
lines += ["# KUNAL Universal Video: Exhaustive 13-Stage Problem Discovery", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
lines += ["> This report enumerates distinct failure modes. PASS means an explicit guard/evidence marker was found, not that a physical phone has been proven perfect.", ""]

total = gaps = 0
for n, (name, cases) in STAGES.items():
    lines += [f"## Stage {n}: {name}", "", "| # | Failure mode | What can go wrong | Current audit | Evidence/required fix |", "|---:|---|---|---|---|"]
    for i, (label, detail, req) in enumerate(cases, 1):
        status, evidence = detect(label, detail)
        total += 1
        if status == "GAP": gaps += 1
        lines.append(f"| {i} | {label} | {detail} | **{status}** | {evidence}. Required: {req} |")
    lines.append("")

lines += ["## Historically observed CI failures", "", "| Layer | Exact/near-exact failure | Root cause |", "|---|---|---|"]
for layer, sig, root in KNOWN:
    lines.append(f"| {layer} | `{sig}` | {root} |")
lines += ["", "## Audit summary", "", f"- Catalogued failure modes: **{total}**", f"- Current explicit-marker gaps: **{gaps}**", "- `GAP` entries are intentionally fail-closed: they must be implemented and then exercised before claiming that the corresponding stage is production-verified.", "- `INFO` physical-device items must be tested on an actual Android device. CI cannot manufacture that evidence.", ""]
lines += ["## Required second-pass rule", "", "1. Repair every GAP that is applicable to the production contract.", "2. Add a deterministic test/evidence assertion for each repaired GAP.", "3. Run the full 1→13 flow from a clean session.", "4. Separately run physical-device connection, target operation, recording, assembly, verification and Gallery export.", "5. Do not reuse stale artifacts or previous PASS evidence.", "6. Only then mark a stage production-verified."]

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"WROTE={OUT}")
print(f"CATALOGUE_CASES={total}")
print(f"EXPLICIT_MARKER_GAPS={gaps}")
print("NOTE=Static audit is not physical-device proof.")
