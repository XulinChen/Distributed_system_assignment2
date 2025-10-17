# Distributed System Benchmark Bundle

This bundle load-tests your API gateway at `http://localhost:8080/submit`, summarizes metrics, plots figures, and generates an English evaluation report that matches your assignment requirements.

## Prereqs
- Python 3.9+
- `pip install aiohttp pyyaml matplotlib numpy`
- Your distributed system is up locally (gateway reachable at `http://localhost:8080/submit`).

## Quick Start
1. Edit `config.yaml` if needed (token, challenge_id, payload, concurrency levels).
2. Run the benchmark:
   ```bash
   python3 benchmark.py -c config.yaml
   ```
   This creates `./runs/<run_label>_raw.csv` and `./runs/<run_label>_summary.csv`.
3. Analyze and plot:
   ```bash
   python3 analyze.py --summary ./runs/baseline_summary.csv --outdir ./runs --run_label baseline
   ```
   This writes:
   - `./runs/baseline_throughput.png`
   - `./runs/baseline_p95_latency.png`
   - `./runs/baseline_error_rate.png`
   - `./runs/baseline_summary_clean.csv`
4. Generate the report markdown:
   ```bash
   python3 generate_report.py -c config.yaml -s ./runs/baseline_summary_clean.csv      --hardware_env "Fill in your CPUs/GPUs/RAM/NICs"      --software_env "Fill in OS, Docker version, image tags"      --num_nodes "e.g., gateway=1, worker=4, DB=1"
   ```
   Output: `./runs/baseline_report.md`

## Scaling Experiments (Optional)
Repeat the steps above after changing the number of service replicas (e.g., via your `docker compose` or orchestrator). For each replica setting, set a new `run_label` in `config.yaml` (e.g., `1x`, `2x`, `4x`) and re-run the three steps. Compare the plots and CSV summaries across runs.

### Example `docker compose` scaling (if your stack supports it)
```bash
# Scale a worker service to 4 replicas (service name may differ in your compose file)
docker compose up -d --scale worker=4
```

## What the Scripts Measure
- **Throughput (req/s)** – successful requests / elapsed wall time.
- **Latency percentiles (p50, p95, p99)** – end-to-end request time as observed by the client.
- **Error rate** – percentage of requests that failed or timed out.

## Report Contents
The generated report includes:
1. Experimental setup (hardware, node counts, workload specs).
2. Figures for throughput, latency, and error rate vs concurrency.
3. A trade-off analysis section with prompts you can fill in based on your architecture.
4. Conclusions and recommendations.

## Tips
- Start with small concurrency to avoid overwhelming a single-node setup.
- If timeouts occur, decrease `timeout_seconds` or reduce concurrency; or improve server resources.
- Keep raw CSVs for auditing; include them in your submission if allowed.
