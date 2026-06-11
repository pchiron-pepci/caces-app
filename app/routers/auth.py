from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.utilisateur import Utilisateur
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
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

ROLES_VALIDES = {"admin", "formateur", "testeur", "utilisateur", "terrain"}

class UtilisateurCreate(BaseModel):
    nom: str
    prenom: str
    email: str
    mot_de_passe: str
    role: str = "testeur"
    telephone: Optional[str] = None
    role_referent: Optional[str] = None

    @validator('role')
    def role_valide(cls, v):
        if v not in ROLES_VALIDES:
            raise ValueError(f"Role invalide. Valeurs acceptées : {', '.join(ROLES_VALIDES)}")
        return v

class UtilisateurUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    telephone: Optional[str] = None
    role_referent: Optional[str] = None
    actif: Optional[bool] = None
    mot_de_passe: Optional[str] = None

    @validator('role')
    def role_valide(cls, v):
        if v is not None and v not in ROLES_VALIDES:
            raise ValueError(f"Role invalide. Valeurs acceptées : {', '.join(ROLES_VALIDES)}")
        return v

@router.get("/utilisateurs")
def liste_utilisateurs(current_user: Utilisateur = Depends(get_utilisateur_courant), db: DBSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    return db.query(Utilisateur).all()

@router.post("/utilisateurs")
def creer_utilisateur(data: UtilisateurCreate, current_user: Utilisateur = Depends(get_utilisateur_courant), db: DBSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    existing = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email deja utilise")
    u = Utilisateur(
        nom=data.nom,
        prenom=data.prenom,
        email=data.email,
        mot_de_passe=hasher_mot_de_passe(data.mot_de_passe),
        role=data.role,
        telephone=data.telephone,
        role_referent=data.role_referent,
        actif=True
    )
    db.add(u)
    db.commit()
    return {"message": "Utilisateur cree", "id": u.id}

@router.put("/utilisateurs/{id}")
def modifier_utilisateur(id: int, data: UtilisateurUpdate, current_user: Utilisateur = Depends(get_utilisateur_courant), db: DBSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    u = db.query(Utilisateur).filter(Utilisateur.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouve")
    if data.nom: u.nom = data.nom
    if data.prenom: u.prenom = data.prenom
    if data.email: u.email = data.email
    if data.role: u.role = data.role
    if data.telephone is not None: u.telephone = data.telephone or None
    if data.role_referent is not None: u.role_referent = data.role_referent or None
    if data.actif is not None: u.actif = data.actif
    if data.mot_de_passe: u.mot_de_passe = hasher_mot_de_passe(data.mot_de_passe)
    db.commit()
    return {"message": "Utilisateur mis a jour"}

@router.delete("/utilisateurs/{id}")
def supprimer_utilisateur(id: int, current_user: Utilisateur = Depends(get_utilisateur_courant), db: DBSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acces refuse")
    if id == current_user.id:
        raise HTTPException(status_code=400, detail="Impossible de supprimer son propre compte")
    u = db.query(Utilisateur).filter(Utilisateur.id == id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur non trouve")
    u.actif = False
    db.commit()
    return {"message": "Utilisateur desactive"}