from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from datetime import timedelta

from ..db.database import get_session
from ..models.user import User, UserCreate, UserRead, UserLogin, Token, UserUpdate
from ..services.auth import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from ..middleware.security import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, session: Session = Depends(get_session)):
    """
    Enregistrer un nouvel utilisateur
    
    Args:
        user_data: Données du nouvel utilisateur
        session: Session de base de données
        
    Returns:
        UserRead: Utilisateur créé
        
    Raises:
        HTTPException 400: Si l'email existe déjà
    """
    # Vérifier si l'email existe déjà
    from sqlmodel import select
    statement = select(User).where(User.email == user_data.email)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Créer le nouvel utilisateur
    hashed_password = AuthService.get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    Se connecter et obtenir un token JWT
    
    Args:
        form_data: Formulaire OAuth2 (username = email, password)
        session: Session de base de données
        
    Returns:
        Token: Token JWT d'accès
        
    Raises:
        HTTPException 401: Si les identifiants sont incorrects
    """
    # Authentifier l'utilisateur (username = email dans OAuth2)
    user = AuthService.authenticate_user(session, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Créer le token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # en secondes
    )


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Récupérer les informations de l'utilisateur connecté
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserRead: Informations de l'utilisateur
    """
    return current_user


@router.post("/logout")
def logout():
    """
    Déconnecter l'utilisateur
    
    Note: Avec JWT, la déconnexion est gérée côté client
    en supprimant le token. Cette route est informative.
    """
    return {"message": "Successfully logged out. Please delete the token from client."}


@router.put("/me", response_model=UserRead)
def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Modifier son propre profil
    
    Args:
        user_update: Nouvelles données (email, nom, mot de passe)
        current_user: Utilisateur authentifié
        
    Returns:
        UserRead: Utilisateur mis à jour
    """
    from ..models.user import UserUpdate
    
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.password is not None:
        current_user.hashed_password = AuthService.get_password_hash(user_update.password)
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.delete("/me")
def delete_my_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Supprimer son propre compte
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        Message de confirmation
    """
    email = current_user.email
    session.delete(current_user)
    session.commit()
    return {"message": f"Account {email} deleted successfully"}


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    Modifier un utilisateur (admin uniquement)
    
    Permet de changer le rôle et le statut actif
    
    Args:
        user_id: ID de l'utilisateur à modifier
        user_update: Nouvelles données
        current_user: Admin authentifié
        
    Returns:
        UserRead: Utilisateur mis à jour
    """
    from ..models.user import UserUpdate
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.password is not None:
        user.hashed_password = AuthService.get_password_hash(user_update.password)
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    Supprimer un utilisateur (admin uniquement)
    
    Args:
        user_id: ID de l'utilisateur à supprimer
        current_user: Admin authentifié
        
    Returns:
        Message de confirmation
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    email = user.email
    session.delete(user)
    session.commit()
    return {"message": f"User {email} deleted successfully"}
