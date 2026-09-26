# KUNAL Cartoon Studio Engine v1

Purpose: turn a structured story into a repeatable 3D cartoon scene/timeline without regenerating the character every frame.

## Architecture

Story -> Story Director -> Character DNA -> World DNA -> Scene Timeline -> Actions -> Camera -> Blender render -> MP4

The renderer is designed around real 3D objects, rigs/actions, keyframes and Blender's animation/render pipeline. Blender supports Python automation and background rendering through its Python API. See the official API: https://docs.blender.org/api/

## Important quality rule

Do not use contact sheets, duplicated images, or AI-generated stills as fake animation frames. Frames must come from the animated 3D scene.

## Current implementation

- multi-character registry
- reusable Character DNA records
- scene/timeline representation
- action clips
- camera shots
- 24 FPS timeline
- Blender background renderer
- direct FFmpeg movie output through Blender
- validation of frame count/duration before rendering
- fail-closed validation for unknown characters/actions

## Current limitation

This branch contains the engine foundation and a procedural stylized asset fallback. It is NOT yet a verified Pixar/Disney-quality asset library. High-quality production models, rigs, materials, voices and motion clips must be supplied/licensed and then locked into the registry.

## First test

Use `example_story.json`.

From a machine with Blender installed:

```bash
blender -b --python cartoon_engine/blender/render_cartoon.py -- --story cartoon_engine/example_story.json --output output/raju_test.mp4
```

For a fast diagnostic, add `--preview` to render at low resolution.

Do not call the result production-ready until the rendered MP4 is inspected.
