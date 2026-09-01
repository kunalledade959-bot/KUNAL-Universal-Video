#!/usr/bin/env bash
set -u
set -o pipefail
APK="artifact/KUNAL_UNIVERSAL_VIDEO_PRO_V3.apk"
PKG="com.kunal.universalvideo"
REPORT="mobile_connection_runtime_diagnostic.txt"
: > "$REPORT"
exec > >(tee -a "$REPORT") 2>&1
P=0; F=0; W=0
ok(){ echo "PASS | $1"; P=$((P+1)); }
bad(){ echo "FAIL | $1"; F=$((F+1)); }
warn(){ echo "WARN | $1"; W=$((W+1)); }
section(){ echo; echo "===== $1 ====="; }
section "DEVICE IDENTITY"
adb get-state || true
adb shell getprop ro.build.version.release || true
adb shell getprop ro.build.version.sdk || true
adb shell getprop ro.product.model || true

section "APK INSTALL / LAUNCH"
[ -s "$APK" ] && ok "APK exists" || bad "APK missing"
adb install --no-streaming -r "$APK" >/tmp/kuv-install.log 2>&1 && ok "APK install" || { bad "APK install"; cat /tmp/kuv-install.log; }
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb logcat -c
adb shell am start -W -n "$PKG/.MainActivity" >/tmp/kuv-launch.log 2>&1 && ok "MainActivity launch" || bad "MainActivity launch"
sleep 8
adb shell pidof "$PKG" && ok "App process alive" || bad "App process alive"

section "ACCESSIBILITY CONFIGURATION"
SERVICE="$PKG/.UniversalAccessibilityService"
BEFORE="$(adb shell settings get secure enabled_accessibility_services 2>/dev/null | tr -d '\r' || true)"
echo "enabled_accessibility_services BEFORE=$BEFORE"
adb shell settings put secure enabled_accessibility_services "$SERVICE" >/dev/null 2>&1 || true
adb shell settings put secure accessibility_enabled 1 >/dev/null 2>&1 || true
sleep 5
AFTER="$(adb shell settings get secure enabled_accessibility_services 2>/dev/null | tr -d '\r' || true)"
echo "enabled_accessibility_services AFTER=$AFTER"
printf '%s' "$AFTER" | grep -Fqi "$SERVICE" && ok "Accessibility service enabled in secure settings" || bad "Accessibility service not enabled in secure settings"
adb shell dumpsys accessibility > accessibility-dumpsys.txt 2>&1 || true
grep -Fqi "$SERVICE" accessibility-dumpsys.txt && ok "Accessibility service appears in dumpsys" || bad "Accessibility service absent from dumpsys"

section "UI HIERARCHY BEFORE STAGE 2"
adb shell uiautomator dump /sdcard/kuv-before.xml >/tmp/kuv-ui.log 2>&1 || true
adb pull /sdcard/kuv-before.xml e2e-stage2-before.xml >/dev/null 2>&1 || true
[ -s e2e-stage2-before.xml ] && ok "UI hierarchy captured" || bad "UI hierarchy capture"
grep -Fq '2 • ENABLE ACCESSIBILITY / CONNECT' e2e-stage2-before.xml && ok "Stage 2 control visible" || bad "Stage 2 control missing"

section "TAP STAGE 2"
python3 - <<'PY'
import re,subprocess,xml.etree.ElementTree as ET
p='e2e-stage2-before.xml'
root=ET.parse(p).getroot()
needle='2 • ENABLE ACCESSIBILITY / CONNECT'
for n in root.iter('node'):
    if n.attrib.get('text')==needle:
        b=n.attrib.get('bounds','')
        m=re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',b)
        if m:
            x=(int(m.group(1))+int(m.group(3)))//2; y=(int(m.group(2))+int(m.group(4)))//2
            print(f'TAPPING_STAGE2 x={x} y={y}')
            subprocess.run(['adb','shell','input','tap',str(x),str(y)],check=False)
            raise SystemExit(0)
print('STAGE2_NODE_NOT_FOUND')
raise SystemExit(1)
PY
sleep 6
adb shell uiautomator dump /sdcard/kuv-after.xml >/tmp/kuv-ui-after.log 2>&1 || true
adb pull /sdcard/kuv-after.xml e2e-stage2-after.xml >/dev/null 2>&1 || true
[ -s e2e-stage2-after.xml ] && ok "Post-click UI hierarchy captured" || bad "Post-click UI hierarchy capture"

section "APP STATUS / BRIDGE"
adb forward tcp:18765 tcp:8765 >/tmp/kuv-forward.log 2>&1 || true
python3 - <<'PY'
import json,urllib.request
for path in ['/health','/status']:
    try:
        data=json.load(urllib.request.urlopen('http://127.0.0.1:18765'+path,timeout=3))
        print(path, json.dumps(data,sort_keys=True))
    except Exception as e:
        print(path,'ERROR',repr(e))
PY
python3 - <<'PY'
import json,urllib.request
try:
    req=urllib.request.Request('http://127.0.0.1:18765/',data=json.dumps({'command':'PING'}).encode(),headers={'Content-Type':'application/json'})
    print('PING',urllib.request.urlopen(req,timeout=3).read().decode())
except Exception as e: print('PING ERROR',repr(e))
PY

section "LOGCAT / SERVICE EVIDENCE"
adb logcat -d -t 6000 > e2e-stage2-logcat.txt || true
grep -Ei 'FATAL EXCEPTION|AndroidRuntime|kunal\.universalvideo|AccessibilityService|LocalBridgeService|Bridge failed|REAL CONNECT|PONG|permission|denied|exception|error' e2e-stage2-logcat.txt | tail -n 300 || true

section "SOURCE / RUNTIME CONSISTENCY"
python3 - <<'PY'
from pathlib import Path
s=Path('pro_repair_v3.py').read_text(errors='replace')
checks={
'actual_accessibility_binding_gate':'UniversalAccessibilityService.instance!=null',
'ping_requires_bound_service':'PING"->if(UniversalAccessibilityService.isEnabled&&UniversalAccessibilityService.instance!=null)',
'localhost_bridge':'127.0.0.1',
'bridge_port':'PORT=8765',
'service_connected_callback':'override fun onServiceConnected()',
}
for k,v in checks.items(): print(k, 'PASS' if v in s else 'FAIL', '|',v)
PY

section "RAW ARTIFACTS"
adb shell dumpsys package "$PKG" > package-dumpsys.txt 2>&1 || true
adb shell dumpsys activity services "$PKG" > services-dumpsys.txt 2>&1 || true
adb shell dumpsys accessibility > accessibility-dumpsys-final.txt 2>&1 || true
adb shell settings list secure > secure-settings.txt 2>&1 || true

section "VERDICT"
echo "PASS=$P"
echo "FAIL=$F"
echo "WARN=$W"
if (( F == 0 )); then echo "RUNTIME_DIAGNOSTIC=NO_FAILURE_OBSERVED"; else echo "RUNTIME_DIAGNOSTIC=FAILURES_CAPTURED"; fi
echo "PHYSICAL_PHONE_LIMIT=GitHub emulator evidence is not proof of the user's physical phone."
