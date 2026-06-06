import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.database import SessionLocal

router = APIRouter(prefix="/api/upload", tags=["Upload"])

UPLOAD_DIR = "uploads/questions"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def configurer_cloudinary():
    """Configure Cloudinary avec les variables d'environnement.
    On appelle cette fonction à chaque requête pour être sûr
    que les variables sont bien chargées."""
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )

@router.post("/question-images")
async def upload_question_images(files: list[UploadFile] = File(...)):
    configurer_cloudinary()
    uploaded = []
    errors = []
    for file in files:
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            errors.append(f"{file.filename}: format non supporte")
            continue
        try:
            contents = await file.read()
            # Le public_id est le nom du fichier sans extension
            # ex: R482-G1-T2-Q1
            public_id = f"caces_questions/{file.filename.rsplit('.', 1)[0]}"
            result = cloudinary.uploader.upload(
                contents,
                public_id=public_id,
                overwrite=True,
                resource_type="image"
            )
            uploaded.append({
                "filename": file.filename,
                "url": result["secure_url"]
            })
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    return {"uploaded": [u["filename"] for u in uploaded], "errors": errors}

@router.post("/associer-images")
async def associer_images(pin: str):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    from app.models.grille_theorie import ReponseGrille, GrilleTheorie
    db = SessionLocal()
    updated = 0
    try:
        # On liste toutes les images stockées sur Cloudinary
        # dans le dossier caces_questions
        result = cloudinary.api.resources(
            type="upload",
            prefix="caces_questions/",
            max_results=500
        )
        resources = result.get("resources", [])
        for resource in resources:
            # Le public_id ressemble à "caces_questions/R482-G1-T2-Q1"
            # On extrait juste le nom du fichier
            public_id = resource["public_id"]
            filename = public_id.split("/")[-1]  # R482-G1-T2-Q1
            url = resource["secure_url"]
            try:
                parts = filename.upper().split("-")
                famille = parts[0]              # R482
                grille_num = int(parts[1][1:])  # G1 → 1
                theme = int(parts[2][1:])       # T2 → 2
                question = int(parts[3][1:])    # Q1 → 1

                grille = db.query(GrilleTheorie).filter(
                    GrilleTheorie.numero == grille_num,
                    GrilleTheorie.famille == famille
                ).first()

                if grille:
                    rq = db.query(ReponseGrille).filter(
                        ReponseGrille.grille_id == grille.id,
                        ReponseGrille.theme == theme,
                        ReponseGrille.numero_question == question
                    ).first()
                    if rq:
                        rq.image_url = url
                        updated += 1
            except Exception as e:
                print(f"Erreur parsing {filename}: {e}")
                continue
        db.commit()
        from app.models.association_log import AssociationLog
        from datetime import datetime
        db.add(AssociationLog(date_association=datetime.utcnow(), nb_images=updated))
        db.commit()
    finally:
        db.close()
    return {"message": f"{updated} images associees"}


@router.get("/derniere-association")
def derniere_association():
    from app.models.association_log import AssociationLog
    db = SessionLocal()
    try:
        try:
            log = db.query(AssociationLog).order_by(AssociationLog.date_association.desc()).first()
        except Exception:
            log = None
        try:
            configurer_cloudinary()
            result = cloudinary.api.resources(
                type="upload",
                prefix="caces_questions/",
                max_results=500
            )
            total_cloudinary = len(result.get("resources", []))
        except Exception:
            total_cloudinary = None
        if not log:
            return {"date": None, "nb_images": None, "total_cloudinary": total_cloudinary}
        return {
            "date": log.date_association.strftime("%d/%m/%Y %H:%M"),
            "nb_images": log.nb_images,
            "total_cloudinary": total_cloudinary
        }
    finally:
        db.close()

@router.delete("/supprimer-image")
async def supprimer_image(filename: str, pin: str):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    try:
        # On supprime l'image de Cloudinary via son public_id
        public_id = f"caces_questions/{filename.rsplit('.', 1)[0]}"
        cloudinary.uploader.destroy(public_id)
        return {"message": "Image supprimee"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents-officiels")
def get_documents_officiels():
    from app.models.document_officiel import DocumentOfficiel
    db = SessionLocal()
    try:
        docs = db.query(DocumentOfficiel).all()
        return {
            "documents": [
                {
                    "type": d.type,
                    "url": d.url,
                    "nom_fichier": d.nom_fichier,
                    "date_validite": d.date_validite.strftime("%Y-%m-%d") if d.date_validite else None
                }
                for d in docs
            ]
        }
    finally:
        db.close()


@router.post("/document-officiel")
async def upload_document_officiel(type: str, pin: str, file: UploadFile = File(...), date_validite: str = None):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    TYPES_VALIDES = ["certificat_organisme", "attestation_assurance", "procedure_interne"]
    if type not in TYPES_VALIDES:
        raise HTTPException(status_code=400, detail="Type de document invalide")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    configurer_cloudinary()
    contents = await file.read()
    public_id = f"document_{type}"
    result = cloudinary.uploader.upload(
        contents,
        public_id=public_id,
        resource_type="raw",
        overwrite=True
    )
    url = result["secure_url"]
    from app.models.document_officiel import DocumentOfficiel
    from datetime import datetime
    db = SessionLocal()
    try:
        dv = None
        if date_validite:
            try:
                dv = datetime.strptime(date_validite, "%Y-%m-%d")
            except ValueError:
                pass
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == type).first()
        if doc:
            doc.url = url
            doc.nom_fichier = file.filename
            doc.date_validite = dv
        else:
            db.add(DocumentOfficiel(type=type, url=url, nom_fichier=file.filename, date_validite=dv))
        db.commit()
    finally:
        db.close()
    return {"message": "Document uploade", "url": url}


@router.get("/document-officiel/{type}/download")
def telecharger_document_officiel(type: str):
    TYPES_VALIDES = ["certificat_organisme", "attestation_assurance", "procedure_interne"]
    if type not in TYPES_VALIDES:
        raise HTTPException(status_code=400, detail="Type invalide")
    from app.models.document_officiel import DocumentOfficiel
    from fastapi.responses import RedirectResponse
    db = SessionLocal()
    try:
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == type).first()
        if not doc or not doc.url:
            raise HTTPException(status_code=404, detail="Document non disponible")
        doc_url = doc.url
    finally:
        db.close()
    return RedirectResponse(url=doc_url)


@router.delete("/document-officiel/{type}")
def supprimer_document_officiel(type: str, pin: str):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    TYPES_VALIDES = ["certificat_organisme", "attestation_assurance", "procedure_interne"]
    if type not in TYPES_VALIDES:
        raise HTTPException(status_code=400, detail="Type de document invalide")
    configurer_cloudinary()
    try:
        cloudinary.uploader.destroy(f"document_{type}", resource_type="raw")
    except Exception:
        pass
    from app.models.document_officiel import DocumentOfficiel
    db = SessionLocal()
    try:
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == type).first()
        if doc:
            doc.url = None
            doc.nom_fichier = None
            doc.date_validite = None
            db.commit()
    finally:
        db.close()
    return {"message": "Document supprime"}


def _extraire_public_id(url: str) -> str | None:
    import re
    m = re.search(r'/raw/upload/(?:v\d+/)?(.+)$', url)
    return m.group(1) if m else None


@router.post("/carte-testeur/{testeur_id}")
async def upload_carte_testeur(testeur_id: int, pin: str, file: UploadFile = File(...)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    configurer_cloudinary()
    contents = await file.read()
    public_id = f"testeur_{testeur_id}_carte"
    try:
        result = cloudinary.uploader.upload(
            contents,
            public_id=public_id,
            resource_type="raw",
            overwrite=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Cloudinary upload : {e}")
    url = result["secure_url"]
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        t.carte_url = url
        t.carte_nom_fichier = file.filename
        db.commit()
    finally:
        db.close()
    return {"message": "Carte uploadée", "url": url}


@router.delete("/carte-testeur/{testeur_id}")
def supprimer_carte_testeur(testeur_id: int, pin: str):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    try:
        cloudinary.uploader.destroy(f"testeur_{testeur_id}_carte", resource_type="raw")
    except Exception:
        pass
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            t.carte_url = None
            t.carte_nom_fichier = None
            db.commit()
    finally:
        db.close()
    return {"message": "Carte supprimée"}


@router.get("/carte-testeur/{testeur_id}/download")
def telecharger_carte_testeur(testeur_id: int):
    from app.models.testeur import Testeur
    from fastapi.responses import Response
    import requests as req
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.carte_url:
            raise HTTPException(status_code=404, detail="Carte non disponible")
        carte_url = t.carte_url
        nom_fichier = f"{t.nom}_{t.prenom}_{t.carte_nom_fichier or 'carte.pdf'}"
    finally:
        db.close()
    r = req.get(carte_url, timeout=10)
    r.raise_for_status()
    return Response(
        content=r.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'}
    )


@router.post("/attestation-prevention/{testeur_id}")
async def upload_attestation_prevention(testeur_id: int, pin: str, date_attestation: str = None, file: UploadFile = File(...)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    configurer_cloudinary()
    contents = await file.read()
    public_id = f"testeur_{testeur_id}_prevention"
    try:
        result = cloudinary.uploader.upload(
            contents,
            public_id=public_id,
            resource_type="raw",
            overwrite=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Cloudinary upload : {e}")
    url = result["secure_url"]
    from app.models.testeur import Testeur
    from datetime import datetime
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        t.attestation_prevention_url = url
        t.attestation_prevention_nom = file.filename
        if date_attestation:
            try:
                t.attestation_prevention_date = datetime.strptime(date_attestation, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.commit()
    finally:
        db.close()
    return {"message": "Attestation uploadée", "url": url}


@router.get("/attestation-prevention/{testeur_id}/download")
def telecharger_attestation_prevention(testeur_id: int):
    from app.models.testeur import Testeur
    from fastapi.responses import Response
    import requests as req
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.attestation_prevention_url:
            raise HTTPException(status_code=404, detail="Attestation non disponible")
        url = t.attestation_prevention_url
        nom_fichier = f"{t.nom}_{t.prenom}_{t.attestation_prevention_nom or 'attestation.pdf'}"
    finally:
        db.close()
    r = req.get(url, timeout=10)
    r.raise_for_status()
    return Response(
        content=r.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'}
    )


@router.delete("/attestation-prevention/{testeur_id}")
def supprimer_attestation_prevention(testeur_id: int, pin: str):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    try:
        cloudinary.uploader.destroy(f"testeur_{testeur_id}_prevention", resource_type="raw")
    except Exception:
        pass
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            t.attestation_prevention_url = None
            t.attestation_prevention_nom = None
            t.attestation_prevention_date = None
            db.commit()
    finally:
        db.close()
    return {"message": "Attestation supprimée"}


@router.get("/liste-images")
def liste_images():
    configurer_cloudinary()
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix="caces_questions/",
            max_results=500
        )
        images = []
        for r in result.get("resources", []):
            filename = r["public_id"].split("/")[-1]
            images.append({
                "filename": filename,
                "url": r["secure_url"]
            })
        return {"images": sorted(images, key=lambda x: x["filename"])}
    except Exception as e:
        return {"images": [], "error": str(e)}