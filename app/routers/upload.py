import os
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.database import SessionLocal

router = APIRouter(prefix="/api/upload", tags=["Upload"])

# Configuration Cloudinary depuis les variables d'environnement
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

UPLOAD_DIR = "uploads/questions"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/question-images")
async def upload_question_images(files: list[UploadFile] = File(...)):
    uploaded = []
    errors = []
    for file in files:
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            errors.append(f"{file.filename}: format non supporte")
            continue
        try:
            # Upload vers Cloudinary
            contents = await file.read()
            # Nom public sans extension pour Cloudinary
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
async def associer_images():
    from app.models.grille_theorie import ReponseGrille, GrilleTheorie
    import cloudinary.api
    db = SessionLocal()
    updated = 0
    try:
        # Lister toutes les images dans le dossier caces_questions sur Cloudinary
        result = cloudinary.api.resources(
            type="upload",
            prefix="caces_questions/",
            max_results=500
        )
        resources = result.get("resources", [])
        for resource in resources:
            # Extraire le nom du fichier depuis le public_id
            # ex: caces_questions/R482-G1-T2-Q1
            public_id = resource["public_id"]
            filename = public_id.split("/")[-1]  # R482-G1-T2-Q1
            url = resource["secure_url"]
            try:
                parts = filename.upper().split("-")
                famille = parts[0]       # R482
                grille_num = int(parts[1][1:])  # G1 → 1
                theme = int(parts[2][1:])        # T2 → 2
                question = int(parts[3][1:])     # Q1 → 1

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
    finally:
        db.close()
    return {"message": f"{updated} images associees"}

@router.delete("/supprimer-image")
async def supprimer_image(filename: str):
    try:
        # Supprimer depuis Cloudinary
        public_id = f"caces_questions/{filename.rsplit('.', 1)[0]}"
        cloudinary.uploader.destroy(public_id)
        return {"message": "Image supprimee"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/liste-images")
def liste_images():
    try:
        import cloudinary.api
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