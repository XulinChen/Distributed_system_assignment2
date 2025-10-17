from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(title="Challenge Service (HTTP)")

CHALLENGES = {}  # id -> info

class Challenge(BaseModel):
    title: str
    description: str
    deadline: str

@app.post("/create")
def create(c: Challenge):
    cid = str(uuid.uuid4())
    CHALLENGES[cid] = c.model_dump()
    return {"challenge_id": cid}

@app.get("/list")
def list_challenges():
    return CHALLENGES
