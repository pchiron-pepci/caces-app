import math
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

from app.routers import stagiaires, testeurs, admin, sessions, upload, auth
from app.models.utilisateur import Utilisateur

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
app.include_router(upload.router)
app.include_router(auth.router)

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

@app.get("/admin/images")
def page_admin_images(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_images.html",
        context={"page": "admin"}
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

    session_candidats = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.actif == True
    ).all()
    for sc in session_candidats:
        sc.stagiaire = db.query(Stagiaire).filter(Stagiaire.id == sc.stagiaire_id).first()

    epreuves = db.query(SessionEpreuve).filter(SessionEpreuve.session_id == session_id).all()

    famille = db.query(Famille).filter(Famille.code == session.famille).first()
    categories_obj = db.query(Categorie).filter(
        Categorie.famille_id == (famille.id if famille else 0),
        Categorie.pepci_habilite == True,
        Categorie.actif == True
    ).all() if famille else []
    categories = [c.code for c in categories_obj]
    ut_par_cat = {c.code: c.ut_pratique for c in categories_obj}

    epreuves_map = {}
    for e in epreuves:
        testeur = db.query(Testeur).filter(Testeur.id == e.testeur_id).first()
        e.testeur_nom = f"{testeur.nom} {testeur.prenom}" if testeur else "?"
        epreuves_map[(e.stagiaire_id, e.categorie)] = e

    ut_candidat = {}
    for e in epreuves:
        ut_candidat[e.stagiaire_id] = ut_candidat.get(e.stagiaire_id, 0) + e.ut

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

        jtcs = db.query(JourTestCandidat).filter(
            JourTestCandidat.jour_test_id == j.id,
            JourTestCandidat.actif == True
        ).all()
        j.candidats_ids = [jtc.stagiaire_id for jtc in jtcs]
        j.candidats_categories = {
            jtc.stagiaire_id: jtc.categories.split(",") if jtc.categories else []
            for jtc in jtcs
        }
        j.identites_verifiees = {
            jtc.stagiaire_id: jtc.identite_verifiee
            for jtc in jtcs
        }

        if j.type == 'pratique':
            total_ut = 0
            for jtc in jtcs:
                cats = jtc.categories.split(",") if jtc.categories else []
                for cat in cats:
                    cat = cat.strip()
                    if cat:
                        total_ut += ut_par_cat.get(cat, 1.0)
            nb_testeurs = math.ceil(total_ut / 6) if total_ut > 0 else 1
            j.total_ut = round(total_ut, 1)
            j.nb_testeurs = nb_testeurs
            j.ut_libres = round((nb_testeurs * 6) - total_ut, 1)
        else:
            j.total_ut = 0
            j.nb_testeurs = 0
            j.ut_libres = 0

    ut_planifie_candidat = {}
    for j in jours_test:
        if j.type == 'pratique':
            for stagiaire_id, cats in j.candidats_categories.items():
                for cat in cats:
                    cat = cat.strip()
                    if cat:
                        ut_planifie_candidat[stagiaire_id] = round(
                            ut_planifie_candidat.get(stagiaire_id, 0) + ut_par_cat.get(cat, 1.0), 1
                        )

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
            "ut_planifie_candidat": ut_planifie_candidat,
            "ut_testeurs": ut_testeurs,
            "jours_test": jours_test,
            "resultats_theorie_par_jour": resultats_theorie_par_jour,
            "resultats_theorie": resultats_theorie,
            "equipements": equipements,
            "stagiaires": stagiaires,
            "testeurs": testeurs_list
        }
    )

@app.get("/sessions/{session_id}/theorie/{stagiaire_id}/detail")
def page_detail_theorie(request: Request, session_id: int, stagiaire_id: int, jour_id: int = None):
    db = SessionLocal()

    query = db.query(ResultatTheorie).filter(
        ResultatTheorie.session_id == session_id,
        ResultatTheorie.stagiaire_id == stagiaire_id
    )
    if jour_id:
        query = query.filter(ResultatTheorie.jour_test_id == jour_id)
    rt = query.order_by(ResultatTheorie.id.desc()).first()

    if not rt:
        db.close()
        return {"error": "Resultat non trouve"}

    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()

    reponses_grille = db.query(ReponseGrille).filter(
        ReponseGrille.grille_id == rt.grille_id
    ).order_by(ReponseGrille.theme, ReponseGrille.numero_question).all()

    import json
    reponses_candidat = json.loads(rt.reponses_json) if rt.reponses_json else {}

    detail_themes = {}
    for r in reponses_grille:
        t = str(r.theme)
        if t not in detail_themes:
            detail_themes[t] = []
        candidat_reponses = reponses_candidat.get(t, [])
        q_idx = r.numero_question - 1
        reponse_candidat = candidat_reponses[q_idx] if q_idx < len(candidat_reponses) else None
        correcte = reponse_candidat is not None and reponse_candidat == r.reponse_correcte
        detail_themes[t].append({
            "numero": r.numero_question,
            "texte": r.texte_question,
            "reponse_correcte": r.reponse_correcte,
            "reponse_candidat": reponse_candidat,
            "correcte": correcte,
            "points": r.points
        })

    db.close()
    return templates.TemplateResponse(
        request=request,
        name="detail_theorie.html",
        context={
            "stagiaire": stagiaire,
            "session_id": session_id,
            "rt": rt,
            "detail_themes": detail_themes,
            "theme_noms": {
                "1": "Connaissances generales",
                "2": "Technologie et stabilite",
                "3": "Exploitation",
                "4": "Circulation",
                "5": "Fin de poste"
            }
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

@app.get("/statistiques")
def page_statistiques(request: Request):
    db = SessionLocal()
    from datetime import datetime
    annee = datetime.now().year

    grilles = db.query(GrilleTheorie).filter(GrilleTheorie.actif == True).all()
    total = db.query(UtilisationGrille).filter(UtilisationGrille.annee == annee).count()

    stats_grilles = []
    for g in grilles:
        count = db.query(UtilisationGrille).filter(
            UtilisationGrille.grille_id == g.id,
            UtilisationGrille.annee == annee
        ).count()
        pct = round(count / total * 100, 1) if total > 0 else 0
        statut = "OK"
        if pct < 10 and total > 0:
            statut = "SOUS"
        elif pct > 30:
            statut = "SUR"
        stats_grilles.append({
            "numero": g.numero,
            "famille": g.famille,
            "count": count,
            "pct": pct,
            "statut": statut
        })

    historique = db.query(UtilisationGrille).filter(
        UtilisationGrille.annee == annee
    ).order_by(UtilisationGrille.id.desc()).all()

    historique_detail = []
    for u in historique:
        g = db.query(GrilleTheorie).filter(GrilleTheorie.id == u.grille_id).first()
        s = db.query(Session).filter(Session.id == u.session_id).first()
        j = db.query(JourTest).filter(
            JourTest.session_id == u.session_id,
            JourTest.grille_id == u.grille_id
        ).first()
        historique_detail.append({
            "grille_numero": str(g.numero) if g else "—",
            "session_ref": str(s.reference) if s else "—",
            "date": str(j.date) if j and j.date else "—"
        })

    db.close()
    return templates.TemplateResponse(
        request=request,
        name="statistiques.html",
        context={
            "page": "statistiques",
            "annee": annee,
            "total": total,
            "stats_grilles": stats_grilles,
            "historique": historique_detail
        }
    )

@app.post("/api/statistiques/reset-grilles")
def reset_compteurs_grilles():
    db = SessionLocal()
    nb = db.query(UtilisationGrille).count()
    db.query(UtilisationGrille).delete()
    db.commit()
    db.close()
    return {"message": f"{nb} utilisations supprimees"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/login")
def page_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )