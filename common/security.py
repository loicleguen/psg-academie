from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from common.user import User, UserRole
from common.auth import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    """
    Sélectionne dynamiquement la bonne fonction de session selon le backend.
    """
    try:
        # Backend catapult
        from backend_catapult.src.db.database import get_session
        yield from get_session()
    except ImportError:
        # Backend veo
        from app.db.session import get_db as veo_get_db
        yield from veo_get_db()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session = Depends(get_db)
) -> User:
    return AuthService.get_current_user(token, session)

def require_coach_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.COACH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user