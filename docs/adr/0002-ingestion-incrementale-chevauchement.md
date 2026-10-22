# ADR 0002 — Ingestion incrémentale avec filigrane et chevauchement

- **Statut** : acceptée
- **Date** : 22/10/2026

## Contexte

Le pipeline interroge chaque jour l'API publique GLEIF pour les entités dont le siège légal est
au Maroc (`filter[entity.legalAddress.country]=MA`), par pages de 200, le maximum accepté.
Chaque enregistrement porte une date de dernière mise à jour
(`registration.lastUpdateDate`), sur laquelle l'API accepte un filtre.

Le premier run du 22/10/2026 a lu 211 LEI en 2 pages. Relire tout chaque jour resterait
possible à ce volume, mais ne passerait pas à l'échelle et ne refléterait pas un pipeline de
production. À l'inverse, un filtre trop strict sur la date peut perdre des enregistrements :
mises à jour publiées avec retard, plusieurs enregistrements à la même seconde, écarts de fuseau
horaire.

## Options envisagées

1. **Rechargement complet à chaque run.** Le plus simple et sans risque de trou, mais le coût
   croît avec le périmètre et chaque run relit des données inchangées.
2. **Incrémental strict** : ne lire que ce qui est postérieur à la dernière date vue. Économe,
   mais un enregistrement publié en retard, ou à la même date que le filigrane, peut être perdu
   sans que rien ne le signale.
3. **Incrémental avec chevauchement** : repartir du filigrane moins une marge, accepter de
   relire quelques enregistrements, et dédoublonner en aval.
4. **Fichiers Golden Copy et fichiers delta publiés par GLEIF.** Adaptés au périmètre mondial,
   mais disproportionnés pour un seul pays : on téléchargerait le monde pour en garder 211
   lignes.

## Décision

Option 3, avec une marge d'un jour.

- **Filigrane** : la date de mise à jour la plus récente vue, par pays, stockée dans
  `data/state/gleif_watermark.json`.
- **Filtre du run suivant** : `registration.lastUpdateDate > (filigrane − 1 jour)`, à la
  granularité de la date (`LOOKBACK` dans `src/cdp/ingestion/gleif.py`).
- **Le filigrane ne recule jamais** : on garde le maximum entre l'ancien filigrane et les dates
  du run, car le chevauchement peut ramener des dates antérieures.
- **Zone d'atterrissage immuable** : un fichier JSON Lines par run, rangé par date
  d'ingestion (`data/raw/gleif/ingest_date=AAAA-MM-JJ/`), jamais réécrit.
- **Dédoublonnage en staging** : `stg_gleif__lei_records` garde la dernière version de chaque
  LEI (`row_number()` par LEI, trié sur `last_updated_at` puis sur le nom du fichier source).
- **Échappatoires** : `--full-refresh` ignore le filigrane ; `--from-sample` rejoue
  l'échantillon versionné pour la CI sans toucher au filigrane.
- **Reprises** : 5 tentatives avec attente croissante sur les réponses 429, 500, 502, 503 et 504.

Le filtre envoyé à l'API et le calcul du filigrane avec la marge sont couverts par
`tests/test_gleif_ingestion.py`.

## Conséquences

- **Chaque run relit environ un jour de données.** Au run incrémental suivant le premier, un
  seul enregistrement a été relu, puis éliminé en staging.
- **La garantie est « au moins une fois », rendue sûre par l'idempotence en aval.** Si le run
  s'arrête après l'écriture du fichier mais avant celle du filigrane, le run suivant relit la
  même fenêtre et le staging absorbe les doublons.
- **La zone d'atterrissage grossit d'un fichier par run.** C'est voulu (on peut tout rejouer),
  mais il faudra un jour compacter ou archiver les anciens fichiers.
- **Les suppressions ne sont pas un sujet ici** : un LEI n'est pas supprimé, il change de
  statut (par exemple `LAPSED` ou `RETIRED`), ce qui arrive comme une mise à jour.
- **Le filigrane est un état hors d'Airflow.** Il est simple, mais rejouer une date précise
  n'est pas naturel. Une variante pilotée par l'intervalle de données d'Airflow
  (`data_interval_start`, `data_interval_end`) rendrait le backfill direct ; elle n'est pas
  retenue tant que le besoin est un rafraîchissement quotidien.
- **Limite connue** : le fichier d'un run est écrit directement à son emplacement final. Un
  arrêt brutal pourrait laisser un fichier incomplet que `load_raw` chargerait. Une écriture
  dans un fichier temporaire suivie d'un renommage corrigera ce point.
