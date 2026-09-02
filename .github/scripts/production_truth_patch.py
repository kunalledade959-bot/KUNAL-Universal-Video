#!/usr/bin/env python3
"""Deterministic source patch for known production-truth violations.

The patch is intentionally exact: if the expected source is not present, it fails
instead of silently producing a partially patched APK. It only changes the checked
in production controller and never invents missing implementation.
"""
from pathlib import Path

p = Path("activity_fixed.kt")
s = p.read_text(encoding="utf-8")

replacements = [
(
'''        prefs().edit().putString(STORY,s).apply();pass(5,"Story persisted (${s.length} chars)")''',
'''        val editor=prefs().edit().putString(STORY,s)
        if(!editor.commit()){fail(5,"Story persistence commit failed");return}
        val stored=prefs().getString(STORY,null)
        if(stored!=s){fail(5,"Story persistence read-back mismatch");return}
        val digest=java.security.MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString(""){ "%02x".format(it) }
        prefs().edit().putString("story_sha256",digest).commit()
        pass(5,"Story persisted and read-back verified (${s.length} chars, sha256=$digest)")'''
),
(
'''        val parts=s.split(Regex("(?<=[.!?])\\\\s+")).filter{it.isNotBlank()}.take(30);val chunks=if(parts.isEmpty())listOf(s)else parts
        val scenes=chunks.mapIndexed{idx,x->"SCENE_${idx+1}\\nACTION=${x.trim()}\\nBACKGROUND=scene-specific\\nCHARACTER=consistent\\nCLIP=recorded\\n"}.joinToString("\\n")
        prefs().edit().putString(SCENES,scenes).apply();pass(8,"Ordered scene plan created: ${chunks.size} scenes")''',
'''        val chunks=s.split(Regex("(?<=[.!?])\\\\s+")).map{it.trim()}.filter{it.isNotBlank()}
        if(chunks.isEmpty()){fail(8,"Story produced zero scenes");return}
        val scenes=chunks.mapIndexed{idx,x->"SCENE_${idx+1}\\nACTION=${x}\\nBACKGROUND=scene-specific\\nCHARACTER=consistent\\nCLIP=recorded\\n"}.joinToString("\\n")
        val expected=chunks.size
        val actual=Regex("(?m)^SCENE_\\\\d+$").findAll(scenes).count()
        if(actual!=expected){fail(8,"Scene completeness mismatch: expected=$expected actual=$actual");return}
        if(!prefs().edit().putString(SCENES,scenes).commit()){fail(8,"Scene plan persistence failed");return}
        val stored=prefs().getString(SCENES,null)
        if(stored!=scenes){fail(8,"Scene plan read-back mismatch");return}
        pass(8,"Lossless ordered scene plan verified: $actual scenes")'''
),
(
'''        val plan=scenes.lines().filter{it.startsWith("SCENE_")}.joinToString("\\n"){it+" | VISUAL_PROMPT=cinematic_3D_cartoon_consistent_character | ACTION_PROMPT=execute_scene_action"}
        prefs().edit().putString(PLAN,plan).apply();pass(9,"Production prompts generated for every ordered scene")''',
'''        val blocks=scenes.split(Regex("\\n\\s*\\n")).map{it.trim()}.filter{it.startsWith("SCENE_")}
        if(blocks.isEmpty()){fail(9,"No complete scene blocks available");return}
        val plan=blocks.joinToString("\\n\\n"){block ->
            block+"\\nVISUAL_PROMPT=cinematic_3D_cartoon_consistent_character | ACTION_PROMPT=execute_scene_action"
        }
        val expected=blocks.size
        val actual=Regex("(?m)^SCENE_\\\\d+$").findAll(plan).count()
        if(actual!=expected){fail(9,"Production-plan scene loss: expected=$expected actual=$actual");return}
        if(!prefs().edit().putString(PLAN,plan).commit()){fail(9,"Production plan persistence failed");return}
        val stored=prefs().getString(PLAN,null)
        if(stored!=plan){fail(9,"Production plan read-back mismatch");return}
        pass(9,"Production plan preserved all $actual scene blocks with prompts")'''
),
]

for old, new in replacements:
    if old not in s:
        raise SystemExit("PRODUCTION_TRUTH_PATCH: expected source fragment missing; refusing partial patch")
    s = s.replace(old, new, 1)

old6='''            var nodes=0
            fun probe(n:AccessibilityNodeInfo?){if(n==null)return;nodes++;for(k in 0 until n.childCount)probe(n.getChild(k))}
            probe(root);root.recycle()'''
new6='''            var nodes=0
            val queue=java.util.ArrayDeque<AccessibilityNodeInfo>()
            queue.add(root)
            while(queue.isNotEmpty() && nodes<5000){
                val n=queue.removeFirst();nodes++
                for(k in 0 until minOf(n.childCount,256)){n.getChild(k)?.let{queue.addLast(it)}}
            }
            queue.clear()
            root.recycle()'''
if old6 not in s:
    raise SystemExit("PRODUCTION_TRUTH_PATCH: Stage 6 traversal fragment missing")
s=s.replace(old6,new6,1)

old7='''        var nodes=0;var clickable=0;var editable=0
        fun walk(n:AccessibilityNodeInfo?){if(n==null)return;nodes++;if(n.isClickable)clickable++;if(n.isEditable)editable++;for(i in 0 until n.childCount)walk(n.getChild(i))}
        walk(root);root.recycle()'''
new7='''        var nodes=0;var clickable=0;var editable=0
        val queue=java.util.ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        while(queue.isNotEmpty() && nodes<10000){
            val n=queue.removeFirst();nodes++
            if(n.isClickable)clickable++;if(n.isEditable)editable++
            for(i in 0 until minOf(n.childCount,256)){n.getChild(i)?.let{queue.addLast(it)}}
        }
        queue.clear()
        root.recycle()'''
if old7 not in s:
    raise SystemExit("PRODUCTION_TRUTH_PATCH: Stage 7 traversal fragment missing")
s=s.replace(old7,new7,1)

p.write_text(s, encoding="utf-8")
print("PRODUCTION_TRUTH_PATCH: PASS")
