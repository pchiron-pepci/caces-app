from sqlalchemy import Column, Integer, DateTime
from datetime import datetime
from app.database import Base


class AssociationAudioLog(Base):
    __tablename__ = "association_audio_log"

    id = Column(Integer, primary_key=True)
    date_association = Column(DateTime, default=datetime.utcnow)
    nb_audios = Column(Integer, nullable=False)
