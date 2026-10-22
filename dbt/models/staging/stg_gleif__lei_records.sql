with source as (

    select * from {{ source('raw', 'gleif_lei_records') }}

),

parsed as (

    select
        payload ->> '$.attributes.lei' as lei,
        payload ->> '$.attributes.entity.legalName.name' as legal_name,
        payload ->> '$.attributes.entity.legalForm.id' as legal_form_id,
        payload ->> '$.attributes.entity.legalForm.other' as legal_form_label,
        payload ->> '$.attributes.entity.category' as entity_category,
        payload ->> '$.attributes.entity.status' as entity_status,
        payload ->> '$.attributes.entity.legalAddress.city' as legal_city,
        payload ->> '$.attributes.entity.legalAddress.region' as legal_region,
        payload ->> '$.attributes.entity.legalAddress.country' as legal_country,
        payload ->> '$.attributes.registration.status' as registration_status,
        payload ->> '$.attributes.registration.corroborationLevel' as corroboration_level,
        (payload ->> '$.attributes.registration.initialRegistrationDate')::timestamptz as registered_at,
        (payload ->> '$.attributes.registration.lastUpdateDate')::timestamptz as last_updated_at,
        (payload ->> '$.attributes.registration.nextRenewalDate')::timestamptz as next_renewal_at,
        _source_file,
        _loaded_at
    from source

)

-- L'ingestion incrémentale se chevauche volontairement (docs/adr/0002) :
-- on ne garde que la dernière version connue de chaque LEI.
select *
from parsed
qualify row_number() over (
    partition by lei
    order by last_updated_at desc, _source_file desc
) = 1
