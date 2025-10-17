from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid, time, requests, os

WORKER_URL = os.getenv("WORKER_URL", "http://worker:8003")

app = FastAPI(title="Scheduler (HTTP)")

SUBMISSIONS = {}  # id -> {"user":..., "challenge_id":..., "state":..., "payload":...}

class Submission(BaseModel):
    token: str
    challenge_id: str
    payload: dict  # points to code artifact ID / params

@app.post("/submit")
def submit(s: Submission):
    sid = str(uuid.uuid4())
    SUBMISSIONS[sid] = {"user": s.token, "challenge_id": s.challenge_id, "state":"QUEUED", "payload": s.payload}
    # dispatch to worker
    try:
        r = requests.post(f"{WORKER_URL}/run", json={"submission_id": sid, "payload": s.payload, "challenge_id": s.challenge_id})
        r.raise_for_status()
        SUBMISSIONS[sid]["state"] = "RUNNING"
    except Exception as e:
        SUBMISSIONS[sid]["state"] = "FAILED_DISPATCH"
        raise HTTPException(500, f"dispatch error: {e}")
    return {"submission_id": sid, "state": SUBMISSIONS[sid]["state"]}

@app.get("/status/{sid}")
def status(sid: str):
    if sid not in SUBMISSIONS:
        raise HTTPException(404, "not found")
    return SUBMISSIONS[sid]
