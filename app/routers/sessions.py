from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.services import storage
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.session import Session
from app.utils_famille import fam_variantes
from app.models.session_candidat import SessionCandidat
from app.models.session_epreuve import SessionEpreuve
from app.models.equipement import Equipement
from app.models.stagiaire import Stagiaire
from app.models.testeur import Testeur
from app.models.categorie import Categorie, Famille
from app.models.jour_test import JourTest, JourTestCandidat, ResultatTheorie, BrouillonTheorie
from app.models.jour_formation import JourFormation, AffectationFormation, PlanningApprenant, AffectationTest
from app.models.caces_obtenu import CacesObtenu
from app.models.justificatif import Justificatif
from app.models.grille_theorie import GrilleTheorie, ReponseGrille, UtilisationGrille
from app.models.consentement_rgpd import ConsentementRGPD
from app.models.utilisations_themes import UtilisationTheme
from app.models.non_conformite import NonConformite
from app.services.tirage_grille import (
    tirer_grille, calculer_resultat_theorie, enregistrer_tirage_grille, mode_vers_regime,
    tirer_themes_phase2, enregistrer_tirage_themes,
    get_questions_phase2, calculer_resultat_theorie_phase2,
    tirage_to_json
)
from app.services.caces_obtenus import calculer_et_synchroniser
from app.models.utilisateur import Utilisateur
from app.routers.auth import get_utilisateur_courant
from app.config_utils import get_pin_admin, get_pin_formateur, get_mode_tirage
from pydantic import BaseModel, model_validator
from datetime import date, datetime as dt
from typing import Optional, List, Dict
import json
import math


def _appliquer_tracabilite_dispense(sc, data, db, stagiaire_id, famille, session_id):
    if not data.theorie_dispensee:
        sc.dispense_origine = None
        sc.dispense_source_type = None
        sc.dispense_source_id = None
        return
    if data.dispense_origine_choisie == "externe":
        sc.dispense_origine = "externe"
        sc.dispense_source_type = None
        sc.dispense_source_id = None
        return
    from app.services.caces_obtenus import detecter_base_theorique
    _base = detecter_base_theorique(db, stagiaire_id, famille, session_id)
    if _base.get("possible"):
        sc.dispense_origine = "interne"
        sc.dispense_source_type = _base.get("type")
        sc.dispense_source_id = _base.get("source_id")
    else:
        sc.dispense_origine = "externe"
        sc.dispense_source_type = None
        sc.dispense_source_id = None


router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

class JourModifData(BaseModel):
    date: Optional[str] = None
    note: Optional[str] = None

class SessionCreate(BaseModel):
    famille: str
    lieu_id: int
    reference: Optional[str] = None
    date_theorie: Optional[date] = None
    date_pratique_debut: Optional[date] = None
    date_pratique_fin: Optional[date] = None
    note: Optional[str] = None
    responsable: Optional[str] = None

class SessionResponse(BaseModel):
    id: int
    famille: str
    lieu_id: int
    reference: Optional[str] = None
    date_theorie: Optional[date] = None
    date_pratique_debut: Optional[date] = None
    date_pratique_fin: Optional[date] = None
    statut: str
    annee: int
    responsable: Optional[str] = None

    class Config:
        from_attributes = True

class SessionCandidatCreate(BaseModel):
    session_id: int
    stagiaire_id: int
    rgpd_accepte: bool = True
    photo_accepte: bool = True
    theorie_dispensee: bool = False
    dispense_note: Optional[str] = None
    dispense_date: Optional[date] = None
    dispense_echeance: Optional[date] = None
    dispense_origine_choisie: Optional[str] = None

class EquipementCreate(BaseModel):
    session_id: int
    numero: int
    designation: Optional[str] = None
    marque: Optional[str] = None
    type_modele: Optional[str] = None
    numero_serie: Optional[str] = None
    date_verification: Optional[date] = None
    organisme_verification: Optional[str] = None
    proprietaire: Optional[str] = None

class CandidatJourPratique(BaseModel):
    stagiaire_id: int
    categories: List[str] = []
    options: Dict[str, List[str]] = {}

    @model_validator(mode="after")
    def _options_rattachees_a_categorie(self):
        # Garde-fou INRS : une option n'existe pas sans sa categorie support passee.
        # On ecarte silencieusement toute option orpheline (categorie non cochee/passee).
        if self.options:
            cats = set(self.categories)
            self.options = {
                cat: opts for cat, opts in self.options.items() if cat in cats
            }
        return self

class JourTestCreate(BaseModel):
    session_id: int
    date: date
    type: str
    note: Optional[str] = None
    candidats: List[int] = []
    candidats_pratique: List[CandidatJourPratique] = []

class AjoutCandidatsJour(BaseModel):
    candidats: List[int] = []
    candidats_pratique: List[CandidatJourPratique] = []

class ReponsesCandidatCreate(BaseModel):
    jour_test_id: int
    stagiaire_id: int
    reponses: dict
    testeur_id: Optional[int] = None


class BrouillonCreate(BaseModel):
    jour_test_id: int
    stagiaire_id: int
    reponses: dict
    demarrer: bool = False

class EpreuveCreate(BaseModel):
    session_id: int
    stagiaire_id: int
    testeur_id: int
    date: date
    famille: str
    categorie: str
    obtenue: bool
    note_testeur: Optional[str] = None
    options_obtenues: Optional[str] = None

def _check_modifiable(session: Session):
    if session and session.statut in ("terminee", "annulee"):
        raise HTTPException(status_code=409, detail="Session verrouillée — réouvrez-la d'abord")


def assert_modifiable_terrain(session: Session, role: str):
    if role == "terrain" and session and session.date_cloture_terrain is not None:
        raise HTTPException(
            status_code=403,
            detail="Session clôturée terrain — modification impossible. Demandez la réouverture au back-office."
        )


def session_a_des_donnees(session_id: int, db: DBSession) -> bool:
    # Soft-deleted : ne compter que les enregistrements actifs
    for model in [JourTest, SessionCandidat]:
        if db.query(model).filter(
            model.session_id == session_id, model.actif == True
        ).first():
            return True
    # Hard-deleted ou sans soft-delete : toute ligne est une vraie donnée
    for model in [ResultatTheorie, JourFormation, SessionEpreuve,
                  Equipement, CacesObtenu, UtilisationGrille]:
        if db.query(model).filter(model.session_id == session_id).first():
            return True
    if db.query(NonConformite).filter(NonConformite.session_id == session_id).first():
        return True
    if db.query(ConsentementRGPD).filter(ConsentementRGPD.session_id == session_id).first():
        return True
    return False


@router.get("/search")
def search_sessions(q: str = "", db: DBSession = Depends(get_db)):
    rows = db.query(Session).filter(
        Session.reference.ilike(f"%{q}%"),
        (Session.type != "reprise") | (Session.type.is_(None)),
    ).order_by(Session.id.desc()).limit(10).all()
    return [{"id": s.id, "reference": s.reference or f"Session #{s.id}", "famille": s.famille, "statut": s.statut} for s in rows]

@router.get("/", response_model=list[SessionResponse])
def liste_sessions(db: DBSession = Depends(get_db)):
    return db.query(Session).filter((Session.type != "reprise") | (Session.type.is_(None))).order_by(Session.id.desc()).all()

@router.post("/", response_model=SessionResponse)
def create_session(data: SessionCreate, db: DBSession = Depends(get_db)):
    from datetime import datetime
    annee = datetime.now().year
    if not data.reference:
        import re as _re
        _prefix = f"SESSION-{annee}-"
        _refs = db.query(Session.reference).filter(
            Session.reference.like(f"{_prefix}%")
        ).all()
        _nums = []
        for (_r,) in _refs:
            _m = _re.search(r'-(\d+)$', _r or "")
            if _m:
                _nums.append(int(_m.group(1)))
        _next = (max(_nums) + 1) if _nums else 1
        data.reference = f"{_prefix}{str(_next).zfill(3)}"
    if not data.date_pratique_debut or not data.date_pratique_fin:
        raise HTTPException(400, "Les dates de début et de fin sont obligatoires")
    if data.date_pratique_debut > data.date_pratique_fin:
        raise HTTPException(400, "La date de début doit être ≤ à la date de fin")
    s = Session(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/{id}")
def delete_session(id: int, pin: str, db: DBSession = Depends(get_db)):
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    if db.query(UtilisationTheme).filter(UtilisationTheme.session_id == id).first():
        raise HTTPException(
            status_code=400,
            detail="Cette session a un tirage déclenché et ne peut plus être supprimée."
        )
    if db.query(NonConformite).filter(NonConformite.session_id == id).first():
        raise HTTPException(
            status_code=400,
            detail="Des non-conformités sont liées à cette session — déliez-les d'abord."
        )
    if session_a_des_donnees(id, db):
        raise HTTPException(
            status_code=400,
            detail="Cette session contient des données (jours, épreuves, stagiaires, matériel, CACES® ou consentements). Clôturez-la depuis la vue détail."
        )
    # Nettoyer les enregistrements soft-deletés avant suppression (FK PostgreSQL)
    jour_ids = [row.id for row in db.query(JourTest.id).filter(JourTest.session_id == id).all()]
    if jour_ids:
        db.query(AffectationTest).filter(AffectationTest.jour_test_id.in_(jour_ids)).delete(synchronize_session=False)
        db.query(JourTest).filter(JourTest.session_id == id).delete(synchronize_session=False)
    db.query(SessionCandidat).filter(SessionCandidat.session_id == id).delete(synchronize_session=False)
    db.delete(s)
    db.commit()
    return {"message": "Session supprimee"}

@router.post("/{id}/cloturer")
def cloturer_session(id: int, db: DBSession = Depends(get_db),
                     current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")

    candidats_actifs = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == id,
        SessionCandidat.actif == True
    ).all()
    consentements = {
        c.stagiaire_id: c
        for c in db.query(ConsentementRGPD).filter(ConsentementRGPD.session_id == id).all()
    }
    en_attente = []
    for sc in candidats_actifs:
        c = consentements.get(sc.stagiaire_id)
        if not c or c.horodatage is None:
            stag = db.query(Stagiaire).filter(Stagiaire.id == sc.stagiaire_id).first()
            nom = f"{stag.nom} {stag.prenom}" if stag else str(sc.stagiaire_id)
            en_attente.append(nom)
    if en_attente:
        raise HTTPException(
            status_code=400,
            detail="Consentement RGPD manquant pour : " + ", ".join(en_attente)
        )

    s.statut = "terminee"
    db.commit()
    # Recalcule les CacesObtenu a_valider : les théories issues de cette session
    # passent en mode extension (date_echeance = échéance CACES® initial)
    calculer_et_synchroniser(db)
    return {"message": "Session cloturee"}

# CANDIDATS
@router.post("/{session_id}/candidats")
def add_candidat(session_id: int, data: SessionCandidatCreate, db: DBSession = Depends(get_db),
                 current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    existing = db.query(SessionCandidat).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.stagiaire_id == data.stagiaire_id,
        SessionCandidat.actif == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Candidat deja inscrit")
    sc = SessionCandidat(**data.model_dump(exclude={"dispense_origine_choisie"}))
    _appliquer_tracabilite_dispense(sc, data, db, data.stagiaire_id, s.famille, session_id)
    sc.dispense_echeance = data.dispense_echeance if (data.theorie_dispensee and sc.dispense_origine == "externe") else None
    if sc.dispense_origine == "externe":
        from app.services.caces_obtenus import limite_12_mois
        if not data.dispense_date:
            raise HTTPException(status_code=400, detail="Dispense externe : la date d'obtention justifiant la dispense est obligatoire.")
        if limite_12_mois(data.dispense_date) < date.today():
            raise HTTPException(status_code=400, detail="Dispense externe : la base invoquee a plus de 12 mois (theorie perimee).")
        if not data.dispense_echeance:
            raise HTTPException(status_code=400, detail="Dispense externe : la date d'echeance (reportee du CACES externe) est obligatoire.")
        from app.services.caces_obtenus import _date_echeance
        _borne_haute = _date_echeance(s.famille, data.dispense_date)
        if data.dispense_echeance <= data.dispense_date:
            raise HTTPException(status_code=400, detail="Date d'echeance incoherente : elle doit etre posterieure a la date de base externe.")
        if data.dispense_echeance > _borne_haute:
            raise HTTPException(status_code=400, detail="Date d'echeance incoherente : elle depasse la duree maximale du CACES a partir de la date de base externe (verifiez le justificatif).")
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return {"message": "Candidat ajoute", "id": sc.id}

@router.put("/{session_id}/candidats/{id}")
def update_candidat(session_id: int, id: int, data: SessionCandidatCreate, db: DBSession = Depends(get_db),
                    current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    sc = db.query(SessionCandidat).filter(SessionCandidat.id == id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    # --- Verrou reglementaire : un CACES delivre (valide) gele la dispense ---
    _caces_valide = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == sc.stagiaire_id,
        CacesObtenu.session_id == sc.session_id,
        CacesObtenu.statut == "valide",
    ).first()
    if _caces_valide:
        _dispense_change = (
            bool(data.theorie_dispensee) != bool(sc.theorie_dispensee)
            or (data.dispense_date or None) != (sc.dispense_date or None)
            or (data.dispense_echeance or None) != (sc.dispense_echeance or None)
            or ((data.dispense_note or None) != (sc.dispense_note or None))
        )
        if _dispense_change:
            raise HTTPException(
                status_code=409,
                detail="Un CACES delivre repose sur cette base de dispense. Annulez d'abord le CACES (page CACES obtenus) avant de modifier la dispense de ce candidat.",
            )
    sc.theorie_dispensee = data.theorie_dispensee
    sc.dispense_note = data.dispense_note if data.theorie_dispensee else None
    sc.dispense_date = data.dispense_date if data.theorie_dispensee else None
    _appliquer_tracabilite_dispense(sc, data, db, sc.stagiaire_id, s.famille, sc.session_id)
    sc.dispense_echeance = data.dispense_echeance if (data.theorie_dispensee and sc.dispense_origine == "externe") else None
    if sc.dispense_origine == "externe":
        from app.services.caces_obtenus import limite_12_mois
        if not data.dispense_date:
            raise HTTPException(status_code=400, detail="Dispense externe : la date d'obtention justifiant la dispense est obligatoire.")
        if limite_12_mois(data.dispense_date) < date.today():
            raise HTTPException(status_code=400, detail="Dispense externe : la base invoquee a plus de 12 mois (theorie perimee).")
        if not data.dispense_echeance:
            raise HTTPException(status_code=400, detail="Dispense externe : la date d'echeance (reportee du CACES externe) est obligatoire.")
        from app.services.caces_obtenus import _date_echeance
        _borne_haute = _date_echeance(s.famille, data.dispense_date)
        if data.dispense_echeance <= data.dispense_date:
            raise HTTPException(status_code=400, detail="Date d'echeance incoherente : elle doit etre posterieure a la date de base externe.")
        if data.dispense_echeance > _borne_haute:
            raise HTTPException(status_code=400, detail="Date d'echeance incoherente : elle depasse la duree maximale du CACES a partir de la date de base externe (verifiez le justificatif).")
    db.commit()
    return {"message": "Candidat mis a jour"}

@router.delete("/{session_id}/candidats/{id}")
def remove_candidat(session_id: int, id: int, pin: str = "", db: DBSession = Depends(get_db),
                    current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="PIN invalide")
    sc = db.query(SessionCandidat).filter(SessionCandidat.id == id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    planifie = db.query(JourTestCandidat).join(
        JourTest, JourTest.id == JourTestCandidat.jour_test_id
    ).filter(
        JourTest.session_id == session_id,
        JourTestCandidat.stagiaire_id == sc.stagiaire_id
    ).first()
    if planifie:
        raise HTTPException(
            status_code=400,
            detail="Ce candidat est planifié dans le séquençage, retirez-le d'abord des jours avant de le supprimer"
        )
    # Purge du justificatif de dispense sur R2 (ne part jamais avec la ligne)
    if sc.dispense_fichier_cle:
        try:
            storage.delete_fichier(sc.dispense_fichier_cle)
        except Exception:
            pass

    # Purge du consentement RGPD lie au candidat (couple session_id + stagiaire_id)
    db.query(ConsentementRGPD).filter(
        ConsentementRGPD.session_id == session_id,
        ConsentementRGPD.stagiaire_id == sc.stagiaire_id,
    ).delete(synchronize_session=False)

    # Hard delete : la ligne + colonnes dispense/note/date/fichier_* partent avec
    db.delete(sc)
    db.commit()
    return {"message": "Candidat supprime"}

# EQUIPEMENTS
@router.post("/{session_id}/equipements")
def add_equipement(session_id: int, data: EquipementCreate, db: DBSession = Depends(get_db),
                   current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    e = Equipement(**data.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"message": "Equipement ajoute", "id": e.id}

@router.put("/{session_id}/equipements/{id}")
def update_equipement(session_id: int, id: int, data: EquipementCreate, db: DBSession = Depends(get_db),
                      current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    e = db.query(Equipement).filter(Equipement.id == id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Equipement non trouve")
    for key, value in data.model_dump().items():
        setattr(e, key, value)
    db.commit()
    return {"message": "Equipement mis a jour"}

@router.delete("/{session_id}/equipements/{id}")
def delete_equipement(session_id: int, id: int, db: DBSession = Depends(get_db),
                      current_user: Utilisateur = Depends(get_utilisateur_courant)):
    session = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(session)
    assert_modifiable_terrain(session, current_user.role)
    e = db.query(Equipement).filter(Equipement.id == id, Equipement.session_id == session_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Equipement non trouve")
    db.delete(e)
    db.commit()
    return {"message": "Equipement supprime"}

# JOURS DE TEST
@router.post("/{session_id}/jours")
def add_jour_test(session_id: int, data: JourTestCreate, db: DBSession = Depends(get_db),
                  current_user: Utilisateur = Depends(get_utilisateur_courant)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    _check_modifiable(session)
    assert_modifiable_terrain(session, current_user.role)

    jour = JourTest(
        session_id=session_id,
        date=data.date,
        type=data.type,
        grille_id=None,
        note=data.note
    )
    db.add(jour)
    db.flush()

    if data.type == "theorie":
        for stagiaire_id in data.candidats:
            jtc = JourTestCandidat(
                jour_test_id=jour.id,
                stagiaire_id=stagiaire_id
            )
            db.add(jtc)
    else:
        for cp in data.candidats_pratique:
            jtc = JourTestCandidat(
                jour_test_id=jour.id,
                stagiaire_id=cp.stagiaire_id,
                categories=",".join(cp.categories),
                options_planifiees=json.dumps(cp.options) if cp.options else None
            )
            db.add(jtc)

    db.commit()
    db.refresh(jour)

    return {"message": "Jour de test ajoute", "id": jour.id}

@router.post("/{session_id}/jours/{jour_id}/candidats")
def add_candidats_jour(session_id: int, jour_id: int, data: AjoutCandidatsJour, db: DBSession = Depends(get_db),
                       current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()

    if jour and jour.type == "pratique":
        for cp in data.candidats_pratique:
            existing = db.query(JourTestCandidat).filter(
                JourTestCandidat.jour_test_id == jour_id,
                JourTestCandidat.stagiaire_id == cp.stagiaire_id
            ).first()
            if existing:
                old_cats = set(c.strip() for c in existing.categories.split(',') if c.strip()) if existing.categories else set()
                new_cats = set(cp.categories)
                for cat in (old_cats - new_cats):
                    ep = db.query(SessionEpreuve).filter(
                        SessionEpreuve.session_id == session_id,
                        SessionEpreuve.stagiaire_id == cp.stagiaire_id,
                        SessionEpreuve.categorie == cat,
                        SessionEpreuve.date == jour.date
                    ).first()
                    if ep:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Supprimez d'abord le résultat de la catégorie {cat} avant de la retirer"
                        )
                existing.categories = ",".join(cp.categories)
                existing.options_planifiees = json.dumps(cp.options) if cp.options else None
            else:
                jtc = JourTestCandidat(
                    jour_test_id=jour_id,
                    stagiaire_id=cp.stagiaire_id,
                    categories=",".join(cp.categories),
                    options_planifiees=json.dumps(cp.options) if cp.options else None
                )
                db.add(jtc)
    else:
        existing_ids = db.query(JourTestCandidat.stagiaire_id).filter(
            JourTestCandidat.jour_test_id == jour_id,
            JourTestCandidat.stagiaire_id.in_(data.candidats)
        ).all()
        if existing_ids:
            raise HTTPException(status_code=400, detail="Certains candidats sont déjà affectés à ce jour")
        for stagiaire_id in data.candidats:
            db.add(JourTestCandidat(jour_test_id=jour_id, stagiaire_id=stagiaire_id))
    db.commit()
    return {"message": "Candidats ajoutes"}

@router.delete("/{session_id}/jours/{id}")
def delete_jour_test(session_id: int, id: int, db: DBSession = Depends(get_db),
                     current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    j = db.query(JourTest).filter(JourTest.id == id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouve")

    # Niveau 0 — refus si des candidats sont encore inscrits (théorie ET pratique)
    if db.query(JourTestCandidat).filter(JourTestCandidat.jour_test_id == j.id).first():
        raise HTTPException(
            status_code=409,
            detail="Retirez d'abord les candidats de ce jour avant de le supprimer."
        )

    if j.type == "theorie":
        # Niveau 1 — blocage si CACES délivré sur une théorie réussie de ce jour
        rt_positifs = db.query(ResultatTheorie).filter(
            ResultatTheorie.jour_test_id == j.id,
            ResultatTheorie.obtenue == True,
        ).all()
        if rt_positifs:
            stagiaire_ids = [rt.stagiaire_id for rt in rt_positifs]
            co = db.query(CacesObtenu).filter(
                CacesObtenu.session_id == session_id,
                CacesObtenu.stagiaire_id.in_(stagiaire_ids),
                CacesObtenu.statut.in_(["a_valider", "valide"]),
            ).first()
            if co:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Impossible de supprimer : un ou plusieurs CACES ont été délivrés "
                        "sur ce jour. Annulez-les d'abord via le workflow d'annulation CACES."
                    ),
                )
        # Niveau 2 — refus si des résultats théoriques existent
        if db.query(ResultatTheorie).filter(ResultatTheorie.jour_test_id == j.id).first():
            raise HTTPException(
                status_code=409,
                detail=(
                    "Ce jour contient des enregistrements. Supprimez d'abord les résultats "
                    "de chaque candidat avant de pouvoir supprimer ce jour."
                ),
            )

    if j.type == "pratique":
        candidats_jour = db.query(JourTestCandidat).filter(
            JourTestCandidat.jour_test_id == j.id
        ).all()
        # Niveau 1 — blocage si CACES délivré sur une épreuve de ce jour
        for jtc in candidats_jour:
            cats = [c for c in (jtc.categories or "").split(",") if c]
            for cat in cats:
                co = db.query(CacesObtenu).filter(
                    CacesObtenu.session_id == session_id,
                    CacesObtenu.stagiaire_id == jtc.stagiaire_id,
                    CacesObtenu.categorie == cat,
                    CacesObtenu.statut.in_(["a_valider", "valide"]),
                ).first()
                if co:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Impossible de supprimer : un ou plusieurs CACES ont été délivrés "
                            "sur ce jour. Annulez-les d'abord via le workflow d'annulation CACES."
                        ),
                    )
        # Niveau 2 — refus si des épreuves pratiques existent
        for jtc in candidats_jour:
            cats = [c for c in (jtc.categories or "").split(",") if c]
            for cat in cats:
                if db.query(SessionEpreuve).filter(
                    SessionEpreuve.session_id == session_id,
                    SessionEpreuve.stagiaire_id == jtc.stagiaire_id,
                    SessionEpreuve.categorie == cat,
                ).first():
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Ce jour contient des enregistrements. Supprimez d'abord les résultats "
                            "de chaque candidat avant de pouvoir supprimer ce jour."
                        ),
                    )

    # Niveau 3 — jour vide : soft delete + nettoyage metadata grille (théorie uniquement)
    j.actif = False

    if j.type == "theorie" and j.grille_id:
        uti = db.query(UtilisationGrille).filter(
            UtilisationGrille.grille_id == j.grille_id,
            UtilisationGrille.session_id == j.session_id,
        ).first()
        if uti:
            db.delete(uti)

    db.commit()
    return {"message": "Jour supprime"}

def _finaliser_brouillons_expires(session_id: int, db: DBSession):
    """Cree le ResultatTheorie pour les brouillons dont le temps (60 min) est ecoule
    et qui n'ont pas encore de resultat. Appele par le polling etat-live : un test
    abandonne (navigateur ferme) est ainsi finalise automatiquement, sans action testeur."""
    DUREE_S = 60 * 60
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return
    brouillons = db.query(BrouillonTheorie).filter(
        BrouillonTheorie.session_id == session_id,
        BrouillonTheorie.date_debut.isnot(None),
    ).all()
    for b in brouillons:
        ecoule = (dt.utcnow() - b.date_debut).total_seconds()
        if ecoule < DUREE_S:
            continue
        existe = db.query(ResultatTheorie).filter(
            ResultatTheorie.jour_test_id == b.jour_test_id,
            ResultatTheorie.stagiaire_id == b.stagiaire_id,
        ).first()
        if existe:
            continue
        reponses = json.loads(b.reponses_json) if b.reponses_json else {}
        try:
            resultat = calculer_resultat_theorie_phase2(reponses, session_id, session.famille, db)
        except Exception:
            continue
        rt = ResultatTheorie(
            session_id=session_id,
            stagiaire_id=b.stagiaire_id,
            jour_test_id=b.jour_test_id,
            reponses_json=json.dumps(reponses),
            note_totale=resultat["note_totale"],
            note_theme1=resultat["notes_themes"].get("1"),
            note_theme2=resultat["notes_themes"].get("2"),
            note_theme3=resultat["notes_themes"].get("3"),
            note_theme4=resultat["notes_themes"].get("4"),
            note_theme5=resultat["notes_themes"].get("5"),
            theme1_ok=resultat["themes_ok"].get("1"),
            theme2_ok=resultat["themes_ok"].get("2"),
            theme3_ok=resultat["themes_ok"].get("3"),
            theme4_ok=resultat["themes_ok"].get("4"),
            theme5_ok=resultat["themes_ok"].get("5"),
            obtenue=resultat["obtenue"],
            mode="numerique",
        )
        db.add(rt)
    db.commit()


@router.get("/{session_id}/etat-live")
def etat_live_session(session_id: int, request: Request, db: DBSession = Depends(get_db)):
    from app.models.attestation_neutralite import AttestationNeutralite
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")

    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")

    # Finalisation auto des tests theoriques dont le temps est ecoule (abandon/navigateur ferme)
    try:
        _finaliser_brouillons_expires(session_id, db)
    except Exception:
        pass

    # Candidats actifs — batch JOIN Stagiaire (pas de N+1)
    sc_rows = db.query(SessionCandidat, Stagiaire).join(
        Stagiaire, Stagiaire.id == SessionCandidat.stagiaire_id
    ).filter(
        SessionCandidat.session_id == session_id,
        SessionCandidat.actif == True
    ).order_by(Stagiaire.nom, Stagiaire.prenom).all()

    if not sc_rows:
        return {"session_id": session_id, "ts": dt.utcnow().isoformat() + "Z", "candidats": []}

    stagiaire_ids = [stag.id for _, stag in sc_rows]

    # ResultatTheorie — un par (jour_test_id, stagiaire_id), on garde le plus récent par stagiaire
    rts = db.query(ResultatTheorie).filter(
        ResultatTheorie.session_id == session_id,
        ResultatTheorie.stagiaire_id.in_(stagiaire_ids)
    ).order_by(ResultatTheorie.id.desc()).all()
    rt_par_stag: Dict[int, ResultatTheorie] = {}
    for rt in rts:
        if rt.stagiaire_id not in rt_par_stag:
            rt_par_stag[rt.stagiaire_id] = rt

    # SessionEpreuve — catégories réalisées par candidat
    epreuves = db.query(SessionEpreuve).filter(
        SessionEpreuve.session_id == session_id,
        SessionEpreuve.stagiaire_id.in_(stagiaire_ids)
    ).all()
    cats_faites: Dict[int, set] = {}
    for ep in epreuves:
        if getattr(ep, 'bloque', False):
            continue
        cats_faites.setdefault(ep.stagiaire_id, set()).add(ep.categorie)

    # Catégories planifiées (jours pratique → JourTestCandidat)
    jp_ids = [j.id for j in db.query(JourTest.id).filter(
        JourTest.session_id == session_id, JourTest.type == "pratique"
    ).all()]
    cats_planifiees: Dict[int, set] = {}
    if jp_ids:
        for jtc in db.query(JourTestCandidat).filter(
            JourTestCandidat.jour_test_id.in_(jp_ids),
            JourTestCandidat.stagiaire_id.in_(stagiaire_ids),
            JourTestCandidat.actif == True
        ).all():
            if jtc.categories:
                for cat in (c.strip() for c in jtc.categories.split(",") if c.strip()):
                    cats_planifiees.setdefault(jtc.stagiaire_id, set()).add(cat)

    # AttestationNeutralite (via jours théorie)
    jt_ids = [j.id for j in db.query(JourTest.id).filter(
        JourTest.session_id == session_id, JourTest.type == "theorie"
    ).all()]
    attest_par_stag: Dict[int, AttestationNeutralite] = {}
    if jt_ids:
        for an in db.query(AttestationNeutralite).filter(
            AttestationNeutralite.jour_test_id.in_(jt_ids),
            AttestationNeutralite.stagiaire_id.in_(stagiaire_ids)
        ).all():
            existing = attest_par_stag.get(an.stagiaire_id)
            if not existing or (an.horodatage and (not existing.horodatage or an.horodatage > existing.horodatage)):
                attest_par_stag[an.stagiaire_id] = an

    # Construction réponse
    candidats = []
    for sc, stag in sc_rows:
        sid = stag.id
        rt = rt_par_stag.get(sid)

        if (rt and rt.dispense) or sc.theorie_dispensee:
            theorie = "dispense"
        elif rt and not rt.bloque and rt.obtenue is not None:
            theorie = "passe"
        else:
            theorie = "en_attente"

        faites = cats_faites.get(sid, set())
        planifiees = cats_planifiees.get(sid, set())
        if faites and planifiees and faites >= planifiees:
            pratique = "complet"
        elif faites:
            pratique = "partiel"
        else:
            pratique = "en_attente"

        an = attest_par_stag.get(sid)
        neutralite = "signee" if (an and an.signature_base64) else "en_attente"

        candidats.append({
            "stagiaire_id": sid,
            "nom": stag.nom,
            "prenom": stag.prenom,
            "theorie": theorie,
            "pratique": pratique,
            "neutralite": neutralite,
        })

    return {
        "session_id": session_id,
        "ts": dt.utcnow().isoformat() + "Z",
        "candidats": candidats,
    }

@router.get("/{session_id}/theorie/{stagiaire_id}")
def get_resultat_theorie(session_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    rt = db.query(ResultatTheorie).filter(
        ResultatTheorie.session_id == session_id,
        ResultatTheorie.stagiaire_id == stagiaire_id
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Resultat non trouve")
    return {
        "note_totale": rt.note_totale,
        "note_theme1": rt.note_theme1,
        "note_theme2": rt.note_theme2,
        "note_theme3": rt.note_theme3,
        "note_theme4": rt.note_theme4,
        "note_theme5": rt.note_theme5,
        "obtenue": rt.obtenue,
        "reponses": json.loads(rt.reponses_json) if rt.reponses_json else {}
    }

@router.post("/{session_id}/theorie/brouillon")
def sauver_brouillon_theorie(session_id: int, data: BrouillonCreate, db: DBSession = Depends(get_db)):
    """Sauvegarde fil de l'eau des reponses en cours (SANS calcul de note ni verdict)."""
    from datetime import datetime
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    b = db.query(BrouillonTheorie).filter(
        BrouillonTheorie.jour_test_id == data.jour_test_id,
        BrouillonTheorie.stagiaire_id == data.stagiaire_id,
    ).first()
    if not b:
        b = BrouillonTheorie(
            session_id=session_id,
            jour_test_id=data.jour_test_id,
            stagiaire_id=data.stagiaire_id,
        )
        db.add(b)
    DUREE_S = 60 * 60
    if b.date_debut is not None:
        ecoule = (datetime.utcnow() - b.date_debut).total_seconds()
        if ecoule >= DUREE_S and not data.demarrer:
            raise HTTPException(status_code=409, detail="Temps ecoule")
    b.reponses_json = json.dumps(data.reponses)
    b.date_maj = datetime.utcnow()
    if data.demarrer and b.date_debut is None:
        b.date_debut = datetime.utcnow()
    db.commit()
    temps_restant = None
    expire = False
    if b.date_debut:
        ecoule = (datetime.utcnow() - b.date_debut).total_seconds()
        temps_restant = int(max(0, DUREE_S - ecoule))
        expire = ecoule >= DUREE_S
    return {
        "message": "Brouillon enregistre",
        "date_debut": b.date_debut.isoformat() if b.date_debut else None,
        "temps_restant_s": temps_restant,
        "expire": expire,
    }


@router.get("/{session_id}/theorie/brouillon/{jour_test_id}/{stagiaire_id}")
def lire_brouillon_theorie(session_id: int, jour_test_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    """Reprise : renvoie les reponses en cours + date_debut."""
    b = db.query(BrouillonTheorie).filter(
        BrouillonTheorie.jour_test_id == jour_test_id,
        BrouillonTheorie.stagiaire_id == stagiaire_id,
    ).first()
    if not b:
        return {"existe": False, "reponses": {}, "date_debut": None,
                "temps_restant_s": None, "expire": False}
    from datetime import datetime
    DUREE_S = 60 * 60
    temps_restant = None
    expire = False
    if b.date_debut:
        ecoule = (datetime.utcnow() - b.date_debut).total_seconds()
        temps_restant = int(max(0, DUREE_S - ecoule))
        expire = ecoule >= DUREE_S
    return {
        "existe": True,
        "reponses": json.loads(b.reponses_json) if b.reponses_json else {},
        "date_debut": b.date_debut.isoformat() if b.date_debut else None,
        "temps_restant_s": temps_restant,
        "expire": expire,
    }


@router.post("/{session_id}/theorie/reponses")
def soumettre_reponses_theorie(session_id: int, data: ReponsesCandidatCreate, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    _check_modifiable(session)
    if session.date_cloture_terrain is not None:
        raise HTTPException(status_code=403, detail="Session clôturée terrain — modification impossible.")
    jour = db.query(JourTest).filter(JourTest.id == data.jour_test_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour non trouve")

    try:
        resultat = calculer_resultat_theorie_phase2(data.reponses, session_id, session.famille, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == data.jour_test_id,
        ResultatTheorie.stagiaire_id == data.stagiaire_id,
    ).first()

    if existing:
        if existing.mode == "degrade":
            raise HTTPException(
                status_code=409,
                detail="Un résultat de saisie manuelle existe pour ce jour — supprimez-le d'abord (Corriger/Supprimer sous PIN).",
            )
        # mode == 'numerique' : reprise — écrasement du résultat existant
        existing.reponses_json = json.dumps(data.reponses)
        existing.note_totale = resultat["note_totale"]
        existing.note_theme1 = resultat["notes_themes"].get("1")
        existing.note_theme2 = resultat["notes_themes"].get("2")
        existing.note_theme3 = resultat["notes_themes"].get("3")
        existing.note_theme4 = resultat["notes_themes"].get("4")
        existing.note_theme5 = resultat["notes_themes"].get("5")
        existing.theme1_ok = resultat["themes_ok"].get("1")
        existing.theme2_ok = resultat["themes_ok"].get("2")
        existing.theme3_ok = resultat["themes_ok"].get("3")
        existing.theme4_ok = resultat["themes_ok"].get("4")
        existing.theme5_ok = resultat["themes_ok"].get("5")
        existing.obtenue = resultat["obtenue"]
        existing.mode = "numerique"
        if data.testeur_id is not None:
            existing.testeur_id = data.testeur_id
    else:
        rt = ResultatTheorie(
            session_id=session_id,
            stagiaire_id=data.stagiaire_id,
            jour_test_id=data.jour_test_id,
            grille_id=None,
            reponses_json=json.dumps(data.reponses),
            note_totale=resultat["note_totale"],
            note_theme1=resultat["notes_themes"].get("1"),
            note_theme2=resultat["notes_themes"].get("2"),
            note_theme3=resultat["notes_themes"].get("3"),
            note_theme4=resultat["notes_themes"].get("4"),
            note_theme5=resultat["notes_themes"].get("5"),
            theme1_ok=resultat["themes_ok"].get("1"),
            theme2_ok=resultat["themes_ok"].get("2"),
            theme3_ok=resultat["themes_ok"].get("3"),
            theme4_ok=resultat["themes_ok"].get("4"),
            theme5_ok=resultat["themes_ok"].get("5"),
            obtenue=resultat["obtenue"],
            dispense=False,
            mode="numerique",
            testeur_id=data.testeur_id,
        )
        db.add(rt)

    db.commit()
    if existing:
        db.refresh(existing)
    return {"resultat": resultat}


class TheoriePinBody(BaseModel):
    pin: str


class NotesParThemeCreate(BaseModel):
    jour_test_id: int
    stagiaire_id: int
    pin: str
    notes_par_theme: Dict[str, int]  # {"1": 8, "2": 20, …} — nb bonnes réponses saisies
    testeur_id: Optional[int] = None


@router.post("/{session_id}/theorie/reouvrir/{stagiaire_id}/{jour_test_id}")
def reouvrir_theorie(session_id: int, stagiaire_id: int, jour_test_id: int,
                     body: TheoriePinBody, db: DBSession = Depends(get_db)):
    if body.pin != get_pin_formateur(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    rt = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_test_id,
        ResultatTheorie.stagiaire_id == stagiaire_id,
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Aucun résultat théorique pour ce candidat et ce jour")
    return {
        "resultat_id": rt.id,
        "mode": rt.mode,
        "reponses": json.loads(rt.reponses_json) if rt.reponses_json else {},
        "note_totale": rt.note_totale,
        "obtenue": rt.obtenue,
        "testeur_id": rt.testeur_id,
    }


@router.delete("/{session_id}/theorie/reponses/{stagiaire_id}/{jour_test_id}")
def supprimer_resultat_theorie(session_id: int, stagiaire_id: int, jour_test_id: int,
                                body: TheoriePinBody, db: DBSession = Depends(get_db)):
    if body.pin != get_pin_formateur(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    rt = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_test_id,
        ResultatTheorie.stagiaire_id == stagiaire_id,
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Aucun résultat théorique pour ce candidat et ce jour")
    db.delete(rt)
    db.commit()
    return {"ok": True}


class JustificatifBody(BaseModel):
    pin: str
    fichier_base64: str   # contenu PDF encodé base64 (sans préfixe data:...)
    fichier_nom: str


@router.post("/{session_id}/theorie/justificatif/{stagiaire_id}/{jour_test_id}")
def upload_justificatif_theorie(session_id: int, stagiaire_id: int, jour_test_id: int,
                                 body: JustificatifBody, db: DBSession = Depends(get_db)):
    if body.pin != get_pin_formateur(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    rt = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_test_id,
        ResultatTheorie.stagiaire_id == stagiaire_id,
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Aucun résultat théorique pour ce candidat et ce jour")
    import base64 as _b64
    contenu = _b64.b64decode(body.fichier_base64)
    if rt.justificatif_cle:
        try: storage.delete_fichier(rt.justificatif_cle)
        except Exception: pass
    nom = body.fichier_nom or "justificatif.pdf"
    cle = storage.construire_cle("justificatifs/theorie", nom)
    storage.upload_fichier(contenu, cle, "application/pdf")
    rt.justificatif_cle = cle
    rt.justificatif_nom = nom
    db.commit()
    return {"ok": True, "fichier_nom": rt.justificatif_nom}


@router.get("/{session_id}/theorie/justificatif/{stagiaire_id}/{jour_test_id}")
def get_justificatif_theorie(session_id: int, stagiaire_id: int, jour_test_id: int,
                              request: Request, db: DBSession = Depends(get_db)):
    # Auth via cookie (middleware) — window.open n'envoie PAS le Bearer header.
    # Même pattern que les routes PDF sujet/corrigé.
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    import base64
    from io import BytesIO
    from fastapi.responses import StreamingResponse as SR
    rt = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_test_id,
        ResultatTheorie.stagiaire_id == stagiaire_id,
    ).first()
    if not rt or not rt.justificatif_cle:
        raise HTTPException(status_code=404, detail="Aucun justificatif pour ce résultat")
    pdf_bytes = storage.get_fichier(rt.justificatif_cle)
    nom = rt.justificatif_nom or "justificatif.pdf"
    return SR(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nom}"'},
    )


# ── Justificatif grille d'évaluation PRATIQUE (1 fichier, multi-format) ──
_EXT_AUTORISEES_PRATIQUE = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "heic": "image/heic",
    "webp": "image/webp",
}
# Formats affichables inline dans le navigateur (sinon téléchargement)
_INLINE_PRATIQUE = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
_MAX_OCTETS_PRATIQUE = 10 * 1024 * 1024  # 10 Mo


@router.post("/{session_id}/pratique/justificatif/{epreuve_id}")
def upload_justificatif_pratique(session_id: int, epreuve_id: int,
                                 body: JustificatifBody, db: DBSession = Depends(get_db)):
    if body.pin != get_pin_formateur(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    ep = db.query(SessionEpreuve).filter(
        SessionEpreuve.id == epreuve_id,
        SessionEpreuve.session_id == session_id,
    ).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Épreuve pratique introuvable")

    nom = body.fichier_nom or "justificatif"
    ext = (nom.rsplit(".", 1)[-1].lower() if "." in nom else "")
    if ext not in _EXT_AUTORISEES_PRATIQUE:
        raise HTTPException(status_code=400,
            detail="Format non autorisé. Acceptés : PDF, Excel, Word, images (jpg, png, heic, webp).")
    content_type = _EXT_AUTORISEES_PRATIQUE[ext]

    import base64 as _b64
    contenu = _b64.b64decode(body.fichier_base64)
    if len(contenu) > _MAX_OCTETS_PRATIQUE:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (10 Mo maximum).")

    if ep.justificatif_cle:
        try: storage.delete_fichier(ep.justificatif_cle)
        except Exception: pass

    cle = storage.construire_cle("justificatifs/pratique", nom)
    storage.upload_fichier(contenu, cle, content_type)
    ep.justificatif_cle = cle
    ep.justificatif_nom = nom
    db.commit()
    return {"ok": True, "fichier_nom": ep.justificatif_nom}


@router.get("/{session_id}/pratique/justificatif/{epreuve_id}")
def get_justificatif_pratique(session_id: int, epreuve_id: int,
                              request: Request, db: DBSession = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    from io import BytesIO
    from fastapi.responses import StreamingResponse as SR
    ep = db.query(SessionEpreuve).filter(
        SessionEpreuve.id == epreuve_id,
        SessionEpreuve.session_id == session_id,
    ).first()
    if not ep or not ep.justificatif_cle:
        raise HTTPException(status_code=404, detail="Aucun justificatif pour cette épreuve")
    data = storage.get_fichier(ep.justificatif_cle)
    nom = ep.justificatif_nom or "justificatif"
    ext = (nom.rsplit(".", 1)[-1].lower() if "." in nom else "")
    content_type = _EXT_AUTORISEES_PRATIQUE.get(ext, "application/octet-stream")
    disposition = "inline" if content_type in _INLINE_PRATIQUE else "attachment"
    return SR(
        BytesIO(data),
        media_type=content_type,
        headers={"Content-Disposition": f'{disposition}; filename="{nom}"'},
    )


@router.post("/{session_id}/theorie/reponses-degrade")
def soumettre_reponses_theorie_degrade(
    session_id: int,
    data: NotesParThemeCreate,
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    # a. PIN formateur
    if data.pin != get_pin_formateur(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")

    # b. Session + jour
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    _check_modifiable(session)
    if session.date_cloture_terrain is not None:
        raise HTTPException(status_code=403, detail="Session clôturée terrain — modification impossible.")
    jour = db.query(JourTest).filter(JourTest.id == data.jour_test_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour non trouvé")

    # c. Totaux réels par thème depuis le tirage (identique à calculer_resultat_theorie_phase2)
    tirages = (
        db.query(UtilisationTheme)
        .filter(
            UtilisationTheme.session_id == session_id,
            UtilisationTheme.famille == session.famille,
        )
        .all()
    )
    if not tirages:
        raise HTTPException(status_code=400, detail="Aucun tirage Phase 2 pour cette session")

    questions_par_theme: Dict[str, list] = {}
    for ut in tirages:
        questions = (
            db.query(ReponseGrille)
            .filter(
                ReponseGrille.grille_id == ut.grille_id,
                ReponseGrille.theme == ut.theme,
            )
            .order_by(ReponseGrille.numero_question)
            .all()
        )
        questions_par_theme[str(ut.theme)] = questions

    # d. Validation
    for t_str, qs in questions_par_theme.items():
        if t_str not in data.notes_par_theme:
            raise HTTPException(
                status_code=400,
                detail=f"Thème {t_str} manquant dans la saisie",
            )
        note = data.notes_par_theme[t_str]
        nb_q = len(qs)
        if note < 0 or note > nb_q:
            raise HTTPException(
                status_code=400,
                detail=f"Thème {t_str} : valeur {note} hors bornes (0–{nb_q})",
            )

    # e+f. Calcul direct — les numéros de questions sont locaux à chaque thème
    # (1–N par thème). Construire un dict global reponses_synthetique crée des
    # collisions : T5 écrase T1–T4 sur les clés "1"–"4", etc. On court-circuite
    # calculer_resultat_theorie_phase2 et on calcule directement depuis n_bonnes.
    notes_themes_d: Dict[str, float] = {}
    max_themes_d:   Dict[str, float] = {}
    themes_ok_d:    Dict[str, bool]  = {}
    note_totale_d = 0.0
    max_total_d   = 0.0
    for t_str, qs in questions_par_theme.items():
        n_bonnes   = data.notes_par_theme[t_str]
        max_theme  = sum(q.points for q in qs)
        note_theme = sum(q.points for q in qs[:n_bonnes])
        max_total_d   += max_theme
        note_totale_d += note_theme
        notes_themes_d[t_str] = round(note_theme, 1)
        max_themes_d[t_str]   = round(max_theme, 1)
        themes_ok_d[t_str]    = note_theme >= (max_theme / 2)
    pct_total_d = (note_totale_d / max_total_d * 100) if max_total_d else 0.0
    resultat = {
        "note_totale":  round(note_totale_d, 1),
        "max_total":    round(max_total_d, 1),
        "pct_total":    round(pct_total_d, 1),
        "notes_themes": notes_themes_d,
        "max_themes":   max_themes_d,
        "themes_ok":    themes_ok_d,
        "obtenue":      pct_total_d >= 70 and all(themes_ok_d.values()),
    }

    # g. Écriture ResultatTheorie
    existing = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == data.jour_test_id,
        ResultatTheorie.stagiaire_id == data.stagiaire_id,
    ).first()

    if existing:
        if existing.mode == "numerique":
            raise HTTPException(
                status_code=409,
                detail="Un résultat numérique (tablette) existe pour ce candidat — supprimez-le d'abord (Corriger/Supprimer sous PIN).",
            )
        # mode == 'degrade' : mise à jour des notes, justificatif préservé
        existing.note_totale = resultat["note_totale"]
        existing.note_theme1 = resultat["notes_themes"].get("1")
        existing.note_theme2 = resultat["notes_themes"].get("2")
        existing.note_theme3 = resultat["notes_themes"].get("3")
        existing.note_theme4 = resultat["notes_themes"].get("4")
        existing.note_theme5 = resultat["notes_themes"].get("5")
        existing.theme1_ok   = resultat["themes_ok"].get("1")
        existing.theme2_ok   = resultat["themes_ok"].get("2")
        existing.theme3_ok   = resultat["themes_ok"].get("3")
        existing.theme4_ok   = resultat["themes_ok"].get("4")
        existing.theme5_ok   = resultat["themes_ok"].get("5")
        existing.obtenue     = resultat["obtenue"]
        if data.testeur_id is not None:
            existing.testeur_id = data.testeur_id
        # reponses_json et justificatif_* intentionnellement non modifiés
    else:
        rt = ResultatTheorie(
            session_id=session_id,
            stagiaire_id=data.stagiaire_id,
            jour_test_id=data.jour_test_id,
            grille_id=None,
            reponses_json=None,
            note_totale=resultat["note_totale"],
            note_theme1=resultat["notes_themes"].get("1"),
            note_theme2=resultat["notes_themes"].get("2"),
            note_theme3=resultat["notes_themes"].get("3"),
            note_theme4=resultat["notes_themes"].get("4"),
            note_theme5=resultat["notes_themes"].get("5"),
            theme1_ok=resultat["themes_ok"].get("1"),
            theme2_ok=resultat["themes_ok"].get("2"),
            theme3_ok=resultat["themes_ok"].get("3"),
            theme4_ok=resultat["themes_ok"].get("4"),
            theme5_ok=resultat["themes_ok"].get("5"),
            obtenue=resultat["obtenue"],
            dispense=False,
            mode="degrade",
            testeur_id=data.testeur_id,
        )
        db.add(rt)

    db.commit()
    if existing:
        db.refresh(existing)
    return {"resultat": resultat}


@router.get("/{session_id}/jours/{jour_id}/grille")
def get_grille_jour(session_id: int, jour_id: int, db: DBSession = Depends(get_db)):
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour non trouve")

    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    try:
        data = get_questions_phase2(session_id, session.famille, db)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Le tirage n'a pas encore été déclenché pour cette session — déclenchez-le avant de lancer le test."
        )

    return {
        "grille_id": None,
        "grille_numero": None,
        "famille": session.famille,
        "tirage": data["tirage"],
        "themes": data["themes"]
    }

# EPREUVES PRATIQUES
@router.post("/{session_id}/epreuves")
def add_epreuve(session_id: int, data: EpreuveCreate, db: DBSession = Depends(get_db),
                current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    # G1 : bloquer si épreuve antérieure à un CACES déjà délivré (statut valide) dans la même famille
    caces_valide_posterieur = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == data.stagiaire_id,
        CacesObtenu.famille == data.famille,
        CacesObtenu.statut == "valide",
        CacesObtenu.date_obtention > data.date,
        CacesObtenu.session_id != data.session_id,
    ).first()
    if caces_valide_posterieur:
        raise HTTPException(status_code=409, detail=(
            "epreuve anterieure a un CACES deja delivre "
            "- annulez d'abord le CACES concerne. "
            "NORYX ne rattrape jamais automatiquement."
        ))
    famille = db.query(Famille).filter(Famille.code == data.famille).first()
    cat = db.query(Categorie).filter(
        Categorie.famille_id == (famille.id if famille else 0),
        Categorie.code == data.categorie
    ).first()
    from app.models.option_categorie import OptionCategorie
    incluse_codes = {
        opt.code_option
        for opt in db.query(OptionCategorie).filter(
            OptionCategorie.famille.in_(fam_variantes(data.famille)),
            OptionCategorie.categorie == data.categorie,
            OptionCategorie.incluse == True,
        ).all()
    }
    options_count = len([
        o for o in (data.options_obtenues or "").split(",")
        if o.strip() and o.strip() not in incluse_codes
    ])
    ut = (cat.ut_pratique if cat else 1.0) + options_count * 0.5

    e = db.query(SessionEpreuve).filter(
        SessionEpreuve.session_id == session_id,
        SessionEpreuve.stagiaire_id == data.stagiaire_id,
        SessionEpreuve.categorie == data.categorie,
        SessionEpreuve.date == data.date
    ).first()

    if e:
        e.testeur_id = data.testeur_id
        e.obtenue = data.obtenue
        e.note_testeur = data.note_testeur
        e.options_obtenues = data.options_obtenues
        e.ut = ut
    else:
        e = SessionEpreuve(
            session_id=session_id,
            stagiaire_id=data.stagiaire_id,
            testeur_id=data.testeur_id,
            date=data.date,
            famille=data.famille,
            categorie=data.categorie,
            ut=ut,
            obtenue=data.obtenue,
            note_testeur=data.note_testeur,
            options_obtenues=data.options_obtenues
        )
        db.add(e)

    db.commit()
    return {"message": "Epreuve ajoutee"}

@router.delete("/{session_id}/epreuves/{epreuve_id}")
def delete_epreuve(session_id: int, epreuve_id: int, pin: str = "", db: DBSession = Depends(get_db),
                   current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="PIN invalide")
    e = db.query(SessionEpreuve).filter(
        SessionEpreuve.id == epreuve_id,
        SessionEpreuve.session_id == session_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Epreuve non trouvee")

    # Nettoyage de la saisie pratique en ligne liee a cette epreuve.
    # SaisiePratique n'a pas de FK vers SessionEpreuve : lien par triplet
    # (jour_test.session_id + stagiaire_id + categorie). Sans ce nettoyage,
    # SaisieBloc / SaisieItemNote / SaisieEliminatoire restent orphelins.
    from app.models.grille_pratique import SaisiePratique
    from app.models.jour_test import JourTest
    saisies_orphelines = (
        db.query(SaisiePratique)
        .join(JourTest, JourTest.id == SaisiePratique.jour_test_id)
        .filter(
            JourTest.session_id == session_id,
            SaisiePratique.stagiaire_id == e.stagiaire_id,
            SaisiePratique.categorie == e.categorie,
        )
        .all()
    )
    for _saisie in saisies_orphelines:
        db.delete(_saisie)  # cascade ORM -> blocs, notes, eliminatoires

    db.delete(e)
    db.commit()
    return {"message": "Epreuve supprimee", "saisies_nettoyees": len(saisies_orphelines)}

class CloturerTerrainBody(BaseModel):
    pin: str

class RouvrirTerrainBody(BaseModel):
    pin: str

class ReouvrirBody(BaseModel):
    pin: str = ""

@router.post("/{id}/reouvrir")
def reouvrir_session(id: int, body: ReouvrirBody, db: DBSession = Depends(get_db),
                     current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    if body.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    s.statut = "planifiee"
    db.commit()
    return {"message": "Session reuverte"}

@router.post("/{id}/cloturer-terrain")
def cloturer_terrain(id: int, body: CloturerTerrainBody, db: DBSession = Depends(get_db),
                     current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    _check_modifiable(s)
    if body.pin != get_pin_formateur(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if s.date_cloture_terrain is not None:
        return {"message": "Session déjà clôturée terrain", "date_cloture_terrain": s.date_cloture_terrain.isoformat()}
    s.date_cloture_terrain = dt.utcnow()
    db.commit()
    return {"message": "Session clôturée terrain", "date_cloture_terrain": s.date_cloture_terrain.isoformat()}

@router.post("/{id}/rouvrir-terrain")
def rouvrir_terrain(id: int, body: RouvrirTerrainBody, db: DBSession = Depends(get_db),
                    current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Réservé au back-office")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    if body.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if s.date_cloture_terrain is None:
        return {"message": "Session terrain déjà ouverte"}
    s.date_cloture_terrain = None
    db.commit()
    return {"message": "Session terrain réouverte"}

@router.put("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}/identite")
def toggle_identite(session_id: int, jour_id: int, stagiaire_id: int, db: DBSession = Depends(get_db),
                    current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    jtc = db.query(JourTestCandidat).filter(
        JourTestCandidat.jour_test_id == jour_id,
        JourTestCandidat.stagiaire_id == stagiaire_id
    ).first()
    if not jtc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    jtc.identite_verifiee = not jtc.identite_verifiee
    db.commit()
    return {"identite_verifiee": jtc.identite_verifiee}

@router.post("/{id}/declencher-tirage")
def declencher_tirage(id: int, pin: str = "", db: DBSession = Depends(get_db),
                      current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    if s.statut == "terminee":
        raise HTTPException(status_code=400, detail="Impossible de déclencher le tirage sur une session clôturée")

    # ── Garde-fou audit : tirage suspendu tant qu'un reset est requis ──
    # Si la date d'audit externe est atteinte sans reset effectue, le
    # declenchement est bloque pour TOUT l'organisme (on ne peut pas deviner
    # quelles familles sont auditees). L'utilisateur doit reinitialiser ses
    # compteurs (Statistiques) ou corriger sa date d'audit (Administration).
    # Import local : contourne "organize imports on save" de l'IDE.
    from app.models.reset_tirage import audit_reset_requis
    _audit_date = audit_reset_requis(db)
    if _audit_date is not None:
        raise HTTPException(
            status_code=409,
            detail=("Déclenchement des tirages suspendu : votre date d'audit externe "
                    "(%s) est atteinte. Réinitialisez les compteurs de tirage "
                    "(Statistiques → Grilles) une fois l'audit terminé, ou corrigez "
                    "votre date d'audit dans Administration → Calendrier qualité."
                    % _audit_date.strftime("%d/%m/%Y")),
        )

    nb_candidats_theorie = (
        db.query(JourTestCandidat)
        .join(JourTest, JourTest.id == JourTestCandidat.jour_test_id)
        .filter(
            JourTest.session_id == id,
            JourTest.type == "theorie",
            JourTest.actif == True
        )
        .count()
    )
    if nb_candidats_theorie == 0:
        db.rollback()
        raise HTTPException(status_code=400,
            detail="Aucun candidat n'est inscrit en théorie — inscrivez au moins un candidat avant de déclencher le tirage.")

    mode = get_mode_tirage(db)
    regime = mode_vers_regime(mode)

    # Approche A : toute la donnee de tirage vit dans UtilisationTheme,
    # quel que soit le mode. La garde d'idempotence lit donc UtilisationTheme.
    existants = (
        db.query(UtilisationTheme)
        .filter(UtilisationTheme.session_id == id, UtilisationTheme.famille == s.famille)
        .all()
    )
    if existants:
        date_t = getattr(existants[0], "date_tirage", None)
        return {
            "deja_declenche": True,
            "date_tirage": date_t.isoformat() if date_t else None,
        }

    from datetime import datetime
    annee = datetime.now().year
    now = datetime.now()
    try:
        if mode == "themes":
            tirage = tirer_themes_phase2(s.famille, id, annee, db)
            enregistrer_tirage_themes(id, s.famille, annee, tirage, db, date_tirage=now, declenche_par_id=current_user.id, regime=regime)
        else:
            grille = tirer_grille(s.famille, id, annee, db)
            enregistrer_tirage_grille(id, s.famille, annee, grille, db, date_tirage=now, declenche_par_id=current_user.id, regime=regime)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {"deja_declenche": False, "date_tirage": now.isoformat()}


@router.put("/{id}")
def update_session(id: int, data: SessionCreate, db: DBSession = Depends(get_db),
                   current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    if data.famille != s.famille:
        tirage_existant = db.query(UtilisationTheme).filter(
            UtilisationTheme.session_id == id
        ).first()
        if tirage_existant:
            raise HTTPException(status_code=400,
                detail="La famille ne peut pas être modifiée après le déclenchement du tirage.")
        s.famille = data.famille
    if not data.date_pratique_debut or not data.date_pratique_fin:
        raise HTTPException(400, "Les dates de début et de fin sont obligatoires")
    if data.date_pratique_debut > data.date_pratique_fin:
        raise HTTPException(400, "La date de début doit être ≤ à la date de fin")
    debut = str(data.date_pratique_debut)
    fin = str(data.date_pratique_fin)
    jours_hors = []
    for j in db.query(JourTest).filter(JourTest.session_id == id, JourTest.actif == True).all():
        if j.date and (str(j.date) < debut or str(j.date) > fin):
            jours_hors.append(f"{j.date.strftime('%d/%m/%Y')} ({j.type})")
    for j in db.query(JourFormation).filter(JourFormation.session_id == id, JourFormation.actif == True).all():
        if j.date and (str(j.date) < debut or str(j.date) > fin):
            jours_hors.append(f"{j.date.strftime('%d/%m/%Y')} (formation)")
    if jours_hors:
        raise HTTPException(400, f"Ces jours sont hors de l'intervalle : {', '.join(jours_hors)}")
    s.date_theorie = data.date_theorie
    s.date_pratique_debut = data.date_pratique_debut
    s.date_pratique_fin = data.date_pratique_fin
    s.responsable = data.responsable
    s.note = data.note
    s.lieu_id = data.lieu_id
    s.reference = data.reference
    db.commit()
    return {"message": "Session mise a jour"}

@router.put("/{session_id}/jours/{jour_id}/modifier")
def modifier_jour(session_id: int, jour_id: int, data: JourModifData, db: DBSession = Depends(get_db),
                  current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    from datetime import date as date_type
    j = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouve")
    if data.date:
        j.date = date_type.fromisoformat(data.date)
    if data.note is not None:
        j.note = data.note or None
    db.commit()
    return {"message": "Jour modifie"}

@router.get("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}/check-theorie")
def check_resultat_theorie_candidat(session_id: int, jour_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    has_resultat = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_id,
        ResultatTheorie.stagiaire_id == stagiaire_id
    ).first() is not None
    return {"has_resultat": has_resultat}

@router.delete("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}")
def remove_candidat_jour(session_id: int, jour_id: int, stagiaire_id: int, db: DBSession = Depends(get_db),
                         current_user: Utilisateur = Depends(get_utilisateur_courant)):
    s = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(s)
    assert_modifiable_terrain(s, current_user.role)
    jtc = db.query(JourTestCandidat).filter(
        JourTestCandidat.jour_test_id == jour_id,
        JourTestCandidat.stagiaire_id == stagiaire_id
    ).first()
    if not jtc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")

    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()

    # CacesObtenu actif dans cette session (a_valider ou valide) — gap : SE peut être supprimée mais CO persiste
    if db.query(CacesObtenu).filter(
        CacesObtenu.session_id == session_id,
        CacesObtenu.stagiaire_id == stagiaire_id,
        CacesObtenu.statut.in_(["a_valider", "valide"])
    ).first():
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ce candidat a un CACES® en cours ou validé dans cette session — annulez-le d'abord avant de le retirer."
        )

    if jour and jour.type == 'pratique':
        if db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == session_id,
            SessionEpreuve.stagiaire_id == stagiaire_id,
            SessionEpreuve.date == jour.date
        ).first():
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Ce candidat a déjà un résultat saisi — supprimez d'abord son résultat pour le retirer."
            )

    if jour and jour.type == 'theorie':
        if db.query(ResultatTheorie).filter(
            ResultatTheorie.jour_test_id == jour_id,
            ResultatTheorie.stagiaire_id == stagiaire_id
        ).first():
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Ce candidat a déjà un résultat saisi — supprimez d'abord son résultat pour le retirer."
            )

    db.delete(jtc)
    db.commit()
    return {"message": "Candidat retire du jour"}


# ── JOURS DE FORMATION ────────────────────────────────────────────────────────

class JourFormationCreate(BaseModel):
    date: date
    intitule: Optional[str] = None
    note: Optional[str] = None
    stagiaire_ids: Optional[List[int]] = None


@router.post("/{session_id}/jours-formation")
def add_jour_formation(
    session_id: int,
    data: JourFormationCreate,
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    _check_modifiable(session)

    # Validation : la date doit être dans la période de la session
    bornes = [d for d in [session.date_theorie, session.date_pratique_debut,
                           session.date_pratique_fin] if d]
    if bornes:
        date_debut = min(bornes)
        date_fin = max(bornes)
        if data.date < date_debut or data.date > date_fin:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La date doit être comprise dans la période de la session "
                    f"(du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')})"
                ),
            )

    jf = JourFormation(
        session_id=session_id,
        date=data.date,
        intitule=data.intitule,
        note=data.note,
        candidats_ids=json.dumps(data.stagiaire_ids) if data.stagiaire_ids is not None else None,
        col_theorie=False,
        col_libre=False,
    )
    db.add(jf)
    db.commit()
    db.refresh(jf)
    return {"message": "Jour de formation ajouté", "id": jf.id}


class JourFormationUpdate(BaseModel):
    date_str: Optional[str] = None
    intitule: Optional[str] = None
    note: Optional[str] = None
    stagiaire_ids: Optional[List[int]] = None


@router.patch("/{session_id}/jours-formation/{id}")
def update_jour_formation(
    session_id: int,
    id: int,
    data: JourFormationUpdate,
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    _check_modifiable(session)
    jf = db.query(JourFormation).filter(
        JourFormation.id == id, JourFormation.session_id == session_id
    ).first()
    if not jf:
        raise HTTPException(status_code=404, detail="Jour de formation non trouvé")

    if data.date_str:
        from datetime import datetime as _dt
        try:
            nouvelle_date = _dt.strptime(data.date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide (attendu YYYY-MM-DD)")
        bornes = [d for d in [session.date_theorie, session.date_pratique_debut,
                               session.date_pratique_fin] if d]
        if bornes:
            date_debut = min(bornes)
            date_fin = max(bornes)
            if nouvelle_date < date_debut or nouvelle_date > date_fin:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"La date doit être comprise dans la période de la session "
                        f"(du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')})"
                    ),
                )
        jf.date = nouvelle_date

    if data.intitule is not None:
        jf.intitule = data.intitule or None
    if data.note is not None:
        jf.note = data.note or None

    if data.stagiaire_ids is not None:
        anciens = set(json.loads(jf.candidats_ids)) if jf.candidats_ids else {
            sc.stagiaire_id for sc in db.query(SessionCandidat).filter(
                SessionCandidat.session_id == session_id,
                SessionCandidat.actif == True,
            ).all()
        }
        nouveaux = set(data.stagiaire_ids)
        retires = anciens - nouveaux
        if retires:
            for sid in retires:
                pa = db.query(PlanningApprenant).filter(
                    PlanningApprenant.jour_formation_id == jf.id,
                    PlanningApprenant.stagiaire_id == sid,
                ).first()
                if pa:
                    hpc = {}
                    try:
                        hpc = json.loads(pa.heures_par_cat) if pa.heures_par_cat else {}
                    except Exception:
                        pass
                    if (pa.heures_theorie or 0) > 0 or (pa.heures_libre or 0) > 0 or any(v > 0 for v in hpc.values()):
                        raise HTTPException(
                            status_code=409,
                            detail="Impossible de retirer ce candidat : il a des heures saisies. Remettez d'abord ses heures à zéro."
                        )
            db.query(PlanningApprenant).filter(
                PlanningApprenant.jour_formation_id == jf.id,
                PlanningApprenant.stagiaire_id.in_(retires),
            ).delete()
        jf.candidats_ids = json.dumps(data.stagiaire_ids)

    db.commit()
    return {"id": jf.id, "date": str(jf.date), "intitule": jf.intitule}


@router.delete("/{session_id}/jours-formation/{id}")
def delete_jour_formation(
    session_id: int,
    id: int,
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    session = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(session)
    jf = db.query(JourFormation).filter(
        JourFormation.id == id, JourFormation.session_id == session_id
    ).first()
    if not jf:
        raise HTTPException(status_code=404, detail="Jour de formation non trouvé")
    if (
        db.query(AffectationFormation).filter(AffectationFormation.jour_formation_id == jf.id).first()
        or db.query(PlanningApprenant).filter(PlanningApprenant.jour_formation_id == jf.id).first()
    ):
        raise HTTPException(
            status_code=409,
            detail="Ce jour contient des données. Videz-le à zéro avant de le supprimer.",
        )
    db.delete(jf)
    db.commit()
    return {"message": "Jour de formation supprimé"}


# ── NOTES PRIVÉES ─────────────────────────────────────────────────────────────

class NotePivreeBody(BaseModel):
    note: str
    pin: Optional[str] = None  # requis pour admin non-principal

class NotePivreeDeleteBody(BaseModel):
    pin: Optional[str] = None


@router.put("/{session_id}/jours/{jour_id}/note-privee")
def put_note_privee_test(
    session_id: int, jour_id: int, body: NotePivreeBody,
    current_user: Utilisateur = Depends(get_utilisateur_courant),
    db: DBSession = Depends(get_db)
):
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session introuvable")
    if s.statut == "terminee":
        raise HTTPException(403, "Session clôturée — lecture seule")
    assert_modifiable_terrain(s, current_user.role)
    j = db.query(JourTest).filter(JourTest.id == jour_id, JourTest.session_id == session_id).first()
    if not j:
        raise HTTPException(404, "Jour introuvable")
    is_admin = current_user.role in ("admin", "utilisateur")
    af = db.query(AffectationTest).filter(
        AffectationTest.jour_test_id == jour_id,
        AffectationTest.user_id == current_user.id,
        AffectationTest.principal == True
    ).first()
    est_principal = af is not None
    if est_principal:
        pass  # auteur : create ou modify libre
    elif is_admin and j.note_privee and body.pin == get_pin_admin(db):
        pass  # admin + PIN : modify seulement (pas create ex nihilo)
    else:
        raise HTTPException(403, "Réservé au testeur principal (ou admin+PIN pour modifier)")
    j.note_privee = body.note.strip() or None
    if est_principal:
        j.note_privee_auteur_id = current_user.id
    db.commit()
    return {"ok": True}


@router.delete("/{session_id}/jours/{jour_id}/note-privee")
def delete_note_privee_test(
    session_id: int, jour_id: int, body: NotePivreeDeleteBody,
    current_user: Utilisateur = Depends(get_utilisateur_courant),
    db: DBSession = Depends(get_db)
):
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session introuvable")
    if s.statut == "terminee":
        raise HTTPException(403, "Session clôturée — lecture seule")
    assert_modifiable_terrain(s, current_user.role)
    j = db.query(JourTest).filter(JourTest.id == jour_id, JourTest.session_id == session_id).first()
    if not j or not j.note_privee:
        raise HTTPException(404, "Aucune note privée sur ce jour")
    is_admin = current_user.role in ("admin", "utilisateur")
    af = db.query(AffectationTest).filter(
        AffectationTest.jour_test_id == jour_id,
        AffectationTest.user_id == current_user.id,
        AffectationTest.principal == True
    ).first()
    est_auteur = j.note_privee_auteur_id == current_user.id and af is not None
    if not est_auteur:
        if not is_admin or body.pin != get_pin_admin(db):
            raise HTTPException(403, "Auteur ou admin+PIN requis")
    j.note_privee = None
    j.note_privee_auteur_id = None
    db.commit()
    return {"ok": True}


@router.put("/{session_id}/jours-formation/{jour_id}/note-privee")
def put_note_privee_formation(
    session_id: int, jour_id: int, body: NotePivreeBody,
    current_user: Utilisateur = Depends(get_utilisateur_courant),
    db: DBSession = Depends(get_db)
):
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session introuvable")
    if s.statut == "terminee":
        raise HTTPException(403, "Session clôturée — lecture seule")
    jf = db.query(JourFormation).filter(JourFormation.id == jour_id, JourFormation.session_id == session_id).first()
    if not jf:
        raise HTTPException(404, "Jour introuvable")
    is_admin = current_user.role in ("admin", "utilisateur")
    af = db.query(AffectationFormation).filter(
        AffectationFormation.jour_formation_id == jour_id,
        AffectationFormation.user_id == current_user.id,
        AffectationFormation.principal == True
    ).first()
    est_principal = af is not None
    if est_principal:
        pass
    elif is_admin and jf.note_privee and body.pin == get_pin_admin(db):
        pass
    else:
        raise HTTPException(403, "Réservé au formateur principal (ou admin+PIN pour modifier)")
    jf.note_privee = body.note.strip() or None
    if est_principal:
        jf.note_privee_auteur_id = current_user.id
    db.commit()
    return {"ok": True}


@router.delete("/{session_id}/jours-formation/{jour_id}/note-privee")
def delete_note_privee_formation(
    session_id: int, jour_id: int, body: NotePivreeDeleteBody,
    current_user: Utilisateur = Depends(get_utilisateur_courant),
    db: DBSession = Depends(get_db)
):
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session introuvable")
    if s.statut == "terminee":
        raise HTTPException(403, "Session clôturée — lecture seule")
    jf = db.query(JourFormation).filter(JourFormation.id == jour_id, JourFormation.session_id == session_id).first()
    if not jf or not jf.note_privee:
        raise HTTPException(404, "Aucune note privée sur ce jour")
    is_admin = current_user.role in ("admin", "utilisateur")
    af = db.query(AffectationFormation).filter(
        AffectationFormation.jour_formation_id == jour_id,
        AffectationFormation.user_id == current_user.id,
        AffectationFormation.principal == True
    ).first()
    est_auteur = jf.note_privee_auteur_id == current_user.id and af is not None
    if not est_auteur:
        if not is_admin or body.pin != get_pin_admin(db):
            raise HTTPException(403, "Auteur ou admin+PIN requis")
    jf.note_privee = None
    jf.note_privee_auteur_id = None
    db.commit()
    return {"ok": True}


# ── AFFECTATIONS FORMATEURS ────────────────────────────────────────────────────

def _verifier_impartialite(db, session_id: int, user_id: int) -> bool:
    """True si user_id est testeur pratique sur un JourTest actif de cette session.

    Implémente la règle d'impartialité CACES® : un formateur pratique ne peut pas
    être testeur pratique dans la même session, et vice-versa.
    La table AffectationTest est vide tant que le LOT 3 n'est pas déployé,
    donc ce check ne bloquera jamais avant cette étape — mais le code est correct.
    """
    return (
        db.query(AffectationTest)
        .join(JourTest, AffectationTest.jour_test_id == JourTest.id)
        .filter(
            JourTest.session_id == session_id,
            JourTest.type == "pratique",
            JourTest.actif == True,
            AffectationTest.user_id == user_id,
            AffectationTest.role == "testeur",
        )
        .first() is not None
    )


def _est_formateur_pratique(db, session_id: int, user_id: int) -> bool:
    """True si user_id est formateur pratique sur un JourFormation actif de cette session."""
    return (
        db.query(AffectationFormation)
        .join(JourFormation, AffectationFormation.jour_formation_id == JourFormation.id)
        .filter(
            JourFormation.session_id == session_id,
            JourFormation.actif == True,
            AffectationFormation.user_id == user_id,
            AffectationFormation.pratique == True,
        )
        .first() is not None
    )


class AffectationFormationItem(BaseModel):
    user_id: int
    theorie: bool = False
    pratique: bool = False
    principal: bool = False


@router.get("/{session_id}/jours-formation/{jour_id}/affectations")
def get_affectations_formation(
    session_id: int,
    jour_id: int,
    db: DBSession = Depends(get_db),
):
    jf = db.query(JourFormation).filter(
        JourFormation.id == jour_id,
        JourFormation.session_id == session_id,
    ).first()
    if not jf:
        raise HTTPException(status_code=404, detail="Jour de formation non trouvé")
    afs = db.query(AffectationFormation).filter(
        AffectationFormation.jour_formation_id == jour_id
    ).all()
    return [
        {"user_id": af.user_id, "theorie": af.theorie,
         "pratique": af.pratique, "principal": af.principal}
        for af in afs
    ]


@router.put("/{session_id}/jours-formation/{jour_id}/affectations")
def save_affectations_formation(
    session_id: int,
    jour_id: int,
    data: List[AffectationFormationItem],
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    session = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(session)
    jf = db.query(JourFormation).filter(
        JourFormation.id == jour_id,
        JourFormation.session_id == session_id,
    ).first()
    if not jf:
        raise HTTPException(status_code=404, detail="Jour de formation non trouvé")

    # Impartialité : formateur pratique ≠ testeur pratique dans la même session
    for item in data:
        if item.pratique and _verifier_impartialite(db, session_id, item.user_id):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Ce formateur est déjà désigné comme testeur pratique dans cette session "
                    "(règle d'impartialité CACES®)."
                ),
            )

    # Principal unique : au plus 1 principal dans la liste soumise
    if sum(1 for item in data if item.principal) > 1:
        raise HTTPException(status_code=400, detail="Un seul formateur principal par jour.")

    # Remplacement atomique — le DELETE global garantit qu'un ancien principal est remplacé
    db.query(AffectationFormation).filter(
        AffectationFormation.jour_formation_id == jour_id
    ).delete()
    for item in data:
        db.add(AffectationFormation(
            jour_formation_id=jour_id,
            user_id=item.user_id,
            theorie=item.theorie,
            pratique=item.pratique,
            principal=item.principal,
        ))
    db.commit()
    return {"message": "Affectations enregistrées"}


class PlanningApprenantItem(BaseModel):
    stagiaire_id: int
    heures_theorie: float = 0.0
    heures_par_cat: Dict[str, float] = {}
    heures_libre: float = 0.0

class PlanningJourBody(BaseModel):
    libelle_colonne_libre: Optional[str] = None
    has_theorie_col: bool = False
    has_libre_col: bool = False
    apprenants: List[PlanningApprenantItem] = []


@router.put("/{session_id}/jours-formation/{jour_id}/planning")
def save_planning_jour_formation(
    session_id: int,
    jour_id: int,
    data: PlanningJourBody,
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    session = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(session)
    jf = db.query(JourFormation).filter(
        JourFormation.id == jour_id,
        JourFormation.session_id == session_id,
    ).first()
    if not jf:
        raise HTTPException(status_code=404, detail="Jour de formation non trouvé")

    for item in data.apprenants:
        total = item.heures_theorie + sum(item.heures_par_cat.values()) + item.heures_libre
        if total > 7.0:
            stag = db.query(Stagiaire).filter(Stagiaire.id == item.stagiaire_id).first()
            nom = f"{stag.nom} {stag.prenom}" if stag else f"#{item.stagiaire_id}"
            raise HTTPException(
                status_code=400,
                detail=f"Apprenant {nom} : total dépasse 7h ({total:.1f}h saisis)"
            )

    if data.libelle_colonne_libre is not None:
        jf.libelle_colonne_libre = data.libelle_colonne_libre
    jf.col_theorie = data.has_theorie_col
    jf.col_libre = data.has_libre_col

    db.query(PlanningApprenant).filter(PlanningApprenant.jour_formation_id == jour_id).delete()
    for item in data.apprenants:
        total = item.heures_theorie + sum(item.heures_par_cat.values()) + item.heures_libre
        if total > 0 or item.heures_par_cat:
            db.add(PlanningApprenant(
                jour_formation_id=jour_id,
                stagiaire_id=item.stagiaire_id,
                heures_theorie=item.heures_theorie,
                heures_par_cat=json.dumps(item.heures_par_cat) if item.heures_par_cat else None,
                heures_libre=item.heures_libre,
            ))
    db.commit()
    return {"message": "Planning enregistré"}


# ── AFFECTATIONS TESTEURS (jours de test) ──────────────────────────────────────

class AffectationTestItem(BaseModel):
    user_id: int
    principal: bool = False


@router.get("/{session_id}/jours/{jour_id}/affectations-test")
def get_affectations_test(session_id: int, jour_id: int, db: DBSession = Depends(get_db)):
    j = db.query(JourTest).filter(JourTest.id == jour_id, JourTest.session_id == session_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouvé")
    ats = db.query(AffectationTest).filter(AffectationTest.jour_test_id == jour_id).all()
    return [{"user_id": at.user_id, "principal": at.principal} for at in ats]


@router.put("/{session_id}/jours/{jour_id}/affectations-test")
def save_affectations_test(
    session_id: int,
    jour_id: int,
    data: List[AffectationTestItem],
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    session = db.query(Session).filter(Session.id == session_id).first()
    _check_modifiable(session)
    j = db.query(JourTest).filter(JourTest.id == jour_id, JourTest.session_id == session_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouvé")

    # Impartialité : testeur pratique ≠ formateur pratique dans la même session
    if j.type == "pratique":
        for item in data:
            if _est_formateur_pratique(db, session_id, item.user_id):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Ce testeur est déjà désigné comme formateur pratique dans cette session "
                        "(règle d'impartialité CACES®)."
                    ),
                )

    if sum(1 for item in data if item.principal) > 1:
        raise HTTPException(status_code=400, detail="Un seul testeur principal par jour.")

    existing = {at.user_id: at for at in db.query(AffectationTest).filter(AffectationTest.jour_test_id == jour_id).all()}
    submitted_ids = {item.user_id for item in data}
    for uid, at in existing.items():
        if uid not in submitted_ids:
            db.delete(at)
    for item in data:
        at = existing.get(item.user_id)
        if at:
            at.principal = item.principal
        else:
            db.add(AffectationTest(
                jour_test_id=jour_id,
                user_id=item.user_id,
                role="testeur",
                principal=item.principal,
            ))
    db.commit()
    return {"message": "Affectations testeurs enregistrées"}


# ---------- Justificatif de dispense (stockage R2) ----------

@router.post("/{session_id}/candidats/{sc_id}/dispense-fichier")
async def upload_dispense_fichier(
    session_id: int,
    sc_id: int,
    request: Request,
    fichier: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")

    sc = db.query(SessionCandidat).filter(
        SessionCandidat.id == sc_id,
        SessionCandidat.session_id == session_id,
    ).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat de session introuvable")

    nom = fichier.filename or "fichier"
    ext = nom.rsplit(".", 1)[1].lower() if "." in nom else ""
    if ext not in storage.EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Type de fichier non autorise (PDF, Word ou Excel uniquement)")

    contenu = await fichier.read()
    if len(contenu) > storage.TAILLE_MAX:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (10 Mo maximum)")
    if not contenu:
        raise HTTPException(status_code=400, detail="Fichier vide")

    content_type = fichier.content_type or "application/octet-stream"

    if sc.dispense_fichier_cle:
        try:
            storage.delete_fichier(sc.dispense_fichier_cle)
        except Exception:
            pass

    cle = storage.construire_cle("dispenses", nom)
    storage.upload_fichier(contenu, cle, content_type)

    sc.dispense_fichier_cle = cle
    sc.dispense_fichier_nom = nom[:255]
    sc.dispense_fichier_type = content_type[:100]
    db.commit()

    return {"ok": True, "fichier_nom": sc.dispense_fichier_nom}


@router.get("/{session_id}/candidats/{sc_id}/dispense-fichier")
def get_dispense_fichier(
    session_id: int,
    sc_id: int,
    request: Request,
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")

    sc = db.query(SessionCandidat).filter(
        SessionCandidat.id == sc_id,
        SessionCandidat.session_id == session_id,
    ).first()
    if not sc or not sc.dispense_fichier_cle:
        raise HTTPException(status_code=404, detail="Aucun justificatif")

    contenu = storage.get_fichier(sc.dispense_fichier_cle)
    media = sc.dispense_fichier_type or "application/octet-stream"
    nom = sc.dispense_fichier_nom or "justificatif"
    return StreamingResponse(
        BytesIO(contenu),
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{nom}"'},
    )


@router.delete("/{session_id}/candidats/{sc_id}/dispense-fichier")
def delete_dispense_fichier(
    session_id: int,
    sc_id: int,
    request: Request,
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")

    sc = db.query(SessionCandidat).filter(
        SessionCandidat.id == sc_id,
        SessionCandidat.session_id == session_id,
    ).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat de session introuvable")

    if sc.dispense_fichier_cle:
        try:
            storage.delete_fichier(sc.dispense_fichier_cle)
        except Exception:
            pass
    sc.dispense_fichier_cle = None
    sc.dispense_fichier_nom = None
    sc.dispense_fichier_type = None
    db.commit()
    return {"ok": True}


# ---------- Justificatifs generiques (multi-fichiers, table justificatifs / R2) ----------

@router.post("/{session_id}/justificatifs")
async def upload_justificatif(
    session_id: int,
    request: Request,
    type: str = Form(...),
    session_candidat_id: int = Form(None),
    libelle: str = Form(None),
    fichier: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    if type not in ("formation", "dispense", "presence_session", "document_session"):
        raise HTTPException(status_code=400, detail="Type de justificatif invalide")

    nom = fichier.filename or "fichier"
    ext = nom.rsplit(".", 1)[1].lower() if "." in nom else ""
    if ext not in storage.EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Type de fichier non autorise (PDF, Word ou Excel)")

    contenu = await fichier.read()
    if len(contenu) > storage.TAILLE_MAX:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (10 Mo maximum)")
    if not contenu:
        raise HTTPException(status_code=400, detail="Fichier vide")

    content_type = fichier.content_type or "application/octet-stream"
    cle = storage.construire_cle(f"justificatifs/{type}", nom)
    storage.upload_fichier(contenu, cle, content_type)

    j = Justificatif(
        type=type,
        session_id=session_id,
        session_candidat_id=session_candidat_id,
        fichier_cle=cle,
        fichier_nom=nom[:300],
        fichier_type=content_type[:100],
        date_upload=dt.utcnow(),
        uploade_par=f"{user.prenom} {user.nom}"[:200],
        libelle=(libelle[:300] if libelle else None),
        uploade_par_role=(user.role if getattr(user, "role", None) else None),
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return {"ok": True, "id": j.id, "fichier_nom": j.fichier_nom}


@router.get("/{session_id}/justificatifs")
def lister_justificatifs(
    session_id: int,
    request: Request,
    type: str = None,
    session_candidat_id: int = None,
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    q = db.query(Justificatif).filter(Justificatif.session_id == session_id)
    if type:
        q = q.filter(Justificatif.type == type)
    if session_candidat_id is not None:
        q = q.filter(Justificatif.session_candidat_id == session_candidat_id)
    rows = q.order_by(Justificatif.date_upload.desc()).all()
    return [
        {
            "id": j.id,
            "type": j.type,
            "fichier_nom": j.fichier_nom,
            "date_upload": j.date_upload.isoformat() if j.date_upload else None,
            "uploade_par": j.uploade_par,
            "libelle": j.libelle,
            "uploade_par_role": j.uploade_par_role,
        }
        for j in rows
    ]


@router.get("/{session_id}/justificatifs/{justif_id}")
def voir_justificatif(
    session_id: int,
    justif_id: int,
    request: Request,
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    j = db.query(Justificatif).filter(
        Justificatif.id == justif_id,
        Justificatif.session_id == session_id,
    ).first()
    if not j or not j.fichier_cle:
        raise HTTPException(status_code=404, detail="Justificatif introuvable")
    contenu = storage.get_fichier(j.fichier_cle)
    media = j.fichier_type or "application/octet-stream"
    nom = j.fichier_nom or "justificatif"
    return StreamingResponse(
        BytesIO(contenu),
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{nom}"'},
    )


@router.delete("/{session_id}/justificatifs/{justif_id}")
def supprimer_justificatif(
    session_id: int,
    justif_id: int,
    request: Request,
    db: DBSession = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    j = db.query(Justificatif).filter(
        Justificatif.id == justif_id,
        Justificatif.session_id == session_id,
    ).first()
    if not j:
        raise HTTPException(status_code=404, detail="Justificatif introuvable")
    role = getattr(user, "role", None)
    est_back_office = role in ("admin", "utilisateur")
    if not est_back_office:
        if j.uploade_par_role != "terrain":
            raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que les documents ajoutes par le terrain.")
    if j.fichier_cle:
        try:
            storage.delete_fichier(j.fichier_cle)
        except Exception:
            pass
    db.delete(j)
    db.commit()
    return {"ok": True}


@router.get("/{session_id}/attestation-reussite/{stagiaire_id}")
def attestation_reussite_pdf(session_id: int, stagiaire_id: int,
                             request: Request, db: DBSession = Depends(get_db)):
    # Auth via cookie (middleware) — window.open n'envoie pas le Bearer header.
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    from app.services.pdf_attestation_reussite import generer_attestation_reussite
    pdf_bytes = generer_attestation_reussite(session_id, stagiaire_id, db)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Candidat ou session introuvable")
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="attestation_reussite.pdf"'},
    )


# ── VISIBILITE TERRAIN PAR SESSION ────────────────────────────────
def _personnes_affectees_session(db, session_id: int):
    """Retourne [{user_id, nom, prenom}] dedoublonne : formateurs + testeurs (via utilisateur_id)."""
    user_ids = set()
    _jf_ids = [r.id for r in db.query(JourFormation.id).filter(
        JourFormation.session_id == session_id, JourFormation.actif == True
    ).all()]
    if _jf_ids:
        for r in db.query(AffectationFormation.user_id).filter(
            AffectationFormation.jour_formation_id.in_(_jf_ids)
        ).distinct().all():
            if r.user_id:
                user_ids.add(r.user_id)
    # Testeurs : la source reelle est AffectationTest.user_id (deja un user_id),
    # PAS JourTest.testeur_id (souvent None). Symetrique aux formateurs.
    _jt_ids = [r.id for r in db.query(JourTest.id).filter(
        JourTest.session_id == session_id, JourTest.actif == True
    ).all()]
    if _jt_ids:
        for r in db.query(AffectationTest.user_id).filter(
            AffectationTest.jour_test_id.in_(_jt_ids)
        ).distinct().all():
            if r.user_id:
                user_ids.add(r.user_id)
    if not user_ids:
        return []
    users = db.query(Utilisateur).filter(Utilisateur.id.in_(user_ids)).order_by(
        Utilisateur.nom, Utilisateur.prenom
    ).all()
    return [{"user_id": u.id, "nom": u.nom, "prenom": u.prenom or ""} for u in users]


@router.get("/{session_id}/visibilite")
def get_visibilite(session_id: int, db: DBSession = Depends(get_db),
                   current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(403, "Acces non autorise")
    from app.models.session_visibilite import SessionVisibilite
    personnes = _personnes_affectees_session(db, session_id)
    coches = {r.user_id for r in db.query(SessionVisibilite.user_id).filter(
        SessionVisibilite.session_id == session_id
    ).all()}
    for p in personnes:
        p["visible"] = p["user_id"] in coches
    return personnes


class VisibiliteBody(BaseModel):
    user_ids: List[int] = []


@router.put("/{session_id}/visibilite")
def save_visibilite(session_id: int, data: VisibiliteBody,
                    db: DBSession = Depends(get_db),
                    current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role not in ("admin", "utilisateur"):
        raise HTTPException(403, "Acces non autorise")
    from app.models.session_visibilite import SessionVisibilite
    affectees = {p["user_id"] for p in _personnes_affectees_session(db, session_id)}
    voulus = {uid for uid in data.user_ids if uid in affectees}
    db.query(SessionVisibilite).filter(SessionVisibilite.session_id == session_id).delete()
    for uid in voulus:
        db.add(SessionVisibilite(session_id=session_id, user_id=uid))
    db.commit()
    return {"message": "Visibilite enregistree", "count": len(voulus)}
