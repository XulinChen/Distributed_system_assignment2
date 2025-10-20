import os, sqlite3, uuid, bcrypt, time
import grpc
from concurrent import futures

import api_pb2, api_pb2_grpc

DB_PATH = os.environ.get("DB_PATH", "/data/auth.db")
PORT = os.environ.get("PORT", "50051")

os.makedirs("/data", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash BLOB
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sessions(
        token TEXT PRIMARY KEY,
        user_id TEXT,
        created_at REAL
    );
    """)
    conn.commit()
    return conn

db = get_db()

class AuthService(api_pb2_grpc.AuthServiceServicer):
    def Register(self, request, context):
        username = request.username.strip()
        password = request.password.encode("utf-8")
        if not username or not password:
            return api_pb2.RegisterResponse(ok=False, message="empty username/password")
        user_id = str(uuid.uuid4())
        pw_hash = bcrypt.hashpw(password, bcrypt.gensalt())
        try:
            db.execute("INSERT INTO users(id, username, password_hash) VALUES(?,?,?)",
                       (user_id, username, pw_hash))
            db.commit()
        except sqlite3.IntegrityError:
            return api_pb2.RegisterResponse(ok=False, message="username already exists")
        return api_pb2.RegisterResponse(ok=True, message="registered",
                                        user=api_pb2.User(id=user_id, username=username))

    def Login(self, request, context):
        username = request.username.strip()
        password = request.password.encode("utf-8")
        cur = db.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            return api_pb2.LoginResponse(ok=False, message="user not found")
        user_id, stored_hash = row[0], row[1]
        if not bcrypt.checkpw(password, stored_hash):
            return api_pb2.LoginResponse(ok=False, message="invalid password")
        token = str(uuid.uuid4())
        db.execute("INSERT INTO sessions(token, user_id, created_at) VALUES(?,?,?)",
                   (token, user_id, time.time()))
        db.commit()
        return api_pb2.LoginResponse(ok=True, message="ok", token=token,
                                     user=api_pb2.User(id=user_id, username=username))

    def ValidateToken(self, request, context):
        token = request.token
        cur = db.execute("SELECT user_id FROM sessions WHERE token=?", (token,))
        row = cur.fetchone()
        if not row:
            return api_pb2.ValidateTokenResponse(ok=False, message="invalid token")
        user_id = row[0]
        cur = db.execute("SELECT username FROM users WHERE id=?", (user_id,))
        r2 = cur.fetchone()
        if not r2:
            return api_pb2.ValidateTokenResponse(ok=False, message="user not found")
        return api_pb2.ValidateTokenResponse(ok=True, message="ok",
                                             user=api_pb2.User(id=user_id, username=r2[0]))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    api_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    print(f"AuthService listening on {PORT}")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
