#!/usr/bin/env python3
import asyncio, aiohttp, time, json, argparse, os, sys, uuid, yaml, csv
from statistics import mean

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

async def one_request(session, url, json_body, timeout_s):
    t0 = time.perf_counter()
    try:
        async with session.post(url, json=json_body, timeout=timeout_s) as resp:
            text = await resp.text()
            t1 = time.perf_counter()
            ok = (200 <= resp.status < 300)
            return {
                "ok": ok,
                "status": resp.status,
                "latency_ms": (t1 - t0) * 1000.0,
                "resp_len": len(text),
            }
    except Exception as e:
        t1 = time.perf_counter()
        return {
            "ok": False,
            "status": -1,
            "latency_ms": (t1 - t0) * 1000.0,
            "resp_len": 0,
            "error": repr(e),
        }

async def run_level(session, url, json_body, timeout_s, concurrency, total_requests, writer, run_label):
    in_flight = 0
    completed = 0
    latencies = []
    ok_count = 0
    start_wall = time.perf_counter()

    sem = asyncio.Semaphore(concurrency)

    async def worker(req_id):
        nonlocal ok_count, completed
        async with sem:
            res = await one_request(session, url, json_body, timeout_s)
            completed += 1
            if res["ok"]:
                ok_count += 1
            latencies.append(res["latency_ms"])
            writer.writerow({
                "run_label": run_label,
                "concurrency": concurrency,
                "req_id": req_id,
                "ok": int(res["ok"]),
                "status": res["status"],
                "latency_ms": f'{res["latency_ms"]:.3f}',
                "resp_len": res["resp_len"]
            })

    tasks = []
    for i in range(total_requests):
        req_uuid = str(uuid.uuid4())
        tasks.append(asyncio.create_task(worker(req_uuid)))
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start_wall
    throughput = ok_count / elapsed if elapsed > 0 else 0.0
    p50 = percentile(latencies, 50.0)
    p95 = percentile(latencies, 95.0)
    p99 = percentile(latencies, 99.0)

    return {
        "concurrency": concurrency,
        "requests": total_requests,
        "ok": ok_count,
        "errors": total_requests - ok_count,
        "elapsed_s": elapsed,
        "throughput_rps": throughput,
        "latency_avg_ms": mean(latencies) if latencies else float("nan"),
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99
    }

def percentile(values, p):
    if not values:
        return float("nan")
    arr = sorted(values)
    k = (len(arr)-1) * (p/100.0)
    f = int(k)
    c = min(f+1, len(arr)-1)
    if f == c:
        return arr[f]
    return arr[f] + (arr[c]-arr[f]) * (k - f)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    url = cfg["target_url"]

    json_body = {
        "token": cfg.get("token", ""),
        "challenge_id": cfg.get("challenge_id", ""),
        "payload": cfg.get("payload", {})
    }
    headers = cfg.get("headers", {})
    warmup = int(cfg.get("warmup_requests", 0))
    per_level = int(cfg.get("requests_per_level", 100))
    conc_levels = list(cfg.get("concurrency_levels", [1,2,4,8]))
    timeout_s = float(cfg.get("timeout_seconds", 30))
    run_label = str(cfg.get("run_label", "baseline"))
    outdir = cfg.get("output_dir", "./runs")

    os.makedirs(outdir, exist_ok=True)
    raw_path = os.path.join(outdir, f"{run_label}_raw.csv")
    summary_path = os.path.join(outdir, f"{run_label}_summary.csv")

    async with aiohttp.ClientSession(headers=headers) as session:
        # Warmup
        if warmup > 0:
            print(f"[warmup] sending {warmup} requests at max concurrency {max(conc_levels)} ...")
            tasks = [one_request(session, url, json_body, timeout_s) for _ in range(warmup)]
            await asyncio.gather(*tasks)

        with open(raw_path, "w", newline="") as fraw:
            writer = csv.DictWriter(fraw, fieldnames=["run_label","concurrency","req_id","ok","status","latency_ms","resp_len"])
            writer.writeheader()

            summaries = []
            for c in conc_levels:
                print(f"[measure] concurrency={c} sending {per_level} requests ...")
                s = await run_level(session, url, json_body, timeout_s, c, per_level, writer, run_label)
                summaries.append(s)
                print(f"  -> throughput={s['throughput_rps']:.2f} rps, ok={s['ok']}/{s['requests']}, p95={s['latency_p95_ms']:.1f} ms")

        # write summary
        with open(summary_path, "w", newline="") as fs:
            w = csv.DictWriter(fs, fieldnames=[
                "run_label","concurrency","requests","ok","errors","elapsed_s","throughput_rps",
                "latency_avg_ms","latency_p50_ms","latency_p95_ms","latency_p99_ms"
            ])
            w.writeheader()
            for s in summaries:
                s = dict(s)
                s["run_label"] = run_label
                w.writerow(s)

        print(f"Raw CSV  : {raw_path}")
        print(f"Summary  : {summary_path}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(1)
