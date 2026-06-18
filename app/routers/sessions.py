from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.session import Session
from app.models.session_candidat import SessionCandidat
from app.models.session_epreuve import SessionEpreuve
from app.models.equipement import Equipement
from app.models.stagiaire import Stagiaire
from app.models.testeur import Testeur
from app.models.categorie import Categorie, Famille
from app.models.jour_test import JourTest, JourTestCandidat, ResultatTheorie
from app.models.jour_formation import JourFormation, AffectationFormation, PlanningApprenant, AffectationTest
from app.models.caces_obtenu import CacesObtenu
from app.models.grille_theorie import GrilleTheorie, ReponseGrille, UtilisationGrille
from app.models.consentement_rgpd import ConsentementRGPD
from app.models.utilisations_themes import UtilisationTheme
from app.models.non_conformite import NonConformite
from app.services.tirage_grille import (
    tirer_grille, calculer_resultat_theorie,
    tirer_themes_phase2, enregistrer_tirage_themes,
    get_questions_phase2, calculer_resultat_theorie_phase2,
    tirage_to_json
)
from app.services.caces_obtenus import calculer_et_synchroniser
from app.models.utilisateur import Utilisateur
from app.routers.auth import get_utilisateur_courant
from app.config_utils import get_pin_admin, get_pin_formateur
from pydantic import BaseModel
from datetime import date, datetime as dt
from typing import Optional, List, Dict
import json
import math

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
        Session.reference.ilike(f"%{q}%")
    ).order_by(Session.id.desc()).limit(10).all()
    return [{"id": s.id, "reference": s.reference or f"Session #{s.id}", "famille": s.famille, "statut": s.statut} for s in rows]

@router.get("/", response_model=list[SessionResponse])
def liste_sessions(db: DBSession = Depends(get_db)):
    return db.query(Session).order_by(Session.id.desc()).all()

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
    sc = SessionCandidat(**data.model_dump())
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
    sc.theorie_dispensee = data.theorie_dispensee
    sc.dispense_note = data.dispense_note if data.theorie_dispensee else None
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
    sc.actif = False
    db.commit()
    return {"message": "Candidat retire"}

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

    # [DIAG] ── lookup existing (numerique) ───────────────────────────────────
    if existing:
        print(f"[DIAG NUMERIQUE] existing FOUND id={existing.id} jour_test_id={existing.jour_test_id} mode={existing.mode!r} note_actuelle={existing.note_totale} obtenue_actuelle={existing.obtenue}", flush=True)
    else:
        print(f"[DIAG NUMERIQUE] existing NOT FOUND → INSERT path (jour_test_id={data.jour_test_id} stag={data.stagiaire_id})", flush=True)
    # ──────────────────────────────────────────────────────────────────────────

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
        # [DIAG] ── après assignments ─────────────────────────────────────────
        print(f"[DIAG NUMERIQUE] UPDATE assigné: note_totale={existing.note_totale} obtenue={existing.obtenue} dirty={db.is_modified(existing)}", flush=True)
        # ─────────────────────────────────────────────────────────────────────
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
        )
        db.add(rt)

    # [DIAG] ── commit + refresh (numerique) ──────────────────────────────────
    db.commit()
    print("[DIAG NUMERIQUE] COMMIT OK", flush=True)
    if existing:
        db.refresh(existing)
        print(f"[DIAG NUMERIQUE] AFTER REFRESH: note_totale={existing.note_totale} obtenue={existing.obtenue}", flush=True)
    # ──────────────────────────────────────────────────────────────────────────
    return {"resultat": resultat}


class TheoriePinBody(BaseModel):
    pin: str


class NotesParThemeCreate(BaseModel):
    jour_test_id: int
    stagiaire_id: int
    pin: str
    notes_par_theme: Dict[str, int]  # {"1": 8, "2": 20, …} — nb bonnes réponses saisies


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
    rt.justificatif_pdf = body.fichier_base64
    rt.justificatif_nom = body.fichier_nom
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
    if not rt or not rt.justificatif_pdf:
        raise HTTPException(status_code=404, detail="Aucun justificatif pour ce résultat")
    pdf_bytes = base64.b64decode(rt.justificatif_pdf)
    nom = rt.justificatif_nom or "justificatif.pdf"
    return SR(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nom}"'},
    )


@router.post("/{session_id}/theorie/reponses-degrade")
def soumettre_reponses_theorie_degrade(
    session_id: int,
    data: NotesParThemeCreate,
    db: DBSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_utilisateur_courant),
):
    # [DIAG] ── début ──────────────────────────────────────────────────────────
    print(f"[DIAG DEGRADE] HANDLER REACHED session={session_id} stag={data.stagiaire_id} jour={data.jour_test_id}", flush=True)
    print(f"[RECU] notes_par_theme={dict(data.notes_par_theme)}", flush=True)
    _pin_db = get_pin_formateur(db)
    print(f"[DIAG DEGRADE] PIN recu={data.pin!r} PIN_db={_pin_db!r} match={data.pin == _pin_db}", flush=True)
    # ──────────────────────────────────────────────────────────────────────────

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

    # [DIAG] ── questions par thème (nb questions × points) ─────────────────────
    # ──────────────────────────────────────────────────────────────────────────

    # [DIAG] ── résultat calculé ──────────────────────────────────────────────
    print(f"[DIAG DEGRADE] resultat: note_totale={resultat['note_totale']} notes_themes={resultat['notes_themes']} obtenue={resultat['obtenue']}", flush=True)
    # ──────────────────────────────────────────────────────────────────────────

    # g. Écriture ResultatTheorie
    existing = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == data.jour_test_id,
        ResultatTheorie.stagiaire_id == data.stagiaire_id,
    ).first()

    # [DIAG] ── lookup existing ────────────────────────────────────────────────
    if existing:
        print(f"[DIAG DEGRADE] existing FOUND id={existing.id} jour_test_id={existing.jour_test_id} mode={existing.mode!r} note_actuelle={existing.note_totale} obtenue_actuelle={existing.obtenue}", flush=True)
    else:
        print(f"[DIAG DEGRADE] existing NOT FOUND → INSERT path (jour_test_id={data.jour_test_id} stag={data.stagiaire_id})", flush=True)
    # ──────────────────────────────────────────────────────────────────────────

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
        # reponses_json et justificatif_* intentionnellement non modifiés
        # [DIAG] ── après assignments ─────────────────────────────────────────
        print(f"[DIAG DEGRADE] UPDATE assigné: note_totale={existing.note_totale} obtenue={existing.obtenue} dirty={db.is_modified(existing)}", flush=True)
        # ─────────────────────────────────────────────────────────────────────
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
        )
        db.add(rt)

    # [DIAG] ── commit + refresh ───────────────────────────────────────────────
    db.commit()
    print("[DIAG DEGRADE] COMMIT OK", flush=True)
    if existing:
        db.refresh(existing)
        print(f"[DIAG DEGRADE] AFTER REFRESH: note_totale={existing.note_totale} obtenue={existing.obtenue}", flush=True)
    # ──────────────────────────────────────────────────────────────────────────
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
    famille = db.query(Famille).filter(Famille.code == data.famille).first()
    cat = db.query(Categorie).filter(
        Categorie.famille_id == (famille.id if famille else 0),
        Categorie.code == data.categorie
    ).first()
    from app.models.option_categorie import OptionCategorie
    incluse_codes = {
        opt.code_option
        for opt in db.query(OptionCategorie).filter(
            OptionCategorie.famille == data.famille,
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
    db.delete(e)
    db.commit()
    return {"message": "Epreuve supprimee"}

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
    if current_user.role == "terrain":
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    if s.statut == "terminee":
        raise HTTPException(status_code=400, detail="Impossible de déclencher le tirage sur une session clôturée")

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

    existants = (
        db.query(UtilisationTheme)
        .filter(UtilisationTheme.session_id == id, UtilisationTheme.famille == s.famille)
        .all()
    )
    if existants:
        date_t = existants[0].date_tirage
        return {
            "deja_declenche": True,
            "date_tirage": date_t.isoformat() if date_t else None,
        }

    from datetime import datetime
    annee = datetime.now().year
    now = datetime.now()
    try:
        tirage = tirer_themes_phase2(s.famille, id, annee, db)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    enregistrer_tirage_themes(id, s.famille, annee, tirage, db, date_tirage=now, declenche_par_id=current_user.id)
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
    if current_user.role == "terrain":
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
    if current_user.role == "terrain":
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
    if current_user.role == "terrain":
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
    if current_user.role == "terrain":
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
    if current_user.role == "terrain":
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
    if current_user.role == "terrain":
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