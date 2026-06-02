from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class HabilitationTesteur(Base):
    __tablename__ = "habilitations_testeurs"

    id = Column(Integer, primary_key=True, index=True)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=False)
    testeur = relationship("Testeur")
    famille = Column(String(10), nullable=False)
    categorie = Column(String(10), nullable=False)
    option_pe = Column(Boolean, default=False)
    option_tel = Column(Boolean, default=False)
    date_integration = Column(Date, nullable=False)
    date_expiration = Column(Date, nullable=True)
    actif = Column(Boolean, default=True)