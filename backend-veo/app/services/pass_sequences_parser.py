"""
pass_sequence_parser.py

Parseur pour le menu VEO "Enchaînements de passes".
Extrait les statistiques sur les séries de passes.

Fonction principale :
    parse_veo_pass_sequence(text: str) -> Dict
"""

from typing import Dict

MAX_LINE_LENGTH = 100

LABELS = ["3 à 5 passes", "6 passes ou plus", "Enchaînement de passes le plus long"]


def parse_veo_pass_sequence(raw_text: str) -> Dict:
    """
    Parse le menu "Enchaînements de passes" de VEO.

    Attend 3 labels avec leurs valeurs numériques associées (au total 6 lignes).

    Args:
        raw_text (str): Texte brut collé depuis VEO.

    Returns:
        dict: Dictionnaire structurant les labels et valeurs extraites.

    Raises:
        ValueError: Si les données ne sont pas valides ou incomplètes.
    """
    lines = [
        line.strip()[:MAX_LINE_LENGTH]
        for line in raw_text.strip().splitlines()
        if line.strip()
    ]

    if len(lines) != 6:
        raise ValueError(
            "Le menu 'Enchaînements de passes' doit contenir exactement 6 lignes."
        )

    data = {}
    for i in range(0, 6, 2):
        label = lines[i]
        value = lines[i + 1]

        if label not in LABELS:
            raise ValueError(f"Label inconnu : '{label}'")

        if not value.isdigit():
            raise ValueError(
                f"Valeur numérique attendue pour '{label}', reçu : '{value}'"
            )

        data[label] = int(value)

    return {"type": "enchaînements_de_passes", "data": data}
