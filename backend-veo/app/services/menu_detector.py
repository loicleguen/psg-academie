"""
menu_detector.py

Détecte dynamiquement le type de menu VEO (Statistiques, Carte des tirs, etc.)
en analysant le contenu brut collé par l’utilisateur.

Cette détection permet de rediriger automatiquement vers le parseur adapté sans intervention manuelle.
"""


def detect_veo_menu_type(text: str) -> str:
    """
    Détecte le type de menu VEO à partir d’un collage brut.

    Cette fonction analyse le texte fourni pour déterminer s’il provient du menu :
    - "statistiques"
    - "carte_des_tirs"
    - ou s’il est "unknown"

    La détection est basée sur des mots-clés spécifiques à chaque menu.

    Args:
        text (str): Texte brut collé depuis VEO.

    Returns:
        str: Type détecté parmi ["statistiques", "carte_des_tirs", "unknown"]

    Examples:
        >>> detect_veo_menu_type("Possession en %\n64%\n36%")
        "statistiques"
        >>> detect_veo_menu_type("0% conversion rate.\n33% of total attempts")
        "carte_des_tirs"
    """
    lower = text.lower()

    if "possession en %" in lower or ("tir" in lower and "but" in lower):
        return "statistiques"
    elif "conversion rate" in lower and "total attempts" in lower:
        return "carte_des_tirs"
    elif all(keyword in lower for keyword in ["défense", "milieu", "attaque"]):
        if lower.count("%") == 3:
            if "zone" in lower or "possession" in lower:
                return "zone_de_possession"
            return "zone_de_passes"
    elif "enchaînements collectifs" in lower:
        return "enchaînements_collectifs"

    return "unknown"
