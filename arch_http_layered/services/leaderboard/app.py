from fastapi import FastAPI
from pydantic import BaseModel
from heapq import nlargest

app = FastAPI(title="Leaderboard (HTTP)")

LB = {}  # challenge_id -> {submission_id: score}

class Update(BaseModel):
    challenge_id: str
    submission_id: str
    score: float

@app.post("/update")
def update(u: Update):
    LB.setdefault(u.challenge_id, {})[u.submission_id] = u.score
    return {"status": "ok"}

@app.get("/top/{challenge_id}")
def top(challenge_id: str, k: int = 10):
    items = LB.get(challenge_id, {}).items()
    topk = nlargest(k, items, key=lambda kv: kv[1])
    return [{"submission_id": s, "score": sc} for s, sc in topk]
