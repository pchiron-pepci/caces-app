from sqlalchemy import Column, Integer, String, Boolean, Date, Float
from app.database import Base

class Famille(Base):
    __tablename__ = "familles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), nullable=False, unique=True)
    libelle = Column(String(200), nullable=False)
    validite_ans = Column(Integer, default=5)
    actif = Column(Boolean, default=True)

class Categorie(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    famille_id = Column(Integer, nullable=False)
    code = Column(String(10), nullable=False)
    libelle = Column(String(200), nullable=True)
    ut_pratique = Column(Float, default=1.0)  # Nombre d'UT pour l'épreuve pratique
    est_option = Column(Boolean, default=False)  # True si c'est une option (PE, Tel...)
    option_pe = Column(Boolean, default=False)
    option_tel = Column(Boolean, default=False)
    pepci_habilite = Column(Boolean, default=False)
    date_habilitation = Column(Date, nullable=True)
    date_sortie = Column(Date, nullable=True)
    actif = Column(Boolean, default=True)