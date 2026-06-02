from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.database import Base

class LieuHabilitation(Base):
    __tablename__ = "lieu_habilitations"

    id = Column(Integer, primary_key=True, index=True)
    lieu_id = Column(Integer, ForeignKey("lieux.id"), nullable=False)
    famille = Column(String(10), nullable=False)
    categorie = Column(String(10), nullable=False)
    actif = Column(Boolean, default=True)