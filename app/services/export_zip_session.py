"""
app/services/export_zip_session.py
Génération du ZIP de dossier de session : corrigé + récap résultats + justificatifs.
"""

import base64
import zipfile
from io import BytesIO

from sqlalchemy.orm import Session as DBSession

from app.models.jour_test import ResultatTheorie
from app.services.pdf_test_theorie import generer_corrige
from app.services.pdf_recap_session import generer_recap_resultats


def generer_zip_session(session_id: int, db: DBSession) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        try:
            zf.writestr("corrige.pdf", generer_corrige(session_id, db))
        except Exception as e:
            print(f"[ZIP] corrige.pdf error session={session_id}: {e}", flush=True)

        try:
            zf.writestr("recap_resultats.pdf", generer_recap_resultats(session_id, db))
        except Exception as e:
            print(f"[ZIP] recap_resultats.pdf error session={session_id}: {e}", flush=True)

        rts = (
            db.query(ResultatTheorie)
            .filter(
                ResultatTheorie.session_id == session_id,
                ResultatTheorie.justificatif_pdf.isnot(None),
            )
            .all()
        )
        for rt in rts:
            try:
                pdf_bytes = base64.b64decode(rt.justificatif_pdf)
                nom = (rt.justificatif_nom or f"justificatif_stag{rt.stagiaire_id}.pdf")
                nom = nom.replace("/", "_").replace("\\", "_")
                zf.writestr(f"justificatifs/{nom}", pdf_bytes)
            except Exception as e:
                print(f"[ZIP] justificatif stag={rt.stagiaire_id} error: {e}", flush=True)

    buf.seek(0)
    return buf.getvalue()
