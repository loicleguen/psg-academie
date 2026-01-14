from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from fastapi import HTTPException, status

from ..models.user import User, TokenData

# Configuration
SECRET_KEY = "YOUR_SECRET_KEY_CHANGE_THIS_IN_PRODUCTION"  # TODO: Mettre dans .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Context pour hasher les mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service d'authentification JWT"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifie si un mot de passe correspond au hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash un mot de passe avec bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Crée un JWT access token
        
        Args:
            data: Données à encoder dans le token (email, role, etc.)
            expires_delta: Durée de validité du token
            
        Returns:
            Token JWT encodé
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """
        Vérifie et décode un JWT token
        
        Args:
            token: Token JWT à vérifier
            
        Returns:
            TokenData avec les informations de l'utilisateur
            
        Raises:
            HTTPException: Si le token est invalide ou expiré
        """
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
    def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
        """
        Authentifie un utilisateur avec email et mot de passe
        
        Args:
            session: Session SQLModel
            email: Email de l'utilisateur
            password: Mot de passe en clair
            
        Returns:
            User si authentifié, None sinon
        """
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        
        if not user:
            return None
        
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        
        return user
