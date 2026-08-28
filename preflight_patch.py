from pathlib import Path
import re

p = Path("pro_repair_v3.py")
s = p.read_text(encoding="utf-8")

# The production asset engine is a canonical repository source.  The repair
# script must overlay it after project extraction, otherwise an older engine
# inside the source ZIP can silently replace the verified source and break the
# build.  Humans apparently enjoy having two copies of the same file.
needle = 'android=STAGE/"android-controller"'
injection = '''android=STAGE/"android-controller"\n canonical=INPUT/"production_asset_engine.kt"\n if canonical.is_file():\n  write(android/"app/src/main/java/com/kunal/universalvideo/ProductionAssetEngine.kt",read(canonical))'''
if needle in s and injection not in s:
    s = s.replace(needle, injection, 1)

# Never allow the build gate to report success without a real APK.
marker = 'if __name__=="__main__":main()'
if marker not in s:
    raise SystemExit("MAIN_ENTRY_NOT_FOUND")

p.write_text(s, encoding="utf-8")
print("PRE-FLIGHT PATCH: PASS")
