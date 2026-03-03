from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from fastapi import HTTPException, status
import os

from ..models.user import User, TokenData

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set for JWT security")
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

    @staticmethod
    def create_refresh_token(user_id: int, session: Session) -> str:
        """
        Crée un refresh token et le stocke en base de données
        
        Args:
            user_id: ID de l'utilisateur
            session: Session de base de données
            
        Returns:
            Token de rafraîchissement
        """
        from ..models.user import RefreshToken
        import secrets
        
        # Générer un token aléatoire sécurisé
        token = secrets.token_urlsafe(64)
        
        # Expiration dans 1 jours
        expires_at = datetime.utcnow() + timedelta(days=1)
        
        # Stocker en base
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        session.add(refresh_token)
        session.commit()
        
        return token
    
    @staticmethod
    def verify_refresh_token(token: str, session: Session) -> Optional[User]:
        """
        Vérifie un refresh token et retourne l'utilisateur associé
        
        Args:
            token: Refresh token à vérifier
            session: Session de base de données
            
        Returns:
            User si le token est valide, None sinon
        """
        from ..models.user import RefreshToken
        
        # Récupérer le refresh token depuis la DB
        statement = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False
        )
        db_token = session.exec(statement).first()
        
        if not db_token:
            return None
        
        # Vérifier l'expiration
        if db_token.expires_at < datetime.utcnow():
            return None
        
        # Récupérer l'utilisateur
        user = session.get(User, db_token.user_id)
        return user
