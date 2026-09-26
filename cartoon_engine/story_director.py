"""Deterministic story/timeline validator.

This module intentionally does not pretend to be a generative model. A future
LLM adapter can produce this JSON, but the production renderer consumes only a
validated schema.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_ACTIONS = {
    "human": {"idle", "walk", "run", "look_right", "talk", "sit"},
    "dog": {"idle", "walk", "run", "sit", "jump"},
}


@dataclass(frozen=True)
class Project:
    fps: int
    width: int
    height: int
    duration_seconds: float


def load_story(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_story(data)
    return data


def validate_story(data: dict) -> Project:
    project = data.get("project", {})
    fps = int(project.get("fps", 24))
    width = int(project.get("width", 720))
    height = int(project.get("height", 1280))
    duration = float(project.get("duration_seconds", 0))

    if fps <= 0 or width <= 0 or height <= 0 or duration <= 0:
        raise ValueError("Invalid project timing/resolution")

    characters = {c["id"]: c for c in data.get("characters", [])}
    if not characters:
        raise ValueError("No characters defined")

    for scene in data.get("scenes", []):
        if scene["start"] < 1 or scene["end"] < scene["start"]:
            raise ValueError(f"Invalid scene range: {scene['id']}")
        for actor in scene.get("actors", []):
            cid = actor["character"]
            if cid not in characters:
                raise ValueError(f"Unknown character: {cid}")
            ctype = characters[cid].get("type", "human")
            action = actor["action"]
            if action not in SUPPORTED_ACTIONS.get(ctype, set()):
                raise ValueError(f"Unsupported action '{action}' for {ctype}:{cid}")

    expected_frames = round(duration * fps)
    max_end = max((s["end"] for s in data.get("scenes", [])), default=0)
    if max_end > expected_frames:
        raise ValueError(
            f"Timeline exceeds project duration: end={max_end}, expected={expected_frames}"
        )

    return Project(fps=fps, width=width, height=height, duration_seconds=duration)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("story")
    args = parser.parse_args()
    p = load_story(args.story)
    print(f"VALID: {p.fps} FPS, {p.width}x{p.height}, {p.duration_seconds:.3f}s")
