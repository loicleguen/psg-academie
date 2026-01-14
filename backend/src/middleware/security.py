from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from typing import List

from ..db.database import get_session
from ..models.user import User, UserRole
from ..services.auth import AuthService

# OAuth2 scheme pour récupérer le token depuis le header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    Récupère l'utilisateur actuel à partir du token JWT
    
    Args:
        token: Token JWT depuis le header Authorization
        session: Session de base de données
        
    Returns:
        User authentifié
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Vérifier et décoder le token
    token_data = AuthService.verify_token(token)
    
    # Récupérer l'utilisateur depuis la base de données
    statement = select(User).where(User.email == token_data.email)
    user = session.exec(statement).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Récupère l'utilisateur actuel s'il est actif
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        User actif
        
    Raises:
        HTTPException: Si l'utilisateur est inactif
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: List[UserRole]):
    """
    Decorator pour vérifier que l'utilisateur a un rôle autorisé
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(user: User = Depends(require_role([UserRole.ADMIN]))):
            ...
    
    Args:
        allowed_roles: Liste des rôles autorisés
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker


# Raccourcis pour les rôles courants
require_admin = require_role([UserRole.ADMIN])
require_coach_or_admin = require_role([UserRole.COACH, UserRole.ADMIN])
require_analyst_or_above = require_role([UserRole.ANALYST, UserRole.COACH, UserRole.ADMIN])
