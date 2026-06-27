from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# ─────────────────────────────────────────────────────────────
# DÉFINITION INRS (générique, figée, alimentée par script d'init)
# ─────────────────────────────────────────────────────────────

class GrillePratique(Base):
    """Grille d'évaluation pratique INRS. type='base' (catégorie) ou 'option'."""
    __tablename__ = "grille_pratique"

    id = Column(Integer, primary_key=True, index=True)
    recommandation = Column(String(10), nullable=False)      # "R.482"
    categorie = Column(String(10), nullable=False)           # "F"
    type = Column(String(10), nullable=False, default="base")  # "base" | "option"
    code_option = Column(String(30), nullable=True)          # "PORTE_ENGINS", "TELECOMMANDE" (si option)
    libelle = Column(String(200), nullable=False)            # "Chariots de manutention tout-terrain" / "Porte-engins"
    ut = Column(Float, nullable=True)                        # unités de test (0.5 pour option)
    note_min = Column(Float, nullable=False, default=70)     # seuil global (70 base / 35 option)
    note_max = Column(Float, nullable=False, default=100)    # total (100 base / 50 option)
    version = Column(String(20), nullable=True)              # "2025"
    ordre = Column(Integer, nullable=False, default=0)
    actif = Column(Boolean, nullable=False, default=True)

    themes = relationship("ThemePratique", back_populates="grille",
                          cascade="all, delete-orphan", order_by="ThemePratique.ordre")
    criteres_eliminatoires = relationship("CritereEliminatoire", back_populates="grille",
                                          cascade="all, delete-orphan", order_by="CritereEliminatoire.ordre")


class ThemePratique(Base):
    __tablename__ = "theme_pratique"

    id = Column(Integer, primary_key=True, index=True)
    grille_id = Column(Integer, ForeignKey("grille_pratique.id"), nullable=False)
    libelle = Column(String(200), nullable=False)            # "Prise de poste et mise en service"
    bareme_theme = Column(Float, nullable=False)             # 16 (le seuil = bareme_theme / 2)
    ordre = Column(Integer, nullable=False, default=0)

    grille = relationship("GrillePratique", back_populates="themes")
    points = relationship("PointEvaluation", back_populates="theme",
                        cascade="all, delete-orphan", order_by="PointEvaluation.ordre")


class PointEvaluation(Base):
    """Un point d'évaluation (PE). La règle 'note > 0' s'applique au TOTAL du PE."""
    __tablename__ = "point_evaluation"

    id = Column(Integer, primary_key=True, index=True)
    theme_id = Column(Integer, ForeignKey("theme_pratique.id"), nullable=False)
    numero = Column(String(10), nullable=False)             # "1", "2"... (numéro PE)
    libelle_chapeau = Column(Text, nullable=True)           # intitulé du PE (ex. "Circuler à vide et en charge...")
    ordre = Column(Integer, nullable=False, default=0)

    theme = relationship("ThemePratique", back_populates="points")
    items = relationship("ItemPratique", back_populates="pe",
                        cascade="all, delete-orphan", order_by="ItemPratique.ordre")


class ItemPratique(Base):
    """Une ligne notée (critère) sous un PE. descriptif_seul=True => sous-puce explicative non notée."""
    __tablename__ = "item_pratique"

    id = Column(Integer, primary_key=True, index=True)
    pe_id = Column(Integer, ForeignKey("point_evaluation.id"), nullable=False)
    libelle = Column(Text, nullable=False)
    bareme_max = Column(Float, nullable=True)               # null si descriptif_seul
    descriptif_seul = Column(Boolean, nullable=False, default=False)
    ordre = Column(Integer, nullable=False, default=0)

    pe = relationship("PointEvaluation", back_populates="items")


class CritereEliminatoire(Base):
    __tablename__ = "critere_eliminatoire"

    id = Column(Integer, primary_key=True, index=True)
    grille_id = Column(Integer, ForeignKey("grille_pratique.id"), nullable=False)
    libelle = Column(Text, nullable=False)
    ordre = Column(Integer, nullable=False, default=0)

    grille = relationship("GrillePratique", back_populates="criteres_eliminatoires")


# ─────────────────────────────────────────────────────────────
# SAISIE TESTEUR (rattachée au SessionEpreuve existant)
# ─────────────────────────────────────────────────────────────

class SaisiePratique(Base):
    """Une saisie globale (base + options) ancree sur la PLANIFICATION
    (jour de test + candidat + categorie), comme le theorique numerique.
    Le SessionEpreuve (resultat) n'est cree qu'a la validation. Un seul en_cours par (jour, candidat, categorie)."""
    __tablename__ = "saisie_pratique"

    id = Column(Integer, primary_key=True, index=True)
    jour_test_id = Column(Integer, ForeignKey("jours_test.id"), nullable=False)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)
    categorie = Column(String(10), nullable=False)
    mode = Column(String(20), nullable=False, default="binaire")  # binaire | partiel_entier | partiel_demi
    statut = Column(String(20), nullable=False, default="en_cours")  # en_cours | valide
    testeur_nom = Column(String(120), nullable=True)
    observations = Column(Text, nullable=True)
    justification_ecart = Column(Text, nullable=True)        # requise si décision = échec
    resultat_propose = Column(Boolean, nullable=True)        # proposition système (global)
    resultat_valide = Column(Boolean, nullable=True)         # décision testeur (global)
    date_creation = Column(DateTime, server_default=func.now())
    date_validation = Column(DateTime, nullable=True)

    blocs = relationship("SaisieBloc", back_populates="saisie",
                        cascade="all, delete-orphan")


class SaisieBloc(Base):
    """Un bloc de résultat = la base, ou une option. Résultats calculés séparément."""
    __tablename__ = "saisie_bloc"

    id = Column(Integer, primary_key=True, index=True)
    saisie_id = Column(Integer, ForeignKey("saisie_pratique.id"), nullable=False)
    grille_id = Column(Integer, ForeignKey("grille_pratique.id"), nullable=False)
    type = Column(String(10), nullable=False, default="base")   # base | option
    note_calculee = Column(Float, nullable=True)
    resultat_propose = Column(Boolean, nullable=True)        # réussite de CE bloc (avant subordination)
    resultat_acquis = Column(Boolean, nullable=True)         # après subordination (option ⟺ base réussie)

    saisie = relationship("SaisiePratique", back_populates="blocs")
    notes = relationship("SaisieItemNote", back_populates="bloc",
                        cascade="all, delete-orphan")
    eliminatoires = relationship("SaisieEliminatoire", back_populates="bloc",
                                cascade="all, delete-orphan")


class SaisieItemNote(Base):
    __tablename__ = "saisie_item_note"

    id = Column(Integer, primary_key=True, index=True)
    bloc_id = Column(Integer, ForeignKey("saisie_bloc.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("item_pratique.id"), nullable=False)
    note = Column(Float, nullable=True)                     # Float pour le pas de 0,5

    bloc = relationship("SaisieBloc", back_populates="notes")


class SaisieEliminatoire(Base):
    __tablename__ = "saisie_eliminatoire"

    id = Column(Integer, primary_key=True, index=True)
    bloc_id = Column(Integer, ForeignKey("saisie_bloc.id"), nullable=False)
    critere_id = Column(Integer, ForeignKey("critere_eliminatoire.id"), nullable=False)

    bloc = relationship("SaisieBloc", back_populates="eliminatoires")
