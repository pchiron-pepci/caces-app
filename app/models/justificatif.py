from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class Justificatif(Base):
    __tablename__ = "justificatifs"

    id = Column(Integer, primary_key=True, index=True)

    # 'formation' | 'dispense' | 'presence_session'
    type = Column(String(30), nullable=False)

    # Contexte : session toujours remplie, candidat nullable (ex: justif formation = niveau session)
    session_id = Column(Integer, nullable=False)
    session_candidat_id = Column(Integer, nullable=True)

    # Fichier stocké sur R2
    fichier_cle = Column(String(500), nullable=True)
    fichier_nom = Column(String(300), nullable=True)
    fichier_type = Column(String(100), nullable=True)

    date_upload = Column(DateTime, nullable=True)
    uploade_par = Column(String(200), nullable=True)
