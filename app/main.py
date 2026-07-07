import math
import json
import re as _re
import os as _os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse as _HTMLResponse, JSONResponse as _JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse as _RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from jose import JWTError as _JWTError, jwt as _jwt
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
from app.models.association_audio_log import AssociationAudioLog
from app.models.document_officiel import DocumentOfficiel
from app.models.carte_testeur import CarteTesteur
from app.models.config_organisme import ConfigOrganisme
from app.models.habilitation_option import HabilitationOption
from app.models.non_conformite import NonConformite
from app.models.utilisateur import Utilisateur
from app.models.reset_tirage import ResetTirage
from app.models.grille_pratique import (GrillePratique, ThemePratique, PointEvaluation, ItemPratique, CritereEliminatoire, SaisiePratique, SaisieBloc, SaisieItemNote, SaisieEliminatoire, CompteurTemps)
from app.models.option_categorie import OptionCategorie
from app.models.caces_obtenu import CacesObtenu
from app.models.carte_caces import CarteCaces
from app.models.fiche_recommandation import FicheRecommandation
from app.models.consentement_rgpd import ConsentementRGPD
from app.models.attestation_neutralite import AttestationNeutralite
from app.models.jour_formation import JourFormation, AffectationFormation, PlanningApprenant, AffectationTest
from app.models.justificatif import Justificatif

from sqlalchemy import text, or_
from app.routers import stagiaires, testeurs, admin, sessions, upload, auth, statistiques
from app.routers import non_conformites
from app.routers import caces_obtenus
from app.routers import registre_caces
from app.routers import cartes_caces
from app.routers import dev
from app.routers import consentements
from app.routers import neutralite
from app.routers import saisie_pratique
from app.routers import fiches_reco
from app.models.utilisateur import Utilisateur

Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────────────────────
# RÈGLE ABSOLUE : toute colonne ajoutée à une table EXISTANTE doit être listée
# ici avec ALTER TABLE ... ADD COLUMN IF NOT EXISTS. create_all() ne modifie
# jamais les tables existantes — il crée uniquement les tables absentes.
# ➜ UNIQUEMENT des ADD COLUMN (additif, sans risque). Aucun DROP dans cette
#   fonction. Les suppressions de colonnes se font manuellement, en conscience,
#   après vérification que la colonne est vide en prod.
# ─────────────────────────────────────────────────────────────────────────────
def _run_startup_migrations():
    _MIGRATIONS = [
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS sous_traitance BOOLEAN DEFAULT FALSE",
        # document_officiel
        "ALTER TABLE document_officiel ADD COLUMN IF NOT EXISTS date_validite TIMESTAMP",
        "ALTER TABLE document_officiel ADD COLUMN IF NOT EXISTS numero_certificat VARCHAR(100)",
        "ALTER TABLE document_officiel ADD COLUMN IF NOT EXISTS cle VARCHAR(500)",
        "ALTER TABLE carte_testeur ADD COLUMN IF NOT EXISTS cle VARCHAR(500)",
        # lieux
        "ALTER TABLE lieux ADD COLUMN IF NOT EXISTS date_integration DATE",
        "ALTER TABLE lieux ADD COLUMN IF NOT EXISTS date_sortie DATE",
        # categories : sortie d'habilitation
        "ALTER TABLE categories ADD COLUMN IF NOT EXISTS date_sortie DATE",
        # caces externes (dispense tracee)
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS organisme_externe VARCHAR(200)",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS justificatif_cle VARCHAR(500)",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS justificatif_nom VARCHAR(255)",
        "ALTER TABLE session_epreuves ALTER COLUMN testeur_id DROP NOT NULL",
        # testeurs
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS carte_cle VARCHAR(500)",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS carte_nom_fichier VARCHAR",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS attestation_prevention_cle VARCHAR(500)",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS attestation_prevention_nom VARCHAR",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS attestation_prevention_date DATE",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS visite_medicale_cle VARCHAR(500)",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS visite_medicale_nom VARCHAR",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS visite_medicale_date DATE",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS evaluation_cle VARCHAR(500)",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS evaluation_nom VARCHAR",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS evaluation_date DATE",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS autorisation_conduite_cle VARCHAR(500)",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS autorisation_conduite_nom VARCHAR",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS etat VARCHAR(20) DEFAULT 'actif'",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS mode_saisie_pratique VARCHAR(20) DEFAULT 'binaire'",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS reco_h_theme_pratique DOUBLE PRECISION DEFAULT 1.5",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS reco_h_forfait_elim DOUBLE PRECISION DEFAULT 1.0",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS reco_h_theorie_courte DOUBLE PRECISION DEFAULT 2.0",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS reco_h_theorie_longue DOUBLE PRECISION DEFAULT 4.0",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS reco_seuil_theorie DOUBLE PRECISION DEFAULT 50.0",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS reco_h_temps DOUBLE PRECISION DEFAULT 1.0",
        "ALTER TABLE item_pratique ADD COLUMN IF NOT EXISTS critere_evaluation TEXT",
        "ALTER TABLE saisie_pratique ADD COLUMN IF NOT EXISTS signature_testeur TEXT",
        "ALTER TABLE saisie_pratique ADD COLUMN IF NOT EXISTS testeur_id INTEGER",
        "ALTER TABLE grille_pratique DROP COLUMN IF EXISTS obligatoire",
        "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS utilisateur_id INTEGER REFERENCES utilisateurs(id)",
        # utilisateurs
        "ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS role_referent VARCHAR",
        "ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS telephone VARCHAR",
        # config_organisme
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS audit_interne_date DATE",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS audit_externe_date DATE",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS revue_direction_date DATE",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS pin_formateur VARCHAR(20) DEFAULT '1234'",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS pin_admin VARCHAR(20) DEFAULT '1505'",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS prochain_numero_caces INTEGER DEFAULT 1",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS adresse TEXT",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS siret VARCHAR(20)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS email VARCHAR(200)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS telephone VARCHAR(50)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signataire_nom VARCHAR(100)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signataire_prenom VARCHAR(100)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signataire_qualite VARCHAR(100)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signature_base64 TEXT",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS signature_nom VARCHAR(200)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS url_verification_caces VARCHAR(500)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS logo2_base64 TEXT",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS logo2_nom VARCHAR(200)",
        # sessions
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS type VARCHAR(20) DEFAULT 'caces'",
        # jours_test
        "ALTER TABLE jours_test ADD COLUMN IF NOT EXISTS testeurs_sup TEXT",
        "ALTER TABLE jours_test ADD COLUMN IF NOT EXISTS tirage_themes_json TEXT",
        "ALTER TABLE jours_test ADD COLUMN IF NOT EXISTS note_privee TEXT",
        "ALTER TABLE jours_test ADD COLUMN IF NOT EXISTS note_privee_auteur_id INTEGER REFERENCES utilisateurs(id)",
        # jours_formation
        "ALTER TABLE jours_formation ADD COLUMN IF NOT EXISTS note_privee TEXT",
        "ALTER TABLE jours_formation ADD COLUMN IF NOT EXISTS note_privee_auteur_id INTEGER REFERENCES utilisateurs(id)",
        "ALTER TABLE jours_formation ADD COLUMN IF NOT EXISTS candidats_ids TEXT",
        "ALTER TABLE jours_formation ADD COLUMN IF NOT EXISTS col_theorie BOOLEAN DEFAULT FALSE",
        "ALTER TABLE jours_formation ADD COLUMN IF NOT EXISTS col_libre BOOLEAN DEFAULT FALSE",
        # jour_test_candidats
        "ALTER TABLE jour_test_candidats ADD COLUMN IF NOT EXISTS options_planifiees TEXT",
        # session_epreuves
        "ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS options_obtenues VARCHAR(200)",
        "ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS bloque BOOLEAN NOT NULL DEFAULT FALSE",
        # resultats_theorie
        "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS bloque BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS mode VARCHAR(12) NOT NULL DEFAULT 'numerique'",
        "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS justificatif_cle VARCHAR(500)",
        "ALTER TABLE resultats_theorie DROP COLUMN IF EXISTS justificatif_pdf",
        "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS justificatif_nom VARCHAR(255)",
        # justificatif grille pratique (SessionEpreuve)
        "ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS justificatif_cle VARCHAR(500)",
        "ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS justificatif_nom VARCHAR(255)",
        "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS testeur_id INTEGER REFERENCES testeurs(id)",
        # caces_obtenus
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS motif_annulation TEXT",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS post_cloture BOOLEAN DEFAULT FALSE",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS resultat_theorie_id INTEGER",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS caces_initial_id INTEGER",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS dispense_externe_sc_id INTEGER",
        "ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS ancien_numero VARCHAR(50)",
        # carte_caces
        "ALTER TABLE carte_caces ADD COLUMN IF NOT EXISTS caces_json TEXT",
        "ALTER TABLE carte_caces ADD COLUMN IF NOT EXISTS token_verification VARCHAR(36)",
        # stagiaires
        "ALTER TABLE stagiaires ADD COLUMN IF NOT EXISTS photo_base64 TEXT",
        # option_categorie
        "ALTER TABLE option_categorie ADD COLUMN IF NOT EXISTS incluse BOOLEAN DEFAULT FALSE",
        # non_conformites
        "ALTER TABLE non_conformites ADD COLUMN IF NOT EXISTS reference VARCHAR(20) UNIQUE",
        "ALTER TABLE non_conformites ADD COLUMN IF NOT EXISTS nature VARCHAR(30)",
        # consentements_rgpd
        "ALTER TABLE consentements_rgpd ADD COLUMN IF NOT EXISTS verificateur_identite VARCHAR(200)",
        "ALTER TABLE consentements_rgpd ADD COLUMN IF NOT EXISTS horodatage_verification TIMESTAMP",
        # session_candidats
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_note TEXT",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_fichier_cle VARCHAR(500)",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_fichier_nom VARCHAR(255)",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_fichier_type VARCHAR(100)",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_date DATE",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_origine VARCHAR(20)",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_source_type VARCHAR(20)",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_source_id INTEGER",
        "ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS dispense_echeance DATE",
        # utilisations_themes
        "ALTER TABLE utilisations_themes ADD COLUMN IF NOT EXISTS date_tirage TIMESTAMP",
        "ALTER TABLE utilisations_themes ADD COLUMN IF NOT EXISTS declenche_par_id INTEGER",
        # reponses_grilles
        "ALTER TABLE reponses_grilles ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)",
        "ALTER TABLE reponses_grilles ADD COLUMN IF NOT EXISTS audio_url_f VARCHAR(500)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS echantillon_audio_h VARCHAR(500)",
        "ALTER TABLE config_organisme ADD COLUMN IF NOT EXISTS echantillon_audio_f VARCHAR(500)",
        # justificatifs
        "ALTER TABLE justificatifs ADD COLUMN IF NOT EXISTS libelle VARCHAR(300)",
        "ALTER TABLE justificatifs ADD COLUMN IF NOT EXISTS uploade_par_role VARCHAR(20)",
    ]
    for sql in _MIGRATIONS:
        try:
            with engine.connect() as _c:
                _c.execute(text(sql))
                _c.commit()
        except Exception as e:
            print(f"[migration] WARN {sql[:80]!r} → {e}", flush=True)

_run_startup_migrations()

try:
    with engine.connect() as _conn:
        _conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_testeur_utilisateur_id ON testeurs (utilisateur_id) WHERE utilisateur_id IS NOT NULL"))
        _conn.commit()
except Exception:
    pass

# Index unique référence session — créé après résolution du doublon prod (2026-06-17)
# Non-silencieux : vérifie explicitement que l'index existe après création
try:
    with engine.connect() as _conn:
        _conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_session_reference "
            "ON sessions (reference) WHERE reference IS NOT NULL"
        ))
        _conn.commit()
    # Vérification explicite (pg_indexes pour PostgreSQL, sqlite_master pour SQLite)
    with engine.connect() as _conn:
        try:
            row = _conn.execute(text(
                "SELECT indexname FROM pg_indexes WHERE indexname = 'uq_session_reference'"
            )).fetchone()
        except Exception:
            row = _conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_session_reference'"
            )).fetchone()
        if row:
            print("[migration] uq_session_reference : index unique cree et verifie.", flush=True)
        else:
            print("[migration] ERREUR : uq_session_reference introuvable apres creation — doublons residuels ?", flush=True)
except Exception as _e:
    print(f"[migration] ERREUR creation uq_session_reference : {_e}", flush=True)

# Index unique résultat théorique (jour_test_id, stagiaire_id) — posé après résolution des doublons base de test (2026-06-17)
# ATTENTION : refaire SELECT jour_test_id, stagiaire_id, COUNT(*) FROM resultats_theorie
#             GROUP BY jour_test_id, stagiaire_id HAVING COUNT(*) > 1  sur PROD avant déploiement
try:
    with engine.connect() as _conn:
        _conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_resultat_theorie_jour_stagiaire "
            "ON resultats_theorie (jour_test_id, stagiaire_id)"
        ))
        _conn.commit()
    with engine.connect() as _conn:
        try:
            row = _conn.execute(text(
                "SELECT indexname FROM pg_indexes WHERE indexname = 'uq_resultat_theorie_jour_stagiaire'"
            )).fetchone()
        except Exception:
            row = _conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_resultat_theorie_jour_stagiaire'"
            )).fetchone()
        if row:
            print("[migration] uq_resultat_theorie_jour_stagiaire : index unique cree et verifie.", flush=True)
        else:
            print("[migration] ERREUR : uq_resultat_theorie_jour_stagiaire introuvable apres creation — doublons residuels ?", flush=True)
except Exception as _e:
    print(f"[migration] ERREUR creation uq_resultat_theorie_jour_stagiaire : {_e}", flush=True)

try:
    with engine.connect() as _conn:
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS affectations_test (
                id SERIAL PRIMARY KEY,
                jour_test_id INTEGER NOT NULL REFERENCES jours_test(id),
                user_id INTEGER NOT NULL REFERENCES utilisateurs(id),
                role VARCHAR(20) DEFAULT 'testeur',
                principal BOOLEAN DEFAULT FALSE,
                UNIQUE (jour_test_id, user_id)
            )
        """))
        _conn.commit()
except Exception as _e:
    print(f"[migration] affectations_test: {_e}", flush=True)

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
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS carte_testeur (
                id SERIAL PRIMARY KEY,
                testeur_id INTEGER NOT NULL REFERENCES testeurs(id),
                famille VARCHAR(50) NOT NULL,
                nom_fichier VARCHAR(200) NOT NULL,
                cle VARCHAR(500),
                date_upload TIMESTAMP DEFAULT NOW(),
                actif BOOLEAN DEFAULT TRUE
            )
        """))
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
            CREATE TABLE IF NOT EXISTS fiche_recommandation (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                stagiaire_id INTEGER NOT NULL REFERENCES stagiaires(id),
                statut VARCHAR(20) NOT NULL DEFAULT 'brouillon',
                fraude_theorie BOOLEAN NOT NULL DEFAULT FALSE,
                difficultes_langue BOOLEAN NOT NULL DEFAULT FALSE,
                comportement_dangereux BOOLEAN NOT NULL DEFAULT FALSE,
                autres_precisions TEXT,
                saisies_json TEXT,
                snapshot_json TEXT,
                testeur_id INTEGER REFERENCES testeurs(id),
                testeur_nom VARCHAR(120),
                date_creation TIMESTAMP DEFAULT NOW(),
                date_maj TIMESTAMP DEFAULT NOW(),
                date_finalisation TIMESTAMP
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
                post_cloture BOOLEAN DEFAULT FALSE,
                resultat_theorie_id INTEGER,
                caces_initial_id INTEGER,
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
        _conn.execute(text("""
            CREATE TABLE IF NOT EXISTS justificatifs (
                id SERIAL PRIMARY KEY,
                type VARCHAR(30) NOT NULL,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                session_candidat_id INTEGER REFERENCES session_candidats(id),
                fichier_cle VARCHAR(500),
                fichier_nom VARCHAR(300),
                fichier_type VARCHAR(100),
                date_upload TIMESTAMP,
                uploade_par VARCHAR(200),
                libelle VARCHAR(300),
                uploade_par_role VARCHAR(20)
            )
        """))
        _conn.commit()
except Exception:
    pass

def ut_ligne(base_ut: float, cat_code: str, options: list, opt_incluse_set: set) -> float:
    """UT pour une catégorie + ses options cochées.
    base_ut = 0.0 pour option-seule (catégorie non planifiée en base)."""
    return round(base_ut + sum(0.5 for o in options if (cat_code, o) not in opt_incluse_set), 1)

def _initiales_testeur(nom_complet: str) -> str:
    parts = nom_complet.strip().split()
    if len(parts) >= 2:
        return (parts[0][:2] + parts[1][0]).upper()
    return parts[0][:3].upper() if parts else "?"

app = FastAPI(
    title="NORYX Engins",
    description="Pilotage CACES® & Autorisation de conduite — PEPCI Formation",
    version="0.1.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
from app.templates_instance import templates

import time as _time

_organisme_cache: dict = {}
_ORGANISME_TTL = 60  # secondes

def _load_organisme_config():
    now = _time.monotonic()
    if _organisme_cache.get("ts", 0) + _ORGANISME_TTL > now:
        return _organisme_cache.get("data")
    db = SessionLocal()
    try:
        data = db.query(ConfigOrganisme).first()
        _organisme_cache["data"] = data
        _organisme_cache["ts"] = now
        return data
    except Exception:
        return _organisme_cache.get("data")
    finally:
        db.close()

_certificat_cache: dict = {}

def _load_certificat():
    now = _time.monotonic()
    if _certificat_cache.get("ts", 0) + _ORGANISME_TTL > now:
        return _certificat_cache.get("data")
    db = SessionLocal()
    try:
        data = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == 'certificat_organisme').first()
        _certificat_cache["data"] = data
        _certificat_cache["ts"] = now
        return data
    except Exception:
        return _certificat_cache.get("data")
    finally:
        db.close()

def _get_nom_organisme():
    config = _load_organisme_config()
    return config.nom_organisme if config and config.nom_organisme else "PEPCI Formation"

def _get_logo_organisme():
    config = _load_organisme_config()
    if config and config.logo_base64 and config.logo_nom:
        ext = config.logo_nom.rsplit('.', 1)[-1].lower()
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
        return f"data:{mime};base64,{config.logo_base64}"
    return ""

def _get_numero_certificat():
    doc = _load_certificat()
    return doc.numero_certificat if doc and doc.numero_certificat else ""

def _get_config_organisme():
    return _load_organisme_config()

def _get_date_validite_certificat():
    doc = _load_certificat()
    if doc and doc.date_validite:
        return doc.date_validite.strftime('%d/%m/%Y')
    return ""

def _static_mtime(relpath):
    try:
        return int(_os.path.getmtime(_os.path.join("static", relpath)))
    except OSError:
        return ""

templates.env.globals['nom_organisme'] = _get_nom_organisme
templates.env.globals['logo_organisme'] = _get_logo_organisme
templates.env.globals['numero_certificat'] = _get_numero_certificat
templates.env.globals['get_config_organisme'] = _get_config_organisme
templates.env.globals['date_validite_certificat'] = _get_date_validite_certificat
templates.env.globals['static_mtime'] = _static_mtime

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src *; img-src * data: blob:; script-src * 'unsafe-inline' 'unsafe-eval'; style-src * 'unsafe-inline';"
        return response

# ── Contrôle d'accès ─────────────────────────────────────────────────────────

_SECRET_KEY = "pepci_caces_2025_secret"
_ALGORITHM = "HS256"

_PUBLIC_PREFIXES = (
    "/static/",
    "/uploads/",
    "/login",
    "/verifier/",
    "/test/theorie/",
    "/consentement/",
    "/neutralite/",
)
_PUBLIC_EXACT = {"/api/auth/token", "/api/auth/logout", "/health"}
_PUBLIC_PATTERNS = [
    _re.compile(r"^/api/sessions/\d+/jours/\d+/grille$"),
    _re.compile(r"^/api/sessions/\d+/theorie/reponses$"),
    _re.compile(r"^/api/sessions/\d+/theorie/brouillon$"),
    _re.compile(r"^/api/sessions/\d+/theorie/brouillon/\d+/\d+$"),
    _re.compile(r"^/admin/config/verifier-pin-formateur$"),
    _re.compile(r"^/api/consentements/"),
    _re.compile(r"^/api/neutralite/"),
]

_GESTION_PATHS = frozenset({
    "/stagiaires", "/caces-obtenus", "/cartes-caces",
    "/non-conformites", "/statistiques", "/registre-caces",
})

_403_HTML = (
    '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Accès refusé</title></head>'
    '<body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;'
    'min-height:100vh;margin:0;background:#f5f6fa;">'
    '<div style="text-align:center;background:white;padding:40px;border-radius:16px;'
    'box-shadow:0 2px 12px rgba(0,0,0,.1);">'
    '<div style="font-size:48px;margin-bottom:16px;">🚫</div>'
    '<h2 style="color:#c62828;margin-bottom:8px;">Accès refusé</h2>'
    '<p style="color:#666;margin-bottom:24px;">Vous n\'avez pas les droits pour accéder à cette page.</p>'
    '<a href="javascript:history.back()" style="background:#1a237e;color:white;padding:12px 24px;'
    'border-radius:10px;text-decoration:none;font-weight:700;">← Retour</a>'
    '</div></body></html>'
)

def _est_public(path: str) -> bool:
    if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return True
    if path in _PUBLIC_EXACT:
        return True
    return any(p.match(path) for p in _PUBLIC_PATTERNS)

def _est_api(path: str) -> bool:
    return path.startswith("/api/") or (
        path.startswith("/admin/") and not path.startswith("/admin/config/verifier-pin-formateur")
    )

def _verifier_role(path: str, method: str, role: str):
    """Retourne True (ok), False (403), ou une URL de redirect."""
    # /admin* → admin uniquement
    if path.startswith("/admin"):
        return role == "admin"
    # Dashboard → accessible au terrain en lecture (blocs filtres dans le template)
    # Pages de gestion → admin + utilisateur seulement
    if path in _GESTION_PATHS or path.startswith("/statistiques") or path.startswith("/api/statistiques") or path.startswith("/api/registre-caces"):
        return role in ("admin", "utilisateur")
    # Actions interdites au terrain
    if role == "terrain":
        base = path.rstrip("/")
        # Exception ciblée : note privée du principal — l'endpoint revérifie user_id == principal
        if _re.match(r"^/api/sessions/\d+/jours(-formation)?/\d+/note-privee$", base):
            return True
        # Exception : saisie/modification résultat pratique — le terrain est testeur, c'est son rôle
        if method == "POST" and _re.match(r"^/api/sessions/\d+/epreuves$", base):
            return True
        # Exception : clôture terrain — déclenchable par tous les rôles (PIN formateur requis)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/cloturer-terrain$", base):
            return True
        # Exception : toggle identité candidat — coché par le testeur sur tablette à l'accueil
        if method == "PUT" and _re.match(r"^/api/sessions/\d+/jours/\d+/candidats/\d+/identite$", base):
            return True
        # Exception : annulation résultat pratique — testeur corrige une erreur de saisie
        if method == "DELETE" and _re.match(r"^/api/sessions/\d+/epreuves/\d+$", base):
            return True
        # Exception : réouverture résultat théorique — récupération d'une validation accidentelle en salle (PIN formateur requis)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/theorie/reouvrir/\d+/\d+$", base):
            return True
        # Exception : saisie dégradée (papier) — le testeur corrige le papier et saisit les notes (PIN formateur requis)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/theorie/reponses-degrade$", base):
            return True
        # Exception : upload justificatif PDF — terrain et back-office peuvent attacher le scan (PIN formateur requis)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/theorie/justificatif/\d+/\d+$", base):
            return True
        # Exception : upload justificatif grille pratique (PIN formateur requis)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/pratique/justificatif/\d+$", base):
            return True
        # Exceptions : saisie pratique EN LIGNE (terrain testeur, PIN formateur requis)
        # ouvrir : chemin reel = /pratique/saisie/{jour_test_id}/{stagiaire_id}/{categorie}/ouvrir
        if method == "POST" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/\d+/[^/]+/ouvrir$", base):
            return True
        # variantes (GET) : meme forme de chemin, requis pour preparer la saisie
        if method == "GET" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/\d+/[^/]+/variantes$", base):
            return True
        if method == "POST" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/enregistrer$", base):
            return True
        if method == "GET" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/calculer$", base):
            return True
        if method == "GET" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/testeurs-habilites$", base):
            return True
        if method == "POST" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/valider$", base):
            return True
        if method == "POST" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+/rouvrir$", base):
            return True
        if method == "DELETE" and _re.match(r"^/api/sessions/\d+/pratique/saisie/\d+$", base):
            return True
        # Exception : suppression résultat théorique — terrain peut corriger un mauvais candidat (PIN formateur requis)
        if method == "DELETE" and _re.match(r"^/api/sessions/\d+/theorie/reponses/\d+/\d+$", base):
            return True
        # justificatif de dispense POST (terrain peut uploader, ex: CACES externe apporte le jour du test)
        # NB: DELETE volontairement NON whiteliste -> suppression reservee au back-office (anti-erreur)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/candidats/\d+/dispense-fichier$", base):
            return True
        # justificatif generique POST (terrain peut uploader : feuille de presence formation, etc.)
        if method == "POST" and _re.match(r"^/api/sessions/\d+/justificatifs$", base):
            return True
        # justificatif generique DELETE (terrain autorise a ATTEINDRE la route ;
        # la route verifie ensuite que uploade_par_role == 'terrain', sinon 403)
        if method == "DELETE" and _re.match(r"^/api/sessions/\d+/justificatifs/\d+$", base):
            return True
        # Toutes les routes d'écriture sur les sessions (création + toutes sous-ressources)
        if method != "GET" and (base == "/api/sessions" or _re.match(r"^/api/sessions/\d+", base)):
            return False
        # Pages de modification session et de modification jour
        if _re.match(r"^/sessions/\d+/(modifier|jours/\d+/modifier)$", base):
            return False
        if method in ("PUT", "DELETE") and _re.match(r"^/api/testeurs/\d+$", base):
            return False
        # Tout sous /stagiaires/ est interdit sauf consultation + upload/suppression photo
        if base.startswith("/stagiaires/") and not _re.match(
            r"^/stagiaires/\d+/(consultation|photo-upload|photo)$", base
        ):
            return False
        # Terrain en lecture seule sur ses documents : ecriture /api/upload/* interdite
        # (upload, suppression, modification date d'expiration). GET (/download) reste autorise.
        if method != "GET" and base.startswith("/api/upload"):
            return False
    return True

class AccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        path = request.url.path
        method = request.method

        if method == "OPTIONS" or _est_public(path):
            return await call_next(request)

        # Extraction token : header (fetch) puis cookie (navigation)
        token = None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            if _est_api(path):
                return _JSONResponse({"detail": "Non authentifié"}, status_code=401)
            return _RedirectResponse(url="/login", status_code=302)

        try:
            payload = _jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
            email = payload.get("sub")
            if not email:
                raise _JWTError()
        except _JWTError:
            if _est_api(path):
                return _JSONResponse({"detail": "Token invalide"}, status_code=401)
            return _RedirectResponse(url="/login", status_code=302)

        db = SessionLocal()
        try:
            user = db.query(Utilisateur).filter(
                Utilisateur.email == email,
                Utilisateur.actif == True
            ).first()
        finally:
            db.close()

        if not user:
            if _est_api(path):
                return _JSONResponse({"detail": "Non authentifié"}, status_code=401)
            return _RedirectResponse(url="/login", status_code=302)

        verdict = _verifier_role(path, method, user.role)
        if isinstance(verdict, str):
            return _RedirectResponse(url=verdict, status_code=302)
        if verdict is False:
            if _est_api(path):
                return _JSONResponse({"detail": "Accès refusé"}, status_code=403)
            return _HTMLResponse(content=_403_HTML, status_code=403)

        request.state.user = user
        return await call_next(request)

app.add_middleware(CSPMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessMiddleware)

app.include_router(stagiaires.router)
app.include_router(testeurs.router)
app.include_router(admin.router)
app.include_router(sessions.router)
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(statistiques.router)
app.include_router(non_conformites.router)
app.include_router(caces_obtenus.router)
app.include_router(registre_caces.router)
app.include_router(cartes_caces.router)
app.include_router(fiches_reco.router)
app.include_router(dev.router)
app.include_router(consentements.router)
app.include_router(neutralite.router)
app.include_router(saisie_pratique.router)


@app.get("/sessions/{session_id}/projection/{jour_id}")
def page_projection_theorie(session_id: int, jour_id: int, request: Request, db: DBSession = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    from app.services.tirage_grille import get_questions_phase2 as _gqp2
    tirage_ok = True
    questions_flat = []
    try:
        data = _gqp2(session_id, session.famille, db)
        seq = 1
        for theme_num in sorted(data["themes"].keys()):
            for q in data["themes"][theme_num]:
                questions_flat.append({
                    "seq": seq,
                    "theme": theme_num,
                    "texte": q.get("texte") or "",
                    "image": q.get("image") or None,
                    "audio": q.get("audio") or None,
                    "audio_f": q.get("audio_f") or None,
                })
                seq += 1
    except ValueError:
        tirage_ok = False
    return templates.TemplateResponse(
        request=request,
        name="projection_theorie.html",
        context={
            "session_ref": session.reference or f"Session {session.id}",
            "famille": session.famille,
            "tirage_ok": tirage_ok,
            "questions": questions_flat,
            "total": len(questions_flat),
        },
    )


@app.get("/api/sessions/{session_id}/theorie/pdf/sujet")
def pdf_sujet_vierge(session_id: int, request: Request, db: DBSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    from io import BytesIO as _BIO
    from app.services.pdf_test_theorie import generer_sujet_vierge
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        pdf_bytes = generer_sujet_vierge(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {e}")
    return StreamingResponse(
        _BIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=sujet_theorie_session{session_id}.pdf"},
    )


@app.get("/api/sessions/{session_id}/theorie/pdf/corrige")
def pdf_corrige(session_id: int, request: Request, db: DBSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    from io import BytesIO as _BIO
    from app.services.pdf_test_theorie import generer_corrige
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        pdf_bytes = generer_corrige(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {e}")
    return StreamingResponse(
        _BIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=corrige_theorie_session{session_id}.pdf"},
    )


@app.get("/sessions/{session_id}/export-zip")
def export_zip_session(session_id: int, request: Request, pin: str = "", db: DBSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    from io import BytesIO as _BIO
    from app.services.export_zip_session import generer_zip_session
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    if getattr(user, "role", None) == "terrain":
        raise HTTPException(status_code=403, detail="Réservé au back-office.")
    if pin != "1505":
        raise HTTPException(status_code=403, detail="Code PIN incorrect.")
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    try:
        zip_bytes = generer_zip_session(session_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération ZIP : {e}")
    ref = (session.reference or str(session_id)).replace("/", "-").replace(" ", "_")
    return StreamingResponse(
        _BIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=session-{ref}.zip"},
    )


@app.get("/")
def dashboard(request: Request):
    from datetime import date, timedelta
    _u_dash = getattr(request.state, "user", None)
    _user_role_dash = _u_dash.role if _u_dash else None
    today = date.today()
    limite_4ans = today - timedelta(days=4*365)
    limite_2ans = today - timedelta(days=2*365)
    seuil_carte_orange = today + timedelta(days=180)
    seuil_carte_rouge = today + timedelta(days=90)
    seuil_rcp_orange = today + timedelta(days=60)
    db = SessionLocal()
    try:
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
        from app.models.utilisations_themes import UtilisationTheme as _UTDash
        _sa_ids = [s.id for s in sessions_actives]
        sessions_avec_tirage = {
            row.session_id
            for row in db.query(_UTDash.session_id).filter(
                _UTDash.session_id.in_(_sa_ids)
            ).distinct().all()
        } if _sa_ids else set()
        sessions_avec_nc = {
            row.session_id
            for row in db.query(NonConformite.session_id).filter(
                NonConformite.session_id.in_(_sa_ids),
                NonConformite.statut.in_(["ouvert", "en_cours"])
            ).distinct().all()
        } if _sa_ids else set()
        from app.services.session_statut import statut_affichage_session as _sas_dash
        _dash_avec_epreuve = {
            row.session_id
            for row in db.query(SessionEpreuve.session_id).filter(
                SessionEpreuve.session_id.in_(_sa_ids)
            ).distinct().all()
        } if _sa_ids else set()
        _dash_avec_rt = {
            row.session_id
            for row in db.query(ResultatTheorie.session_id).filter(
                ResultatTheorie.session_id.in_(_sa_ids)
            ).distinct().all()
        } if _sa_ids else set()
        statuts_affichage = {
            s.id: _sas_dash(s, a_tirage=s.id in sessions_avec_tirage,
                            a_epreuve=s.id in _dash_avec_epreuve,
                            a_resultat_theorie=s.id in _dash_avec_rt)
            for s in sessions_actives
        }
        alertes_testeurs = []
        for t in testeurs_list:
            alertes = []
            if not t.attestation_prevention_cle:
                alertes.append({"label": "Attestation prévention manquante", "couleur": "rouge"})
            elif t.attestation_prevention_date and t.attestation_prevention_date < limite_4ans:
                alertes.append({"label": "Attestation prévention > 4 ans", "couleur": "orange"})
            if not t.visite_medicale_cle:
                alertes.append({"label": "Visite médicale manquante", "couleur": "rouge"})
            elif t.visite_medicale_date and t.visite_medicale_date < limite_2ans:
                alertes.append({"label": "Visite médicale > 2 ans", "couleur": "orange"})
            if t.date_prochain_controle and t.date_prochain_controle < today:
                alertes.append({"label": "Prochain contrôle dépassé", "couleur": "rouge"})
            _cartes_t = db.query(CarteTesteur).filter(
                CarteTesteur.testeur_id == t.id,
                CarteTesteur.actif == True,
                CarteTesteur.date_expiration.isnot(None)
            ).all()
            for _ct in _cartes_t:
                if _ct.date_expiration < seuil_carte_rouge:
                    alertes.append({"label": "Carte " + _ct.famille + " expire le " + _ct.date_expiration.strftime("%d/%m/%Y"), "couleur": "rouge"})
                elif _ct.date_expiration < seuil_carte_orange:
                    alertes.append({"label": "Carte " + _ct.famille + " expire le " + _ct.date_expiration.strftime("%d/%m/%Y"), "couleur": "orange"})
            if not t.rcp_cle:
                alertes.append({"label": "RCP manquante", "couleur": "rouge"})
            elif t.rcp_date:
                if t.rcp_date < today:
                    alertes.append({"label": "RCP expirée le " + t.rcp_date.strftime("%d/%m/%Y"), "couleur": "rouge"})
                elif t.rcp_date < seuil_rcp_orange:
                    alertes.append({"label": "RCP expire le " + t.rcp_date.strftime("%d/%m/%Y"), "couleur": "orange"})
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
            or_(Stagiaire.photo_base64 == None, Stagiaire.photo_base64 == ""),
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
        # ── Rappel d'audit externe (meme critere que le blocage du tirage) ──
        # Import local : contourne "organize imports on save" de l'IDE.
        from app.models.reset_tirage import audit_reset_requis
        audit_rappel_date = audit_reset_requis(db)
        audit_rappel = audit_rappel_date is not None

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "page": "dashboard",
                "audit_rappel": audit_rappel,
                "audit_rappel_date": audit_rappel_date,
                "stats": stats,
                "testeurs": testeurs_list,
                "docs": docs_map,
                "today": today,
                "referents": referents,
                "nc_ouvertes": nc_ouvertes,
                "sessions_actives": sessions_actives,
                "sessions_avec_tirage": sessions_avec_tirage,
                "sessions_avec_nc": sessions_avec_nc,
                "statuts_affichage": statuts_affichage,
                "alertes_testeurs": alertes_testeurs,
                "familles_carto": familles_carto,
                "lieux_cdt": lieux_cdt,
                "stagiaires_sans_photo": stagiaires_sans_photo,
                "caces_a_valider": caces_a_valider,
                "user_role": _user_role_dash,
            }
        )
    finally:
        db.close()

@app.get("/stagiaires")
def page_stagiaires(request: Request):
    db = SessionLocal()
    try:
        liste = db.query(Stagiaire).filter(Stagiaire.actif == 1).order_by(Stagiaire.nom, Stagiaire.prenom).all()
        familles = db.query(Famille).filter(Famille.actif == True).order_by(Famille.code).all()
        familles_data = [{"code": f.code, "libelle": f.libelle} for f in familles]
        actifs_ids = set(
            row[0] for row in db.query(SessionCandidat.stagiaire_id)
            .join(Session, Session.id == SessionCandidat.session_id)
            .filter(Session.statut.notin_(["terminee", "annulee"]))
            .distinct()
            .all()
        )
        return templates.TemplateResponse(
            request=request,
            name="stagiaires.html",
            context={
                "page": "stagiaires",
                "stagiaires": liste,
                "familles_reprise": familles_data,
                "stagiaires_actifs": actifs_ids,
            }
        )
    finally:
        db.close()

@app.get("/stagiaires/{stagiaire_id}/consultation")
def page_stagiaire_consultation(request: Request, stagiaire_id: int, session_id: int = None):
    from datetime import date as _date
    _u = getattr(request.state, "user", None)
    db = SessionLocal()
    try:
        stagiaire = db.query(Stagiaire).filter(
            Stagiaire.id == stagiaire_id,
            Stagiaire.actif == 1
        ).first()
        if not stagiaire:
            raise HTTPException(status_code=404)

        # Terrain : le stagiaire doit appartenir à au moins une session non clôturée
        if _u and _u.role == "terrain":
            accessible = db.query(SessionCandidat).join(
                Session, Session.id == SessionCandidat.session_id
            ).filter(
                SessionCandidat.stagiaire_id == stagiaire_id,
                SessionCandidat.actif == True,
                Session.statut != "terminee"
            ).first()
            if not accessible:
                return _HTMLResponse(_403_HTML, status_code=403)

        caces_valides = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == stagiaire_id,
            CacesObtenu.statut == "valide"
        ).order_by(CacesObtenu.famille, CacesObtenu.categorie).all()

        consentement = db.query(ConsentementRGPD).filter(
            ConsentementRGPD.stagiaire_id == stagiaire_id
        ).order_by(ConsentementRGPD.id.desc()).first()

        # Historique sessions : calcul serveur (terrain ne peut pas appeler l'API /historique)
        candidatures = db.query(SessionCandidat).filter(
            SessionCandidat.stagiaire_id == stagiaire_id,
            SessionCandidat.actif == True
        ).all()
        historique = []
        for sc in candidatures:
            sess = db.query(Session).filter(Session.id == sc.session_id).first()
            if not sess:
                continue
            rt = db.query(ResultatTheorie).filter(
                ResultatTheorie.session_id == sc.session_id,
                ResultatTheorie.stagiaire_id == stagiaire_id,
                ResultatTheorie.obtenue == True
            ).order_by(ResultatTheorie.id.asc()).first()
            if not rt:
                rt = db.query(ResultatTheorie).filter(
                    ResultatTheorie.session_id == sc.session_id,
                    ResultatTheorie.stagiaire_id == stagiaire_id
                ).order_by(ResultatTheorie.id.desc()).first()
            epreuves = db.query(SessionEpreuve).filter(
                SessionEpreuve.session_id == sc.session_id,
                SessionEpreuve.stagiaire_id == stagiaire_id
            ).order_by(SessionEpreuve.categorie).all()
            historique.append({"session": sess, "theorie": rt, "epreuves": epreuves})
        historique.sort(key=lambda x: x["session"].id, reverse=True)

        return templates.TemplateResponse(
            request=request,
            name="stagiaire_consultation.html",
            context={
                "page": "sessions",
                "stagiaire": stagiaire,
                "caces_valides": caces_valides,
                "consentement": consentement,
                "historique": historique,
                "session_id": session_id,
                "user_role": _u.role if _u else None,
                "today_date": _date.today(),
            }
        )
    finally:
        db.close()

@app.get("/testeurs")
def page_testeurs(request: Request):
    from datetime import date
    db = SessionLocal()
    _u = getattr(request.state, "user", None)
    _user_role = _u.role if _u else None
    try:
        if _user_role == "terrain" and _u:
            liste = db.query(Testeur).filter(
                Testeur.actif == True,
                Testeur.utilisateur_id == _u.id
            ).order_by(Testeur.nom, Testeur.prenom).all()
        else:
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
        utilisateurs_terrain = db.query(Utilisateur).filter(
            Utilisateur.role == "terrain",
            Utilisateur.actif == True
        ).order_by(Utilisateur.nom, Utilisateur.prenom).all()
        return templates.TemplateResponse(
            request=request,
            name="testeurs.html",
            context={
                "page": "testeurs",
                "testeurs": liste,
                "today": date.today(),
                "utilisateurs_terrain": utilisateurs_terrain,
                "user_role": _user_role,
                "terrain_sans_fiche": (_user_role == "terrain" and len(liste) == 0),
            }
        )
    finally:
        db.close()

@app.get("/admin")
def page_admin(request: Request):
    db = SessionLocal()
    try:
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
        all_hab_options = db.query(HabilitationOption).all()
        options_habs = {}
        for ho in all_hab_options:
            options_habs.setdefault(ho.habilitation_id, []).append(ho.code_option)
        options_cat_map = {}
        options_incluses_map = {}
        for opt in db.query(OptionCategorie).all():
            key = f"{opt.famille}__{opt.categorie}"
            if opt.incluse:
                options_incluses_map.setdefault(key, []).append(opt)
            else:
                options_cat_map.setdefault(key, []).append(opt)
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "page": "admin",
                "familles": familles,
                "categories": categories,
                "testeurs": testeurs_list,
                "lieux": lieux,
                "options_habs": options_habs,
                "options_cat_map": options_cat_map,
                "options_incluses_map": options_incluses_map,
            }
        )
    finally:
        db.close()

@app.get("/admin/images")
def page_admin_images(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_images.html",
        context={"page": "admin"}
    )

@app.get("/sessions")
def page_sessions(request: Request):
    _u = getattr(request.state, "user", None)
    db = SessionLocal()
    try:
        liste = db.query(Session).filter((Session.type != "reprise") | (Session.type.is_(None))).order_by(Session.id.desc()).all()
        lieux = db.query(Lieu).filter(Lieu.actif == True).all()
        familles = db.query(Famille).filter(Famille.actif == True).all()
        testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
        from app.models.utilisations_themes import UtilisationTheme as _UTSess
        from datetime import date as _date
        from app.services.session_statut import statut_affichage_session
        _sess_ids = [s.id for s in liste]
        sessions_avec_tirage = {
            row.session_id
            for row in db.query(_UTSess.session_id).filter(
                _UTSess.session_id.in_(_sess_ids)
            ).distinct().all()
        } if _sess_ids else set()
        _today = _date.today()
        _sessions_avec_epreuve = {
            row.session_id
            for row in db.query(SessionEpreuve.session_id).filter(
                SessionEpreuve.session_id.in_(_sess_ids)
            ).distinct().all()
        } if _sess_ids else set()
        _sessions_avec_rt = {
            row.session_id
            for row in db.query(ResultatTheorie.session_id).filter(
                ResultatTheorie.session_id.in_(_sess_ids)
            ).distinct().all()
        } if _sess_ids else set()
        statuts_affichage = {
            s.id: statut_affichage_session(
                s,
                a_tirage=s.id in sessions_avec_tirage,
                a_epreuve=s.id in _sessions_avec_epreuve,
                a_resultat_theorie=s.id in _sessions_avec_rt,
                today=_today,
            )
            for s in liste
        }
        return templates.TemplateResponse(
            request=request,
            name="sessions.html",
            context={
                "page": "sessions",
                "sessions": liste,
                "lieux": lieux,
                "familles": familles,
                "testeurs": testeurs_list,
                "user_role": _u.role if _u else None,
                "sessions_avec_tirage": sessions_avec_tirage,
                "statuts_affichage": statuts_affichage,
            }
        )
    finally:
        db.close()

@app.get("/sessions/{session_id}/jours/{jour_id}/modifier")
def page_modifier_jour(request: Request, session_id: int, jour_id: int):
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
        testeurs_list = db.query(Testeur).filter(Testeur.actif == True).order_by(Testeur.nom, Testeur.prenom).all()
        # Immuabilite : si le jour est deja affecte a un testeur desactive depuis,
        # l'inclure dans la liste pour qu'il reste selectionne (sinon risque d'ecrasement).
        if jour and jour.testeur_id and all(t.id != jour.testeur_id for t in testeurs_list):
            t_hist = db.query(Testeur).filter(Testeur.id == jour.testeur_id).first()
            if t_hist:
                testeurs_list = list(testeurs_list) + [t_hist]
        return templates.TemplateResponse(
            request=request,
            name="modifier_jour.html",
            context={"session": session, "jour": jour, "testeurs": testeurs_list}
        )
    finally:
        db.close()

@app.post("/sessions/{session_id}/jours/{jour_id}/modifier")
async def post_modifier_jour(request: Request, session_id: int, jour_id: int):
    from fastapi.responses import RedirectResponse
    from datetime import date
    form = await request.form()
    db = SessionLocal()
    try:
        j = db.query(JourTest).filter(JourTest.id == jour_id).first()
        s = db.query(Session).filter(Session.id == session_id).first()
        new_date = form.get("date")
        testeur_id = form.get("testeur_id")
        erreur = None
        if new_date:
            if s.date_pratique_debut and new_date < str(s.date_pratique_debut):
                erreur = f"⚠️ Date antérieure au début de la session ({s.date_pratique_debut.strftime('%d/%m/%Y')})"
            elif s.date_pratique_fin and new_date > str(s.date_pratique_fin):
                erreur = f"⚠️ Date postérieure à la fin de la session ({s.date_pratique_fin.strftime('%d/%m/%Y')})"
        if erreur:
            testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()
            return templates.TemplateResponse(
                request=request,
                name="modifier_jour.html",
                context={"session": s, "jour": j, "testeurs": testeurs_list, "erreur": erreur}
            )
        note = form.get("note", "").strip() or None
        j.date = date.fromisoformat(new_date) if new_date else j.date
        j.testeur_id = int(testeur_id) if testeur_id else j.testeur_id
        j.note = note
        db.commit()
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
    finally:
        db.close()

@app.get("/sessions/{session_id}/modifier")
def page_modifier_session(request: Request, session_id: int):
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        lieux = db.query(Lieu).filter(Lieu.actif == True).all()
        return templates.TemplateResponse(
            request=request,
            name="modifier_session.html",
            context={"session": session, "lieux": lieux}
        )
    finally:
        db.close()

@app.post("/sessions/{session_id}/modifier")
async def post_modifier_session(request: Request, session_id: int):
    from fastapi.responses import RedirectResponse
    from datetime import date
    form = await request.form()
    db = SessionLocal()
    try:
        s = db.query(Session).filter(Session.id == session_id).first()
        debut = form.get("date_pratique_debut")
        fin = form.get("date_pratique_fin")
        responsable = form.get("responsable")

        def erreur_resp(msg):
            return templates.TemplateResponse(
                request=request,
                name="modifier_session.html",
                context={"session": s, "lieux": [], "erreur": msg}
            )

        if not debut:
            return erreur_resp("La date de début est obligatoire")
        if not fin:
            return erreur_resp("La date de fin est obligatoire")
        if date.fromisoformat(debut) > date.fromisoformat(fin):
            return erreur_resp("La date de début doit être ≤ à la date de fin")

        jours_hors = []
        for j in db.query(JourTest).filter(JourTest.session_id == session_id, JourTest.actif == True).all():
            if j.date and (str(j.date) < debut or str(j.date) > fin):
                jours_hors.append(f"{j.date.strftime('%d/%m/%Y')} ({j.type})")
        for j in db.query(JourFormation).filter(JourFormation.session_id == session_id, JourFormation.actif == True).all():
            if j.date and (str(j.date) < debut or str(j.date) > fin):
                jours_hors.append(f"{j.date.strftime('%d/%m/%Y')} (formation)")
        if jours_hors:
            db.rollback()
            return erreur_resp(f"⚠️ Ces jours sont hors de l'intervalle : {', '.join(jours_hors)}")

        s.date_pratique_debut = date.fromisoformat(debut)
        s.date_pratique_fin = date.fromisoformat(fin)
        s.responsable = responsable or None
        db.commit()
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
    finally:
        db.close()

@app.get("/sessions/{session_id}")
def page_session_detail(request: Request, session_id: int):
    _u = getattr(request.state, "user", None)
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
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
        ).order_by(Categorie.code).all() if famille else []
        categories = [c.code for c in categories_obj]
        ut_par_cat = {c.code: c.ut_pratique for c in categories_obj}
        # Immuabilite historique : inclure les categories reellement presentes dans
        # cette session (via SessionEpreuve), meme si desactivees depuis dans la cartographie.
        # Le filtre actif ci-dessus ne concerne QUE les categories proposables ; une
        # session deja saisie doit toujours afficher ses categories d'origine.
        codes_deja = set(categories)
        codes_epreuves = {e.categorie for e in epreuves if e.categorie}
        codes_manquants = codes_epreuves - codes_deja
        if codes_manquants and famille:
            cats_hist = db.query(Categorie).filter(
                Categorie.famille_id == famille.id,
                Categorie.code.in_(codes_manquants),
                Categorie.est_option == False
            ).order_by(Categorie.code).all()
            for c in cats_hist:
                if c.code not in codes_deja:
                    categories.append(c.code)
                    ut_par_cat[c.code] = c.ut_pratique
                    codes_deja.add(c.code)
            categories = sorted(categories)
        # Formation : toutes les catégories de la famille, sans filtre habilitation
        categories_formation_obj = db.query(Categorie).filter(
            Categorie.famille_id == (famille.id if famille else 0),
            Categorie.actif == True,
            Categorie.est_option == False
        ).order_by(Categorie.code).all() if famille else []
        categories_formation = [c.code for c in categories_formation_obj]

        options_par_cat = {}
        opt_incluse_set = set()
        for opt in db.query(OptionCategorie).filter(OptionCategorie.famille == session.famille).all():
            if opt.categorie not in options_par_cat:
                options_par_cat[opt.categorie] = []
            options_par_cat[opt.categorie].append({
                "code": opt.code_option,
                "libelle": opt.libelle_option,
                "incluse": bool(opt.incluse),
            })
            if opt.incluse:
                opt_incluse_set.add((opt.categorie, opt.code_option))

        epreuves_map = {}
        for e in epreuves:
            testeur = db.query(Testeur).filter(Testeur.id == e.testeur_id).first()
            e.testeur_nom = f"{testeur.nom} {testeur.prenom}" if testeur else "?"
            key = (e.stagiaire_id, e.categorie)
            if key not in epreuves_map:
                epreuves_map[key] = e
            else:
                if e.obtenue and not epreuves_map[key].obtenue:
                    epreuves_map[key] = e

        # Couples (stagiaire_id, categorie) issus de la SAISIE NUMERIQUE en ligne.
        # Sert a masquer l'icone justificatif externe (📎/⚠️) : la grille
        # native de la saisie en ligne tient deja lieu de justificatif.
        saisie_numerique_set = set()
        _saisies_sess = (
            db.query(SaisiePratique)
            .join(JourTest, JourTest.id == SaisiePratique.jour_test_id)
            .filter(JourTest.session_id == session_id)
            .all()
        )
        for _sp in _saisies_sess:
            saisie_numerique_set.add((_sp.stagiaire_id, _sp.categorie))

        testeur_initiales_par_stag_cat = {}
        for (stag_id, cat), e in epreuves_map.items():
            if e.testeur_id and e.testeur_nom and e.testeur_nom != "?":
                testeur_initiales_par_stag_cat.setdefault(stag_id, {})[cat] = {
                    "initiales": _initiales_testeur(e.testeur_nom),
                    "nom": e.testeur_nom,
                }

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
            ut_testeurs[e.testeur_id]["categories"][cat] += e.ut

        jours_test = db.query(JourTest).filter(
            JourTest.session_id == session_id,
            JourTest.actif == True
        ).order_by(JourTest.date).all()

        jours_formation = db.query(JourFormation).filter(
            JourFormation.session_id == session_id,
            JourFormation.actif == True
        ).order_by(JourFormation.date).all()

        # Affectations formateurs — annoter chaque jf pour l'affichage inline
        _af_ids = [jf.id for jf in jours_formation]
        _af_list = db.query(AffectationFormation).filter(
            AffectationFormation.jour_formation_id.in_(_af_ids)
        ).all() if _af_ids else []
        _af_user_ids = list({af.user_id for af in _af_list})
        _af_users_map = {u.id: u for u in db.query(Utilisateur).filter(
            Utilisateur.id.in_(_af_user_ids)
        ).all()} if _af_user_ids else {}
        def _abr(u):
            if not u:
                return "?"
            p = (u.prenom or "")[:1].upper()
            n = (u.nom or "")[:3].upper()
            return f"{p}.{n}" if p and n else (u.nom or u.prenom or "?")

        for jf in jours_formation:
            jf.affectations = sorted(
                [{"user_id": af.user_id,
                  "nom_complet": f"{_af_users_map[af.user_id].nom} {_af_users_map[af.user_id].prenom}"
                                 if af.user_id in _af_users_map else "?",
                  "abreviation": _abr(_af_users_map.get(af.user_id)),
                  "theorie": af.theorie, "pratique": af.pratique, "principal": af.principal}
                 for af in _af_list if af.jour_formation_id == jf.id],
                key=lambda x: (not x["principal"], x["nom_complet"])
            )

        # Planning apprenants — annoter chaque jf
        _pl_list = db.query(PlanningApprenant).filter(
            PlanningApprenant.jour_formation_id.in_(_af_ids)
        ).all() if _af_ids else []
        for jf in jours_formation:
            _pl_this = [pa for pa in _pl_list if pa.jour_formation_id == jf.id]
            jf.planning = {}
            for pa in _pl_this:
                hpc = {}
                if pa.heures_par_cat:
                    try:
                        hpc = json.loads(pa.heures_par_cat)
                    except Exception:
                        pass
                jf.planning[pa.stagiaire_id] = {
                    "heures_theorie": pa.heures_theorie or 0.0,
                    "heures_par_cat": hpc,
                    "heures_libre": pa.heures_libre or 0.0,
                }
            _cats_set = set()
            for pa in _pl_this:
                if pa.heures_par_cat:
                    try:
                        _cats_set.update(json.loads(pa.heures_par_cat).keys())
                    except Exception:
                        pass
            jf.cats_colonnes = [c for c in categories_formation if c in _cats_set]
            jf.has_theorie = bool(jf.col_theorie) or any(v.get("heures_theorie", 0) > 0 for v in jf.planning.values())
            jf.has_libre = bool(jf.col_libre) or bool(jf.libelle_colonne_libre) or any(v.get("heures_libre", 0) > 0 for v in jf.planning.values())
            if jf.candidats_ids:
                _cids = set(json.loads(jf.candidats_ids))
                jf.candidats_list = [sc for sc in session_candidats if sc.stagiaire_id in _cids]
            else:
                jf.candidats_list = list(session_candidats)
            _avec_heures = [
                sid for sid, v in jf.planning.items()
                if v.get("heures_theorie", 0) > 0
                or v.get("heures_libre", 0) > 0
                or any(h > 0 for h in v.get("heures_par_cat", {}).values())
            ]
            jf.candidats_avec_heures_json = json.dumps(_avec_heures)

        utilisateurs_terrain = db.query(Utilisateur).filter(
            Utilisateur.role == "terrain",
            Utilisateur.actif == True
        ).order_by(Utilisateur.nom, Utilisateur.prenom).all()

        # ── AffectationTest : charger pour annotation des jours ────────────────
        _jt_ids = [j.id for j in jours_test]
        _at_list = []
        _at_users = {}
        if _jt_ids:
            try:
                _at_list = db.query(AffectationTest).filter(
                    AffectationTest.jour_test_id.in_(_jt_ids)
                ).all()
                _au_ids = list({at.user_id for at in _at_list})
                if _au_ids:
                    _at_users = {u.id: u for u in db.query(Utilisateur).filter(
                        Utilisateur.id.in_(_au_ids)
                    ).all()}
            except Exception as _e:
                print(f"[AffectationTest load error]: {_e}", flush=True)
                db.rollback()

        # ── utilisateurs_testeurs : comptes liés à une fiche testeur ───────────
        _testeur_by_user = {}
        _habs_by_tid = {}
        utilisateurs_testeurs = []
        try:
            _tf_rows = db.query(Testeur).filter(
                Testeur.utilisateur_id != None,
                Testeur.actif == True
            ).all()
            if _tf_rows:
                _testeur_by_user = {t.utilisateur_id: t for t in _tf_rows}
                _tf_ids = [t.id for t in _tf_rows]
                for _h in db.query(HabilitationTesteur).filter(
                    HabilitationTesteur.testeur_id.in_(_tf_ids),
                    HabilitationTesteur.famille == session.famille,
                    HabilitationTesteur.actif == True
                ).all():
                    _habs_by_tid.setdefault(_h.testeur_id, []).append(_h.categorie)
                _tu_list = db.query(Utilisateur).filter(
                    Utilisateur.id.in_(list(_testeur_by_user.keys())),
                    Utilisateur.actif == True
                ).order_by(Utilisateur.nom, Utilisateur.prenom).all()
                for _u2 in _tu_list:
                    _tf = _testeur_by_user.get(_u2.id)
                    utilisateurs_testeurs.append({
                        "user_id": _u2.id,
                        "nom": _u2.nom,
                        "prenom": _u2.prenom or "",
                        "habs": sorted(_habs_by_tid.get(_tf.id, [])) if _tf else [],
                    })
        except Exception as _e:
            print(f"[utilisateurs_testeurs error]: {_e}", flush=True)
            db.rollback()

        for j in jours_test:
            # testeur_nom depuis AffectationTest.principal (si disponible), sinon j.testeur_id legacy
            _ats_j = [at for at in _at_list if at.jour_test_id == j.id]
            _at_principal = next((at for at in _ats_j if at.principal), None)
            _pu = _at_users.get(_at_principal.user_id) if _at_principal else None
            if _pu:
                j.testeur_nom = f"{_pu.prenom[0]}.{_pu.nom[:3].upper()}" if _pu.prenom else _pu.nom[:3].upper()
            elif j.testeur_id:
                t = db.query(Testeur).filter(Testeur.id == j.testeur_id).first()
                j.testeur_nom = f"{t.nom} {t.prenom}" if t else "?"
            else:
                j.testeur_nom = "—"
            j.testeurs_affectes = []
            for _at in _ats_j:
                _u2 = _at_users.get(_at.user_id)
                if not _u2:
                    continue
                _tf2 = _testeur_by_user.get(_u2.id)
                _habs_u = sorted(_habs_by_tid.get(_tf2.id, [])) if _tf2 else []
                _abr_nom = f"{_u2.prenom[0]}.{_u2.nom[:3].upper()}" if _u2.prenom else _u2.nom[:3].upper()
                j.testeurs_affectes.append({
                    "user_id": _at.user_id,
                    "nom_abr": _abr_nom,
                    "habs": _habs_u,
                    "principal": _at.principal,
                })
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
                j.ut_cand_cat = {}
                j.ut_total_cat = {}
                for jtc in jtcs:
                    cats_base = {c.strip() for c in (jtc.categories or "").split(",") if c.strip()}
                    opts = {}
                    if jtc.options_planifiees:
                        try:
                            opts = json.loads(jtc.options_planifiees)
                        except Exception:
                            pass
                    cand_d = {}
                    for cat in cats_base | set(opts.keys()):
                        base = ut_par_cat.get(cat, 1.0) if cat in cats_base else 0.0
                        cand_d[cat] = ut_ligne(base, cat, opts.get(cat, []), opt_incluse_set)
                    j.ut_cand_cat[jtc.stagiaire_id] = cand_d
                    for cat, ut in cand_d.items():
                        j.ut_total_cat[cat] = round(j.ut_total_cat.get(cat, 0.0) + ut, 1)
                j.ut_cand_total = {sid: round(sum(d.values()), 1) for sid, d in j.ut_cand_cat.items()}
                total_ut = round(sum(j.ut_cand_total.values()), 1)
                nb_testeurs = math.ceil(total_ut / 6) if total_ut > 0 else 1
                j.total_ut = total_ut
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
                j.ut_cand_cat = {}
                j.ut_total_cat = {}
                j.ut_cand_total = {}
                j.total_ut = 0
                j.nb_testeurs = 0
                j.ut_libres = 0
                j.candidats_epreuves = {}

        jours_par_date: dict = {}
        for j in jours_test:
            d = j.date
            if d not in jours_par_date:
                jours_par_date[d] = {"jours": [], "candidats_ids": [], "testeurs": [], "total_ut": 0.0}
            entry = jours_par_date[d]
            entry["jours"].append(j)
            for sid in j.candidats_ids:
                if sid not in entry["candidats_ids"]:
                    entry["candidats_ids"].append(sid)
            if j.testeur_nom and j.testeur_nom != "—" and j.testeur_nom not in entry["testeurs"]:
                entry["testeurs"].append(j.testeur_nom)
            entry["total_ut"] = round(entry["total_ut"] + j.total_ut, 1)

        ut_planifie_candidat = {}
        ut_planifie_par_stag_cat = {}
        for j in jours_test:
            if j.type == 'pratique':
                for stag_id, cand_d in j.ut_cand_cat.items():
                    ut_planifie_candidat[stag_id] = round(
                        ut_planifie_candidat.get(stag_id, 0.0) + j.ut_cand_total[stag_id], 1
                    )
                    if stag_id not in ut_planifie_par_stag_cat:
                        ut_planifie_par_stag_cat[stag_id] = {}
                    for cat, ut in cand_d.items():
                        ut_planifie_par_stag_cat[stag_id][cat] = round(
                            ut_planifie_par_stag_cat[stag_id].get(cat, 0.0) + ut, 1
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
        stagiaires_json = json.dumps([{"id": s.id, "nom": s.nom or "", "prenom": s.prenom or ""} for s in stagiaires])
        testeurs_list = db.query(Testeur).filter(Testeur.actif == True).all()

        consentements_list = db.query(ConsentementRGPD).filter(
            ConsentementRGPD.session_id == session_id
        ).all()
        consentements_map = {c.stagiaire_id: c for c in consentements_list}

        _verif_testeurs = [
            {"nom_complet": f"{t.nom} {t.prenom}", "role": "testeur"}
            for t in db.query(Testeur).filter(
                Testeur.actif == True,
                Testeur.etat.in_(["actif", "suspendu"])
            ).order_by(Testeur.nom, Testeur.prenom).all()
        ]
        _verif_utilisateurs = [
            {"nom_complet": f"{u.nom} {u.prenom}", "role": u.role or "utilisateur"}
            for u in db.query(Utilisateur).filter(
                Utilisateur.actif == True
            ).order_by(Utilisateur.nom, Utilisateur.prenom).all()
        ]
        verificateurs_liste = sorted(
            _verif_testeurs + _verif_utilisateurs,
            key=lambda x: x["nom_complet"]
        )

        # ── Notes privées : accès filtré par utilisateur connecté ────────────
        _cu_id = _u.id if _u else None
        _cu_admin = bool(_u and _u.role in ('admin', 'utilisateur'))

        _principal_test_ids = {
            at.jour_test_id for at in _at_list
            if _cu_id and at.user_id == _cu_id and at.principal
        }
        _principal_formation_ids = {
            af.jour_formation_id for af in _af_list
            if _cu_id and af.user_id == _cu_id and af.principal
        }

        acces_notes_test = {}
        for _j in jours_test:
            _est_principal = _j.id in _principal_test_ids
            _a_note = bool(_j.note_privee)
            _est_auteur = _a_note and _j.note_privee_auteur_id == _cu_id
            _peut_lire = _est_auteur or (_cu_admin and _a_note)
            if _est_principal or _peut_lire:
                acces_notes_test[_j.id] = {
                    'note': _j.note_privee if _peut_lire else None,
                    'est_principal': _est_principal,
                    'est_admin_only': _cu_admin and not _est_principal,
                    'session_modifiable': session.statut != 'terminee',
                }

        acces_notes_formation = {}
        for _jf in jours_formation:
            _est_principal = _jf.id in _principal_formation_ids
            _a_note = bool(_jf.note_privee)
            _est_auteur = _a_note and _jf.note_privee_auteur_id == _cu_id
            _peut_lire = _est_auteur or (_cu_admin and _a_note)
            if _est_principal or _peut_lire:
                acces_notes_formation[_jf.id] = {
                    'note': _jf.note_privee if _peut_lire else None,
                    'est_principal': _est_principal,
                    'est_admin_only': _cu_admin and not _est_principal,
                    'session_modifiable': session.statut != 'terminee',
                }
        # ─────────────────────────────────────────────────────────────────────

        jours_pratiques_ids = [j.id for j in jours_test if j.type == 'pratique']
        attestations_neutralite_list = db.query(AttestationNeutralite).filter(
            AttestationNeutralite.jour_test_id.in_(jours_pratiques_ids)
        ).all() if jours_pratiques_ids else []
        attestations_neutralite_map = {
            (a.jour_test_id, a.stagiaire_id): a for a in attestations_neutralite_list
        }

        from app.models.utilisations_themes import UtilisationTheme as _UT
        _ut = db.query(_UT).filter(
            _UT.session_id == session_id,
            _UT.famille == session.famille
        ).first()
        tirage_declenche = _ut is not None
        date_tirage = _ut.date_tirage if _ut else None

        from app.services.session_statut import statut_affichage_session as _sas
        _a_epreuve = db.query(SessionEpreuve).filter(SessionEpreuve.session_id == session_id).first() is not None
        _a_rt = db.query(ResultatTheorie).filter(ResultatTheorie.session_id == session_id).first() is not None
        statut_affichage = ("Annulée" if session.statut == "annulee"
                            else _sas(session, a_tirage=tirage_declenche, a_epreuve=_a_epreuve, a_resultat_theorie=_a_rt))
        session_sans_resultat = tirage_declenche and not _a_epreuve and not _a_rt

        a_candidats_theorie = db.query(JourTestCandidat).join(
            JourTest, JourTest.id == JourTestCandidat.jour_test_id
        ).filter(
            JourTest.session_id == session_id,
            JourTest.type == "theorie",
            JourTest.actif == True
        ).first() is not None

        # --- Indicateur justificatif de formation (chantier table Justificatif) ---
        from app.models.justificatif import Justificatif

        # 1. Quels candidats passent au moins une epreuve (theorie OU pratique) ?
        #    = stagiaire_id present dans candidats_ids d'au moins un jour de test
        stagiaires_avec_epreuve = set()
        for j in jours_test:
            for sid in getattr(j, "candidats_ids", []) or []:
                stagiaires_avec_epreuve.add(sid)

        # 2. Justificatifs formation de la session, groupes par session_candidat_id (1 requete)
        justifs_formation = db.query(Justificatif).filter(
            Justificatif.session_id == session_id,
            Justificatif.type == "formation",
        ).all()
        nb_justif_formation_par_sc = {}
        for jf in justifs_formation:
            if jf.session_candidat_id is not None:
                nb_justif_formation_par_sc[jf.session_candidat_id] = nb_justif_formation_par_sc.get(jf.session_candidat_id, 0) + 1

        # 3. Annoter chaque SessionCandidat : passe_epreuve + nb_justif_formation
        for sc in session_candidats:
            sc.passe_epreuve = sc.stagiaire_id in stagiaires_avec_epreuve
            sc.nb_justif_formation = nb_justif_formation_par_sc.get(sc.id, 0)

        return templates.TemplateResponse(
            request=request,
            name="session_detail.html",
            context={
            "saisie_numerique_set": saisie_numerique_set,
                "page": "sessions",
                "session": session,
                "lieu": lieu,
                "session_candidats": session_candidats,
                "categories": categories,
                "categories_formation": categories_formation,
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
                "stagiaires_json": stagiaires_json,
                "testeurs": testeurs_list,
                "options_par_cat": options_par_cat,
                "opt_incluse_set": opt_incluse_set,
                "ut_planifie_par_stag_cat": ut_planifie_par_stag_cat,
                "testeur_initiales_par_stag_cat": testeur_initiales_par_stag_cat,
                "jours_par_date": jours_par_date,
                "jours_dates": [{"date": str(j.date), "type": j.type, "label": j.date.strftime('%d/%m/%Y') + ' (' + j.type + ')'} for j in jours_test if j.date],
                "consentements_map": consentements_map,
                "verificateurs_liste": verificateurs_liste,
                "attestations_neutralite_map": attestations_neutralite_map,
                "jours_formation": jours_formation,
                "utilisateurs_terrain": utilisateurs_terrain,
                "utilisateurs_testeurs": utilisateurs_testeurs,
                "user_role": _u.role if _u else None,
                "acces_notes_test": acces_notes_test,
                "acces_notes_formation": acces_notes_formation,
                "tirage_declenche": tirage_declenche,
                "date_tirage": date_tirage,
                "a_candidats_theorie": a_candidats_theorie,
                "statut_affichage": statut_affichage,
                "session_sans_resultat": session_sans_resultat,
            }
        )
    finally:
        db.close()

@app.get("/consentement/{session_id}/{stagiaire_id}/relire")
def page_consentement_relire(request: Request, session_id: int, stagiaire_id: int):
    from datetime import date
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
        consentement = db.query(ConsentementRGPD).filter(
            ConsentementRGPD.session_id == session_id,
            ConsentementRGPD.stagiaire_id == stagiaire_id
        ).first()
        if not session or not stagiaire:
            return {"error": "Non trouvé"}
        return templates.TemplateResponse(
            request=request,
            name="consentement_relire.html",
            context={
                "session": session,
                "stagiaire": stagiaire,
                "consentement": consentement,
            }
        )
    finally:
        db.close()

@app.get("/consentement/{session_id}/{stagiaire_id}")
def page_consentement(request: Request, session_id: int, stagiaire_id: int, direct: int = 0):
    from datetime import date
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
        if not session or not stagiaire:
            return {"error": "Non trouvé"}
        today = date.today().strftime('%d/%m/%Y')
        return templates.TemplateResponse(
            request=request,
            name="consentement.html",
            context={
                "session": session,
                "stagiaire": stagiaire,
                "today": today,
                "mode_direct": bool(direct),
            }
        )
    finally:
        db.close()

@app.get("/neutralite/{jour_test_id}/{stagiaire_id}/relire")
def page_neutralite_relire(request: Request, jour_test_id: int, stagiaire_id: int):
    from app.models.jour_test import JourTest
    db = SessionLocal()
    try:
        jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
        stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
        attestation = db.query(AttestationNeutralite).filter(
            AttestationNeutralite.jour_test_id == jour_test_id,
            AttestationNeutralite.stagiaire_id == stagiaire_id
        ).first()
        session = db.query(Session).filter(Session.id == jour.session_id).first() if jour else None
        return templates.TemplateResponse(
            request=request,
            name="neutralite_relire.html",
            context={
                "attestation": attestation,
                "stagiaire": stagiaire,
                "jour": jour,
                "session": session,
            }
        )
    finally:
        db.close()


@app.get("/neutralite/{jour_test_id}/{stagiaire_id}")
def page_neutralite(request: Request, jour_test_id: int, stagiaire_id: int, direct: int = 0):
    from app.models.jour_test import JourTest
    from datetime import date
    db = SessionLocal()
    try:
        jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
        stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
        today = date.today()
        return templates.TemplateResponse(
            request=request,
            name="neutralite.html",
            context={
                "jour_test_id": jour_test_id,
                "stagiaire_id": stagiaire_id,
                "stagiaire": stagiaire,
                "jour": jour,
                "today": today,
                "mode_direct": bool(direct),
            }
        )
    finally:
        db.close()


@app.get("/sessions/{session_id}/theorie/{stagiaire_id}/detail")
def page_detail_theorie(request: Request, session_id: int, stagiaire_id: int, jour_id: int = None):
    import json
    from app.models.utilisations_themes import UtilisationTheme
    db = SessionLocal()
    try:
        query = db.query(ResultatTheorie).filter(
            ResultatTheorie.session_id == session_id,
            ResultatTheorie.stagiaire_id == stagiaire_id
        )
        if jour_id:
            query = query.filter(ResultatTheorie.jour_test_id == jour_id)
        rt = query.order_by(ResultatTheorie.id.desc()).first()

        if not rt:
            return {"error": "Resultat non trouve"}

        stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
        reponses_candidat = json.loads(rt.reponses_json) if rt.reponses_json else {}
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
                reponse_candidat = reponses_candidat.get(str(ut.theme) + "_" + str(r.numero_question))
                correcte = reponse_candidat is not None and reponse_candidat == r.reponse_correcte
                detail_themes[t].append({
                    "numero": r.numero_question,
                    "texte": r.texte_question,
                    "reponse_correcte": r.reponse_correcte,
                    "reponse_candidat": reponse_candidat,
                    "correcte": correcte,
                    "points": r.points
                })

        return templates.TemplateResponse(
            request=request,
            name="detail_theorie.html",
            context={
                "stagiaire": stagiaire,
                "session": session_obj,
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
    finally:
        db.close()


@app.get("/sessions/{session_id}/pratique/saisie-en-ligne/{jour_test_id}/{stagiaire_id}/{categorie}")
def page_saisie_pratique(session_id: int, jour_test_id: int, stagiaire_id: int, categorie: str,
                         request: Request, db: DBSession = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    from app.models.jour_test import JourTest as _JT
    jour = db.query(_JT).filter(_JT.id == jour_test_id).first()

    return templates.TemplateResponse(
        request=request,
        name="saisie_pratique.html",
        context={
            "session_id": session_id,
            "jour_test_id": jour_test_id,
            "stagiaire_id": stagiaire_id,
            "categorie": categorie,
            "session_ref": session.reference if hasattr(session, "reference") else "",
            "candidat_nom": (stagiaire.nom or "") if stagiaire else "",
            "candidat_prenom": (stagiaire.prenom or "") if stagiaire else "",
            "candidat_ddn": stagiaire.date_naissance.strftime("%d/%m/%Y") if stagiaire and stagiaire.date_naissance else "",
            "recommandation": session.famille or "",
            "categorie": categorie,
        },
    )


@app.get("/sessions/{session_id}/theorie/saisie-degrade/{jour_id}")
def page_saisie_degrade(session_id: int, jour_id: int, request: Request, db: DBSession = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour introuvable")

    # Candidats inscrits sur ce jour
    candidats_ids = [
        jtc.stagiaire_id for jtc in db.query(JourTestCandidat).filter(
            JourTestCandidat.jour_test_id == jour_id,
            JourTestCandidat.actif == True,
        ).all()
    ]
    session_candidats = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.stagiaire_id.in_(candidats_ids),
        SessionCandidat.actif == True,
    ).all()
    for sc in session_candidats:
        sc.stagiaire = db.query(Stagiaire).filter(Stagiaire.id == sc.stagiaire_id).first()

    # Résultats théoriques existants pour ce jour
    rt_list = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_id,
        ResultatTheorie.stagiaire_id.in_(candidats_ids),
    ).all()
    rt_par_stagiaire = {rt.stagiaire_id: rt for rt in rt_list}

    # Tirage réel : totaux par thème depuis DB (identique à calculer_resultat_theorie_phase2)
    from app.models.utilisations_themes import UtilisationTheme as _UTd
    tirages = db.query(_UTd).filter(
        _UTd.session_id == session_id,
        _UTd.famille == session.famille,
    ).order_by(_UTd.theme).all()
    _THEME_NOMS = {
        1: 'Connaissances générales',
        2: 'Technologie et stabilité',
        3: 'Exploitation',
        4: 'Circulation',
        5: 'Fin de poste',
    }
    themes = []
    for ut in tirages:
        qs = db.query(ReponseGrille).filter(
            ReponseGrille.grille_id == ut.grille_id,
            ReponseGrille.theme == ut.theme,
        ).all()
        themes.append({
            "num": ut.theme,
            "nom": _THEME_NOMS.get(ut.theme, f"Thème {ut.theme}"),
            "total": len(qs),
        })

    # Construction de la liste candidats pour le template
    cands = []
    for sc in session_candidats:
        rt = rt_par_stagiaire.get(sc.stagiaire_id)
        rt_data = None
        if rt:
            rt_data = {
                "mode": rt.mode,
                "note_totale": rt.note_totale,
                "obtenue": rt.obtenue,
                "notes": {
                    "1": int(rt.note_theme1) if rt.note_theme1 is not None else None,
                    "2": int(rt.note_theme2) if rt.note_theme2 is not None else None,
                    "3": int(rt.note_theme3) if rt.note_theme3 is not None else None,
                    "4": int(rt.note_theme4) if rt.note_theme4 is not None else None,
                    "5": int(rt.note_theme5) if rt.note_theme5 is not None else None,
                },
                "themes_ok": {
                    "1": rt.theme1_ok, "2": rt.theme2_ok, "3": rt.theme3_ok,
                    "4": rt.theme4_ok, "5": rt.theme5_ok,
                },
                "justificatif_nom": rt.justificatif_nom or "",
                "testeur_id": rt.testeur_id,
            }
        cands.append({
            "stagiaire_id": sc.stagiaire_id,
            "nom": sc.stagiaire.nom or "" if sc.stagiaire else "",
            "prenom": sc.stagiaire.prenom or "" if sc.stagiaire else "",
            "ddn": sc.stagiaire.date_naissance.strftime('%d/%m/%Y') if sc.stagiaire and sc.stagiaire.date_naissance else "",
            "dispensee": bool(sc.theorie_dispensee),
            "rt": rt_data,
        })

    return templates.TemplateResponse(
        request=request,
        name="saisie_degrade.html",
        context={
            "session_id": session_id,
            "session_ref": session.reference or f"Session {session.id}",
            "famille": session.famille,
            "jour_id": jour_id,
            "jour_date": jour.date.strftime('%d/%m/%Y') if jour.date else "",
            "testeur_id_jour": jour.testeur_id,
            "candidats": cands,
            "themes": themes,
            "user_role": user.get("role", "") if isinstance(user, dict) else getattr(user, "role", ""),
        },
    )


@app.get("/test/theorie/{session_id}/{jour_id}")
def page_test_theorie(request: Request, session_id: int, jour_id: int):
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
        if not session or not jour:
            return {"error": "Non trouve"}
        grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == jour.grille_id).first()
        from app.models.utilisations_themes import UtilisationTheme as _UT2
        _tirage = db.query(_UT2).filter(_UT2.session_id == session_id, _UT2.famille == session.famille).first()
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
        rt_list = db.query(ResultatTheorie).filter(
            ResultatTheorie.jour_test_id == jour_id
        ).all()
        rt_par_stagiaire = {rt.stagiaire_id: rt.mode for rt in rt_list}
        candidats_eligibles_ids = [
            sc.stagiaire_id for sc in session_candidats if not sc.theorie_dispensee
        ]
        tous_notes = bool(candidats_eligibles_ids) and all(
            sid in rt_par_stagiaire for sid in candidats_eligibles_ids
        )
        return templates.TemplateResponse(
            request=request,
            name="test_theorie.html",
            context={
                "session_id": session_id,
                "jour_id": jour_id,
                "grille_id": jour.grille_id,
                "echantillon_h": (lambda c: c.echantillon_audio_h if c else None)(db.query(ConfigOrganisme).first()),
                "echantillon_f": (lambda c: c.echantillon_audio_f if c else None)(db.query(ConfigOrganisme).first()),
                "grille_numero": grille.numero if grille else "Phase 2",
                "session_candidats": session_candidats,
                "terrain_gele": session.date_cloture_terrain is not None,
                "tirage_declenche": _tirage is not None,
                "rt_par_stagiaire": rt_par_stagiaire,
                "tous_notes": tous_notes,
                "famille": session.famille,
                "testeur_id_jour": jour.testeur_id,
            }
        )
    finally:
        db.close()


@app.get("/test/theorie/{jour_test_id}/{stagiaire_id}/start")
def page_test_theorie_start(request: Request, jour_test_id: int, stagiaire_id: int):
    db = SessionLocal()
    try:
        jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
        if not jour:
            return {"error": "Non trouve"}
        session = db.query(Session).filter(Session.id == jour.session_id).first()
        grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == jour.grille_id).first() if jour.grille_id else None
        stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
        from app.models.utilisations_themes import UtilisationTheme as _UT3
        _tirage2 = db.query(_UT3).filter(_UT3.session_id == jour.session_id, _UT3.famille == session.famille).first() if session else None
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
        rt_list = db.query(ResultatTheorie).filter(
            ResultatTheorie.jour_test_id == jour_test_id
        ).all()
        rt_par_stagiaire = {rt.stagiaire_id: rt.mode for rt in rt_list}
        candidats_eligibles_ids = [
            sc.stagiaire_id for sc in session_candidats if not sc.theorie_dispensee
        ]
        tous_notes = bool(candidats_eligibles_ids) and all(
            sid in rt_par_stagiaire for sid in candidats_eligibles_ids
        )
        return templates.TemplateResponse(
            request=request,
            name="test_theorie.html",
            context={
                "session_id": jour.session_id,
                "jour_id": jour_test_id,
                "grille_id": jour.grille_id,
                "echantillon_h": (lambda c: c.echantillon_audio_h if c else None)(db.query(ConfigOrganisme).first()),
                "echantillon_f": (lambda c: c.echantillon_audio_f if c else None)(db.query(ConfigOrganisme).first()),
                "grille_numero": grille.numero if grille else "Phase 2",
                "session_candidats": session_candidats,
                "start_direct": True,
                "start_stagiaire_id": stagiaire_id,
                "start_nom": stagiaire.nom if stagiaire else "",
                "start_prenom": stagiaire.prenom if stagiaire else "",
                "start_ddn": stagiaire.date_naissance.isoformat() if stagiaire and stagiaire.date_naissance else "",
                "terrain_gele": session.date_cloture_terrain is not None if session else False,
                "tirage_declenche": _tirage2 is not None,
                "rt_par_stagiaire": rt_par_stagiaire,
                "tous_notes": tous_notes,
                "famille": session.famille if session else "",
                "testeur_id_jour": jour.testeur_id,
            }
        )
    finally:
        db.close()


@app.get("/non-conformites")
def page_non_conformites(request: Request):
    import json
    db = SessionLocal()
    try:
        nc_list = db.query(NonConformite).order_by(NonConformite.date.desc()).all()
        utilisateurs_list = db.query(Utilisateur).all()
        utilisateurs_map = {u.id: u for u in utilisateurs_list}
        session_ids = [nc.session_id for nc in nc_list if nc.session_id]
        sessions_map = {s.id: s for s in db.query(Session).filter(Session.id.in_(session_ids)).all()} if session_ids else {}
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
            "session_id": nc.session_id,
            "session_ref": sessions_map[nc.session_id].reference if nc.session_id and nc.session_id in sessions_map else None,
        } for nc in nc_list])
        return templates.TemplateResponse(
            request=request,
            name="non_conformites.html",
            context={
                "page": "non_conformites",
                "non_conformites": nc_list,
                "utilisateurs": utilisateurs_map,
                "sessions_map": sessions_map,
                "nc_json": nc_json,
            }
        )
    finally:
        db.close()

@app.get("/caces-obtenus")
def page_caces_obtenus(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="caces_obtenus.html",
        context={"page": "caces_obtenus"}
    )


@app.get("/registre-caces")
def page_registre_caces(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="registre_caces.html",
        context={"page": "registre_caces"}
    )

@app.get("/cartes-caces")
def page_cartes_caces(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="cartes_caces.html",
        context={"page": "cartes_caces"}
    )

@app.get("/aide")
def page_aide(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return _RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="aide.html",
        context={"page": "aide"}
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


@app.get("/verifier/{token}")
def page_verifier_carte(token: str, request: Request, db: DBSession = Depends(get_db)):
    from datetime import date as _date, datetime as _dt
    config = db.query(ConfigOrganisme).first()
    today = _date.today()
    from app.models.carte_caces import CarteCaces as _CC
    carte = (
        db.query(_CC).filter(_CC.token_verification == token).first()
        or db.query(_CC).filter(_CC.numero_carte == token).first()
    )
    if not carte:
        return templates.TemplateResponse(
            request=request,
            name="verifier.html",
            context={"statut": "introuvable", "numero_carte": token, "config": config, "today": today},
        )
    s = db.query(Stagiaire).filter(Stagiaire.id == carte.stagiaire_id).first()
    from app.routers.cartes_caces import _parse_snapshot
    raw, frozen_photo = _parse_snapshot(carte.caces_json)

    def _fmt(iso):
        if not iso:
            return ""
        try:
            return _dt.fromisoformat(iso[:10]).strftime("%d/%m/%Y")
        except Exception:
            return iso

    caces_list = [
        {**c,
         "date_obtention_fmt": _fmt(c.get("date_obtention")),
         "date_echeance_fmt": _fmt(c.get("date_echeance")),
         "echeance_expired": bool(c.get("date_echeance") and c["date_echeance"][:10] < today.isoformat()),
         }
        for c in raw
    ]
    return templates.TemplateResponse(
        request=request,
        name="verifier.html",
        context={
            "statut": carte.statut,
            "numero_carte": carte.numero_carte,
            "date_generation": carte.date_generation,
            "famille": carte.famille,
            "stagiaire_nom": s.nom if s else "",
            "stagiaire_prenom": ((s.prenom[0] + ".") if s and s.prenom else ""),
            "stagiaire_ddn_annee": s.date_naissance.year if s and s.date_naissance else None,
            "photo_url": (
                f"data:image/jpeg;base64,{frozen_photo}" if frozen_photo
                else ((s.photo_base64 and f"data:image/jpeg;base64,{s.photo_base64}") or s.photo or "" if s else "")
            ),
            "caces_list": caces_list,
            "config": config,
            "today": today,
        },
    )

@app.get("/login")
def page_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )