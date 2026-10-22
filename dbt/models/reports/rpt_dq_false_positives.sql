-- Fiches signalées alors qu'aucune anomalie n'y a été injectée.
-- Sur les vraies données GLEIF, une ligne ici peut aussi révéler un défaut réel de la source.

with truth as (

    select counterparty_id from {{ ref('stg_internal__anomalies_truth') }}

)

select
    issues.counterparty_id,
    issues.lei,
    string_agg(issues.rule_name, ', ' order by issues.rule_name) as rules_triggered
from {{ ref('fct_dq_issues') }} as issues
left join truth
    on issues.counterparty_id = truth.counterparty_id
where truth.counterparty_id is null
group by issues.counterparty_id, issues.lei
