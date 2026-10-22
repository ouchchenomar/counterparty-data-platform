select
    trim(counterparty_id) as counterparty_id,
    trim(anomaly_type) as anomaly_type
from {{ source('raw', 'anomalies_truth') }}
