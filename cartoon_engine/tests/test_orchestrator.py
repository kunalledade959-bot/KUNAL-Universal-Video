from cartoon_engine.orchestrator import Orchestrator

def test_five_workers_and_progress():
    o=Orchestrator()
    o.load_manifest({"frames":[{"frame_id":f"frame_{i:06d}","status":"queued"} for i in range(1,26)]})
    o.assign()
    assert len(o.workers)==5
    assert all(j["status"]=="assigned" for j in o.jobs.values())
    assert o.completion()==0
