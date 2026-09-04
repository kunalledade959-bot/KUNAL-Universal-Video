#!/usr/bin/env python3
"""KUNAL Universal Video - Pro Repair V4.

Canonical production build entrypoint.

The previous architecture kept a second generator-patching layer that edited
an embedded copy of MainActivity at runtime. That created a fragile dependency
on generator paths and allowed the repair chain itself to become the blocker.
V4 removes that layer: activity_fixed.kt is the canonical Android controller
source, and the proven V3 build engine is executed with that source injected
as its authoritative ACTIVITY payload.
Fail closed: the canonical source must exist and must contain the production
launch-target discovery contract before the underlying build engine runs.
"""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parent
CANONICAL_ACTIVITY = ROOT / "activity_fixed.kt"
BASE = ROOT / "pro_repair_v3.py"

if not CANONICAL_ACTIVITY.is_file():
    raise SystemExit(f"CANONICAL_ACTIVITY_NOT_FOUND: {CANONICAL_ACTIVITY}")
if not BASE.is_file():
    raise SystemExit(f"BASE_BUILD_ENGINE_NOT_FOUND: {BASE}")

activity = CANONICAL_ACTIVITY.read_text(encoding="utf-8")
required = (
    "queryIntentActivities",
    "CATEGORY_LAUNCHER",
    "getLaunchIntentForPackage",
    "mainHandler",
)
for token in required:
    if token not in activity:
        raise SystemExit(f"CANONICAL_ACTIVITY_CONTRACT_MISSING: {token}")
if "getInstalledApplications" in activity:
    raise SystemExit("FORBIDDEN_SYNC_INSTALLED_APPLICATION_ENUMERATION")

spec = importlib.util.spec_from_file_location("kuv_pro_repair_v3_engine", BASE)
if spec is None or spec.loader is None:
    raise SystemExit("BUILD_ENGINE_IMPORT_FAILED")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

# V3's embedded Gradle payload had regressed from the known-good production
# contract: it omitted the Kotlin Android plugin and kotlin jvmToolchain(17).
# Keep the V4 canonical entrypoint tied to the verified production toolchain.
engine.APP_GRADLE = r'''plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android { namespace="com.kunal.universalvideo"; compileSdk=35; defaultConfig { applicationId="com.kunal.universalvideo"; minSdk=26; targetSdk=35; versionCode=3; versionName="3.0.0" }; compileOptions { sourceCompatibility=JavaVersion.VERSION_17; targetCompatibility=JavaVersion.VERSION_17 } }
kotlin { jvmToolchain(17) }
dependencies { implementation("androidx.core:core-ktx:1.15.0"); implementation("androidx.appcompat:appcompat:1.7.0"); implementation("androidx.activity:activity-ktx:1.10.1") }'''

# Replace the embedded activity definition at the source of truth instead of
# maintaining another regex-based patcher. All V3 build/static verification
# remains active and now validates the canonical production activity.
engine.ACTIVITY = activity

print("PRO_REPAIR_V4_CANONICAL_ACTIVITY=PASS", flush=True)
print("PRO_REPAIR_V4_KNOWN_GOOD_GRADLE=PASS", flush=True)
engine.main()
