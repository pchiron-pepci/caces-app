from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base

# Import de tous les modèles
from app.models.stagiaire import Stagiaire
from app.models.testeur import Testeur
from app.models.lieu import Lieu
from app.models.session import Session
from app.models.categorie import Famille, Categorie
from app.models.habilitation_testeur import HabilitationTesteur

# Import des routers
from app.routers import stagiaires

# Création des tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CACES® Manager",
    description="Gestion des certifications CACES® - PEPCI Formation",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(stagiaires.router)

@app.get("/")
def root():
    return {
        "message": "CACES® Manager API",
        "version": "0.1.0",
        "status": "ok"
    }

@app.get("/health")
def health():
    return {"status": "ok"}