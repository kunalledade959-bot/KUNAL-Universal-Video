#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
EVIDENCE="$ROOT/final-user-flow-evidence"
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
mkdir -p "$EVIDENCE" artifact
exec > >(tee "$EVIDENCE/final-user-flow.log") 2>&1

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
    else
      echo 'FUNCTIONAL: USER_FLOW_CONTRACT_FAILURE'
    fi
  } > "$EVIDENCE/root-cause-classification.txt"
}

fail(){
  local reason="$1"
  printf 'FINAL_USER_FLOW_FAIL: %s\n' "$reason" | tee "$EVIDENCE/FAIL.txt"
  capture_all "$reason" || true
  exit 1
}

[[ -s "$APK" ]] || fail "APK missing"
adbq wait-for-device >/dev/null || fail "ADB unavailable"
[[ "$(adbq shell getprop sys.boot_completed | tr -d '\r')" == "1" ]] || fail "Emulator boot not complete"
adbq install -r "$APK" > "$EVIDENCE/install.txt" 2>&1 || fail "APK install failed"
adbq shell pm clear "$PKG" > "$EVIDENCE/clear-data.txt" 2>&1 || fail "Fresh app data reset failed"
adbq shell am start -W -n "$PKG/.MainActivity" > "$EVIDENCE/launch.txt" 2>&1 || fail "MainActivity launch failed"
sleep 4
[[ -n "$(adbq shell pidof "$PKG" | tr -d '\r' || true)" ]] || fail "Application process not alive"

adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui-initial.xml" 2>"$EVIDENCE/ui-initial.err" || fail "Initial UI hierarchy unavailable"
if python3 - "$EVIDENCE/ui-initial.xml" > "$EVIDENCE/spinner-center.txt" <<'PY'
import sys,xml.etree.ElementTree as ET,re
root=ET.parse(sys.argv[1]).getroot(); nodes=list(root.iter())
sp=[n for n in nodes if n.attrib.get('class')=='android.widget.Spinner']
if not sp: raise SystemExit('TARGET_SELECTION_CONTROL_MISSING')
if not any('1 • START / DIAGNOSTIC' in n.attrib.get('text','') for n in nodes): raise SystemExit('STAGE1_CONTROL_MISSING')
m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',sp[0].attrib.get('bounds',''))
if not m: raise SystemExit('TARGET_SELECTION_BOUNDS_INVALID')
x1,y1,x2,y2=map(int,m.groups()); print((x1+x2)//2,(y1+y2)//2)
PY
then
  :
else
  STATUS=$?
  fail "Production target-selection control is missing or malformed (diagnostic=$STATUS)"
fi
read -r X Y < "$EVIDENCE/spinner-center.txt"
adbq shell input tap "$X" "$Y" || fail "Target selection control could not be opened"
sleep 2
adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui-selection-open.xml" 2>"$EVIDENCE/ui-selection-open.err" || fail "Selection popup hierarchy unavailable"

TARGET=""
if grep -Fq 'com.android.settings' "$EVIDENCE/ui-selection-open.xml"; then TARGET="com.android.settings"; else
  TARGET="$(python3 - "$EVIDENCE/ui-selection-open.xml" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
for p in re.findall(r'([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+){2,})',s):
    if p!='com.kunal.universalvideo' and not p.startswith('android.'):
        print(p); break
PY
)"
fi
[[ -n "$TARGET" ]] || fail "Target selection popup exists but contains no real target package"
printf '%s\n' "$TARGET" | tee "$EVIDENCE/target-package.txt"

if python3 - "$EVIDENCE/ui-selection-open.xml" "$TARGET" > "$EVIDENCE/target-center.txt" <<'PY'
import sys,xml.etree.ElementTree as ET,re
root=ET.parse(sys.argv[1]).getroot(); target=sys.argv[2]
for n in root.iter():
    if target in n.attrib.get('text',''):
        m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',n.attrib.get('bounds',''))
        if m:
            x1,y1,x2,y2=map(int,m.groups()); print((x1+x2)//2,(y1+y2)//2); break
else: raise SystemExit('TARGET_ROW_NOT_FOUND')
PY
then
  :
else
  STATUS=$?
  fail "Selected target row is not represented in popup hierarchy (diagnostic=$STATUS)"
fi
read -r RX RY < "$EVIDENCE/target-center.txt"
adbq shell input tap "$RX" "$RY" || fail "Target row tap failed"
sleep 2
adbq exec-out uiautomator dump /dev/tty > "$EVIDENCE/ui-after-selection.xml" 2>"$EVIDENCE/ui-after-selection.err" || fail "Post-selection UI hierarchy unavailable"
grep -Fq "$TARGET" "$EVIDENCE/ui-after-selection.xml" || fail "Target selection was not reflected back in production UI"

adbq shell run-as "$PKG" cat shared_prefs/kuv.xml > "$EVIDENCE/prefs.xml" 2>&1 || true
if [[ -s "$EVIDENCE/prefs.xml" ]] && ! grep -Fq "$TARGET" "$EVIDENCE/prefs.xml"; then fail "UI showed a target but target_package was not persisted"; fi

capture_all "selection-flow-complete"
printf 'FINAL_PRODUCTION_USER_FLOW_PASS\nTARGET_SELECTION_CONTROL=PASS\nTARGET_POPUP_POPULATED=PASS\nTARGET_SELECTION_REFLECTED=PASS\n' | tee "$EVIDENCE/PASS.txt"
