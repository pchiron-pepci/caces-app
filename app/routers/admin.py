import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.categorie import Categorie, Famille
from app.models.habilitation_testeur import HabilitationTesteur
from app.models.lieu import Lieu
from app.models.lieu_habilitation import LieuHabilitation
from pydantic import BaseModel
from datetime import date
from typing import Optional, List

router = APIRouter(prefix="/admin", tags=["Administration"])

class HabilitationCreate(BaseModel):
    testeur_id: int
    famille: str
    categorie: str
    date_integration: date
    date_expiration: Optional[date] = None
    option_pe: bool = False
    option_tel: bool = False

class HabilitationUpdate(BaseModel):
    date_integration: date
    date_expiration: Optional[date] = None
    option_pe: bool = False
    option_tel: bool = False

class LieuHabilitationCreate(BaseModel):
    famille: str
    categorie: str

class LieuCreate(BaseModel):
    nom: str
    type: str = "cdt"
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    habilitations: List[LieuHabilitationCreate] = []

@router.get("/categories/{famille}")
def get_categories_famille(famille: str, db: Session = Depends(get_db)):
    f = db.query(Famille).filter(Famille.code == famille).first()
    if not f:
        raise HTTPException(status_code=404, detail="Famille non trouvee")
    cats = db.query(Categorie).filter(
        Categorie.famille_id == f.id,
        Categorie.actif == True
    ).all()
    return [{"code": c.code, "libelle": c.libelle} for c in cats]

@router.post("/categorie/{id}/activer")
def activer_categorie(id: int, db: Session = Depends(get_db)):
    c = db.query(Categorie).filter(Categorie.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie non trouvee")
    c.pepci_habilite = True
    db.commit()
    return {"message": "Categorie activee"}

@router.post("/categorie/{id}/desactiver")
def desactiver_categorie(id: int, db: Session = Depends(get_db)):
    c = db.query(Categorie).filter(Categorie.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie non trouvee")
    c.pepci_habilite = False
    db.commit()
    return {"message": "Categorie desactivee"}

@router.post("/habilitation")
def add_habilitation(data: HabilitationCreate, db: Session = Depends(get_db)):
    h = HabilitationTesteur(**data.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"message": "Habilitation ajoutee", "id": h.id}

@router.put("/habilitation/{id}")
def update_habilitation(id: int, data: HabilitationUpdate, db: Session = Depends(get_db)):
    h = db.query(HabilitationTesteur).filter(HabilitationTesteur.id == id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habilitation non trouvee")
    h.date_integration = data.date_integration
    h.date_expiration = data.date_expiration
    h.option_pe = data.option_pe
    h.option_tel = data.option_tel
    db.commit()
    return {"message": "Habilitation mise a jour"}

@router.post("/habilitation/{id}/activer")
def activer_habilitation(id: int, db: Session = Depends(get_db)):
    h = db.query(HabilitationTesteur).filter(HabilitationTesteur.id == id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habilitation non trouvee")
    h.actif = True
    db.commit()
    return {"message": "Habilitation activee"}

@router.post("/habilitation/{id}/desactiver")
def desactiver_habilitation(id: int, db: Session = Depends(get_db)):
    h = db.query(HabilitationTesteur).filter(HabilitationTesteur.id == id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habilitation non trouvee")
    h.actif = False
    db.commit()
    return {"message": "Habilitation desactivee"}

@router.delete("/habilitation/{id}")
def delete_habilitation(id: int, pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    h = db.query(HabilitationTesteur).filter(HabilitationTesteur.id == id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habilitation non trouvee")
    db.delete(h)
    db.commit()
    return {"message": "Habilitation supprimee"}

@router.get("/lieu/{id}/habilitations")
def get_lieu_habilitations(id: int, db: Session = Depends(get_db)):
    habs = db.query(LieuHabilitation).filter(
        LieuHabilitation.lieu_id == id,
        LieuHabilitation.actif == True
    ).all()
    return [{"famille": h.famille, "categorie": h.categorie} for h in habs]

@router.post("/lieu")
def create_lieu(data: LieuCreate, db: Session = Depends(get_db)):
    lieu_data = data.model_dump(exclude={"habilitations"})
    l = Lieu(**lieu_data)
    db.add(l)
    db.flush()
    for h in data.habilitations:
        lh = LieuHabilitation(lieu_id=l.id, famille=h.famille, categorie=h.categorie)
        db.add(lh)
    db.commit()
    db.refresh(l)
    return {"message": "Lieu cree", "id": l.id}

@router.put("/lieu/{id}")
def update_lieu(id: int, data: LieuCreate, db: Session = Depends(get_db)):
    l = db.query(Lieu).filter(Lieu.id == id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lieu non trouve")
    lieu_data = data.model_dump(exclude={"habilitations"})
    for key, value in lieu_data.items():
        setattr(l, key, value)
    db.query(LieuHabilitation).filter(LieuHabilitation.lieu_id == id).delete()
    for h in data.habilitations:
        lh = LieuHabilitation(lieu_id=id, famille=h.famille, categorie=h.categorie)
        db.add(lh)
    db.commit()
    return {"message": "Lieu mis a jour"}

@router.post("/lieu/{id}/activer")
def activer_lieu(id: int, db: Session = Depends(get_db)):
    l = db.query(Lieu).filter(Lieu.id == id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lieu non trouve")
    l.actif = True
    db.commit()
    return {"message": "Lieu active"}

@router.post("/lieu/{id}/desactiver")
def desactiver_lieu(id: int, db: Session = Depends(get_db)):
    l = db.query(Lieu).filter(Lieu.id == id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lieu non trouve")
    l.actif = False
    db.commit()
    return {"message": "Lieu desactive"}


# --- Config organisme ---

class ConfigOrganismeUpdate(BaseModel):
    nom_organisme: Optional[str] = None
    audit_interne_date: Optional[date] = None
    audit_externe_date: Optional[date] = None
    revue_direction_date: Optional[date] = None
    pin_formateur: Optional[str] = None
    prochain_numero_caces: Optional[int] = None

@router.get("/config-organisme")
def get_config_organisme(db: Session = Depends(get_db)):
    from app.models.config_organisme import ConfigOrganisme
    config = db.query(ConfigOrganisme).first()
    if not config:
        return {"nom_organisme": "", "logo_data_uri": ""}
    logo_data_uri = ""
    if config.logo_base64 and config.logo_nom:
        ext = config.logo_nom.rsplit('.', 1)[-1].lower()
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
        logo_data_uri = f"data:{mime};base64,{config.logo_base64}"
    return {
        "nom_organisme": config.nom_organisme or "",
        "logo_data_uri": logo_data_uri,
        "audit_interne_date": config.audit_interne_date.isoformat() if config.audit_interne_date else "",
        "audit_externe_date": config.audit_externe_date.isoformat() if config.audit_externe_date else "",
        "revue_direction_date": config.revue_direction_date.isoformat() if config.revue_direction_date else "",
        "pin_formateur": config.pin_formateur or "1234",
        "prochain_numero_caces": config.prochain_numero_caces if config.prochain_numero_caces is not None else 1,
    }

@router.put("/config-organisme")
def update_config_organisme(pin: str, data: ConfigOrganismeUpdate, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.config_organisme import ConfigOrganisme
    config = db.query(ConfigOrganisme).first()
    if not config:
        config = ConfigOrganisme()
        db.add(config)
    config.nom_organisme = data.nom_organisme
    config.audit_interne_date = data.audit_interne_date
    config.audit_externe_date = data.audit_externe_date
    config.revue_direction_date = data.revue_direction_date
    if data.pin_formateur is not None:
        config.pin_formateur = data.pin_formateur or "1234"
    if data.prochain_numero_caces is not None:
        config.prochain_numero_caces = data.prochain_numero_caces
    db.commit()
    return {"message": "Configuration mise à jour"}

@router.post("/config-organisme/logo")
async def upload_logo_organisme(pin: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
        raise HTTPException(status_code=400, detail="Format image invalide (png, jpg, gif, webp)")
    contents = await file.read()
    logo_b64 = base64.b64encode(contents).decode()
    from app.models.config_organisme import ConfigOrganisme
    config = db.query(ConfigOrganisme).first()
    if not config:
        config = ConfigOrganisme()
        db.add(config)
    config.logo_base64 = logo_b64
    config.logo_nom = file.filename
    db.commit()
    return {"message": "Logo mis à jour"}

@router.delete("/config-organisme/logo")
def supprimer_logo_organisme(pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.config_organisme import ConfigOrganisme
    config = db.query(ConfigOrganisme).first()
    if config:
        config.logo_base64 = None
        config.logo_nom = None
        db.commit()
    return {"message": "Logo supprimé"}


@router.post("/config/verifier-pin-formateur")
def verifier_pin_formateur(data: dict, db: Session = Depends(get_db)):
    from app.models.config_organisme import ConfigOrganisme
    config = db.query(ConfigOrganisme).first()
    pin_attendu = (config.pin_formateur if config and config.pin_formateur else "1234")
    if data.get("pin") != pin_attendu:
        raise HTTPException(status_code=403, detail="PIN formateur incorrect")
    return {"ok": True}

# --- Options catégories ---

class OptionsUpdate(BaseModel):
    codes: List[str]

@router.get("/options/{famille}/{categorie}")
def get_options_disponibles(famille: str, categorie: str, db: Session = Depends(get_db)):
    from app.models.option_categorie import OptionCategorie
    opts = db.query(OptionCategorie).filter(
        OptionCategorie.famille == famille,
        OptionCategorie.categorie == categorie
    ).all()
    return [{"code": o.code_option, "libelle": o.libelle_option} for o in opts]

@router.get("/habilitation/{hab_id}/options")
def get_options_habilitation(hab_id: int, db: Session = Depends(get_db)):
    from app.models.habilitation_option import HabilitationOption
    opts = db.query(HabilitationOption).filter(HabilitationOption.habilitation_id == hab_id).all()
    return [o.code_option for o in opts]

@router.put("/habilitation/{hab_id}/options")
def update_options_habilitation(hab_id: int, pin: str, data: OptionsUpdate, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.habilitation_option import HabilitationOption
    db.query(HabilitationOption).filter(HabilitationOption.habilitation_id == hab_id).delete()
    for code in data.codes:
        db.add(HabilitationOption(habilitation_id=hab_id, code_option=code))
    db.commit()
    return {"message": "Options mises à jour"}