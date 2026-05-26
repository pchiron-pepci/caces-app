from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import engine, Base, SessionLocal

from app.models.stagiaire import Stagiaire
from app.models.testeur import Testeur
from app.models.lieu import Lieu
from app.models.session import Session
from app.models.categorie import Famille, Categorie
from app.models.habilitation_testeur import HabilitationTesteur

from app.routers import stagiaires, testeurs

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CACES® Manager",
    description="Gestion des certifications CACES® - PEPCI Formation",
    version="0.1.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stagiaires.router)
app.include_router(testeurs.router)

@app.get("/")
def dashboard(request: Request):
    db = SessionLocal()
    testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
    stats = {
        "stagiaires": db.query(Stagiaire).filter(Stagiaire.actif == 1).count(),
        "cartes": 0,
        "sessions": db.query(Session).count(),
        "expirations": 0
    }
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page": "dashboard",
            "stats": stats,
            "testeurs": testeurs_list
        }
    )

@app.get("/stagiaires")
def page_stagiaires(request: Request):
    db = SessionLocal()
    liste = db.query(Stagiaire).filter(Stagiaire.actif == 1).all()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="stagiaires.html",
        context={
            "page": "stagiaires",
            "stagiaires": liste
        }
    )

@app.get("/testeurs")
def page_testeurs(request: Request):
    db = SessionLocal()
    liste = db.query(Testeur).filter(Testeur.actif == True).all()
    for t in liste:
        t.habilitations = db.query(HabilitationTesteur).filter(
            HabilitationTesteur.testeur_id == t.id,
            HabilitationTesteur.actif == True
        ).all()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="testeurs.html",
        context={
            "page": "testeurs",
            "testeurs": liste
        }
    )

@app.get("/health")
def health():
    return {"status": "ok"}