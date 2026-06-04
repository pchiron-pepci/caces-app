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
from app.models.grille_theorie import GrilleTheorie, ReponseGrille
from app.services.tirage_grille import (
    tirer_grille, calculer_resultat_theorie,
    tirer_themes_phase2, enregistrer_tirage_themes,
    get_questions_phase2, calculer_resultat_theorie_phase2,
    tirage_to_json
)
from pydantic import BaseModel
from datetime import date
from typing import Optional, List, Dict
import json
import math

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

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
    if pin != "1505":
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
    s.statut = "terminee"
    db.commit()
    return {"message": "Session cloturee"}

# CANDIDATS
@router.post("/{session_id}/candidats")
def add_candidat(session_id: int, data: SessionCandidatCreate, db: DBSession = Depends(get_db)):
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
    sc = db.query(SessionCandidat).filter(SessionCandidat.id == id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    sc.rgpd_accepte = data.rgpd_accepte
    sc.photo_accepte = data.photo_accepte
    sc.theorie_dispensee = data.theorie_dispensee
    db.commit()
    return {"message": "Candidat mis a jour"}

@router.delete("/{session_id}/candidats/{id}")
def remove_candidat(session_id: int, id: int, db: DBSession = Depends(get_db)):
    sc = db.query(SessionCandidat).filter(SessionCandidat.id == id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Candidat non trouve")
    sc.actif = False
    db.commit()
    return {"message": "Candidat retire"}

# EQUIPEMENTS
@router.post("/{session_id}/equipements")
def add_equipement(session_id: int, data: EquipementCreate, db: DBSession = Depends(get_db)):
    e = Equipement(**data.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"message": "Equipement ajoute", "id": e.id}

@router.put("/{session_id}/equipements/{id}")
def update_equipement(session_id: int, id: int, data: EquipementCreate, db: DBSession = Depends(get_db)):
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

    tirage_json = None
    if data.type == "theorie":
        from datetime import datetime
        annee = datetime.now().year
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
                categories=",".join(cp.categories)
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
    jour = db.query(JourTest).filter(JourTest.id == jour_id).first()

    if jour and jour.type == "pratique":
        for cp in data.candidats_pratique:
            existing = db.query(JourTestCandidat).filter(
                JourTestCandidat.jour_test_id == jour_id,
                JourTestCandidat.stagiaire_id == cp.stagiaire_id
            ).first()
            if existing:
                existing.categories = ",".join(cp.categories)
            else:
                jtc = JourTestCandidat(
                    jour_test_id=jour_id,
                    stagiaire_id=cp.stagiaire_id,
                    categories=",".join(cp.categories)
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
    j = db.query(JourTest).filter(JourTest.id == id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouve")
    j.actif = False

    if j.type == "theorie" and j.grille_id:
        from app.models.grille_theorie import UtilisationGrille
        uti = db.query(UtilisationGrille).filter(
            UtilisationGrille.grille_id == j.grille_id,
            UtilisationGrille.session_id == j.session_id
        ).first()
        if uti:
            db.delete(uti)

    if j.type == "theorie":
        from app.models.utilisations_themes import UtilisationTheme
        db.query(UtilisationTheme).filter(
            UtilisationTheme.session_id == j.session_id
        ).delete()

    db.commit()
    return {"message": "Jour supprime"}

# RESULTATS THEORIE
@router.post("/{session_id}/theorie/reponses")
def sauvegarder_reponses(session_id: int, data: ReponsesCandidatCreate, db: DBSession = Depends(get_db)):
    jour = db.query(JourTest).filter(JourTest.id == data.jour_test_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="Jour de test non trouve")

    session = db.query(Session).filter(Session.id == session_id).first()
    resultat = calculer_resultat_theorie_phase2(data.reponses, session_id, session.famille, db)

    rt = ResultatTheorie(
        jour_test_id=data.jour_test_id,
        session_id=session_id,
        stagiaire_id=data.stagiaire_id,
        grille_id=None
    )
    db.add(rt)

    rt.reponses_json = json.dumps(data.reponses)
    rt.note_theme1 = resultat["notes_themes"].get("1")
    rt.note_theme2 = resultat["notes_themes"].get("2")
    rt.note_theme3 = resultat["notes_themes"].get("3")
    rt.note_theme4 = resultat["notes_themes"].get("4")
    rt.note_theme5 = resultat["notes_themes"].get("5")
    rt.note_totale = resultat["note_totale"]
    rt.theme1_ok = resultat["themes_ok"].get("1")
    rt.theme2_ok = resultat["themes_ok"].get("2")
    rt.theme3_ok = resultat["themes_ok"].get("3")
    rt.theme4_ok = resultat["themes_ok"].get("4")
    rt.theme5_ok = resultat["themes_ok"].get("5")
    rt.obtenue = resultat["obtenue"]
    db.commit()

    return {"message": "Reponses sauvegardees", "resultat": resultat}

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
    famille = db.query(Famille).filter(Famille.code == data.famille).first()
    cat = db.query(Categorie).filter(
        Categorie.famille_id == (famille.id if famille else 0),
        Categorie.code == data.categorie
    ).first()
    ut = cat.ut_pratique if cat else 1.0

    e = SessionEpreuve(
        session_id=session_id,
        stagiaire_id=data.stagiaire_id,
        testeur_id=data.testeur_id,
        date=data.date,
        famille=data.famille,
        categorie=data.categorie,
        ut=ut,
        obtenue=data.obtenue,
        note_testeur=data.note_testeur
    )
    db.add(e)
    db.commit()
    return {"message": "Epreuve ajoutee"}

@router.post("/{id}/reouvrir")
def reouvrir_session(id: int, db: DBSession = Depends(get_db)):
    s = db.query(Session).filter(Session.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session non trouvee")
    s.statut = "planifiee"
    db.commit()
    return {"message": "Session reuverte"}

@router.put("/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}/identite")
def toggle_identite(session_id: int, jour_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
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
    s.date_theorie = data.date_theorie
    s.date_pratique_debut = data.date_pratique_debut
    s.date_pratique_fin = data.date_pratique_fin
    s.responsable = data.responsable
    s.note = data.note
    db.commit()
    return {"message": "Session mise a jour"}

@router.put("/{session_id}/jours/{jour_id}/modifier")
def modifier_jour(session_id: int, jour_id: int, data: dict, db: DBSession = Depends(get_db)):
    from datetime import date as date_type
    j = db.query(JourTest).filter(JourTest.id == jour_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jour non trouve")
    j.date = data.get("date")
    j.testeur_id = data.get("testeur_id")
    db.commit()
    return {"message": "Jour modifie"}