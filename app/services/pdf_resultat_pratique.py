"""
app/services/pdf_resultat_pratique.py

PDF de résultat d'évaluation PRATIQUE (généré à la volée, jamais stocké).
- en-tête candidat + organisme (charte NORYX anthracite/rouge)
- verdict global (catégorie acquise ou non)
- détail par bloc (base + options) : note globale, notes par thème, points d'évaluation
- signature du testeur (base64), observations, justification d'écart
NB : les critères d'évaluation NE figurent PAS sur ce PDF (décision produit).

NORYX assiste : ce PDF est une vue des données validées. La responsabilité
de la décision reste humaine (testeur habilité, signature).
"""

from io import BytesIO
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.models.config_organisme import ConfigOrganisme
from app.models.stagiaire import Stagiaire
from app.models.grille_pratique import SaisiePratique
from app.models.session import Session as SessionModel
from app.models.jour_test import JourTest
from app.services.calcul_pratique import calculer_saisie

ANTHRACITE = "#2d2d2d"
ROUGE = "#cc0000"


# ── Helpers config ───────────────────────────────────────────────────────────

def _get_logo_data(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    if cfg and cfg.logo_base64 and cfg.logo_nom:
        ext = cfg.logo_nom.rsplit('.', 1)[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        return f"data:{mime};base64,{cfg.logo_base64}"
    return ""


def _get_nom_organisme(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    return cfg.nom_organisme if cfg and cfg.nom_organisme else "PEPCI Formation"


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _fmt(v) -> str:
    """Formate une note : entier si entier, sinon 1 décimale."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f == int(f) else f"{f:.1f}"


# ── Collecte ─────────────────────────────────────────────────────────────────

def _collecter(saisie: SaisiePratique, db: DBSession) -> dict:
    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == saisie.stagiaire_id).first()
    jour = db.query(JourTest).filter(JourTest.id == saisie.jour_test_id).first()
    session = None
    if jour:
        session = db.query(SessionModel).filter(SessionModel.id == jour.session_id).first()
    calcul = calculer_saisie(saisie, db)
    return {"stagiaire": stagiaire, "jour": jour, "session": session, "calcul": calcul}


# ── Rendu d'un bloc (base ou option) ─────────────────────────────────────────

def _badge(ok: bool, label: str) -> str:
    if ok:
        return (f'<span class="badge ok">{_esc(label)}</span>')
    return (f'<span class="badge ko">{_esc(label)}</span>')


def _bloc_html(bloc: dict, est_base: bool, acquis: bool) -> str:
    titre = "Épreuve de base" if est_base else f"Option — {_esc(bloc.get('libelle') or bloc.get('code_option') or '')}"
    note_str = f"{_fmt(bloc['note_globale'])} / {_fmt(bloc['note_max'])}"
    seuil_str = f"seuil {_fmt(bloc['note_min'])}"
    verdict = _badge(acquis, "ACQUIS" if acquis else "NON ACQUIS")

    # Tableau des thèmes
    themes_rows = ""
    for th in bloc.get("themes", []):
        score = f"{_fmt(th['note'])} / {_fmt(th['bareme'])}"
        seuil = _fmt(th["seuil"])
        etat = _badge(th["ok"], "OK" if th["ok"] else "INSUFFISANT")
        themes_rows += (
            f"<tr>"
            f"<td class='lib'>{_esc(th['libelle'])}</td>"
            f"<td class='c'>{score}</td>"
            f"<td class='c'>{seuil}</td>"
            f"<td class='c'>{etat}</td>"
            f"</tr>\n"
        )

    # Tableau des points d'évaluation (regroupés par thème)
    pe_rows = ""
    for pe in bloc.get("points_evaluation", []):
        etat = _badge(pe["ok"], "OK" if pe["ok"] else "0 = échec")
        pe_rows += (
            f"<tr>"
            f"<td class='lib'>{_esc(pe['theme'])} — PE {_esc(pe['numero'])}</td>"
            f"<td class='c'>{_fmt(pe['note'])} / {_fmt(pe['bareme'])}</td>"
            f"<td class='c'>{etat}</td>"
            f"</tr>\n"
        )

    pe_section = ""
    if pe_rows:
        pe_section = f"""
        <div class="sub">Détail des points d'évaluation</div>
        <table class="grid">
          <thead><tr><th class="lib">Point d'évaluation</th><th class="c">Note</th><th class="c">État</th></tr></thead>
          <tbody>{pe_rows}</tbody>
        </table>"""

    return f"""
    <div class="bloc">
      <div class="bloc-head">
        <span class="bloc-titre">{_esc(titre)}</span>
        <span class="bloc-note">{note_str} <span class="seuil">({seuil_str})</span> {verdict}</span>
      </div>
      <div class="sub">Notes par thème</div>
      <table class="grid">
        <thead><tr><th class="lib">Thème</th><th class="c">Note</th><th class="c">Seuil</th><th class="c">État</th></tr></thead>
        <tbody>{themes_rows}</tbody>
      </table>
      {pe_section}
    </div>"""


# ── Construction HTML ────────────────────────────────────────────────────────

def _build_html(saisie: SaisiePratique, donnees: dict, nom_organisme: str, logo_data: str) -> str:
    stagiaire = donnees["stagiaire"]
    session = donnees["session"]
    calcul = donnees["calcul"]

    nom_candidat = f"{stagiaire.nom} {stagiaire.prenom}" if stagiaire else "Candidat inconnu"
    naissance = stagiaire.date_naissance.strftime("%d/%m/%Y") if stagiaire and stagiaire.date_naissance else "—"
    ref = (session.reference if session and getattr(session, "reference", None) else (f"Session {session.id}" if session else "—"))
    famille = session.famille if session and getattr(session, "famille", None) else "—"
    categorie = saisie.categorie or "—"
    date_val = saisie.date_validation.strftime("%d/%m/%Y à %H:%M") if saisie.date_validation else "—"

    acquise = bool(calcul.get("categorie_acquise"))
    verdict_label = "CATÉGORIE ACQUISE" if acquise else "CATÉGORIE NON ACQUISE"
    verdict_class = "ok" if acquise else "ko"

    logo_html = (f'<img src="{logo_data}" style="height:46px; max-width:140px; object-fit:contain;" alt="Logo" />'
                 if logo_data else "")

    # Blocs base + options
    blocs_html = ""
    if calcul.get("base"):
        blocs_html += _bloc_html(calcul["base"], True, calcul.get("base_reussie", False))
    for opt in calcul.get("options", []):
        blocs_html += _bloc_html(opt, False, opt.get("acquis", False))

    # Observations / justification
    obs_html = ""
    if saisie.observations:
        obs_html += f'<div class="note-block"><div class="nb-titre">Observations du testeur</div><div class="nb-corps">{_esc(saisie.observations)}</div></div>'
    if saisie.justification_ecart:
        obs_html += f'<div class="note-block warn"><div class="nb-titre">Justification (écart à la proposition système)</div><div class="nb-corps">{_esc(saisie.justification_ecart)}</div></div>'

    # Signature
    sig_html = ""
    if saisie.signature_testeur:
        sig_src = saisie.signature_testeur
        if not sig_src.startswith("data:"):
            sig_src = "data:image/png;base64," + sig_src
        sig_html = f'<img src="{_esc(sig_src)}" style="height:70px; max-width:240px; object-fit:contain;" alt="Signature" />'
    else:
        sig_html = '<span style="color:#999; font-style:italic;">Signature non disponible</span>'

    testeur_nom = saisie.testeur_nom or "—"

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><style>
  @page {{ size: A4; margin: 14mm 14mm 16mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; font-size: 11px; margin: 0; }}
  .head {{ display: flex; justify-content: space-between; align-items: center;
           border-bottom: 3px solid {ROUGE}; padding-bottom: 10px; margin-bottom: 14px; }}
  .head .org {{ font-size: 16px; font-weight: bold; color: {ANTHRACITE}; }}
  .head .org small {{ display:block; font-size:10px; font-weight:normal; color:#666; margin-top:2px; }}
  h1 {{ font-size: 15px; color: {ANTHRACITE}; margin: 0 0 12px; }}
  .candidat {{ background: #f6f7f9; border: 1px solid #e2e6ee; border-radius: 6px;
               padding: 10px 12px; margin-bottom: 14px; }}
  .candidat table {{ width: 100%; border-collapse: collapse; }}
  .candidat td {{ padding: 2px 6px; font-size: 11px; vertical-align: top; }}
  .candidat .k {{ color: #666; width: 130px; }}
  .candidat .v {{ font-weight: bold; color: {ANTHRACITE}; }}
  .verdict {{ text-align: center; padding: 12px; border-radius: 6px; margin-bottom: 16px;
              font-size: 16px; font-weight: bold; letter-spacing: 0.5px; }}
  .verdict.ok {{ background: #e8f5e9; color: #1b5e20; border: 2px solid #66bb6a; }}
  .verdict.ko {{ background: #fcebeb; color: #a32d2d; border: 2px solid #e57373; }}
  .bloc {{ margin-bottom: 16px; page-break-inside: avoid; }}
  .bloc-head {{ display: flex; justify-content: space-between; align-items: center;
                background: {ANTHRACITE}; color: #fff; padding: 6px 10px; border-radius: 5px 5px 0 0; }}
  .bloc-titre {{ font-weight: bold; font-size: 12px; }}
  .bloc-note {{ font-size: 11px; }}
  .bloc-note .seuil {{ color: #c9c9c9; font-size: 10px; }}
  .sub {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #888;
          margin: 8px 0 3px; }}
  table.grid {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
  table.grid th {{ background: #eef0f4; color: #444; text-align: left; padding: 4px 7px;
                   border: 1px solid #dfe3ea; font-size: 9px; text-transform: uppercase; }}
  table.grid td {{ padding: 4px 7px; border: 1px solid #e6e9ef; }}
  table.grid td.c, table.grid th.c {{ text-align: center; }}
  table.grid td.lib {{ width: 55%; }}
  .badge {{ display: inline-block; border-radius: 3px; padding: 1px 6px; font-size: 9px;
            font-weight: bold; }}
  .badge.ok {{ background: #e8f5e9; color: #1b5e20; border: 1px solid #66bb6a; }}
  .badge.ko {{ background: #fcebeb; color: #a32d2d; border: 1px solid #e57373; }}
  .note-block {{ border: 1px solid #e2e6ee; border-left: 3px solid {ANTHRACITE};
                 border-radius: 0 5px 5px 0; padding: 7px 10px; margin: 8px 0; }}
  .note-block.warn {{ border-left-color: {ROUGE}; }}
  .nb-titre {{ font-size: 9px; text-transform: uppercase; color: #888; margin-bottom: 3px; }}
  .nb-corps {{ font-size: 11px; color: #333; white-space: pre-wrap; }}
  .sig-zone {{ margin-top: 18px; border-top: 1px solid #e2e6ee; padding-top: 12px;
               display: flex; justify-content: space-between; align-items: flex-end; }}
  .sig-cert {{ font-size: 9px; color: #666; max-width: 60%; line-height: 1.4; }}
  .sig-box {{ text-align: center; }}
  .sig-box .lbl {{ font-size: 9px; color: #888; margin-bottom: 3px; }}
  .sig-box .nom {{ font-size: 10px; font-weight: bold; color: {ANTHRACITE}; margin-top: 3px; }}
  .footer {{ margin-top: 14px; border-top: 1px solid #eee; padding-top: 6px;
             font-size: 8px; color: #999; text-align: center; }}
</style></head><body>

  <div class="head">
    <div class="org">{_esc(nom_organisme)}<small>Organisme testeur certifié — Évaluation pratique CACES®</small></div>
    {logo_html}
  </div>

  <h1>Résultat d'évaluation pratique</h1>

  <div class="candidat">
    <table>
      <tr><td class="k">Candidat</td><td class="v">{_esc(nom_candidat)}</td>
          <td class="k">Né(e) le</td><td class="v">{_esc(naissance)}</td></tr>
      <tr><td class="k">Recommandation</td><td class="v">{_esc(famille)} — Catégorie {_esc(categorie)}</td>
          <td class="k">Session</td><td class="v">{_esc(ref)}</td></tr>
      <tr><td class="k">Date de validation</td><td class="v">{_esc(date_val)}</td>
          <td class="k">Testeur</td><td class="v">{_esc(testeur_nom)}</td></tr>
    </table>
  </div>

  <div class="verdict {verdict_class}">{_esc(verdict_label)}</div>

  {blocs_html}

  {obs_html}

  <div class="sig-zone">
    <div class="sig-cert">Je soussigné(e) {_esc(testeur_nom)}, testeur habilité, certifie avoir vérifié
      l'identité du candidat et atteste de la sincérité des résultats consignés.</div>
    <div class="sig-box">
      <div class="lbl">Signature du testeur</div>
      {sig_html}
      <div class="nom">{_esc(testeur_nom)}</div>
    </div>
  </div>

  <div class="footer">Document généré par NORYX le {datetime.now().strftime("%d/%m/%Y à %H:%M")} —
    {_esc(nom_organisme)}. NORYX assiste le testeur sans se substituer à lui : la responsabilité
    de la décision reste humaine et opposable en audit.</div>

</body></html>"""


# ── API publique ─────────────────────────────────────────────────────────────

def generer_pdf_resultat_pratique(saisie_id: int, db: DBSession) -> bytes:
    """Génère le PDF de résultat pratique pour une saisie VALIDÉE (à la volée)."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise ValueError(f"SaisiePratique {saisie_id} introuvable")
    if saisie.statut != "valide":
        raise ValueError(f"SaisiePratique {saisie_id} n'est pas validée (statut '{saisie.statut}')")

    nom_organisme = _get_nom_organisme(db)
    logo_data = _get_logo_data(db)
    donnees = _collecter(saisie, db)
    html = _build_html(saisie, donnees, nom_organisme, logo_data)

    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()
