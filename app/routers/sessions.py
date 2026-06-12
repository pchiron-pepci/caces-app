from fastapi import APIRouter, Depends, HTTPException
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
from app.models.jour_formation import JourFormation, AffectationFormation, PlanningApprenant
from app.models.caces_obtenu import CacesObtenu
from app.models.grille_theorie import GrilleTheorie, ReponseGrille
from app.models.consentement_rgpd import ConsentementRGPD
from app.services.tirage_grille import (
    tirer_grille, calculer_resultat_theorie,
    tirer_themes_phase2, enregistrer_tirage_themes,
    get_questions_phase2, calculer_resultat_theorie_phase2,
    tirage_to_json
)
from app.services.caces_obtenus import calculer_et_synchroniser
from app.models.utilisateur import Utilisateur
from app.routers.auth import get_utilisateur_courant
from app.config_utils import get_pin_admin
from pydantic import BaseModel
from datetime import date
from typing import Optional, List, Dict
import json
import math

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

class JourModifData(BaseModel):
    date: Optional[str] = None
    testeur_id: Optional[int] = None

class TesteurSupData(BaseModel):
    testeurs_sup: Optional[str] = None

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
    testeur_id: Optional[int] = None
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


@router.get("/", response_model=list[SessionResponse])
def liste_sessions(db: DBSession = Depends(get_db)):
    return db.query(Session).order_by(Session.id.desc()).all()

@router.post("/", response_model=SessionResponse)
def create_session(data: SessionCreate, db: DBSession = Depends(get_db)):
    from datetime import datetime
    annee = datetime.now().year
    if not data.reference:
        nb = db.query(Session).filter(Session.annee == annee).count()
        data.reference = f"SESSION-{annee}-{str(nb + 1).zfill(3)}"
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
    s.statut = "annulee"
    db.commit()
    return {"message": "Session annulee"}

@router.post("/{id}/cloturer")
def cloturer_session(id: int, db: DBSession = Depends(get_db)):
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
def add_candidat(session_id: int, data: SessionCandidatCreate, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
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
def update_candidat(session_id: int, id: int, data: SessionCandidatCreate, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    sc = db.query(SessionCandidat).filter(SessionCandidat.id == id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    sc.theorie_dispensee = data.theorie_dispensee
    db.commit()
    return {"message": "Candidat mis a jour"}

@router.delete("/{session_id}/candidats/{id}")
def remove_candidat(session_id: int, id: int, pin: str = "", db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
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
def add_equipement(session_id: int, data: EquipementCreate, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    e = Equipement(**data.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"message": "Equipement ajoute", "id": e.id}

@router.put("/{session_id}/equipements/{id}")
def update_equipement(session_id: int, id: int, data: EquipementCreate, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    e = db.query(Equipement).filter(Equipement.id == id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Equipement non trouve")
    for key, value in data.model_dump().items():
        setattr(e, key, value)
    db.commit()
    return {"message": "Equipement mis a jour"}

# JOURS DE TEST
@router.post("/{session_id}/jours")
def add_jour_test(session_id: int, data: JourTestCreate, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    _check_modifiable(session)

    tirage_json = None
    if data.type == "theorie":
        from datetime import datetime
        from app.models.utilisations_themes import UtilisationTheme as UT
        annee = datetime.now().year
        tirages_existants = (
            db.query(UT)
            .filter(UT.session_id == session_id, UT.famille == session.famille)
            .order_by(UT.theme)
            .all()
        )
        if tirages_existants:
            grille_map = {
                g.id: g.numero
                for g in db.query(GrilleTheorie).filter(GrilleTheorie.famille == session.famille).all()
            }
            tirage_json = json.dumps({str(t.theme): grille_map.get(t.grille_id, 0) for t in tirages_existants})
        else:
            try:
                tirage = tirer_themes_phase2(session.famille, session_id, annee, db)
                enregistrer_tirage_themes(session_id, session.famille, annee, tirage, db)
                tirage_json = tirage_to_json(tirage)
            except ValueError:
                tirage_json = None

    jour = JourTest(
        session_id=session_id,
        date=data.date,
        type=data.type,
        testeur_id=data.testeur_id,
        grille_id=None,
        tirage_themes_json=tirage_json,
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

    result = {"message": "Jour de test ajoute", "id": jour.id}
    if tirage_json:
        result["tirage"] = json.loads(tirage_json)
    return result

@router.post("/{session_id}/jours/{jour_id}/candidats")
def add_candidats_jour(session_id: int, jour_id: int, data: AjoutCandidatsJour, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
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
        for stagiaire_id in data.candidats:
            existing = db.query(JourTestCandidat).filter(
                JourTestCandidat.jour_test_id == jour_id,
                JourTestCandidat.stagiaire_id == stagiaire_id
            ).first()
            if not existing:
                jtc = JourTestCandidat(jour_test_id=jour_id, stagiaire_id=stagiaire_id)
                db.add(jtc)
    db.commit()
    return {"message": "Candidats ajoutes"}

@router.delete("/{session_id}/jours/{id}")
def delete_jour_test(session_id: int, id: int, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    j = db.query(JourTest).filter(JourTest.id == id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouve")

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
        from app.models.grille_theorie import UtilisationGrille
        uti = db.query(UtilisationGrille).filter(
            UtilisationGrille.grille_id == j.grille_id,
            UtilisationGrille.session_id == j.session_id,
        ).first()
        if uti:
            db.delete(uti)

    if j.type == "theorie":
        from app.models.utilisations_themes import UtilisationTheme
        autres_jours_theorie = (
            db.query(JourTest)
            .filter(
                JourTest.session_id == j.session_id,
                JourTest.type == "theorie",
                JourTest.actif == True,
                JourTest.id != j.id,
            )
            .count()
        )
        if autres_jours_theorie == 0:
            db.query(UtilisationTheme).filter(
                UtilisationTheme.session_id == j.session_id
            ).delete()

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
    jour = db.query(JourTest).filter(JourTest.id == data.jour_test_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour non trouve")

    try:
        resultat = calculer_resultat_theorie_phase2(data.reponses, session_id, session.famille, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    )
    db.add(rt)
    db.commit()

    return {"resultat": resultat}

@router.get("/{session_id}/jours/{jour_id}/grille")
def get_grille_jour(session_id: int, jour_id: int, db: DBSession = Depends(get_db)):
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour non trouve")

    session = db.query(Session).filter(Session.id == session_id).first()
    data = get_questions_phase2(session_id, session.famille, db)

    return {
        "grille_id": None,
        "grille_numero": None,
        "famille": session.famille,
        "tirage": data["tirage"],
        "themes": data["themes"]
    }

# EPREUVES PRATIQUES
@router.post("/{session_id}/epreuves")
def add_epreuve(session_id: int, data: EpreuveCreate, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
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
def delete_epreuve(session_id: int, epreuve_id: int, pin: str = "", db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
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

@router.post("/{id}/reouvrir")
def reouvrir_session(id: int, pin: str = "", db: DBSession = Depends(get_db),
                     current_user: Utilisateur = Depends(get_utilisateur_courant)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur")
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    s.statut = "planifiee"
    db.commit()
    return {"message": "Session reuverte"}

@router.put("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}/identite")
def toggle_identite(session_id: int, jour_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    jtc = db.query(JourTestCandidat).filter(
        JourTestCandidat.jour_test_id == jour_id,
        JourTestCandidat.stagiaire_id == stagiaire_id
    ).first()
    if not jtc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    jtc.identite_verifiee = not jtc.identite_verifiee
    db.commit()
    return {"identite_verifiee": jtc.identite_verifiee}

@router.put("/{id}")
def update_session(id: int, data: SessionCreate, db: DBSession = Depends(get_db)):
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    _check_modifiable(s)
    s.date_theorie = data.date_theorie
    s.date_pratique_debut = data.date_pratique_debut
    s.date_pratique_fin = data.date_pratique_fin
    s.responsable = data.responsable
    s.note = data.note
    db.commit()
    return {"message": "Session mise a jour"}

@router.put("/{session_id}/jours/{jour_id}/modifier")
def modifier_jour(session_id: int, jour_id: int, data: JourModifData, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    from datetime import date as date_type
    j = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouve")
    if data.date:
        j.date = date_type.fromisoformat(data.date)
    if data.testeur_id:
        j.testeur_id = data.testeur_id
    db.commit()
    return {"message": "Jour modifie"}

@router.patch("/{session_id}/jours/{jour_id}/testeurs-sup")
def update_testeurs_sup(session_id: int, jour_id: int, data: TesteurSupData, db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    j = db.query(JourTest).filter(JourTest.id == jour_id, JourTest.session_id == session_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouvé")
    j.testeurs_sup = data.testeurs_sup or None
    db.commit()
    return {"message": "OK"}

@router.get("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}/check-theorie")
def check_resultat_theorie_candidat(session_id: int, jour_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    has_resultat = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_id,
        ResultatTheorie.stagiaire_id == stagiaire_id
    ).first() is not None
    return {"has_resultat": has_resultat}

@router.delete("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}")
def remove_candidat_jour(session_id: int, jour_id: int, stagiaire_id: int, pin: str = "", db: DBSession = Depends(get_db)):
    _check_modifiable(db.query(Session).filter(Session.id == session_id).first())
    jtc = db.query(JourTestCandidat).filter(
        JourTestCandidat.jour_test_id == jour_id,
        JourTestCandidat.stagiaire_id == stagiaire_id
    ).first()
    if not jtc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")

    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()

    if jour and jour.type == 'pratique':
        epreuve_existante = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == session_id,
            SessionEpreuve.stagiaire_id == stagiaire_id,
            SessionEpreuve.date == jour.date
        ).first()
        if epreuve_existante:
            raise HTTPException(
                status_code=400,
                detail="Supprimez d'abord les résultats de ce candidat avant de le retirer du jour"
            )

    resultat_theorie = db.query(ResultatTheorie).filter(
        ResultatTheorie.jour_test_id == jour_id,
        ResultatTheorie.stagiaire_id == stagiaire_id
    ).first()
    if resultat_theorie:
        if pin != get_pin_admin(db):
            raise HTTPException(status_code=403, detail="Code PIN incorrect")
        db.query(ResultatTheorie).filter(
            ResultatTheorie.jour_test_id == jour_id,
            ResultatTheorie.stagiaire_id == stagiaire_id
        ).delete()

    db.delete(jtc)
    db.commit()
    return {"message": "Candidat retire du jour"}


# ── JOURS DE FORMATION ────────────────────────────────────────────────────────

class JourFormationCreate(BaseModel):
    date: date
    intitule: Optional[str] = None
    note: Optional[str] = None


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

    jf = JourFormation(session_id=session_id, date=data.date,
                       intitule=data.intitule, note=data.note)
    db.add(jf)
    db.commit()
    db.refresh(jf)
    return {"message": "Jour de formation ajouté", "id": jf.id}


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
    db.query(AffectationFormation).filter(AffectationFormation.jour_formation_id == jf.id).delete()
    db.query(PlanningApprenant).filter(PlanningApprenant.jour_formation_id == jf.id).delete()
    db.delete(jf)
    db.commit()
    return {"message": "Jour de formation supprimé"}