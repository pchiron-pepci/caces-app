from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class OptionCategorie(Base):
    __tablename__ = "option_categorie"

    id = Column(Integer, primary_key=True, index=True)
    famille = Column(String(10), nullable=False)
    categorie = Column(String(10), nullable=False)
    code_option = Column(String(10), nullable=False)
    libelle_option = Column(String(100), nullable=False)
    incluse = Column(Boolean, default=False, nullable=False)
