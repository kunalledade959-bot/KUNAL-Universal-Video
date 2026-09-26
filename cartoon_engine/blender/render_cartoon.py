"""KUNAL Cartoon Studio Blender renderer.

Run:
  blender -b --python render_cartoon.py -- --story ../example_story.json --output out.mp4

This is a deterministic procedural fallback renderer. Replace the fallback
meshes with production characters/world assets without changing the timeline
contract.
"""

from __future__ import annotations
import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent


def args_after_double_dash():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--story", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--preview", action="store_true")
    return p.parse_args(args_after_double_dash())


def rgba(v, fallback):
    return tuple(v) if isinstance(v, list) and len(v) == 4 else fallback


def mat(name, color, roughness=0.72):
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.roughness = roughness
    return m


def cube(name, loc, scale, material, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new("soft_edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    o.data.materials.append(material)
    return o


def sphere(name, loc, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return o


def build_world(story):
    w = story["world"]
    ground = mat("Ground", rgba(w.get("ground"), (0.35, 0.58, 0.22, 1)))
    sky = mat("Sky", rgba(w.get("sky"), (0.55, 0.78, 1.0, 1)))

    cube("Ground", (0, 0, -0.35), (12, 12, 0.35), ground, 0)
    bpy.context.scene.world.color = sky.diffuse_color[:3]

    # Simple village silhouettes: intentionally replaceable assets.
    house = mat("House", (0.82, 0.55, 0.32, 1))
    roof = mat("Roof", (0.45, 0.12, 0.06, 1))
    for x in (-7, 7):
        cube("House", (x, 2, 1.0), (2.0, 1.8, 1.0), house)
        cube("Roof", (x, 2, 2.35), (2.3, 2.0, 0.35), roof)


def make_human(c):
    d = c["dna"]
    s = float(d.get("body_scale", 1.0))
    skin = mat(c["id"] + "_skin", rgba(d.get("skin"), (0.55, 0.30, 0.18, 1)))
    shirt = mat(c["id"] + "_shirt", rgba(d.get("shirt"), (0.05, 0.25, 0.75, 1)))
    pants = mat(c["id"] + "_pants", rgba(d.get("pants"), (0.08, 0.08, 0.12, 1)))
    hair = mat(c["id"] + "_hair", rgba(d.get("hair"), (0.04, 0.02, 0.01, 1)))

    root = bpy.data.objects.new(c["id"], None)
    bpy.context.collection.objects.link(root)

    torso = cube(c["id"]+"_torso", (0, 0, 1.7*s), (0.48*s, 0.30*s, 0.72*s), shirt)
    head = sphere(c["id"]+"_head", (0, 0, 2.75*s), (0.43*s, 0.38*s, 0.48*s), skin)
    hair_o = sphere(c["id"]+"_hair", (0, -0.02*s, 3.02*s), (0.44*s, 0.39*s, 0.22*s), hair)
    arm_l = cube(c["id"]+"_armL", (-0.62*s, 0, 1.72*s), (0.16*s, 0.16*s, 0.60*s), shirt)
    arm_r = cube(c["id"]+"_armR", (0.62*s, 0, 1.72*s), (0.16*s, 0.16*s, 0.60*s), shirt)
    leg_l = cube(c["id"]+"_legL", (-0.23*s, 0, 0.65*s), (0.18*s, 0.18*s, 0.62*s), pants)
    leg_r = cube(c["id"]+"_legR", (0.23*s, 0, 0.65*s), (0.18*s, 0.18*s, 0.62*s), pants)

    for o in (torso, head, hair_o, arm_l, arm_r, leg_l, leg_r):
        o.parent = root

    return root


def make_dog(c):
    d = c["dna"]
    s = float(d.get("body_scale", 0.55))
    fur = mat(c["id"]+"_fur", rgba(d.get("fur"), (0.55, 0.32, 0.16, 1)))
    root = bpy.data.objects.new(c["id"], None)
    bpy.context.collection.objects.link(root)
    body = sphere(c["id"]+"_body", (0,0,0.65*s), (0.9*s,0.45*s,0.5*s), fur)
    head = sphere(c["id"]+"_head", (0.75*s,0,0.85*s), (0.45*s,0.40*s,0.42*s), fur)
    for o in (body, head):
        o.parent = root
    return root


def character_factory(c):
    return make_human(c) if c.get("type") == "human" else make_dog(c)


def key(root, frame, location=None, rotation=None):
    if location is not None:
        root.location = location
        root.keyframe_insert(data_path="location", frame=frame)
    if rotation is not None:
        root.rotation_euler = rotation
        root.keyframe_insert(data_path="rotation_euler", frame=frame)


def animate_actor(root, actor):
    start, end = int(actor["start"]), int(actor["end"])
    action = actor["action"]
    if "position" in actor:
        p = actor["position"]
        key(root, start, (p[0], p[1], p[2]))
        key(root, end, (p[0], p[1], p[2]))
        return

    a = actor.get("from", [0,0,0])
    b = actor.get("to", a)
    key(root, start, tuple(a))
    key(root, end, tuple(b))

    if action == "walk":
        # Gentle body sway plus forward movement. Replace with rigged action
        # clips when production character assets are installed.
        for f in range(start, end + 1, 6):
            phase = (f-start) / max(1, end-start)
            root.rotation_euler[1] = math.sin(phase * math.pi * 12) * 0.025
            root.keyframe_insert(data_path="rotation_euler", frame=f)
    elif action == "run":
        for f in range(start, end + 1, 4):
            phase = (f-start) / max(1, end-start)
            root.rotation_euler[1] = math.sin(phase * math.pi * 18) * 0.045
            root.keyframe_insert(data_path="rotation_euler", frame=f)
    elif action == "look_right":
        key(root, start, rotation=(0,0,0))
        key(root, end, rotation=(0,0,math.radians(-25)))
    elif action == "sit":
        key(root, start, rotation=(math.radians(75),0,0))
        key(root, end, rotation=(math.radians(75),0,0))


def setup_camera(story):
    bpy.ops.object.camera_add(location=(0, -13, 6), rotation=(math.radians(72), 0, 0))
    cam = bpy.context.object
    cam.name = "StoryCamera"
    bpy.context.scene.camera = cam
    cam.data.lens = 42
    return cam


def animate_camera(cam, scenes):
    for scene in scenes:
        shot = scene.get("camera", {})
        start, end = int(scene["start"]), int(scene["end"])
        loc = (float(shot.get("x", 0)), float(shot.get("y", -10)), float(shot.get("z", 5)))
        key(cam, start, loc)
        key(cam, end, loc)


def setup_lighting():
    bpy.ops.object.light_add(type="AREA", location=(0,-4,8))
    key = bpy.context.object
    key.data.energy = 1100
    key.data.shape = "DISK"
    key.data.size = 7

    bpy.ops.object.light_add(type="AREA", location=(5,2,4))
    fill = bpy.context.object
    fill.data.energy = 500
    fill.data.size = 5


def main():
    args = parse_args()
    story = json.loads(Path(args.story).read_text(encoding="utf-8"))

    project = story["project"]
    fps = int(project["fps"])
    duration = float(project["duration_seconds"])
    total_frames = round(fps * duration)

    if total_frames < 1:
        raise SystemExit("FAIL: invalid duration")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.resolution_x = int(project["width"])
    scene.render.resolution_y = int(project["height"])
    scene.render.resolution_percentage = 35 if args.preview else 100
    scene.frame_start = 1
    scene.frame_end = total_frames

    # Eevee is selected for practical animation throughput.
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except Exception:
        pass

    build_world(story)
    setup_lighting()
    cam = setup_camera(story)
    animate_camera(cam, story["scenes"])

    registry = {}
    for c in story["characters"]:
        registry[c["id"]] = character_factory(c)

    for scene_data in story["scenes"]:
        for actor in scene_data.get("actors", []):
            animate_actor(registry[actor["character"]], actor)

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.filepath = str(output)

    # Render the actual animation. No fake frame generation.
    bpy.ops.render.render(animation=True)

    if not output.exists():
        raise SystemExit(f"FAIL: renderer completed without output: {output}")

    print(f"PASS: rendered {output} | frames={total_frames} | fps={fps} | seconds={duration:.3f}")


if __name__ == "__main__":
    main()
