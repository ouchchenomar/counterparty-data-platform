{#-
    Clé de contrôle d'un LEI (ISO 17442, ISO 7064 MOD 97-10), même règle que
    src/cdp/quality/lei.py. Les lettres deviennent des nombres (A=10 ... Z=35), puis le
    reste modulo 97 est calculé chiffre par chiffre pour éviter un entier de 40 chiffres.
    Le LEI est valide si ce reste vaut 1.
-#}
{% macro lei_mod97(column) -%}
    list_reduce(
        list_transform(
            string_split(
                array_to_string(
                    list_transform(
                        string_split({{ column }}, ''),
                        lambda c: case when c between 'A' and 'Z' then (ord(c) - 55)::varchar else c end
                    ),
                    ''
                ),
                ''
            ),
            lambda d: d::integer
        ),
        lambda acc, d: (acc * 10 + d) % 97
    )
{%- endmacro %}

{% macro is_valid_lei_format(column) -%}
    regexp_full_match({{ column }}, '[A-Z0-9]{18}[0-9]{2}')
{%- endmacro %}

{% macro is_valid_lei_checksum(column) -%}
    ({{ is_valid_lei_format(column) }} and {{ lei_mod97(column) }} = 1)
{%- endmacro %}
