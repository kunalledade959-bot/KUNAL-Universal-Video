from pathlib import Path

p = Path("activity_fixed.kt")
s = p.read_text(encoding="utf-8")

old_stage1 = '''    private fun stage1(){
        if(gate.state(1)!=StageGate.State.PASS){gate.resetForRepair(1);gate.begin(1);gate.pass(1,"MainActivity launched; workflow controller attached")}
        loadApps();renderStatus()
    }'''
new_stage1 = '''    private fun stage1(){
        try {
            if(gate.state(1)!=StageGate.State.PASS){
                if(!gate.resetForRepair(1) || !gate.begin(1)){
                    fail(1,"Startup StageGate could not enter RUNNING state");return
                }
            }
            loadApps()
            if(apps.isEmpty()){
                fail(1,"PackageManager returned no installed target applications");return
            }
            if(gate.state(1)==StageGate.State.RUNNING){
                pass(1,"MainActivity launched; workflow controller attached; installed-app discovery verified")
            }
            renderStatus()
        }catch(e:Exception){
            fail(1,"Startup self-diagnostic failed: ${e.javaClass.simpleName}: ${e.message}")
        }
    }'''

old_stream = 'contentResolver.openOutputStream(uri).use{os->FileInputStream(src).use{input->input.copyTo(os!!)}}'
new_stream = 'contentResolver.openOutputStream(uri).use{os->if(os==null)throw IllegalStateException("Gallery output stream unavailable");FileInputStream(src).use{input->input.copyTo(os)}}'

changed = False
if old_stage1 in s:
    s = s.replace(old_stage1, new_stage1, 1)
    changed = True
elif new_stage1 not in s:
    raise SystemExit("stage1 repair anchor not found and repaired form is absent")

if old_stream in s:
    s = s.replace(old_stream, new_stream, 1)
    changed = True
elif new_stream not in s:
    raise SystemExit("gallery output stream repair anchor not found and repaired form is absent")

if changed:
    p.write_text(s, encoding="utf-8")
    print("PRODUCTION_SAFETY_PATCH=PASS_APPLIED")
else:
    print("PRODUCTION_SAFETY_PATCH=PASS_ALREADY_APPLIED")
