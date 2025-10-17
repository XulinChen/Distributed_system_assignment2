#!/usr/bin/env python3
import argparse, csv, os, math
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

def read_summary(path):
    rows = []
    with open(path, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            row = {k: try_num(v) for k,v in row.items()}
            rows.append(row)
    return rows

def try_num(x):
    try:
        if "." in x:
            return float(x)
        return int(x)
    except Exception:
        return x

def plot_xy(xs, ys, xlabel, ylabel, title, out_path):
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True, help="Path to *_summary.csv")
    ap.add_argument("--outdir", default="./runs")
    ap.add_argument("--run_label", default="baseline")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    rows = read_summary(args.summary)
    rows = sorted(rows, key=lambda r: r["concurrency"])

    conc = [r["concurrency"] for r in rows]
    thr = [r["throughput_rps"] for r in rows]
    p95 = [r["latency_p95_ms"] for r in rows]
    err = [100.0 * r["errors"]/max(1,r["requests"]) for r in rows]

    plot_xy(conc, thr, "Concurrency", "Throughput (req/s)",
            f"Throughput vs Concurrency ({args.run_label})",
            os.path.join(args.outdir, f"{args.run_label}_throughput.png"))
    plot_xy(conc, p95, "Concurrency", "p95 Latency (ms)",
            f"p95 Latency vs Concurrency ({args.run_label})",
            os.path.join(args.outdir, f"{args.run_label}_p95_latency.png"))
    plot_xy(conc, err, "Concurrency", "Error Rate (%)",
            f"Error Rate vs Concurrency ({args.run_label})",
            os.path.join(args.outdir, f"{args.run_label}_error_rate.png"))

    # Write a cleaned summary CSV with extra columns
    out_csv = os.path.join(args.outdir, f"{args.run_label}_summary_clean.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "concurrency","requests","ok","errors","elapsed_s","throughput_rps",
            "latency_avg_ms","latency_p50_ms","latency_p95_ms","latency_p99_ms","error_rate_pct"
        ])
        w.writeheader()
        for r in rows:
            r2 = {k:r[k] for k in w.fieldnames if k in r}
            r2["error_rate_pct"] = 100.0 * r["errors"]/max(1,r["requests"])
            w.writerow(r2)

    print("Wrote plots and cleaned summary to", args.outdir)

if __name__ == "__main__":
    main()
