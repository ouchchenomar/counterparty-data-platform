.PHONY: install lint test sample pipeline docs up down

install:  ## venv activé : installe le projet et les outils de dev
	python -m pip install -e ".[dev]"

lint:
	ruff check .

test:
	pytest

sample:  ## pipeline complet hors ligne, sur l'échantillon versionné
	python -m cdp.pipeline --from-sample

pipeline:  ## pipeline complet sur l'API GLEIF (incrémental après le premier run)
	python -m cdp.pipeline

docs:  ## documentation dbt locale (lineage) dans dbt/target/static_index.html
	cd dbt && dbt docs generate --static

up:  ## Airflow sur http://localhost:8080
	docker compose up --build -d

down:
	docker compose down
