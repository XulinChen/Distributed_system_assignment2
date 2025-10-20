#!/usr/bin/env python3
import asyncio, aiohttp, time, json, argparse, os, sys, uuid, yaml, csv
from statistics import mean
from urllib.parse import urlencode

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

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

async def http_call(session, method, url, json_body, timeout_s):
    t0 = time.perf_counter()
    try:
        if method.upper() == "GET":
            async with session.get(url, timeout=timeout_s) as resp:
                text = await resp.text()
                t1 = time.perf_counter()
                return {
                    "ok": (200 <= resp.status < 300),
                    "status": resp.status,
                    "latency_ms": (t1 - t0) * 1000.0,
                    "resp_len": len(text),
                }
        else:
            async with session.post(url, json=json_body, timeout=timeout_s) as resp:
                text = await resp.text()
                t1 = time.perf_counter()
                return {
                    "ok": (200 <= resp.status < 300),
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

def subst_placeholders(obj, ctx):
    if obj is None:
        return None
    if isinstance(obj, str):
        s = obj
        for k, v in ctx.items():
            s = s.replace("${%s}" % k, str(v))
        return s
    if isinstance(obj, list):
        return [subst_placeholders(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: subst_placeholders(v, ctx) for k, v in obj.items()}
    return obj

async def run_level(session, method, url, json_body, timeout_s, concurrency, total_requests, writer, run_label):
    from statistics import mean
    latencies = []
    ok_count = 0
    start_wall = time.perf_counter()
    sem = asyncio.Semaphore(concurrency)

    async def worker(req_id):
        nonlocal ok_count
        async with sem:
            res = await http_call(session, method, url, json_body, timeout_s)
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
    for _ in range(total_requests):
        import uuid
        req_uuid = str(uuid.uuid4())
        tasks.append(asyncio.create_task(worker(req_uuid)))
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start_wall
    throughput = ok_count / elapsed if elapsed > 0 else 0.0
    def pct(values, p):
        if not values:
            return float("nan")
        arr = sorted(values)
        k = (len(arr)-1) * (p/100.0)
        f = int(k)
        c = min(f+1, len(arr)-1)
        if f == c:
            return arr[f]
        return arr[f] + (arr[c]-arr[f]) * (k - f)
    return {
        "concurrency": concurrency,
        "requests": total_requests,
        "ok": ok_count,
        "errors": total_requests - ok_count,
        "elapsed_s": elapsed,
        "throughput_rps": throughput,
        "latency_avg_ms": mean(latencies) if latencies else float("nan"),
        "latency_p50_ms": pct(latencies, 50.0),
        "latency_p95_ms": pct(latencies, 95.0),
        "latency_p99_ms": pct(latencies, 99.0)
    }

async def prepare_context(base_url, headers, timeout_s):
    ctx = {}
    async with aiohttp.ClientSession(headers=headers) as session:
        # Register
        import uuid
        uname = f"user_{uuid.uuid4().hex[:8]}"
        pw = "pw"
        await http_call(session, "POST", f"{base_url}/register", {"username": uname, "password": pw}, timeout_s)

        # Login
        async with session.post(f"{base_url}/login", json={"username": uname, "password": pw}, timeout=timeout_s) as resp:
            j = await resp.json(content_type=None)
            ctx["TOKEN"] = j.get("token","")

        # Create challenge
        chal_body = {"token": ctx["TOKEN"], "title": "Bench Challenge", "description": "benchmark"}
        async with session.post(f"{base_url}/challenges", json=chal_body, timeout=timeout_s) as resp:
            j = await resp.json(content_type=None)
            chal = (j.get("challenge") or {})
            ctx["CHALLENGE_ID"] = chal.get("id") or "default"

        # Submit once
        subm_body = {"token": ctx["TOKEN"], "challenge_id": ctx["CHALLENGE_ID"], "artifact": "demo_model_v1"}
        async with session.post(f"{base_url}/submit", json=subm_body, timeout=timeout_s) as resp:
            j = await resp.json(content_type=None)
            s = (j.get("submission") or {})
            ctx["SUBMISSION_ID"] = s.get("id","")

        # Evaluate once
        if ctx["SUBMISSION_ID"]:
            await http_call(session, "POST", f"{base_url}/evaluate",
                            {"submission_id": ctx["SUBMISSION_ID"], "challenge_id": ctx["CHALLENGE_ID"]},
                            timeout_s)
    return ctx

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default="suite.yaml")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    base_url = cfg["base_url"].rstrip("/")
    headers = cfg.get("headers", {})
    timeout_s = float(cfg.get("timeout_seconds", 30.0))
    outdir = cfg.get("output_dir", "./bench_runs")
    os.makedirs(outdir, exist_ok=True)

    print("[prepare] registering/login/create-challenge/submit/evaluate ...")
    ctx = await prepare_context(base_url, headers, timeout_s)
    print("[prepare] context:", ctx)

    all_rows = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for run in cfg["runs"]:
            name = run["name"]
            method = run.get("method", "POST").upper()
            path = run["path"]
            conc_levels = list(run.get("concurrency_levels", [1,2,4,8]))
            per_level = int(run.get("requests_per_level", 100))
            warmup = int(run.get("warmup_requests", 0))

            body_tpl = run.get("json_body")
            query_tpl = run.get("query")
            body = subst_placeholders(body_tpl, ctx) if body_tpl else None
            query = subst_placeholders(query_tpl, ctx) if query_tpl else None

            # URL
            if method == "GET" and query:
                url = f"{base_url}{path}?{urlencode(query)}"
            else:
                url = f"{base_url}{path}"

            print(f"[run:{name}] {method} {url}")
            if warmup > 0:
                tasks = [http_call(session, method, url, body, timeout_s) for _ in range(warmup)]
                await asyncio.gather(*tasks)

            raw_path = os.path.join(outdir, f"{name}_raw.csv")
            summary_path = os.path.join(outdir, f"{name}_summary.csv")
            with open(raw_path, "w", newline="") as fraw:
                writer = csv.DictWriter(fraw, fieldnames=["run_label","concurrency","req_id","ok","status","latency_ms","resp_len"])
                writer.writeheader()

                summaries = []
                for c in conc_levels:
                    print(f"  [measure] concurrency={c} sending {per_level} requests ...")
                    s = await run_level(session, method, url, body, timeout_s, c, per_level, writer, name)
                    summaries.append(s)
                    print(f"    -> throughput={s['throughput_rps']:.2f} rps, ok={s['ok']}/{s['requests']}, p95={s['latency_p95_ms']:.1f} ms")

            with open(summary_path, "w", newline="") as fs:
                w = csv.DictWriter(fs, fieldnames=[
                    "run_label","concurrency","requests","ok","errors","elapsed_s","throughput_rps",
                    "latency_avg_ms","latency_p50_ms","latency_p95_ms","latency_p99_ms"
                ])
                w.writeheader()
                for s in summaries:
                    s = dict(s)
                    s["run_label"] = name
                    w.writerow(s)

            for s in summaries:
                s = dict(s)
                s["run_label"] = name
                all_rows.append(s)

    combined_path = os.path.join(outdir, "combined_summary.csv")
    with open(combined_path, "w", newline="") as fc:
        w = csv.DictWriter(fc, fieldnames=[
            "run_label","concurrency","requests","ok","errors","elapsed_s","throughput_rps",
            "latency_avg_ms","latency_p50_ms","latency_p95_ms","latency_p99_ms"
        ])
        w.writeheader()
        for s in all_rows:
            w.writerow(s)

    print(f"All done.Combined summary: {combined_path}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(1)
