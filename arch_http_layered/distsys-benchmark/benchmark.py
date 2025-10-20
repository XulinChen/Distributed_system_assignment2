
#!/usr/bin/env python3
"""
Enhanced benchmark.py
Now supports multi-service benchmarking (HTTP + Layered architecture)
Compatible with config.yaml that defines multiple runs (register, submit, evaluate, leaderboard)
Generates:
  - Individual raw CSVs per service
  - Summary CSVs per service
  - Combined summary CSV for all services
"""

import asyncio
import aiohttp
import time
import yaml
import csv
import os
import sys
import uuid
from statistics import mean


# ------------------------------------------------------------
# Helper functions
def percentile(values, p):
    if not values:
        return float("nan")
    arr = sorted(values)
    k = (len(arr) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(arr) - 1)
    if f == c:
        return arr[f]
    return arr[f] + (arr[c] - arr[f]) * (k - f)


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------
async def one_request(session, url, json_body, timeout_s, method="POST"):
    t0 = time.perf_counter()
    try:
        if method.upper() == "GET":
            async with session.get(url, timeout=timeout_s) as resp:
                _ = await resp.text()
                t1 = time.perf_counter()
                return {
                    "ok": (200 <= resp.status < 300),
                    "status": resp.status,
                    "latency_ms": (t1 - t0) * 1000.0,
                }
        else:
            async with session.post(url, json=json_body, timeout=timeout_s) as resp:
                _ = await resp.text()
                t1 = time.perf_counter()
                return {
                    "ok": (200 <= resp.status < 300),
                    "status": resp.status,
                    "latency_ms": (t1 - t0) * 1000.0,
                }
    except Exception as e:
        t1 = time.perf_counter()
        return {"ok": False, "status": -1, "latency_ms": (t1 - t0) * 1000.0, "error": str(e)}


async def run_level(session, url, json_body, timeout_s, concurrency, total_requests, writer, run_label, method):
    latencies = []
    ok_count = 0
    sem = asyncio.Semaphore(concurrency)
    t_start = time.perf_counter()

    async def worker(req_id):
        nonlocal ok_count
        async with sem:
            res = await one_request(session, url, json_body, timeout_s, method)
            latencies.append(res["latency_ms"])
            if res["ok"]:
                ok_count += 1
            writer.writerow({
                "run_label": run_label,
                "concurrency": concurrency,
                "req_id": req_id,
                "ok": int(res["ok"]),
                "status": res["status"],
                "latency_ms": f"{res['latency_ms']:.3f}"
            })

    tasks = [asyncio.create_task(worker(str(uuid.uuid4()))) for _ in range(total_requests)]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - t_start
    throughput = ok_count / elapsed if elapsed > 0 else 0.0

    return {
        "concurrency": concurrency,
        "requests": total_requests,
        "ok": ok_count,
        "errors": total_requests - ok_count,
        "elapsed_s": elapsed,
        "throughput_rps": throughput,
        "latency_avg_ms": mean(latencies) if latencies else float("nan"),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "latency_p99_ms": percentile(latencies, 99),
    }


# ------------------------------------------------------------
async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    outdir = cfg.get("output_dir", "./bench_runs")
    os.makedirs(outdir, exist_ok=True)
    timeout_s = float(cfg.get("timeout_seconds", 30.0))

    async with aiohttp.ClientSession() as session:
        all_rows = []

        for run in cfg["runs"]:
            name = run["name"]
            url = run["url"]
            body = run.get("json_body", {})
            conc_levels = run.get("concurrency_levels", [1, 2, 4, 8])
            per_level = int(run.get("requests_per_level", 100))

            # 允许自动识别 GET 请求（如 leaderboard）
            method = "GET" if url.strip().startswith("http") and "?" in url else "POST"

            print(f"[run:{name}] -> {url} ({method})")

            raw_path = os.path.join(outdir, f"{name}_raw.csv")
            summary_path = os.path.join(outdir, f"{name}_summary.csv")

            with open(raw_path, "w", newline="") as fraw:
                writer = csv.DictWriter(fraw, fieldnames=["run_label", "concurrency", "req_id", "ok", "status", "latency_ms"])
                writer.writeheader()
                summaries = []

                for c in conc_levels:
                    print(f"  [concurrency={c}] running {per_level} requests ...")
                    s = await run_level(session, url, body, timeout_s, c, per_level, writer, name, method)
                    s["run_label"] = name
                    summaries.append(s)
                    print(f"    ✅ throughput={s['throughput_rps']:.2f} rps, p95={s['latency_p95_ms']:.1f} ms")

            # 写入单个 service summary
            with open(summary_path, "w", newline="") as fs:
                w = csv.DictWriter(fs, fieldnames=[
                    "run_label", "concurrency", "requests", "ok", "errors",
                    "elapsed_s", "throughput_rps", "latency_avg_ms",
                    "latency_p50_ms", "latency_p95_ms", "latency_p99_ms"
                ])
                w.writeheader()
                for s in summaries:
                    w.writerow(s)

            all_rows.extend(summaries)

        # 合并写入总汇
        combined_path = os.path.join(outdir, "combined_summary.csv")
        with open(combined_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "run_label", "concurrency", "requests", "ok", "errors",
                "elapsed_s", "throughput_rps", "latency_avg_ms",
                "latency_p50_ms", "latency_p95_ms", "latency_p99_ms"
            ])
            w.writeheader()
            for s in all_rows:
                w.writerow(s)
        print(f"\n✅ [saved] combined_summary.csv -> {combined_path}")


# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(1)
