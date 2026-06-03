from app.database import SessionLocal
from app.models.grille_theorie import UtilisationGrille

db = SessionLocal()
nb = db.query(UtilisationGrille).count()
db.query(UtilisationGrille).delete()
db.commit()
db.close()
print(f"{nb} utilisations supprimees - compteurs remis a zero !")