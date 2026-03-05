"""
shotmap_parser.py

Parseur sécurisé pour le menu VEO "Carte des tirs".

Ce module extrait les statistiques de tirs, taux de conversion, et répartitions
dans un format structuré et sécurisé. Il limite les données traitées, nettoie les
entrées utilisateur et valide chaque valeur.

Fonctions:
    parse_veo_shotmap(raw_text: str, club_prefix: str) -> Dict[str, Any]
"""

import re
from typing import Any, Dict, Optional

# === Sécurité : Limites ===
MAX_LINE_LENGTH = 100
MAX_ITEMS = 30

# Labels attendus (valeur sur la ligne suivante)
ALLOWED_LABELS = {
    "Buts",
    "Tirs",
    "Total des tentatives",
}

# Regex helpers
_RE_NUMBER = re.compile(r"^\d+(\.\d+)?$")
_RE_PERCENT_LINE = re.compile(r"^(?P<pct>\d+(\.\d+)?)%\s+(?P<rest>.+)$", re.IGNORECASE)


def _clean_line(line: str) -> str:
    """Nettoie une ligne du collage brut (anti-injection + taille limitée)."""
    line = line.strip()[:MAX_LINE_LENGTH]
    # Autorise lettres/chiffres/espaces/%/.,- et apostrophe typographique
    return re.sub(r"[^\w\s%.,\-’']", "", line)


def _is_valid_number(value: str) -> bool:
    """Vérifie qu'une valeur est un nombre (entier ou flottant)."""
    return bool(_RE_NUMBER.fullmatch(value))


def _extract_percent(line: str) -> Optional[str]:
    """Extrait un pourcentage normalisé (ex: '9%') si la ligne commence par un pourcentage."""
    m = _RE_PERCENT_LINE.match(line)
    if not m:
        return None
    pct = m.group("pct")
    # Normalise "9" ou "9.0" -> "9%"
    return f"{pct}%"


def _normalize_phrase(rest: str) -> str:
    """Normalise la partie texte après le % pour faciliter les comparaisons."""
    s = rest.strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    # enlève ponctuation finale
    s = s.rstrip(".")
    return s


def parse_veo_shotmap(raw_text: str, club_prefix: str = "TEG") -> Dict[str, Any]:
    """
    Parse les données collées depuis le menu VEO "Carte des tirs".

    Nettoie les entrées, valide les formats, et retourne les données structurées.

    Args:
        raw_text (str): Contenu collé brut depuis VEO.
        club_prefix (str): Préfixe de l’équipe du club (optionnel).

    Returns:
        dict: Dictionnaire structuré contenant :
            - "type": Nom du menu ("carte_des_tirs")
            - "data": Dictionnaire de statistiques sécurisées

    Raises:
        ValueError: Si le format est invalide ou insuffisant.
    """
    lines = [line for line in raw_text.strip().splitlines() if line.strip()]
    safe_lines = [_clean_line(line) for line in lines if _clean_line(line)]

    if len(safe_lines) < 3:
        raise ValueError("Contenu trop court pour être une carte des tirs.")

    data: Dict[str, str] = {}
    i = 0
    item_count = 0

    # Mapping phrases (FR) -> clés de sortie stables
    # On matche sur la partie texte après le % (normalisée).
    phrase_to_key = {
        # FR (new)
        "taux de conversion": "team_shotmap_conversion_rate_pct",
        "dans la surface de réparation": "team_shotmap_inside_box_conversion_rate_pct",
        "hors de la surface de réparation": "team_shotmap_outside_box_conversion_rate_pct",
        "des tentatives totales dans la surface": "team_shotmap_attempts_inside_box_pct",
        "des tentatives totales hors de la surface": "team_shotmap_attempts_outside_box_pct",

        # EN (legacy) - optionnel mais recommandé
        "conversion rate": "team_shotmap_conversion_rate_pct",
        "inside box conversion rate": "team_shotmap_inside_box_conversion_rate_pct",
        "outside box conversion rate": "team_shotmap_outside_box_conversion_rate_pct",
        "of total attempts inside box": "team_shotmap_attempts_inside_box_pct",
        "of total attempts outside box": "team_shotmap_attempts_outside_box_pct",
    }

    while i < len(safe_lines) and item_count < MAX_ITEMS:
        label = safe_lines[i].rstrip(".").strip()

        # 1) Labels avec valeur sur la ligne suivante
        if label in ALLOWED_LABELS and i + 1 < len(safe_lines):
            value = safe_lines[i + 1].strip()
            if _is_valid_number(value):
                data[label] = value
                item_count += 1
            i += 2
            continue

        # 2) Lignes du style "9% taux de conversion."
        pct = _extract_percent(label)
        if pct:
            # récupère le texte après le pourcentage
            m = _RE_PERCENT_LINE.match(label)
            rest = _normalize_phrase(m.group("rest")) if m else ""
            # essaye de mapper
            for phrase, out_key in phrase_to_key.items():
                if phrase in rest:
                    data[out_key] = pct
                    item_count += 1
                    break
            i += 1
            continue

        # 3) Sinon: ignore
        i += 1

    if not data:
        raise ValueError("Aucune donnée exploitable détectée (Carte des tirs).")

    return {
        "type": "carte_des_tirs",  # ✅ nouvelle dénomination conservée
        "data": data,
    }