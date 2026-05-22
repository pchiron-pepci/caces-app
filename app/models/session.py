from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum

class TypeSession(str, enum.Enum):
    PREMIER_TEST = "premier_test"
    RECYCLAGE = "recyclage"
    EXTENSION = "extension"

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Type de session
    type = Column(String(20), nullable=False, default="premier_test")
    
    # Famille CACES concernée
    famille = Column(String(10), nullable=False)  # R482, R489, R486...
    
    # Lieu
    lieu_id = Column(Integer, ForeignKey("lieux.id"), nullable=False)
    lieu = relationship("Lieu")
    
    # Dates
    date_theorie = Column(Date, nullable=True)
    date_pratique_debut = Column(Date, nullable=True)
    date_pratique_fin = Column(Date, nullable=True)
    
    # Statut
    statut = Column(String(20), default="planifiee")  # planifiee / en_cours / terminee / annulee
    
    # Référence interne
    reference = Column(String(50), nullable=True)
    
    # Note libre
    note = Column(Text, nullable=True)
    
    # Métadonnées
    date_creation = Column(DateTime, default=datetime.utcnow)
    annee = Column(Integer, default=datetime.utcnow().year)