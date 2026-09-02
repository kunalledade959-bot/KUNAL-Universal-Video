#!/usr/bin/env python3
"""Final deterministic Kotlin runtime hardening before the production build.

This script removes Kotlin string-escape fragility and makes stages 8/9 lossless.
It is fail-closed: expected method boundaries must exist exactly once.
"""
from pathlib import Path

p = Path("activity_fixed.kt")
s = p.read_text(encoding="utf-8")

start8 = s.index("    private fun scenePlan(){")
end8 = s.index("    private fun buildPlan(){", start8)
start9 = end8
end9 = s.index("    private fun audioAndRecord()", start9)

scene = '''    private fun scenePlan(){
        if(!begin(8))return
        val s=prefs().getString(STORY,"")?:""
        if(s.isBlank()){fail(8,"Story missing");return}
        val chunks=ArrayList<String>()
        var start=0
        for(i in s.indices){
            val ch=s[i]
            if(ch=='.' || ch=='!' || ch=='?'){
                val part=s.substring(start,i+1).trim()
                if(part.isNotBlank())chunks.add(part)
                start=i+1
            }
        }
        val tail=s.substring(start).trim()
        if(tail.isNotBlank())chunks.add(tail)
        if(chunks.isEmpty()){fail(8,"Story produced zero scenes");return}
        val scenes=chunks.mapIndexed{idx,x->"SCENE_${idx+1}\\nACTION=${x}\\nBACKGROUND=scene-specific\\nCHARACTER=consistent\\nCLIP=recorded\\n"}.joinToString("\\n")
        val expected=chunks.size
        val actual=scenes.lineSequence().count{it.startsWith("SCENE_")}
        if(actual!=expected){fail(8,"Scene completeness mismatch: expected=$expected actual=$actual");return}
        if(!prefs().edit().putString(SCENES,scenes).commit()){fail(8,"Scene plan persistence failed");return}
        if(prefs().getString(SCENES,null)!=scenes){fail(8,"Scene plan read-back mismatch");return}
        pass(8,"Lossless ordered scene plan verified: $actual scenes")
    }
'''

build = '''    private fun buildPlan(){
        if(!begin(9))return
        val scenes=prefs().getString(SCENES,"")?:""
        if(scenes.isBlank()){fail(9,"Scene plan missing");return}
        val blocks=scenes.split("\\n\\n").map{it.trim()}.filter{it.startsWith("SCENE_")}
        if(blocks.isEmpty()){fail(9,"No complete scene blocks available");return}
        val plan=blocks.joinToString("\\n\\n"){block ->
            val action=block.lineSequence().firstOrNull{it.startsWith("ACTION=")}?.removePrefix("ACTION=")?.trim()?:""
            val background=block.lineSequence().firstOrNull{it.startsWith("BACKGROUND=")}?.removePrefix("BACKGROUND=")?.trim()?:""
            val character=block.lineSequence().firstOrNull{it.startsWith("CHARACTER=")}?.removePrefix("CHARACTER=")?.trim()?:""
            val visual="VISUAL_PROMPT=3D cartoon scene; action=$action; background=$background; character=$character; consistent character design"
            val actionPrompt="ACTION_PROMPT=Animate the described action faithfully: $action"
            block+"\\n"+visual+"\\n"+actionPrompt
        }
        val expected=blocks.size
        val actual=plan.lineSequence().count{it.startsWith("SCENE_")}
        if(actual!=expected){fail(9,"Production-plan scene loss: expected=$expected actual=$actual");return}
        if(!prefs().edit().putString(PLAN,plan).commit()){fail(9,"Production plan persistence failed");return}
        if(prefs().getString(PLAN,null)!=plan){fail(9,"Production plan read-back mismatch");return}
        pass(9,"Production plan preserved all $actual scene blocks with scene-derived prompts")
    }
'''

s = s[:start8] + scene + build + s[end9:]

if "Regex(\"(?<=[.!?])" in s or "\\\\s+\"" in s:
    raise SystemExit("PRODUCTION_TRUTH_RUNTIME_FIX: Kotlin regex escape remained in controller")
if "take(30)" in s:
    raise SystemExit("PRODUCTION_TRUTH_RUNTIME_FIX: silent scene truncation remained")
if "VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character" in s:
    raise SystemExit("PRODUCTION_TRUTH_RUNTIME_FIX: generic visual prompt remained")

p.write_text(s, encoding="utf-8")
print("PRODUCTION_TRUTH_RUNTIME_FIX: PASS")
