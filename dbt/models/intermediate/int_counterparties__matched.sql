with internal as (

    select * exclude (_source_file, _loaded_at)
    from {{ ref('stg_internal__counterparties') }}

),

gleif as (

    select * from {{ ref('stg_gleif__lei_records') }}

)

-- Rapprochement exact sur le LEI.
-- TODO : rapprochement approché sur la raison sociale pour les fiches sans LEI
-- (normalisation du nom, jaro_winkler_similarity, seuil documenté dans un ADR).
select
    internal.*,
    gleif.lei is not null as is_matched_gleif,
    gleif.legal_name as gleif_legal_name,
    gleif.legal_city as gleif_city,
    gleif.legal_country as gleif_country,
    gleif.entity_status as gleif_entity_status,
    gleif.registration_status as gleif_registration_status,
    gleif.next_renewal_at as gleif_next_renewal_at
from internal
left join gleif
    on internal.lei = gleif.lei
