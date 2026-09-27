from __future__ import annotations
import json,sys
from pathlib import Path
from cartoon_engine.story_director import load_story
from cartoon_engine.story_to_manifest import compile_manifest

def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: python -m cartoon_engine.build_manifest story.json manifest.json")
    load_story(sys.argv[1])
    data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    manifest=compile_manifest(data)
    Path(sys.argv[2]).write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"MANIFEST {manifest['expected_frames']} frames @ {manifest['fps']} FPS")

if __name__=="__main__": main()
