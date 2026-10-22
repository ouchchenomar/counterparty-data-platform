-- Taux de détection par type d'anomalie : les anomalies injectées (vérité terrain)
-- ont-elles été signalées par la règle prévue pour elles dans le catalogue ?

with truth as (

    select * from {{ ref('stg_internal__anomalies_truth') }}

),

catalog as (

    select rule_name, expected_anomaly_type
    from {{ ref('dq_rule_catalog') }}
    where expected_anomaly_type is not null

),

issues as (

    select counterparty_id, rule_name from {{ ref('fct_dq_issues') }}

),

detections as (

    select
        truth.counterparty_id,
        truth.anomaly_type,
        count(issues.rule_name) > 0 as is_detected
    from truth
    left join catalog
        on truth.anomaly_type = catalog.expected_anomaly_type
    left join issues
        on truth.counterparty_id = issues.counterparty_id
        and catalog.rule_name = issues.rule_name
    group by truth.counterparty_id, truth.anomaly_type

)

select
    anomaly_type,
    count(*) as injected,
    count(*) filter (where is_detected) as detected,
    round(100.0 * count(*) filter (where is_detected) / count(*), 1) as detection_rate_pct
from detections
group by anomaly_type
order by anomaly_type
