-- Golden record : une ligne par contrepartie, doublons exclus.
-- Règle de survivance : GLEIF fait foi pour l'identité légale (nom, ville, pays) quand le LEI
-- est reconnu ; le système interne fait foi pour les données de relation (segment, RM).
-- TODO : fusionner les attributs des doublons au lieu de garder la première fiche ;
--        historiser les changements (snapshot SCD2 dans dbt/snapshots).

with matched as (

    select * from {{ ref('int_counterparties__matched') }}

),

checks as (

    select counterparty_id, chk_not_duplicate
    from {{ ref('int_counterparties__dq_checks') }}

),

issues as (

    select
        counterparty_id,
        count(*) as dq_issue_count,
        bool_or(is_blocking) as has_blocking_issue
    from {{ ref('fct_dq_issues') }}
    group by counterparty_id

),

rule_count as (

    select count(*) as n_rules from {{ ref('dq_rule_catalog') }}

)

select
    matched.counterparty_id,
    matched.lei,
    coalesce(matched.gleif_legal_name, matched.legal_name) as legal_name,
    coalesce(matched.gleif_city, matched.city) as city,
    coalesce(matched.gleif_country, matched.country_code) as country_code,
    matched.legal_form,
    matched.segment,
    matched.onboarding_date,
    matched.relationship_manager,
    case when matched.is_matched_gleif then 'GLEIF' else 'INTERNE' end as identity_source,
    matched.gleif_registration_status,
    matched.gleif_next_renewal_at,
    coalesce(issues.dq_issue_count, 0) as dq_issue_count,
    round(1 - coalesce(issues.dq_issue_count, 0) / rule_count.n_rules, 3) as dq_score,
    coalesce(issues.has_blocking_issue, false) as is_quarantined
from matched
inner join checks
    on matched.counterparty_id = checks.counterparty_id
left join issues
    on matched.counterparty_id = issues.counterparty_id
cross join rule_count
where checks.chk_not_duplicate
