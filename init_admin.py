from app.database import SessionLocal, engine, Base
from app.models.utilisateur import Utilisateur
from passlib.context import CryptContext

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

db = SessionLocal()

# Vérifier si admin existe déjà
existing = db.query(Utilisateur).filter(Utilisateur.email == "admin@pepci.fr").first()
if existing:
    print("Admin existe deja !")
else:
    admin = Utilisateur(
        nom="CHIRON",
        prenom="Patrice",
        email="admin@pepci.fr",
        mot_de_passe=pwd_context.hash("pepci25"),
        role="admin",
        actif=True
    )
    db.add(admin)
    db.commit()
    print("Admin cree : admin@pepci.fr / pepci2025")

db.close()