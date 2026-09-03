#!/usr/bin/env bash
# Final production user-flow gate.
# This is intentionally above the ordinary E2E gate and checks the user-visible
# target-app selection contract that component/system E2E can miss.
set -euo pipefail

ROOT="$(pwd)"
EVIDENCE="$ROOT/final-user-flow-evidence"
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
mkdir -p "$EVIDENCE" artifact
exec > >(tee "$EVIDENCE/final-user-flow.log") 2>&1

fail(){
  local reason="$1"
  printf 'FINAL_USER_FLOW_FAIL: %s\n' "$reason" | tee "$EVIDENCE/FAIL.txt"
  capture_all "$reason" || true
  exit 1
}

adbq(){ timeout 30s adb -s emulator-5554 "$@"; }

capture_all(){
  local reason="${1:-unknown}"
  printf '%s\n' "$reason" > "$EVIDENCE/root-cause-trigger.txt"
  adbq devices -l > "$EVIDENCE/adb-devices.txt" 2>&1 || true
  adbq shell getprop > "$EVIDENCE/device-props.txt" 2>&1 || true
  adbq shell dumpsys activity activities > "$EVIDENCE/activity.txt" 2>&1 || true
  adbq shell dumpsys window windows > "$EVIDENCE/windows.txt" 2>&1 || true
  adbq shell dumpsys package "$PKG" > "$EVIDENCE/package.txt" 2>&1 || true
  adbq shell settings get secure enabled_accessibility_services > "$EVIDENCE/accessibility.txt" 2>&1 || true
  adbq logcat -d -b crash > "$EVIDENCE/crash-logcat.txt" 2>&1 || true
  adbq logcat -d -t 3000 > "$EVIDENCE/logcat.txt" 2>&1 || true
  adbq exec-out screencap -p > "$EVIDENCE/screen.png" 2>/dev/null || true
  adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui.xml" 2>"$EVIDENCE/ui.err" || true
  if [[ -f e2e-PASS.txt ]]; then cp e2e-PASS.txt "$EVIDENCE/upstream-e2e-PASS.txt"; fi
  if [[ -f e2e-FAIL.txt ]]; then cp e2e-FAIL.txt "$EVIDENCE/upstream-e2e-FAIL.txt"; fi
  if [[ -f e2e-start.txt ]]; then cp e2e-start.txt "$EVIDENCE/upstream-e2e-start.txt"; fi
  {
    echo "ROOT_CAUSE_CLASSIFICATION"
    if grep -Eiq 'Application Not Responding: com.android.systemui|System UI isn.t responding' "$EVIDENCE/windows.txt" "$EVIDENCE/ui.xml"; then
      echo 'INFRASTRUCTURE: SYSTEMUI_ANR'
    elif grep -Eiq 'FATAL EXCEPTION|Process: com\.kunal\.universalvideo.*has died|Fatal signal' "$EVIDENCE/crash-logcat.txt" "$EVIDENCE/logcat.txt"; then
      echo 'RUNTIME: APP_OR_PLATFORM_CRASH'
    elif ! grep -q 'com.kunal.universalvideo/.MainActivity' "$EVIDENCE/activity.txt"; then
      echo 'APP: MAIN_ACTIVITY_NOT_FOREGROUND'
    elif [[ ! -s "$EVIDENCE/ui.xml" ]]; then
      echo 'INFRASTRUCTURE: UIAUTOMATOR_DUMP_UNAVAILABLE'
    elif ! grep -Eq 'android.widget.Spinner' "$EVIDENCE/ui.xml"; then
      echo 'APP: TARGET_SELECTION_CONTROL_MISSING'
    elif ! grep -Eq 'com\\.android\\.settings|com\\.android\\.launcher|android\\.settings' "$EVIDENCE/ui.xml"; then
      echo 'APP: TARGET_SELECTION_LIST_NOT_POPULATED_OR_VISIBLE'
    else
      echo 'FUNCTIONAL: USER_FLOW_CONTRACT_FAILURE'
    fi
  } > "$EVIDENCE/root-cause-classification.txt"
}

[[ -s "$APK" ]] || fail "APK missing"

# A fresh emulator is required. No stale app data is allowed to mask a missing
# first-run selection control.
adbq wait-for-device >/dev/null || fail "ADB unavailable"
boot="$(adbq shell getprop sys.boot_completed | tr -d '\r' || true)"
[[ "$boot" == "1" ]] || fail "Emulator boot not complete"
adbq shell pm install-existing "$PKG" >/dev/null 2>&1 || true
adbq install -r "$APK" > "$EVIDENCE/install.txt" 2>&1 || fail "APK install failed"
adbq shell pm clear "$PKG" > "$EVIDENCE/clear-data.txt" 2>&1 || fail "Fresh app data reset failed"
adbq shell am start -W -n "$PKG/.MainActivity" > "$EVIDENCE/launch.txt" 2>&1 || fail "MainActivity launch failed"
sleep 4

PID="$(adbq shell pidof "$PKG" | tr -d '\r' || true)"
[[ -n "$PID" ]] || fail "Application process not alive"

# First blind-spot assertion: the target selection control itself must exist.
adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui-initial.xml" 2>"$EVIDENCE/ui-initial.err" || fail "Initial UI hierarchy unavailable"
python3 - "$EVIDENCE/ui-initial.xml" <<'PY' || exit 1
import re,sys
p=sys.argv[1]; s=open(p,encoding='utf-8',errors='replace').read()
if not re.search(r'class="android\.widget\.Spinner"',s):
    print('TARGET_SELECTION_CONTROL_MISSING'); raise SystemExit(2)
if not re.search(r'1 • START / DIAGNOSTIC',s):
    print('STAGE1_CONTROL_MISSING'); raise SystemExit(3)
print('TARGET_SELECTION_CONTROL_PRESENT')
PY

# Locate Spinner bounds from the real production hierarchy, then open it.
BOUNDS="$(python3 - "$EVIDENCE/ui-initial.xml" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
m=re.search(r'<node[^>]*class="android\.widget\.Spinner"[^>]*bounds="(\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\])"',s)
if not m: raise SystemExit(2)
print(m.group(1))
PY
)" || fail "Target selection Spinner has no usable bounds"
read -r X1Y1 X2Y2 <<< "$(sed 's/\[/ /g;s/\]/ /g;s/,/ /g' <<< "$BOUNDS")"
X=$(( (X1Y1 + X2Y1) / 2 ))
Y=$(( (X1Y2 + X2Y2) / 2 ))
adbq shell input tap "$X" "$Y" || fail "Target selection control could not be opened"
sleep 2
adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui-selection-open.xml" 2>"$EVIDENCE/ui-selection-open.err" || fail "Selection popup hierarchy unavailable"

# Second blind-spot assertion: popup/list must contain a real selectable installed
# target. Prefer Settings, then fall back to another package with a launcher.
TARGET=""
if grep -Fq 'com.android.settings' "$EVIDENCE/ui-selection-open.xml"; then
  TARGET="com.android.settings"
else
  TARGET="$(python3 - "$EVIDENCE/ui-selection-open.xml" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
for p in re.findall(r'([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+){2,})',s):
    if p not in {'com.kunal.universalvideo'} and not p.startswith('android.'):
        print(p); break
PY
)"
fi
[[ -n "$TARGET" ]] || fail "Target selection popup exists but contains no real target package"
printf '%s\n' "$TARGET" | tee "$EVIDENCE/target-package.txt"

# Select the exact target row from the popup. This is intentionally based on the
# package text shown to the user, not on internal SharedPreferences access.
python3 - "$EVIDENCE/ui-selection-open.xml" "$TARGET" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read(); target=sys.argv[2]
for m in re.finditer(r'<node[^>]*text="([^"]*'+re.escape(target)+r'[^"]*)"[^>]*bounds="(\[[^\"]+\])"',s):
    print(m.group(2)); break
else:
    raise SystemExit(2)
PY
> "$EVIDENCE/target-bounds.txt" || fail "Selected target row is not represented in popup hierarchy"

# Parse the row bounds and tap it.
ROW="$(cat "$EVIDENCE/target-bounds.txt")"
read -r RX1 RY1 RX2 RY2 <<< "$(sed 's/\[/ /g;s/\]/ /g;s/,/ /g' <<< "$ROW")"
RX=$(( (RX1 + RX2) / 2 )); RY=$(( (RY1 + RY2) / 2 ))
adbq shell input tap "$RX" "$RY" || fail "Target row tap failed"
sleep 2

adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui-after-selection.xml" 2>"$EVIDENCE/ui-after-selection.err" || fail "Post-selection UI hierarchy unavailable"
if ! grep -Fq "$TARGET" "$EVIDENCE/ui-after-selection.xml"; then
  fail "Target selection was not reflected back in production UI"
fi

# Verify the app's persisted selection when the debug build permits run-as. This
# is secondary evidence only, never the primary user-flow assertion.
adbq shell run-as "$PKG" cat shared_prefs/kuv.xml > "$EVIDENCE/prefs.xml" 2>&1 || true
if [[ -s "$EVIDENCE/prefs.xml" ]] && ! grep -Fq "$TARGET" "$EVIDENCE/prefs.xml"; then
  fail "UI showed a target but target_package was not persisted"
fi

# Final root-cause snapshot after successful selection.
capture_all "selection-flow-complete"
printf 'FINAL_PRODUCTION_USER_FLOW_PASS\nTARGET_SELECTION_CONTROL=PASS\nTARGET_POPUP_POPULATED=PASS\nTARGET_SELECTION_REFLECTED=PASS\n' | tee "$EVIDENCE/PASS.txt"
