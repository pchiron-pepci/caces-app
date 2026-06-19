"""
app/services/pdf_recap_session.py
Génération PDF du récapitulatif des résultats d'une session.
"""

import json
from io import BytesIO
from html import escape as _esc
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.models.session_candidat import SessionCandidat
from app.models.jour_test import JourTest, ResultatTheorie
from app.models.session_epreuve import SessionEpreuve
from app.models.stagiaire import Stagiaire
from app.models.testeur import Testeur
from app.models.config_organisme import ConfigOrganisme
from app.models.jour_formation import JourFormation, AffectationFormation, PlanningApprenant
from app.models.utilisateur import Utilisateur


# ── Helpers config ──────────────────────────────────────────────────────────

def _get_logo_data(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    if cfg and cfg.logo_base64 and cfg.logo_nom:
        ext = cfg.logo_nom.rsplit('.', 1)[-1].lower()
        mime = {
            'png': 'image/png', 'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp',
        }.get(ext, 'image/png')
        return f"data:{mime};base64,{cfg.logo_base64}"
    return ""


def _get_nom_organisme(db: DBSession) -> str:
    cfg = db.query(ConfigOrganisme).first()
    return cfg.nom_organisme if cfg and cfg.nom_organisme else "PEPCI Formation"


# ── Collecte des données ────────────────────────────────────────────────────

def _collecter_donnees(
    session_id: int, db: DBSession
) -> tuple[list[dict], dict]:
    """
    Retourne (candidats, formation_meta).

    candidats : liste de dicts par candidat actif, triés NOM prénom :
      { "nom", "prenom",
        "theorie": None | {"obtenue", "note", "mode", "date", "testeur"},
        "epreuves": [{"categorie", "obtenue", "options", "date", "testeur"}],
        "uf_formation": None | {"theorie": float, "par_cat": {cat: float}} }
      uf_formation = None si le candidat n'a aucun PlanningApprenant.

    formation_meta : { "has_formation": bool, "formateurs": str }
      has_formation = True si la session a au moins un JourFormation actif.
      formateurs    = "Nom Prénom (principal), Nom Prénom" (peut être "").
    """
    # Candidats actifs de la session
    rows = (
        db.query(Stagiaire, SessionCandidat)
        .join(SessionCandidat, SessionCandidat.stagiaire_id == Stagiaire.id)
        .filter(SessionCandidat.session_id == session_id, SessionCandidat.actif == True)
        .order_by(Stagiaire.nom, Stagiaire.prenom)
        .all()
    )
    candidats = [(s, sc) for s, sc in rows]

    # Récap : on prend le DERNIER résultat (récence), pas le meilleur —
    # diffère volontairement de l'affichage ligne candidat (meilleur réussi).
    # ResultatTheorie n'a pas de colonne date/created_at → id DESC (insertion séquentielle).
    all_rt = (
        db.query(ResultatTheorie)
        .filter(ResultatTheorie.session_id == session_id)
        .order_by(
            ResultatTheorie.stagiaire_id,
            ResultatTheorie.id.desc(),
        )
        .all()
    )
    theorie_par_candidat: dict[int, ResultatTheorie] = {}
    for rt in all_rt:
        if rt.stagiaire_id not in theorie_par_candidat:
            theorie_par_candidat[rt.stagiaire_id] = rt

    # Pratique : toutes les épreuves de la session
    all_se = (
        db.query(SessionEpreuve)
        .filter(SessionEpreuve.session_id == session_id)
        .order_by(SessionEpreuve.stagiaire_id, SessionEpreuve.categorie)
        .all()
    )
    epreuves_par_candidat: dict[int, list[SessionEpreuve]] = {}
    for se in all_se:
        epreuves_par_candidat.setdefault(se.stagiaire_id, []).append(se)

    # ── Requêtes groupées anti-N+1 : JourTest + Testeur ────────────────────
    jt_ids = {rt.jour_test_id for rt in all_rt if rt.jour_test_id}
    jours: dict[int, JourTest] = {}
    if jt_ids:
        jours = {
            jt.id: jt
            for jt in db.query(JourTest).filter(JourTest.id.in_(jt_ids)).all()
        }

    testeur_ids: set[int] = set()
    for jt in jours.values():
        if jt.testeur_id:
            testeur_ids.add(jt.testeur_id)
    for se in all_se:
        if se.testeur_id:
            testeur_ids.add(se.testeur_id)
    testeurs: dict[int, str] = {}
    if testeur_ids:
        testeurs = {
            t.id: f"{t.nom} {t.prenom}"
            for t in db.query(Testeur).filter(Testeur.id.in_(testeur_ids)).all()
        }

    # ── Requêtes groupées : Formation ────────────────────────────────────────
    jours_formation = (
        db.query(JourFormation)
        .filter(JourFormation.session_id == session_id, JourFormation.actif == True)
        .all()
    )
    jf_ids = {jf.id for jf in jours_formation}
    has_formation = bool(jf_ids)
    formateurs_label = ""
    uf_theorie_par_cand: dict[int, float] = {}
    uf_cat_par_cand: dict[int, dict[str, float]] = {}
    uf_stag_ids: set[int] = set()

    if jf_ids:
        affectations = (
            db.query(AffectationFormation)
            .filter(AffectationFormation.jour_formation_id.in_(jf_ids))
            .all()
        )
        user_ids = {af.user_id for af in affectations}
        utilisateurs: dict[int, str] = {}
        if user_ids:
            utilisateurs = {
                u.id: f"{u.nom} {u.prenom}"
                for u in db.query(Utilisateur).filter(Utilisateur.id.in_(user_ids)).all()
            }
        # Un user principal sur au moins un jour = classé "principal" globalement
        principal_ids: set[int] = set()
        autre_ids: set[int] = set()
        for af in affectations:
            if af.principal:
                principal_ids.add(af.user_id)
            else:
                autre_ids.add(af.user_id)
        autre_ids -= principal_ids
        parts = [f"{utilisateurs.get(uid, f'Formateur {uid}')} (principal)" for uid in sorted(principal_ids)]
        parts += [utilisateurs.get(uid, f"Formateur {uid}") for uid in sorted(autre_ids)]
        formateurs_label = ", ".join(parts)

        plannings = (
            db.query(PlanningApprenant)
            .filter(
                PlanningApprenant.jour_formation_id.in_(jf_ids),
                PlanningApprenant.actif == True,
            )
            .all()
        )
        for pa in plannings:
            sid_pa = pa.stagiaire_id
            uf_stag_ids.add(sid_pa)
            # UF théorie
            uf_theorie_par_cand[sid_pa] = (
                uf_theorie_par_cand.get(sid_pa, 0.0) + (pa.heures_theorie or 0.0)
            )
            # UF par catégorie (heures_par_cat JSON {"A": 2.0, "B1": 1.5})
            if pa.heures_par_cat:
                try:
                    cat_h = json.loads(pa.heures_par_cat)
                    if isinstance(cat_h, dict):
                        d = uf_cat_par_cand.setdefault(sid_pa, {})
                        for cat, val in cat_h.items():
                            d[cat] = d.get(cat, 0.0) + float(val or 0)
                except (ValueError, TypeError):
                    pass

    formation_meta = {"has_formation": has_formation, "formateurs": formateurs_label}

    def _testeur_label(jt: JourTest | None) -> str | None:
        """Construit le label testeur(s) d'un JourTest (principal + sup éventuels)."""
        if jt is None:
            return None
        parts = []
        if jt.testeur_id and jt.testeur_id in testeurs:
            parts.append(testeurs[jt.testeur_id])
        if jt.testeurs_sup:
            try:
                sup = json.loads(jt.testeurs_sup)
                if isinstance(sup, list):
                    parts.extend(str(s) for s in sup if s)
            except (ValueError, TypeError):
                pass
        return " + ".join(parts) if parts else None

    # Assemblage
    result = []
    for stagiaire, _ in candidats:
        sid = stagiaire.id

        theorie_data = None
        rt = theorie_par_candidat.get(sid)
        if rt is not None:
            mode_label = "Saisie manuelle" if rt.mode == "degrade" else "Numérique"
            jt = jours.get(rt.jour_test_id) if rt.jour_test_id else None
            theorie_data = {
                "obtenue": rt.obtenue,
                "note": rt.note_totale,
                "mode": mode_label,
                "date": jt.date.strftime("%d/%m/%Y") if jt and jt.date else None,
                "testeur": _testeur_label(jt),
            }

        epreuves_data = []
        for se in epreuves_par_candidat.get(sid, []):
            opts = ""
            if se.options_obtenues:
                opts = ", ".join(o.strip() for o in se.options_obtenues.split(",") if o.strip())
            epreuves_data.append({
                "categorie": se.categorie,
                "obtenue": se.obtenue,
                "options": opts,
                "date": se.date.strftime("%d/%m/%Y") if se.date else None,
                "testeur": testeurs.get(se.testeur_id) if se.testeur_id else None,
            })

        result.append({
            "nom": stagiaire.nom,
            "prenom": stagiaire.prenom,
            "theorie": theorie_data,
            "epreuves": epreuves_data,
            "uf_formation": {
                "theorie": uf_theorie_par_cand.get(sid, 0.0),
                "par_cat": uf_cat_par_cand.get(sid, {}),
            } if sid in uf_stag_ids else None,
        })

    return result, formation_meta


# ── Construction HTML ───────────────────────────────────────────────────────

_BADGE_OK  = "background:#e8f5e9; color:#1b5e20; border:1px solid #4caf50;"
_BADGE_KO  = "background:#ffebee; color:#b71c1c; border:1px solid #ef9a9a;"
_BADGE_ATT = "background:#f5f5f5; color:#757575; border:1px solid #bdbdbd;"


def _badge(obtenue, label_ok="Acquis", label_ko="Échec", label_att="En attente") -> str:
    if obtenue is None:
        style, label = _BADGE_ATT, label_att
    elif obtenue:
        style, label = _BADGE_OK, label_ok
    else:
        style, label = _BADGE_KO, label_ko
    return (
        f'<span style="display:inline-block; padding:1px 8px; border-radius:3px; '
        f'font-size:9px; font-weight:bold; {style}">{label}</span>'
    )


def _fmt_uf(val: float) -> str:
    """Formate un nombre d'UF : entier si .0, sinon 1 décimale."""
    return str(int(val)) if val == int(val) else f"{val:.1f}"


def _meta_str(date: str | None, testeur: str | None) -> str:
    """Fragment HTML grisé 'jj/mm/aaaa · Nom Prénom' à insérer après le détail principal."""
    parts = []
    if date:
        parts.append(_esc(date))
    if testeur:
        parts.append(_esc(testeur))
    elif date:
        parts.append("—")
    if not parts:
        return ""
    return (
        f" &nbsp;<span style='color:#888; font-size:9px;'>"
        f"{'&nbsp;·&nbsp;'.join(parts)}"
        f"</span>"
    )


def _build_html(
    session: Session,
    nom_organisme: str,
    logo_data: str,
    candidats: list[dict],
    formation_meta: dict,
) -> str:
    has_formation   = formation_meta.get("has_formation", False)
    formateurs_str  = formation_meta.get("formateurs", "")

    ref_str  = session.reference or f"Session {session.id}"
    famille  = session.famille

    date_parts = []
    if session.date_theorie:
        date_parts.append(f"Théorie : {session.date_theorie.strftime('%d/%m/%Y')}")
    if session.date_pratique_debut:
        d = session.date_pratique_debut.strftime('%d/%m/%Y')
        if session.date_pratique_fin and session.date_pratique_fin != session.date_pratique_debut:
            d += f" – {session.date_pratique_fin.strftime('%d/%m/%Y')}"
        date_parts.append(f"Pratique : {d}")
    dates_str = " &nbsp;|&nbsp; ".join(date_parts) if date_parts else "—"

    logo_html = (
        f'<img src="{logo_data}" style="height:44px; max-width:130px; object-fit:contain;" alt="Logo" />'
        if logo_data else ""
    )

    # Blocs candidats
    blocs_html = ""
    for c in candidats:
        nom_complet = _esc(f"{c['nom']} {c['prenom']}")

        # ── Ligne théorie ──
        th = c["theorie"]
        if th is None:
            th_badge = _badge(None)
            th_detail = "—"
        else:
            th_badge  = _badge(th["obtenue"])
            note_str  = f"{int(th['note'])}/100" if th["note"] is not None else "—/100"
            th_meta   = _meta_str(th.get("date"), th.get("testeur"))
            th_detail = f"{note_str} &nbsp;·&nbsp; {_esc(th['mode'])}{th_meta}"

        theorie_row = (
            f"<tr>"
            f"<td class='ep-label'>Théorie</td>"
            f"<td>{th_badge}</td>"
            f"<td class='ep-detail'>{th_detail}</td>"
            f"</tr>"
        )

        # ── Ligne formation ──
        formation_row = ""
        if has_formation:
            uf = c.get("uf_formation")
            if uf is None:
                uf_detail = "—"
            else:
                uf_parts = []
                theo = uf.get("theorie", 0.0)
                if theo:
                    uf_parts.append(f"Théorie&nbsp;: {_fmt_uf(theo)}&nbsp;UF")
                for cat in sorted(uf.get("par_cat", {})):
                    val = uf["par_cat"][cat]
                    if val:
                        uf_parts.append(f"{_esc(cat)}&nbsp;: {_fmt_uf(val)}&nbsp;UF")
                uf_detail = " &nbsp;·&nbsp; ".join(uf_parts) if uf_parts else "—"
            formation_row = (
                f"<tr>"
                f"<td class='ep-label'>Formation</td>"
                f"<td></td>"
                f"<td class='ep-detail'>{uf_detail}</td>"
                f"</tr>"
            )

        # ── Lignes pratique ──
        if c["epreuves"]:
            pratique_rows = ""
            for i, ep in enumerate(c["epreuves"]):
                ep_badge = _badge(ep["obtenue"])
                opts_str = f"&nbsp;·&nbsp; <em>{_esc(ep['options'])}</em>" if ep["options"] else ""
                ep_meta  = _meta_str(ep.get("date"), ep.get("testeur"))
                label = "Pratique" if i == 0 else ""
                pratique_rows += (
                    f"<tr>"
                    f"<td class='ep-label'>{label}</td>"
                    f"<td>{ep_badge}</td>"
                    f"<td class='ep-detail'><strong>{_esc(ep['categorie'])}</strong>{opts_str}{ep_meta}</td>"
                    f"</tr>"
                )
        else:
            pratique_rows = (
                "<tr>"
                "<td class='ep-label'>Pratique</td>"
                f"<td>{_badge(None)}</td>"
                "<td class='ep-detail'>—</td>"
                "</tr>"
            )

        blocs_html += f"""
<div class="candidat-bloc">
  <div class="candidat-nom">{nom_complet}</div>
  <table class="ep-table">
    <tbody>
      {formation_row}
      {theorie_row}
      {pratique_rows}
    </tbody>
  </table>
</div>"""

    if not blocs_html:
        blocs_html = '<p style="color:#888; font-style:italic;">Aucun candidat actif pour cette session.</p>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 16mm 14mm 14mm 14mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10.5px; color: #1a1a1a; margin: 0; }}

  /* En-tête */
  .doc-header {{
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 2px solid #1a237e; padding-bottom: 8px; margin-bottom: 18px;
  }}
  .doc-header-left {{ display: flex; align-items: center; gap: 14px; }}
  h1 {{ font-size: 14px; color: #1a237e; margin: 0 0 3px 0; }}
  .doc-meta {{ text-align: right; font-size: 9.5px; color: #555; line-height: 1.7; }}

  /* Blocs candidats */
  .candidat-bloc {{
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    margin-bottom: 10px;
    page-break-inside: avoid;
    overflow: hidden;
  }}
  .candidat-nom {{
    background: #1a237e;
    color: white;
    font-weight: bold;
    font-size: 11px;
    padding: 5px 10px;
  }}

  /* Table résultats */
  .ep-table {{
    width: 100%;
    border-collapse: collapse;
  }}
  .ep-table td {{
    padding: 4px 10px;
    border-top: 1px solid #eeeeee;
    vertical-align: middle;
    font-size: 10px;
  }}
  .ep-table tr:first-child td {{ border-top: none; }}
  td.ep-label {{
    width: 68px;
    color: #666;
    font-size: 9.5px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
  }}
  td.ep-detail {{
    color: #333;
  }}

  /* Pied de page */
  .footer {{
    text-align: center; font-size: 8.5px; color: #aaa;
    margin-top: 20px; border-top: 1px solid #eee; padding-top: 6px;
  }}
</style>
</head>
<body>

<div class="doc-header">
  <div class="doc-header-left">
    {logo_html}
    <div>
      <h1>Récapitulatif des résultats</h1>
      <div style="font-size:9.5px; color:#666;">{_esc(nom_organisme)}</div>
    </div>
  </div>
  <div class="doc-meta">
    <div><strong>Réf. :</strong> {_esc(ref_str)}</div>
    <div><strong>Famille :</strong> {_esc(famille)}</div>
    <div>{dates_str}</div>
    {f'<div><strong>Formateurs :</strong> {_esc(formateurs_str)}</div>' if has_formation and formateurs_str else ''}
  </div>
</div>

{blocs_html}

<div class="footer">
  Document généré automatiquement &mdash; {_esc(nom_organisme)} &mdash; {_esc(ref_str)}
</div>

</body>
</html>"""


# ── Point d'entrée public ───────────────────────────────────────────────────

def generer_recap_resultats(session_id: int, db: DBSession) -> bytes:
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} introuvable")

    nom_organisme           = _get_nom_organisme(db)
    logo_data               = _get_logo_data(db)
    candidats, formation    = _collecter_donnees(session_id, db)

    html = _build_html(session, nom_organisme, logo_data, candidats, formation)

    from weasyprint import HTML
    buf = BytesIO()
    HTML(string=html, base_url=None).write_pdf(buf)
    return buf.getvalue()
