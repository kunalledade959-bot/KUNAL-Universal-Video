from pathlib import Path

p = Path("activity_fixed.kt")
s = p.read_text(encoding="utf-8")

start = s.find("    private fun buildUi(")
end = s.find("    private fun begin(", start)
if start < 0 or end < 0:
    raise SystemExit("PROGRESSIVE_UI: buildUi/begin anchors not found")

new = '''    private lateinit var actions: LinearLayout
    private val stageButtons = mutableListOf<Button>()

    private fun buildUi(p:android.content.SharedPreferences){
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)}
        root.addView(TextView(this).apply{text="Kunal Universal Video • 13 Stage Engine";textSize=25f})
        status=TextView(this).apply{textSize=15f;setPadding(0,12,0,12)};root.addView(status)
        targetSpinner=Spinner(this);root.addView(targetSpinner)
        story=EditText(this).apply{hint="Enter story";minLines=4;setText(p.getString(STORY,""))};root.addView(story,LinearLayout.LayoutParams(-1,0,1f))
        actions=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        val defs=listOf(
            "1 • START / DIAGNOSTIC" to {stage1()},
            "2 • ENABLE ACCESSIBILITY / CONNECT" to {connectMobile()},
            "3 • SELECT / SAVE TARGET" to {selectTarget()},
            "4 • STUDY SELECTED APK" to {studyTarget()},
            "5 • SAVE STORY INPUT" to {saveStory()},
            "6 • OPERATE SELECTED TARGET" to {operateTarget()},
            "7 • DEEP TARGET UNDERSTANDING" to {deepStudy()},
            "8 • CREATE EXACT SCENE PLAN" to {scenePlan()},
            "9 • BUILD PRODUCTION PLAN / PROMPTS" to {buildPlan()},
            "10 • CREATE AUDIO / VOICE / MUSIC / SFX + RECORD" to {audioAndRecord()},
            "11 • ASSEMBLE / EDIT" to {assembleEdit()},
            "12 • VERIFY / AUTO-FIX" to {verifyAndFix()},
            "13 • FINAL GALLERY EXPORT" to {finalExport()}
        )
        defs.forEachIndexed{idx,pair->
            val b=Button(this).apply{text=pair.first;setOnClickListener{pair.second.invoke()};visibility=android.view.View.GONE}
            stageButtons.add(b);actions.addView(b)
        }
        root.addView(actions)
        setContentView(root)
        renderStatus()
    }

    private fun refreshStageUi(){
        if(!::gate.isInitialized || stageButtons.isEmpty()) return
        val id=gate.currentStage().coerceIn(1,13)
        val state=gate.state(id)
        stageButtons.forEachIndexed{i,b->b.visibility=if(i+1==id)android.view.View.VISIBLE else android.view.View.GONE}
        targetSpinner.visibility=if(id==3)android.view.View.VISIBLE else android.view.View.GONE
        story.visibility=if(id==5)android.view.View.VISIBLE else android.view.View.GONE
        val label=when(state){
            StageGate.State.FAIL -> "${id} • RETRY / REPAIR • ${gate.evidenceJson().optJSONArray(\"stages\")?.optJSONObject(id-1)?.optString(\"name\",\"\") ?: \"STAGE\"}"
            StageGate.State.RUNNING -> "${id} • RUNNING / VERIFYING"
            else -> stageButtons[id-1].text.toString()
        }
        stageButtons[id-1].text=label
    }
'''
s = s[:start] + new + s[end:]

old = '''    private fun renderStatus(){
        if(!::gate.isInitialized)return
        val id=gate.currentStage();val st=gate.state(id);status.text="Stage $id • ${st.name} • ${gate.evidenceJson().optBoolean(\"final_pass\")}\\nSession ${sid.take(8)}"
    }'''
new_status = '''    private fun renderStatus(){
        if(!::gate.isInitialized)return
        val id=gate.currentStage();val st=gate.state(id);status.text="Stage $id • ${st.name}\\nSession ${sid.take(8)}\\nOnly the current stage is available. Next stage unlocks only after verified PASS."
        refreshStageUi()
    }'''
if old not in s:
    raise SystemExit("PROGRESSIVE_UI: renderStatus anchor not found")
s = s.replace(old, new_status, 1)

p.write_text(s, encoding="utf-8")
print("PROGRESSIVE_STAGE_UI=PASS")
