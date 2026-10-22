FROM apache/airflow:3.3.2-python3.12

# Le pipeline tourne dans son propre venv : Airflow orchestre sans partager ses dépendances
# avec dbt. Le code est monté au démarrage (docker-compose.yml) et prime via PYTHONPATH.
USER airflow
COPY --chown=airflow:root pyproject.toml README.md /tmp/cdp/
COPY --chown=airflow:root src /tmp/cdp/src
RUN python -m venv /home/airflow/cdp-venv \
    && PIP_USER=false /home/airflow/cdp-venv/bin/pip install --no-cache-dir /tmp/cdp
