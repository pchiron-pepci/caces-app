from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.orm import relationship
from app.database import Base

class Famille(Base):
    __tablename__ = "familles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), nullable=False, unique=True)  # R482, R489, R486A
    libelle = Column(String(200), nullable=False)
    validite_ans = Column(Integer, default=5)  # 5 ans par défaut, 10 pour R482
    actif = Column(Boolean, default=True)

class Categorie(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    famille_id = Column(Integer, nullable=False)
    code = Column(String(10), nullable=False)   # A, B1, C1, 1B, 3...
    libelle = Column(String(200), nullable=True) # Engins compacts...
    
    # Options possibles
    option_pe = Column(Boolean, default=False)  # Porte-engins
    option_tel = Column(Boolean, default=False) # Télécommande
    
    # Habilitation PEPCI
    pepci_habilite = Column(Boolean, default=False)
    date_habilitation = Column(Date, nullable=True)
    
    actif = Column(Boolean, default=True)