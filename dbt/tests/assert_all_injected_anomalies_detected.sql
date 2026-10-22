-- Test de non-régression : chaque type d'anomalie injectée doit être détecté à 100 %.
select *
from {{ ref('rpt_dq_detection') }}
where detected < injected
