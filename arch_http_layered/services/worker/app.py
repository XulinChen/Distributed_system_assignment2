from fastapi import FastAPI
from pydantic import BaseModel
import time, requests, os, random

EVALUATOR_URL = os.getenv("EVALUATOR_URL", "http://evaluator:8004")

app = FastAPI(title="Worker (HTTP)")

class RunReq(BaseModel):
    submission_id: str
    payload: dict
    challenge_id: str

@app.post("/run")
def run(r: RunReq):
    # Simulate inference time
    time.sleep(0.05 + random.random() * 0.05)
    # Produce mock predictions
    yhat = [random.random() for _ in range(100)]
    # Send for evaluation
    requests.post(f"{EVALUATOR_URL}/evaluate", json={"submission_id": r.submission_id, "challenge_id": r.challenge_id, "pred": yhat})
    return {"ok": True}
