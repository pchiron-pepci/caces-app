from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey
from app.database import Base

class NonConformite(Base):
    __tablename__ = "non_conformites"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(20), nullable=True, unique=True)
    date = Column(Date, nullable=False)
    declarant_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    origine = Column(String(50), nullable=False)
    type_nc = Column(String(30), nullable=False)
    titre = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    action_preventive = Column(Text, nullable=True)
    action_corrective = Column(Text, nullable=True)
    justificatif_pdf = Column(Text, nullable=True)
    justificatif_nom = Column(String(200), nullable=True)
    statut = Column(String(20), nullable=False, default="ouvert")
    date_cloture = Column(Date, nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=True)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=True)
