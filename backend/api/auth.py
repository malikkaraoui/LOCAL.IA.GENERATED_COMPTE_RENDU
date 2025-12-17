"""Utilitaires JWT et authentification."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib

from backend.config import settings

# JWT bearer
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash un mot de passe (SHA256 pour les tests)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe."""
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token JWT.
    
    Args:
        data: Données à encoder dans le token
        expires_delta: Durée de validité du token
        
    Returns:
        Token JWT encodé
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Décode et valide un token JWT.
    
    Args:
        token: Token JWT à décoder
        
    Returns:
        Payload du token
        
    Raises:
        HTTPException: Si le token est invalide
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Dependency pour obtenir l'utilisateur courant depuis le token.
    
    Args:
        credentials: Credentials HTTP Bearer
        
    Returns:
        Username de l'utilisateur
        
    Raises:
        HTTPException: Si le token est invalide
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Dependency pour vérifier que l'utilisateur est admin.
    
    Args:
        credentials: Credentials HTTP Bearer
        
    Returns:
        Username de l'admin
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas admin
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    username: str = payload.get("sub")
    is_admin: bool = payload.get("is_admin", False)
    
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Droits administrateur requis"
        )
    
    return username


# Store utilisateurs en mémoire (remplacer par DB en production)
USERS_DB = {
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # admin123 en SHA256
        "is_active": True,
        "is_admin": True,
        "created_at": datetime.utcnow()
    },
    "user": {
        "username": "user",
        "email": "user@example.com",
        "hashed_password": "04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",  # user123 en SHA256
        "is_active": True,
        "is_admin": False,
        "created_at": datetime.utcnow()
    }
}


def get_user(username: str) -> Optional[dict]:
    """Récupère un utilisateur depuis le store."""
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authentifie un utilisateur.
    
    Args:
        username: Nom d'utilisateur
        password: Mot de passe en clair
        
    Returns:
        User dict si authentification réussie, None sinon
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
