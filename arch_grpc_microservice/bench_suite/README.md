# Benchmark Suite for ML Microservices (HTTP API Gateway)

This suite stress-tests multiple endpoints of your merged microservice system:
- `/register`, `/login`, `/challenges`, `/submit`, `/evaluate`, `/leaderboard`, `/submissions`

## Files
- `bench_suite.py` — Async multi-endpoint benchmark (GET/POST, concurrency sweep, CSV outputs)
- `suite.yaml` — Config describing runs and payloads
- Output directory: `bench_runs/` (created automatically)

## Quick Start
```bash
# 1) Ensure docker stack is running:
# docker compose up -d

# 2) Install deps (Python 3.9+ recommended)
pip install aiohttp pyyaml

# 3) Run the suite
python bench_suite.py -c suite.yaml
```
