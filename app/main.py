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
from app.models.lieu_habilitation import LieuHabilitation
from app.models.session_candidat import SessionCandidat
from app.models.session_epreuve import SessionEpreuve
from app.models.equipement import Equipement
from app.models.jour_test import JourTest, JourTestCandidat, ResultatTheorie
from app.models.grille_theorie import GrilleTheorie, ReponseGrille, UtilisationGrille

from app.routers import stagiaires, testeurs, admin, sessions

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
app.include_router(admin.router)
app.include_router(sessions.router)

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

@app.get("/admin")
def page_admin(request: Request):
    db = SessionLocal()
    familles = db.query(Famille).filter(Famille.actif == True).all()
    categories_raw = db.query(Categorie).filter(Categorie.actif == True).all()
    testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
    lieux = db.query(Lieu).all()
    for t in testeurs_list:
        t.habilitations = db.query(HabilitationTesteur).filter(
            HabilitationTesteur.testeur_id == t.id
        ).all()
    for l in lieux:
        habs = db.query(LieuHabilitation).filter(
            LieuHabilitation.lieu_id == l.id,
            LieuHabilitation.actif == True
        ).all()
        familles_dict = {}
        for h in habs:
            if h.famille not in familles_dict:
                familles_dict[h.famille] = []
            familles_dict[h.famille].append(h.categorie)
        l.habilitations = [
            {"famille": f, "categories": ", ".join(cats)}
            for f, cats in familles_dict.items()
        ]
    categories = []
    for c in categories_raw:
        f = db.query(Famille).filter(Famille.id == c.famille_id).first()
        c.famille_code = f.code if f else "?"
        categories.append(c)
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "page": "admin",
            "familles": familles,
            "categories": categories,
            "testeurs": testeurs_list,
            "lieux": lieux
        }
    )

@app.get("/sessions")
def page_sessions(request: Request):
    db = SessionLocal()
    liste = db.query(Session).order_by(Session.id.desc()).all()
    lieux = db.query(Lieu).filter(Lieu.actif == True).all()
    familles = db.query(Famille).filter(Famille.actif == True).all()
    testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="sessions.html",
        context={
            "page": "sessions",
            "sessions": liste,
            "lieux": lieux,
            "familles": familles,
            "testeurs": testeurs_list
        }
    )

@app.get("/sessions/{session_id}")
def page_session_detail(request: Request, session_id: int):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        db.close()
        return templates.TemplateResponse(
            request=request,
            name="sessions.html",
            context={"page": "sessions", "sessions": [], "lieux": [], "familles": [], "testeurs": []}
        )

    lieu = db.query(Lieu).filter(Lieu.id == session.lieu_id).first()

    # Candidats
    session_candidats = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.actif == True
    ).all()
    for sc in session_candidats:
        sc.stagiaire = db.query(Stagiaire).filter(Stagiaire.id == sc.stagiaire_id).first()

    # Epreuves pratiques
    epreuves = db.query(SessionEpreuve).filter(SessionEpreuve.session_id == session_id).all()

    # Catégories
    famille = db.query(Famille).filter(Famille.code == session.famille).first()
    categories_obj = db.query(Categorie).filter(
        Categorie.famille_id == (famille.id if famille else 0),
        Categorie.pepci_habilite == True,
        Categorie.actif == True
    ).all() if famille else []
    categories = [c.code for c in categories_obj]
    ut_par_cat = {c.code: c.ut_pratique for c in categories_obj}

    # Map épreuves
    epreuves_map = {}
    for e in epreuves:
        testeur = db.query(Testeur).filter(Testeur.id == e.testeur_id).first()
        e.testeur_nom = f"{testeur.nom} {testeur.prenom}" if testeur else "?"
        epreuves_map[(e.stagiaire_id, e.categorie)] = e

    # UT par candidat
    ut_candidat = {}
    for e in epreuves:
        ut_candidat[e.stagiaire_id] = ut_candidat.get(e.stagiaire_id, 0) + e.ut

    # UT par testeur
    ut_testeurs = {}
    for e in epreuves:
        if e.testeur_id not in ut_testeurs:
            testeur = db.query(Testeur).filter(Testeur.id == e.testeur_id).first()
            ut_testeurs[e.testeur_id] = {
                "nom": f"{testeur.nom} {testeur.prenom}" if testeur else "?",
                "ut_pratique": 0,
                "categories": {},
                "est_principal": False
            }
        ut_testeurs[e.testeur_id]["ut_pratique"] += e.ut
        cat = e.categorie
        if cat not in ut_testeurs[e.testeur_id]["categories"]:
            ut_testeurs[e.testeur_id]["categories"][cat] = 0
        ut_testeurs[e.testeur_id]["categories"][cat] += 1

    # Jours de test
    jours_test = db.query(JourTest).filter(
        JourTest.session_id == session_id,
        JourTest.actif == True
    ).order_by(JourTest.date).all()

    for j in jours_test:
        if j.testeur_id:
            t = db.query(Testeur).filter(Testeur.id == j.testeur_id).first()
            j.testeur_nom = f"{t.nom} {t.prenom}" if t else "?"
        else:
            j.testeur_nom = "—"
        if j.grille_id:
            g = db.query(GrilleTheorie).filter(GrilleTheorie.id == j.grille_id).first()
            j.grille_numero = g.numero if g else "?"
        else:
            j.grille_numero = None
        j.candidats_ids = [
            jtc.stagiaire_id for jtc in db.query(JourTestCandidat).filter(
                JourTestCandidat.jour_test_id == j.id,
                JourTestCandidat.actif == True
            ).all()
        ]

    # Résultats théorie par jour (pour affichage dans chaque bloc jour)
    resultats_theorie_par_jour = {}
    for j in jours_test:
        if j.type == 'theorie':
            resultats_jour = {}
            for sc in session_candidats:
                rt = db.query(ResultatTheorie).filter(
                    ResultatTheorie.jour_test_id == j.id,
                    ResultatTheorie.stagiaire_id == sc.stagiaire_id
                ).order_by(ResultatTheorie.id.desc()).first()
                resultats_jour[sc.stagiaire_id] = rt
            resultats_theorie_par_jour[j.id] = resultats_jour

    # Résultats théorie pour tableau pratique (meilleur résultat)
    resultats_theorie = {}
    for sc in session_candidats:
        rt = db.query(ResultatTheorie).filter(
            ResultatTheorie.session_id == session_id,
            ResultatTheorie.stagiaire_id == sc.stagiaire_id,
            ResultatTheorie.obtenue == True
        ).order_by(ResultatTheorie.id.asc()).first()
        if not rt:
            rt = db.query(ResultatTheorie).filter(
                ResultatTheorie.session_id == session_id,
                ResultatTheorie.stagiaire_id == sc.stagiaire_id
            ).order_by(ResultatTheorie.id.desc()).first()
        resultats_theorie[sc.stagiaire_id] = rt

    # Equipements
    equipements = db.query(Equipement).filter(
        Equipement.session_id == session_id,
        Equipement.actif == True
    ).order_by(Equipement.numero).all()

    stagiaires = db.query(Stagiaire).filter(Stagiaire.actif == 1).all()
    testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()

    db.close()
    return templates.TemplateResponse(
        request=request,
        name="session_detail.html",
        context={
            "page": "sessions",
            "session": session,
            "lieu": lieu,
            "session_candidats": session_candidats,
            "categories": categories,
            "ut_par_cat": ut_par_cat,
            "epreuves_map": epreuves_map,
            "ut_candidat": ut_candidat,
            "ut_testeurs": ut_testeurs,
            "jours_test": jours_test,
            "resultats_theorie_par_jour": resultats_theorie_par_jour,
            "resultats_theorie": resultats_theorie,
            "equipements": equipements,
            "stagiaires": stagiaires,
            "testeurs": testeurs_list
        }
    )

@app.get("/test/theorie/{session_id}/{jour_id}")
def page_test_theorie(request: Request, session_id: int, jour_id: int):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not session or not jour:
        db.close()
        return {"error": "Non trouve"}
    grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == jour.grille_id).first()
    candidats_ids = [
        jtc.stagiaire_id for jtc in db.query(JourTestCandidat).filter(
            JourTestCandidat.jour_test_id == jour_id,
            JourTestCandidat.actif == True
        ).all()
    ]
    session_candidats = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.stagiaire_id.in_(candidats_ids),
        SessionCandidat.actif == True
    ).all()
    for sc in session_candidats:
        sc.stagiaire = db.query(Stagiaire).filter(Stagiaire.id == sc.stagiaire_id).first()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="test_theorie.html",
        context={
            "session_id": session_id,
            "jour_id": jour_id,
            "grille_id": jour.grille_id,
            "grille_numero": grille.numero if grille else "?",
            "session_candidats": session_candidats
        }
    )

@app.get("/health")
def health():
    return {"status": "ok"}