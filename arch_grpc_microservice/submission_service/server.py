import os, sqlite3, uuid, grpc
from concurrent import futures

import api_pb2, api_pb2_grpc

AUTH_ADDR = os.environ.get("AUTH_ADDR", "auth:50051")
DB_PATH = os.environ.get("DB_PATH", "/data/submission.db")
PORT = os.environ.get("PORT", "50053")

os.makedirs("/data", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS submissions(
        id TEXT PRIMARY KEY,
        challenge_id TEXT,
        user_id TEXT,
        artifact TEXT
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

class SubmissionService(api_pb2_grpc.SubmissionServiceServicer):
    def SubmitModel(self, request, context):
        v = validate_token(request.token)
        if not v.ok:
            return api_pb2.SubmitModelResponse(ok=False, message="unauthorized")
        sid = str(uuid.uuid4())
        db.execute("INSERT INTO submissions(id, challenge_id, user_id, artifact) VALUES(?,?,?,?)",
                   (sid, request.challenge_id.strip(), v.user.id, request.artifact.strip()))
        db.commit()
        sub = api_pb2.Submission(id=sid, challenge_id=request.challenge_id.strip(),
                                 user_id=v.user.id, artifact=request.artifact.strip())
        return api_pb2.SubmitModelResponse(ok=True, message="submitted", submission=sub)

    def ListSubmissions(self, request, context):
        rows = db.execute("SELECT id, challenge_id, user_id, artifact FROM submissions WHERE challenge_id=?",
                          (request.challenge_id.strip(),)).fetchall()
        items = [api_pb2.Submission(id=r[0], challenge_id=r[1], user_id=r[2], artifact=r[3]) for r in rows]
        return api_pb2.ListSubmissionsResponse(items=items)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    api_pb2_grpc.add_SubmissionServiceServicer_to_server(SubmissionService(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    print(f"SubmissionService listening on {PORT}")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
