from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

class DocumentOfficiel(Base):
    __tablename__ = "document_officiel"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, unique=True, nullable=False)
    contenu_pdf = Column(Text, nullable=True)
    nom_fichier = Column(String, nullable=True)
    date_validite = Column(DateTime, nullable=True)
