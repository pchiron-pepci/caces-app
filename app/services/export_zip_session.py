"""
app/services/export_zip_session.py
Génération du ZIP de dossier de session.

Contenu final :
  corrige.pdf                          — corrigé de la grille tirée
  recap_resultats.pdf                  — récap tous candidats (date + testeur)
  justificatifs/{nom}.pdf              — justificatifs scannés (mode dégradé)
  tests_numeriques/{NOM_Prenom}.pdf    — détail candidat (mode numérique)
"""

import base64
import zipfile
from io import BytesIO

from sqlalchemy.orm import Session as DBSession

from app.models.jour_test import ResultatTheorie
from app.models.stagiaire import Stagiaire
from app.services.pdf_test_theorie import generer_corrige
from app.services.pdf_recap_session import generer_recap_resultats
from app.services.pdf_detail_theorie import generer_pdf_detail_theorie


def _nom_fichier_candidat(rt: ResultatTheorie, stagiaires: dict[int, Stagiaire]) -> str:
    """Retourne 'NOM_Prenom.pdf', sûr pour un chemin ZIP."""
    stag = stagiaires.get(rt.stagiaire_id)
    if stag:
        nom = f"{stag.nom}_{stag.prenom}"
    else:
        nom = f"stag{rt.stagiaire_id}"
    # Sanitize : retire les caractères problématiques dans un nom de fichier ZIP
    for ch in r'/\:*?"<>|':
        nom = nom.replace(ch, "_")
    return f"{nom}.pdf"


def generer_zip_session(session_id: int, db: DBSession) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # ── corrigé grille ────────────────────────────────────────────────────
        try:
            zf.writestr("corrige.pdf", generer_corrige(session_id, db))
        except Exception as e:
            print(f"[ZIP] corrige.pdf error session={session_id}: {e}", flush=True)

        # ── récap résultats ───────────────────────────────────────────────────
        try:
            zf.writestr("recap_resultats.pdf", generer_recap_resultats(session_id, db))
        except Exception as e:
            print(f"[ZIP] recap_resultats.pdf error session={session_id}: {e}", flush=True)

        # ── tous les RT de la session, une seule requête ──────────────────────
        all_rts = (
            db.query(ResultatTheorie)
            .filter(ResultatTheorie.session_id == session_id)
            .all()
        )

        # Batch-load stagiaires pour éviter N+1
        stag_ids = {rt.stagiaire_id for rt in all_rts}
        stagiaires: dict[int, Stagiaire] = {}
        if stag_ids:
            stagiaires = {
                s.id: s
                for s in db.query(Stagiaire).filter(Stagiaire.id.in_(stag_ids)).all()
            }

        # ── justificatifs scannés (mode dégradé) ─────────────────────────────
        for rt in all_rts:
            if not rt.justificatif_pdf:
                continue
            try:
                pdf_bytes = base64.b64decode(rt.justificatif_pdf)
                nom = (rt.justificatif_nom or f"justificatif_stag{rt.stagiaire_id}.pdf")
                nom = nom.replace("/", "_").replace("\\", "_")
                zf.writestr(f"justificatifs/{nom}", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] justificatif stag={rt.stagiaire_id} error: {e}", flush=True)

        # ── détails test numérique (mode numérique uniquement) ────────────────
        for rt in all_rts:
            if rt.mode != "numerique" or not rt.reponses_json:
                continue
            try:
                pdf_bytes = generer_pdf_detail_theorie(rt.id, db)
                nom = _nom_fichier_candidat(rt, stagiaires)
                zf.writestr(f"tests_numeriques/{nom}", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] test_numerique stag={rt.stagiaire_id} rt={rt.id} error: {e}", flush=True)

    buf.seek(0)
    return buf.getvalue()
