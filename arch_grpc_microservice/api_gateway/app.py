from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import grpc, os

import api_pb2, api_pb2_grpc

AUTH_ADDR = os.environ.get("AUTH_ADDR", "auth:50051")
CHALLENGE_ADDR = os.environ.get("CHALLENGE_ADDR", "challenge:50052")
SUBMISSION_ADDR = os.environ.get("SUBMISSION_ADDR", "submission:50053")

app = FastAPI(title="HTTP API Gateway (to gRPC microservices)")

# --------- Schemas ----------
class RegisterIn(BaseModel):
    username: str
    password: str

class LoginIn(BaseModel):
    username: str
    password: str

class CreateChallengeIn(BaseModel):
    token: str
    title: str
    description: str = ""

class SubmitIn(BaseModel):
    token: str
    challenge_id: str
    artifact: str

# --------- Helpers ----------
def auth_stub():
    ch = grpc.insecure_channel(AUTH_ADDR)
    return api_pb2_grpc.AuthServiceStub(ch), ch

def challenge_stub():
    ch = grpc.insecure_channel(CHALLENGE_ADDR)
    return api_pb2_grpc.ChallengeServiceStub(ch), ch

def submission_stub():
    ch = grpc.insecure_channel(SUBMISSION_ADDR)
    return api_pb2_grpc.SubmissionServiceStub(ch), ch

# --------- Routes -----------
@app.post("/register")
def register(payload: RegisterIn):
    stub, ch = auth_stub()
    try:
        resp = stub.Register(api_pb2.RegisterRequest(username=payload.username, password=payload.password))
        if not resp.ok:
            raise HTTPException(status_code=400, detail=resp.message)
        return {"ok": True, "user": {"id": resp.user.id, "username": resp.user.username}}
    finally:
        ch.close()

@app.post("/login")
def login(payload: LoginIn):
    stub, ch = auth_stub()
    try:
        resp = stub.Login(api_pb2.LoginRequest(username=payload.username, password=payload.password))
        if not resp.ok:
            raise HTTPException(status_code=401, detail=resp.message)
        return {"ok": True, "token": resp.token, "user": {"id": resp.user.id, "username": resp.user.username}}
    finally:
        ch.close()

@app.post("/challenges")
def create_challenge(payload: CreateChallengeIn):
    stub, ch = challenge_stub()
    try:
        resp = stub.CreateChallenge(api_pb2.CreateChallengeRequest(token=payload.token, title=payload.title, description=payload.description))
        if not resp.ok:
            raise HTTPException(status_code=401, detail=resp.message)
        c = resp.challenge
        return {"ok": True, "challenge": {"id": c.id, "title": c.title, "description": c.description, "owner_user_id": c.owner_user_id}}
    finally:
        ch.close()

@app.get("/challenges")
def list_challenges():
    stub, ch = challenge_stub()
    try:
        resp = stub.ListChallenges(api_pb2.ListChallengesRequest())
        return {"items": [{"id": c.id, "title": c.title, "description": c.description, "owner_user_id": c.owner_user_id} for c in resp.items]}
    finally:
        ch.close()

@app.post("/submit")
def submit(payload: SubmitIn):
    stub, ch = submission_stub()
    try:
        resp = stub.SubmitModel(api_pb2.SubmitModelRequest(token=payload.token, challenge_id=payload.challenge_id, artifact=payload.artifact))
        if not resp.ok:
            raise HTTPException(status_code=401, detail=resp.message)
        s = resp.submission
        return {"ok": True, "submission": {"id": s.id, "challenge_id": s.challenge_id, "user_id": s.user_id, "artifact": s.artifact}}
    finally:
        ch.close()

@app.get("/submissions")
def list_submissions(challenge_id: str):
    stub, ch = submission_stub()
    try:
        resp = stub.ListSubmissions(api_pb2.ListSubmissionsRequest(challenge_id=challenge_id))
        return {"items": [{"id": s.id, "challenge_id": s.challenge_id, "user_id": s.user_id, "artifact": s.artifact} for s in resp.items]}
    finally:
        ch.close()


# ---- NEW: evaluator & leaderboard wiring ----
EVALUATOR_ADDR = os.environ.get("EVALUATOR_ADDR", "evaluator:50054")
LEADERBOARD_ADDR = os.environ.get("LEADERBOARD_ADDR", "leaderboard:50055")

def evaluator_stub():
    ch = grpc.insecure_channel(EVALUATOR_ADDR)
    stub = api_pb2_grpc.EvaluatorServiceStub(ch)
    return stub, ch

def leaderboard_stub():
    ch = grpc.insecure_channel(LEADERBOARD_ADDR)
    stub = api_pb2_grpc.LeaderboardServiceStub(ch)
    return stub, ch

class EvaluateIn(BaseModel):
    submission_id: str
    challenge_id: str | None = None

@app.post("/evaluate")
def evaluate(inp: EvaluateIn):
    stub, ch = evaluator_stub()
    try:
        req = api_pb2.EvaluateRequest(submission_id=inp.submission_id, challenge_id=inp.challenge_id or "default")
        resp = stub.Evaluate(req)
        if not resp.ok:
            raise HTTPException(status_code=400, detail=resp.message)
        return {"ok": True, "submission_id": resp.submission_id, "score": resp.score}
    finally:
        ch.close()

@app.get("/leaderboard")
def get_leaderboard(challenge_id: str = "default"):
    stub, ch = leaderboard_stub()
    try:
        resp = stub.GetLeaderboard(api_pb2.GetLeaderboardRequest(challenge_id=challenge_id))
        items = [{"submission_id": e.submission_id, "score": e.score} for e in resp.entries]
        return {"challenge_id": challenge_id, "entries": items}
    finally:
        ch.close()
