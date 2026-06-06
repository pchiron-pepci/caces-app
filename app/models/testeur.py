from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean
from app.database import Base
from datetime import datetime

class Testeur(Base):
    __tablename__ = "testeurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    telephone = Column(String(20), nullable=True)
    photo = Column(String(500), nullable=True)
    statut = Column(String(20), default="interne")
    entreprise = Column(String(200), nullable=True)
    numero_inrs = Column(String(50), nullable=True)
    date_habilitation = Column(Date, nullable=True)
    date_expiration_habilitation = Column(Date, nullable=True)
    visite_medicale = Column(Date, nullable=True)
    formation_continue = Column(Date, nullable=True)
    date_prochain_controle = Column(Date, nullable=True)
    note = Column(Text, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    actif = Column(Boolean, default=True)
    carte_url = Column(String(500), nullable=True)
    carte_nom_fichier = Column(String(200), nullable=True)