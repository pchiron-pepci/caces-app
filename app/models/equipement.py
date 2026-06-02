from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from app.database import Base

class Equipement(Base):
    __tablename__ = "equipements"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    numero = Column(Integer, nullable=False)  # 1 à 15
    designation = Column(String(200), nullable=True)
    marque = Column(String(100), nullable=True)
    type_modele = Column(String(100), nullable=True)
    numero_serie = Column(String(100), nullable=True)
    conformite = Column(String(200), nullable=True)
    verifications = Column(String(200), nullable=True)
    date_verification = Column(Date, nullable=True)
    organisme_verification = Column(String(200), nullable=True)
    proprietaire = Column(String(200), nullable=True)
    actif = Column(Boolean, default=True)