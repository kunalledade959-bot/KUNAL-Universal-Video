#!/usr/bin/env python3
"""KUNAL Universal Video - Pro Repair V4.

Canonical production build entrypoint.

V4 owns the production Android controller contract. It starts from
activity_fixed.kt, applies only the deterministic constructor/package-manager
hardening required by the verified production path, then injects that exact
source into the proven V3 build engine. No regex patch workflow or repair loop
is involved.

Fail closed: the source must match one of the known production forms, the
result must contain launcher-based target discovery and lifecycle-safe handler
initialization, and the forbidden synchronous installed-application
enumeration must be absent before the build engine runs.
"""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent
CANONICAL_ACTIVITY = ROOT / "activity_fixed.kt"
BASE = ROOT / "pro_repair_v3.py"

if not CANONICAL_ACTIVITY.is_file():
    raise SystemExit(f"CANONICAL_ACTIVITY_NOT_FOUND: {CANONICAL_ACTIVITY}")
if not BASE.is_file():
    raise SystemExit(f"BASE_BUILD_ENGINE_NOT_FOUND: {BASE}")

activity = CANONICAL_ACTIVITY.read_text(encoding="utf-8")

OLD_HANDLER = "    private val mainHandler = Handler(mainLooper)"
NEW_HANDLER = "    private lateinit var mainHandler: Handler"
OLD_ONCREATE = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n"
NEW_ONCREATE = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n        mainHandler = Handler(mainLooper)\n"

OLD_LOAD = '''    private fun loadApps() {
        apps = packageManager.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0))
            .filter { it.packageName != packageName }
            .sortedBy { packageManager.getApplicationLabel(it).toString().lowercase() }
        targetSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            apps.map { "${packageManager.getApplicationLabel(it)}\\n${it.packageName}" }
        )
        val saved = prefs().getString(TARGET, "") ?: ""
        val idx = apps.indexOfFirst { it.packageName == saved }
        if (idx >= 0) targetSpinner.setSelection(idx)
    }'''

NEW_LOAD = '''    private fun loadApps() {
        // PackageManager enumeration can contend with system_server when done on
        // the Activity main thread. Discover only launchable targets off-thread,
        // then perform the small UI adapter update back on the main thread.
        status.text = "Loading target apps…"
        Thread {
            val discovered = try {
                val launcher = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                packageManager.queryIntentActivities(
                    launcher,
                    PackageManager.ResolveInfoFlags.of(0)
                ).asSequence()
                    .mapNotNull { it.activityInfo?.applicationInfo }
                    .filter { it.packageName != packageName }
                    .distinctBy { it.packageName }
                    .sortedBy { it.loadLabel(packageManager).toString().lowercase() }
                    .toList()
            } catch (_: Exception) {
                emptyList()
            }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                apps = discovered
                targetSpinner.adapter = ArrayAdapter(
                    this,
                    android.R.layout.simple_spinner_dropdown_item,
                    apps.map { "${it.loadLabel(packageManager)}\\n${it.packageName}" }
                )
                val saved = prefs().getString(TARGET, "") ?: ""
                val idx = apps.indexOfFirst { it.packageName == saved }
                if (idx >= 0) targetSpinner.setSelection(idx)
                status.text = "Target apps ready • ${apps.size} launchable apps"
            }
        }.start()
    }'''

if OLD_HANDLER in activity:
    if activity.count(OLD_HANDLER) != 1:
        raise SystemExit("CONSTRUCTOR_LIFECYCLE_CONTRACT_FAIL: handler declaration count")
    if activity.count(OLD_ONCREATE) != 1:
        raise SystemExit("CONSTRUCTOR_LIFECYCLE_CONTRACT_FAIL: onCreate marker count")
    activity = activity.replace(OLD_HANDLER, NEW_HANDLER, 1)
    activity = activity.replace(OLD_ONCREATE, NEW_ONCREATE, 1)
elif NEW_HANDLER not in activity or NEW_ONCREATE not in activity:
    raise SystemExit("CONSTRUCTOR_LIFECYCLE_CONTRACT_FAIL: unsupported handler form")

if OLD_LOAD in activity:
    if activity.count(OLD_LOAD) != 1:
        raise SystemExit("PACKAGE_MANAGER_UI_CONTRACT_FAIL: loadApps count")
    activity = activity.replace(OLD_LOAD, NEW_LOAD, 1)
elif NEW_LOAD not in activity:
    raise SystemExit("PACKAGE_MANAGER_UI_CONTRACT_FAIL: unsupported loadApps form")

required = (
    "queryIntentActivities",
    "Intent.CATEGORY_LAUNCHER",
    "getLaunchIntentForPackage",
    "mainHandler",
    "runOnUiThread",
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

# Keep the complete verified Gradle plugin contract instead of relying on the
# V3 embedded defaults, which previously regressed.
engine.APP_GRADLE = r'''plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android { namespace="com.kunal.universalvideo"; compileSdk=35; defaultConfig { applicationId="com.kunal.universalvideo"; minSdk=26; targetSdk=35; versionCode=3; versionName="3.0.0" }; compileOptions { sourceCompatibility=JavaVersion.VERSION_17; targetCompatibility=JavaVersion.VERSION_17 } }
kotlin { jvmToolchain(17) }
dependencies { implementation("androidx.core:core-ktx:1.15.0"); implementation("androidx.appcompat:appcompat:1.7.0"); implementation("androidx.activity:activity-ktx:1.10.1") }'''
engine.ROOT_GRADLE = r'''plugins { id("com.android.application") version "8.7.3" apply false; id("org.jetbrains.kotlin.android") version "2.0.21" apply false }'''
engine.ACTIVITY = activity

print("PRO_REPAIR_V4_CANONICAL_ACTIVITY_HARDENED=PASS", flush=True)
print("PRO_REPAIR_V4_KNOWN_GOOD_GRADLE=PASS", flush=True)
engine.main()
