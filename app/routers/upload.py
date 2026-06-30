import os
import base64
import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response, RedirectResponse
from app.services import storage
from app.database import SessionLocal
from app.config_utils import get_pin_admin as _gpa

router = APIRouter(prefix="/api/upload", tags=["Upload"])

def _get_pin_admin() -> str:
    db = SessionLocal()
    try:
        return _gpa(db)
    finally:
        db.close()

UPLOAD_DIR = "uploads/questions"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def configurer_cloudinary():
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
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    from app.models.grille_theorie import ReponseGrille, GrilleTheorie
    db = SessionLocal()
    updated = 0
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix="caces_questions/",
            max_results=500
        )
        resources = result.get("resources", [])
        for resource in resources:
            public_id = resource["public_id"]
            filename = public_id.split("/")[-1]
            url = resource["secure_url"]
            try:
                parts = filename.upper().split("_")
                famille = parts[0]
                grille_num = int(parts[1][1:])
                theme = int(parts[2][1:])
                question = int(parts[3][1:])

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
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    try:
        public_id = f"caces_questions/{filename.rsplit('.', 1)[0]}"
        cloudinary.uploader.destroy(public_id)
        return {"message": "Image supprimee"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Documents officiels (stockage base64 PostgreSQL) ---

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
                    "nom_fichier": d.nom_fichier,
                    "has_file": bool(d.contenu_pdf),
                    "date_validite": d.date_validite.strftime("%Y-%m-%d") if d.date_validite else None,
                    "numero_certificat": d.numero_certificat or ""
                }
                for d in docs
            ]
        }
    finally:
        db.close()


@router.put("/document-officiel/{type}/numero")
def enregistrer_numero_certificat(type: str, pin: str, numero_certificat: str = None):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if type != "certificat_organisme":
        raise HTTPException(status_code=400, detail="Numéro applicable au certificat organisme uniquement")
    from app.models.document_officiel import DocumentOfficiel
    db = SessionLocal()
    try:
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == type).first()
        if not doc:
            db.add(DocumentOfficiel(type=type, numero_certificat=numero_certificat))
        else:
            doc.numero_certificat = numero_certificat
        db.commit()
    finally:
        db.close()
    return {"message": "Numéro enregistré"}

@router.post("/document-officiel")
async def upload_document_officiel(type: str, pin: str, file: UploadFile = File(...), date_validite: str = None, numero_certificat: str = None):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    TYPES_VALIDES = ["certificat_organisme", "attestation_assurance", "procedure_interne"]
    if type not in TYPES_VALIDES:
        raise HTTPException(status_code=400, detail="Type de document invalide")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    contenu_b64 = base64.b64encode(contents).decode()
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
            doc.contenu_pdf = contenu_b64
            doc.nom_fichier = file.filename
            doc.date_validite = dv
            if numero_certificat is not None:
                doc.numero_certificat = numero_certificat
        else:
            db.add(DocumentOfficiel(type=type, contenu_pdf=contenu_b64, nom_fichier=file.filename, date_validite=dv, numero_certificat=numero_certificat))
        db.commit()
    finally:
        db.close()
    return {"message": "Document uploade"}


@router.get("/document-officiel/{type}/download")
def telecharger_document_officiel(type: str):
    TYPES_VALIDES = ["certificat_organisme", "attestation_assurance", "procedure_interne"]
    if type not in TYPES_VALIDES:
        raise HTTPException(status_code=400, detail="Type invalide")
    from app.models.document_officiel import DocumentOfficiel
    db = SessionLocal()
    try:
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == type).first()
        print(f"[DOC] type={type} doc={doc} contenu_pdf_len={len(doc.contenu_pdf) if doc and doc.contenu_pdf else 'NULL'}")
        if not doc or not doc.contenu_pdf:
            raise HTTPException(status_code=404, detail="Document non disponible")
        contenu = base64.b64decode(doc.contenu_pdf)
        nom = doc.nom_fichier or f"{type}.pdf"
    finally:
        db.close()
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'}
    )


@router.delete("/document-officiel/{type}")
def supprimer_document_officiel(type: str, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    TYPES_VALIDES = ["certificat_organisme", "attestation_assurance", "procedure_interne"]
    if type not in TYPES_VALIDES:
        raise HTTPException(status_code=400, detail="Type de document invalide")
    from app.models.document_officiel import DocumentOfficiel
    db = SessionLocal()
    try:
        doc = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == type).first()
        if doc:
            doc.contenu_pdf = None
            doc.nom_fichier = None
            doc.date_validite = None
            db.commit()
    finally:
        db.close()
    return {"message": "Document supprime"}


# --- Carte CACES® testeur (stockage base64 PostgreSQL) ---

@router.post("/carte-testeur/{testeur_id}")
async def upload_carte_testeur(testeur_id: int, pin: str, file: UploadFile = File(...)):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    cle = storage.construire_cle("testeurs/carte", file.filename)
    storage.upload_fichier(contents, cle, "application/pdf")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        if t.carte_cle:
            try: storage.delete_fichier(t.carte_cle)
            except Exception: pass
        t.carte_cle = cle
        t.carte_nom_fichier = file.filename
        db.commit()
    finally:
        db.close()
    return {"message": "Carte uploadée"}


@router.get("/carte-testeur/{testeur_id}/download")
def telecharger_carte_testeur(testeur_id: int):
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.carte_cle:
            raise HTTPException(status_code=404, detail="Carte non disponible")
        nom = f"{t.nom}_{t.prenom}_{t.carte_nom_fichier or 'carte.pdf'}"
        url = storage.generer_url_presignee(t.carte_cle, nom_telechargement=nom, inline=False)
    finally:
        db.close()
    return RedirectResponse(url)


@router.delete("/carte-testeur/{testeur_id}")
def supprimer_carte_testeur(testeur_id: int, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            if t.carte_cle:
                try: storage.delete_fichier(t.carte_cle)
                except Exception: pass
            t.carte_cle = None
            t.carte_nom_fichier = None
            db.commit()
    finally:
        db.close()
    return {"message": "Carte supprimée"}


# --- CarteTesteur multi-cartes (stockage base64 PostgreSQL) ---

FAMILLES_VALIDES = ["R482", "R483", "R484", "R485", "R486", "R487", "R489", "R490"]

@router.get("/cartes-testeur/{testeur_id}")
def liste_cartes_testeur(testeur_id: int):
    from app.models.carte_testeur import CarteTesteur
    db = SessionLocal()
    try:
        cartes = db.query(CarteTesteur).filter(
            CarteTesteur.testeur_id == testeur_id,
            CarteTesteur.actif == True
        ).order_by(CarteTesteur.famille).all()
        return [
            {"id": c.id, "famille": c.famille, "nom_fichier": c.nom_fichier,
             "date_upload": c.date_upload.strftime("%d/%m/%Y") if c.date_upload else None}
            for c in cartes
        ]
    finally:
        db.close()


@router.post("/cartes-testeur/{testeur_id}")
async def upload_nouvelle_carte_testeur(testeur_id: int, pin: str, famille: str, file: UploadFile = File(...)):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if famille not in FAMILLES_VALIDES:
        raise HTTPException(status_code=400, detail="Famille invalide")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    cle = storage.construire_cle("testeurs/cartes", file.filename)
    storage.upload_fichier(contents, cle, "application/pdf")
    from app.models.carte_testeur import CarteTesteur
    from datetime import datetime
    db = SessionLocal()
    try:
        carte = CarteTesteur(
            testeur_id=testeur_id,
            famille=famille,
            nom_fichier=file.filename,
            cle=cle,
            date_upload=datetime.utcnow()
        )
        db.add(carte)
        db.commit()
        db.refresh(carte)
        return {"message": "Carte uploadée", "id": carte.id}
    finally:
        db.close()


@router.get("/carte/{carte_id}/download")
def telecharger_carte(carte_id: int):
    from app.models.carte_testeur import CarteTesteur
    db = SessionLocal()
    try:
        c = db.query(CarteTesteur).filter(CarteTesteur.id == carte_id).first()
        if not c or not c.cle:
            raise HTTPException(status_code=404, detail="Carte non disponible")
        nom = c.nom_fichier
        url = storage.generer_url_presignee(c.cle, nom_telechargement=nom, inline=False)
    finally:
        db.close()
    return RedirectResponse(url)


@router.delete("/carte/{carte_id}")
def supprimer_carte(carte_id: int, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.carte_testeur import CarteTesteur
    db = SessionLocal()
    try:
        c = db.query(CarteTesteur).filter(CarteTesteur.id == carte_id).first()
        if c:
            if c.cle:
                try: storage.delete_fichier(c.cle)
                except Exception: pass
            c.actif = False
            db.commit()
    finally:
        db.close()
    return {"message": "Carte supprimée"}


# --- Attestation prévention testeur (stockage base64 PostgreSQL) ---

@router.post("/attestation-prevention/{testeur_id}")
async def upload_attestation_prevention(testeur_id: int, pin: str, date_attestation: str = None, file: UploadFile = File(...)):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    cle = storage.construire_cle("testeurs/attestation", file.filename)
    storage.upload_fichier(contents, cle, "application/pdf")
    from app.models.testeur import Testeur
    from datetime import datetime
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        if t.attestation_prevention_cle:
            try: storage.delete_fichier(t.attestation_prevention_cle)
            except Exception: pass
        t.attestation_prevention_cle = cle
        t.attestation_prevention_nom = file.filename
        if date_attestation:
            try:
                t.attestation_prevention_date = datetime.strptime(date_attestation, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.commit()
    finally:
        db.close()
    return {"message": "Attestation uploadée"}


@router.get("/attestation-prevention/{testeur_id}/download")
def telecharger_attestation_prevention(testeur_id: int):
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.attestation_prevention_cle:
            raise HTTPException(status_code=404, detail="Attestation non disponible")
        nom = f"{t.nom}_{t.prenom}_{t.attestation_prevention_nom or 'attestation.pdf'}"
        url = storage.generer_url_presignee(t.attestation_prevention_cle, nom_telechargement=nom, inline=False)
    finally:
        db.close()
    return RedirectResponse(url)


@router.delete("/attestation-prevention/{testeur_id}")
def supprimer_attestation_prevention(testeur_id: int, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            if t.attestation_prevention_cle:
                try: storage.delete_fichier(t.attestation_prevention_cle)
                except Exception: pass
            t.attestation_prevention_cle = None
            t.attestation_prevention_nom = None
            t.attestation_prevention_date = None
            db.commit()
    finally:
        db.close()
    return {"message": "Attestation supprimée"}


# --- Visite médicale testeur (stockage base64 PostgreSQL) ---

@router.post("/visite-medicale/{testeur_id}")
async def upload_visite_medicale(testeur_id: int, pin: str, date_visite: str = None, file: UploadFile = File(...)):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    cle = storage.construire_cle("testeurs/visite", file.filename)
    storage.upload_fichier(contents, cle, "application/pdf")
    from app.models.testeur import Testeur
    from datetime import datetime, date as date_type
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        if t.visite_medicale_cle:
            try: storage.delete_fichier(t.visite_medicale_cle)
            except Exception: pass
        t.visite_medicale_cle = cle
        t.visite_medicale_nom = file.filename
        if date_visite:
            try:
                t.visite_medicale_date = datetime.strptime(date_visite, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.commit()
    finally:
        db.close()
    return {"message": "Visite médicale uploadée"}


@router.get("/visite-medicale/{testeur_id}/download")
def telecharger_visite_medicale(testeur_id: int):
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.visite_medicale_cle:
            raise HTTPException(status_code=404, detail="Visite non disponible")
        nom = f"{t.nom}_{t.prenom}_{t.visite_medicale_nom or 'visite.pdf'}"
        url = storage.generer_url_presignee(t.visite_medicale_cle, nom_telechargement=nom, inline=False)
    finally:
        db.close()
    return RedirectResponse(url)


@router.delete("/visite-medicale/{testeur_id}")
def supprimer_visite_medicale(testeur_id: int, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            if t.visite_medicale_cle:
                try: storage.delete_fichier(t.visite_medicale_cle)
                except Exception: pass
            t.visite_medicale_cle = None
            t.visite_medicale_nom = None
            db.commit()
    finally:
        db.close()
    return {"message": "Visite supprimée"}


# --- Évaluation testeur (stockage base64 PostgreSQL) ---

@router.post("/evaluation/{testeur_id}")
async def upload_evaluation(testeur_id: int, pin: str, date_evaluation: str = None, file: UploadFile = File(...)):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    cle = storage.construire_cle("testeurs/evaluation", file.filename)
    storage.upload_fichier(contents, cle, "application/pdf")
    from app.models.testeur import Testeur
    from datetime import datetime
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        if t.evaluation_cle:
            try: storage.delete_fichier(t.evaluation_cle)
            except Exception: pass
        t.evaluation_cle = cle
        t.evaluation_nom = file.filename
        if date_evaluation:
            try:
                t.evaluation_date = datetime.strptime(date_evaluation, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.commit()
    finally:
        db.close()
    return {"message": "Évaluation uploadée"}


@router.get("/evaluation/{testeur_id}/download")
def telecharger_evaluation(testeur_id: int):
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.evaluation_cle:
            raise HTTPException(status_code=404, detail="Évaluation non disponible")
        nom = f"{t.nom}_{t.prenom}_{t.evaluation_nom or 'evaluation.pdf'}"
        url = storage.generer_url_presignee(t.evaluation_cle, nom_telechargement=nom, inline=False)
    finally:
        db.close()
    return RedirectResponse(url)


@router.delete("/evaluation/{testeur_id}")
def supprimer_evaluation(testeur_id: int, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            if t.evaluation_cle:
                try: storage.delete_fichier(t.evaluation_cle)
                except Exception: pass
            t.evaluation_cle = None
            t.evaluation_nom = None
            t.evaluation_date = None
            db.commit()
    finally:
        db.close()
    return {"message": "Évaluation supprimée"}


# --- Autorisation de conduite testeur (stockage base64 PostgreSQL) ---

@router.post("/autorisation-conduite/{testeur_id}")
async def upload_autorisation_conduite(testeur_id: int, pin: str, file: UploadFile = File(...)):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Format PDF uniquement")
    contents = await file.read()
    cle = storage.construire_cle("testeurs/autorisation", file.filename)
    storage.upload_fichier(contents, cle, "application/pdf")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Testeur non trouvé")
        if t.autorisation_conduite_cle:
            try: storage.delete_fichier(t.autorisation_conduite_cle)
            except Exception: pass
        t.autorisation_conduite_cle = cle
        t.autorisation_conduite_nom = file.filename
        db.commit()
    finally:
        db.close()
    return {"message": "Autorisation de conduite uploadée"}


@router.get("/autorisation-conduite/{testeur_id}/download")
def telecharger_autorisation_conduite(testeur_id: int):
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if not t or not t.autorisation_conduite_cle:
            raise HTTPException(status_code=404, detail="Autorisation non disponible")
        nom = f"{t.nom}_{t.prenom}_{t.autorisation_conduite_nom or 'autorisation.pdf'}"
        url = storage.generer_url_presignee(t.autorisation_conduite_cle, nom_telechargement=nom, inline=False)
    finally:
        db.close()
    return RedirectResponse(url)


@router.delete("/autorisation-conduite/{testeur_id}")
def supprimer_autorisation_conduite(testeur_id: int, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    from app.models.testeur import Testeur
    db = SessionLocal()
    try:
        t = db.query(Testeur).filter(Testeur.id == testeur_id).first()
        if t:
            if t.autorisation_conduite_cle:
                try: storage.delete_fichier(t.autorisation_conduite_cle)
                except Exception: pass
            t.autorisation_conduite_cle = None
            t.autorisation_conduite_nom = None
            db.commit()
    finally:
        db.close()
    return {"message": "Autorisation supprimée"}


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


# --- Audio questions (MP3 Cloudinary, resource_type="video") ---

@router.post("/question-audio")
async def upload_question_audio(files: list[UploadFile] = File(...)):
    configurer_cloudinary()
    uploaded = []
    errors = []
    for file in files:
        if not file.filename.lower().endswith(".mp3"):
            errors.append(f"{file.filename}: format non supporte (mp3 attendu)")
            continue
        try:
            contents = await file.read()
            public_id = f"caces_questions/audio/{file.filename.rsplit('.', 1)[0]}"
            result = cloudinary.uploader.upload(
                contents,
                public_id=public_id,
                overwrite=True,
                resource_type="video"
            )
            uploaded.append({"filename": file.filename, "url": result["secure_url"]})
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    return {"uploaded": [u["filename"] for u in uploaded], "errors": errors}

@router.post("/associer-audios")
async def associer_audios(pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    from app.models.grille_theorie import ReponseGrille, GrilleTheorie
    db = SessionLocal()
    updated = 0
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix="caces_questions/audio/",
            max_results=500,
            resource_type="video"
        )
        for resource in result.get("resources", []):
            public_id = resource["public_id"]
            filename = public_id.split("/")[-1]
            url = resource["secure_url"]
            try:
                parts = filename.upper().split("_")
                famille = parts[0]
                grille_num = int(parts[1][1:])
                theme = int(parts[2][1:])
                question = int(parts[3][1:])
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
                        rq.audio_url = url
                        updated += 1
            except Exception as e:
                print(f"Erreur parsing audio {filename}: {e}")
                continue
        db.commit()
        from app.models.association_audio_log import AssociationAudioLog
        from datetime import datetime
        db.add(AssociationAudioLog(date_association=datetime.utcnow(), nb_audios=updated))
        db.commit()
    finally:
        db.close()
    return {"message": f"{updated} audios associes"}

@router.get("/derniere-association-audio")
def derniere_association_audio():
    configurer_cloudinary()
    from app.models.association_audio_log import AssociationAudioLog
    db = SessionLocal()
    try:
        log = db.query(AssociationAudioLog).order_by(AssociationAudioLog.date_association.desc()).first()
        date_str = log.date_association.strftime("%d/%m/%Y %H:%M") if log else None
        nb_audios = log.nb_audios if log else 0
    finally:
        db.close()
    total_cloudinary = 0
    try:
        result = cloudinary.api.resources(
            type="upload", prefix="caces_questions/audio/",
            max_results=500, resource_type="video"
        )
        total_cloudinary = len(result.get("resources", []))
    except Exception:
        pass
    return {"date": date_str, "nb_audios": nb_audios, "total_cloudinary": total_cloudinary}

@router.delete("/supprimer-audio")
async def supprimer_audio(filename: str, pin: str):
    if pin != _get_pin_admin():
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    configurer_cloudinary()
    try:
        public_id = f"caces_questions/audio/{filename.rsplit('.', 1)[0]}"
        cloudinary.uploader.destroy(public_id, resource_type="video")
        return {"message": "Audio supprime"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/liste-audios")
def liste_audios():
    configurer_cloudinary()
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix="caces_questions/audio/",
            max_results=500,
            resource_type="video"
        )
        audios = []
        for r in result.get("resources", []):
            filename = r["public_id"].split("/")[-1]
            audios.append({"filename": filename, "url": r["secure_url"]})
        return {"audios": audios}
    except Exception as e:
        return {"audios": [], "error": str(e)}
