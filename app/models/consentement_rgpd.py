from sqlalchemy import Column, Integer, Boolean, DateTime, String, UniqueConstraint
from app.database import Base


class ConsentementRGPD(Base):
    __tablename__ = "consentements_rgpd"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)
    stagiaire_id = Column(Integer, nullable=False)

    # Vérification d'identité (formateur, côté overlay)
    verificateur_identite = Column(String(200), nullable=True)
    horodatage_verification = Column(DateTime, nullable=True)

    # Signature candidat (côté page consentement)
    rgpd_accepte = Column(Boolean, nullable=True)
    photo_accepte = Column(Boolean, nullable=True)
    plaintes_atteste = Column(Boolean, nullable=True)
    signature_base64 = Column(String, nullable=True)
    horodatage = Column(DateTime, nullable=True)
    ip_address = Column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint('session_id', 'stagiaire_id', name='uq_consentement_session_stagiaire'),
    )
