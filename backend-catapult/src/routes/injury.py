from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import date

from ..db.database import get_session
from ..models.injury import Injury, InjuryCreate, InjuryRead, InjuryUpdate
from ..models.user import User
from ..middleware.security import get_current_user, require_admin

router = APIRouter(prefix="/players", tags=["Injuries"])


@router.get("/{player_id}/injuries", response_model=List[InjuryRead], summary="Get player injuries")
def get_player_injuries(
    player_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer toutes les blessures d'un joueur triées par date décroissante
    
    Args:
        player_id: ID du joueur
        session: Session de base de données
        current_user: Utilisateur connecté
        
    Returns:
        List[InjuryRead]: Liste des blessures
    """
    # Verify player exists
    player = session.get(User, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # Get injuries sorted by injury_date desc
    statement = select(Injury).where(Injury.user_id == player_id).order_by(Injury.injury_date.desc())
    injuries = session.exec(statement).all()
    
    return injuries


@router.post("/{player_id}/injuries", response_model=InjuryRead, status_code=status.HTTP_201_CREATED, summary="Add player injury")
def create_injury(
    player_id: int,
    injury_data: InjuryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Ajouter une blessure pour un joueur
    
    Args:
        player_id: ID du joueur
        injury_data: Données de la blessure
        session: Session de base de données
        current_user: Utilisateur connecté
        
    Returns:
        InjuryRead: Blessure créée
        
    Raises:
        HTTPException 404: Si le joueur n'existe pas
    """
    # Verify player exists
    player = session.get(User, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # Create injury
    db_injury = Injury(
        user_id=player_id,
        body_part=injury_data.body_part,
        injury_date=injury_data.injury_date,
        comment=injury_data.comment
    )
    
    session.add(db_injury)
    session.commit()
    session.refresh(db_injury)
    
    return db_injury


@router.put("/{player_id}/injuries/{injury_id}", response_model=InjuryRead, summary="Update player injury")
def update_injury(
    player_id: int,
    injury_id: int,
    injury_data: InjuryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Mettre à jour une blessure
    
    Args:
        player_id: ID du joueur
        injury_id: ID de la blessure
        injury_data: Nouvelles données
        session: Session de base de données
        current_user: Utilisateur connecté
        
    Returns:
        InjuryRead: Blessure mise à jour
        
    Raises:
        HTTPException 404: Si la blessure n'existe pas ou n'appartient pas au joueur
    """
    # Get injury
    injury = session.get(Injury, injury_id)
    if not injury or injury.user_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Injury not found"
        )
    
    # Update fields if provided
    if injury_data.body_part is not None:
        injury.body_part = injury_data.body_part
    if injury_data.injury_date is not None:
        injury.injury_date = injury_data.injury_date
    if injury_data.comment is not None:
        injury.comment = injury_data.comment
    
    session.add(injury)
    session.commit()
    session.refresh(injury)
    
    return injury


@router.delete("/{player_id}/injuries/{injury_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete player injury")
def delete_injury(
    player_id: int,
    injury_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Supprimer une blessure
    
    Args:
        player_id: ID du joueur
        injury_id: ID de la blessure
        session: Session de base de données
        current_user: Utilisateur connecté
        
    Raises:
        HTTPException 404: Si la blessure n'existe pas ou n'appartient pas au joueur
    """
    # Get injury
    injury = session.get(Injury, injury_id)
    if not injury or injury.user_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Injury not found"
        )
    
    session.delete(injury)
    session.commit()
    
    return None
