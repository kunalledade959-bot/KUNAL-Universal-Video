#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
EVIDENCE="$ROOT/final-user-flow-evidence"
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
SERVICE="$PKG/.UniversalAccessibilityService"
mkdir -p "$EVIDENCE" artifact
exec > >(tee "$EVIDENCE/final-user-flow.log") 2>&1

adbq(){ timeout 30s adb -s emulator-5554 "$@"; }

dump_ui(){
  local out="$1"
  local err="$2"
  local remote="/sdcard/kuv-ui.xml"
  local raw="${out}.raw"
  adbq shell rm -f "$remote" >/dev/null 2>&1 || true
  if ! adbq shell uiautomator dump "$remote" > "$err" 2>&1; then return 1; fi
  if ! adbq exec-out cat "$remote" > "$raw" 2>>"$err"; then return 1; fi
  python3 - "$raw" "$out" <<'PY'
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
raw=Path(sys.argv[1]).read_bytes(); start=raw.find(b'<?xml'); end=raw.find(b'</hierarchy>',start)
if start<0 or end<0: raise SystemExit('UI_XML_PAYLOAD_MISSING')
end+=len(b'</hierarchy>'); payload=raw[start:end]; ET.fromstring(payload); Path(sys.argv[2]).write_bytes(payload+b'\n')
PY
  rm -f "$raw"
  [[ -s "$out" ]] || return 1
}

capture_all(){
  local reason="${1:-unknown}"
  printf '%s\n' "$reason" > "$EVIDENCE/root-cause-trigger.txt"
  adbq devices -l > "$EVIDENCE/adb-devices.txt" 2>&1 || true
  adbq shell getprop > "$EVIDENCE/device-props.txt" 2>&1 || true
  adbq shell dumpsys activity activities > "$EVIDENCE/activity.txt" 2>&1 || true
  adbq shell dumpsys window windows > "$EVIDENCE/windows.txt" 2>&1 || true
  adbq shell dumpsys package "$PKG" > "$EVIDENCE/package.txt" 2>&1 || true
  adbq shell settings get secure enabled_accessibility_services > "$EVIDENCE/accessibility.txt" 2>&1 || true
  adbq shell dumpsys accessibility > "$EVIDENCE/accessibility-dumpsys.txt" 2>&1 || true
  adbq logcat -d -b crash > "$EVIDENCE/crash-logcat.txt" 2>&1 || true
  adbq logcat -d -t 3000 > "$EVIDENCE/logcat.txt" 2>&1 || true
  adbq exec-out screencap -p > "$EVIDENCE/screen.png" 2>/dev/null || true
  dump_ui "$EVIDENCE/ui.xml" "$EVIDENCE/ui.err" || true
  {
    echo "ROOT_CAUSE_CLASSIFICATION"
    if grep -Eiq 'Application Not Responding: com.android.systemui|System UI isn.t responding' "$EVIDENCE/windows.txt" "$EVIDENCE/ui.xml"; then echo 'INFRASTRUCTURE: SYSTEMUI_ANR'
    elif grep -Eiq 'FATAL EXCEPTION|Process: com\\.kunal\\.universalvideo.*has died|Fatal signal' "$EVIDENCE/crash-logcat.txt" "$EVIDENCE/logcat.txt"; then echo 'RUNTIME: APP_OR_PLATFORM_CRASH'
    elif ! grep -q 'com.kunal.universalvideo/.MainActivity' "$EVIDENCE/activity.txt"; then echo 'APP: MAIN_ACTIVITY_NOT_FOREGROUND'
    elif [[ ! -s "$EVIDENCE/ui.xml" ]]; then echo 'INFRASTRUCTURE: UIAUTOMATOR_DUMP_UNAVAILABLE'
    elif ! grep -Eq 'android.widget.Spinner' "$EVIDENCE/ui.xml"; then echo 'APP: TARGET_SELECTION_CONTROL_MISSING'
    else echo 'FUNCTIONAL: USER_FLOW_CONTRACT_FAILURE'; fi
  } > "$EVIDENCE/root-cause-classification.txt"
}

fail(){ local reason="$1"; printf 'FINAL_USER_FLOW_FAIL: %s\n' "$reason" | tee "$EVIDENCE/FAIL.txt"; capture_all "$reason" || true; exit 1; }

[[ -s "$APK" ]] || fail "APK missing"
adbq wait-for-device >/dev/null || fail "ADB unavailable"
[[ "$(adbq shell getprop sys.boot_completed | tr -d '\r')" == "1" ]] || fail "Emulator boot not complete"
adbq install -r "$APK" > "$EVIDENCE/install.txt" 2>&1 || fail "APK install failed"
adbq shell pm clear "$PKG" > "$EVIDENCE/clear-data.txt" 2>&1 || fail "Fresh app data reset failed"
adbq shell am start -W -n "$PKG/.MainActivity" > "$EVIDENCE/launch.txt" 2>&1 || fail "MainActivity launch failed"
sleep 4
[[ -n "$(adbq shell pidof "$PKG" | tr -d '\r' || true)" ]] || fail "Application process not alive"

dump_ui "$EVIDENCE/ui-initial.xml" "$EVIDENCE/ui-initial.err" || fail "Initial UI hierarchy unavailable"
if python3 - "$EVIDENCE/ui-initial.xml" > "$EVIDENCE/spinner-center.txt" <<'PY'
import sys,xml.etree.ElementTree as ET,re
root=ET.parse(sys.argv[1]).getroot(); nodes=list(root.iter()); sp=[n for n in nodes if n.attrib.get('class')=='android.widget.Spinner']
if not sp: raise SystemExit('TARGET_SELECTION_CONTROL_MISSING')
if not any('1 • START / DIAGNOSTIC' in n.attrib.get('text','') for n in nodes): raise SystemExit('STAGE1_CONTROL_MISSING')
if not any('2 • ENABLE ACCESSIBILITY / CONNECT' in n.attrib.get('text','') for n in nodes): raise SystemExit('STAGE2_CONTROL_MISSING')
if not any('3 • SELECT / SAVE TARGET' in n.attrib.get('text','') for n in nodes): raise SystemExit('STAGE3_CONTROL_MISSING')
m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',sp[0].attrib.get('bounds',''))
if not m: raise SystemExit('TARGET_SELECTION_BOUNDS_INVALID')
x1,y1,x2,y2=map(int,m.groups()); print((x1+x2)//2,(y1+y2)//2)
PY
then :; else STATUS=$?; fail "Production target-selection controls are missing or malformed (diagnostic=$STATUS)"; fi

# Stage 2 is a real prerequisite of Stage 3. The previous gate jumped from
# target selection directly to Stage 3, while StageGate correctly rejected it.
# Prepare the fresh emulator's declared accessibility service, then execute the
# actual production Stage 2 button so the app itself validates the connection.
adbq shell settings put secure enabled_accessibility_services "$SERVICE" > "$EVIDENCE/accessibility-enable.txt" 2>&1 || fail "Could not configure emulator accessibility service"
adbq shell settings put secure accessibility_enabled 1 >> "$EVIDENCE/accessibility-enable.txt" 2>&1 || fail "Could not enable emulator accessibility"
sleep 3
ACCESS_STATE="$(adbq shell settings get secure enabled_accessibility_services | tr -d '\r' || true)"
printf 'EXPECTED_SERVICE=%s\nACTUAL_SERVICES=%s\n' "$SERVICE" "$ACCESS_STATE" > "$EVIDENCE/accessibility-pre-stage2.txt"
grep -Fq "$SERVICE" <<<"$ACCESS_STATE" || fail "Declared Accessibility service did not become enabled before Stage 2"
adbq shell dumpsys accessibility > "$EVIDENCE/accessibility-pre-stage2-dumpsys.txt" 2>&1 || fail "Accessibility diagnostics unavailable before Stage 2"
grep -Fq "$PKG/.UniversalAccessibilityService" "$EVIDENCE/accessibility-pre-stage2-dumpsys.txt" || fail "Production AccessibilityService is not registered in the running accessibility manager"

if python3 - "$EVIDENCE/ui-initial.xml" > "$EVIDENCE/stage2-center.txt" <<'PY'
import sys,xml.etree.ElementTree as ET,re
root=ET.parse(sys.argv[1]).getroot()
for n in root.iter():
    if n.attrib.get('text','')=='2 • ENABLE ACCESSIBILITY / CONNECT' and n.attrib.get('enabled','true')=='true' and n.attrib.get('clickable','true')=='true':
        m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',n.attrib.get('bounds',''))
        if m:
            x1,y1,x2,y2=map(int,m.groups())
            if x2>x1 and y2>y1: print((x1+x2)//2,(y1+y2)//2); break
else: raise SystemExit('STAGE2_CONTROL_NOT_FOUND')
PY
then :; else STATUS=$?; fail "Explicit Stage 2 control unavailable (diagnostic=$STATUS)"; fi
read -r C2X C2Y < "$EVIDENCE/stage2-center.txt"
adbq shell input tap "$C2X" "$C2Y" || fail "Stage 2 connect action failed"
sleep 2
dump_ui "$EVIDENCE/ui-after-stage2.xml" "$EVIDENCE/ui-after-stage2.err" || fail "Post-Stage 2 UI hierarchy unavailable"
grep -Eq 'Stage 2 (PASS|READY)' "$EVIDENCE/ui-after-stage2.xml" || fail "Stage 2 did not report a successful connection state"
ACCESS_STATE_AFTER="$(adbq shell settings get secure enabled_accessibility_services | tr -d '\r' || true)"
printf 'STAGE2_ACCESSIBILITY_STATE=%s\n' "$ACCESS_STATE_AFTER" > "$EVIDENCE/stage2-accessibility-state.txt"
grep -Fq "$SERVICE" <<<"$ACCESS_STATE_AFTER" || fail "Accessibility service disappeared after Stage 2 connect"
adbq shell dumpsys accessibility > "$EVIDENCE/accessibility-post-stage2-dumpsys.txt" 2>&1 || fail "Accessibility diagnostics unavailable after Stage 2"
grep -Fq "$PKG/.UniversalAccessibilityService" "$EVIDENCE/accessibility-post-stage2-dumpsys.txt" || fail "Production AccessibilityService is not registered after Stage 2 connect"
printf 'STAGE2_EXECUTION=PASS\n' > "$EVIDENCE/stage2-result.txt"

read -r X Y < "$EVIDENCE/spinner-center.txt"
adbq shell input tap "$X" "$Y" || fail "Target selection control could not be opened"
sleep 2
dump_ui "$EVIDENCE/ui-selection-open.xml" "$EVIDENCE/ui-selection-open.err" || fail "Selection popup hierarchy unavailable"

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
printf 'TARGET=%s\n' "$TARGET" | tee "$EVIDENCE/target-package.txt"
printf 'TARGET=%s\n' "$TARGET" > "$EVIDENCE/root-cause-trigger.txt"

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
then :; else STATUS=$?; fail "Selected target row is not represented in popup hierarchy (diagnostic=$STATUS)"; fi
read -r RX RY < "$EVIDENCE/target-center.txt"
adbq shell input tap "$RX" "$RY" || fail "Target row tap failed"
sleep 2
dump_ui "$EVIDENCE/ui-after-selection.xml" "$EVIDENCE/ui-after-selection.err" || fail "Post-selection UI hierarchy unavailable"
grep -Fq "$TARGET" "$EVIDENCE/ui-after-selection.xml" || fail "Target selection was not reflected back in production UI"

if python3 - "$EVIDENCE/ui-after-selection.xml" > "$EVIDENCE/stage3-save-center.txt" <<'PY'
import sys,xml.etree.ElementTree as ET,re
root=ET.parse(sys.argv[1]).getroot()
for n in root.iter():
    if n.attrib.get('text','')=='3 • SELECT / SAVE TARGET' and n.attrib.get('enabled','true')=='true' and n.attrib.get('clickable','true')=='true':
        m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',n.attrib.get('bounds',''))
        if m:
            x1,y1,x2,y2=map(int,m.groups())
            if x2>x1 and y2>y1: print((x1+x2)//2,(y1+y2)//2); break
else: raise SystemExit('STAGE3_SAVE_CONTROL_NOT_FOUND')
PY
then :; else STATUS=$?; fail "Explicit Stage 3 save control unavailable (diagnostic=$STATUS)"; fi
read -r SX SY < "$EVIDENCE/stage3-save-center.txt"
adbq shell input tap "$SX" "$SY" || fail "Stage 3 save action failed"
sleep 1
dump_ui "$EVIDENCE/ui-after-save.xml" "$EVIDENCE/ui-after-save.err" || fail "Post-save UI hierarchy unavailable"
grep -Fq "$TARGET" "$EVIDENCE/ui-after-save.xml" || fail "Stage 3 save action lost the selected target from production UI"

adbq shell run-as "$PKG" cat shared_prefs/kuv.xml > "$EVIDENCE/prefs.txt" 2>&1 || fail "Target preference file could not be read after Stage 3 save"
[[ -s "$EVIDENCE/prefs.txt" ]] || fail "Target preference file is empty after Stage 3 save"
grep -Fq "$TARGET" "$EVIDENCE/prefs.txt" || fail "Stage 3 save action did not persist target_package"
printf 'STAGE3_SAVE=PASS\nTARGET_PERSISTENCE=PASS\n' > "$EVIDENCE/stage3-save-result.txt"

adbq shell cmd package resolve-activity --brief "$TARGET" > "$EVIDENCE/target-resolve.txt" 2>&1 || fail "Selected target package could not resolve a launch activity"
if grep -Eq 'No activity found|priority=0.*No activity' "$EVIDENCE/target-resolve.txt"; then fail "Selected target has no resolvable launch activity"; fi
adbq shell monkey -p "$TARGET" -c android.intent.category.LAUNCHER 1 > "$EVIDENCE/target-launch.txt" 2>&1 || fail "Selected target launch command failed"
sleep 3
FOCUS="$(adbq shell dumpsys activity activities | grep -m1 -E 'mResumedActivity|mCurrentFocus' || true)"
printf '%s\n' "$FOCUS" > "$EVIDENCE/target-foreground.txt"
grep -Fq "$TARGET" "$EVIDENCE/target-foreground.txt" || fail "Selected target was not brought to the real foreground"

adbq shell am start -W -n "$PKG/.MainActivity" > "$EVIDENCE/return-to-controller.txt" 2>&1 || fail "Controller could not be restored after target handoff"
sleep 2
dump_ui "$EVIDENCE/ui-after-target-handoff.xml" "$EVIDENCE/ui-after-target-handoff.err" || fail "Post-handoff controller UI hierarchy unavailable"
grep -Fq "$TARGET" "$EVIDENCE/ui-after-target-handoff.xml" || fail "Selected target was lost after target-app handoff"

capture_all "selection-stage2-stage3-save-and-target-handoff-complete"
printf 'FINAL_PRODUCTION_USER_FLOW_PASS\nTARGET_SELECTION_CONTROL=PASS\nTARGET_POPUP_POPULATED=PASS\nTARGET_SELECTION_REFLECTED=PASS\nSTAGE2_EXECUTION=PASS\nSTAGE3_SAVE_CONTROL=PASS\nTARGET_PERSISTENCE=PASS\nTARGET_LAUNCH=PASS\nTARGET_FOREGROUND=PASS\nTARGET_HANDOFF_STATE=PASS\n' | tee "$EVIDENCE/PASS.txt"
