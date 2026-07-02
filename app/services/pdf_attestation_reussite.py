"""
app/services/pdf_attestation_reussite.py
Genere l'attestation de reussite PROVISOIRE d'un candidat sur une session.
Document d'attente (valable 1 mois) remis avant delivrance de la carte CACES officielle.
Liste : epreuves passees (theorie + pratique, reussite/echec) + CACES pouvant etre
delivres (statut a_valider) sous reserve de confirmation. Signature responsable OF.
"""

from io import BytesIO
from datetime import date, timedelta
from html import escape as _esc
from weasyprint import HTML
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.models.session_candidat import SessionCandidat
from app.models.session_epreuve import SessionEpreuve
from app.models.jour_test import JourTest, ResultatTheorie
from app.models.stagiaire import Stagiaire
from app.models.caces_obtenu import CacesObtenu
from app.models.config_organisme import ConfigOrganisme


def _get_cfg(db):
    return db.query(ConfigOrganisme).first()


def _logo_data(cfg):
    if cfg and cfg.logo_base64:
        nom = (cfg.logo_nom or "").lower()
        mime = "image/png"
        if nom.endswith(".jpg") or nom.endswith(".jpeg"):
            mime = "image/jpeg"
        elif nom.endswith(".svg"):
            mime = "image/svg+xml"
        return "data:%s;base64,%s" % (mime, cfg.logo_base64)
    return ""


def _nom_organisme(cfg):
    return (cfg.nom_organisme if cfg and cfg.nom_organisme else "PEPCI Formation")


def _signature_img(cfg):
    sig = cfg.signature_base64 if cfg else None
    if not sig:
        return '<span style="color:#888; font-style:italic;">Signature non configuree</span>'
    src = sig if sig.startswith("data:") else ("data:image/png;base64,%s" % sig)
    return '<img src="%s" style="max-height:70px; max-width:220px;" alt="signature">' % src


def _signataire(cfg):
    if not cfg:
        return "Le responsable"
    parts = []
    if cfg.signataire_prenom:
        parts.append(cfg.signataire_prenom)
    if cfg.signataire_nom:
        parts.append(cfg.signataire_nom)
    nom = " ".join(parts) if parts else (cfg.signature_nom or "Le responsable")
    qualite = cfg.signataire_qualite or "Responsable OTC"
    return "%s<br><span style='font-size:11px; color:#666;'>%s</span>" % (_esc(nom), _esc(qualite))


def _fmt_date(d):
    return d.strftime("%d/%m/%Y") if d else "—"


def _ref_session(sess):
    if getattr(sess, "reference", None):
        return sess.reference
    return "n° %s" % sess.id


def _collecter(session_id, stagiaire_id, db):
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        return None
    stag = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    if not stag:
        return None

    epreuves = (
        db.query(SessionEpreuve)
        .filter(
            SessionEpreuve.session_id == session_id,
            SessionEpreuve.stagiaire_id == stagiaire_id,
        )
        .all()
    )

    theories = (
        db.query(ResultatTheorie)
        .filter(
            ResultatTheorie.session_id == session_id,
            ResultatTheorie.stagiaire_id == stagiaire_id,
        )
        .all()
    )
    fam_session = getattr(sess, "famille", None)
    theorie_famille = None
    for t in theories:
        if t.obtenue is True:
            theorie_famille = True
            break
        if t.obtenue is False and theorie_famille is None:
            theorie_famille = False

    caces = (
        db.query(CacesObtenu)
        .filter(
            CacesObtenu.session_id == session_id,
            CacesObtenu.stagiaire_id == stagiaire_id,
            CacesObtenu.statut == "a_valider",
        )
        .order_by(CacesObtenu.famille, CacesObtenu.categorie)
        .all()
    )
    # Categories pour lesquelles un CACES est delivrable -> theorie couverte
    # (dispense, theorie du jour reussie, ou theorie valide reconstituee ailleurs)
    cat_couvertes = {(c.famille, c.categorie) for c in caces}

    lignes = {}
    for ep in epreuves:
        key = (ep.famille, ep.categorie)
        if key not in lignes:
            lignes[key] = {"famille": ep.famille, "categorie": ep.categorie,
                           "theorie": None, "pratique": None}
        lignes[key]["pratique"] = ep.obtenue
        if fam_session and ep.famille == fam_session:
            lignes[key]["theorie"] = theorie_famille

    # Principe du plus favorable : si un CACES est delivrable pour la categorie et que
    # la theorie du jour est en echec ou absente, on affiche "Dispense" (theorie couverte).
    for key, lg in lignes.items():
        if key in cat_couvertes and lg["theorie"] is not True:
            lg["theorie"] = "dispense"

    lignes_list = sorted(lignes.values(), key=lambda x: (x["famille"], x["categorie"]))

    return {"session": sess, "stagiaire": stag, "lignes": lignes_list, "caces": caces}


def _badge_epreuve(obt):
    if obt is True:
        return '<span style="color:#2e7d32;">&#10003; R&eacute;ussie</span>'
    if obt is False:
        return '<span style="color:#c62828;">&#10007; &Eacute;chec</span>'
    if obt == "dispense":
        return '<span style="color:#1565c0;">Dispense</span>'
    return '<span style="color:#999;">&mdash;</span>'


def _build_html(data, cfg):
    sess = data["session"]
    stag = data["stagiaire"]
    today = date.today()
    validite = today + timedelta(days=30)

    nom_org = _nom_organisme(cfg)
    logo = _logo_data(cfg)
    logo_html = ('<img src="%s" style="max-height:48px;">' % logo) if logo else (
        '<div style="font-size:22px; font-weight:bold; color:#2d2d2d;">NORYX</div>')

    nom_cand = "%s %s" % ((stag.nom or "").upper(), (stag.prenom or ""))
    ligne_naiss = []
    if getattr(stag, "date_naissance", None):
        ligne_naiss.append("N&eacute;(e) le %s" % _fmt_date(stag.date_naissance))
    if getattr(stag, "entreprise", None):
        ligne_naiss.append("Entreprise : %s" % _esc(stag.entreprise))
    sous_cand = " &mdash; ".join(ligne_naiss)

    rows = ""
    for lg in data["lignes"]:
        rows += (
            '<tr style="border-bottom:0.5px solid #eee;">'
            '<td style="padding:6px 4px;">%s %s</td>'
            '<td style="padding:6px 4px;">%s</td>'
            '<td style="padding:6px 4px;">%s</td>'
            '</tr>'
        ) % (_esc(lg["famille"]), _esc(lg["categorie"]),
             _badge_epreuve(lg["theorie"]), _badge_epreuve(lg["pratique"]))
    if not rows:
        rows = '<tr><td colspan="3" style="padding:8px; color:#999; font-style:italic;">Aucune &eacute;preuve enregistr&eacute;e.</td></tr>'

    caces_rows = ""
    for c in data["caces"]:
        opts = (" + options %s" % _esc(c.options_obtenues)) if c.options_obtenues else ""
        caces_rows += (
            '<div style="display:flex; justify-content:space-between; padding:5px 0; '
            'font-size:13px; border-bottom:0.5px solid #f0d0d0;">'
            '<span style="font-weight:bold;">%s cat&eacute;gorie %s%s</span>'
            '<span style="color:#666; font-size:12px;">&eacute;ch&eacute;ance : %s</span>'
            '</div>'
        ) % (_esc(c.famille), _esc(c.categorie), opts, _fmt_date(c.date_echeance))
    if not caces_rows:
        caces_bloc = ('<div style="color:#999; font-style:italic; font-size:13px;">'
                      'Aucun CACES&reg; d&eacute;livrable en l\'&eacute;tat.</div>')
    else:
        caces_bloc = ('<div style="border:1px solid #cc0000; border-radius:8px; padding:10px 14px;">%s</div>'
                      % caces_rows)

    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 1.6cm; }}
body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color:#222; font-size:13px; }}
.entete {{ display:flex; justify-content:space-between; align-items:flex-start;
  border-bottom:2px solid #2d2d2d; padding-bottom:12px; margin-bottom:16px; }}
.titre {{ text-align:center; margin-bottom:14px; }}
.titre .t {{ font-size:17px; font-weight:bold; color:#cc0000; }}
.titre .st {{ font-size:12px; color:#888; font-style:italic; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; font-size:11px; color:#666; border-bottom:1px solid #ddd; padding:5px 4px; }}
.sect {{ font-size:13px; font-weight:bold; color:#2d2d2d; margin:16px 0 6px; }}
.cand {{ background:#f5f6fa; border-radius:8px; padding:10px 14px; margin:12px 0; }}
.validite {{ background:#fff8e1; border-radius:8px; padding:10px 14px; margin:16px 0;
  font-size:12px; color:#5d4037; line-height:1.5; }}
.sign {{ display:flex; justify-content:space-between; align-items:flex-end; margin-top:26px; font-size:12px; color:#444; }}
</style></head><body>

  <div class="entete">
    <div>{logo_html}<div style="font-size:11px; color:#666; margin-top:4px;">{nom_org} &mdash; OTC CACES&reg;</div></div>
    <div style="text-align:right; font-size:11px; color:#666;">Session {ref}<br>Le {today}</div>
  </div>

  <div class="titre">
    <div class="t">Attestation de r&eacute;ussite provisoire</div>
    <div class="st">Document d'attente &mdash; ne remplace pas la carte CACES&reg;</div>
  </div>

  <div class="cand">
    <div style="font-size:11px; color:#666;">D&eacute;livr&eacute;e &agrave;</div>
    <div style="font-weight:bold; font-size:15px;">{nom_cand}</div>
    <div style="color:#666; font-size:12px;">{sous_cand}</div>
  </div>

  <div class="sect">&Eacute;preuves pass&eacute;es sur la session</div>
  <table>
    <thead><tr><th>Cat&eacute;gorie</th><th>Th&eacute;orie</th><th>Pratique</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <div class="sect">CACES&reg; pouvant &ecirc;tre d&eacute;livr&eacute;s
    <span style="font-weight:normal; color:#888; font-size:11px;">&mdash; sous r&eacute;serve de confirmation</span></div>
  {caces_bloc}

  <div class="validite">
    <strong>Validit&eacute; :</strong> le pr&eacute;sent document est valable <strong>un mois</strong>
    &agrave; compter de sa date d'&eacute;mission (soit jusqu'au <strong>{validite}</strong>), dans l'attente de la
    d&eacute;livrance de la ou des cartes CACES&reg; correspondantes. Il atteste de la r&eacute;ussite aux
    &eacute;preuves mais ne constitue pas le certificat officiel.
  </div>

  <div class="sign">
    <div>Fait le {today}</div>
    <div style="text-align:center;">
      <div style="margin-bottom:4px;">{signature_img}</div>
      <div style="border-top:0.5px solid #999; padding-top:3px; min-width:200px;">{signataire}</div>
    </div>
  </div>

</body></html>""".format(
        logo_html=logo_html, nom_org=_esc(nom_org), ref=_esc(_ref_session(sess)),
        today=_fmt_date(today), nom_cand=_esc(nom_cand), sous_cand=sous_cand,
        rows=rows, caces_bloc=caces_bloc, validite=_fmt_date(validite),
        signature_img=_signature_img(cfg), signataire=_signataire(cfg),
    )


def generer_attestation_reussite(session_id, stagiaire_id, db):
    data = _collecter(session_id, stagiaire_id, db)
    if not data:
        return None
    cfg = _get_cfg(db)
    html = _build_html(data, cfg)
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()
