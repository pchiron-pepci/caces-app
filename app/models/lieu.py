from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Text
from app.database import Base
from datetime import datetime
import enum

class TypeLieu(str, enum.Enum):
    CDT = "cdt"           # Centre De Test agréé
    HORS_CDT = "hors_cdt" # Chez le client

class Lieu(Base):
    __tablename__ = "lieux"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identification
    nom = Column(String(200), nullable=False)
    type = Column(String(10), nullable=False, default="cdt")  # cdt / hors_cdt
    
    # Adresse
    adresse = Column(String(300), nullable=True)
    code_postal = Column(String(10), nullable=True)
    ville = Column(String(100), nullable=True)
    
    # Contact
    telephone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    
    # Note libre
    note = Column(Text, nullable=True)
    
    # Métadonnées
    date_creation = Column(DateTime, default=datetime.utcnow)
    actif = Column(Boolean, default=True)