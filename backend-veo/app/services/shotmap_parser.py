"""
shotmap_parser.py

Parseur sécurisé pour le menu VEO "Carte de tirs".

Ce module extrait les statistiques de tirs, taux de conversion, et répartitions
dans un format structuré et sécurisé. Il limite les données traitées, nettoie les
entrées utilisateur et valide chaque valeur.

Fonctions:
    parse_veo_shotmap(text: str, club_prefix: str) -> Dict
"""

import re
from typing import Any, Dict

# === Sécurité : Limites ===
MAX_LINE_LENGTH = 100
MAX_ITEMS = 30
MAX_LABEL_LENGTH = 50

# Labels attendus (en mode clé:valeur)
ALLOWED_LABELS = {
    "Buts",
    "Tirs",
    "Total des tentatives",
}

# Mots-clés pour détecter certaines phrases statistiques
PHRASE_CATEGORIES = {
    "conversion rate": "conversion_rate",
    "inside box conversion rate": "inside_box_conversion",
    "outside box conversion rate": "outside_box_conversion",
    "of total attempts inside box": "inside_box_attempts",
    "of total attempts outside box": "outside_box_attempts",
}


def _clean_line(line: str) -> str:
    """Nettoie une ligne du collage brut (anti-injection + taille limitée)."""
    line = line.strip()[:MAX_LINE_LENGTH]
    return re.sub(r"[^\w\s%.,\-]", "", line)


def _is_valid_number(value: str) -> bool:
    """Vérifie qu'une valeur est un nombre (entier ou flottant)."""
    return bool(re.fullmatch(r"\d+(\.\d+)?", value))


def _is_valid_percent_phrase(text: str) -> bool:
    """Vérifie qu'une phrase commence par un pourcentage valide."""
    return bool(re.match(r"^\d+(\.\d+)?%\s", text))


def parse_veo_shotmap(raw_text: str, club_prefix: str = "TEG") -> Dict[str, Any]:
    """
    Parse les données collées depuis le menu VEO "Carte de tirs".

    Nettoie les entrées, valide les formats, et retourne les données structurées.

    Args:
        raw_text (str): Contenu collé brut depuis VEO.
        club_prefix (str): Préfixe de l’équipe du club (optionnel).

    Returns:
        dict: Dictionnaire structuré contenant :
            - "type": Nom du menu ("carte_de_tirs")
            - "data": Dictionnaire de statistiques sécurisées

    Raises:
        ValueError: Si le format est invalide ou insuffisant.
    """
    lines = [line for line in raw_text.strip().splitlines() if line.strip()]
    safe_lines = [_clean_line(line) for line in lines]

    if len(safe_lines) < 3:
        raise ValueError("Contenu trop court pour être une carte de tirs.")

    data: Dict[str, str] = {}
    i = 0
    item_count = 0

    while i < len(safe_lines) and item_count < MAX_ITEMS:
        label = safe_lines[i].rstrip(".").strip()

        # Cas : label avec valeur numérique (Buts, Tirs, etc.)
        if label in ALLOWED_LABELS and i + 1 < len(safe_lines):
            value = safe_lines[i + 1]
            if _is_valid_number(value):
                data[label] = value
                i += 2
                item_count += 1
                continue
            else:
                i += 2
                continue

        # Cas : ligne avec pourcentage + texte (phrases)
        if "%" in label and _is_valid_percent_phrase(label):
            for key in PHRASE_CATEGORIES:
                if key in label:
                    phrase_key = PHRASE_CATEGORIES[key]
                    percent_value = label.split(" ")[0]
                    data[phrase_key] = percent_value
                    item_count += 1
                    break
            i += 1
            continue

        # Si ligne inconnue → on ignore
        i += 1

    if not data:
        raise ValueError("Aucune donnée exploitable détectée.")

    return {
        "type": "carte_de_tirs",
        "data": data,
    }
