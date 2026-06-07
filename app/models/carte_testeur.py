from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from app.database import Base
from datetime import datetime

class CarteTesteur(Base):
    __tablename__ = "carte_testeur"
    id = Column(Integer, primary_key=True, index=True)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=False)
    famille = Column(String(50), nullable=False)
    nom_fichier = Column(String(200), nullable=False)
    contenu_pdf = Column(Text, nullable=True)
    date_upload = Column(DateTime, default=datetime.utcnow)
    actif = Column(Boolean, default=True)
