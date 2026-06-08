import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.jour_test import JourTest, ResultatTheorie

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
