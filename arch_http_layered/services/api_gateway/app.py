from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, requests

AUTH_URL = os.getenv("AUTH_URL", "http://auth:8000")
CHALLENGE_URL = os.getenv("CHALLENGE_URL", "http://challenge:8001")
SCHEDULER_URL = os.getenv("SCHEDULER_URL", "http://scheduler:8002")
LEADERBOARD_URL = os.getenv("LEADERBOARD_URL", "http://leaderboard:8005")

app = FastAPI(title="API Gateway (HTTP)")

class Register(BaseModel):
    username: str
    password: str

class Submit(BaseModel):
    token: str
    challenge_id: str
    payload: dict

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

@app.get("/leaderboard/{challenge_id}")
def leaderboard(challenge_id: str, k: int = 10):
    return requests.get(f"{LEADERBOARD_URL}/top/{challenge_id}", params={"k": k}).json()
