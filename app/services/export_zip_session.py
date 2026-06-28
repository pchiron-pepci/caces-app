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
from app.models.justificatif import Justificatif
from app.models.session_candidat import SessionCandidat
from app.services import storage
from app.services.pdf_test_theorie import generer_corrige
from app.services.pdf_recap_session import generer_recap_resultats
from app.services.pdf_detail_theorie import generer_pdf_detail_theorie
from app.services.pdf_resultat_pratique import generer_pdf_resultat_pratique
from app.services.pdf_fiche_reco import generer_pdf_fiche_reco
from app.services.calcul_fiche_reco import calculer_fiche_reco
from app.models.grille_pratique import SaisiePratique
from app.services.pdf_consentement_neutralite import (
    generer_pdf_consentement,
    generer_pdf_neutralite,
)


def _sanitize(nom: str) -> str:
    """Remplace les caractères interdits dans un chemin ZIP."""
    for ch in r'/\:*?"<>| ':
        nom = nom.replace(ch, "_")
    return nom


def _sc_to_stag(session_candidat_id, db):
    if not session_candidat_id:
        return None
    sc = db.query(SessionCandidat).filter(SessionCandidat.id == session_candidat_id).first()
    return sc.stagiaire_id if sc else None


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
            if not rt.justificatif_cle:
                continue
            try:
                pdf_bytes = storage.get_fichier(rt.justificatif_cle)
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

        # Élargissement du dict stagiaires aux candidats dispense/formation
        scs_all = db.query(SessionCandidat).filter(
            SessionCandidat.session_id == session_id,
        ).all()
        extra_ids = {sc.stagiaire_id for sc in scs_all} - stag_ids
        if extra_ids:
            for s in db.query(Stagiaire).filter(Stagiaire.id.in_(extra_ids)).all():
                stagiaires[s.id] = s

        # ── boucle 5 : justificatifs de FORMATION ────────────────────────────
        justifs_formation = db.query(Justificatif).filter(
            Justificatif.session_id == session_id,
            Justificatif.type == "formation",
        ).all()
        for j in justifs_formation:
            try:
                if not j.fichier_cle:
                    continue
                data = storage.get_fichier(j.fichier_cle)
                nom_cand = _nom_candidat(_sc_to_stag(j.session_candidat_id, db), stagiaires) if j.session_candidat_id else "session"
                nom_fichier = _sanitize(j.fichier_nom or f"formation_{j.id}")
                zf.writestr(f"formation/{nom_cand}/{nom_fichier}", data)
            except Exception:
                pass

        # ── boucle 6 : DOCUMENTS de session ──────────────────────────────────
        justifs_docs = db.query(Justificatif).filter(
            Justificatif.session_id == session_id,
            Justificatif.type == "document_session",
        ).all()
        for j in justifs_docs:
            try:
                if not j.fichier_cle:
                    continue
                data = storage.get_fichier(j.fichier_cle)
                prefixe = _sanitize(j.libelle) + "_" if j.libelle else ""
                nom_fichier = prefixe + _sanitize(j.fichier_nom or f"document_{j.id}")
                zf.writestr(f"documents/{nom_fichier}", data)
            except Exception:
                pass

        # ── boucle 7 : justificatifs de DISPENSE ─────────────────────────────
        scs_dispense = db.query(SessionCandidat).filter(
            SessionCandidat.session_id == session_id,
            SessionCandidat.dispense_fichier_cle.isnot(None),
        ).all()
        for sc in scs_dispense:
            try:
                data = storage.get_fichier(sc.dispense_fichier_cle)
                nom_cand = _nom_candidat(sc.stagiaire_id, stagiaires)
                ext = ""
                if sc.dispense_fichier_nom and "." in sc.dispense_fichier_nom:
                    ext = "." + sc.dispense_fichier_nom.rsplit(".", 1)[1]
                zf.writestr(f"dispense/{nom_cand}{ext}", data)
            except Exception:
                pass

        # resultats pratiques valides (saisie en ligne, genere a la volee)
        if jt_ids:
            saisies_prat = db.query(SaisiePratique).filter(
                SaisiePratique.jour_test_id.in_(jt_ids),
                SaisiePratique.statut == "valide",
            ).all()
            for sp in saisies_prat:
                try:
                    pdf_bytes = generer_pdf_resultat_pratique(sp.id, db)
                    nom = _nom_candidat(sp.stagiaire_id, stagiaires)
                    cat = _sanitize(sp.categorie or "cat")
                    zf.writestr(f"resultats_pratiques/{nom}_{cat}.pdf", pdf_bytes)
                except Exception as e:
                    print(f"[ZIP] resultat_pratique saisie={sp.id} error: {e}", flush=True)

        # ── fiches de recommandation (candidats en echec) ────────────────────
        for sid in stag_ids:
            try:
                calc = calculer_fiche_reco(session_id, sid, db)
                if not calc.get("a_des_echecs"):
                    continue
                pdf_bytes = generer_pdf_fiche_reco(session_id, sid, db)
                nom = _nom_candidat(sid, stagiaires)
                zf.writestr(f"recommandations/recommandation_{nom}.pdf", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] recommandation stag={sid} error: {e}", flush=True)

    buf.seek(0)
    return buf.getvalue()
