#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os, argparse
import io

sns.set(style="whitegrid", font_scale=1.2)

def plot_metric(df, metric, ylabel, title, outfile):
    plt.figure(figsize=(8,6))
    sns.lineplot(
        data=df, x="concurrency", y=metric, hue="run_label", marker="o", linewidth=2.0
    )
    plt.title(title)
    plt.xlabel("Concurrency Level")
    plt.ylabel(ylabel)
    plt.legend(title="Endpoint", loc="best")
    plt.tight_layout()
    plt.savefig(outfile)
    print(f"[saved] {outfile}")
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="./bench_runs/combined_summary.csv", help="path to combined_summary.csv")
    ap.add_argument("--outdir", default="./bench_plots", help="output directory for plots")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    with open(args.csv, "r", encoding="utf-8") as f:
        content = f.read().strip()
    df = pd.read_csv(io.StringIO(content), dtype=str)  # 先读成字符串
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass
    print(f"[info] Loaded {len(df)} rows, columns={list(df.columns)}")
    print(f"[info] Loaded {len(df)} rows from {args.csv}")

    metrics = [
        ("throughput_rps", "Throughput (req/s)", "Throughput vs Concurrency"),
        ("latency_avg_ms", "Average Latency (ms)", "Average Latency vs Concurrency"),
        ("latency_p95_ms", "P95 Latency (ms)", "95th Percentile Latency vs Concurrency"),
        ("latency_p99_ms", "P99 Latency (ms)", "99th Percentile Latency vs Concurrency"),
    ]

    for col, ylabel, title in metrics:
        outfile = os.path.join(args.outdir, f"{col}.png")
        plot_metric(df, col, ylabel, title, outfile)

if __name__ == "__main__":
    main()
