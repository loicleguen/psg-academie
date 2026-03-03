from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from common.user import User, UserRole
from common.auth import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def make_get_current_user(get_db, UserModel):
    """
    Factory pour les backends qui ont leur propre table User (ex: catapult).
    Vérifie le token JWT et récupère l'utilisateur depuis la DB.
    """
    from sqlmodel import select

    def get_current_user(
        token: str = Depends(oauth2_scheme),
        session=Depends(get_db),
    ):
        token_data = AuthService.verify_token(token)
        user = session.exec(
            select(UserModel).where(UserModel.email == token_data.email)
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        return user

    return get_current_user


def make_get_current_user_from_token():
    """
    Factory pour les backends sans table User (ex: veo).
    Vérifie le token JWT et retourne un objet User construit depuis le token.
    """
    def get_current_user(
        token: str = Depends(oauth2_scheme),
    ) -> User:
        token_data = AuthService.verify_token(token)
        return User(
            id=0,
            email=token_data.email,
            role=token_data.role,
        )

    return get_current_user


def make_require_coach_or_admin(get_current_user_dep):
    """
    Factory générique : prend n'importe quelle dépendance get_current_user
    et retourne une dépendance require_coach_or_admin.
    """
    def require_coach_or_admin(
        current_user=Depends(get_current_user_dep),
    ):
        if current_user.role not in [UserRole.ADMIN, UserRole.COACH]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return require_coach_or_admin
