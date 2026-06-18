"""
app/services/pdf_consentement_neutralite.py
Génération PDF du consentement RGPD et de l'attestation de neutralité,
un document par candidat.
"""

from io import BytesIO
from html import escape as _esc
from sqlalchemy.orm import Session as DBSession

from app.models.consentement_rgpd import ConsentementRGPD
from app.models.attestation_neutralite import AttestationNeutralite
from app.models.jour_test import JourTest
from app.models.session import Session
from app.models.stagiaire import Stagiaire
from app.models.config_organisme import ConfigOrganisme


# ── Helpers partagés ────────────────────────────────────────────────────────

def _get_logo_data(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    if cfg and cfg.logo_base64 and cfg.logo_nom:
        ext = cfg.logo_nom.rsplit('.', 1)[-1].lower()
        mime = {
            'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'gif': 'image/gif', 'webp': 'image/webp',
        }.get(ext, 'image/png')
        return f"data:{mime};base64,{cfg.logo_base64}"
    return ""


def _get_nom_organisme(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    return cfg.nom_organisme if cfg and cfg.nom_organisme else "PEPCI Formation"


def _horodatage_str(dt) -> str:
    """Formate un DateTime en 'jj/mm/aaaa hh:mm', ou 'Non signé' si null."""
    if dt is None:
        return "Non signé"
    return dt.strftime("%d/%m/%Y %H:%M")


def _signature_html(sig: str | None) -> str:
    """Retourne un <img> si sig est une data URI ou base64 brut, sinon 'Non signé'."""
    if not sig:
        return '<span style="color:#888; font-style:italic;">Non signé</span>'
    # Déjà une data URI (canvas JS) → utiliser directement
    if sig.startswith("data:"):
        src = sig
    else:
        # Base64 brut → supposer PNG
        src = f"data:image/png;base64,{sig}"
    return (
        f'<img src="{src}" '
        f'style="max-height:80px; max-width:260px; border:1px solid #ddd; '
        f'border-radius:3px; padding:4px; background:white; display:block;" '
        f'alt="Signature" />'
    )


def _oui_non(val: bool | None) -> str:
    if val is True:
        return '<span style="color:#1b5e20; font-weight:bold;">OUI</span>'
    if val is False:
        return '<span style="color:#b71c1c; font-weight:bold;">NON</span>'
    return '<span style="color:#888;">—</span>'


def _html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()


# ── CSS commun ──────────────────────────────────────────────────────────────

_CSS = """
  @page { margin: 18mm 15mm 15mm 15mm; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #1a1a1a; margin: 0; }

  .doc-header {
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 2px solid #1a237e; padding-bottom: 8px; margin-bottom: 20px;
  }
  .doc-header-left { display: flex; align-items: center; gap: 14px; }
  h1 { font-size: 15px; color: #1a237e; margin: 0 0 2px 0; }
  .doc-meta { text-align: right; font-size: 9.5px; color: #555; line-height: 1.7; }

  .section { margin-bottom: 18px; }
  .section-title {
    font-size: 10px; font-weight: bold; text-transform: uppercase;
    letter-spacing: 0.5px; color: #666; border-bottom: 1px solid #e0e0e0;
    padding-bottom: 3px; margin-bottom: 10px;
  }
  .field-row { display: flex; align-items: baseline; margin-bottom: 7px; gap: 8px; }
  .field-label { color: #555; font-size: 10px; min-width: 200px; flex-shrink: 0; }
  .field-value { font-size: 11px; }

  .check-row {
    display: flex; align-items: center; gap: 10px;
    border: 1px solid #e0e0e0; border-radius: 3px;
    padding: 5px 10px; margin-bottom: 5px; background: #fafafa;
  }
  .check-label { flex: 1; font-size: 10.5px; }

  .sig-block { margin-top: 6px; }

  .footer {
    text-align: center; font-size: 8.5px; color: #aaa;
    margin-top: 24px; border-top: 1px solid #eee; padding-top: 6px;
  }
"""


# ── Consentement RGPD ───────────────────────────────────────────────────────

def _build_html_consentement(
    c:             ConsentementRGPD,
    stagiaire:     Stagiaire | None,
    session:       Session | None,
    nom_organisme: str,
    logo_data:     str,
) -> str:
    nom_candidat = f"{stagiaire.nom} {stagiaire.prenom}" if stagiaire else f"Candidat #{c.stagiaire_id}"
    ref_str      = (session.reference or f"Session {session.id}") if session else "—"
    date_str     = session.date_theorie.strftime("%d/%m/%Y") if session and session.date_theorie else "—"

    logo_html = (
        f'<img src="{logo_data}" style="height:44px; max-width:130px; object-fit:contain;" alt="Logo" />'
        if logo_data else ""
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>{_CSS}</style>
</head>
<body>

<div class="doc-header">
  <div class="doc-header-left">
    {logo_html}
    <div>
      <h1>Consentement RGPD</h1>
      <div style="font-size:9.5px; color:#666;">{_esc(nom_organisme)}</div>
    </div>
  </div>
  <div class="doc-meta">
    <div><strong>Session :</strong> {_esc(ref_str)}</div>
    <div><strong>Date :</strong> {date_str}</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Candidat</div>
  <div class="field-row">
    <span class="field-label">Nom et prénom</span>
    <span class="field-value" style="font-weight:bold; font-size:13px;">{_esc(nom_candidat)}</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Déclarations du candidat</div>

  <div class="check-row">
    <span class="check-label">
      J'ai pris connaissance de la politique de protection des données personnelles
      et j'accepte le traitement de mes données dans le cadre de cette formation.
    </span>
    <span>{_oui_non(c.rgpd_accepte)}</span>
  </div>

  <div class="check-row">
    <span class="check-label">
      J'autorise l'organisme à utiliser ma photographie à des fins d'identification
      et d'édition de la carte CACES®.
    </span>
    <span>{_oui_non(c.photo_accepte)}</span>
  </div>

  <div class="check-row">
    <span class="check-label">
      J'atteste sur l'honneur ne faire l'objet d'aucune plainte ou condamnation
      pour conduite dangereuse d'engins ou de véhicules.
    </span>
    <span>{_oui_non(c.plaintes_atteste)}</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Vérification d'identité</div>
  <div class="field-row">
    <span class="field-label">Vérificateur</span>
    <span class="field-value">{_esc(c.verificateur_identite or "—")}</span>
  </div>
  <div class="field-row">
    <span class="field-label">Horodatage vérification</span>
    <span class="field-value">{_horodatage_str(c.horodatage_verification)}</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Signature du candidat</div>
  <div class="field-row">
    <span class="field-label">Horodatage signature</span>
    <span class="field-value">{_horodatage_str(c.horodatage)}</span>
  </div>
  <div class="sig-block">
    {_signature_html(c.signature_base64)}
  </div>
</div>

<div class="footer">
  Consentement RGPD &mdash; {_esc(nom_candidat)} &mdash; {_esc(ref_str)} &mdash; {_esc(nom_organisme)}
</div>

</body>
</html>"""


def generer_pdf_consentement(consentement_id: int, db: DBSession) -> bytes:
    """Génère le PDF du consentement RGPD d'un candidat."""
    c = db.query(ConsentementRGPD).filter(ConsentementRGPD.id == consentement_id).first()
    if not c:
        raise ValueError(f"ConsentementRGPD {consentement_id} introuvable")

    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == c.stagiaire_id).first()
    session   = db.query(Session).filter(Session.id == c.session_id).first()

    html = _build_html_consentement(
        c, stagiaire, session,
        _get_nom_organisme(db),
        _get_logo_data(db),
    )
    return _html_to_pdf(html)


# ── Attestation de neutralité ───────────────────────────────────────────────

def _build_html_neutralite(
    a:             AttestationNeutralite,
    stagiaire:     Stagiaire | None,
    session:       Session | None,
    jour_test:     JourTest | None,
    nom_organisme: str,
    logo_data:     str,
) -> str:
    nom_candidat = f"{stagiaire.nom} {stagiaire.prenom}" if stagiaire else f"Candidat #{a.stagiaire_id}"
    ref_str      = (session.reference or f"Session {session.id}") if session else "—"
    date_jour    = jour_test.date.strftime("%d/%m/%Y") if jour_test and jour_test.date else "—"

    logo_html = (
        f'<img src="{logo_data}" style="height:44px; max-width:130px; object-fit:contain;" alt="Logo" />'
        if logo_data else ""
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>{_CSS}</style>
</head>
<body>

<div class="doc-header">
  <div class="doc-header-left">
    {logo_html}
    <div>
      <h1>Attestation de neutralité</h1>
      <div style="font-size:9.5px; color:#666;">{_esc(nom_organisme)}</div>
    </div>
  </div>
  <div class="doc-meta">
    <div><strong>Session :</strong> {_esc(ref_str)}</div>
    <div><strong>Date épreuve :</strong> {date_jour}</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Candidat</div>
  <div class="field-row">
    <span class="field-label">Nom et prénom</span>
    <span class="field-value" style="font-weight:bold; font-size:13px;">{_esc(nom_candidat)}</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Vérification d'identité</div>
  <div class="field-row">
    <span class="field-label">Vérificateur</span>
    <span class="field-value">{_esc(a.verificateur_identite or "—")}</span>
  </div>
  <div class="field-row">
    <span class="field-label">Horodatage vérification</span>
    <span class="field-value">{_horodatage_str(a.horodatage_verification)}</span>
  </div>
</div>

<div class="section">
  <div class="section-title">
    Attestation sur l'honneur — absence de lien avec l'organisme évaluateur
  </div>
  <div style="font-size:10.5px; line-height:1.6; color:#333; margin-bottom:12px;">
    Le candidat soussigné atteste qu'il n'entretient aucun lien de subordination
    ou d'intérêt avec l'organisme évaluateur qui pourrait nuire à la neutralité
    de l'évaluation CACES®.
  </div>
  <div class="field-row">
    <span class="field-label">Horodatage signature</span>
    <span class="field-value">{_horodatage_str(a.horodatage)}</span>
  </div>
  <div class="sig-block">
    {_signature_html(a.signature_base64)}
  </div>
</div>

<div class="footer">
  Attestation de neutralité &mdash; {_esc(nom_candidat)} &mdash; {_esc(ref_str)} &mdash; {_esc(nom_organisme)}
</div>

</body>
</html>"""


def generer_pdf_neutralite(attestation_id: int, db: DBSession) -> bytes:
    """Génère le PDF de l'attestation de neutralité d'un candidat."""
    a = db.query(AttestationNeutralite).filter(AttestationNeutralite.id == attestation_id).first()
    if not a:
        raise ValueError(f"AttestationNeutralite {attestation_id} introuvable")

    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == a.stagiaire_id).first()
    jour_test = db.query(JourTest).filter(JourTest.id == a.jour_test_id).first()
    session   = (
        db.query(Session).filter(Session.id == jour_test.session_id).first()
        if jour_test else None
    )

    html = _build_html_neutralite(
        a, stagiaire, session, jour_test,
        _get_nom_organisme(db),
        _get_logo_data(db),
    )
    return _html_to_pdf(html)
