from sqlalchemy import Column, Integer, String, Text, Date
from app.database import Base

class ConfigOrganisme(Base):
    __tablename__ = "config_organisme"
    id = Column(Integer, primary_key=True)
    nom_organisme = Column(String(200), nullable=True)
    logo_base64 = Column(Text, nullable=True)
    logo_nom = Column(String(200), nullable=True)
    audit_interne_date = Column(Date, nullable=True)
    audit_externe_date = Column(Date, nullable=True)
    revue_direction_date = Column(Date, nullable=True)
    pin_formateur = Column(String(20), nullable=True)
    pin_admin = Column(String(20), nullable=True)
    prochain_numero_caces = Column(Integer, nullable=True)
    adresse = Column(Text, nullable=True)
    siret = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    telephone = Column(String(50), nullable=True)
    signataire_nom = Column(String(100), nullable=True)
    signataire_prenom = Column(String(100), nullable=True)
    signataire_qualite = Column(String(100), nullable=True)
    signature_base64 = Column(Text, nullable=True)
    signature_nom = Column(String(200), nullable=True)
    url_verification_caces = Column(String(500), nullable=True)
    logo2_base64 = Column(Text, nullable=True)
    logo2_nom = Column(String(200), nullable=True)
