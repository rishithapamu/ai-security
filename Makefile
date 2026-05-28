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
