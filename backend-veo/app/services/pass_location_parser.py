"""
pass_location_parser.py

Parseur pour le menu VEO "Zone de passe".
Extrait les pourcentages de passes par zone : Défense, Milieu, Attaque.

Fonction principale :
    parse_veo_pass_location(text: str) -> Dict
"""

import re
from typing import Dict

MAX_LINE_LENGTH = 100
ALLOWED_ZONES = ["Défense", "Milieu", "Attaque"]


def _sanitize_line(line: str) -> str:
    """Supprime les caractères non sûrs, limite la longueur."""
    return re.sub(r"[^\w\s%À-ÿ\-]", "", line.strip())[:MAX_LINE_LENGTH]


def _validate_percent(value: str) -> str:
    """Valide qu'une chaîne est bien un pourcentage simple comme '86%'."""
    if re.fullmatch(r"\d{1,3}%", value):
        return value
    raise ValueError(f"Pourcentage invalide : '{value}'")


def parse_veo_pass_location(raw_text: str) -> Dict:
    """
    Parse le menu "Zone de passes" de VEO.

    Attend 3 pourcentages suivis de 3 labels de zone (Défense, Milieu, Attaque).

    Args:
        raw_text (str): Texte brut collé depuis VEO.

    Returns:
        dict: Dictionnaire structuré avec type et data associant chaque zone à son pourcentage.

    Raises:
        ValueError: Si le format ou les données sont invalides.
    """
    lines = [
        _sanitize_line(line) for line in raw_text.strip().splitlines() if line.strip()
    ]

    if len(lines) != 6:
        raise ValueError(
            "Le menu 'Zone de passes' doit contenir exactement 6 lignes."
        )

    percents = lines[:3]
    zones = lines[3:]

    # Validation des pourcentages
    percents = [_validate_percent(p) for p in percents]

    # Validation des zones
    if sorted(zones) != sorted(ALLOWED_ZONES):
        raise ValueError(f"Zones attendues : {ALLOWED_ZONES}, mais reçu : {zones}")

    data = {zone: percent for zone, percent in zip(zones, percents)}

    return {"type": "zone_de_passes", "data": data}
