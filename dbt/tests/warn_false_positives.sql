{{ config(severity='warn') }}

-- Avertissement seulement : sur les vraies données, un signalement peut être un défaut réel de GLEIF.
select * from {{ ref('rpt_dq_false_positives') }}
