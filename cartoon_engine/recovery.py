"""Fail-closed recovery state machine for Story-to-Video jobs.

This module is backend-agnostic. Browser/Blender/FFmpeg adapters call it after
each observable event. It deliberately never treats an attempted operation as
success until a validator reports success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Dict, Optional


class FrameState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    RETRY = "retry"
    BLOCKED = "blocked"
    DEAD = "dead"


@dataclass
class FrameRecord:
    frame_id: int
    state: FrameState = FrameState.QUEUED
    attempts: int = 0
    last_error: Optional[str] = None
    worker_id: Optional[str] = None
    output_path: Optional[str] = None
    checksum: Optional[str] = None
    updated_at: float = field(default_factory=time)


class RecoveryController:
    """Bounded, idempotent frame recovery with fail-closed semantics."""

    def __init__(self, frame_ids, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.frames: Dict[int, FrameRecord] = {
            int(fid): FrameRecord(int(fid)) for fid in frame_ids
        }

    def claim(self, frame_id: int, worker_id: str) -> FrameRecord:
        rec = self.frames[int(frame_id)]
        if rec.state == FrameState.VERIFIED:
            return rec
        if rec.state in (FrameState.BLOCKED, FrameState.DEAD):
            raise RuntimeError(f"frame {frame_id} is terminal: {rec.state.value}")
        rec.state = FrameState.RUNNING
        rec.worker_id = worker_id
        rec.attempts += 1
        rec.updated_at = time()
        return rec

    def verify(self, frame_id: int, ok: bool, output_path=None, checksum=None, reason=None):
        rec = self.frames[int(frame_id)]
        if ok:
            rec.state = FrameState.VERIFIED
            rec.output_path = output_path
            rec.checksum = checksum
            rec.last_error = None
        else:
            rec.last_error = reason or "validation_failed"
            if rec.attempts >= self.max_attempts:
                rec.state = FrameState.DEAD
            else:
                rec.state = FrameState.RETRY
        rec.updated_at = time()
        return rec

    def block(self, frame_id: int, reason: str):
        rec = self.frames[int(frame_id)]
        if rec.state != FrameState.VERIFIED:
            rec.state = FrameState.BLOCKED
            rec.last_error = reason
            rec.updated_at = time()
        return rec

    def retry_ids(self):
        return [fid for fid, rec in self.frames.items() if rec.state == FrameState.RETRY]

    def unresolved_ids(self):
        return [fid for fid, rec in self.frames.items()
                if rec.state != FrameState.VERIFIED]

    def progress(self):
        total = len(self.frames)
        verified = sum(r.state == FrameState.VERIFIED for r in self.frames.values())
        return {
            "verified": verified,
            "total": total,
            "percent": (verified / total * 100.0) if total else 100.0,
            "unresolved": self.unresolved_ids(),
        }

    def snapshot(self):
        return {
            "max_attempts": self.max_attempts,
            "frames": {
                str(fid): {
                    "state": rec.state.value,
                    "attempts": rec.attempts,
                    "last_error": rec.last_error,
                    "worker_id": rec.worker_id,
                    "output_path": rec.output_path,
                    "checksum": rec.checksum,
                    "updated_at": rec.updated_at,
                }
                for fid, rec in self.frames.items()
            },
        }
