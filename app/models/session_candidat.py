from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class SessionCandidat(Base):
    __tablename__ = "session_candidats"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)

    # Consentements RGPD
    rgpd_accepte = Column(Boolean, default=True)
    photo_accepte = Column(Boolean, default=True)

    # Théorie
    theorie_dispensee = Column(Boolean, default=False)
    dispense_note = Column(Text, nullable=True)
    dispense_fichier_cle = Column(String(500), nullable=True)
    dispense_fichier_nom = Column(String(255), nullable=True)
    dispense_fichier_type = Column(String(100), nullable=True)
    dispense_date = Column(Date, nullable=True)
    theorie_date = Column(Date, nullable=True)
    theorie_note_totale = Column(Integer, nullable=True)
    theorie_obtenue = Column(Boolean, nullable=True)

    # Notes théorie par thème
    theorie_theme1 = Column(Integer, nullable=True)  # Connaissances générales
    theorie_theme2 = Column(Integer, nullable=True)  # Technologie et stabilité
    theorie_theme3 = Column(Integer, nullable=True)  # Exploitation
    theorie_theme4 = Column(Integer, nullable=True)  # Circulation
    theorie_theme5 = Column(Integer, nullable=True)  # Entretien

    # Note libre
    note = Column(Text, nullable=True)

    actif = Column(Boolean, default=True)