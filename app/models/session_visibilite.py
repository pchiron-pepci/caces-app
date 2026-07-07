from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.database import Base


class SessionVisibilite(Base):
    """Visibilite d'une session cote terrain, decidee manuellement par le back-office.
    1 ligne = la personne (user_id) voit cette session. Absence de ligne = ne voit pas.
    Decoche par defaut : une personne affectee ne voit rien tant qu'elle n'est pas cochee.
    """
    __tablename__ = "session_visibilite"
    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_session_visibilite"),)

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False, index=True)
