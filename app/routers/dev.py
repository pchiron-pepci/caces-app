import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.jour_test import JourTest, ResultatTheorie
from app.models.session_epreuve import SessionEpreuve
from app.models.session import Session as SessionModel
from app.models.caces_obtenu import CacesObtenu
from app.models.stagiaire import Stagiaire

router = APIRouter(prefix="/api/dev", tags=["Dev"])

_DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def _check_dev():
    if not _DEV_MODE:
        raise HTTPException(status_code=403, detail="Route disponible en DEV_MODE uniquement")


@router.post("/forcer-resultat-theorie/{jour_test_id}/{stagiaire_id}")
def forcer_resultat_theorie(jour_test_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    _check_dev()

    jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
    if not jour:
        raise HTTPException(status_code=404, detail="JourTest introuvable")
    if jour.type != "theorie":
        raise HTTPException(status_code=400, detail="Ce jour n'est pas un jour de théorie")

    rt = ResultatTheorie(
        jour_test_id=jour_test_id,
        session_id=jour.session_id,
        stagiaire_id=stagiaire_id,
        grille_id=jour.grille_id,
        note_theme1=8.0,
        note_theme2=8.0,
        note_theme3=8.0,
        note_theme4=8.0,
        note_theme5=8.0,
        note_totale=40.0,
        theme1_ok=True,
        theme2_ok=True,
        theme3_ok=True,
        theme4_ok=True,
        theme5_ok=True,
        obtenue=True,
        dispense=False,
        reponses_json="{}",
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return {"ok": True, "resultat_theorie_id": rt.id, "session_id": rt.session_id}


@router.get("/debug-caces/{stagiaire_id}")
def debug_caces(stagiaire_id: int, db: DBSession = Depends(get_db)):
    """
    Trace exactement pourquoi un stagiaire génère ou non des CacesObtenu à valider.
    Retourne un rapport JSON détaillé pour chaque épreuve pratique réussie.
    """
    _check_dev()

    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    if not stagiaire:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")

    epreuves_ok = (
        db.query(SessionEpreuve)
        .filter(
            SessionEpreuve.stagiaire_id == stagiaire_id,
            SessionEpreuve.obtenue == True,
        )
        .order_by(SessionEpreuve.session_id, SessionEpreuve.categorie)
        .all()
    )

    rapport = {
        "stagiaire_id": stagiaire_id,
        "stagiaire": f"{stagiaire.nom} {stagiaire.prenom}",
        "epreuves_pratiques_reussies": len(epreuves_ok),
        "detail": [],
    }

    for ep in epreuves_ok:
        sess = db.query(SessionModel).filter(SessionModel.id == ep.session_id).first()
        item = {
            "epreuve_id": ep.id,
            "session_id": ep.session_id,
            "session_reference": sess.reference if sess else "?",
            "session_statut": sess.statut if sess else "?",
            "famille": ep.famille,
            "categorie": ep.categorie,
            "date_pratique": ep.date.isoformat() if ep.date else None,
            "options_obtenues": ep.options_obtenues,
        }

        # Étape 1 : CacesObtenu existant ?
        existing = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == stagiaire_id,
            CacesObtenu.session_id == ep.session_id,
            CacesObtenu.categorie == ep.categorie,
        ).first()
        if existing:
            item["bloque_par"] = "CacesObtenu existant"
            item["caces_obtenu_id"] = existing.id
            item["caces_obtenu_statut"] = existing.statut
            rapport["detail"].append(item)
            continue

        item["bloque_par"] = None

        # Étape 2 : théorie dans la même session
        rt_same = db.query(ResultatTheorie).filter(
            ResultatTheorie.stagiaire_id == stagiaire_id,
            ResultatTheorie.session_id == ep.session_id,
            ResultatTheorie.obtenue == True,
        ).order_by(ResultatTheorie.id.asc()).first()

        if rt_same:
            jour = db.query(JourTest).filter(JourTest.id == rt_same.jour_test_id).first()
            item["theorie"] = {
                "source": "meme_session",
                "resultat_id": rt_same.id,
                "session_id": rt_same.session_id,
                "jour_test_id": rt_same.jour_test_id,
                "date_theorie": jour.date.isoformat() if jour and jour.date else None,
            }
        else:
            # Étape 3 : post-clôture
            item["theorie_meme_session"] = "AUCUNE"

            # Lister toutes les sessions terminées de la même famille pour ce stagiaire
            sessions_terminees = (
                db.query(SessionModel)
                .join(ResultatTheorie, ResultatTheorie.session_id == SessionModel.id)
                .filter(
                    ResultatTheorie.stagiaire_id == stagiaire_id,
                    SessionModel.famille == ep.famille,
                    SessionModel.statut == "terminee",
                )
                .distinct()
                .all()
            )
            item["sessions_terminees_meme_famille"] = [
                {"session_id": s.id, "reference": s.reference, "statut": s.statut}
                for s in sessions_terminees
            ]

            rt_other = (
                db.query(ResultatTheorie)
                .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
                .filter(
                    ResultatTheorie.stagiaire_id == stagiaire_id,
                    ResultatTheorie.obtenue == True,
                    SessionModel.famille == ep.famille,
                    SessionModel.statut == "terminee",
                )
                .order_by(ResultatTheorie.id.asc())
                .first()
            )

            if rt_other:
                jour = db.query(JourTest).filter(JourTest.id == rt_other.jour_test_id).first()
                item["theorie"] = {
                    "source": "post_cloture",
                    "resultat_id": rt_other.id,
                    "session_id": rt_other.session_id,
                    "jour_test_id": rt_other.jour_test_id,
                    "date_theorie": jour.date.isoformat() if jour and jour.date else None,
                }
            else:
                item["theorie"] = None
                item["bloque_par"] = "Aucun ResultatTheorie.obtenue=True trouvé (même session ou post-clôture)"

                # Diagnostic : toutes les théories de ce stagiaire, réussies ou non
                toutes_theories = (
                    db.query(ResultatTheorie)
                    .filter(ResultatTheorie.stagiaire_id == stagiaire_id)
                    .order_by(ResultatTheorie.session_id)
                    .all()
                )
                item["toutes_theories_stagiaire"] = [
                    {
                        "id": t.id,
                        "session_id": t.session_id,
                        "obtenue": t.obtenue,
                        "note_totale": t.note_totale,
                        "dispense": t.dispense,
                    }
                    for t in toutes_theories
                ]

        rapport["detail"].append(item)

    return rapport
