from app.models.config_organisme import ConfigOrganisme

_FALLBACK_PIN_ADMIN = "1505"
_FALLBACK_PIN_FORMATEUR = "1234"


def get_pin_admin(db) -> str:
    config = db.query(ConfigOrganisme).first()
    pin = (config.pin_admin or "").strip() if config else ""
    return pin if pin else _FALLBACK_PIN_ADMIN


def get_pin_formateur(db) -> str:
    config = db.query(ConfigOrganisme).first()
    pin = (config.pin_formateur or "").strip() if config else ""
    return pin if pin else _FALLBACK_PIN_FORMATEUR


def get_mode_tirage(db) -> str:
    """Retourne le mode de tirage theorique de l'organisme.
    'grille_complete' (defaut, referentiel INRS V2) ou 'themes' (assemblage)."""
    from app.models.config_organisme import ConfigOrganisme
    cfg = db.query(ConfigOrganisme).first()
    return (cfg.mode_tirage_theorie if cfg and cfg.mode_tirage_theorie else "grille_complete")
