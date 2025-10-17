#!/usr/bin/env python3
import argparse, os, json, yaml, datetime

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c","--config", default="config.yaml")
    ap.add_argument("-s","--summary_clean", required=True, help="Path to *_summary_clean.csv from analyze.py")
    ap.add_argument("-t","--template", default="templates/report_template.md")
    ap.add_argument("-o","--out", default=None, help="Output Markdown path")
    ap.add_argument("--hardware_env", default="(fill in: e.g., 1× AMD Ryzen 9 7950X, 64 GB RAM, NVMe SSD)")
    ap.add_argument("--software_env", default="(fill in: e.g., Ubuntu 22.04, Docker 27.x, Python 3.10)")
    ap.add_argument("--num_nodes", default="(fill in: e.g., gateway=1, worker=4, DB=1)")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    run_label = cfg.get("run_label","baseline")

    with open(args.template, "r") as f:
        tmpl = f.read()

    md = tmpl.format(
        date=str(datetime.date.today()),
        run_label=run_label,
        hardware_env=args.hardware_env,
        software_env=args.software_env,
        num_nodes=args.num_nodes,
        target_url=cfg.get("target_url","(unknown)"),
        warmup=cfg.get("warmup_requests",0),
        requests_per_level=cfg.get("requests_per_level",100),
        concurrency_levels=cfg.get("concurrency_levels",[1,2,4,8]),
        timeout_seconds=cfg.get("timeout_seconds",30),
        payload=cfg.get("payload",{}),
    )

    out_path = args.out or os.path.join(os.path.dirname(args.summary_clean), f"{run_label}_report.md")
    with open(out_path, "w") as f:
        f.write(md)

    print("Wrote report to", out_path)

if __name__ == "__main__":
    main()
