from app.models.config_organisme import ConfigOrganisme

_FALLBACK_PIN_ADMIN = "1505"


def get_pin_admin(db) -> str:
    config = db.query(ConfigOrganisme).first()
    pin = (config.pin_admin or "").strip() if config else ""
    return pin if pin else _FALLBACK_PIN_ADMIN
