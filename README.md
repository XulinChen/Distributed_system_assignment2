# Distributed ML Challenge Platform 

This repository implements a **basic framework** for your distributed systems project with **two distinct architectures** and **two communication models**:

- **Architecture A — Layered over HTTP (FastAPI + REST)**
- **Architecture B — Microservices over gRPC (grpcio)**

Both architectures include **≥ 5 containerized nodes** (Docker) and scripts to **benchmark throughput and latency** under varying workloads. You will plug in your **challenge rules, datasets, inference/evaluation code** later.

> ⚠️ This is a teaching scaffold. It focuses on the distributed-system plumbing: service boundaries, inter-service comms, simple data flow, basic scheduler/worker pattern, consistency hook, and metrics collection.

---
## Functional Requirements (covered)

1. **User Registration & Login** (Auth service; mock token based).
2. **Challenge CRUD & Distribution** (Challenge service; served via gateway).
3. **Submission Upload & Queueing** (Gateway → Scheduler → Workers).
4. **Automated Evaluation Pipeline** (Worker produces predictions → Evaluator scores).
5. **Leaderboard with Real‑Time-ish Updates** (Leaderboard service; gateway polls/pushes).

---
## Quick Start

### Prereqs
- Docker + Docker Compose

### Run HTTP Architecture
```bash
cd arch_http_layered
docker-compose build or docker compose build  (it depends on your docker version)
docker-compose up or docker compose up (it depends on your docker version)
# Services:
# - api-gateway (FastAPI)
# - auth
# - challenge
# - scheduler
# - worker (scale >1 with: docker compose up --scale worker=3)
# - evaluator
# - leaderboard
```

In another terminal, test each Functional Requirements:
```bash
# register
curl -X POST http://localhost:8080/register \
  -H "Content-Type: application/json" \
  -d '{
        "username": "your_name",
        "password": "your_password"
      }'
```

```bash
# login
curl -X POST http://localhost:8080/login \
  -H "Content-Type: application/json" \
  -d '{
        "username": "your_name",
        "password": "your_password"
      }'
```

```bash
# create challenge
curl -X POST http://localhost:8080/challenge/create \
  -H "Content-Type: application/json" \
  -d '{
        "challenge_id": "bladder-cancer-survival",
        "title": "Bladder Cancer Survival Prediction Challenge",
        "description": "Predict recurrence likelihood of bladder cancer from histopathology and gene data.",
        "deadline": "2025-12-31",
        "created_by": "xulin"
      }'
```

```bash
# submit a demo
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
        "token": "the token of your account obtained by the login step",
        "challenge_id": "the token of the challenge obtained by the challenge create step",
        "payload": {"artifact": "demo_model_v1"}
      }'
```

```bash
# evaluate the submission
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
        "submission_id": "the token obtained by the submission step",
        "challenge_id": "the token of the challenge obtained by the challenge create step",
       "pred": 0.6   
      }'
```

```bash
# check the top ten submission results on the leaderboard, input the token of the challenge obtained by the challenge create step
curl "http://localhost:8080/leaderboard/the token of the challenge obtained by the challenge create step?k=10"
```

### Benchmark Suite for Distributed System (HTTP API Gateway + Layered Architecture)
It measures **throughput**, **latency**, and **scalability** under different concurrency levels and generates ready-to-publish plots.
In another terminal, run a tiny workload to benchmark the performance:

cd distsys-benchmark, Edit `config.yaml`, fill in the required information according to the instructions inside. 
### ⚙️ Benchmark Principle

This benchmark applies **asynchronous load simulation** to emulate multiple concurrent users.  

For each endpoint:
1. **N concurrent workers** send requests simultaneously.  
2. Each worker records **latency (ms)** and **status code**.  
3. Statistics such as **average latency**, **p95/p99 percentile**, and **throughput (req/s)** are computed.  
4. Results are stored in per-service CSV files and combined for cross-service comparison.

**Metrics:**
| Metric | Description |
|---------|-------------|
| `throughput_rps` | Successful requests per second |
| `latency_avg_ms` | Average response time |
| `latency_p95_ms` | 95th percentile latency |
| `latency_p99_ms` | 99th percentile latency |
| `ok/errors` | Success and failure counts |

### 1️⃣ Install dependencies

```bash
pip install aiohttp pandas matplotlib seaborn pyyaml
```

### 2️⃣ Run Benchmark

```bash
python benchmark.py -c config.yaml
```

This creates files in `./bench_runs/`:

```
register_summary.csv
submit_summary.csv
evaluate_summary.csv
leaderboard_summary.csv
combined_summary.csv
```

### 3️⃣ Generate Plots

```bash
python analyze.py --csv ./bench_runs/combined_summary.csv --outdir ./bench_plots
```

Outputs:

```
bench_plots/
 ├── throughput_rps.png
 ├── latency_avg_ms.png
 ├── latency_p95_ms.png
 └── latency_p99_ms.png
```

Each plot shows curves for all services (`register`, `submit`, `evaluate`, `leaderboard`).


### Run gRPC Architecture
This repo includes a distributed system exposing six functions via an HTTP API Gateway that fans out to gRPC microservices:

- **register** (AuthService)
- **login** (AuthService)
- **create challenge** (ChallengeService)
- **submit** (SubmissionService)
- **evaluate** (EvaluatorService; updates Leaderboard)
- **leaderboard** (LeaderboardService; in-memory, sorted by score desc)

## Run
cd arch_grpc_microservice
```bash
docker-compose build
docker-compose up 
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
  -d '{"token":"the token obtained by the login step","title":"Demo Challenge","description":"Deadline November 1st, 2025"}' | jq
# input the token obtained by the login step
```

### 4) Submit a model/artifact
```bash
export SUBMISSION_ID=$(curl -s -X POST http://localhost:8080/submit   -H "Content-Type: application/json"   -d '{"token":"the token obtained by the login step","challenge_id":"the token obtained by creating challenge step","artifact":"demo_model_v1"}' | jq -r '.submission.id')
echo $SUBMISSION_ID
```

### 5) Evaluate the submission (pushes to Leaderboard)
```bash
curl -s -X POST http://localhost:8080/evaluate   -H "Content-Type: application/json"   -d '{"submission_id":"the token obtained by the submission step","challenge_id":"the token obtained by creating challenge step"}' | jq
```

### 6) Get leaderboard
```bash
# input the token obtained by creating challenge step
curl -s "http://localhost:8080/leaderboard?challenge_id=default" | jq
```

### 7) List submissions (optional)
```bash
# input the token obtained by creating challenge step
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
- Evaluator calls Leaderboard.UpdateScore.
- Protobuf is compiled at Docker build time in each image.

---

# Benchmark Suite for grpc Microservices 
cd bench_suite
This suite stress-tests multiple endpoints of your microservice system:
- `/register`, `/login`, `/challenges`, `/submit`, `/evaluate`, `/leaderboard`, `/submissions`

## Files
- `bench_suite.py` — Async multi-endpoint benchmark (GET/POST, concurrency sweep, CSV outputs)
- `suite.yaml` — Config describing runs and payloads, please edit it according to the instruction inside.
- Output directory: `bench_runs/` (created automatically)

## Quick Start
```bash
# 1) Ensure docker stack is running:
# docker-compose up 

# 2) Install deps (Python 3.9+ recommended)

pip install aiohttp pyyaml

# 3) Run the suite
python bench_suite.py -c suite.yaml

# 4) Generate Plots

python plot_bench_results.py --csv ./bench_runs/combined_summary.csv --outdir ./bench_plots
```


## Design & Trade-offs

### Architecture A (HTTP, layered)
- **Communication**: HTTP/JSON
- **Pros**: Easy to debug; widely supported; human-friendly.
- **Cons**: Higher overhead vs gRPC; no strong interface contracts; serialization cost.

### Architecture B (gRPC, microservices)
- **Communication**: gRPC/Protobuf
- **Pros**: Compact binary, strong interface; streaming; faster per call.
- **Cons**: Slightly heavier tooling; schema-first dev requires .proto changes for evolution.

### Consistency & Fault Tolerance (Hooks)
- Scheduler writes a **submission record** with state transitions (`QUEUED` → `RUNNING` → `EVALUATED`) in a tiny in-process store. Swap to Redis/Postgres for real durability.
- Leaderboard updates are **atomic per submission** (single-writer in evaluator) to avoid split-brain ordering.
- Idempotent evaluator: if re-run for the same `(submission_id, challenge_id)`, it overwrites score with the latest timestamp to ensure last‑write wins.


Good luck, and have fun!
