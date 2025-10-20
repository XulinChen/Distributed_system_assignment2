from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, requests

AUTH_URL = os.getenv("AUTH_URL", "http://auth:8000")
CHALLENGE_URL = os.getenv("CHALLENGE_URL", "http://challenge:8001")
SCHEDULER_URL = os.getenv("SCHEDULER_URL", "http://scheduler:8002")
EVALUATOR_URL = os.getenv("EVALUATOR_URL", "http://evaluator:8004")
LEADERBOARD_URL = os.getenv("LEADERBOARD_URL", "http://leaderboard:8005")

app = FastAPI(title="API Gateway (HTTP)")

class Register(BaseModel):
    username: str
    password: str

class Submit(BaseModel):
    token: str
    challenge_id: str
    payload: dict

class Evaluate(BaseModel):
    submission_id: str
    challenge_id: str
    pred: float

@app.post("/register")
def register(r: Register):
    return requests.post(f"{AUTH_URL}/register", json=r.model_dump()).json()

@app.post("/login")
def login(r: Register):
    return requests.post(f"{AUTH_URL}/login", json=r.model_dump()).json()

@app.post("/challenge/create")
def create_challenge(c: dict):
    return requests.post(f"{CHALLENGE_URL}/create", json=c).json()

@app.get("/challenge/list")
def list_challenges():
    return requests.get(f"{CHALLENGE_URL}/list").json()

@app.post("/submit")
def submit(s: Submit):
    # verify token (simple pass-through)
    v = requests.get(f"{AUTH_URL}/verify", params={"token": s.token})
    if v.status_code != 200:
        raise HTTPException(401, "invalid token")
    return requests.post(f"{SCHEDULER_URL}/submit", json=s.model_dump()).json()

@app.post("/evaluate")
def evaluate(e: Evaluate):
    """
    转发评估请求到 evaluator 服务。
    evaluator 接收 submission_id, challenge_id, pred (可选)
    """
    resp = requests.post(f"{EVALUATOR_URL}/evaluate", json=e.model_dump())
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Evaluator error: {resp.text}")
    return resp.json()

@app.get("/leaderboard/{challenge_id}")
def leaderboard(challenge_id: str, k: int = 10):
    return requests.get(f"{LEADERBOARD_URL}/top/{challenge_id}", params={"k": k}).json()
