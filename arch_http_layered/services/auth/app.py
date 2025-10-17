from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI(title="Auth Service (HTTP)")

USERS = {}  # username -> {"password":..., "id":...}
TOKENS = {}  # token -> username

class RegisterReq(BaseModel):
    username: str
    password: str

class LoginReq(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(r: RegisterReq):
    if r.username in USERS:
        raise HTTPException(400, "user exists")
    USERS[r.username] = {"password": r.password, "id": str(uuid.uuid4())}
    return {"status": "ok"}

@app.post("/login")
def login(r: LoginReq):
    u = USERS.get(r.username)
    if not u or u["password"] != r.password:
        raise HTTPException(401, "bad creds")
    token = str(uuid.uuid4())
    TOKENS[token] = r.username
    return {"token": token}

@app.get("/verify")
def verify(token: str):
    if token not in TOKENS:
        raise HTTPException(401, "invalid token")
    return {"username": TOKENS[token]}
