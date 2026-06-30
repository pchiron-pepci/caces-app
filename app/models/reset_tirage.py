"""Modele des RESETS de compteurs de tirage, PAR FAMILLE.

Un reset cree une borne datee a partir de laquelle le tirage ET les statistiques
repartent a zero pour la famille concernee. Les donnees (UtilisationTheme) ne sont
JAMAIS supprimees : le reset n'est qu'un point de repere temporel, empilable.

Le dernier reset d'une famille definit la borne active du comptage de priorite.
S'il n'existe aucun reset pour une famille, le comptage porte sur tout l'historique.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ResetTirage(Base):
    __tablename__ = "reset_tirage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    famille = Column(String(10), nullable=False, index=True)   # "R482", "R489"...
    date_reset = Column(DateTime, nullable=False, server_default=func.now())
    declenche_par_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)


def dernier_reset(famille: str, db) -> "datetime | None":
    """Renvoie la date du dernier reset de la famille, ou None s'il n'y en a pas.
    Sert de borne basse au comptage de priorite (tirage) et aux statistiques."""
    r = (
        db.query(ResetTirage)
        .filter(ResetTirage.famille == famille)
        .order_by(ResetTirage.date_reset.desc())
        .first()
    )
    return r.date_reset if r else None


def resets_famille(famille: str, db) -> list:
    """Renvoie tous les resets d'une famille, du plus recent au plus ancien.
    Sert a construire les periodes selectionnables dans les statistiques."""
    return (
        db.query(ResetTirage)
        .filter(ResetTirage.famille == famille)
        .order_by(ResetTirage.date_reset.desc())
        .all()
    )


def audit_reset_requis(db) -> "date | None":
    """Renvoie la date d'audit si un reset est requis (et donc si le tirage doit
    etre bloque + le bandeau affiche), sinon None.

    Regle : reset requis si la date d'audit externe est aujourd'hui ou passee ET
    qu'aucun reset n'a eu lieu a cette date. Se resout des qu'un reset est fait le
    jour de l'audit, ou que l'OF repousse sa date d'audit. Le meme critere pilote
    le bandeau du dashboard et le blocage du tirage."""
    from datetime import date as _date
    from sqlalchemy import func as _func
    from app.models.config_organisme import ConfigOrganisme  # import local : evite les cycles

    cfg = db.query(ConfigOrganisme).first()
    if not cfg or not cfg.audit_externe_date:
        return None
    if cfg.audit_externe_date > _date.today():
        return None
    reset_ce_jour = (
        db.query(ResetTirage)
        .filter(_func.date(ResetTirage.date_reset) == cfg.audit_externe_date)
        .first()
    )
    return None if reset_ce_jour else cfg.audit_externe_date