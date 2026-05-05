import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select, delete
from datetime import timedelta

from ..middleware.security import require_coach_or_admin, get_current_user, require_admin_only
from ..db.database import get_session
from ..models.user import User, UserCreate, UserRead, Token, UserUpdate, UserUpdateMe, UserRole, RefreshToken
from ..services.auth import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["Auth - Public"], summary="Register new user")
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
        role=UserRole.PLAYER,  # Par défaut, le rôle est 'player' pour les inscriptions publiques
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token, tags=["Auth - Public"], summary="Login and get JWT token")
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
        Token: Token JWT d'accès + refresh token
        
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
    
    # Créer le refresh token
    refresh_token = AuthService.create_refresh_token(user.id, session)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # en secondes
    )




@router.post("/refresh", response_model=Token, tags=["Auth - Public"], summary="Refresh access token")
def refresh_access_token(
    refresh_token: str,
    session: Session = Depends(get_session)
):
    """
    Obtenir un nouveau access token avec un refresh token
    
    Args:
        refresh_token: Token de rafraîchissement
        session: Session de base de données
        
    Returns:
        Token: Nouveau token JWT d'accès
        
    Raises:
        HTTPException 401: Si le refresh token est invalide ou expiré
    """
    # Vérifier le refresh token
    user = AuthService.verify_refresh_token(refresh_token, session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Créer un nouveau access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,  # On renvoie le même refresh token
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
@router.get("/me", response_model=UserRead, tags=["Auth - User"], summary="[Me] Get my profile")
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Récupérer les informations de l'utilisateur connecté
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserRead: Informations de l'utilisateur
    """
    return current_user


@router.post("/logout", tags=["Auth - Public"], summary="Logout (client-side)")
def logout():
    """
    Déconnecter l'utilisateur
    
    Note: Avec JWT, la déconnexion est gérée côté client
    en supprimant le token. Cette route est informative.
    """
    return {"message": "Successfully logged out. Please delete the token from client."}


@router.put("/me", response_model=UserRead, tags=["Auth - User"], summary="[Me] Update my profile")
def update_my_profile(
    user_update: UserUpdateMe,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Modifier son propre profil (nom, mot de passe et champs joueur si applicable)
    """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.password is not None:
        # Vérification de l'ancien mot de passe
        if not user_update.old_password or not AuthService.verify_password(user_update.old_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")
        current_user.hashed_password = AuthService.get_password_hash(user_update.password)

    # Gérer les champs liés au joueur si l'utilisateur est un joueur
    has_player_fields = any([
        user_update.team_id is not None,
        user_update.age is not None,
        user_update.player_name is not None,
        user_update.position is not None
    ])

    if has_player_fields:
        is_player = str(current_user.role).lower() == "player"
        if not is_player:
            raise HTTPException(status_code=400, detail="Only users with role 'player' can update player fields")
        if user_update.player_name is not None:
            current_user.player_name = user_update.player_name
        if user_update.age is not None:
            current_user.age = user_update.age
        if user_update.team_id is not None:
            current_user.team_id = user_update.team_id

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.delete("/me", tags=["Auth - User"], summary="[Me] Delete my account")
def delete_my_account(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Supprimer son propre compte
    """
    email = current_user.email
    # Supprimer les refresh tokens liés pour éviter les contraintes FK
    session.exec(delete(RefreshToken).where(RefreshToken.user_id == current_user.id))
    session.delete(current_user)
    session.commit()
    return {"message": f"Account {email} deleted successfully"}


@router.get("/users", tags=["Auth - Coach/Admin"], summary="List all users")
def get_all_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Lister tous les utilisateurs avec leurs équipes complètes (coach or admin uniquement)
    """
    from .team import get_team_full_path
    
    users = session.exec(select(User)).all()
    result = []
    
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "full_name": user.full_name,
            "player_name": user.player_name,
            "age": user.age,
            "team_id": user.team_id,
            "position": user.position,
            "created_at": user.created_at,
            "team_name": None,
            "photo_url": user.photo_url,
            "date_of_birth": user.date_of_birth,
            "adress": user.adress,
            "height": user.height,
            "weight": user.weight,
            "strong_foot": user.strong_foot,
            "phone_number": user.phone_number,
            "emergency_contact": user.emergency_contact,
        }
        
        # Ajouter le chemin complet de l'équipe pour les joueurs
        if user.team_id:
            team_path = get_team_full_path(session, user.team_id)
            if team_path:
                user_dict["team_name"] = team_path
        
        result.append(user_dict)
    
    return result


@router.get("/staff", response_model=list[UserRead], tags=["Auth - Coach/Admin"], summary="List admins and coaches")
def get_admins_and_coaches(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    stmt = select(User).where(User.role.in_([UserRole.ADMIN, UserRole.COACH]))
    return session.exec(stmt).all()


@router.get("/players-list", response_model=list[UserRead], tags=["Auth - Coach/Admin"], summary="List all players")
def get_players(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    stmt = select(User).where(User.role == UserRole.PLAYER)
    return session.exec(stmt).all()


@router.put("/users/{user_id}", tags=["Auth - Coach/Admin"], summary="Update user")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Modifier un utilisateur (coach or admin uniquement)
    Permet de changer le rôle et le statut actif.
    """
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

    # Gérer les champs joueur fournis par l'admin
    has_player_fields = any([
        user_update.team_id is not None,
        user_update.age is not None,
        user_update.player_name is not None,
        user_update.position is not None
    ])

    # Si le rôle est défini à 'player', exiger un team_id (soit fourni, soit déjà présent)
    if user_update.role is not None and str(user_update.role).lower() == "player":
        if (user_update.team_id is None) and (user.team_id is None) and not has_player_fields:
            raise HTTPException(status_code=400, detail="team_id required when assigning role 'player'")

    if has_player_fields:
        if user_update.player_name is not None:
            user.player_name = user_update.player_name
        if user_update.age is not None:
            user.age = user_update.age
        if user_update.team_id is not None:
            user.team_id = user_update.team_id
        if user_update.position is not None:
            user.position = user_update.position

    # Champs profil étendus
    if user_update.date_of_birth is not None:
        user.date_of_birth = user_update.date_of_birth
    if user_update.adress is not None:
        user.adress = user_update.adress
    if user_update.height is not None:
        user.height = user_update.height
    if user_update.weight is not None:
        user.weight = user_update.weight
    if user_update.strong_foot is not None:
        user.strong_foot = user_update.strong_foot
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number
    if user_update.emergency_contact is not None:
        user.emergency_contact = user_update.emergency_contact

    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Retourner avec le team_name complet
    from .team import get_team_full_path
    
    user_dict = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "full_name": user.full_name,
        "player_name": user.player_name,
        "age": user.age,
        "team_id": user.team_id,
        "position": user.position,
        "created_at": user.created_at,
        "team_name": None,
        "photo_url": user.photo_url,
        "date_of_birth": user.date_of_birth,
        "adress": user.adress,
        "height": user.height,
        "weight": user.weight,
        "strong_foot": user.strong_foot,
        "phone_number": user.phone_number,
        "emergency_contact": user.emergency_contact,
    }
    
    if user.team_id:
        team_path = get_team_full_path(session, user.team_id)
        if team_path:
            user_dict["team_name"] = team_path
    
    return user_dict


@router.delete("/users/{user_id}", tags=["Auth - Coach/Admin"], summary="Delete user")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Supprimer un utilisateur (coach or admin uniquement)
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    email = user.email
    # Supprimer les refresh tokens liés pour éviter les contraintes FK
    session.exec(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    session.delete(user)
    session.commit()
    return {"message": f"User {email} deleted successfully"}


@router.post("/me/photo", tags=["Auth - User"], summary="[Me] Upload profile photo")
def upload_my_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    filename = file.filename or f"{current_user.id}.jpg"
    _, ext = os.path.splitext(filename)
    os.makedirs('static/uploads/players', exist_ok=True)
    safe_name = f"{current_user.id}{ext}"
    dest_path = os.path.join('static', 'uploads', 'players', safe_name)
    with open(dest_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    current_user.photo_url = f"/static/uploads/players/{safe_name}"
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return {"photo_url": current_user.photo_url}


@router.post("/users/{user_id}/photo", tags=["Auth - Coach/Admin"], summary="Upload profile photo for a user (coach/admin)")
def upload_user_photo(
    user_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_coach_or_admin),
    session: Session = Depends(get_session)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    filename = file.filename or f"{user.id}.jpg"
    _, ext = os.path.splitext(filename)
    os.makedirs('static/uploads/players', exist_ok=True)
    safe_name = f"{user.id}{ext}"
    dest_path = os.path.join('static', 'uploads', 'players', safe_name)
    with open(dest_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    user.photo_url = f"/static/uploads/players/{safe_name}"
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"photo_url": user.photo_url}

# backend-catapult/src/routes/auth.py

@router.post(
    "/users/{user_id}/reset-password",
    tags=["Auth - Admin"],
    summary="Reset user password to first name uppercased",
)
def reset_user_password(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin_only),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.full_name:
        raise HTTPException(status_code=400, detail="full_name is required")

    first_name = user.full_name.strip().split()[0].upper()
    user.hashed_password = AuthService.get_password_hash(first_name)

    session.add(user)
    session.commit()
    session.refresh(user)

    return {"message": "Password reset successfully", "password": first_name}
