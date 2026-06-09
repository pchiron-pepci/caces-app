from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey
from app.database import Base

class CarteCaces(Base):
    __tablename__ = "carte_caces"
    id = Column(Integer, primary_key=True)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    famille = Column(String(20), nullable=False)
    numero_carte = Column(String(30), unique=True, nullable=False)
    date_generation = Column(Date, nullable=False)
    statut = Column(String(20), nullable=False, default="en_preparation")
    motif_annulation = Column(String(500), nullable=True)
    caces_json = Column(Text, nullable=True)
