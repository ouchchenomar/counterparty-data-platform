{#- Test générique : toutes les valeurs non nulles de la colonne sont des LEI valides. -#}
{% test valid_lei(model, column_name) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} is not null
      and not {{ is_valid_lei_checksum(column_name) }}
{% endtest %}
