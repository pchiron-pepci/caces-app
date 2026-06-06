from sqlalchemy import Column, Integer, DateTime
from app.database import Base
from datetime import datetime

class AssociationLog(Base):
    __tablename__ = "association_log"

    id = Column(Integer, primary_key=True, index=True)
    date_association = Column(DateTime, default=datetime.utcnow)
    nb_images = Column(Integer, nullable=False)
