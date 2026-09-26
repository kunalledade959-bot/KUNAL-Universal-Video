# One-command cartoon test

## 1. Install Blender

Install a current supported Blender release on the computer that will do the render.

## 2. Run

From repository root:

```bash
blender -b --python cartoon_engine/blender/render_cartoon.py -- \
  --story cartoon_engine/example_story.json \
  --output output/raju_test.mp4
```

Fast preview:

```bash
blender -b --python cartoon_engine/blender/render_cartoon.py -- \
  --story cartoon_engine/example_story.json \
  --output output/raju_preview.mp4 \
  --preview
```

## 3. Production path

After the test is visually inspected:

1. Replace procedural fallback meshes with licensed/high-quality 3D characters.
2. Add rig/action libraries.
3. Add facial/eye/mouth controls.
4. Add character interaction constraints.
5. Add camera shot templates.
6. Add TTS/SFX/music.
7. Add a story-to-JSON AI planner.
8. Add render validation and automatic retry.
9. Only then expose the one-click Story -> MP4 button.

The current branch deliberately refuses to call the procedural test “production quality”.
