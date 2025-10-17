# Distributed ML Challenge Platform 

This repository implements a **basic framework** for your distributed systems project with **two distinct architectures** and **two communication models**:

- **Architecture A — Layered over HTTP (FastAPI + REST)**
- **Architecture B — Microservices over gRPC (grpcio)**

Both architectures include **≥ 5 containerized nodes** (Docker) and scripts to **benchmark throughput and latency** under varying workloads. You will plug in your **challenge rules, datasets, inference/evaluation code** later.

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
curl -X POST http://localhost:8080/register \
  -H "Content-Type: application/json" \
  -d '{
        "username": "your_name",
        "password": "your_password"
      }'
```

```bash
curl -X POST http://localhost:8080/login \
  -H "Content-Type: application/json" \
  -d '{
        "username": "your_name",
        "password": "your_password"
      }'
```

```bash
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
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
        "token": "the token of your account obtained by the login step",
        "challenge_id": "the token of the challenge obtained by the create step",
        "payload": {"artifact": "demo_model_v1"}
      }'
```

In another terminal, run a tiny workload to benchmark the performance:
## Quick Start
1. cd distsys-benchmark, Edit `config.yaml`, fill in the token and challenge_id obtained from the login step and create step above. 
2. Run the benchmark:
   ```bash
   python benchmark.py -c config.yaml
   ```
   This creates `./runs/<run_label>_raw.csv` and `./runs/<run_label>_summary.csv`.
3. Analyze and plot:
   ```bash
   python analyze.py --summary ./runs/baseline_summary.csv --outdir ./runs --run_label baseline
   ```
   This writes:
   - `./runs/baseline_throughput.png`
   - `./runs/baseline_p95_latency.png`
   - `./runs/baseline_error_rate.png`
   - `./runs/baseline_summary_clean.csv`

## What the Scripts Measure
- **Throughput (req/s)** – successful requests / elapsed wall time.
- **Latency percentiles (p50, p95, p99)** – end-to-end request time as observed by the client.
- **Error rate** – percentage of requests that failed or timed out.

### Run gRPC Architecture
```bash
cd arch_grpc_microservice
# Generate code (done in Dockerfile too, but you can do locally):
python -m grpc_tools.protoc -I proto --python_out=services --grpc_python_out=services proto/platform.proto
docker compose up --build
```

Benchmark:
```bash
python bench/bench_grpc.py --rps 20 --seconds 10
```

### Scale Nodes
Both architectures support scaling the **worker** service:
```bash
docker compose up --scale worker=5
```

---

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
