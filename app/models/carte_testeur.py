from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey
from app.database import Base
from datetime import datetime

class CarteTesteur(Base):
    __tablename__ = "carte_testeur"
    id = Column(Integer, primary_key=True, index=True)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=False)
    famille = Column(String(50), nullable=False)
    nom_fichier = Column(String(200), nullable=False)
    cle = Column(String(500), nullable=True)
    date_upload = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(Date, nullable=True)
    actif = Column(Boolean, default=True)
