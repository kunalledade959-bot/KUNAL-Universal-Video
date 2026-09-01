#!/usr/bin/env bash
set -u
ROOT="${GITHUB_WORKSPACE:-.}"
REPORT="mobile_connection_deep_diagnostic.txt"
PASS=0; FAIL=0; WARN=0
log(){ printf '%s\n' "$*" | tee -a "$REPORT"; }
check(){ local n="$1"; local ok="$2"; if [[ "$ok" == 1 ]]; then log "PASS | $n"; PASS=$((PASS+1)); else log "FAIL | $n"; FAIL=$((FAIL+1)); fi; }
warn(){ log "WARN | $1"; WARN=$((WARN+1)); }
: > "$REPORT"
log "KUNAL UNIVERSAL VIDEO - MOBILE CONNECTION A-Z DIAGNOSTIC"
log "Commit=${GITHUB_SHA:-unknown}"
log "This diagnostic is read-only against production source; it does not modify APK/app code."
log ""

# 1. Repository/source integrity
for f in pro_repair_v3.py mobile_connection_real_fix.py activity_fixed.kt .github/scripts/sequence-stage-check.sh; do
  [[ -f "$ROOT/$f" ]] && check "Required source exists: $f" 1 || check "Required source exists: $f" 0
done
python3 -m py_compile "$ROOT/pro_repair_v3.py" 2>&1 | tee -a "$REPORT"; [[ ${PIPESTATUS[0]} -eq 0 ]] && check "pro_repair_v3.py syntax" 1 || check "pro_repair_v3.py syntax" 0

# 2. Locate generated Android blocks and contracts
SRC="$ROOT/pro_repair_v3.py"
for token in 'BRIDGE=r''' 'ACCESS=r''' 'ACTIVITY=r''' 'MANIFEST=r''' 'ControllerProtocol' 'LocalBridgeService' 'UniversalAccessibilityService'; do
  grep -Fq "$token" "$SRC" && check "Generator contains: $token" 1 || check "Generator contains: $token" 0
done
for token in 'const val PING="PING"' 'const val PONG="PONG"' 'const val PROTOCOL="kunal-video-v1"' '127.0.0.1' 'PORT=8765' '/health' '/status'; do
  grep -Fq "$token" "$SRC" && check "Transport contract contains: $token" 1 || check "Transport contract contains: $token" 0
done

# 3. Real binding gates
for token in 'onServiceConnected()' 'instance=this' 'isEnabled=true' 'onDestroy()' 'isEnabled=false' 'instance=null'; do
  grep -Fq "$token" "$SRC" && check "Accessibility lifecycle: $token" 1 || check "Accessibility lifecycle: $token" 0
done
for token in 'UniversalAccessibilityService.isEnabled' 'UniversalAccessibilityService.instance!=null'; do
  grep -Fq "$token" "$SRC" && check "Connection requires actual service binding: $token" 1 || check "Connection requires actual service binding: $token" 0
done

# 4. Bridge correctness and failure modes
for token in 'ServerSocket' 'server=ServerSocket(PORT,32,java.net.InetAddress.getByName("127.0.0.1"))' 'connected.set(false)' 'REAL CONNECT FAIL' 'Unsupported command' 'DISCONNECT' 'OPEN_TARGET' 'STATUS'; do
  grep -Fq "$token" "$SRC" && check "Bridge behavior: $token" 1 || check "Bridge behavior: $token" 0
done

# 5. Android manifest/accessibility declarations from generated source
for token in 'android.accessibilityservice.AccessibilityService' 'BIND_ACCESSIBILITY_SERVICE' 'android.permission.INTERNET' 'FOREGROUND_SERVICE'; do
  grep -Fq "$token" "$SRC" && check "Manifest/service contract: $token" 1 || check "Manifest/service contract: $token" 0
done

# 6. UI -> bridge wiring
for token in 'findViewById<Button>(R.id.connect)' 'bridge?.connect(target)' 'R.id.permissions' 'Settings.ACTION_ACCESSIBILITY_SETTINGS' 'targetPackage=target'; do
  grep -Fq "$token" "$SRC" && check "UI wiring: $token" 1 || check "UI wiring: $token" 0
done

# 7. Target selection/foreground observation
for token in 'getInstalledApplications' 'target_package' 'targetForeground' 'onAccessibilityEvent' 'p==targetPackage'; do
  grep -Fq "$token" "$SRC" && check "Target tracking: $token" 1 || check "Target tracking: $token" 0
done

# 8. Protocol endpoint sanity
python3 - "$SRC" <<'PY' 2>&1 | tee -a "$REPORT"
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
required=['/health','/status','PING','PONG','DISCONNECT','OPEN_TARGET','STATUS','START_RECORD','STOP_RECORD']
missing=[x for x in required if x not in s]
print('PROTOCOL_REQUIRED=',','.join(required))
print('PROTOCOL_MISSING=',','.join(missing) if missing else 'NONE')
print('PROTOCOL_SANITY=PASS' if not missing else 'PROTOCOL_SANITY=FAIL')
raise SystemExit(0 if not missing else 1)
PY
[[ ${PIPESTATUS[0]} -eq 0 ]] && check "Protocol endpoint matrix" 1 || check "Protocol endpoint matrix" 0

# 9. Detect dangerous false-positive patterns
if grep -Fq 'connected.set(true)' "$SRC" && grep -Fq 'isEnabled ||' "$SRC"; then
  warn "A legacy/generated path may still contain a weak boolean connection path; inspect all generator blocks before release."
fi
if grep -Fq 'fun connect(t:String){target=t;UniversalAccessibilityService.targetPackage=t;connected.set(true)' "$SRC"; then
  check "NO weak connect implementation" 0
  log "DETAIL | Found legacy weak connect(t) implementation in pro_repair_v3.py. The repair patch file exists, but the generator itself must be regenerated with the hardened block."
else
  check "NO weak connect implementation" 1
fi

# 10. Sequence 02 test quality
W="$ROOT/.github/workflows/sequence-02.yml"
if [[ -f "$W" ]]; then
  if grep -Fq 'sequence-stage-check.sh 2' "$W"; then
    warn "Sequence 02 CI currently uses static sequence-stage-check.sh; this proves source wiring, not a real physical-phone connection."
  fi
fi

# 11. Local Android project, if present
PROJECT="$ROOT/KUNAL_UNIVERSAL_VIDEO"
if [[ -d "$PROJECT" ]]; then
  check "Generated Android project present" 1
  [[ -f "$PROJECT/gradlew" ]] && check "Gradle wrapper present" 1 || check "Gradle wrapper present" 0
  find "$PROJECT" -type f -name AndroidManifest.xml -print -exec grep -Hn 'AccessibilityService\|BIND_ACCESSIBILITY_SERVICE' {} \; 2>/dev/null | tee -a "$REPORT" || true
else
  warn "No generated Android project is checked into this repository snapshot; APK/runtime inspection requires running the generator/build job."
fi

log ""
log "=== SUMMARY ==="
log "PASS=$PASS"
log "FAIL=$FAIL"
log "WARN=$WARN"
if (( FAIL == 0 )); then log "DIAGNOSTIC_VERDICT=SOURCE_CONTRACTS_PASS_WITH_RUNTIME_LIMITS"; else log "DIAGNOSTIC_VERDICT=FAIL_REPAIR_REQUIRED"; fi
log ""
log "RUNTIME LIMIT: GitHub cannot prove a user's physical Android phone is connected. A real-phone verdict requires device-side evidence (Accessibility bound, bridge health/status, PING/PONG, target foreground, reconnect after restart)."
