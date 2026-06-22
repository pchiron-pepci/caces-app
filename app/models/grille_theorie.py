from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Text
from app.database import Base

class GrilleTheorie(Base):
    __tablename__ = "grilles_theorie"

    id = Column(Integer, primary_key=True, index=True)
    famille = Column(String(10), nullable=False)
    numero = Column(Integer, nullable=False)
    annee = Column(Integer, default=2024)
    actif = Column(Boolean, default=True)

class ReponseGrille(Base):
    __tablename__ = "reponses_grilles"

    id = Column(Integer, primary_key=True, index=True)
    grille_id = Column(Integer, ForeignKey("grilles_theorie.id"), nullable=False)
    theme = Column(Integer, nullable=False)
    numero_question = Column(Integer, nullable=False)
    reponse_correcte = Column(Boolean, nullable=False)
    points = Column(Float, default=1.0)
    texte_question = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)

class UtilisationGrille(Base):
    __tablename__ = "utilisations_grilles"

    id = Column(Integer, primary_key=True, index=True)
    grille_id = Column(Integer, ForeignKey("grilles_theorie.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    annee = Column(Integer, nullable=False)