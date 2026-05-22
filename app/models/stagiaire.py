from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from app.database import Base
from datetime import datetime

class Stagiaire(Base):
    __tablename__ = "stagiaires"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    date_naissance = Column(Date, nullable=False)
    email = Column(String(200), nullable=True)
    telephone = Column(String(20), nullable=True)
    employeur = Column(String(200), nullable=True)
    photo = Column(String(500), nullable=True)
    note = Column(Text, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    actif = Column(Integer, default=1)