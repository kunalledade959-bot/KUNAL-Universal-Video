from pathlib import Path

path = Path("activity_fixed.kt")
text = path.read_text(encoding="utf-8")

old = "    private val mainHandler = Handler(mainLooper)"
new = "    private lateinit var mainHandler: Handler"

if old in text:
    text = text.replace(old, new, 1)
    marker = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n"
    replacement = "    override fun onCreate(b: Bundle?) {\n        super.onCreate(b)\n        mainHandler = Handler(mainLooper)\n"
    if marker not in text:
        raise SystemExit("CONSTRUCTOR_LIFECYCLE_FIX_FAIL: onCreate marker not found")
    text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")
    print("CONSTRUCTOR_LIFECYCLE_FIX: APPLIED")
elif new in text and "mainHandler = Handler(mainLooper)" in text:
    print("CONSTRUCTOR_LIFECYCLE_FIX: ALREADY_APPLIED")
else:
    raise SystemExit("CONSTRUCTOR_LIFECYCLE_FIX_FAIL: expected MainActivity handler declaration not found")

remaining = text.count(old)
if remaining:
    raise SystemExit(f"CONSTRUCTOR_LIFECYCLE_FIX_FAIL: stale declaration count={remaining}")
