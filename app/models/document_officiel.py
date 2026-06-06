from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from datetime import datetime

class DocumentOfficiel(Base):
    __tablename__ = "document_officiel"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, unique=True, nullable=False)
    url = Column(String, nullable=True)
    nom_fichier = Column(String, nullable=True)
    date_upload = Column(DateTime, nullable=True, default=datetime.utcnow)
