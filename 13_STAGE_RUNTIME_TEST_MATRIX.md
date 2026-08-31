# KUNAL Universal Video — 13-Stage Runtime Test Matrix

Purpose: convert the 13-stage problem catalog into explicit tests. This file is the execution contract. A test is not considered PASS merely because a string exists in source.

Status meanings:
- `STATIC`: can be exercised/verified in CI from source or deterministic unit-style harness.
- `EMULATOR`: requires Android runtime/emulator execution.
- `DEVICE`: requires the physical Android phone and production APK.
- `BOTH`: source guard plus runtime execution are required.
- `PENDING`: no runtime evidence yet.

## Stage 1 — START / DIAGNOSTIC
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S01-P01 | Activity creation failure | startup FAIL, no false PASS | BOTH | PENDING |
| S01-P02 | StageGate refuses RUNNING | explicit startup FAIL | STATIC | PENDING |
| S01-P03 | installed-app query empty | stage 1 FAIL | BOTH | PENDING |
| S01-P04 | PackageManager exception/unusable result | caught exception + FAIL | BOTH | PENDING |
| S01-P05 | UI construction failure | startup failure evidence | BOTH | PENDING |
| S01-P06 | SharedPreferences read/write failure | session/data persistence FAIL | BOTH | PENDING |
| S01-P07 | session ID missing after restart | persistent session evidence | BOTH | PENDING |
| S01-P08 | TTS init never succeeds | audio path cannot silently PASS | BOTH | PENDING |
| S01-P09 | local bridge start failure | connection unavailable | BOTH | PENDING |
| S01-P10 | stale/crashed status rendering | visible consistent state | DEVICE | PENDING |
| S01-P11 | process killed after launch | restart preserves safe state | DEVICE | PENDING |
| S01-P12 | Activity recreation | gate/session/controller state recovered | DEVICE | PENDING |

## Stage 2 — ENABLE ACCESSIBILITY / CONNECT
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S02-P01 | accessibility disabled | explicit FAIL + settings path | BOTH | PENDING |
| S02-P02 | settings intent cannot open | visible actionable failure | DEVICE | PENDING |
| S02-P03 | service enabled but not bound | connection must not PASS | DEVICE | PENDING |
| S02-P04 | service disconnect during handshake | handshake FAIL | DEVICE | PENDING |
| S02-P05 | empty/wrong target at handshake | connection FAIL | BOTH | PENDING |
| S02-P06 | bridge null/not started | connection FAIL | STATIC | PENDING |
| S02-P07 | bridge.connect returns false | connection FAIL | BOTH | PENDING |
| S02-P08 | PING/PONG failure | no connection PASS | BOTH | PENDING |
| S02-P09 | accessibility drops after handshake | post-handshake FAIL | DEVICE | PENDING |
| S02-P10 | binder dies between checks | no false PASS | DEVICE | PENDING |
| S02-P11 | OS/security policy blocks service | explicit device failure | DEVICE | PENDING |
| S02-P12 | fake/static connection evidence | reject without live transport | STATIC/BOTH | PENDING |

## Stage 3 — SELECT / SAVE TARGET
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S03-P01 | installed list empty | selection FAIL | BOTH | PENDING |
| S03-P02 | spinner invalid position | selection FAIL | STATIC | PENDING |
| S03-P03 | no target selected | selection FAIL | STATIC | PENDING |
| S03-P04 | saved package uninstalled | reject stale target | BOTH | PENDING |
| S03-P05 | controller app selected | reject self-target | STATIC | PENDING |
| S03-P06 | target persistence write fails | FAIL, no unlock | BOTH | PENDING |
| S03-P07 | saved target lost on restart | persistence FAIL | DEVICE | PENDING |
| S03-P08 | accessibility target not updated | operation must reject stale target | BOTH | PENDING |
| S03-P09 | target changes during later stage | stage must use current target | DEVICE | PENDING |
| S03-P10 | non-launchable package selected | reject before study | BOTH | PENDING |

## Stage 4 — STUDY SELECTED APK
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S04-P01 | target not installed | FAIL | BOTH | PENDING |
| S04-P02 | application-info lookup fails | FAIL | BOTH | PENDING |
| S04-P03 | no launch activity | FAIL | BOTH | PENDING |
| S04-P04 | incomplete package metadata | explicit study failure | DEVICE | PENDING |
| S04-P05 | launch intent exists but launch fails | runtime FAIL | DEVICE | PENDING |
| S04-P06 | wrong activity among multiple activities | runtime target verification | DEVICE | PENDING |
| S04-P07 | target disabled/restricted | launch/study FAIL | DEVICE | PENDING |
| S04-P08 | target requires login/auth | study must not pretend usable | DEVICE | PENDING |
| S04-P09 | target crashes immediately | runtime FAIL | DEVICE | PENDING |
| S04-P10 | metadata-only false PASS | require runtime usability evidence | BOTH | PENDING |

## Stage 5 — SAVE STORY INPUT
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S05-P01 | blank story | FAIL | STATIC/EMULATOR | PENDING |
| S05-P02 | <10 characters | FAIL | STATIC/EMULATOR | PENDING |
| S05-P03 | preference write does not persist | FAIL | BOTH | PENDING |
| S05-P04 | process restart loses story | persistence FAIL | DEVICE | PENDING |
| S05-P05 | Unicode/emoji corruption | exact text comparison | DEVICE | PENDING |
| S05-P06 | very large story | bounded UI/memory behavior | DEVICE | PENDING |
| S05-P07 | control/unsupported characters | safe serialization | DEVICE | PENDING |
| S05-P08 | stale story read | stage must reject mismatch | BOTH | PENDING |
| S05-P09 | story field not editable/visible | UI failure | DEVICE | PENDING |
| S05-P10 | concurrent update loses input | persistence consistency | DEVICE | PENDING |

## Stage 6 — OPERATE SELECTED TARGET
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S06-P01 | missing launch intent | FAIL | STATIC | PENDING |
| S06-P02 | launch target fails | FAIL | DEVICE | PENDING |
| S06-P03 | target never becomes foreground | FAIL | DEVICE | PENDING |
| S06-P04 | accessibility instance unavailable | FAIL | DEVICE | PENDING |
| S06-P05 | root window null | FAIL | DEVICE | PENDING |
| S06-P06 | accessibility tree empty | FAIL | DEVICE | PENDING |
| S06-P07 | stale accessibility tree | reject stale observation | DEVICE | PENDING |
| S06-P08 | inaccessible UI surface | explicit limitation/FAIL | DEVICE | PENDING |
| S06-P09 | target package changes mid-operation | detect mismatch | DEVICE | PENDING |
| S06-P10 | target crash/ANR | timeout/FAIL, no unlock | DEVICE | PENDING |
| S06-P11 | target rejects click/input | action evidence must fail | DEVICE | PENDING |
| S06-P12 | PASS without actual interaction | evidence gate rejects | BOTH | PENDING |

## Stage 7 — DEEP TARGET UNDERSTANDING
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S07-P01 | accessibility drops | FAIL | DEVICE | PENDING |
| S07-P02 | target UI tree unavailable | FAIL | DEVICE | PENDING |
| S07-P03 | zero nodes | FAIL | BOTH | PENDING |
| S07-P04 | node traversal exception | safe traversal + FAIL | DEVICE | PENDING |
| S07-P05 | clickable controls not exposed | explicit capability failure | DEVICE | PENDING |
| S07-P06 | editable controls not exposed | explicit capability failure | DEVICE | PENDING |
| S07-P07 | UI mutates during traversal | stale snapshot detected | DEVICE | PENDING |
| S07-P08 | root belongs to wrong package | reject | DEVICE | PENDING |
| S07-P09 | UI map persistence fails | FAIL | BOTH | PENDING |
| S07-P10 | UI map stale after navigation | require fresh capture | DEVICE | PENDING |
| S07-P11 | WebView/custom rendering hides semantics | capability failure | DEVICE | PENDING |
| S07-P12 | permission dialog hides expected UI | wait/detect dialog, no false PASS | DEVICE | PENDING |

## Stage 8 — CREATE EXACT SCENE PLAN
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S08-P01 | missing story | FAIL | STATIC | PENDING |
| S08-P02 | persistence read failure | FAIL | BOTH | PENDING |
| S08-P03 | zero scene split | FAIL or deterministic fallback | STATIC | PENDING |
| S08-P04 | excessive story length | bounded scene generation | STATIC | PENDING |
| S08-P05 | wrong scene ordering | sequence assertion | STATIC | PENDING |
| S08-P06 | empty scene text | reject empty scene | STATIC | PENDING |
| S08-P07 | plan persistence failure | FAIL | BOTH | PENDING |
| S08-P08 | missing scene fields | schema validation | STATIC | PENDING |
| S08-P09 | special characters break serialization | round-trip test | STATIC | PENDING |
| S08-P10 | story edited after planning | stale-plan detection | BOTH | PENDING |

## Stage 9 — BUILD PRODUCTION PLAN / PROMPTS
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S09-P01 | scene plan missing | FAIL | STATIC | PENDING |
| S09-P02 | zero scenes | FAIL | STATIC | PENDING |
| S09-P03 | prompts missing for scenes | count equality check | STATIC | PENDING |
| S09-P04 | prompt order differs | ordered-ID assertion | STATIC | PENDING |
| S09-P05 | visual prompt missing | schema FAIL | STATIC | PENDING |
| S09-P06 | action prompt missing | schema FAIL | STATIC | PENDING |
| S09-P07 | plan persistence failure | FAIL | BOTH | PENDING |
| S09-P08 | stale prompts after story edit | invalidate/rebuild | BOTH | PENDING |
| S09-P09 | malformed separators/newlines | serialization round-trip | STATIC | PENDING |
| S09-P10 | output cannot map to scene | mapping validation | BOTH | PENDING |

## Stage 10 — AUDIO / VOICE / MUSIC / SFX + RECORD
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S10-P01 | story missing for narration | FAIL | STATIC | PENDING |
| S10-P02 | TTS object null | FAIL | BOTH | PENDING |
| S10-P03 | TTS init fails | FAIL | DEVICE | PENDING |
| S10-P04 | language setup fails | FAIL | DEVICE | PENDING |
| S10-P05 | synthesis returns failure | FAIL | BOTH | PENDING |
| S10-P06 | WAV absent/too small | FAIL | BOTH | PENDING |
| S10-P07 | audio path not persisted | FAIL | BOTH | PENDING |
| S10-P08 | MediaProjection permission cancelled | FAIL | BOTH | PENDING |
| S10-P09 | recording service fails to start | FAIL | DEVICE | PENDING |
| S10-P10 | recording stops without MP4 | FAIL | BOTH | PENDING |
| S10-P11 | stale/invalid recording URI | reject | BOTH | PENDING |
| S10-P12 | empty/unusable media tracks | FAIL | BOTH | PENDING |
| S10-P13 | microphone/audio route unavailable | explicit audio failure | DEVICE | PENDING |
| S10-P14 | long recording exceeds storage/memory/time | controlled failure/recovery | DEVICE | PENDING |
| S10-P15 | capture records wrong surface | surface/package evidence | DEVICE | PENDING |
| S10-P16 | system permission dialog interrupts recording | detect interruption | DEVICE | PENDING |

## Stage 11 — ASSEMBLE / EDIT
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S11-P01 | no visual clip | FAIL | BOTH | PENDING |
| S11-P02 | narration missing | FAIL | BOTH | PENDING |
| S11-P03 | video FD unavailable | FAIL | BOTH | PENDING |
| S11-P04 | video extractor cannot open | FAIL | BOTH | PENDING |
| S11-P05 | audio extractor cannot open | FAIL | BOTH | PENDING |
| S11-P06 | no video track | FAIL | BOTH | PENDING |
| S11-P07 | no audio track | FAIL | BOTH | PENDING |
| S11-P08 | unsupported codec/container | FAIL | DEVICE/BOTH | PENDING |
| S11-P09 | corrupt samples | FAIL | DEVICE | PENDING |
| S11-P10 | mux addTrack fails | FAIL | DEVICE | PENDING |
| S11-P11 | mux start/stop fails | FAIL | DEVICE | PENDING |
| S11-P12 | output missing/too small | FAIL | BOTH | PENDING |
| S11-P13 | output storage disappears/full | FAIL | DEVICE | PENDING |
| S11-P14 | timestamps invalid/misaligned | media validation FAIL | DEVICE | PENDING |
| S11-P15 | very large media causes pressure | controlled failure | DEVICE | PENDING |

## Stage 12 — VERIFY / AUTO-FIX
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S12-P01 | Stage 11 not PASS | locked/FAIL | STATIC | PENDING |
| S12-P02 | assembled path missing | FAIL | STATIC | PENDING |
| S12-P03 | output disappears between checks | FAIL | DEVICE | PENDING |
| S12-P04 | unreadable media | FAIL | DEVICE | PENDING |
| S12-P05 | zero/invalid duration | FAIL | DEVICE | PENDING |
| S12-P06 | audio track absent | FAIL | DEVICE | PENDING |
| S12-P07 | video track absent | FAIL | DEVICE | PENDING |
| S12-P08 | auto-fix does not re-verify | reject PASS | STATIC | PENDING |
| S12-P09 | auto-fix loops | bounded retry/FAIL | BOTH | PENDING |
| S12-P10 | metadata-only false PASS | media decode/track evidence | BOTH | PENDING |
| S12-P11 | verification result persistence fails | FAIL | BOTH | PENDING |
| S12-P12 | verification process crash | controlled FAIL/restart | DEVICE | PENDING |

## Stage 13 — FINAL GALLERY EXPORT
| ID | Failure to provoke | Expected protection/evidence | Level | Status |
|---|---|---|---|---|
| S13-P01 | Stage 12 not PASS | export locked | STATIC | PENDING |
| S13-P02 | final URI/path missing | FAIL | STATIC | PENDING |
| S13-P03 | MediaStore insert failure | FAIL | DEVICE | PENDING |
| S13-P04 | output stream cannot open | FAIL | BOTH | PENDING |
| S13-P05 | IS_PENDING not finalized | export FAIL/incomplete | DEVICE | PENDING |
| S13-P06 | Gallery visibility failure | export not PASS | DEVICE | PENDING |
| S13-P07 | wrong MIME/container | FAIL | DEVICE | PENDING |
| S13-P08 | zero/too-small export | FAIL | BOTH | PENDING |
| S13-P09 | name collision | correct URI/result required | DEVICE | PENDING |
| S13-P10 | storage full | explicit FAIL | DEVICE | PENDING |
| S13-P11 | scoped-storage policy rejects write | explicit device failure | DEVICE | PENDING |
| S13-P12 | process killed during export | safe recovery/no false PASS | DEVICE | PENDING |
| S13-P13 | URI not persisted | FAIL | BOTH | PENDING |
| S13-P14 | PASS before Gallery verification | reject premature PASS | BOTH | PENDING |

## Cross-stage adversarial tests
| ID | Failure | Expected result | Level | Status |
|---|---|---|---|---|
| X-P01 | kill app after Stage 2 PASS | safe restart, no fabricated later PASS | DEVICE | PENDING |
| X-P02 | disconnect Accessibility after Stage 2 | later stages blocked/FAIL | DEVICE | PENDING |
| X-P03 | change target after Stage 3 | stale target detected | DEVICE | PENDING |
| X-P04 | edit story after Stage 8 | scene/prompt invalidation | BOTH | PENDING |
| X-P05 | background target during operation | foreground prerequisite fails | DEVICE | PENDING |
| X-P06 | permission dialog steals focus | stage waits/fails safely | DEVICE | PENDING |
| X-P07 | lock screen during recording | controlled failure/recovery | DEVICE | PENDING |
| X-P08 | rotate/recreate Activity mid-stage | state preserved | DEVICE | PENDING |
| X-P09 | low storage during recording | explicit failure | DEVICE | PENDING |
| X-P10 | low storage during export | explicit failure | DEVICE | PENDING |
| X-P11 | duplicate tap starts stage twice | idempotent/busy guard | DEVICE | PENDING |
| X-P12 | duplicate callback arrives after FAIL | FAIL remains authoritative | BOTH | PENDING |
| X-P13 | stale SharedPreferences artifact | mismatch detected | BOTH | PENDING |
| X-P14 | file URI exists but is unreadable | media validation FAIL | BOTH | PENDING |
| X-P15 | green CI while physical phone untested | verdict remains DEVICE-PENDING | STATIC | PENDING |

## Required verdict rule
A sequence may be called `WORKING` only when its required runtime level has PASS evidence. Static checks alone may establish `STATIC PASS`, and hosted Android may establish `EMULATOR PASS`. Neither may be relabeled as `REAL DEVICE PASS`.

## Current baseline
This matrix intentionally starts at `PENDING`. It is a test inventory, not fabricated evidence. The next repair/test cycle must convert entries to PASS/FAIL with concrete logs and preserve every discovered failure as a regression test.
