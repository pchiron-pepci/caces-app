"""
app/services/export_zip_session.py
Génération du ZIP de dossier de session.

Contenu final :
  corrige.pdf                               — corrigé de la grille tirée
  recap_resultats.pdf                       — récap tous candidats (date + testeur)
  justificatifs/{nom}.pdf                   — justificatifs scannés (mode dégradé)
  tests_numeriques/{NOM_Prenom}.pdf         — détail candidat (mode numérique)
  consentements/consentement_{NOM_Prenom}.pdf — consentement RGPD par candidat
  neutralite/neutralite_{NOM_Prenom}.pdf    — attestation neutralité par candidat
"""

import base64
import zipfile
from io import BytesIO

from sqlalchemy.orm import Session as DBSession

from app.models.jour_test import ResultatTheorie, JourTest
from app.models.stagiaire import Stagiaire
from app.models.consentement_rgpd import ConsentementRGPD
from app.models.attestation_neutralite import AttestationNeutralite
from app.services.pdf_test_theorie import generer_corrige
from app.services.pdf_recap_session import generer_recap_resultats
from app.services.pdf_detail_theorie import generer_pdf_detail_theorie
from app.services.pdf_consentement_neutralite import (
    generer_pdf_consentement,
    generer_pdf_neutralite,
)


def _sanitize(nom: str) -> str:
    """Remplace les caractères interdits dans un chemin ZIP."""
    for ch in r'/\:*?"<>| ':
        nom = nom.replace(ch, "_")
    return nom


def _nom_candidat(stagiaire_id: int, stagiaires: dict) -> str:
    """Retourne 'NOM_Prenom' sanitizé, ou 'stagXXX' si introuvable."""
    stag = stagiaires.get(stagiaire_id)
    if stag:
        return _sanitize(f"{stag.nom}_{stag.prenom}")
    return f"stag{stagiaire_id}"


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

        # ── batch-load : RT, consentements, jours, attestations ──────────────
        all_rts = (
            db.query(ResultatTheorie)
            .filter(ResultatTheorie.session_id == session_id)
            .all()
        )

        all_consentements = (
            db.query(ConsentementRGPD)
            .filter(ConsentementRGPD.session_id == session_id)
            .all()
        )

        jt_ids = {
            jt.id
            for jt in db.query(JourTest.id)
            .filter(JourTest.session_id == session_id)
            .all()
        }

        all_attestations = (
            db.query(AttestationNeutralite)
            .filter(AttestationNeutralite.jour_test_id.in_(jt_ids))
            .all()
        ) if jt_ids else []

        # Batch-load tous les stagiaires impliqués (une seule requête)
        stag_ids = (
            {rt.stagiaire_id for rt in all_rts}
            | {c.stagiaire_id for c in all_consentements}
            | {a.stagiaire_id for a in all_attestations}
        )
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
                nom = _nom_candidat(rt.stagiaire_id, stagiaires)
                zf.writestr(f"tests_numeriques/{nom}.pdf", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] test_numerique stag={rt.stagiaire_id} rt={rt.id} error: {e}", flush=True)

        # ── consentements RGPD ────────────────────────────────────────────────
        for c in all_consentements:
            try:
                pdf_bytes = generer_pdf_consentement(c.id, db)
                nom = _nom_candidat(c.stagiaire_id, stagiaires)
                zf.writestr(f"consentements/consentement_{nom}.pdf", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] consentement stag={c.stagiaire_id} id={c.id} error: {e}", flush=True)

        # ── attestations de neutralité ────────────────────────────────────────
        for a in all_attestations:
            try:
                pdf_bytes = generer_pdf_neutralite(a.id, db)
                nom = _nom_candidat(a.stagiaire_id, stagiaires)
                zf.writestr(f"neutralite/neutralite_{nom}.pdf", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] neutralite stag={a.stagiaire_id} id={a.id} error: {e}", flush=True)

    buf.seek(0)
    return buf.getvalue()
