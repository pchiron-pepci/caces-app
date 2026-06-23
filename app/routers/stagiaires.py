from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.config_utils import get_pin_admin
from app.models.stagiaire import Stagiaire
from app.models.session_candidat import SessionCandidat
from app.models.jour_test import JourTestCandidat, ResultatTheorie
from app.models.session_epreuve import SessionEpreuve
from app.models.caces_obtenu import CacesObtenu
from app.models.carte_caces import CarteCaces
from app.models.jour_formation import PlanningApprenant
from app.models.non_conformite import NonConformite
from app.models.consentement_rgpd import ConsentementRGPD
from app.models.attestation_neutralite import AttestationNeutralite
from pydantic import BaseModel
from datetime import date
from typing import Optional
import shutil
import os

router = APIRouter(prefix="/stagiaires", tags=["Stagiaires"])

UPLOAD_DIR = "uploads/photos"

class StagiaireCreate(BaseModel):
    nom: str
    prenom: str
    date_naissance: date
    email: Optional[str] = None
    telephone: Optional[str] = None
    employeur: Optional[str] = None
    note: Optional[str] = None

class StagiaireResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    date_naissance: date
    email: Optional[str] = None
    telephone: Optional[str] = None
    employeur: Optional[str] = None
    note: Optional[str] = None
    photo: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=list[StagiaireResponse])
def liste_stagiaires(db: Session = Depends(get_db)):
    return db.query(Stagiaire).filter(Stagiaire.actif == 1).order_by(Stagiaire.nom, Stagiaire.prenom).all()

@router.get("/{id}", response_model=StagiaireResponse)
def get_stagiaire(id: int, db: Session = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    return s

@router.post("/", response_model=StagiaireResponse)
def create_stagiaire(data: StagiaireCreate, db: Session = Depends(get_db)):
    s = Stagiaire(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.put("/{id}", response_model=StagiaireResponse)
def update_stagiaire(id: int, data: StagiaireCreate, db: Session = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    for key, value in data.model_dump().items():
        setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s

@router.post("/photo/{id}")
def upload_photo(id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    import base64 as _b64
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Format non supporte")
    raw = file.file.read()
    s.photo_base64 = _b64.b64encode(raw).decode()
    s.photo = f"/uploads/photos/stagiaire_{id}{ext}"
    db.commit()
    return {"message": "Photo uploadee", "photo_base64": True}

class PhotoBase64Payload(BaseModel):
    photo_base64: str

@router.post("/{id}/photo-upload")
def upload_photo_base64(id: int, payload: PhotoBase64Payload, db: Session = Depends(get_db)):
    import base64 as _b64
    from io import BytesIO
    from PIL import Image
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")
    b64_str = payload.photo_base64
    if ',' in b64_str:
        b64_str = b64_str.split(',', 1)[1]
    try:
        raw = _b64.b64decode(b64_str)
        img = Image.open(BytesIO(raw)).convert('RGB')
        w, h = img.size
        if max(w, h) > 600:
            ratio = 600 / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=80)
        final_b64 = _b64.b64encode(buf.getvalue()).decode()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Image invalide : {exc}")
    s.photo_base64 = final_b64
    s.photo = f"/uploads/photos/stagiaire_{id}.jpg"
    db.commit()
    return {"ok": True}

@router.delete("/{id}/photo")
def supprimer_photo(id: int, db: Session = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")
    s.photo_base64 = None
    s.photo = None
    db.commit()
    return {"ok": True}

@router.delete("/{id}")
def delete_stagiaire(id: int, pin: str, db: Session = Depends(get_db)):
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")

    rattachements = []

    n = db.query(SessionCandidat).filter(SessionCandidat.stagiaire_id == id).count()
    if n: rattachements.append(f"inscrit à {n} session(s)")

    n = db.query(JourTestCandidat).filter(JourTestCandidat.stagiaire_id == id).count()
    if n: rattachements.append(f"planifié sur {n} jour(s) de test")

    n = db.query(ResultatTheorie).filter(ResultatTheorie.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} résultat(s) théorique(s)")

    n = db.query(SessionEpreuve).filter(SessionEpreuve.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} résultat(s) pratique(s)")

    n = db.query(CacesObtenu).filter(CacesObtenu.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} CACES® obtenu(s)")

    n = db.query(CarteCaces).filter(CarteCaces.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} carte(s) CACES®")

    n = db.query(PlanningApprenant).filter(PlanningApprenant.stagiaire_id == id).count()
    if n: rattachements.append(f"planifié dans {n} jour(s) de formation")

    n = db.query(NonConformite).filter(NonConformite.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} non-conformité(s) liée(s)")

    n = db.query(ConsentementRGPD).filter(ConsentementRGPD.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} consentement(s) RGPD")

    n = db.query(AttestationNeutralite).filter(AttestationNeutralite.stagiaire_id == id).count()
    if n: rattachements.append(f"{n} attestation(s) de neutralité")

    if rattachements:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Suppression impossible — rattachements existants : " + ", ".join(rattachements)
        )

    db.delete(s)
    db.commit()
    return {"message": "Stagiaire supprimé"}

@router.get("/{id}/historique")
def get_historique_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.session_candidat import SessionCandidat
    from app.models.session import Session as SessionModel
    from app.models.jour_test import JourTest, JourTestCandidat, ResultatTheorie
    from app.models.session_epreuve import SessionEpreuve

    candidats = db.query(SessionCandidat).filter(
        SessionCandidat.stagiaire_id == id,
        SessionCandidat.actif == True
    ).all()

    result = []
    for sc in candidats:
        session = db.query(SessionModel).filter(SessionModel.id == sc.session_id).first()
        if not session:
            continue

        theorie_results = db.query(ResultatTheorie).filter(
            ResultatTheorie.session_id == sc.session_id,
            ResultatTheorie.stagiaire_id == id
        ).all()

        theorie = None
        if theorie_results:
            obtenu_list = [r for r in theorie_results if r.obtenue == True]
            if obtenu_list:
                best = max(obtenu_list, key=lambda r: r.id)
                theorie = {"statut": "obtenu", "note": round(best.note_totale) if best.note_totale is not None else None}
            else:
                non_obtenu = [r for r in theorie_results if r.obtenue == False]
                if non_obtenu:
                    recent = max(non_obtenu, key=lambda r: r.id)
                    theorie = {"statut": "non_obtenu", "note": round(recent.note_totale) if recent.note_totale is not None else None}
                else:
                    theorie = {"statut": "planifie", "note": None}
        else:
            theorie_jours = db.query(JourTest).filter(
                JourTest.session_id == sc.session_id,
                JourTest.type == 'theorie',
                JourTest.actif == True
            ).all()
            for tj in theorie_jours:
                jtc = db.query(JourTestCandidat).filter(
                    JourTestCandidat.jour_test_id == tj.id,
                    JourTestCandidat.stagiaire_id == id
                ).first()
                if jtc:
                    theorie = {"statut": "planifie", "note": None}
                    break

        epreuves = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == sc.session_id,
            SessionEpreuve.stagiaire_id == id
        ).all()

        pratique_jours = db.query(JourTest).filter(
            JourTest.session_id == sc.session_id,
            JourTest.type == 'pratique',
            JourTest.actif == True
        ).all()

        planned_cats = set()
        for j in pratique_jours:
            jtcs = db.query(JourTestCandidat).filter(
                JourTestCandidat.jour_test_id == j.id,
                JourTestCandidat.stagiaire_id == id
            ).all()
            for jtc in jtcs:
                for cat in (jtc.categories or '').split(','):
                    cat = cat.strip()
                    if cat:
                        planned_cats.add(cat)

        evaluated_cats = {e.categorie for e in epreuves}
        pratique = []
        for e in epreuves:
            if e.obtenue == True:
                statut = "obtenu"
            elif e.obtenue == False:
                statut = "non_obtenu"
            else:
                statut = "planifie"
            pratique.append({
                "categorie": e.categorie,
                "statut": statut,
                "options": e.options_obtenues or ""
            })
        for cat in sorted(planned_cats - evaluated_cats):
            pratique.append({"categorie": cat, "statut": "planifie", "options": ""})

        result.append({
            "session_id": session.id,
            "reference": session.reference or f"Session #{session.id}",
            "famille": session.famille,
            "date_theorie": session.date_theorie.isoformat() if session.date_theorie else None,
            "date_pratique_debut": session.date_pratique_debut.isoformat() if session.date_pratique_debut else None,
            "date_pratique_fin": session.date_pratique_fin.isoformat() if session.date_pratique_fin else None,
            "statut": session.statut,
            "theorie": theorie,
            "pratique": pratique,
        })

    result.sort(key=lambda x: x["session_id"], reverse=True)
    return result


@router.get("/{id}/cartes-emises")
def get_cartes_emises_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.carte_caces import CarteCaces
    cartes = (
        db.query(CarteCaces)
        .filter(CarteCaces.stagiaire_id == id, CarteCaces.statut.in_(["emise", "remplacee"]))
        .order_by(CarteCaces.date_generation.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "numero_carte": c.numero_carte,
            "famille": c.famille,
            "date_generation": c.date_generation.isoformat() if c.date_generation else None,
            "statut": c.statut,
        }
        for c in cartes
    ]


@router.get("/{id}/caces-valides")
def get_caces_valides_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.caces_obtenu import CacesObtenu
    from app.models.session_epreuve import SessionEpreuve
    from app.models.testeur import Testeur

    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == id, CacesObtenu.statut == "valide")
        .order_by(CacesObtenu.numero_ordre.desc())
        .all()
    )

    result = []
    for co in cos:
        ep = db.query(SessionEpreuve).filter(
            SessionEpreuve.stagiaire_id == id,
            SessionEpreuve.session_id == co.session_id,
            SessionEpreuve.categorie == co.categorie,
            SessionEpreuve.obtenue == True,
        ).first()
        testeur_nom = ""
        if ep and ep.testeur_id:
            t = db.query(Testeur).filter(Testeur.id == ep.testeur_id).first()
            if t:
                testeur_nom = f"{t.nom} {t.prenom}"

        result.append({
            "id": co.id,
            "numero_ordre": co.numero_ordre,
            "famille": co.famille,
            "categorie": co.categorie,
            "options_obtenues": co.options_obtenues or "",
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
            "testeur_nom": testeur_nom,
        })

    return result


@router.get("/{stag_id}/base-theorique")
def base_theorique_dispense(stag_id: int, famille: str, session_id: int | None = None, db: Session = Depends(get_db)):
    from datetime import date, timedelta
    from app.models.jour_test import ResultatTheorie, JourTest
    from app.models.caces_obtenu import CacesObtenu
    from app.models.session import Session as SessionModel

    candidates = []  # liste de dicts {date, type, reference, source, lien, source_id}

    # helper 12 mois : base valable si base + 1 an - 1 jour >= aujourd'hui
    def _limite_dispense(d):
        try:
            return date(d.year + 1, d.month, d.day) - timedelta(days=1)
        except ValueError:
            return date(d.year + 1, 3, 1) - timedelta(days=1)
    today = date.today()

    # --- Source R1 : CACES non-extension, meme famille, valide/a_valider, < 12 mois ---
    caces_list = (
        db.query(CacesObtenu)
        .filter(
            CacesObtenu.stagiaire_id == stag_id,
            CacesObtenu.famille == famille,
            CacesObtenu.statut.in_(["valide", "a_valider"]),
            CacesObtenu.post_cloture == False,
        )
        .all()
    )
    for c in caces_list:
        if c.date_obtention and _limite_dispense(c.date_obtention) >= today:
            candidates.append({
                "date": c.date_obtention,
                "type": "caces",
                "reference": f"CACES {c.famille} cat {c.categorie}" + (f" n°{c.numero_ordre}" if c.numero_ordre else ""),
                "source": "R1",
                "source_id": c.id,
                "lien": f"/cartes-caces",
            })

    # --- Source R2-a : theorie de la SESSION COURANTE (si session_id fourni) ---
    if session_id:
        rt_courante = (
            db.query(ResultatTheorie)
            .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
            .filter(
                ResultatTheorie.stagiaire_id == stag_id,
                ResultatTheorie.session_id == session_id,
                ResultatTheorie.obtenue == True,
                ResultatTheorie.bloque != True,
            )
            .order_by(JourTest.date.desc(), ResultatTheorie.id.desc())
            .first()
        )
        if rt_courante:
            jt = db.query(JourTest).filter(JourTest.id == rt_courante.jour_test_id).first()
            if jt and jt.date and _limite_dispense(jt.date) >= today:
                candidates.append({
                    "date": jt.date, "type": "theorie", "reference": "Theorie de la session courante",
                    "source": "R2-a", "source_id": rt_courante.id,
                    "lien": f"/sessions/{session_id}/projection/{rt_courante.jour_test_id}",
                })

    # --- Source R2-b : theorie ORPHELINE d'une autre session (aucun CACES rattache) ---
    rts = (
        db.query(ResultatTheorie)
        .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
        .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
        .filter(
            ResultatTheorie.stagiaire_id == stag_id,
            ResultatTheorie.obtenue == True,
            ResultatTheorie.bloque != True,
            SessionModel.famille == famille,
        )
    )
    if session_id:
        rts = rts.filter(ResultatTheorie.session_id != session_id)
    for rt in rts.all():
        # orpheline = aucun CacesObtenu ne pointe vers ce ResultatTheorie
        a_un_caces = db.query(CacesObtenu).filter(CacesObtenu.resultat_theorie_id == rt.id).first()
        if a_un_caces:
            continue
        jt = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
        if jt and jt.date and _limite_dispense(jt.date) >= today:
            candidates.append({
                "date": jt.date, "type": "theorie", "reference": "Theorie (autre session)",
                "source": "R2-b", "source_id": rt.id,
                "lien": "",
            })

    if not candidates:
        return {"possible": False}

    # garder la PLUS RECENTE
    meilleure = max(candidates, key=lambda x: x["date"])
    return {
        "possible": True,
        "type": meilleure["type"],
        "date_origine": meilleure["date"].isoformat(),
        "reference": meilleure["reference"],
        "date_limite_dispense": _limite_dispense(meilleure["date"]).isoformat(),
        "lien": meilleure["lien"],
        "source": meilleure["source"],
    }