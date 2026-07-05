from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.orm import Session
from app.database import get_db
from app.config_utils import get_pin_admin
from app.services import storage
from app.services.caces_obtenus import _date_initiale_depuis_echeance, limite_12_mois
from app.models.stagiaire import Stagiaire
from app.models.session_candidat import SessionCandidat
from app.models.jour_test import JourTest, JourTestCandidat, ResultatTheorie
from app.models.session_epreuve import SessionEpreuve
from app.models.caces_obtenu import CacesObtenu
from app.models.carte_caces import CarteCaces
from app.models.jour_formation import PlanningApprenant
from app.models.non_conformite import NonConformite
from app.models.consentement_rgpd import ConsentementRGPD
from app.models.attestation_neutralite import AttestationNeutralite
from app.models.session import Session as SessionModel
from app.services.reprise_historique import get_or_create_session_reprise
from pydantic import BaseModel
from datetime import date
from typing import Optional
import shutil
import os

router = APIRouter(prefix="/stagiaires", tags=["Stagiaires"])

UPLOAD_DIR = "uploads/photos"

class CacesRepriseCreate(BaseModel):
    famille: str
    categorie: str
    options_obtenues: Optional[str] = None
    date_obtention: date
    date_echeance: date
    ancien_numero: str
    testeur_id: int
    pin: str

class TheorieRepriseCreate(BaseModel):
    famille: str
    date_obtention: date
    testeur_id: int
    pin: str

class PratiqueRepriseCreate(BaseModel):
    famille: str
    categorie: str
    options_obtenues: Optional[str] = None
    date_obtention: date
    testeur_id: int
    pin: str

class SuppressionData(BaseModel):
    pin: str

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
            "ancien_numero": co.ancien_numero,
            "famille": co.famille,
            "categorie": co.categorie,
            "options_obtenues": co.options_obtenues or "",
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
            "testeur_nom": testeur_nom,
            "testeur_id": (ep.testeur_id if ep else None),
            "justificatif_nom": co.justificatif_nom or "",
            "a_justificatif": bool(co.justificatif_cle),
        })

    return result


@router.get("/{id}/reprises")
def get_reprises_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.testeur import Testeur
    reference = "REPRISE-" + str(id)
    sess = db.query(SessionModel).filter(
        SessionModel.type == "reprise",
        SessionModel.reference == reference,
    ).first()
    if not sess:
        return []
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == id, CacesObtenu.session_id == sess.id)
        .order_by(CacesObtenu.famille, CacesObtenu.categorie)
        .all()
    )
    result = []
    for co in cos:
        ep = db.query(SessionEpreuve).filter(
            SessionEpreuve.stagiaire_id == id,
            SessionEpreuve.session_id == sess.id,
            SessionEpreuve.categorie == co.categorie,
        ).first()
        testeur_nom = ""
        if ep and ep.testeur_id:
            t = db.query(Testeur).filter(Testeur.id == ep.testeur_id).first()
            if t:
                testeur_nom = f"{t.nom} {t.prenom}"
        result.append({
            "id": co.id,
            "famille": co.famille,
            "categorie": co.categorie,
            "options_obtenues": co.options_obtenues or "",
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
            "ancien_numero": co.ancien_numero or "",
            "organisme_externe": co.organisme_externe or "",
            "justificatif_nom": co.justificatif_nom or "",
            "a_justificatif": bool(co.justificatif_cle),
            "testeur_nom": testeur_nom,
            "testeur_id": ep.testeur_id if ep else None,
        })
    return result


@router.post("/{id}/reprises")
def creer_reprise_caces(id: int, data: CacesRepriseCreate, db: Session = Depends(get_db)):
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if data.date_echeance <= data.date_obtention:
        raise HTTPException(status_code=400, detail="La date d'echeance doit etre posterieure a la date d'obtention.")
    sess = get_or_create_session_reprise(id, db)
    existe = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == id,
        CacesObtenu.session_id == sess.id,
        CacesObtenu.categorie == data.categorie,
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="Un CACES repris existe deja pour cette categorie. Supprimez-le d'abord pour le remplacer.")
    co = CacesObtenu(
        stagiaire_id=id,
        session_id=sess.id,
        famille=data.famille,
        categorie=data.categorie,
        options_obtenues=data.options_obtenues or None,
        date_obtention=data.date_obtention,
        date_echeance=data.date_echeance,
        statut="valide",
        numero_ordre=None,
        ancien_numero=data.ancien_numero,
    )
    db.add(co)
    ep = SessionEpreuve(
        session_id=sess.id,
        stagiaire_id=id,
        testeur_id=data.testeur_id,
        date=data.date_obtention,
        famille=data.famille,
        categorie=data.categorie,
        options_obtenues=data.options_obtenues or None,
        obtenue=True,
    )
    db.add(ep)
    db.commit()
    db.refresh(co)
    return {"message": "CACES repris ajoute", "id": co.id}


@router.post("/{id}/reprises/theorie")
def creer_reprise_theorie(id: int, data: TheorieRepriseCreate, db: Session = Depends(get_db)):
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")

    # ── Garde-fou EXCLUSIVITE TOTALE (au niveau famille pour la theorie) ──
    # 1) CACES complet repris dans cette famille (CacesObtenu avec ancien_numero non NULL)
    caces_complet = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == id,
        CacesObtenu.famille == data.famille,
        CacesObtenu.ancien_numero.isnot(None),
    ).first()
    if caces_complet:
        raise HTTPException(status_code=409, detail=f"Un CACES complet repris existe deja en {data.famille} — une theorie orpheline est inutile (les extensions repartent des dates du CACES).")

    # session receptacle de la famille (creee si besoin) — sert aussi a detecter les orphelines existantes
    sess = get_or_create_session_reprise(id, db, famille=data.famille)

    # 2) Theorie deja obtenue dans cette famille (NATIVE NORYX ou REPRISE) → doublon interdit
    theorie_existante = (
        db.query(ResultatTheorie)
        .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
        .filter(
            ResultatTheorie.stagiaire_id == id,
            ResultatTheorie.obtenue == True,
            SessionModel.famille == data.famille,
        )
        .first()
    )
    if theorie_existante:
        raise HTTPException(status_code=409, detail=f"Une theorie est deja enregistree pour ce candidat en {data.famille} (interne NORYX ou reprise). Pas de doublon possible.")

    # 3) Pratique orpheline REPRISE dans cette famille (session receptacle UNIQUEMENT, pas les natives) → exclusivite
    pratique_orpheline = db.query(SessionEpreuve).filter(
        SessionEpreuve.stagiaire_id == id,
        SessionEpreuve.session_id == sess.id,
        SessionEpreuve.obtenue == True,
    ).first()
    if pratique_orpheline:
        raise HTTPException(status_code=409, detail=f"Une pratique orpheline reprise existe deja en {data.famille} — theorie + pratique reprises = CACES complet (a saisir comme CACES repris).")

    # ── Creation : JourTest technique (theorie) + ResultatTheorie ──
    jt = JourTest(
        session_id=sess.id,
        type="theorie",
        date=data.date_obtention,
        testeur_id=data.testeur_id,
        grille_id=None,
    )
    db.add(jt)
    db.flush()

    rt = ResultatTheorie(
        jour_test_id=jt.id,
        session_id=sess.id,
        stagiaire_id=id,
        obtenue=True,
        mode="degrade",
        testeur_id=data.testeur_id,
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return {"message": "Theorie reprise ajoutee", "id": rt.id}


@router.post("/{id}/reprises/pratique")
def creer_reprise_pratique(id: int, data: PratiqueRepriseCreate, db: Session = Depends(get_db)):
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")

    # ── Garde-fou EXCLUSIVITE ──
    # 1) CACES complet repris dans cette CATEGORIE → bloque la pratique orpheline
    caces_complet = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == id,
        CacesObtenu.famille == data.famille,
        CacesObtenu.categorie == data.categorie,
        CacesObtenu.ancien_numero.isnot(None),
    ).first()
    if caces_complet:
        raise HTTPException(status_code=409, detail=f"Un CACES complet repris existe deja en {data.categorie} — pas d'orpheline (les extensions repartent des dates du CACES).")

    sess = get_or_create_session_reprise(id, db, famille=data.famille)

    # 2) Theorie orpheline REPRISE dans cette famille (session receptacle UNIQUEMENT, pas les natives) → exclusivite
    theorie_orpheline = db.query(ResultatTheorie).filter(
        ResultatTheorie.stagiaire_id == id,
        ResultatTheorie.session_id == sess.id,
        ResultatTheorie.obtenue == True,
    ).first()
    if theorie_orpheline:
        raise HTTPException(status_code=409, detail=f"Une theorie orpheline reprise existe deja en {data.famille} — theorie + pratique reprises = CACES complet (a saisir comme CACES repris).")

    # 3) Pratique deja obtenue dans la meme categorie (NATIVE NORYX ou REPRISE) → doublon interdit
    pratique_existante = db.query(SessionEpreuve).filter(
        SessionEpreuve.stagiaire_id == id,
        SessionEpreuve.famille == data.famille,
        SessionEpreuve.categorie == data.categorie,
        SessionEpreuve.obtenue == True,
    ).first()
    if pratique_existante:
        raise HTTPException(status_code=409, detail=f"Une pratique est deja enregistree pour ce candidat en {data.categorie} (interne NORYX ou reprise). Pas de doublon possible.")

    # ── Creation : SessionEpreuve (obtenue=True, testeur obligatoire) ──
    ep = SessionEpreuve(
        session_id=sess.id,
        stagiaire_id=id,
        testeur_id=data.testeur_id,
        date=data.date_obtention,
        famille=data.famille,
        categorie=data.categorie,
        options_obtenues=data.options_obtenues or None,
        obtenue=True,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return {"message": "Pratique reprise ajoutee", "id": ep.id}


@router.post("/{id}/reprises/pratique/{ep_id}/supprimer")
def supprimer_reprise_pratique(id: int, ep_id: int, data: SuppressionData, db: Session = Depends(get_db)):
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    ep = db.query(SessionEpreuve).filter(SessionEpreuve.id == ep_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Epreuve introuvable")
    # Securite : l'epreuve doit appartenir a une session receptacle de CE stagiaire
    sess = db.query(SessionModel).filter(SessionModel.id == ep.session_id).first()
    if not sess or not (sess.reference or "").startswith(f"REPRISE-{id}-"):
        raise HTTPException(status_code=403, detail="Epreuve hors perimetre reprise de ce stagiaire")
    # VERROU REGLEMENTAIRE : aucun CACES valide ne doit reposer sur cette pratique
    bloquant = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == ep.stagiaire_id,
        CacesObtenu.session_id == ep.session_id,
        CacesObtenu.categorie == ep.categorie,
        CacesObtenu.statut == "valide",
    ).first()
    if bloquant:
        raise HTTPException(status_code=409, detail=(
            "suppression impossible : un CACES valide repose sur cette pratique reprise. "
            "Annulez d'abord le CACES concerne. NORYX ne rattrape jamais automatiquement."
        ))
    db.delete(ep)
    db.commit()
    return {"ok": True, "message": "Pratique reprise supprimee"}


@router.post("/{id}/reprises/theorie/{rt_id}/supprimer")
def supprimer_reprise_theorie(id: int, rt_id: int, data: SuppressionData, db: Session = Depends(get_db)):
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    rt = db.query(ResultatTheorie).filter(ResultatTheorie.id == rt_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Theorie introuvable")
    # Securite : la theorie doit appartenir a une session receptacle de CE stagiaire
    sess = db.query(SessionModel).filter(SessionModel.id == rt.session_id).first()
    if not sess or not (sess.reference or "").startswith(f"REPRISE-{id}-"):
        raise HTTPException(status_code=403, detail="Theorie hors perimetre reprise de ce stagiaire")
    # VERROU REGLEMENTAIRE : aucun CACES valide ne doit reposer sur cette theorie
    bloquant = db.query(CacesObtenu).filter(
        CacesObtenu.resultat_theorie_id == rt.id,
        CacesObtenu.statut == "valide",
    ).first()
    if bloquant:
        raise HTTPException(status_code=409, detail=(
            "suppression impossible : un CACES valide repose sur cette theorie reprise. "
            "Annulez d'abord le CACES concerne. NORYX ne rattrape jamais automatiquement."
        ))
    # Supprimer le JourTest associe SEULEMENT s'il n'est pas partage par un autre ResultatTheorie
    jt_id = rt.jour_test_id
    db.delete(rt)
    db.flush()  # pour que le COUNT suivant ne compte plus rt
    if jt_id is not None:
        autres = db.query(ResultatTheorie).filter(ResultatTheorie.jour_test_id == jt_id).count()
        if autres == 0:
            jt = db.query(JourTest).filter(JourTest.id == jt_id).first()
            if jt:
                db.delete(jt)
    db.commit()
    return {"ok": True, "message": "Theorie reprise supprimee"}


@router.post("/{id}/reprises/caces/{co_id}/supprimer")
def supprimer_reprise_caces(id: int, co_id: int, data: SuppressionData, db: Session = Depends(get_db)):
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == co_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="CACES repris introuvable")
    # Doit etre une VRAIE reprise CACES complet (ancien_numero rempli)
    if not co.ancien_numero:
        raise HTTPException(status_code=400, detail="Ce CACES n'est pas une reprise (pas d'ancien numero)")
    # Securite : session SENTINELLE EXACTE "REPRISE-{id}" (PAS un receptacle "REPRISE-{id}-famille")
    sess = db.query(SessionModel).filter(SessionModel.id == co.session_id).first()
    if not sess or (sess.reference or "") != f"REPRISE-{id}":
        raise HTTPException(status_code=403, detail="CACES hors perimetre sentinelle de ce stagiaire")
    # VERROU REGLEMENTAIRE : aucun AUTRE CACES valide ne doit avoir cette reprise pour base d'extension
    bloquant = db.query(CacesObtenu).filter(
        CacesObtenu.caces_initial_id == co.id,
        CacesObtenu.statut == "valide",
    ).first()
    if bloquant:
        raise HTTPException(status_code=409, detail=(
            "suppression impossible : un CACES valide a ete forme par extension de cette reprise. "
            "Annulez d'abord le CACES concerne. NORYX ne rattrape jamais automatiquement."
        ))

    # VERROU DISPENSE : ce CACES repris ne doit pas fonder une dispense de theorie en cours.
    disp = db.query(SessionCandidat).filter(
        SessionCandidat.dispense_source_type == "caces",
        SessionCandidat.dispense_source_id == co.id,
    ).first()
    if disp:
        raise HTTPException(status_code=409, detail=(
            "suppression impossible : ce CACES fonde une dispense de theorie pour un candidat "
            "en session. Retirez d'abord la dispense."
        ))

    # VERROU CARTE : une carte emise pour cette famille peut avoir fige ce CACES.
    from app.models.carte_caces import CarteCaces
    carte = db.query(CarteCaces).filter(
        CarteCaces.stagiaire_id == id,
        CarteCaces.famille == co.famille,
        CarteCaces.statut == "emise",
    ).first()
    if carte:
        raise HTTPException(status_code=409, detail=(
            "suppression impossible : une carte CACES active (n. %s) a ete emise pour cette "
            "famille et peut inclure ce CACES. Annulez ou remplacez d'abord la carte." % (
                carte.numero_carte or "")
        ))

    # Supprimer le CacesObtenu repris ET la SessionEpreuve associee (meme triplet, session sentinelle)
    _sid, _sess_id, _cat = co.stagiaire_id, co.session_id, co.categorie
    eps = db.query(SessionEpreuve).filter(
        SessionEpreuve.stagiaire_id == _sid,
        SessionEpreuve.session_id == _sess_id,
        SessionEpreuve.categorie == _cat,
    ).all()
    db.delete(co)
    for ep in eps:
        db.delete(ep)
    db.commit()
    return {"ok": True, "message": "CACES repris supprime"}


@router.put("/{id}/reprises/caces/{co_id}")
def modifier_reprise_caces(id: int, co_id: int, data: CacesRepriseCreate, db: Session = Depends(get_db)):
    """Modifie un CACES repris interne. Bloque si le CACES a deja servi
    (extension, dispense en cours, carte emise) : dans ce cas l'admin doit
    d'abord annuler la dependance."""
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if data.date_echeance <= data.date_obtention:
        raise HTTPException(status_code=400, detail="La date d'echeance doit etre posterieure a la date d'obtention.")

    co = db.query(CacesObtenu).filter(CacesObtenu.id == co_id, CacesObtenu.stagiaire_id == id).first()
    if not co:
        raise HTTPException(status_code=404, detail="CACES repris introuvable")
    if not co.ancien_numero:
        raise HTTPException(status_code=400, detail="Ce CACES n'est pas une reprise (pas d'ancien numero)")

    # BLOCAGE : ne pas modifier un CACES qui a deja servi.
    from app.models.carte_caces import CarteCaces
    ext = db.query(CacesObtenu).filter(
        CacesObtenu.caces_initial_id == co.id, CacesObtenu.statut == "valide"
    ).first()
    if ext:
        raise HTTPException(status_code=409, detail=(
            "Modification impossible : un CACES valide a ete forme par extension de cette reprise. "
            "Annulez d'abord le CACES concerne."
        ))
    disp = db.query(SessionCandidat).filter(
        SessionCandidat.dispense_source_type == "caces",
        SessionCandidat.dispense_source_id == co.id,
    ).first()
    if disp:
        raise HTTPException(status_code=409, detail=(
            "Modification impossible : ce CACES fonde une dispense de theorie pour un candidat "
            "en session. Retirez d'abord la dispense."
        ))
    carte = db.query(CarteCaces).filter(
        CarteCaces.stagiaire_id == id,
        CarteCaces.famille == co.famille,
        CarteCaces.statut == "emise",
    ).first()
    if carte:
        raise HTTPException(status_code=409, detail=(
            "Modification impossible : une carte CACES active (n. %s) a ete emise pour cette "
            "famille et peut inclure ce CACES. Annulez ou remplacez d'abord la carte." % (
                carte.numero_carte or "")
        ))

    # Unicite : si la categorie change, verifier qu'aucun autre CACES repris ne l'occupe deja.
    if data.categorie != co.categorie:
        conflit = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == id,
            CacesObtenu.session_id == co.session_id,
            CacesObtenu.categorie == data.categorie,
            CacesObtenu.id != co.id,
        ).first()
        if conflit:
            raise HTTPException(status_code=409, detail="Un CACES repris existe deja pour cette categorie.")

    ancienne_cat = co.categorie

    # Mise a jour du CacesObtenu
    co.famille = data.famille
    co.categorie = data.categorie
    co.options_obtenues = data.options_obtenues or None
    co.date_obtention = data.date_obtention
    co.date_echeance = data.date_echeance
    co.ancien_numero = data.ancien_numero

    # Mise a jour de la SessionEpreuve associee (meme session sentinelle, ancienne categorie)
    ep = db.query(SessionEpreuve).filter(
        SessionEpreuve.stagiaire_id == id,
        SessionEpreuve.session_id == co.session_id,
        SessionEpreuve.categorie == ancienne_cat,
    ).first()
    if ep:
        ep.famille = data.famille
        ep.categorie = data.categorie
        ep.options_obtenues = data.options_obtenues or None
        ep.date = data.date_obtention
        ep.testeur_id = data.testeur_id

    db.commit()
    return {"ok": True, "message": "CACES repris modifie", "id": co.id}


@router.get("/{id}/reprises/orphelines")
def get_reprises_orphelines(id: int, db: Session = Depends(get_db)):
    from app.models.testeur import Testeur
    from app.models.jour_test import JourTest, ResultatTheorie

    # Sessions receptacles orphelines : reference "REPRISE-{id}-{famille}" (avec tiret + famille).
    # PAS la sentinelle "REPRISE-{id}" (CACES complets).
    prefixe = "REPRISE-" + str(id) + "-"
    sessions = db.query(SessionModel).filter(
        SessionModel.type == "reprise",
        SessionModel.reference.like(prefixe + "%"),
    ).all()
    if not sessions:
        return {"theories": [], "pratiques": []}

    sess_ids = [s.id for s in sessions]

    # cache testeurs (anti N+1)
    def _testeur_nom(tid):
        if not tid:
            return ""
        t = db.query(Testeur).filter(Testeur.id == tid).first()
        return f"{t.nom} {t.prenom}" if t else ""

    # --- Theories orphelines (ResultatTheorie dans les sessions receptacles) ---
    theories = []
    rts = db.query(ResultatTheorie).filter(
        ResultatTheorie.stagiaire_id == id,
        ResultatTheorie.session_id.in_(sess_ids),
    ).all()
    for rt in rts:
        jt = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
        sess = next((s for s in sessions if s.id == rt.session_id), None)
        theories.append({
            "id": rt.id,
            "famille": sess.famille if sess else "",
            "date_obtention": jt.date.isoformat() if (jt and jt.date) else None,
            "testeur_nom": _testeur_nom(rt.testeur_id),
            "testeur_id": rt.testeur_id,
        })

    # --- Pratiques orphelines (SessionEpreuve dans les sessions receptacles) ---
    pratiques = []
    eps = db.query(SessionEpreuve).filter(
        SessionEpreuve.stagiaire_id == id,
        SessionEpreuve.session_id.in_(sess_ids),
        SessionEpreuve.obtenue == True,
    ).all()
    for ep in eps:
        pratiques.append({
            "id": ep.id,
            "famille": ep.famille,
            "categorie": ep.categorie,
            "options_obtenues": ep.options_obtenues or "",
            "date_obtention": ep.date.isoformat() if ep.date else None,
            "testeur_nom": _testeur_nom(ep.testeur_id),
            "testeur_id": ep.testeur_id,
        })

    return {"theories": theories, "pratiques": pratiques}


@router.get("/{stag_id}/base-theorique")
def base_theorique_dispense(stag_id: int, famille: str, session_id: int | None = None, db: Session = Depends(get_db)):
    from app.services.caces_obtenus import detecter_base_theorique
    return detecter_base_theorique(db, stag_id, famille, session_id)


@router.post("/{id}/caces-externe")
async def creer_caces_externe(
    id: int,
    request: Request,
    famille: str = Form(...),
    categorie: str = Form(...),
    date_echeance: str = Form(...),
    organisme: str = Form(...),
    options: str = Form(""),
    pin: str = Form(...),
    fichier: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    from datetime import date as _date, datetime as _dt
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not organisme.strip():
        raise HTTPException(status_code=400, detail="Le nom de l'organisme est obligatoire.")
    try:
        ech = _dt.strptime(date_echeance, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Date d'echeance invalide.")
    if ech.year > _date.today().year + 15 or ech.year < 1990:
        raise HTTPException(status_code=400, detail="Date d'echeance hors plage plausible.")

    sess = get_or_create_session_reprise(id, db)

    existe = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == id,
        CacesObtenu.session_id == sess.id,
        CacesObtenu.categorie == categorie,
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="Un CACES est deja enregistre pour cette categorie dans les reprises. Supprimez-le d'abord.")

    # Test d'exploitabilite (regle 12 mois) — informatif, NE BLOQUE PAS
    origine = _date_initiale_depuis_echeance(famille, ech)
    exploitable = limite_12_mois(origine) >= _date.today()

    cle = None
    nom_fichier = None
    if fichier is not None and fichier.filename:
        nom = fichier.filename
        ext = nom.rsplit(".", 1)[1].lower() if "." in nom else ""
        if ext not in storage.EXTENSIONS_AUTORISEES:
            raise HTTPException(status_code=400, detail="Type de fichier non autorise (PDF, Word ou Excel).")
        contenu = await fichier.read()
        if len(contenu) > storage.TAILLE_MAX:
            raise HTTPException(status_code=400, detail="Fichier trop volumineux (10 Mo maximum).")
        if contenu:
            cle = storage.construire_cle("caces-externes", nom)
            storage.upload_fichier(contenu, cle, fichier.content_type or "application/octet-stream")
            nom_fichier = nom[:255]

    co = CacesObtenu(
        stagiaire_id=id,
        session_id=sess.id,
        famille=famille,
        categorie=categorie,
        date_obtention=origine,
        date_echeance=ech,
        statut="valide",
        numero_ordre=None,
        organisme_externe=organisme.strip()[:200],
        options_obtenues=(options.strip() or None),
        justificatif_cle=cle,
        justificatif_nom=nom_fichier,
    )
    db.add(co)
    ep = SessionEpreuve(
        session_id=sess.id,
        stagiaire_id=id,
        testeur_id=None,
        date=origine,
        famille=famille,
        categorie=categorie,
        obtenue=True,
    )
    db.add(ep)
    db.commit()
    db.refresh(co)

    msg = "CACES externe enregistre."
    if not exploitable:
        msg = ("CACES externe enregistre, mais son echeance ne permet pas de servir de "
               "dispense/base d'extension aujourd'hui (hors de la fenetre des 12 mois).")
    return {"message": msg, "id": co.id, "exploitable": exploitable}


@router.delete("/{id}/reprises/caces/{co_id}/justificatif")
def supprimer_justificatif_reprise(id: int, co_id: int, data: SuppressionData, db: Session = Depends(get_db)):
    """Supprime le justificatif R2 d'un CACES repris (le CACES lui-meme est conserve)."""
    if data.pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == co_id, CacesObtenu.stagiaire_id == id).first()
    if not co:
        raise HTTPException(status_code=404, detail="CACES repris introuvable")
    if not co.justificatif_cle:
        raise HTTPException(status_code=404, detail="Aucun justificatif a supprimer")
    try:
        storage.delete_fichier(co.justificatif_cle)
    except Exception:
        pass
    co.justificatif_cle = None
    co.justificatif_nom = None
    db.commit()
    return {"ok": True, "message": "Justificatif supprime"}


@router.post("/{id}/reprises/caces/{co_id}/justificatif")
async def upload_justificatif_reprise(
    id: int, co_id: int,
    fichier: UploadFile = File(...),
    pin: str = Form(...),
    db: Session = Depends(get_db),
):
    """Attache (ou remplace) un justificatif R2 sur un CACES repris interne."""
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == co_id, CacesObtenu.stagiaire_id == id).first()
    if not co:
        raise HTTPException(status_code=404, detail="CACES repris introuvable")
    if not fichier or not fichier.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni.")
    nom = fichier.filename
    ext = nom.rsplit(".", 1)[1].lower() if "." in nom else ""
    if ext not in storage.EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Type de fichier non autorise (PDF, Word ou Excel).")
    contenu = await fichier.read()
    if len(contenu) > storage.TAILLE_MAX:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (10 Mo maximum).")
    if not contenu:
        raise HTTPException(status_code=400, detail="Fichier vide.")
    if co.justificatif_cle:
        try:
            storage.delete_fichier(co.justificatif_cle)
        except Exception:
            pass
    cle = storage.construire_cle("caces-reprises", nom)
    storage.upload_fichier(contenu, cle, fichier.content_type or "application/octet-stream")
    co.justificatif_cle = cle
    co.justificatif_nom = nom[:255]
    db.commit()
    return {"ok": True, "justificatif_nom": co.justificatif_nom}


@router.put("/{id}/caces-externe/{caces_id}")
async def modifier_caces_externe(
    id: int, caces_id: int,
    famille: str = Form(...),
    categorie: str = Form(...),
    date_echeance: str = Form(...),
    organisme: str = Form(...),
    options: str = Form(""),
    pin: str = Form(...),
    db: Session = Depends(get_db),
):
    """Modifie un CACES externe. Bloque si extension/dispense/carte dependante."""
    from datetime import datetime as _dt
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not organisme.strip():
        raise HTTPException(status_code=400, detail="Le nom de l'organisme est obligatoire.")
    try:
        ech = _dt.strptime(date_echeance, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Date d'echeance invalide.")

    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id, CacesObtenu.stagiaire_id == id).first()
    if not co:
        raise HTTPException(status_code=404, detail="CACES externe introuvable")

    from app.models.carte_caces import CarteCaces
    ext = db.query(CacesObtenu).filter(CacesObtenu.caces_initial_id == co.id, CacesObtenu.statut == "valide").first()
    if ext:
        raise HTTPException(status_code=409, detail="Modification impossible : un CACES valide a ete forme par extension de ce CACES. Annulez-le d'abord.")
    disp = db.query(SessionCandidat).filter(SessionCandidat.dispense_source_type == "caces", SessionCandidat.dispense_source_id == co.id).first()
    if disp:
        raise HTTPException(status_code=409, detail="Modification impossible : ce CACES fonde une dispense de theorie en cours. Retirez d'abord la dispense.")
    carte = db.query(CarteCaces).filter(CarteCaces.stagiaire_id == id, CarteCaces.famille == co.famille, CarteCaces.statut == "emise").first()
    if carte:
        raise HTTPException(status_code=409, detail="Modification impossible : une carte CACES active (n. %s) a ete emise pour cette famille. Annulez ou remplacez-la d'abord." % (carte.numero_carte or ""))

    ancienne_cat = co.categorie
    if categorie != ancienne_cat:
        conflit = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == id, CacesObtenu.session_id == co.session_id,
            CacesObtenu.categorie == categorie, CacesObtenu.id != co.id,
        ).first()
        if conflit:
            raise HTTPException(status_code=409, detail="Un CACES existe deja pour cette categorie dans les reprises.")

    origine = _date_initiale_depuis_echeance(famille, ech)
    co.famille = famille
    co.categorie = categorie
    co.date_obtention = origine
    co.date_echeance = ech
    co.organisme_externe = organisme.strip()[:200]
    co.options_obtenues = options.strip() or None

    ep = db.query(SessionEpreuve).filter(
        SessionEpreuve.stagiaire_id == id, SessionEpreuve.session_id == co.session_id,
        SessionEpreuve.categorie == ancienne_cat,
    ).first()
    if ep:
        ep.famille = famille
        ep.categorie = categorie
        ep.date = origine
        ep.options_obtenues = options.strip() or None
    db.commit()
    return {"ok": True, "message": "CACES externe modifie"}


@router.get("/{id}/caces-externe/{caces_id}/justificatif")
def lire_justificatif_caces_externe(id: int, caces_id: int, request: Request, db: Session = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    co = db.query(CacesObtenu).filter(
        CacesObtenu.id == caces_id,
        CacesObtenu.stagiaire_id == id,
    ).first()
    if not co or not co.justificatif_cle:
        raise HTTPException(status_code=404, detail="Aucun justificatif pour ce CACES externe")
    data = storage.get_fichier(co.justificatif_cle)
    nom = co.justificatif_nom or "justificatif"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{nom}"'},
    )


@router.delete("/{id}/caces-externe/{caces_id}")
def supprimer_caces_externe(id: int, caces_id: int, pin: str = "", db: Session = Depends(get_db)):
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    co = db.query(CacesObtenu).filter(
        CacesObtenu.id == caces_id,
        CacesObtenu.stagiaire_id == id,
    ).first()
    if not co:
        raise HTTPException(status_code=404, detail="CACES externe introuvable")

    # BLOCAGE : ce CACES peut servir a delivrer un autre CACES (extension),
    # fonder une dispense de theorie en cours, ou avoir ete fige dans une carte
    # emise. On verifie ces dependances AVANT tout hard delete.
    from app.models.carte_caces import CarteCaces

    ext = db.query(CacesObtenu).filter(CacesObtenu.caces_initial_id == co.id).first()
    if ext:
        raise HTTPException(
            status_code=409,
            detail="Suppression impossible : ce CACES sert de base a une extension "
                   "(%s cat. %s). Supprimez d'abord l'extension." % (
                       ext.famille or "", ext.categorie or ""),
        )

    disp = db.query(SessionCandidat).filter(
        SessionCandidat.dispense_source_type == "caces",
        SessionCandidat.dispense_source_id == co.id,
    ).first()
    if disp:
        raise HTTPException(
            status_code=409,
            detail="Suppression impossible : ce CACES fonde une dispense de theorie "
                   "pour un candidat en session. Retirez d'abord la dispense.",
        )

    carte = db.query(CarteCaces).filter(
        CarteCaces.stagiaire_id == id,
        CarteCaces.famille == co.famille,
        CarteCaces.statut == "emise",
    ).first()
    if carte:
        raise HTTPException(
            status_code=409,
            detail="Suppression impossible : une carte CACES active (n. %s) a ete emise "
                   "pour cette famille et peut inclure ce CACES. Annulez ou remplacez "
                   "d'abord la carte." % (carte.numero_carte or ""),
        )

    if co.justificatif_cle:
        try:
            storage.delete_fichier(co.justificatif_cle)
        except Exception:
            pass
    db.query(SessionEpreuve).filter(
        SessionEpreuve.session_id == co.session_id,
        SessionEpreuve.stagiaire_id == id,
        SessionEpreuve.categorie == co.categorie,
    ).delete()
    db.delete(co)
    db.commit()
    return {"message": "CACES externe supprime"}