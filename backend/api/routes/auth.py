"""Routes d'authentification JWT."""
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends
from backend.api.models.auth import Token, LoginRequest, User
from backend.api.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_admin,
    USERS_DB
)
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Authentification et génération de token JWT.
    
    Credentials de test :
    - admin / admin123 (admin)
    - user / user123 (utilisateur normal)
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=403,
            detail="Compte désactivé"
        )
    
    # Créer le token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "is_admin": user.get("is_admin", False)
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me", response_model=User)
async def get_me(username: str = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur courant.
    
    Nécessite un token JWT valide.
    """
    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    return {
        "id": 1,  # Mock ID
        "username": user["username"],
        "email": user["email"],
        "is_active": user["is_active"],
        "is_admin": user.get("is_admin", False),
        "created_at": user["created_at"]
    }


@router.post("/logout")
async def logout(username: str = Depends(get_current_user)):
    """
    Déconnexion (côté client, supprimer le token).
    
    Note: JWT est stateless, la déconnexion se fait côté client.
    Pour une vraie déconnexion, implémenter une blacklist de tokens.
    """
    return {"message": f"Utilisateur {username} déconnecté avec succès"}


@router.get("/admin-only")
async def admin_only_route(username: str = Depends(get_current_admin)):
    """
    Route protégée accessible uniquement aux admins.
    
    Exemple d'utilisation du middleware admin.
    """
    return {
        "message": f"Bienvenue admin {username}",
        "data": "Données sensibles réservées aux admins"
    }
