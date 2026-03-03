"""
clipboard.py

Expose une route FastAPI pour parser du contenu brut copié depuis l’interface VEO,
et le transformer en un format structuré exploitable par le frontend.

Le système détecte automatiquement le type de menu (statistiques, carte de tirs, etc.) via
des heuristiques de contenu, puis redirige le parsing vers le module adapté.

Routes:
    POST /parse-veo-clipboard: Analyse le collage VEO et retourne les données structurées.
"""

from typing import Annotated

from app.services.clipboard_parser import parse_veo_clipboard
from app.services.menu_detector import detect_veo_menu_type
from app.services.pass_location_parser import parse_veo_pass_location
from app.services.pass_sequences_parser import parse_veo_pass_sequence
from app.services.possession_zone_parser import parse_veo_possession_zone
from app.services.shotmap_parser import parse_veo_shotmap
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, constr
from app.security import require_coach_or_admin
from common.user import User


router = APIRouter()


class ClipboardInput(BaseModel):
    """
    Modèle d'entrée utilisateur pour le collage VEO.

    Attributes:
        text (str): Texte brut collé depuis l'interface VEO.
        club_prefix (str): Préfixe désignant l’équipe du club (par défaut "TEG").
    """

    text: Annotated[str, constr(strip_whitespace=True, min_length=10)]
    club_prefix: Annotated[str, constr(strip_whitespace=True, min_length=2)] = "TEG"


@router.post("/parse-veo-clipboard")
def parse_veo_clipboard_endpoint(
    data: ClipboardInput,
    current_user: User = Depends(require_coach_or_admin),
) -> dict:
    """
    Route FastAPI principale pour analyser un collage VEO (tous menus confondus).

    Détecte le menu d’origine, applique le parseur correspondant, et retourne les données
    sous format structuré.

    Raises:
        HTTPException: Si le type de menu n'est pas reconnu ou si le parsing échoue.
    """
    menu_type = detect_veo_menu_type(data.text)

    try:
        if menu_type == "statistiques":
            parsed = parse_veo_clipboard(data.text, club_prefix=data.club_prefix)
        elif menu_type == "carte_de_tirs":
            parsed = parse_veo_shotmap(data.text, club_prefix=data.club_prefix)
        elif menu_type == "emplacement_des_passes":
            parsed = parse_veo_pass_location(data.text)
        elif menu_type == "zone_de_possession":
            parsed = parse_veo_possession_zone(data.text)
        elif menu_type == "enchaînements_de_passes":
            parsed = parse_veo_pass_sequence(data.text)
        else:
            raise HTTPException(
                status_code=422, detail="Type de collage VEO non reconnu."
            )

        return {"type": menu_type, "data": parsed}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
