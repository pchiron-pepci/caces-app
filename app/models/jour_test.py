from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Text, Float
from app.database import Base

class JourTest(Base):
    __tablename__ = "jours_test"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(10), nullable=False)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=True)
    grille_id = Column(Integer, ForeignKey("grilles_theorie.id"), nullable=True)
    tirage_themes_json = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    note_privee = Column(Text, nullable=True)
    note_privee_auteur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    testeurs_sup = Column(Text, nullable=True)
    actif = Column(Boolean, default=True)

class JourTestCandidat(Base):
    __tablename__ = "jour_test_candidats"

    id = Column(Integer, primary_key=True, index=True)
    jour_test_id = Column(Integer, ForeignKey("jours_test.id"), nullable=False)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    categories = Column(String(100), nullable=True)
    actif = Column(Boolean, default=True)
    identite_verifiee = Column(Boolean, default=False)
    options_planifiees = Column(Text, nullable=True)

class ResultatTheorie(Base):
    __tablename__ = "resultats_theorie"

    id = Column(Integer, primary_key=True, index=True)
    jour_test_id = Column(Integer, ForeignKey("jours_test.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    grille_id = Column(Integer, ForeignKey("grilles_theorie.id"), nullable=True)
    reponses_json = Column(Text, nullable=True)
    note_theme1 = Column(Float, nullable=True)
    note_theme2 = Column(Float, nullable=True)
    note_theme3 = Column(Float, nullable=True)
    note_theme4 = Column(Float, nullable=True)
    note_theme5 = Column(Float, nullable=True)
    note_totale = Column(Float, nullable=True)
    theme1_ok = Column(Boolean, nullable=True)
    theme2_ok = Column(Boolean, nullable=True)
    theme3_ok = Column(Boolean, nullable=True)
    theme4_ok = Column(Boolean, nullable=True)
    theme5_ok = Column(Boolean, nullable=True)
    obtenue = Column(Boolean, nullable=True)
    dispense = Column(Boolean, default=False)
    bloque = Column(Boolean, default=False, nullable=False)
    mode = Column(String(12), nullable=False, default="numerique")
    justificatif_cle = Column(String(500), nullable=True)
    justificatif_nom = Column(String(255), nullable=True)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=True)