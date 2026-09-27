from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Worker:
    worker_id: str
    busy: bool=False
    status: str="IDLE"
    completed: int=0
    failed: int=0

@dataclass
class Orchestrator:
    worker_count: int=5
    max_attempts: int=4
    workers: list[Worker]=field(init=False)
    jobs: dict[str,dict]=field(default_factory=dict)

    def __post_init__(self):
        self.workers=[Worker(f"worker_{i}") for i in range(1,self.worker_count+1)]

    def load_manifest(self, manifest: dict):
        self.jobs={x["frame_id"]:x for x in manifest["frames"]}

    def assign(self):
        queued=[j for j in self.jobs.values() if j.get("status")=="queued"]
        for i,job in enumerate(queued):
            worker=self.workers[i % len(self.workers)]
            job["worker_id"]=worker.worker_id
            job["status"]="assigned"

    def verified_count(self):
        return sum(j.get("status")=="verified" for j in self.jobs.values())

    def unresolved(self):
        return [j for j in self.jobs.values() if j.get("status")!="verified"]

    def completion(self):
        total=len(self.jobs)
        return 0 if not total else round(self.verified_count()*100/total,2)

    def snapshot(self):
        return {"workers":[vars(w) for w in self.workers],"total":len(self.jobs),
                "verified":self.verified_count(),"unresolved":len(self.unresolved()),
                "progress":self.completion()}
