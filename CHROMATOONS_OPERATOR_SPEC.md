# ChromaToons Operator Specification — Validation Lab

## Purpose
The validation branch must treat ChromaToons as a manual animation editor. The automation must reproduce the user workflow rather than pretending that one Record click creates a finished story.

## Target
- Package: bhootiyadreamstv.moboapp.chromatoons
- Control: user-enabled Android AccessibilityService plus gestures where the target exposes no accessibility node.
- Output: target-produced video/image sequence, then verified Gallery export.

## Required per-scene workflow
1. Launch/return to ChromaToons and verify foreground package.
2. Discover the current screen and record all accessible controls with text, content-description, resource-id, class, bounds and supported actions.
3. Identify the scene editor state. Never guess a coordinate when a semantic control is available.
4. Open/select the character menu and select required characters. Verify each selected character is visible in the scene.
5. Position characters using the target's move interaction. For canvas-only controls, use a calibrated gesture derived from the live node/screen geometry, never a hard-coded device coordinate.
6. Select/set the scene background appropriate to the scene. Verify the scene state changed before continuing.
7. Configure animation using the available keyframe/IK workflow. Verify the keyframe/timeline state after each critical operation.
8. Prepare narration/dialogue audio and synchronize it through the target's audio timeline where the target exposes that workflow. Do not treat Android TTS file creation as proof that ChromaToons received the audio.
9. Record only the current scene/clip. Verify a non-empty output is produced before advancing.
10. Repeat independently for every scene, changing background/characters/actions/audio as required.
11. Assemble the verified clips using an explicit assembly step. If the target app itself does not provide clip assembly, do not pretend that MediaProjection is assembly. Use a deterministic local media assembly stage and verify the resulting MP4.
12. Run media verification: readable MP4, non-zero duration, dimensions, frame/sample decode, and expected scene/clip count evidence.
13. Export the final verified file to MediaStore and re-query the exact content URI.

## Fail-closed rules
- No guessed label may be treated as a verified ChromaToons control.
- No stage 9 PASS unless at least one real target state transition is observed after an action.
- No stage 10 PASS unless a real video file is produced.
- No stage 11 PASS unless the video is decoded successfully and matches the expected scene evidence.
- No stage 12 PASS unless the exact final URI exists and is readable.
- If a control is not exposed through Accessibility, the operator must enter calibration/discovery mode and capture evidence before using a gesture.
- Device-specific encoder failure must be handled by trying the target-supported encoder settings documented by ChromaToons, with each attempt verified.

## Evidence schema
Each scene must record:
- scene id
- target screen fingerprint before action
- action sequence
- matched control identifiers/bounds
- post-action fingerprint
- recording URI/metadata
- verification result

## Merge gate
This specification is a hard requirement for the validation branch. The production/locked APK must not be changed until the complete workflow has passed on a physical Android device with ChromaToons installed.
