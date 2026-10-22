with source as (

    select * from {{ source('raw', 'internal_counterparties') }}

)

select
    trim(counterparty_id) as counterparty_id,
    nullif(trim(legal_name), '') as legal_name,
    nullif(upper(trim(lei)), '') as lei,
    nullif(upper(trim(country_code)), '') as country_code,
    nullif(trim(city), '') as city,
    nullif(trim(legal_form), '') as legal_form,
    nullif(trim(segment), '') as segment,
    try_cast(onboarding_date as date) as onboarding_date,
    nullif(trim(relationship_manager), '') as relationship_manager,
    _source_file,
    _loaded_at
from source
