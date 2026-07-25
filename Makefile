PYTHON = uv run python cli.py

ingest-all:
	$(PYTHON) ingest

ingest-jailbreakbench:
	$(PYTHON) ingest jailbreakbench

ingest-advbench:
	$(PYTHON) ingest advbench

ingest-harmbench:
	$(PYTHON) ingest harmbench

ingest-donotanswer:
	$(PYTHON) ingest donotanswer

ingest-inthewild:
	$(PYTHON) ingest inthewild

embed:
	$(PYTHON) embed

embed-custom:
	$(PYTHON) embed \
		--input $(INPUT) \
		--out $(OUT)

dedup:
	PYTHONPATH=. uv run python src/embed/dedup.py \
		--input data/processed/ \
		--embeddings data/embeddings/

visualize:
	uv run python src/embed/visualize.py \
		--input data/processed/ \
		--embeddings data/embeddings/ \
		--out data/plots/umap.html
		open data/plots/umap.html

cluster:
	uv run python src/cluster/cluster.py \
		--input data/processed/ \
		--embeddings data/embeddings/ \
		--out data/clusters/

tune:
	uv run python src/cluster/tune.py \
		--input data/processed/ \
		--embeddings data/embeddings/ \
		--out data/clusters/tuning_results.csv

cluster-analysis:
	uv run python src/cluster/analysis.py \
		--input data/processed/ \
		--embeddings data/embeddings/ \
		--out data/plots/

quality:
	PYTHONPATH=. uv run python src/cluster/quality.py \
    --embeddings data/embeddings/ \
    --clusters data/clusters/clusters.parquet \
    --labels data/clusters/cluster_labels.yaml \
    --threshold 0.05

noise-analysis:
	uv run python src/cluster/noise-analysis.py \
		--input data/processed/ \
		--embeddings data/embeddings/ \
		--out data/clusters

coverage:
	PYTHONPATH=. uv run python src/analytics/coverage_analysis.py \
		--assignments src/registry/candidates/cluster_assignments.yaml \
		--out reports/

novelty:
	PYTHONPATH=. uv run python src/analytics/novelty.py \
		--embeddings data/embeddings/ \
		--clusters data/clusters/clusters.parquet \
		--out reports/

test_cluster:
	uv run pytest tests/test_cluster.py -v

dedup-run:
	PYTHONPATH=. uv run python src/embed/dedup_merge.py \
		--input data/processed/ \
		--embeddings data/embeddings/ \
		--out data/processed/deduped.parquet

.PHONY: dashboard run

dashboard:
	PYTHONPATH=. uv run streamlit run src/app/main.py

run:
	$(PYTHON) ingest all
	$(PYTHON) embed
	$(MAKE) cluster
	$(MAKE) cluster-analysis
	$(MAKE) quality
	$(MAKE) noise-analysis
	$(MAKE) coverage
	$(MAKE) novelty
	$(MAKE) dashboard
