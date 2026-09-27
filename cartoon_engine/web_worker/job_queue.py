from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class JobStatus(str, Enum):
    QUEUED="queued"; RUNNING="running"; VERIFIED="verified"; RETRY="retry"; FAILED="failed"; BLOCKED="blocked"

@dataclass
class FrameJob:
    frame_id: str
    prompt: str
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    worker_id: str | None = None
    output_path: str | None = None
    error: str | None = None

class RetryQueue:
    def __init__(self, max_attempts: int = 4):
        self.max_attempts=max_attempts
        self.jobs: dict[str,FrameJob]={}

    def add(self, jobs: Iterable[FrameJob]):
        for job in jobs: self.jobs[job.frame_id]=job

    def failed(self):
        return [j for j in self.jobs.values() if j.status in {JobStatus.RETRY,JobStatus.FAILED} and j.attempts < self.max_attempts]

    def mark_retry(self, frame_id: str, error: str):
        j=self.jobs[frame_id]; j.attempts += 1; j.error=error
        j.status = JobStatus.RETRY if j.attempts < self.max_attempts else JobStatus.FAILED

    def mark_verified(self, frame_id: str, output_path: str):
        j=self.jobs[frame_id]; j.status=JobStatus.VERIFIED; j.output_path=output_path; j.error=None

    def unresolved(self):
        return [j for j in self.jobs.values() if j.status != JobStatus.VERIFIED]
