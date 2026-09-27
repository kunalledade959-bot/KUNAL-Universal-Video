from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class BackendLimits:
    max_batch_size: int
    max_concurrency: int
    login_required: bool = False
    automation_allowed: bool | None = None

class BackendBlocked(RuntimeError): pass

class BackendAdapter(Protocol):
    def health_check(self) -> BackendLimits: ...
    def submit(self, frame_jobs: list[dict]) -> str: ...
    def poll(self, remote_job_id: str) -> str: ...
    def collect(self, remote_job_id: str) -> list[dict]: ...
    def close(self) -> None: ...

# Browser adapters must stop rather than bypass CAPTCHA/authentication,
# rate limits, paywalls, or site automation restrictions.
