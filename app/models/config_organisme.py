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
    prochain_numero_caces = Column(Integer, nullable=True)
