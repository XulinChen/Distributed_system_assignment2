import grpc, random
from concurrent import futures
import api_pb2, api_pb2_grpc

SUBMISSION_ADDR = "submission:50053"
LEADERBOARD_ADDR = "leaderboard:50055"

class EvaluatorService(api_pb2_grpc.EvaluatorServiceServicer):
    def Evaluate(self, request, context):
        sid = request.submission_id
        score = round(random.uniform(0, 1), 4)
        # In a real system we'd query SubmissionService for challenge_id
        # For simplicity, assume challenge_id is unknown
        with grpc.insecure_channel(LEADERBOARD_ADDR) as ch:
            stub = api_pb2_grpc.LeaderboardServiceStub(ch)
            stub.UpdateScore(api_pb2.UpdateScoreRequest(submission_id=sid, score=score, challenge_id="default"))
        return api_pb2.EvaluateResponse(ok=True, message="evaluated", submission_id=sid, score=score)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    api_pb2_grpc.add_EvaluatorServiceServicer_to_server(EvaluatorService(), server)
    server.add_insecure_port("[::]:50054")
    print("EvaluatorService on 50054")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
