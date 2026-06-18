"""
app/services/pdf_detail_theorie.py
Génération PDF du détail du test théorique numérique d'un candidat :
réponses du candidat + scores par thème. SANS bonnes réponses (le corrigé est séparé).
"""

import json
from io import BytesIO
from html import escape as _esc
from sqlalchemy.orm import Session as DBSession

from app.models.jour_test import ResultatTheorie
from app.models.session import Session
from app.models.stagiaire import Stagiaire
from app.models.grille_theorie import ReponseGrille
from app.models.utilisations_themes import UtilisationTheme
from app.models.config_organisme import ConfigOrganisme


_THEME_NOMS = {
    "1": "Connaissances générales",
    "2": "Technologie et stabilité",
    "3": "Exploitation",
    "4": "Circulation",
    "5": "Fin de poste",
}


# ── Helpers config ──────────────────────────────────────────────────────────

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


# ── Collecte des données ────────────────────────────────────────────────────

def _collecter_donnees(rt: ResultatTheorie, db: DBSession) -> dict:
    """
    Retourne {
      "stagiaire": Stagiaire,
      "session":   Session,
      "themes": {
          "1": {
              "nom": str,
              "questions": [{"numero", "texte", "reponse_candidat": bool|None,
                             "correcte": bool, "points": float}],
              "note": float,
              "max":  float,
              "ok":   bool,   # note >= max/2
          }, ...
      }
    }
    Même logique que page_detail_theorie (main.py:1910-1948), pas de N+1.
    Clé composite {theme}_{numero} identique au scoring numérique.
    """
    session   = db.query(Session).filter(Session.id == rt.session_id).first()
    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == rt.stagiaire_id).first()
    reponses  = json.loads(rt.reponses_json) if rt.reponses_json else {}

    tirages = (
        db.query(UtilisationTheme)
        .filter(
            UtilisationTheme.session_id == rt.session_id,
            UtilisationTheme.famille    == session.famille,
        )
        .order_by(UtilisationTheme.theme)
        .all()
    )

    themes: dict[str, dict] = {}
    for ut in tirages:
        questions_db = (
            db.query(ReponseGrille)
            .filter(
                ReponseGrille.grille_id == ut.grille_id,
                ReponseGrille.theme     == ut.theme,
            )
            .order_by(ReponseGrille.numero_question)
            .all()
        )
        t_str     = str(ut.theme)
        note      = 0.0
        max_theme = 0.0
        qs        = []
        for q in questions_db:
            key          = f"{ut.theme}_{q.numero_question}"
            rep_candidat = reponses.get(key)          # bool | None
            correcte     = rep_candidat is not None and rep_candidat == q.reponse_correcte
            if correcte:
                note += q.points
            max_theme += q.points
            qs.append({
                "numero":          q.numero_question,
                "texte":           q.texte_question or "",
                "reponse_candidat": rep_candidat,
                "correcte":        correcte,
                "points":          q.points,
            })
        themes[t_str] = {
            "nom":       _THEME_NOMS.get(t_str, f"Thème {t_str}"),
            "questions": qs,
            "note":      round(note, 1),
            "max":       round(max_theme, 1),
            "ok":        note >= (max_theme / 2),
        }

    return {"stagiaire": stagiaire, "session": session, "themes": themes}


# ── Construction HTML ───────────────────────────────────────────────────────

def _build_html(
    rt:            ResultatTheorie,
    donnees:       dict,
    nom_organisme: str,
    logo_data:     str,
) -> str:
    stagiaire    = donnees["stagiaire"]
    session      = donnees["session"]
    themes       = donnees["themes"]

    nom_candidat = f"{stagiaire.nom} {stagiaire.prenom}" if stagiaire else "Candidat inconnu"
    ref_str      = (session.reference or f"Session {session.id}") if session else "—"
    date_str     = session.date_theorie.strftime("%d/%m/%Y") if session and session.date_theorie else "—"
    famille      = session.famille if session else "—"

    note_label   = f"{int(rt.note_totale)}/100" if rt.note_totale is not None else "—/100"
    if rt.obtenue:
        badge_html = (
            f'<span style="background:#e8f5e9; color:#1b5e20; border:1px solid #4caf50; '
            f'border-radius:3px; padding:1px 8px; font-size:10px; font-weight:bold;">'
            f'RÉUSSI — {note_label}</span>'
        )
    else:
        badge_html = (
            f'<span style="background:#ffebee; color:#b71c1c; border:1px solid #ef9a9a; '
            f'border-radius:3px; padding:1px 8px; font-size:10px; font-weight:bold;">'
            f'ÉCHEC — {note_label}</span>'
        )

    logo_html = (
        f'<img src="{logo_data}" style="height:44px; max-width:130px; object-fit:contain;" alt="Logo" />'
        if logo_data else ""
    )

    # ── Blocs thèmes ──
    themes_html = ""
    for t_str in sorted(themes.keys()):
        th    = themes[t_str]
        score = f"{int(th['note'])}/{int(th['max'])}"
        if th["ok"]:
            score_badge = (
                f'<span style="background:#e8f5e9; color:#1b5e20; border:1px solid #4caf50; '
                f'border-radius:3px; padding:1px 6px; font-size:9px; font-weight:bold;">'
                f'{score} ✅</span>'
            )
        else:
            score_badge = (
                f'<span style="background:#ffebee; color:#b71c1c; border:1px solid #ef9a9a; '
                f'border-radius:3px; padding:1px 6px; font-size:9px; font-weight:bold;">'
                f'{score} ❌</span>'
            )

        rows = ""
        for q in th["questions"]:
            bg = "#f1f8e9" if q["correcte"] else "#ffebee"
            if q["reponse_candidat"] is None:
                rep_html = '<span style="color:#888;">—</span>'
            elif q["reponse_candidat"]:
                rep_html = (
                    '<span style="background:#e3f2fd; color:#0d47a1; border:1px solid #90caf9; '
                    'border-radius:3px; padding:1px 6px; font-size:9px; font-weight:bold;">VRAI</span>'
                )
            else:
                rep_html = (
                    '<span style="background:#fff3e0; color:#e65100; border:1px solid #ffcc80; '
                    'border-radius:3px; padding:1px 6px; font-size:9px; font-weight:bold;">FAUX</span>'
                )

            res_html = (
                '<span style="font-weight:bold; color:#1b5e20;">1</span>'
                if q["correcte"] else
                '<span style="font-weight:bold; color:#b71c1c;">0</span>'
            )
            pts_fmt  = f"{q['points']:.1f}" if q['points'] != int(q['points']) else str(int(q['points']))

            rows += (
                f"<tr style='background:{bg};'>"
                f"<td class='num'>{q['numero']}</td>"
                f"<td class='enonce'>{_esc(q['texte'])}</td>"
                f"<td class='pts'>{pts_fmt}</td>"
                f"<td class='rep'>{rep_html}</td>"
                f"<td class='res'>{res_html}</td>"
                f"</tr>\n"
            )

        themes_html += f"""
<div class="theme-block">
  <div class="theme-header">
    <span>Thème {t_str} &nbsp;—&nbsp; {_esc(th['nom'])}</span>
    {score_badge}
  </div>
  <table class="q-table">
    <thead>
      <tr>
        <th class="num">N°</th>
        <th style="text-align:left;">Question</th>
        <th class="pts">Pts</th>
        <th class="rep">Réponse</th>
        <th class="res">Résultat</th>
      </tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 16mm 12mm 14mm 12mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10.5px; color: #1a1a1a; margin: 0; }}

  .doc-header {{
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 2px solid #1a237e; padding-bottom: 8px; margin-bottom: 14px;
  }}
  .doc-header-left {{ display: flex; align-items: center; gap: 12px; }}
  h1 {{ font-size: 15px; color: #1a237e; margin: 0 0 3px 0; }}
  .doc-meta {{ text-align: right; font-size: 9.5px; color: #555; line-height: 1.6; }}

  .theme-block {{ margin-bottom: 14px; break-inside: avoid; }}
  .theme-header {{
    background: #1a237e; color: white; font-weight: bold; font-size: 10.5px;
    padding: 4px 10px; border-radius: 3px 3px 0 0;
    display: flex; justify-content: space-between; align-items: center;
  }}

  .q-table {{ width: 100%; border-collapse: collapse; border: 1px solid #ccc; }}
  .q-table th {{ background: #f0f2f7; padding: 4px 7px; font-size: 9.5px; border: 1px solid #ccc; font-weight: bold; }}
  .q-table td {{ padding: 4px 7px; border: 1px solid #ddd; font-size: 10px; vertical-align: middle; }}
  .q-table tr:nth-child(even) td {{ background: rgba(0,0,0,.018); }}

  td.num, th.num {{ width: 28px; text-align: center; }}
  td.pts, th.pts {{ width: 32px; text-align: center; }}
  td.rep, th.rep {{ width: 72px; text-align: center; }}
  td.res, th.res {{ width: 38px; text-align: center; }}
  td.enonce {{ text-align: left; }}
  td.num {{ font-weight: bold; color: #555; }}

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
      <h1>{_esc(nom_candidat)}</h1>
      <div style="margin-top:3px;">{badge_html}</div>
      <div style="font-size:9px; color:#888; margin-top:3px;">{_esc(nom_organisme)}</div>
    </div>
  </div>
  <div class="doc-meta">
    <div><strong>Session :</strong> {_esc(ref_str)}</div>
    <div><strong>Date :</strong> {date_str}</div>
    <div><strong>Famille :</strong> {_esc(famille)}</div>
  </div>
</div>

{themes_html}

<div class="footer">
  Détail test théorique CACES® &mdash; {_esc(nom_candidat)} &mdash; {_esc(ref_str)} &mdash; {_esc(nom_organisme)}
</div>

</body>
</html>"""


# ── Point d'entrée public ───────────────────────────────────────────────────

def generer_pdf_detail_theorie(rt_id: int, db: DBSession) -> bytes:
    """
    Génère le PDF du détail du test numérique d'un candidat (réponses + scores).
    Prend l'id du ResultatTheorie (mode='numerique' avec reponses_json renseigné).
    Ne contient PAS les bonnes réponses — le corrigé est un document séparé.
    """
    rt = db.query(ResultatTheorie).filter(ResultatTheorie.id == rt_id).first()
    if not rt:
        raise ValueError(f"ResultatTheorie {rt_id} introuvable")
    if rt.mode != "numerique":
        raise ValueError(f"ResultatTheorie {rt_id} est en mode '{rt.mode}', pas 'numerique'")
    if not rt.reponses_json:
        raise ValueError(f"ResultatTheorie {rt_id} n'a pas de reponses_json (test non soumis ?)")

    nom_organisme = _get_nom_organisme(db)
    logo_data     = _get_logo_data(db)
    donnees       = _collecter_donnees(rt, db)
    html          = _build_html(rt, donnees, nom_organisme, logo_data)

    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()
