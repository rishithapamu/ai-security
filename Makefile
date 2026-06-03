PYTHON = cd ~/Desktop/internship_project/ai-sec-workbench && uv run python cli.py

ingest-all:
	$(PYTHON) all

ingest-jailbreakbench:
	$(PYTHON) jailbreakbench

ingest-advbench:
	$(PYTHON) advbench

ingest-harmbench:
	$(PYTHON) harmbench

ingest-donotanswer:
	$(PYTHON) donotanswer

ingest-inthewild:
	$(PYTHON) inthewild

embed:
	cd ~/Desktop/internship_project/ai-sec-workbench && uv run python cli.py embed

embed-custom:
	cd ~/Desktop/internship_project/ai-sec-workbench && uv run python cli.py embed --input $(INPUT) --out $(OUT)

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
		--input data/embeddings/ \
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

	for f in data/plots/*.html; do open $$f; done
