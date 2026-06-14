from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Text, Float, UniqueConstraint
from app.database import Base


class JourFormation(Base):
    __tablename__ = "jours_formation"

    id                    = Column(Integer, primary_key=True, index=True)
    session_id            = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    date                  = Column(Date, nullable=False)
    intitule              = Column(String(200), nullable=True)
    libelle_colonne_libre = Column(String(100), nullable=True)
    note                  = Column(Text, nullable=True)
    note_privee           = Column(Text, nullable=True)
    note_privee_auteur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    actif                 = Column(Boolean, default=True)
    candidats_ids         = Column(Text, nullable=True)   # JSON [1,3,7] ; NULL = tous (rétrocompat)


class AffectationFormation(Base):
    __tablename__ = "affectations_formation"
    __table_args__ = (UniqueConstraint("jour_formation_id", "user_id"),)

    id                = Column(Integer, primary_key=True, index=True)
    jour_formation_id = Column(Integer, ForeignKey("jours_formation.id"), nullable=False)
    user_id           = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    theorie           = Column(Boolean, default=False)
    pratique          = Column(Boolean, default=False)
    principal         = Column(Boolean, default=False)
    # Contrainte applicative : un seul principal par jour_formation_id
    # (le nouvel enregistrant principal=True décoche l'ancien avant insertion)


class PlanningApprenant(Base):
    __tablename__ = "planning_apprenants"
    __table_args__ = (UniqueConstraint("jour_formation_id", "stagiaire_id"),)

    id                = Column(Integer, primary_key=True, index=True)
    jour_formation_id = Column(Integer, ForeignKey("jours_formation.id"), nullable=False)
    stagiaire_id      = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    heures_theorie    = Column(Float, default=0.0)
    heures_par_cat    = Column(Text, nullable=True)   # JSON {"A": 2.0, "B1": 1.5}
    heures_libre      = Column(Float, default=0.0)
    actif             = Column(Boolean, default=True)
    # Contrainte applicative : heures_theorie + sum(heures_par_cat.values()) + heures_libre <= 7.0


class AffectationTest(Base):
    __tablename__ = "affectations_test"
    __table_args__ = (UniqueConstraint("jour_test_id", "user_id"),)

    id           = Column(Integer, primary_key=True, index=True)
    jour_test_id = Column(Integer, ForeignKey("jours_test.id"), nullable=False)
    user_id      = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    role         = Column(String(20), default="testeur")
    principal    = Column(Boolean, default=False)
    # Contrainte applicative : un seul principal par jour_test_id
    # (le nouvel enregistrant principal=True décoche l'ancien avant insertion)
