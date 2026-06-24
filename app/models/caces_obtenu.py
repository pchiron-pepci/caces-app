from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint, Boolean
from app.database import Base
from datetime import datetime


class CacesObtenu(Base):
    __tablename__ = "caces_obtenus"

    id = Column(Integer, primary_key=True, index=True)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    famille = Column(String(10), nullable=False)
    categorie = Column(String(10), nullable=False)
    options_obtenues = Column(String(200), nullable=True)
    date_obtention = Column(Date, nullable=False)
    date_echeance = Column(Date, nullable=False)
    post_cloture = Column(Boolean, default=False, nullable=True)
    resultat_theorie_id = Column(Integer, ForeignKey("resultats_theorie.id"), nullable=True)
    caces_initial_id    = Column(Integer, ForeignKey("caces_obtenus.id"), nullable=True)
    dispense_externe_sc_id = Column(Integer, ForeignKey("session_candidats.id"), nullable=True)  # CACES fonde sur la dispense externe de ce SessionCandidat
    numero_ordre = Column(Integer, unique=True, nullable=True)
    statut = Column(String(20), nullable=False, default="a_valider")
    motif_annulation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("stagiaire_id", "session_id", "categorie", name="uq_caces_obtenu"),
    )
