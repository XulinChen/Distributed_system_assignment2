# Merged ML Challenge Platform (6 services)

This repo merges two attachments into a single distributed system exposing six functions via an HTTP API Gateway that fans out to gRPC microservices:

- **register** (AuthService)
- **login** (AuthService)
- **create challenge** (ChallengeService)
- **submit** (SubmissionService)
- **evaluate** (EvaluatorService; random score + updates Leaderboard)
- **leaderboard** (LeaderboardService; in-memory, sorted by score desc)

## Run

```bash
docker compose build
docker compose up -d
# wait until all services print their start messages
```

HTTP gateway is at **http://localhost:8080**.

## Quick cURL tests

### 1) Register
```bash
curl -s -X POST http://localhost:8080/register   -H "Content-Type: application/json"   -d '{"username":"alice","password":"pw"}' | jq
```

### 2) Login (get token)
```bash
export TOKEN=$(curl -s -X POST http://localhost:8080/login   -H "Content-Type: application/json"   -d '{"username":"alice","password":"pw"}' | jq -r '.token')
echo $TOKEN
```

### 3) Create a challenge
```bash
curl -s -X POST http://localhost:8080/challenges \
  -H "Content-Type: application/json" \
  -d '{"token":"82b6e1a1-604d-4fc1-a9e6-6b755e61de15","title":"Demo Challenge","description":"Deadline November 1st, 2025"}' | jq
# assume the challenge_id is "default" if not specified by service
```

### 4) Submit a model/artifact
```bash
export SUBMISSION_ID=$(curl -s -X POST http://localhost:8080/submit   -H "Content-Type: application/json"   -d '{"token":"'"$TOKEN"'","challenge_id":"default","artifact":"demo_model_v1"}' | jq -r '.submission.id')
echo $SUBMISSION_ID
```

### 5) Evaluate the submission (random score; pushes to Leaderboard)
```bash
curl -s -X POST http://localhost:8080/evaluate   -H "Content-Type: application/json"   -d '{"submission_id":"'"$SUBMISSION_ID"'","challenge_id":"default"}' | jq
```

### 6) Get leaderboard
```bash
curl -s "http://localhost:8080/leaderboard?challenge_id=default" | jq
```

### 7) List submissions (optional)
```bash
curl -s "http://localhost:8080/submissions?challenge_id=default" | jq
```

### 8) List all the challenges (optional)
```bash
curl -s http://localhost:8080/challenges | jq
```

## Notes

- **Ports preserved** from original services:
  - Auth: `50051`
  - Challenge: `50052`
  - Submission: `50053`
  - Evaluator: `50054`
  - Leaderboard: `50055`
  - API Gateway (HTTP): `8080`
- Leaderboard stores data **in-memory** (ephemeral).
- Evaluator generates a **random score** and calls Leaderboard.UpdateScore.
- Protobuf is compiled at Docker build time in each image.
