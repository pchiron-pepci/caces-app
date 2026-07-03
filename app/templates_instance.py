from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

from datetime import timezone as _tz
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _PARIS = _ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover
    _PARIS = None


def _to_paris(dt):
    """Convertit un datetime stocke en UTC vers l'heure de Paris (ete/hiver auto).
    Les datetimes naifs sont supposes UTC (cas du projet : utcnow / func.now())."""
    if dt is None:
        return None
    if _PARIS is None:
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz.utc)
    return dt.astimezone(_PARIS)


def _fmt_paris(dt, fmt="%d/%m/%Y"):
    d = _to_paris(dt)
    return d.strftime(fmt) if d else ""


def _fmt_paris_dt(dt, fmt="%d/%m/%Y %H:%M"):
    d = _to_paris(dt)
    return d.strftime(fmt) if d else ""


templates.env.filters["paris"] = _fmt_paris
templates.env.filters["paris_dt"] = _fmt_paris_dt
