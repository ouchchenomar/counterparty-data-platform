"""Validation des identifiants LEI (ISO 17442).

Un LEI compte 20 caractères : 18 caractères alphanumériques suivis de 2 chiffres de
contrôle calculés selon ISO 7064 MOD 97-10 (le même principe que l'IBAN).
La même règle existe côté SQL dans la macro dbt `is_valid_lei_checksum`.
"""

import re

LEI_PATTERN = re.compile(r"[A-Z0-9]{18}[0-9]{2}")
LEI_BASE_PATTERN = re.compile(r"[A-Z0-9]{18}")


def _to_digits(value: str) -> str:
    # Chaque lettre devient un nombre à deux chiffres : A=10, B=11, ..., Z=35.
    return "".join(str(int(char, 36)) for char in value)


def is_valid_lei(lei: str | None) -> bool:
    """Vrai si le LEI a le bon format et une clé de contrôle correcte."""
    if not lei or not LEI_PATTERN.fullmatch(lei):
        return False
    return int(_to_digits(lei)) % 97 == 1


def compute_check_digits(base: str) -> str:
    """Calcule les 2 chiffres de contrôle d'une base LEI de 18 caractères."""
    if not LEI_BASE_PATTERN.fullmatch(base):
        raise ValueError(f"Base LEI invalide : {base!r} (18 caractères A-Z/0-9 attendus)")
    remainder = int(_to_digits(base + "00")) % 97
    return f"{98 - remainder:02d}"
