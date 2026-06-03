from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base
from datetime import datetime

class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    mot_de_passe = Column(String(200), nullable=False)
    role = Column(String(20), default="testeur")  # admin, testeur
    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)