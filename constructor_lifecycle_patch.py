from pathlib import Path

OLD = "    private val mainHandler = Handler(mainLooper)"
NEW = "    private lateinit var mainHandler: Handler"
MARKER = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n"
REPLACEMENT = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n        mainHandler = Handler(mainLooper)\n"


def patch(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if OLD in text:
        if text.count(OLD) != 1:
            raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: stale declaration count={text.count(OLD)} in {path}")
        if MARKER not in text:
            raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: onCreate marker not found in {path}")
        text = text.replace(OLD, NEW, 1).replace(MARKER, REPLACEMENT, 1)
        path.write_text(text, encoding="utf-8")
        return True
    if NEW in text and REPLACEMENT in text:
        return False
    raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: expected handler declaration not found in {path}")

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
