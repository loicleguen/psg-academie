import os
from jose import JWTError, jwt
from fastapi import HTTPException, status
from common.user import User, UserRole, TokenData

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set for JWT security")
ALGORITHM = "HS256"

class AuthService:
    @staticmethod
    def verify_token(token: str) -> TokenData:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            role: str = payload.get("role")
            if email is None:
                raise credentials_exception
            return TokenData(email=email, role=role)
        except JWTError:
            raise credentials_exception

    @staticmethod
    def get_current_user(token: str, session) -> User:
        from sqlmodel import select  # lazy import: only needed by backends that use SQLModel
        token_data = AuthService.verify_token(token)
        statement = select(User).where(User.email == token_data.email)
        user = session.exec(statement).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
