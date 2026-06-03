from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil

router = APIRouter(prefix="/api/upload", tags=["Upload"])

UPLOAD_DIR = "uploads/questions"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/question-image")
async def upload_question_image(file: UploadFile = File(...)):
    # Vérifier l'extension
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise HTTPException(status_code=400, detail="Format non supporté - JPG/PNG uniquement")
    
    # Sauvegarder le fichier
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"message": "Image uploadee", "filename": file.filename, "url": f"/uploads/questions/{file.filename}"}

@router.post("/question-images")
async def upload_question_images(files: list[UploadFile] = File(...)):
    uploaded = []
    errors = []
    for file in files:
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            errors.append(f"{file.filename}: format non supporte")
            continue
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded.append(file.filename)
    return {"uploaded": uploaded, "errors": errors}

@router.post("/associer-images")
async def associer_images(db=None):
    from app.database import SessionLocal
    from app.models.grille_theorie import ReponseGrille
    db = SessionLocal()
    
    updated = 0
    for filename in os.listdir(UPLOAD_DIR):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        # Parser le nom : g1_t2_q1.jpg
        try:
            name = filename.rsplit('.', 1)[0]
            parts = name.upper().split('-')
            # Format : R482-G1-T2-Q1
            famille = parts[0]  # R482
            grille_num = int(parts[1][1:])  # G1 → 1
            theme = int(parts[2][1:])  # T2 → 2
            question = int(parts[3][1:])  # Q1 → 1
            
            from app.models.grille_theorie import GrilleTheorie
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
                    rq.image_url = f"/uploads/questions/{filename}"
                    updated += 1
        except Exception as e:
            print(f"Erreur parsing {filename}: {e}")
            continue
    
    db.commit()
    db.close()
    return {"message": f"{updated} images associees"}

@router.get("/liste-images")
def liste_images():
    if not os.path.exists(UPLOAD_DIR):
        return {"images": []}
    images = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    return {"images": sorted(images)}

@router.delete("/supprimer-image")
def supprimer_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image non trouvee")
    os.remove(file_path)
    return {"message": "Image supprimee"}