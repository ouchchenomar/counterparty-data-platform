-- Une colonne booléenne par règle du catalogue (seeds/dq_rule_catalog.csv) : true = règle respectée.
-- Chaque règle ne juge que ce qui la concerne : une clé de contrôle n'est vérifiée que si le
-- format est correct, l'existence dans GLEIF que si la clé est correcte. Une anomalie déclenche
-- ainsi une seule règle, ce qui rend le taux de détection lisible.

with matched as (

    select * from {{ ref('int_counterparties__matched') }}

)

select
    counterparty_id,
    lei,

    legal_name is not null
        and city is not null
        and country_code is not null as chk_mandatory_fields,

    lei is not null as chk_lei_present,

    lei is null
        or {{ is_valid_lei_format('lei') }} as chk_lei_format,

    lei is null
        or not {{ is_valid_lei_format('lei') }}
        or {{ is_valid_lei_checksum('lei') }} as chk_lei_checksum,

    lei is null
        or not {{ is_valid_lei_checksum('lei') }}
        or is_matched_gleif as chk_lei_known,

    gleif_country is null
        or country_code is null
        or country_code = gleif_country as chk_country_consistent,

    lei is null
        or row_number() over (
            partition by lei
            order by onboarding_date, counterparty_id
        ) = 1 as chk_not_duplicate

from matched
