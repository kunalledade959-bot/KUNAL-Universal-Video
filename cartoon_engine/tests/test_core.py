import json, tempfile
from pathlib import Path
from cartoon_engine.story_to_manifest import compile_manifest
from cartoon_engine.web_worker.job_queue import RetryQueue, FrameJob, JobStatus

story={"project":{"fps":24,"duration_seconds":1},"characters":[{"id":"raju","type":"human"}],"scenes":[{"id":"s1","start":1,"end":24}]}
m=compile_manifest(story)
assert m["expected_frames"] == 24
assert len(m["frames"]) == 24
assert m["frames"][0]["frame_id"] == "frame_000001"
assert m["frames"][-1]["frame_id"] == "frame_000024"

q=RetryQueue(max_attempts=4)
q.add([FrameJob("frame_000001","test")])
q.mark_retry("frame_000001","temporary")
assert q.jobs["frame_000001"].attempts == 1
assert q.jobs["frame_000001"].status == JobStatus.RETRY
q.mark_verified("frame_000001","/tmp/frame_000001.png")
assert not q.unresolved()
print("PASS: manifest + retry queue")
