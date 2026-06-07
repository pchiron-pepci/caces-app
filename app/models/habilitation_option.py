from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class HabilitationOption(Base):
    __tablename__ = "habilitation_option"

    id = Column(Integer, primary_key=True, index=True)
    habilitation_id = Column(Integer, ForeignKey("habilitations_testeurs.id"), nullable=False)
    code_option = Column(String(10), nullable=False)
