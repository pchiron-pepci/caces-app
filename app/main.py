import math
import json
from fastapi import FastAPI, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base, SessionLocal, get_db
from sqlalchemy.orm import Session as DBSession

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
from app.models.association_log import AssociationLog
from app.models.document_officiel import DocumentOfficiel
from app.models.carte_testeur import CarteTesteur
from app.models.config_organisme import ConfigOrganisme
from app.models.habilitation_option import HabilitationOption
from app.models.non_conformite import NonConformite
from app.models.option_categorie import OptionCategorie
from app.models.caces_obtenu import CacesObtenu
from app.models.carte_caces import CarteCaces

from sqlalchemy import text, or_
from app.routers import stagiaires, testeurs, admin, sessions, upload, auth, statistiques
from app.routers import non_conformites
from app.routers import caces_obtenus
from app.routers import cartes_caces
from app.routers import dev
from app.models.utilisateur import Utilisateur

Base.metadata.create_all(bind=engine)

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE document_officiel ADD COLUMN IF NOT EXISTS date_validite TIMESTAMP"))
        _conn.execute(text("ALTER TABLE document_officiel DROP COLUMN IF EXISTS date_upload"))
        _conn.execute(text("ALTER TABLE document_officiel ADD COLUMN IF NOT EXISTS numero_certificat VARCHAR(100)"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE document_officiel ADD COLUMN IF NOT EXISTS contenu_pdf TEXT"))
        _conn.execute(text("ALTER TABLE document_officiel DROP COLUMN IF EXISTS url"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS carte_pdf TEXT"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS carte_nom_fichier VARCHAR"))
        _conn.execute(text("ALTER TABLE testeurs DROP COLUMN IF EXISTS carte_url"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS attestation_prevention_pdf TEXT"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS attestation_prevention_nom VARCHAR"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS attestation_prevention_date DATE"))
        _conn.execute(text("ALTER TABLE testeurs DROP COLUMN IF EXISTS attestation_prevention_url"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS role_referent VARCHAR"))
        _conn.execute(text("ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS telephone VARCHAR"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS visite_medicale_pdf TEXT"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS visite_medicale_nom VARCHAR"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS visite_medicale_date DATE"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS evaluation_pdf TEXT"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS evaluation_nom VARCHAR"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS evaluation_date DATE"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS autorisation_conduite_pdf TEXT"))
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS autorisation_conduite_nom VARCHAR"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS etat VARCHAR(20) DEFAULT 'actif'"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS config_organisme (
                id SERIAL PRIMARY KEY,
                nom_organisme VARCHAR(200),
                logo_base64 TEXT,
                logo_nom VARCHAR(200)
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS audit_interne_date DATE"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS audit_externe_date DATE"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS revue_direction_date DATE"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS option_categorie (
                id SERIAL PRIMARY KEY,
                famille VARCHAR(10) NOT NULL,
                categorie VARCHAR(10) NOT NULL,
                code_option VARCHAR(10) NOT NULL,
                libelle_option VARCHAR(100) NOT NULL
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS habilitation_option (
                id SERIAL PRIMARY KEY,
                habilitation_id INTEGER NOT NULL REFERENCES habilitations_testeurs(id),
                code_option VARCHAR(10) NOT NULL
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS non_conformites (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                declarant_id INTEGER REFERENCES utilisateurs(id),
                origine VARCHAR(50) NOT NULL,
                type_nc VARCHAR(30) NOT NULL,
                titre VARCHAR(200) NOT NULL,
                description TEXT,
                action_preventive TEXT,
                action_corrective TEXT,
                justificatif_pdf TEXT,
                justificatif_nom VARCHAR(200),
                statut VARCHAR(20) NOT NULL DEFAULT 'ouvert',
                date_cloture DATE,
                session_id INTEGER REFERENCES sessions(id),
                testeur_id INTEGER REFERENCES testeurs(id),
                stagiaire_id INTEGER REFERENCES stagiaires(id)
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE non_conformites ADD COLUMN IF NOT EXISTS reference VARCHAR(20) UNIQUE"))
        _conn.execute(text("ALTER TABLE non_conformites ADD COLUMN IF NOT EXISTS nature VARCHAR(30)"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS carte_testeur (
                id SERIAL PRIMARY KEY,
                testeur_id INTEGER NOT NULL REFERENCES testeurs(id),
                famille VARCHAR(50) NOT NULL,
                nom_fichier VARCHAR(200) NOT NULL,
                contenu_pdf TEXT,
                date_upload TIMESTAMP DEFAULT NOW(),
                actif BOOLEAN DEFAULT TRUE
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE jour_test_candidats ADD COLUMN IF NOT EXISTS options_planifiees TEXT"))
        _conn.execute(text("ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS options_obtenues VARCHAR(200)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS pin_formateur VARCHAR(20) DEFAULT '1234'"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS prochain_numero_caces INTEGER DEFAULT 1"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS adresse TEXT"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS siret VARCHAR(20)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS email VARCHAR(200)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS telephone VARCHAR(50)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signataire_nom VARCHAR(100)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signataire_prenom VARCHAR(100)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signataire_qualite VARCHAR(100)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signature_base64 TEXT"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signature_nom VARCHAR(200)"))
        _conn.execute(text("ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS url_verification_caces VARCHAR(500)"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS motif_annulation TEXT"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS bloque BOOLEAN NOT NULL DEFAULT FALSE"))
        _conn.execute(text("ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS bloque BOOLEAN NOT NULL DEFAULT FALSE"))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS carte_caces (
                id SERIAL PRIMARY KEY,
                stagiaire_id INTEGER NOT NULL REFERENCES stagiaires(id),
                famille VARCHAR(20) NOT NULL,
                numero_carte VARCHAR(30) UNIQUE NOT NULL,
                date_generation DATE NOT NULL,
                statut VARCHAR(20) NOT NULL DEFAULT 'en_preparation',
                motif_annulation VARCHAR(500)
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS caces_obtenus (
                id SERIAL PRIMARY KEY,
                stagiaire_id INTEGER NOT NULL REFERENCES stagiaires(id),
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                famille VARCHAR(10) NOT NULL,
                categorie VARCHAR(10) NOT NULL,
                options_obtenues VARCHAR(200),
                date_obtention DATE NOT NULL,
                date_echeance DATE NOT NULL,
                numero_ordre INTEGER UNIQUE,
                statut VARCHAR(20) NOT NULL DEFAULT 'a_valider',
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT uq_caces_obtenu UNIQUE(stagiaire_id, session_id, categorie)
            )
        """))
        _conn.commit()
except Exception:
    pass

try:
    with engine.connect() as _conn:
        _conn.execute(text("ALTER TABLE carte_caces ADD COLUMN IF NOT EXISTS caces_json TEXT"))
        _conn.commit()
except Exception:
    pass

app = FastAPI(
    title="NORYX Engins",
    description="Pilotage CACES® & Autorisation de conduite — PEPCI Formation",
    version="0.1.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
from app.templates_instance import templates

def _get_nom_organisme():
    try:
        db = SessionLocal()
        config = db.query(ConfigOrganisme).first()
        db.close()
        return config.nom_organisme if config and config.nom_organisme else "PEPCI Formation"
    except Exception:
        return "PEPCI Formation"

def _get_logo_organisme():
    try:
        db = SessionLocal()
        config = db.query(ConfigOrganisme).first()
        db.close()
        if config and config.logo_base64 and config.logo_nom:
            ext = config.logo_nom.rsplit('.', 1)[-1].lower()
            mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
            return f"data:{mime};base64,{config.logo_base64}"
        return ""
    except Exception:
        return ""

def _get_numero_certificat():
    try:
        db = SessionLocal()
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == 'certificat_organisme').first()
        db.close()
        return doc.numero_certificat if doc and doc.numero_certificat else ""
    except Exception:
        return ""

def _get_config_organisme():
    try:
        db = SessionLocal()
        config = db.query(ConfigOrganisme).first()
        db.close()
        return config
    except Exception:
        return None

def _get_date_validite_certificat():
    try:
        db = SessionLocal()
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == 'certificat_organisme').first()
        db.close()
        if doc and doc.date_validite:
            return doc.date_validite.strftime('%d/%m/%Y')
        return ""
    except Exception:
        return ""

templates.env.globals['nom_organisme'] = _get_nom_organisme
templates.env.globals['logo_organisme'] = _get_logo_organisme
templates.env.globals['numero_certificat'] = _get_numero_certificat
templates.env.globals['get_config_organisme'] = _get_config_organisme
templates.env.globals['date_validite_certificat'] = _get_date_validite_certificat

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src *; img-src * data: blob:; script-src * 'unsafe-inline' 'unsafe-eval'; style-src * 'unsafe-inline';"
        return response

app.add_middleware(CSPMiddleware)

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
app.include_router(statistiques.router)
app.include_router(non_conformites.router)
app.include_router(caces_obtenus.router)
app.include_router(cartes_caces.router)
app.include_router(dev.router)

@app.get("/")
def dashboard(request: Request):
    from datetime import date, timedelta
    today = date.today()
    limite_4ans = today - timedelta(days=4*365)
    limite_2ans = today - timedelta(days=2*365)
    db = SessionLocal()
    testeurs_list = db.query(Testeur).filter(
        Testeur.actif == True,
        Testeur.etat.in_(["actif", "suspendu"])
    ).order_by(Testeur.nom, Testeur.prenom).all()
    for t in testeurs_list:
        t.habilitations = db.query(HabilitationTesteur).filter(
            HabilitationTesteur.testeur_id == t.id,
            HabilitationTesteur.actif == True
        ).all()
    stats = {
        "stagiaires": db.query(Stagiaire).filter(Stagiaire.actif == 1).count(),
        "cartes": 0,
        "sessions": db.query(Session).count(),
        "expirations": 0
    }
    docs_list = db.query(DocumentOfficiel).all()
    docs_map = {d.type: d for d in docs_list}
    referents = db.query(Utilisateur).filter(
        Utilisateur.role_referent != None,
        Utilisateur.role_referent != '',
        Utilisateur.actif == True
    ).all()
    nc_ouvertes = db.query(NonConformite).filter(
        NonConformite.statut.in_(["ouvert", "en_cours"])
    ).order_by(NonConformite.date.desc()).all()
    sessions_actives = db.query(Session).filter(
        Session.statut.in_(["planifiee", "en_cours"])
    ).order_by(Session.date_theorie, Session.date_pratique_debut).all()
    alertes_testeurs = []
    for t in testeurs_list:
        alertes = []
        if not t.attestation_prevention_pdf:
            alertes.append({"label": "Attestation prévention manquante", "couleur": "rouge"})
        elif t.attestation_prevention_date and t.attestation_prevention_date < limite_4ans:
            alertes.append({"label": "Attestation prévention > 4 ans", "couleur": "orange"})
        if not t.visite_medicale_pdf:
            alertes.append({"label": "Visite médicale manquante", "couleur": "rouge"})
        elif t.visite_medicale_date and t.visite_medicale_date < limite_2ans:
            alertes.append({"label": "Visite médicale > 2 ans", "couleur": "orange"})
        if t.date_prochain_controle and t.date_prochain_controle < today:
            alertes.append({"label": "Prochain contrôle dépassé", "couleur": "rouge"})
        if alertes:
            alertes_testeurs.append({"testeur": t, "alertes": alertes})
    familles_carto = db.query(Famille).filter(Famille.actif == True).order_by(Famille.code).all()
    for f in familles_carto:
        f.categories_habilites = db.query(Categorie).filter(
            Categorie.famille_id == f.id,
            Categorie.pepci_habilite == True,
            Categorie.actif == True,
            Categorie.est_option == False
        ).order_by(Categorie.code).all()
    familles_carto = [f for f in familles_carto if f.categories_habilites]
    lieux_cdt = db.query(Lieu).filter(Lieu.type == "cdt", Lieu.actif == True).order_by(Lieu.nom).all()
    for lieu in lieux_cdt:
        lieu.habilitations = db.query(LieuHabilitation).filter(
            LieuHabilitation.lieu_id == lieu.id,
            LieuHabilitation.actif == True
        ).order_by(LieuHabilitation.famille, LieuHabilitation.categorie).all()
    stagiaires_sans_photo = db.query(Stagiaire).filter(
        text("stagiaires.actif = 1"),
        or_(Stagiaire.photo == None, Stagiaire.photo == "")
    ).order_by(Stagiaire.nom, Stagiaire.prenom).all()
    caces_a_valider_raw = db.query(CacesObtenu).filter(CacesObtenu.statut == "a_valider").all()
    _stag_ids = {co.stagiaire_id for co in caces_a_valider_raw}
    _stag_map = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(_stag_ids)).all()} if _stag_ids else {}
    caces_a_valider = [
        {
            "id": co.id,
            "stagiaire_nom": (_stag_map.get(co.stagiaire_id).nom if _stag_map.get(co.stagiaire_id) else "?"),
            "stagiaire_prenom": (_stag_map.get(co.stagiaire_id).prenom if _stag_map.get(co.stagiaire_id) else ""),
            "famille": co.famille,
            "categorie": co.categorie,
            "date_obtention": co.date_obtention.strftime('%d/%m/%Y') if co.date_obtention else "—",
        }
        for co in caces_a_valider_raw
    ]
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page": "dashboard",
            "stats": stats,
            "testeurs": testeurs_list,
            "docs": docs_map,
            "today": today,
            "referents": referents,
            "nc_ouvertes": nc_ouvertes,
            "sessions_actives": sessions_actives,
            "alertes_testeurs": alertes_testeurs,
            "familles_carto": familles_carto,
            "lieux_cdt": lieux_cdt,
            "stagiaires_sans_photo": stagiaires_sans_photo,
            "caces_a_valider": caces_a_valider,
        }
    )

@app.get("/stagiaires")
def page_stagiaires(request: Request):
    db = SessionLocal()
    liste = db.query(Stagiaire).filter(Stagiaire.actif == 1).order_by(Stagiaire.nom, Stagiaire.prenom).all()
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
    from datetime import date
    db = SessionLocal()
    liste = db.query(Testeur).filter(Testeur.actif == True).order_by(Testeur.nom, Testeur.prenom).all()
    for t in liste:
        t.habilitations = db.query(HabilitationTesteur).filter(
            HabilitationTesteur.testeur_id == t.id,
            HabilitationTesteur.actif == True
        ).all()
        t.cartes = db.query(CarteTesteur).filter(
            CarteTesteur.testeur_id == t.id,
            CarteTesteur.actif == True
        ).order_by(CarteTesteur.famille).all()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="testeurs.html",
        context={
            "page": "testeurs",
            "testeurs": liste,
            "today": date.today()
        }
    )

@app.get("/admin")
def page_admin(request: Request):
    db = SessionLocal()
    familles = db.query(Famille).filter(Famille.actif == True).all()
    categories_raw = db.query(Categorie).filter(Categorie.actif == True).all()
    testeurs_list = db.query(Testeur).filter(Testeur.actif == True).order_by(Testeur.nom, Testeur.prenom).all()
    lieux = db.query(Lieu).all()
    for t in testeurs_list:
        t.habilitations = sorted(
            db.query(HabilitationTesteur).filter(HabilitationTesteur.testeur_id == t.id).all(),
            key=lambda h: (h.famille, h.categorie)
        )
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
    categories.sort(key=lambda c: (c.famille_code, c.code))
    # Charger les options actives par habilitation_id
    all_hab_options = db.query(HabilitationOption).all()
    options_habs = {}
    for ho in all_hab_options:
        options_habs.setdefault(ho.habilitation_id, []).append(ho.code_option)
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "page": "admin",
            "familles": familles,
            "categories": categories,
            "testeurs": testeurs_list,
            "lieux": lieux,
            "options_habs": options_habs
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

@app.get("/sessions/{session_id}/jours/{jour_id}/modifier")
def page_modifier_jour(request: Request, session_id: int, jour_id: int):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
    testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="modifier_jour.html",
        context={"session": session, "jour": jour, "testeurs": testeurs_list}
    )

@app.post("/sessions/{session_id}/jours/{jour_id}/modifier")
async def post_modifier_jour(request: Request, session_id: int, jour_id: int):
    from fastapi.responses import RedirectResponse
    from datetime import date
    form = await request.form()
    db = SessionLocal()
    j = db.query(JourTest).filter(JourTest.id == jour_id).first()
    s = db.query(Session).filter(Session.id == session_id).first()
    new_date = form.get("date")
    testeur_id = form.get("testeur_id")
    # Vérification intervalle session
    erreur = None
    if new_date:
        if s.date_pratique_debut and new_date < str(s.date_pratique_debut):
            erreur = f"⚠️ Date antérieure au début de la session ({s.date_pratique_debut.strftime('%d/%m/%Y')})"
        elif s.date_pratique_fin and new_date > str(s.date_pratique_fin):
            erreur = f"⚠️ Date postérieure à la fin de la session ({s.date_pratique_fin.strftime('%d/%m/%Y')})"
    if erreur:
        testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
        db.close()
        return templates.TemplateResponse(
            request=request,
            name="modifier_jour.html",
            context={"session": s, "jour": j, "testeurs": testeurs_list, "erreur": erreur}
        )
    j.date = date.fromisoformat(new_date) if new_date else j.date
    j.testeur_id = int(testeur_id) if testeur_id else j.testeur_id
    db.commit()
    db.close()
    return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)

@app.get("/sessions/{session_id}/modifier")
def page_modifier_session(request: Request, session_id: int):
    db = SessionLocal()
    session = db.query(Session).filter(Session.id == session_id).first()
    lieux = db.query(Lieu).filter(Lieu.actif == True).all()
    db.close()
    return templates.TemplateResponse(
        request=request,
        name="modifier_session.html",
        context={"session": session, "lieux": lieux}
    )

@app.post("/sessions/{session_id}/modifier")
async def post_modifier_session(request: Request, session_id: int):
    from fastapi.responses import RedirectResponse
    from datetime import date
    form = await request.form()
    db = SessionLocal()
    s = db.query(Session).filter(Session.id == session_id).first()
    debut = form.get("date_pratique_debut")
    fin = form.get("date_pratique_fin")
    responsable = form.get("responsable")
    # Vérification jours existants
    if debut or fin:
        jours = db.query(JourTest).filter(JourTest.session_id == session_id, JourTest.actif == True).all()
        jours_hors = []
        for j in jours:
            if j.date:
                if debut and str(j.date) < debut:
                    jours_hors.append(f"{j.date.strftime('%d/%m/%Y')} ({j.type})")
                elif fin and str(j.date) > fin:
                    jours_hors.append(f"{j.date.strftime('%d/%m/%Y')} ({j.type})")
        if jours_hors:
            db.close()
            jours_str = ", ".join(jours_hors)
            return templates.TemplateResponse(
                request=request,
                name="modifier_session.html",
                context={
                    "session": s,
                    "lieux": [],
                    "erreur": f"⚠️ Ces jours sont hors de l'intervalle : {jours_str}"
                }
            )
    s.date_pratique_debut = date.fromisoformat(debut) if debut else None
    s.date_pratique_fin = date.fromisoformat(fin) if fin else None
    s.responsable = responsable or None
    db.commit()
    db.close()
    return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)

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

    session_candidats = db.query(SessionCandidat).join(
        Stagiaire, Stagiaire.id == SessionCandidat.stagiaire_id
    ).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.actif == True
    ).order_by(Stagiaire.nom, Stagiaire.prenom).all()
    for sc in session_candidats:
        sc.stagiaire = db.query(Stagiaire).filter(Stagiaire.id == sc.stagiaire_id).first()

    epreuves = db.query(SessionEpreuve).filter(SessionEpreuve.session_id == session_id).all()

    famille = db.query(Famille).filter(Famille.code == session.famille).first()
    categories_obj = db.query(Categorie).filter(
        Categorie.famille_id == (famille.id if famille else 0),
        Categorie.pepci_habilite == True,
        Categorie.actif == True,
        Categorie.est_option == False
    ).all() if famille else []
    categories = [c.code for c in categories_obj]
    ut_par_cat = {c.code: c.ut_pratique for c in categories_obj}

    options_par_cat = {}
    for opt in db.query(OptionCategorie).filter(OptionCategorie.famille == session.famille).all():
        if opt.categorie not in options_par_cat:
            options_par_cat[opt.categorie] = []
        options_par_cat[opt.categorie].append({"code": opt.code_option, "libelle": opt.libelle_option})

    epreuves_map = {}
    for e in epreuves:
        testeur = db.query(Testeur).filter(Testeur.id == e.testeur_id).first()
        e.testeur_nom = f"{testeur.nom} {testeur.prenom}" if testeur else "?"
        key = (e.stagiaire_id, e.categorie)
        if key not in epreuves_map:
            epreuves_map[key] = e
        else:
            # Priorité au réussi, sinon on garde le plus récent
            if e.obtenue and not epreuves_map[key].obtenue:
                epreuves_map[key] = e

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

        j.candidats_options = {}
        for jtc in jtcs:
            if jtc.options_planifiees:
                try:
                    j.candidats_options[jtc.stagiaire_id] = json.loads(jtc.options_planifiees)
                except Exception:
                    j.candidats_options[jtc.stagiaire_id] = {}
            else:
                j.candidats_options[jtc.stagiaire_id] = {}

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
            epreuves_jour = db.query(SessionEpreuve).filter(
                SessionEpreuve.session_id == session_id,
                SessionEpreuve.date == j.date
            ).all()
            j.candidats_epreuves = {}
            for ep in epreuves_jour:
                if ep.stagiaire_id not in j.candidats_epreuves:
                    j.candidats_epreuves[ep.stagiaire_id] = []
                j.candidats_epreuves[ep.stagiaire_id].append(ep.categorie)
        else:
            j.total_ut = 0
            j.nb_testeurs = 0
            j.ut_libres = 0
            j.candidats_epreuves = {}

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

    stagiaires = db.query(Stagiaire).filter(Stagiaire.actif == 1).order_by(Stagiaire.nom, Stagiaire.prenom).all()
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
            "testeurs": testeurs_list,
            "options_par_cat": options_par_cat,
            "jours_dates": [{"date": str(j.date), "type": j.type, "label": j.date.strftime('%d/%m/%Y') + ' (' + j.type + ')'} for j in jours_test if j.date]
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

    import json
    reponses_candidat = json.loads(rt.reponses_json) if rt.reponses_json else {}

    # Phase 2 : récupérer les questions via utilisations_themes
    from app.models.utilisations_themes import UtilisationTheme
    session_obj = db.query(Session).filter(Session.id == session_id).first()

    tirages = db.query(UtilisationTheme).filter(
        UtilisationTheme.session_id == session_id,
        UtilisationTheme.famille == session_obj.famille
    ).all()

    detail_themes = {}
    for ut in tirages:
        questions = db.query(ReponseGrille).filter(
            ReponseGrille.grille_id == ut.grille_id,
            ReponseGrille.theme == ut.theme
        ).order_by(ReponseGrille.numero_question).all()

        t = str(ut.theme)
        detail_themes[t] = []
        for r in questions:
            reponse_candidat = reponses_candidat.get(str(r.numero_question))
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
            "grille_numero": grille.numero if grille else "Phase 2",
            "session_candidats": session_candidats
        }
    )


@app.get("/test/theorie/{jour_test_id}/{stagiaire_id}/start")
def page_test_theorie_start(request: Request, jour_test_id: int, stagiaire_id: int):
    db = SessionLocal()
    jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
    if not jour:
        db.close()
        return {"error": "Non trouve"}
    session = db.query(Session).filter(Session.id == jour.session_id).first()
    grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == jour.grille_id).first() if jour.grille_id else None
    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    candidats_ids = [
        jtc.stagiaire_id for jtc in db.query(JourTestCandidat).filter(
            JourTestCandidat.jour_test_id == jour_test_id,
            JourTestCandidat.actif == True
        ).all()
    ]
    session_candidats = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == jour.session_id,
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
            "session_id": jour.session_id,
            "jour_id": jour_test_id,
            "grille_id": jour.grille_id,
            "grille_numero": grille.numero if grille else "Phase 2",
            "session_candidats": session_candidats,
            "start_direct": True,
            "start_stagiaire_id": stagiaire_id,
            "start_nom": stagiaire.nom if stagiaire else "",
            "start_prenom": stagiaire.prenom if stagiaire else "",
            "start_ddn": stagiaire.date_naissance.isoformat() if stagiaire and stagiaire.date_naissance else "",
        }
    )


@app.get("/non-conformites")
def page_non_conformites(request: Request):
    import json
    db = SessionLocal()
    nc_list = db.query(NonConformite).order_by(NonConformite.date.desc()).all()
    utilisateurs_list = db.query(Utilisateur).all()
    db.close()
    utilisateurs_map = {u.id: u for u in utilisateurs_list}
    nc_json = json.dumps([{
        "id": nc.id,
        "reference": nc.reference or "",
        "date": nc.date.isoformat() if nc.date else "",
        "declarant_id": nc.declarant_id,
        "origine": nc.origine,
        "type_nc": nc.type_nc,
        "nature": nc.nature or "",
        "titre": nc.titre,
        "description": nc.description or "",
        "action_preventive": nc.action_preventive or "",
        "action_corrective": nc.action_corrective or "",
        "justificatif_nom": nc.justificatif_nom or "",
        "statut": nc.statut,
        "date_cloture": nc.date_cloture.isoformat() if nc.date_cloture else "",
    } for nc in nc_list])
    return templates.TemplateResponse(
        request=request,
        name="non_conformites.html",
        context={
            "page": "non_conformites",
            "non_conformites": nc_list,
            "utilisateurs": utilisateurs_map,
            "nc_json": nc_json,
        }
    )

@app.get("/caces-obtenus")
def page_caces_obtenus(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="caces_obtenus.html",
        context={"page": "caces_obtenus"}
    )

@app.get("/cartes-caces")
def page_cartes_caces(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="cartes_caces.html",
        context={"page": "cartes_caces"}
    )

@app.get("/profil")
def page_profil(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="profil.html",
        context={"page": "profil"}
    )

@app.get("/admin/utilisateurs")
def page_utilisateurs(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="utilisateurs.html",
        context={"page": "admin"}
    )

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