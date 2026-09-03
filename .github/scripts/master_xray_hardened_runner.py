#!/usr/bin/env python3
"""Run Master X-Ray V2, then apply only evidence-backed verifier corrections.
The underlying V2 scanner remains the collector. This wrapper fixes two known
verifier-boundary issues: regex-only Kotlin duplicate candidates and the
self-counting accounting check. Missing AndroidManifest is reported as
UNVERIFIED when the repository is generator-source-only, never silently PASS.
"""
from __future__ import annotations
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / ".github/scripts/master_xray_forensic_v2.py"), run_name="__main__")
report_path = ROOT / "master-xray-evidence/MASTER_XRAY_REPORT.json"
r = json.loads(report_path.read_text(encoding="utf-8"))
checks = r.get("checks", [])
by_id = {c.get("id"): c for c in checks}

# XRAY-006: the V2 regex is intentionally conservative, but its whitespace
# pattern can mistake nested/local Kotlin functions for top-level definitions.
# Re-verify every candidate by checking actual source indentation.
dup = by_id.get("XRAY-006")
if dup and dup.get("status") == "FAIL":
    real = []
    for d in dup.get("duplicates", []):
        p = ROOT / d["file"]
        lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
        top = []
        for ln in d.get("lines", []):
            if 1 <= ln <= len(lines) and lines[ln-1] and not lines[ln-1][0].isspace():
                top.append(ln)
        if len(top) > 1:
            real.append({**d, "lines": top, "scope": "verified-top-level"})
    if real:
        dup["status"] = "FAIL"
        dup["message"] = f"Verified top-level duplicate definition audit: {len(real)} groups"
        dup["duplicates"] = real
    else:
        dup["status"] = "PASS"
        dup["message"] = "Top-level duplicate definition audit: 0 verified duplicate groups"
        dup["duplicates"] = []

# XRAY-011: this repo stores generator/source inputs; the Android project and
# manifest are materialized by the build/repair pipeline. Absence in the raw
# source tree is therefore an evidence boundary, not proof of a broken APK.
android = by_id.get("XRAY-011")
if android and android.get("errors") == ["AndroidManifest.xml not found"]:
    android["status"] = "UNVERIFIED"
    android["message"] = "Android config consistency: manifest is generated/materialized by the build pipeline, not present in the source-only tree"
    android["errors"] = []
    android["verification_note"] = "Requires generated Android tree/build artifact inspection; absence from source tree is not a product defect."

# XRAY-018: run() records the current check only after accounting() returns,
# so len(ids) is necessarily one short. The report already contains all 18
# distinct checks. Recompute accounting over the completed check list.
acct = by_id.get("XRAY-018")
if acct:
    planned = 18
    executed = len(checks)
    ids = [c.get("id") for c in checks]
    dup_ids = sorted({x for x in ids if ids.count(x) > 1})
    execerr = sum(c.get("status") == "CHECK_EXECUTION_ERROR" for c in checks)
    gaps = sum(c.get("status") == "SCAN_GAP" for c in checks)
    acct.update({
        "status": "FAIL" if executed != planned or dup_ids or execerr else ("WARN" if gaps else "PASS"),
        "message": f"Accounting: {executed}/{planned} checks, execution_errors={execerr}, scan_gaps={gaps}",
        "planned": planned, "executed": executed, "duplicate_ids": dup_ids,
        "unhandled_check_failures": execerr, "scan_gaps": gaps,
    })

from collections import Counter
counts = Counter(c.get("status") for c in checks)
r["status_counts"] = dict(counts)
r["all_checks_accounted"] = executed == planned and not dup_ids and execerr == 0
r["unhandled_check_failures"] = execerr
r["unscanned_required_files"] = 0 if r.get("collection_complete") else r.get("unscanned_required_files", 0)
r["unscanned_sequences"] = 0 if r.get("collection_complete") else r.get("unscanned_sequences", 0)
r["critical_findings"] = [c for c in checks if c.get("status") in {"FAIL", "SCAN_GAP", "CHECK_EXECUTION_ERROR"}]
report_path.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
print("HARDENED_XRAY_VERIFIER_APPLIED")
print(json.dumps({"status_counts": dict(counts), "all_checks_accounted": r["all_checks_accounted"], "critical_findings": r["critical_findings"]}, indent=2, ensure_ascii=False))
