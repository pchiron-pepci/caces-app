from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.utilisateur import Utilisateur
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["Auth"])

SECRET_KEY = "pepci_caces_2025_secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 heures

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    nom: str

def verifier_mot_de_passe(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hasher_mot_de_passe(mot_de_passe):
    return pwd_context.hash(mot_de_passe)

def creer_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_utilisateur_courant(token: str = Depends(oauth2_scheme), db: DBSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Non authentifie",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if user is None or not user.actif:
        raise credentials_exception
    return user

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: DBSession = Depends(get_db)):
    user = db.query(Utilisateur).filter(Utilisateur.email == form_data.username).first()
    if not user or not verifier_mot_de_passe(form_data.password, user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    token = creer_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "nom": f"{user.prenom} {user.nom}"
    }

@router.get("/me")
def get_me(current_user: Utilisateur = Depends(get_utilisateur_courant)):
    return {
        "id": current_user.id,
        "nom": current_user.nom,
        "prenom": current_user.prenom,
        "email": current_user.email,
        "role": current_user.role
    }

class ProfilUpdate(BaseModel):
    email: Optional[str] = None
    mot_de_passe_actuel: Optional[str] = None
    nouveau_mot_de_passe: Optional[str] = None

@router.put("/profil")
def update_profil(data: ProfilUpdate, current_user: Utilisateur = Depends(get_utilisateur_courant), db: DBSession = Depends(get_db)):
    if data.email:
        current_user.email = data.email
    if data.nouveau_mot_de_passe:
        if not data.mot_de_passe_actuel:
            raise HTTPException(status_code=400, detail="Mot de passe actuel requis")
        if not verifier_mot_de_passe(data.mot_de_passe_actuel, current_user.mot_de_passe):
            raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
        current_user.mot_de_passe = hasher_mot_de_passe(data.nouveau_mot_de_passe)
    db.commit()
    return {"message": "Profil mis a jour"}