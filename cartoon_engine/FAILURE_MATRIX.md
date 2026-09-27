# KUNAL Story-to-Video Failure Matrix

The engine must fail closed: a frame is complete only after the output exists and passes validation.

## Failure classes and recovery

| Class | Detection | Recovery | Retry limit | Final state |
|---|---|---|---:|---|
| Browser/tab crash | worker heartbeat missing | restart worker, resume queued job | 3 | retry/dead-letter |
| Page load timeout | page-ready timeout | reload page | 3 | retry/dead-letter |
| Generator button missing | selector/semantic search fails | refresh, selector fallback | 2 | blocked |
| Login/CAPTCHA/rate-limit | page text/DOM signal | stop worker, never bypass | 0 | blocked |
| Generation timeout | job exceeds timeout | poll once, then retry | 3 | retry/dead-letter |
| Wrong output count | manifest/output mismatch | collect again, then retry missing IDs only | 3 | retry/dead-letter |
| Duplicate output | checksum/frame hash collision | reject duplicate and regenerate affected ID | 3 | retry/dead-letter |
| Corrupt image | decoder/size check fails | delete invalid artifact, regenerate | 3 | retry/dead-letter |
| Wrong dimensions | dimension validator fails | reject and regenerate | 3 | retry/dead-letter |
| Blank/near-blank image | quality heuristic fails | reject and regenerate | 3 | retry/dead-letter |
| Character drift | reference/continuity validator fails | regenerate with locked Character DNA | 3 | retry/dead-letter |
| Wrong scene/frame | frame metadata mismatch | reject and regenerate exact frame ID | 3 | retry/dead-letter |
| Network disconnect | request/worker heartbeat failure | exponential backoff, resume checkpoint | 5 | retry/dead-letter |
| Disk full | free-space threshold | pause generation, clean only temporary files | 0 | paused |
| RAM/GPU pressure | process failure/OOM | reduce batch, restart worker | 3 | retry |
| MP4 encode failure | FFmpeg/Blender exit nonzero or missing file | resume from verified frames, re-encode | 2 | failed |
| Audio missing | track absent/invalid | regenerate only audio stage | 2 | failed |
| Audio/video duration mismatch | duration validator | time-stretch/trim only within configured tolerance, else fail | 2 | failed |
| App restart | persisted state exists | load checkpoint and continue | 0 | resume |
| Power loss | persisted checkpoint | resume from last atomic checkpoint | 0 | resume |
| Partial batch | only some IDs verified | enqueue missing IDs only | 3 | retry |
| Service limit | explicit quota/limit response | pause, preserve state | 0 | blocked |
| Unknown exception | uncaught error | capture diagnostics, isolate job | 1 | dead-letter |

## Non-negotiable rules

1. Never mark a frame complete from a request response alone.
2. Never count a duplicate or corrupt file as success.
3. Never regenerate verified frames during retry.
4. Never bypass CAPTCHA, authentication, paywalls, quotas, or rate limits.
5. Every state transition is persisted atomically.
6. Every retry has an attempt counter and reason.
7. A dead-letter frame remains visible with its exact failure reason.
8. Final MP4 is PASS only if every required frame/audio asset is verified.
9. Resume must be idempotent: restarting the app must not duplicate completed work.
10. "100%" means verified outputs / required outputs, never requested outputs / required outputs.
