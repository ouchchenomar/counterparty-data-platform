# ADR 0001 — DuckDB en local et en CI, BigQuery pour la version cloud

- **Statut** : acceptée
- **Date** : 22/10/2026

## Contexte

Le projet doit tourner sur un poste personnel et dans GitHub Actions, sans compte, sans coût et
sans secret : un recruteur ou un relecteur doit pouvoir le lancer avec `pip install` puis une
commande. Les volumes sont faibles : 211 LEI marocains et 222 fiches internes au run du
22/10/2026.

Il faut pourtant un vrai moteur SQL, compatible dbt, capable de lire les fichiers de la zone
d'atterrissage (JSON Lines, CSV) et proche du SQL d'un entrepôt de production.

## Options envisagées

1. **PostgreSQL dans Docker**, comme dans le projet Onbor. Robuste et réaliste, mais impose
   Docker pour lancer le moindre test, un service à démarrer en CI et un chargement explicite
   des fichiers.
2. **Un entrepôt cloud dès le départ** (BigQuery, Snowflake). Proche de la production, mais
   demande un compte et des identifiants, y compris en CI, et rend le projet impossible à
   lancer hors ligne.
3. **SQLite**. Aucune installation, mais pas de types JSON ni de fonctions analytiques
   suffisantes, et un adaptateur dbt peu maintenu.
4. **DuckDB en local et en CI, entrepôt cloud ensuite.** Un fichier, aucune infrastructure,
   lecture native du JSON Lines et du CSV, adaptateur `dbt-duckdb` maintenu.

## Décision

Option 4. L'entrepôt est le fichier `data/warehouse/cdp.duckdb` (chemin surchargeable par
`CDP_DUCKDB_PATH`), utilisé par dbt via la cible `dev` de `dbt/profiles.yml`, en local comme
en CI.

BigQuery est la cible retenue pour une version cloud, parce que son bac à sable est gratuit et
sans carte bancaire. La cible `bigquery` est préparée, en commentaire, dans `dbt/profiles.yml`.
Elle n'est pas activée.

## Conséquences

- **Ce qui devient simple** : `load_raw.py` charge la zone d'atterrissage en quelques lignes
  de SQL (`read_json_objects`, `read_csv`) ; la CI exécute tout le pipeline hors ligne sur
  l'échantillon versionné, dbt compris.
- **Un seul écrivain à la fois** : DuckDB verrouille le fichier en écriture. Le DAG Airflow
  limite donc les runs simultanés (`max_active_runs=1`). Ce n'est pas une base partageable
  entre plusieurs utilisateurs.
- **Une partie du SQL est propre à DuckDB** : l'extraction JSON (`payload ->> '$.attributes.lei'`),
  les conversions `::timestamptz` et surtout la macro `lei_mod97`, qui repose sur les listes
  et les lambdas de DuckDB. La bascule vers BigQuery demandera une version de ces macros par
  adaptateur (`adapter.dispatch`) et une réécriture du parsing JSON (`JSON_VALUE`).
- **Les tables raw sont reconstruites à chaque run** à partir des fichiers. C'est idempotent
  et suffisant à ce volume ; il faudra un chargement incrémental si la zone d'atterrissage
  grossit fortement.

## Quand revoir cette décision

- Si le volume dépasse ce qu'un poste traite confortablement (par exemple le fichier mondial
  GLEIF de plusieurs millions de LEI).
- Si plusieurs personnes ou outils doivent lire et écrire en même temps.
- Si le projet est transposé dans un contexte bancaire : l'entrepôt serait alors celui de
  l'établissement (PostgreSQL, Oracle ou SQL Server sur site, ou un entrepôt cloud autorisé).
