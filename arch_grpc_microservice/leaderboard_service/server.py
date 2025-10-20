import grpc
from concurrent import futures
import api_pb2, api_pb2_grpc

data = {}

class LeaderboardService(api_pb2_grpc.LeaderboardServiceServicer):
    def UpdateScore(self, request, context):
        cid = request.challenge_id or "default"
        data.setdefault(cid, [])
        # remove old
        data[cid] = [e for e in data[cid] if e.submission_id != request.submission_id]
        entry = api_pb2.LeaderboardEntry(submission_id=request.submission_id, score=request.score)
        data[cid].append(entry)
        data[cid].sort(key=lambda e: e.score, reverse=True)
        return api_pb2.UpdateScoreResponse(ok=True, message="updated")

    def GetLeaderboard(self, request, context):
        cid = request.challenge_id or "default"
        return api_pb2.GetLeaderboardResponse(entries=data.get(cid, []))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    api_pb2_grpc.add_LeaderboardServiceServicer_to_server(LeaderboardService(), server)
    server.add_insecure_port("[::]:50055")
    print("LeaderboardService on 50055")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
