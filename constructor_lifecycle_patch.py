from pathlib import Path

OLD = "    private val mainHandler = Handler(mainLooper)"
NEW = "    private lateinit var mainHandler: Handler"
MARKER = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n"
REPLACEMENT = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n        mainHandler = Handler(mainLooper)\n"

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


def patch(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    changed = False
    if OLD in text:
        if text.count(OLD) != 1:
            raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: stale declaration count={text.count(OLD)} in {path}")
        if MARKER not in text:
            raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: onCreate marker not found in {path}")
        text = text.replace(OLD, NEW, 1).replace(MARKER, REPLACEMENT, 1)
        changed = True
    elif not (NEW in text and REPLACEMENT in text):
        raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: expected handler declaration not found in {path}")
    if OLD_LOAD in text:
        if text.count(OLD_LOAD) != 1:
            raise SystemExit(f"PACKAGE_MANAGER_UI_FIX_FAIL: loadApps count={text.count(OLD_LOAD)} in {path}")
        text = text.replace(OLD_LOAD, NEW_LOAD, 1)
        print(f"PACKAGE_MANAGER_UI_FIX: APPLIED in {path}")
        changed = True
    elif NEW_LOAD in text:
        print(f"PACKAGE_MANAGER_UI_FIX: ALREADY_APPLIED in {path}")
    else:
        raise SystemExit(f"PACKAGE_MANAGER_UI_FIX_FAIL: expected loadApps implementation not found in {path}")
    path.write_text(text, encoding="utf-8")
    return changed

paths = [
    Path("activity_fixed.kt"),
    Path("KUNAL_UNIVERSAL_VIDEO_PRO_V3_STAGE/android-controller/app/src/main/java/com/kunal/universalvideo/MainActivity.kt"),
]

changed = False
for path in paths:
    changed = patch(path) or changed

if changed:
    print("CONSTRUCTOR_LIFECYCLE_FIX: APPLIED")
else:
    print("CONSTRUCTOR_LIFECYCLE_FIX: ALREADY_APPLIED")
