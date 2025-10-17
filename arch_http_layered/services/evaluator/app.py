from fastapi import FastAPI
from pydantic import BaseModel
import random, time, requests, os

LEADERBOARD_URL = os.getenv("LEADERBOARD_URL", "http://leaderboard:8005")

app = FastAPI(title="Evaluator (HTTP)")

class EvalReq(BaseModel):
    submission_id: str
    challenge_id: str
    pred: list

@app.post("/evaluate")
def evaluate(e: EvalReq):
    # Simulate metric computation
    time.sleep(0.02)
    score = sum(e.pred) / max(len(e.pred), 1)
    # Update leaderboard
    requests.post(f"{LEADERBOARD_URL}/update", json={"challenge_id": e.challenge_id, "submission_id": e.submission_id, "score": score})
    return {"score": score}
