from __future__ import annotations
import json
from pathlib import Path

def compile_manifest(story: dict) -> dict:
    project=story["project"]
    fps=int(project.get("fps",24)); duration=float(project["duration_seconds"])
    total=round(fps*duration)
    characters={c["id"]:c for c in story.get("characters",[])}
    if not characters: raise ValueError("Story must contain at least one character")
    scenes=story.get("scenes",[])
    if not scenes: raise ValueError("Story must contain at least one scene")
    frames=[]
    for n in range(1,total+1):
        scene=next((s for s in scenes if s["start"]<=n<=s["end"]),None)
        if scene is None: continue
        frames.append({"frame_id":f"frame_{n:06d}","frame":n,"timestamp":(n-1)/fps,"scene_id":scene["id"],"status":"queued"})
    return {"fps":fps,"duration_seconds":duration,"expected_frames":total,"frames":frames}

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("story"); ap.add_argument("output")
    a=ap.parse_args(); data=json.loads(Path(a.story).read_text(encoding="utf-8"))
    Path(a.output).write_text(json.dumps(compile_manifest(data),indent=2),encoding="utf-8")

if __name__=="__main__": main()
