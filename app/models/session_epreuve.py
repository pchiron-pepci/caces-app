from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base

class SessionEpreuve(Base):
    __tablename__ = "session_epreuves"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=True)

    # Epreuve
    date = Column(Date, nullable=False)
    famille = Column(String(10), nullable=False)
    categorie = Column(String(10), nullable=False)
    option_pe = Column(Boolean, default=False)
    option_tel = Column(Boolean, default=False)
    ut = Column(Float, default=1.0)

    # Notes pratiques (PE1 à PE12)
    pe1 = Column(Integer, nullable=True)
    pe2 = Column(Integer, nullable=True)
    pe3 = Column(Integer, nullable=True)
    pe4 = Column(Integer, nullable=True)
    pe5 = Column(Integer, nullable=True)
    pe6 = Column(Integer, nullable=True)
    pe7 = Column(Integer, nullable=True)
    pe8 = Column(Integer, nullable=True)
    pe9 = Column(Integer, nullable=True)
    pe10 = Column(Integer, nullable=True)
    pe11 = Column(Integer, nullable=True)
    pe12 = Column(Integer, nullable=True)

    # Seuils minimum par thème
    seuil1_ok = Column(Boolean, nullable=True)
    seuil2_ok = Column(Boolean, nullable=True)
    seuil3_ok = Column(Boolean, nullable=True)
    seuil4_ok = Column(Boolean, nullable=True)
    seuil5_ok = Column(Boolean, nullable=True)

    # Résultat
    note_totale = Column(Integer, nullable=True)
    elimination = Column(Boolean, default=False)
    obtenue = Column(Boolean, nullable=True)

    # Note testeur
    note_testeur = Column(Text, nullable=True)
    options_obtenues = Column(String(200), nullable=True)
    bloque = Column(Boolean, default=False, nullable=False)

    # Justificatif grille d'évaluation pratique (1 fichier, multi-format)
    justificatif_cle = Column(String(500), nullable=True)
    justificatif_nom = Column(String(255), nullable=True)