from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, DateTime
from app.database import Base


class UtilisationTheme(Base):
    __tablename__ = "utilisations_themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    famille = Column(String(10), nullable=False)
    theme = Column(Integer, nullable=False)
    grille_id = Column(Integer, ForeignKey("grilles_theorie.id"), nullable=False)
    annee = Column(Integer, nullable=False)

    date_tirage = Column(DateTime, nullable=True)
    declenche_par_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    mode_tirage = Column(String(30), nullable=True)  # regime fige : v2_grille | assemblage_themes

    __table_args__ = (
        UniqueConstraint(
            "session_id", "famille", "theme",
            name="uq_session_famille_theme"
        ),
    )