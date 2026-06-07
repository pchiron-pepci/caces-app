from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class ConfigOrganisme(Base):
    __tablename__ = "config_organisme"
    id = Column(Integer, primary_key=True)
    nom_organisme = Column(String(200), nullable=True)
    logo_base64 = Column(Text, nullable=True)
    logo_nom = Column(String(200), nullable=True)
