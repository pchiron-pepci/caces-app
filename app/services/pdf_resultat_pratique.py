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


ENGIN_LABELS = {
    "PH": "Pelle hydraulique compacte",
    "MB": "Motobasculeur compact",
    "CH": "Chargeuse compacte",
    "CP": "Compacteur compact",
}


def _titre_bloc(bloc: dict, est_base: bool) -> str:
    """Titre d'un bloc : engin N1/N2 si variante (cat A), sinon base/option."""
    if est_base:
        var = bloc.get("variante")
        if var:
            rang = "N°1" if var == "PH" else "N°2"
            nom = ENGIN_LABELS.get(var, var)
            return f"Engin {rang} — {nom} ({var})"
        return "Épreuve de base"
    return f"Option — {_esc(bloc.get('libelle') or bloc.get('code_option') or '')}"


def _bloc_html(bloc: dict, est_base: bool, acquis: bool) -> str:
    titre = _titre_bloc(bloc, est_base)
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

    # Points d'évaluation groupés par thème
    themes_vus: dict = {}
    for pe in bloc.get("points_evaluation", []):
        th_lib = pe.get("theme", "")
        if th_lib not in themes_vus:
            themes_vus[th_lib] = []
        themes_vus[th_lib].append(pe)

    pe_blocks = ""
    for th_lib, pes in themes_vus.items():
        pes_html = ""
        for pe in pes:
            etat = _badge(pe["ok"], "OK" if pe["ok"] else "0 = échec")
            chapeau = (f'<div class="pe-chapeau">{_esc(pe["libelle_chapeau"])}</div>'
                       if pe.get("libelle_chapeau") else "")
            items_html = ""
            for it in pe.get("items", []):
                if it.get("descriptif_seul"):
                    items_html += f'<div class="it-desc">{_esc(it["libelle"])}</div>'
                else:
                    items_html += (
                        f'<div class="it-row">'
                        f'<span class="it-lib">{_esc(it["libelle"])}</span>'
                        f'<span class="it-note">{_fmt(it["note"])} / {_fmt(it["bareme"])}</span>'
                        f'</div>'
                    )
            pes_html += f"""
            <div class="pe-block">
              <div class="pe-titre">
                <span>PE {_esc(pe["numero"])} — {_fmt(pe["note"])} / {_fmt(pe["bareme"])}</span>
                {etat}
              </div>
              {chapeau}{items_html}
            </div>"""
        pe_blocks += f"""
        <div class="th-grp">
          <div class="th-grp-titre">{_esc(th_lib)}</div>
          {pes_html}
        </div>"""

    pe_section = ""
    if pe_blocks:
        pe_section = f"""
        <div class="sub">Détail des points d'évaluation</div>
        {pe_blocks}"""

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


# ── Synthèse multi-colonnes (gabarit unique : N colonnes = bases + options) ──

def _fmt_hms(sec) -> str:
    """Secondes -> H:MM:SS ou MM:SS."""
    if sec is None:
        return "--"
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, sd = divmod(r, 60)
    if h > 0:
        return "%d:%02d:%02d" % (h, m, sd)
    return "%d:%02d" % (m, sd)


def _pct_style(pct):
    """Triple seuil : vert <100, orange 100-130, rouge >130."""
    if pct is None:
        return "", ""
    if pct < 100:
        return "#e8f5e9", "#1b5e20"
    if pct <= 130:
        return "#fff3e0", "#b26a00"
    return "#fdecea", "#a32d2d"


def _temps_html(saisie, db) -> str:
    """Tableau des temps par group_key (CAT = categorie, OPT:<code> = option).
    Insere entre le titre 'Synthese par epreuve' et le tableau des notes."""
    from app.models.grille_pratique import CompteurTemps
    rows = db.query(CompteurTemps).filter(CompteurTemps.saisie_id == saisie.id).all()
    if not rows:
        return ""
    # Ordre : CAT d'abord, puis options par ordre alpha du code.
    def _rang(r):
        gk = (r.group_key or "")
        if gk == "CAT":
            return (0, "")
        if gk.startswith("OPT:"):
            return (1, gk[4:])
        return (2, gk)
    rows = sorted(rows, key=_rang)

    trs = ""
    for r in rows:
        gk = r.group_key or ""
        if gk == "CAT":
            lib = _esc(r.label or "Categorie")
        elif gk.startswith("OPT:"):
            lib = _esc(r.label or ("Option " + gk[4:]))
        else:
            lib = _esc(r.label or gk)
        est_opt = gk.startswith("OPT:")
        ref = r.ref_secondes
        realise = r.cumul_secondes
        pct = None
        if ref and realise is not None and ref > 0:
            pct = round(realise * 100.0 / ref)
        bg, fg = _pct_style(pct)
        pct_cell = "--"
        if pct is not None:
            pct_cell = ('<span style="background:%s;color:%s;padding:1px 6px;'
                        'border-radius:3px;">%d%%</span>' % (bg, fg, pct))
        realise_style = (' style="color:%s;font-weight:700;"' % fg) if pct is not None else ""
        row_bg = ' class="col-opt"' if est_opt else ""
        trs += (
            '<tr>'
            '<td class="lib"%s>%s</td>'
            '<td class="c"%s>%s</td>'
            '<td class="c"%s>%s</td>'
            '<td class="c"%s>%s</td>'
            '<td class="c na"%s>%s</td>'
            '<td class="c"%s%s>%s</td>'
            '<td class="c"%s>%s</td>'
            '</tr>'
        ) % (
            row_bg, lib,
            row_bg, _fmt_hms(r.duree_pp),
            row_bg, _fmt_hms(r.duree_mn),
            row_bg, _fmt_hms(r.duree_fp),
            row_bg, _fmt_hms(ref),
            row_bg, realise_style, _fmt_hms(realise),
            row_bg, pct_cell,
        )

    return """
    <table class="synth" style="margin-bottom:12px;">
      <thead><tr>
        <th class="lib">Epreuve</th>
        <th class="c">Prise poste</th>
        <th class="c">Man&oelig;uvre</th>
        <th class="c">Fin poste</th>
        <th class="c">Ref.</th>
        <th class="c">Realise</th>
        <th class="c">%%</th>
      </tr></thead>
      <tbody>%s</tbody>
    </table>
""" % trs


def _synthese_html(calcul: dict, saisie=None, db=None) -> str:
    """Tableau de synthèse : une colonne par épreuve (bases + options),
    une ligne par thème (— si non applicable), notes globales et verdicts.
    Gabarit unique : 1 colonne (cat F) ou N colonnes (cat A + options)."""
    colonnes = []
    for b in calcul.get("bases", []):
        colonnes.append({
            "kind": "base",
            "titre": _titre_bloc(b, True),
            "acquis": b.get("reussi", False),
            "note": b.get("note_globale"), "max": b.get("note_max"),
            "themes": {t["libelle"]: t for t in b.get("themes", [])},
        })
    for o in calcul.get("options", []):
        colonnes.append({
            "kind": "option",
            "titre": _esc(o.get("libelle") or o.get("code_option") or "Option"),
            "acquis": o.get("acquis", False),
            "note": o.get("note_globale"), "max": o.get("note_max"),
            "themes": {t["libelle"]: t for t in o.get("themes", [])},
        })
    if not colonnes:
        return ""

    # Liste ordonnée des thèmes (union, dans l'ordre d'apparition)
    themes_ordre = []
    for col in colonnes:
        for lib in col["themes"].keys():
            if lib not in themes_ordre:
                themes_ordre.append(lib)

    # En-tête
    head = '<th class="lib">Thème</th>' + "".join(
        f'<th class="c{ " col-opt" if col["kind"]=="option" else "" }">{col["titre"]}</th>'
        for col in colonnes
    )

    # Lignes thèmes
    rows = ""
    for lib in themes_ordre:
        cells = ""
        for col in colonnes:
            t = col["themes"].get(lib)
            if not t:
                cells += f'<td class="c na{ " col-opt" if col["kind"]=="option" else "" }">—</td>'
            else:
                ko = not t.get("ok", True)
                style = ' style="color:#a32d2d;font-weight:700;"' if ko else ""
                extra = " col-opt" if col["kind"] == "option" else ""
                cells += f'<td class="c{extra}"{style}>{_fmt(t["note"])} / {_fmt(t["bareme"])}</td>'
        rows += f'<tr><td class="lib">{_esc(lib)}</td>{cells}</tr>'

    # Note globale
    glob = '<td class="lib"><b>Note globale</b></td>'
    for col in colonnes:
        extra = " col-opt" if col["kind"] == "option" else ""
        ko = (col["note"] is not None and col["max"] is not None and not col["acquis"])
        style = ' style="color:#a32d2d;"' if (col["kind"]=="base" and not col["acquis"]) else ""
        glob += f'<td class="c tot{extra}"{style}><b>{_fmt(col["note"])} / {_fmt(col["max"])}</b></td>'

    # Verdict
    verd = '<td class="lib"><b>Verdict</b></td>'
    for col in colonnes:
        extra = " col-opt" if col["kind"] == "option" else ""
        if col["acquis"]:
            badge = '<span class="badge ok">ACQUIS</span>'
        elif col["kind"] == "option":
            badge = '<span class="badge warn">NON ACQUISE</span>'
        else:
            badge = '<span class="badge ko">NON ACQUIS</span>'
        verd += f'<td class="c tot{extra}">{badge}</td>'

    temps_html = _temps_html(saisie, db) if (saisie is not None and db is not None) else ""
    return f"""
    <div class="sub">Synthèse par épreuve</div>
    {temps_html}
    <table class="synth">
      <thead><tr>{head}</tr></thead>
      <tbody>
        {rows}
        <tr class="tot-row">{glob}</tr>
        <tr class="tot-row">{verd}</tr>
      </tbody>
    </table>
    <div class="synth-note">Une colonne par épreuve. — = thème non applicable à cette épreuve.
      Pour la catégorie A, les DEUX engins doivent être acquis. Une option n'est acquise que si la catégorie de base l'est.</div>
"""


# ── Construction HTML ────────────────────────────────────────────────────────

def _build_html(saisie: SaisiePratique, donnees: dict, nom_organisme: str, logo_data: str, db=None) -> str:
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

    # Critères éliminatoires déclenchés (toutes sources : base + options)
    all_elim = []
    for _b in calcul.get("bases", []):
        all_elim += _b.get("eliminatoires_coches", [])
    for opt in calcul.get("options", []):
        all_elim += opt.get("eliminatoires_coches", [])
    elim_html = ""
    if all_elim:
        elim_items = "".join(f"<li>{_esc(lib)}</li>" for lib in all_elim)
        elim_html = f"""
    <div class="elim-zone">
      <div class="elim-titre">Critères éliminatoires déclenchés</div>
      <ul class="elim-list">{elim_items}</ul>
    </div>"""

    # Synthèse multi-colonnes (gabarit unique)
    synthese_html = _synthese_html(calcul, saisie, db)

    # Blocs base + options
    blocs_html = ""
    for b in calcul.get("bases", []):
        blocs_html += _bloc_html(b, True, b.get("reussi", False))
    for opt in calcul.get("options", []):
        blocs_html += _bloc_html(opt, False, opt.get("acquis", False))

    # Observations / justification
    obs_html = ""
    if saisie.observations:
        obs_html += f'<div class="note-block"><div class="nb-titre">Observations du testeur</div><div class="nb-corps">{_esc(saisie.observations)}</div></div>'
    if saisie.justification_ecart:
        obs_html += f'<div class="note-block warn"><div class="nb-titre">Justification de la décision par le testeur</div><div class="nb-corps">{_esc(saisie.justification_ecart)}</div></div>'

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
  @page {{ size: A4; margin: 14mm 14mm 20mm 14mm;
           @bottom-left {{ content: element(pageRef); }} }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; font-size: 11px; margin: 0; }}
  .head {{ display: flex; justify-content: space-between; align-items: center;
           border-bottom: 3px solid {ROUGE}; padding-bottom: 10px; margin-bottom: 14px; }}
  .head .org {{ font-size: 16px; font-weight: bold; color: {ANTHRACITE}; }}
  .head .org small {{ display:block; font-size:10px; font-weight:normal; color:#666; margin-top:2px; }}
  h1 {{ font-size: 15px; color: {ANTHRACITE}; margin: 0 0 12px; }}
  .candidat {{ background: #f6f7f9; border: 1px solid #e2e6ee; border-radius: 6px;
               padding: 6px 12px; margin-bottom: 8px; }}
  .candidat table {{ width: 100%; border-collapse: collapse; }}
  .candidat td {{ padding: 1px 6px; font-size: 11px; vertical-align: top; }}
  .candidat .k {{ color: #666; width: 130px; }}
  .candidat .v {{ font-weight: bold; color: {ANTHRACITE}; }}
  .verdict {{ text-align: center; padding: 8px; border-radius: 6px; margin-bottom: 10px;
              font-size: 16px; font-weight: bold; letter-spacing: 0.5px; }}
  .verdict.ok {{ background: #e8f5e9; color: #1b5e20; border: 2px solid #66bb6a; }}
  .verdict.ko {{ background: #fcebeb; color: #a32d2d; border: 2px solid #e57373; }}
  .elim-zone {{ background: #fff3cd; border: 2px solid #f0ad4e; border-radius: 6px;
                padding: 8px 12px; margin-bottom: 12px; page-break-inside: avoid; }}
  .elim-titre {{ font-size: 11px; font-weight: bold; color: #7a4a00; margin-bottom: 5px; }}
  .elim-list {{ margin: 0; padding-left: 18px; }}
  .elim-list li {{ font-size: 10px; color: #a32d2d; font-weight: bold; padding: 1px 0; }}
  .bloc {{ margin-bottom: 16px; }}
  .bloc-head {{ display: flex; justify-content: space-between; align-items: center;
                background: {ANTHRACITE}; color: #fff; padding: 6px 10px; border-radius: 5px 5px 0 0; }}
  .bloc-titre {{ font-weight: bold; font-size: 12px; }}
  .bloc-note {{ font-size: 11px; }}
  .bloc-note .seuil {{ color: #c9c9c9; font-size: 10px; }}
  .sub {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #888;
          margin: 8px 0 3px; }}
  table.synth {{ width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 4px; }}
  table.synth th {{ background: #eef0f4; color: #444; padding: 4px 6px; border: 1px solid #dfe3ea;
                    font-size: 9px; text-transform: uppercase; text-align: center; }}
  table.synth th.lib {{ text-align: left; width: 32%; }}
  table.synth td {{ padding: 4px 6px; border: 1px solid #e6e9ef; }}
  table.synth td.c {{ text-align: center; }}
  table.synth td.na {{ color: #aaa; }}
  table.synth td.lib {{ width: 32%; }}
  table.synth .col-opt {{ background: #f4f8fd; }}
  table.synth th.col-opt {{ background: #e3edf8; }}
  table.synth .tot-row td {{ background: #f6f7f9; }}
  table.synth .tot-row td.col-opt {{ background: #eaf1fa; }}
  .synth-note {{ font-size: 8px; color: #888; font-style: italic; margin-bottom: 12px; }}
  .badge.warn {{ background: #fff3cd; color: #7a4a00; border: 1px solid #f0ad4e; }}
  table.grid {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
  table.grid th {{ background: #eef0f4; color: #444; text-align: left; padding: 4px 7px;
                   border: 1px solid #dfe3ea; font-size: 9px; text-transform: uppercase; }}
  table.grid td {{ padding: 4px 7px; border: 1px solid #e6e9ef; }}
  table.grid td.c, table.grid th.c {{ text-align: center; }}
  table.grid td.lib {{ width: 55%; }}
  .th-grp {{ margin: 8px 0 4px; page-break-inside: avoid; }}
  .th-grp-titre {{ font-size: 10px; font-weight: bold; color: {ANTHRACITE}; background: #eef0f4;
                   border: 1px solid #dfe3ea; padding: 3px 7px; border-radius: 3px 3px 0 0; }}
  .pe-block {{ border: 1px solid #e6e9ef; border-top: none; padding: 5px 8px; margin-bottom: 2px;
               page-break-inside: avoid; }}
  .pe-titre {{ display: flex; justify-content: space-between; align-items: center;
               font-size: 10px; font-weight: bold; color: #444; margin-bottom: 3px; }}
  .pe-chapeau {{ font-size: 9px; color: #666; font-style: italic; margin-bottom: 3px; }}
  .it-row {{ display: flex; justify-content: space-between; font-size: 9px;
             padding: 1px 0; border-bottom: 1px dotted #eee; }}
  .it-row:last-child {{ border-bottom: none; }}
  .it-lib {{ color: #333; flex: 1; padding-right: 8px; }}
  .it-note {{ color: #555; white-space: nowrap; }}
  .it-desc {{ font-size: 9px; color: #888; font-style: italic; padding: 1px 0; }}
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
  .page-ref {{ position: running(pageRef); font-size: 8px; color: #888;
               white-space: nowrap; }}
  .ref-bas {{ border-top: 1px dashed #ccc; margin-top: 14px; padding-top: 5px;
              font-size: 8px; color: #888; page-break-inside: avoid; }}
</style></head><body>

  <div class="page-ref">{_esc(nom_candidat)} — {_esc(famille)} cat. {_esc(categorie)} — Session {_esc(ref)}</div>

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

  {synthese_html}

  {elim_html}

  {blocs_html}

  {obs_html}

  <div class="ref-bas">Candidat : {_esc(nom_candidat)} — {_esc(famille)} cat. {_esc(categorie)} — Session {_esc(ref)} — Validé le {_esc(date_val)}</div>

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
    html = _build_html(saisie, donnees, nom_organisme, logo_data, db)

    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()