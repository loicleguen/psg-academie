"""Module de parsing des statistiques VEO.

Ce module contient la logique principale de parsing du texte brut collé depuis
l'interface VEO (menu "Statistiques"). Il identifie dynamiquement l'équipe du
club à l'aide d'un préfixe fourni (par défaut "TEG"), détecte la position
gauche/droite des colonnes et reconstruit un dictionnaire structurant les
statistiques.

Le module applique des mesures de sécurité strictes pour prévenir les injections
HTML/JS, les attaques par déni de service (DoS), et valide rigoureusement le
format des données.

Example:
    Usage typique du module::

        from app.services.clipboard_parser import parse_veo_clipboard

        raw_text = '''
        TEG
        U19
        FCS
        N3
        But
        2
        1
        '''

        result = parse_veo_clipboard(raw_text, club_prefix="TEG")
        print(result["equipe"])  # "TEG"
        print(result["stats"]["But"]["TEG"])  # "2"

Attributes:
    MAX_LINE_LENGTH (int): Longueur maximale autorisée pour une ligne (100 caractères).
    MAX_STATS (int): Nombre maximal de statistiques autorisées (50).
    MAX_TEAM_NAME_LENGTH (int): Longueur maximale pour un nom d'équipe (30 caractères).
    ALLOWED_STATS (set): Liste blanche des noms de statistiques autorisées.
"""

import re
from typing import Any, Dict, Set

# Constantes de configuration et de sécurité
MAX_LINE_LENGTH: int = 100
MAX_STATS: int = 50
MAX_TEAM_NAME_LENGTH: int = 30

# Liste blanche des statistiques attendues depuis l'interface VEO
ALLOWED_STATS: Set[str] = {
    "But",
    "Tir",
    "Total des tentatives",
    "Corner",
    "Coup franc",
    "Touche",
    "Foul",
    "Penalty",
    "Passes effectuées",
    "Possession en %",
    "Minutes de possession",
    "Possession remportée",
}


def _normalize_value(val: str) -> str:
    """Nettoie et normalise une valeur statistique extraite.

    Cette fonction effectue les transformations suivantes :
    - Supprime les espaces inutiles
    - Remplace les virgules par des points (format international)
    - Valide le format numérique ou pourcentage
    - Lève une exception si le format est invalide

    Args:
        val: Valeur brute extraite du texte (ex: "38,5%", "123", "4").

    Returns:
        Valeur nettoyée et validée sous forme de chaîne (ex: "38.5%", "123").

    Raises:
        ValueError: Si la valeur n'est pas au format numérique ou pourcentage valide.

    Examples:
        >>> _normalize_value("38,5%")
        "38.5%"
        >>> _normalize_value("  12  ")
        "12"
        >>> _normalize_value("abc")
        ValueError: Valeur numérique invalide : 'abc'
    """
    # Nettoyer et remplacer virgule par point
    val = val.strip().replace(" ", "").replace(",", ".")

    # Traitement des pourcentages
    if val.endswith("%"):
        num = val[:-1]  # Retire le symbole %
        if re.fullmatch(r"\d+(\.\d+)?", num):
            return f"{num}%"
        else:
            raise ValueError(f"Valeur pourcentage invalide : '{val}'")

    # Traitement des valeurs numériques simples
    if re.fullmatch(r"\d+(\.\d+)?", val):
        return val

    raise ValueError(f"Valeur numérique invalide : '{val}'")


def parse_veo_clipboard(raw_text: str, club_prefix: str = "TEG") -> Dict[str, Any]:
    """Parse et structure le texte brut collé depuis VEO (menu "Statistiques").

    Le parseur identifie l'équipe du club via le préfixe fourni, détecte si elle
    est positionnée à gauche ou à droite dans l'interface, et reconstruit un
    dictionnaire des statistiques. Il applique des filtres de sécurité stricts
    pour éviter les injections, les attaques DoS, et les entrées malformées.

    Mesures de sécurité appliquées:
        - Limitation de la longueur des lignes (100 caractères max)
        - Suppression des caractères HTML/JS dangereux
        - Validation stricte des formats numériques
        - Liste blanche des statistiques autorisées
        - Limite du nombre total de statistiques (50 max)
        - Validation de la longueur des noms d'équipes (30 caractères max)

    Args:
        raw_text: Texte brut collé depuis l'interface VEO, contenant les noms
            d'équipes et les statistiques sur plusieurs lignes.
        club_prefix: Préfixe permettant d'identifier l'équipe du club dans le
            texte. Par défaut "TEG".

    Returns:
        Dictionnaire structuré contenant:
            - "equipe" (str): Nom de l'équipe du club
            - "adversaire" (str): Nom de l'équipe adverse
            - "stats" (Dict[str, Dict[str, str]]): Dictionnaire imbriqué des
              statistiques où chaque clé est un nom de statistique pointant
              vers un dictionnaire {nom_equipe: valeur}

    Raises:
        ValueError: Si les données sont insuffisantes, mal structurées, ou si
            aucune équipe ne correspond au préfixe fourni. Également levée si
            les noms d'équipes dépassent la longueur maximale autorisée.

    Examples:
        >>> raw_text = '''
        ... TEG
        ... U19
        ... FCS
        ... N3
        ... But
        ... 2
        ... 1
        ... Tir
        ... 5
        ... 3
        ... '''
        >>> result = parse_veo_clipboard(raw_text, club_prefix="TEG")
        >>> result["equipe"]
        'TEG'
        >>> result["adversaire"]
        'FCS'
        >>> result["stats"]["But"]["TEG"]
        '2'
        >>> result["stats"]["But"]["FCS"]
        '1'

    Note:
        Le format attendu du texte VEO est :
        - Ligne 0: Nom équipe gauche
        - Ligne 1: Catégorie équipe gauche
        - Ligne 2: Nom équipe droite
        - Ligne 3: Catégorie équipe droite
        - Lignes 4+: Triplets (Label statistique, Valeur gauche, Valeur droite)
    """
    # Nettoyage initial : découpage en lignes, suppression des espaces,
    # limitation de longueur
    lines = [
        line.strip()[:MAX_LINE_LENGTH]
        for line in raw_text.strip().splitlines()
        if line.strip()
    ]

    # Validation : minimum 7 lignes nécessaires (4 pour les équipes + 3 pour 1 stat)
    if len(lines) < 7:
        raise ValueError("Contenu trop court ou mal structuré.")

    # Suppression de caractères suspects (HTML, guillemets, scripts, etc.)
    # On conserve : lettres, chiffres, espaces, %, virgule, point, accents, tiret
    safe_lines = [re.sub(r"[^\w\s%.,\u00C0-\u017F-]", "", line) for line in lines]

    # === Extraction et identification des équipes ===
    club_gauche_nom = safe_lines[0]
    club_droite_nom = safe_lines[2]

    # Validation de la longueur des noms d'équipes (sécurité anti-DoS)
    if (
        len(club_gauche_nom) > MAX_TEAM_NAME_LENGTH
        or len(club_droite_nom) > MAX_TEAM_NAME_LENGTH
    ):
        raise ValueError("Nom d'équipe trop long")

    # Détection de la position de l'équipe du club (gauche ou droite)
    if club_gauche_nom.startswith(club_prefix):
        mon_equipe = club_gauche_nom
        adversaire = club_droite_nom
        ordre = "gauche"
    elif club_droite_nom.startswith(club_prefix):
        mon_equipe = club_droite_nom
        adversaire = club_gauche_nom
        ordre = "droite"
    else:
        raise ValueError(f"Aucune équipe ne commence par '{club_prefix}'.")

    # === Extraction des statistiques ===
    stats: Dict[str, Dict[str, str]] = {}
    i = 4  # Démarrage après les 4 lignes d'en-tête (2 équipes × 2 lignes)
    stat_count = 0

    # Parcours des triplets (label, valeur_gauche, valeur_droite)
    while i + 2 < len(safe_lines) and stat_count < MAX_STATS:
        # Normalisation du label : réduction des espaces multiples
        label = re.sub(r"\s{2,}", " ", safe_lines[i]).strip()

        # Validation du label
        if len(label) > 50 or not label.isprintable():
            i += 3
            continue

        # Vérification contre la liste blanche (sécurité)
        if label not in ALLOWED_STATS:
            i += 3
            continue

        # Extraction et normalisation des valeurs
        try:
            val_gauche = _normalize_value(safe_lines[i + 1])
            val_droite = _normalize_value(safe_lines[i + 2])
        except (ValueError, IndexError):
            # En cas d'erreur de format, on ignore cette statistique
            i += 3
            continue

        # Attribution des valeurs selon l'ordre détecté
        if ordre == "gauche":
            stats[label] = {mon_equipe: val_gauche, adversaire: val_droite}
        else:
            stats[label] = {mon_equipe: val_droite, adversaire: val_gauche}

        stat_count += 1
        i += 3

    return {"equipe": mon_equipe, "adversaire": adversaire, "stats": stats}
