from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean
from app.database import Base
from datetime import datetime

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    famille = Column(String(10), nullable=False)
    lieu_id = Column(Integer, nullable=False)
    reference = Column(String(100), nullable=True)
    date_theorie = Column(Date, nullable=True)
    date_pratique_debut = Column(Date, nullable=True)
    date_pratique_fin = Column(Date, nullable=True)
    statut = Column(String(20), default="planifiee")
    annee = Column(Integer, default=datetime.now().year)
    note = Column(Text, nullable=True)
    responsable = Column(String(200), nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    type = Column(String(20), default="caces", nullable=True)