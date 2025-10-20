import os, sqlite3, uuid
import grpc
from concurrent import futures

import api_pb2, api_pb2_grpc

AUTH_ADDR = os.environ.get("AUTH_ADDR", "auth:50051")
DB_PATH = os.environ.get("DB_PATH", "/data/challenge.db")
PORT = os.environ.get("PORT", "50052")

os.makedirs("/data", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS challenges(
        id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        owner_user_id TEXT
    );
    """)
    conn.commit()
    return conn

db = get_db()

def validate_token(token: str):
    with grpc.insecure_channel(AUTH_ADDR) as ch:
        stub = api_pb2_grpc.AuthServiceStub(ch)
        resp = stub.ValidateToken(api_pb2.ValidateTokenRequest(token=token))
        return resp

class ChallengeService(api_pb2_grpc.ChallengeServiceServicer):
    def CreateChallenge(self, request, context):
        v = validate_token(request.token)
        if not v.ok:
            return api_pb2.CreateChallengeResponse(ok=False, message="unauthorized")
        cid = str(uuid.uuid4())
        db.execute("INSERT INTO challenges(id, title, description, owner_user_id) VALUES(?,?,?,?)",
                   (cid, request.title.strip(), request.description.strip(), v.user.id))
        db.commit()
        ch = api_pb2.Challenge(id=cid, title=request.title.strip(),
                               description=request.description.strip(),
                               owner_user_id=v.user.id)
        return api_pb2.CreateChallengeResponse(ok=True, message="created", challenge=ch)

    def ListChallenges(self, request, context):
        rows = db.execute("SELECT id, title, description, owner_user_id FROM challenges").fetchall()
        items = [api_pb2.Challenge(id=r[0], title=r[1], description=r[2], owner_user_id=r[3]) for r in rows]
        return api_pb2.ListChallengesResponse(items=items)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    api_pb2_grpc.add_ChallengeServiceServicer_to_server(ChallengeService(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    print(f"ChallengeService listening on {PORT}")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
