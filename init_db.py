from app.database import engine, Base
import app.models.stagiaire
import app.models.testeur
import app.models.lieu
import app.models.session
import app.models.categorie
import app.models.habilitation_testeur
import app.models.lieu_habilitation
import app.models.session_candidat
import app.models.session_epreuve
import app.models.equipement
import app.models.jour_test
import app.models.grille_theorie

Base.metadata.create_all(bind=engine)
print("Tables creees !")