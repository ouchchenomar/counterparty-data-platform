-- Une ligne par règle non respectée, enrichie par le catalogue des règles.
-- TODO : passer en modèle incrémental pour historiser les anomalies run après run.

with checks as (

    select * from {{ ref('int_counterparties__dq_checks') }}

),

unpivoted as (

    unpivot checks
    on columns('^chk_')
    into name rule_name value passed

),

catalog as (

    select * from {{ ref('dq_rule_catalog') }}

)

select
    unpivoted.counterparty_id,
    unpivoted.lei,
    unpivoted.rule_name,
    catalog.dimension,
    catalog.severity,
    catalog.is_blocking,
    catalog.description,
    '{{ run_started_at }}'::timestamptz as dq_run_at
from unpivoted
left join catalog
    on unpivoted.rule_name = catalog.rule_name
where not unpivoted.passed
