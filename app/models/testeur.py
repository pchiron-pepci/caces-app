from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum

class StatutTesteur(str, enum.Enum):
    INTERNE = "interne"
    INDEPENDANT = "independant"
    ENTREPRISE = "entreprise"

class Testeur(Base):
    __tablename__ = "testeurs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identité
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    telephone = Column(String(20), nullable=True)
    photo = Column(String(500), nullable=True)
    
    # Statut
    statut = Column(String(20), default="interne")  # interne / independant / entreprise
    entreprise = Column(String(200), nullable=True)  # si entreprise ou indépendant
    
    # Habilitations INRS
    numero_inrs = Column(String(50), nullable=True)
    date_habilitation = Column(Date, nullable=True)
    date_expiration_habilitation = Column(Date, nullable=True)
    
    # Obligations
    visite_medicale = Column(Date, nullable=True)
    formation_continue = Column(Date, nullable=True)
    
    # Note libre
    note = Column(Text, nullable=True)
    
    # Métadonnées
    date_creation = Column(DateTime, default=datetime.utcnow)
    actif = Column(Boolean, default=True)