.PHONY: bench analyze report all

CONFIG?=config.yaml
RUN_LABEL?=baseline

all: bench analyze report

bench:
	python3 benchmark.py -c $(CONFIG)

analyze:
	python3 analyze.py --summary ./runs/$(RUN_LABEL)_summary.csv --outdir ./runs --run_label $(RUN_LABEL)

report:
	python3 generate_report.py -c $(CONFIG) -s ./runs/$(RUN_LABEL)_summary_clean.csv

