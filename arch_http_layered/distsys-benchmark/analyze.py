#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse, os

sns.set(style="whitegrid", font_scale=1.2)

def plot_metric(df, metric, ylabel, title, outfile):
    plt.figure(figsize=(8,6))
    sns.lineplot(
        data=df, x="concurrency", y=metric, hue="run_label", marker="o", linewidth=2
    )
    plt.title(title)
    plt.xlabel("Concurrency Level")
    plt.ylabel(ylabel)
    plt.legend(title="Service", loc="best")
    plt.tight_layout()
    plt.savefig(outfile, dpi=160)
    print(f"[saved] {outfile}")
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="./bench_runs/combined_summary.csv")
    ap.add_argument("--outdir", default="./bench_plots")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.csv)
    metrics = [
        ("throughput_rps", "Throughput (req/s)", "Throughput vs Concurrency"),
        ("latency_avg_ms", "Average Latency (ms)", "Average Latency vs Concurrency"),
        ("latency_p95_ms", "P95 Latency (ms)", "95th Percentile Latency vs Concurrency"),
        ("latency_p99_ms", "P99 Latency (ms)", "99th Percentile Latency vs Concurrency"),
    ]
    for metric, ylabel, title in metrics:
        outfile = os.path.join(args.outdir, f"{metric}.png")
        plot_metric(df, metric, ylabel, title, outfile)

if __name__ == "__main__":
    main()
