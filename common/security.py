from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from common.user import User, UserRole
from common.auth import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session = None  # session doit être injecté explicitement dans chaque backend
) -> User:
    if session is None:
        raise RuntimeError("session (get_db) doit être injecté par le backend")
    return AuthService.get_current_user(token, session)

def require_coach_or_admin(current_user: User):
    if current_user.role not in [UserRole.ADMIN, UserRole.COACH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user