"""
app/services/pdf_test_theorie.py
Génération PDF du sujet vierge et du corrigé du test théorique tiré (Phase 2 INRS).
"""

from io import BytesIO
from html import escape as _esc
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.models.grille_theorie import GrilleTheorie, ReponseGrille
from app.models.utilisations_themes import UtilisationTheme


def _get_logo_data(db: DBSession) -> str:
    from app.models.config_organisme import ConfigOrganisme
    cfg = db.query(ConfigOrganisme).first()
    if cfg and cfg.logo_base64 and cfg.logo_nom:
        ext = cfg.logo_nom.rsplit('.', 1)[-1].lower()
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
        return f"data:{mime};base64,{cfg.logo_base64}"
    return ""


def _get_nom_organisme(db: DBSession) -> str:
    from app.models.config_organisme import ConfigOrganisme
    cfg = db.query(ConfigOrganisme).first()
    return cfg.nom_organisme if cfg and cfg.nom_organisme else "PEPCI Formation"


def _construire_questions(session_id: int, famille: str, db: DBSession) -> dict:
    """
    Retourne {theme_int: [{"numero", "points", "texte", "image", "grille_numero", "reponse_correcte"}]}
    trié par thème puis numero_question.
    """
    tirages = (
        db.query(UtilisationTheme)
        .filter(UtilisationTheme.session_id == session_id, UtilisationTheme.famille == famille)
        .order_by(UtilisationTheme.theme)
        .all()
    )
    if not tirages:
        raise ValueError(f"Aucun tirage pour la session {session_id}")

    result = {}
    for ut in tirages:
        grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == ut.grille_id).first()
        questions = (
            db.query(ReponseGrille)
            .filter(ReponseGrille.grille_id == ut.grille_id, ReponseGrille.theme == ut.theme)
            .order_by(ReponseGrille.numero_question)
            .all()
        )
        result[ut.theme] = [
            {
                "numero": q.numero_question,
                "points": q.points,
                "texte": q.texte_question,
                "image": q.image_url,
                "grille_numero": grille.numero if grille else "?",
                "reponse_correcte": q.reponse_correcte,
            }
            for q in questions
        ]
    return result


def _build_html(
    session: Session,
    nom_organisme: str,
    logo_data: str,
    themes_questions: dict,
    avec_corrige: bool,
) -> str:
    famille = session.famille
    date_str = session.date_theorie.strftime('%d/%m/%Y') if session.date_theorie else "—"
    ref_str = session.reference or f"Session {session.id}"
    titre = f"Test théorique CACES® {famille}"
    type_doc = "CORRIGÉ" if avec_corrige else "SUJET VIERGE"

    accent_bg  = "#e8f5e9" if avec_corrige else "#e3f2fd"
    accent_fg  = "#1b5e20" if avec_corrige else "#0d47a1"
    accent_bd  = "#4caf50" if avec_corrige else "#1976d2"
    correct_fg = "#1b5e20"

    logo_html = (
        f'<img src="{logo_data}" style="height:44px; max-width:130px; object-fit:contain;" alt="Logo" />'
        if logo_data else ""
    )

    themes_html = ""
    for theme_num in sorted(themes_questions.keys()):
        questions = themes_questions[theme_num]
        grille_num = questions[0]["grille_numero"] if questions else "?"

        rows = ""
        for q in questions:
            texte_html = _esc(q["texte"]) if q["texte"] else ""
            image_html = ""
            if q["image"]:
                image_html = (
                    f'<img src="{_esc(q["image"])}" '
                    f'style="max-height:90px; max-width:220px; display:block; margin-top:4px;" />'
                )

            if avec_corrige:
                vrai_cell = (
                    f'<span style="color:{correct_fg}; font-size:14px; font-weight:bold;">✓</span>'
                    if q["reponse_correcte"]
                    else '<span style="color:#bbb;">—</span>'
                )
                faux_cell = (
                    f'<span style="color:{correct_fg}; font-size:14px; font-weight:bold;">✓</span>'
                    if not q["reponse_correcte"]
                    else '<span style="color:#bbb;">—</span>'
                )
            else:
                vrai_cell = '<span class="case-reponse"></span>'
                faux_cell = '<span class="case-reponse"></span>'

            pts_fmt = f"{q['points']:.1f}" if q['points'] != int(q['points']) else str(int(q['points']))

            rows += (
                f"<tr>"
                f"<td class='num'>{q['numero']}</td>"
                f"<td class='enonce'>{texte_html}{image_html}</td>"
                f"<td class='pts'>{pts_fmt}</td>"
                f"<td class='rep'>{vrai_cell}</td>"
                f"<td class='rep'>{faux_cell}</td>"
                f"</tr>\n"
            )

        themes_html += f"""
<div class="theme-block">
  <div class="theme-header">Thème {theme_num} &nbsp;—&nbsp; Grille n°{grille_num}</div>
  <table class="q-table">
    <thead>
      <tr>
        <th class="num">N°</th>
        <th style="text-align:left;">Question</th>
        <th class="pts">Pts</th>
        <th class="rep">VRAI</th>
        <th class="rep">FAUX</th>
      </tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</div>
"""

    confidential_note = (
        '<div class="confidential">⚠ Document confidentiel — corrigé réservé au formateur — ne pas diffuser</div>'
        if avec_corrige else ""
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 16mm 12mm 14mm 12mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10.5px; color: #1a1a1a; margin: 0; }}

  .doc-header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #1a237e; padding-bottom: 8px; margin-bottom: 14px; }}
  .doc-header-left {{ display: flex; align-items: center; gap: 12px; }}
  h1 {{ font-size: 14px; color: #1a237e; margin: 0 0 3px 0; }}
  .type-badge {{
    display: inline-block;
    background: {accent_bg}; color: {accent_fg}; border: 1px solid {accent_bd};
    border-radius: 3px; padding: 1px 7px; font-size: 9px; font-weight: bold;
    vertical-align: middle; margin-left: 6px;
  }}
  .doc-meta {{ text-align: right; font-size: 9.5px; color: #555; line-height: 1.6; }}

  .theme-block {{ margin-bottom: 16px; break-inside: avoid; }}
  .theme-header {{
    background: #1a237e; color: white; font-weight: bold; font-size: 10.5px;
    padding: 4px 10px; border-radius: 3px 3px 0 0;
  }}

  .q-table {{ width: 100%; border-collapse: collapse; border: 1px solid #ccc; }}
  .q-table th {{ background: #f0f2f7; padding: 4px 7px; font-size: 9.5px; border: 1px solid #ccc; font-weight: bold; }}
  .q-table td {{ padding: 5px 7px; border: 1px solid #ddd; font-size: 10px; vertical-align: middle; }}
  .q-table tr:nth-child(even) td {{ background: #fafafa; }}

  td.num, th.num {{ width: 28px; text-align: center; }}
  td.pts, th.pts {{ width: 32px; text-align: center; }}
  td.rep, th.rep {{ width: 52px; text-align: center; }}
  td.enonce {{ text-align: left; }}
  td.num {{ vertical-align: middle; font-weight: bold; color: #555; }}

  .case-reponse {{
    display: inline-block;
    width: 16px; height: 16px;
    border: 1.5px solid #555;
    border-radius: 2px;
    vertical-align: middle;
  }}

  .confidential {{
    background: #fff3e0; color: #bf360c; border: 1px solid #ef6c00;
    border-radius: 4px; padding: 4px 10px; font-size: 9px; font-weight: bold;
    margin-bottom: 12px; text-align: center;
  }}
  .footer {{
    text-align: center; font-size: 8.5px; color: #999;
    margin-top: 16px; border-top: 1px solid #eee; padding-top: 5px;
  }}
</style>
</head>
<body>

<div class="doc-header">
  <div class="doc-header-left">
    {logo_html}
    <div>
      <h1>{_esc(titre)} <span class="type-badge">{type_doc}</span></h1>
      <div style="font-size:9.5px; color:#666;">{_esc(nom_organisme)}</div>
    </div>
  </div>
  <div class="doc-meta">
    <div><strong>Date :</strong> {date_str}</div>
    <div><strong>Réf. :</strong> {_esc(ref_str)}</div>
    <div><strong>Famille :</strong> {_esc(famille)}</div>
  </div>
</div>

{confidential_note}
{themes_html}

<div class="footer">
  Document généré automatiquement &mdash; {_esc(nom_organisme)} &mdash; CACES® {_esc(famille)} &mdash; {type_doc}
</div>

</body>
</html>"""


def _html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()


def generer_sujet_vierge(session_id: int, db: DBSession) -> bytes:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} introuvable")
    themes_questions = _construire_questions(session_id, session.famille, db)
    html = _build_html(session, _get_nom_organisme(db), _get_logo_data(db), themes_questions, avec_corrige=False)
    return _html_to_pdf(html)


def generer_corrige(session_id: int, db: DBSession) -> bytes:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} introuvable")
    themes_questions = _construire_questions(session_id, session.famille, db)
    html = _build_html(session, _get_nom_organisme(db), _get_logo_data(db), themes_questions, avec_corrige=True)
    return _html_to_pdf(html)
