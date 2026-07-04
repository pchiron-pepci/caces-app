"""
app/services/pdf_fiche_reco.py

PDF de la fiche de recommandation de formation (généré à la volée).
Reprend le calcul à jour (calculer_fiche_reco) fusionné avec les saisies testeur
stockées (durées ajustées, cases, autres précisions).

C'est une preuve de recommandation : le PDF reflète l'état actuel au moment de la
génération. Pas de versionnement. NORYX assiste, la responsabilité reste humaine.
"""

import json
from io import BytesIO
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.models.config_organisme import ConfigOrganisme
from app.models.fiche_recommandation import FicheRecommandation
from app.services.calcul_fiche_reco import calculer_fiche_reco, _fmt_heures

ANTHRACITE = "#2d2d2d"
ROUGE = "#cc0000"


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


def _get_num_inrs(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    for attr in ("numero_inrs", "num_inrs", "numero_enregistrement", "numero_otc"):
        v = getattr(cfg, attr, None) if cfg else None
        if v:
            return str(v)
    return ""


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _bloc_theorie(th, duree_label):
    themes = "".join("<li>" + _esc(t["libelle"]) + "</li>" for t in th.get("themes_echoues", []))
    return f"""
    <div class="bloc">
      <div class="bloc-head">Épreuve théorique — non obtenue ({_esc(th.get('note_totale'))}/100)</div>
      <div class="bloc-body">
        <div class="sub">Thèmes à retravailler :</div>
        <ul>{themes or '<li>—</li>'}</ul>
        <div class="duree">Durée de formation recommandée : <strong>{_esc(duree_label)}</strong></div>
      </div>
    </div>"""


def _bloc_pratique(p, duree_label):
    blocs = ""
    for tb in p.get("themes_blocs", []):
        lignes = ""
        if tb.get("moyenne_insuffisante"):
            lignes += '<div class="moy">Moyenne du thème insuffisante</div>'
        for pe in tb.get("pe_zero", []):
            lignes += f'<li class="zero">{_esc(pe["libelle"])} — 0/{_esc(pe["bareme"])} (note éliminatoire)</li>'
        for pe in tb.get("pe_sous_moyenne", []):
            lignes += f'<li class="sous">{_esc(pe["libelle"])} — {_esc(pe["note"])}/{_esc(pe["bareme"])} (sous la moyenne)</li>'
        blocs += f'<div class="theme"><div class="theme-titre">{_esc(tb["theme"])}</div><ul>{lignes or "<li>—</li>"}</ul></div>'

    elim = ""
    if p.get("fautes_eliminatoires"):
        items = "".join("<li>" + _esc(f) + "</li>" for f in p["fautes_eliminatoires"])
        elim = f'<div class="elim"><div class="elim-titre">Faute(s) éliminatoire(s) :</div><ul>{items}</ul></div>'

    opt = ""
    if p.get("options_a_repasser"):
        libs = ", ".join(_esc(o["libelle"]) for o in p["options_a_repasser"])
        opt = f'<div class="opt">Catégorie obtenue, mais option(s) à repasser : {libs}</div>'

    temps = ""
    if p.get("temps_blocs"):
        lignes_t = ""
        for tb in p["temps_blocs"]:
            if tb["niveau"] == "eliminatoire":
                etiq = "temps éliminatoire (&gt; 130%)"
            else:
                etiq = "à améliorer (100–130%)"
            lignes_t += (
                '<li><strong>' + _esc(tb["libelle"]) + '</strong> — réalisé '
                + str(tb["pct"]) + '% du temps de référence : ' + etiq
                + ' &rarr; ' + _esc(tb["duree_label"]) + '</li>'
            )
        temps = ('<div class="temps"><div class="temps-titre">Maîtrise du temps :</div>'
                 '<ul>' + lignes_t + '</ul></div>')

    return f"""
    <div class="bloc">
      <div class="bloc-head">Pratique catégorie {_esc(p['categorie'])} — non obtenue</div>
      <div class="bloc-body">
        <div class="sub">Thèmes à retravailler ({p.get('nb_themes', 0)}) :</div>
        {blocs or '<div>—</div>'}
        {elim}
        {opt}
        {temps}
        <div class="duree">Durée de formation recommandée : <strong>{_esc(duree_label)}</strong></div>
      </div>
    </div>"""


def generer_pdf_fiche_reco(session_id: int, stagiaire_id: int, db: DBSession) -> bytes:
    calcul = calculer_fiche_reco(session_id, stagiaire_id, db)
    fiche = db.query(FicheRecommandation).filter(
        FicheRecommandation.session_id == session_id,
        FicheRecommandation.stagiaire_id == stagiaire_id,
    ).order_by(FicheRecommandation.id.desc()).first()

    # saisies stockées (durées ajustées + cases + texte)
    saisies = {}
    if fiche and fiche.saisies_json:
        try:
            saisies = json.loads(fiche.saisies_json)
        except (ValueError, TypeError):
            saisies = {}

    nom_org = _get_nom_organisme(db)
    num_inrs = _get_num_inrs(db)
    logo = _get_logo_data(db)
    c = calcul.get("candidat", {})
    sess = calcul.get("session", {})
    nom = f"{c.get('nom', '')} {c.get('prenom', '')}".strip()
    naissance = c.get("date_naissance") or "—"

    def _fdate(iso):
        if not iso:
            return None
        try:
            return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return iso

    # bloc session : référence, famille, dates, catégories échouées
    ref = sess.get("reference") or "—"
    famille = sess.get("famille") or "—"
    dates = []
    if sess.get("date_theorie"):
        dates.append("théorie le " + _fdate(sess["date_theorie"]))
    if sess.get("date_pratique_debut"):
        dp = _fdate(sess["date_pratique_debut"])
        if sess.get("date_pratique_fin") and sess["date_pratique_fin"] != sess["date_pratique_debut"]:
            dp += " au " + _fdate(sess["date_pratique_fin"])
        dates.append("pratique le " + dp)
    dates_str = ", ".join(dates) if dates else "—"
    cats = sess.get("categories_echouees") or []
    cats_str = ", ".join(_esc(x) for x in cats) if cats else "—"

    logo_html = (f'<img src="{logo}" style="height:46px; max-width:150px; object-fit:contain;" alt="Logo"/>'
                 if logo else "")

    blocs_html = ""
    # théorie
    if calcul.get("theorie_echec"):
        th = calcul["theorie_echec"]
        dlabel = _fmt_heures(saisies.get("theorie")) if saisies.get("theorie") else th.get("duree_label")
        blocs_html += _bloc_theorie(th, dlabel)
    # pratiques
    for p in calcul.get("pratiques_echec", []):
        sp = (saisies.get("pratiques") or {}).get(p["categorie"]) or {}
        dlabel = _fmt_heures(sp.get("duree_heures")) if sp.get("duree_heures") else p.get("duree_label")
        blocs_html += _bloc_pratique(p, dlabel)

    # total (saisi si présent, sinon calculé)
    total_label = saisies.get("total_label") or calcul.get("duree_totale_label") or "—"

    # cases testeur
    cases = []
    if fiche and fiche.fraude_theorie:
        cases.append("Fraude ou tentative de fraude pendant l'épreuve théorique")
    if fiche and fiche.difficultes_langue:
        cases.append("Importantes difficultés de compréhension de la langue française")
    if fiche and fiche.comportement_dangereux:
        cases.append("Comportement dangereux incompatible avec la conduite en sécurité")
    cases_html = ""
    if cases:
        cases_html = '<div class="cases"><div class="sub">Précisions du testeur :</div><ul>' \
            + "".join("<li>" + _esc(x) + "</li>" for x in cases) + "</ul></div>"
    autres = (fiche.autres_precisions if fiche and fiche.autres_precisions else "") or calcul.get("observations_testeur", "")
    autres_html = ""
    if autres:
        autres_html = f'<div class="cases"><div class="sub">Autres précisions :</div><div class="autres">{_esc(autres)}</div></div>'

    inrs_html = f' — N° {_esc(num_inrs)}' if num_inrs else ""

    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><style>
  @page {{ size: A4; margin: 14mm 14mm 20mm 14mm;
    @bottom-center {{ content: element(pieddepage); }}
    @bottom-right {{ content: "Page " counter(page) "/" counter(pages); font-size: 8px; color: #999; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; font-size: 11px; margin: 0; }}
  .head {{ display: flex; justify-content: space-between; align-items: center;
           border-bottom: 3px solid {ROUGE}; padding-bottom: 10px; margin-bottom: 14px; }}
  .head .org {{ font-size: 16px; font-weight: bold; color: {ANTHRACITE}; }}
  .head .org small {{ display:block; font-size:10px; font-weight:normal; color:#666; margin-top:2px; }}
  h1 {{ font-size: 15px; color: {ANTHRACITE}; margin: 0 0 12px; text-align:center; }}
  .candidat {{ background: #f6f7f9; border: 1px solid #e2e6ee; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px; }}
  .candidat .v {{ font-weight: bold; color: {ANTHRACITE}; }}
  .session {{ background: #fff; border: 1px solid #e2e6ee; border-radius: 6px; padding: 8px 12px;
              margin-bottom: 12px; font-size: 11px; line-height: 1.6; }}
  .session .cats {{ font-weight: bold; color: {ROUGE}; }}
  .validite {{ background: #eef4fb; border: 1px solid #bcd; border-radius: 6px; padding: 8px 12px;
               margin-bottom: 16px; font-size: 10px; color: #345; line-height: 1.5; }}
  .validite p {{ margin: 3px 0; }}
  .validite .vt {{ font-weight: bold; color: {ANTHRACITE}; margin-top: 6px; font-size: 11px; }}
  .validite .vt:first-child {{ margin-top: 0; }}
  .bloc {{ border: 1px solid #e57373; border-radius: 6px; margin-bottom: 12px; page-break-inside: avoid; }}
  .bloc-head {{ background: #fcebeb; color: #a32d2d; padding: 6px 12px; font-weight: bold; font-size: 12px; border-radius: 6px 6px 0 0; }}
  .bloc-body {{ padding: 8px 12px; }}
  .sub {{ font-size: 10px; color: #666; margin: 4px 0; text-transform: uppercase; letter-spacing: 0.3px; }}
  .theme {{ margin-bottom: 6px; }}
  .theme-titre {{ font-weight: bold; font-size: 11px; color: {ANTHRACITE}; }}
  ul {{ margin: 3px 0 6px 18px; padding: 0; }}
  li {{ font-size: 11px; margin: 1px 0; }}
  li.zero {{ color: #a32d2d; }}
  li.sous {{ color: #7a5a12; }}
  .moy {{ font-size: 10px; color: #555; }}
  .elim {{ background: #fcebeb; border: 1px solid #e57373; border-radius: 5px; padding: 5px 9px; margin: 6px 0; }}
  .elim-titre {{ font-weight: bold; color: #a32d2d; font-size: 11px; }}
  .opt {{ background: #faeeda; border-radius: 5px; padding: 5px 9px; margin: 6px 0; font-size: 11px; color: #7a5a12; }}
  .duree {{ margin-top: 6px; font-size: 12px; color: {ANTHRACITE}; }}
  .temps {{ margin-top: 6px; background: #fff8ef; border: 0.5px solid #f0d9b0;
           border-radius: 5px; padding: 6px 10px; }}
  .temps-titre {{ font-weight: bold; font-size: 11px; color: #b26a00; }}
  .temps ul {{ margin: 4px 0 0; padding-left: 16px; font-size: 11px; color: #444; }}
  .total {{ background: {ANTHRACITE}; color: #fff; border-radius: 6px; padding: 10px 14px; margin: 10px 0 16px;
            display: flex; justify-content: space-between; font-size: 14px; font-weight: bold; }}
  .cases {{ margin-bottom: 10px; }}
  .autres {{ white-space: pre-wrap; font-size: 11px; }}
  .footer {{ margin-top: 16px; border-top: 1px solid #eee; padding-top: 8px; font-size: 9px; color: #777; line-height: 1.5; }}
  .cnam {{ margin-top: 16px; background: #f4f4f2; border: 1px solid #d8d8d2; border-radius: 6px;
           padding: 10px 12px; font-size: 9.5px; color: #444; line-height: 1.5; page-break-inside: avoid; }}
  .cnam-t {{ font-weight: bold; color: {ANTHRACITE}; text-transform: uppercase; letter-spacing: 0.4px;
             font-size: 9.5px; margin-bottom: 4px; }}
  .cnam p {{ margin: 0; text-align: justify; }}
  .pieddepage {{ position: running(pieddepage); font-size: 8px; color: #999;
                 border-top: 0.5px solid #ddd; padding-top: 3px; }}
</style></head><body>
  <div class="pieddepage">{_esc(nom)} &nbsp;|&nbsp; Session {_esc(ref)} ({_esc(famille)}) &nbsp;|&nbsp; Recommandation de formation</div>
  <div class="head">
    <div class="org">{_esc(nom_org)}<small>Organisme testeur certifié CACES®{inrs_html}</small></div>
    {logo_html}
  </div>
  <h1>Recommandation de formation complémentaire</h1>
  <div class="candidat">
    Candidat : <span class="v">{_esc(nom)}</span> &nbsp;&nbsp; Né(e) le : <span class="v">{_esc(naissance)}</span>
  </div>
  <div class="session">
    <div><b>Session :</b> {_esc(ref)} &nbsp;|&nbsp; <b>Famille :</b> {_esc(famille)}</div>
    <div><b>Dates :</b> {_esc(dates_str)}</div>
    <div><b>Catégorie(s) non obtenue(s) :</b> <span class="cats">{cats_str}</span></div>
  </div>
  <div class="validite">
    <div class="vt">Validité des épreuves obtenues</div>
    <p>Une épreuve pratique est obtenue dans sa totalité ou ajournée : il n'existe pas de validation partielle d'une catégorie.</p>
    <p>Les épreuves obtenues restent valables un an au sein du même organisme. Durant cette période, le candidat se représente uniquement aux épreuves non-obtenues (épreuve théorique ou catégorie pratique), sans avoir à repasser celles qu'il a validées.</p>
    <p>L'échec à une option (« porte-engins » PE ou « télécommande » TC) implique de repasser la catégorie pratique concernée dans son intégralité si le candidat souhaite tenter à nouveau cette option.</p>
    <div class="vt">Durée de formation recommandée</div>
    <p>Les durées indiquées sont proposées d'un commun accord entre l'organisme et le testeur CACES® certifié, en fonction de leur appréciation et de leur expérience. Elles constituent une recommandation pédagogique et ne sauraient garantir la réussite du candidat lors d'une nouvelle évaluation, l'organisme et le testeur n'étant ni psychologues, ni psychotechniciens.</p>
    <p>Ces durées sont exprimées en heures de formation effectives. Leur organisation au sein du planning de l'organisme, souvent partagé avec d'autres apprenants, peut nécessiter la réservation de plusieurs journées de formation.</p>
  </div>
  {blocs_html}
  <div class="total"><span>Durée totale de formation recommandée</span><span>{_esc(total_label)}</span></div>
  {cases_html}
  {autres_html}
  <div class="cnam">
    <div class="cnam-t">Rappel — Dispositif CACES® de la CNAM</div>
    <p>Le dispositif CACES® de la CNAM est un dispositif d'évaluation, et non de formation. Ce dispositif s'adresse à des conducteurs dont le niveau de compétences est optimal, du fait d'une formation adaptée en durée et en contenu, voire d'une expérience professionnelle. La formation préalable, toujours obligatoire, doit être organisée en tenant compte du profil de chaque conducteur, en fonction de son expérience et de ses aptitudes présumées à la conduite. Pour pouvoir se présenter à un test CACES®, un candidat doit être parfaitement autonome avec l'engin, et être capable de réaliser les opérations à la vitesse demandée en production réelle, sans risque pour lui, les tiers et l'environnement de travail. Cela nécessite plusieurs heures (parfois plusieurs jours) d'apprentissage individuel, par engin. Il est de la responsabilité des commanditaires de choisir le bon format de formation.</p>
  </div>
  <div class="footer">Document établi le {datetime.now().strftime("%d/%m/%Y")} par {_esc(nom_org)}.</div>
</body></html>"""

    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()