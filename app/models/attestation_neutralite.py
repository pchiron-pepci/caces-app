from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from app.database import Base


class AttestationNeutralite(Base):
    __tablename__ = "attestations_neutralite"
    id = Column(Integer, primary_key=True, index=True)
    jour_test_id = Column(Integer, nullable=False)
    stagiaire_id = Column(Integer, nullable=False)
    verificateur_identite = Column(String(200), nullable=True)
    horodatage_verification = Column(DateTime, nullable=True)
    signature_base64 = Column(Text, nullable=True)
    horodatage = Column(DateTime, nullable=True)
    ip_address = Column(String(50), nullable=True)
    __table_args__ = (
        UniqueConstraint('jour_test_id', 'stagiaire_id', name='uq_attestation_jour_stagiaire'),
    )
