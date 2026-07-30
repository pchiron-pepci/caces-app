"""
Audit LECTURE SEULE — verdicts pratiques VALIDÉS vs recalcul des NOTES (toutes familles).
Liste les saisies 'valide' dont SessionEpreuve.obtenue diverge de calculer_saisie.base_reussie
(= tous les engins de base réussis). Attrape le bug multi-engin ET les doublons de notes.
NE recalcule PAS le temps (volet front, non rejouable). À lancer APRÈS la migration de
dédoublonnage. Read-only. Usage : python audit_verdicts_pratique.py
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.grille_pratique import SaisiePratique
from app.models.session_epreuve import SessionEpreuve
from app.models.jour_test import JourTest
from app.models.session import Session as SessionModel
from app.models.stagiaire import Stagiaire
from app.services.calcul_pratique import calculer_saisie

db = sessionmaker(bind=create_engine(os.environ["DATABASE_URL"]))()
divergences, non_calculables = [], []

for s in db.query(SaisiePratique).filter(SaisiePratique.statut == "valide").all():
    try:
        res = calculer_saisie(s, db)
    except Exception as e:
        non_calculables.append((s.id, str(e))); continue
    base_reussie = bool(res.get("base_reussie"))
    jour = db.query(JourTest).filter(JourTest.id == s.jour_test_id).first()
    ep = db.query(SessionEpreuve).filter(
        SessionEpreuve.session_id == jour.session_id,
        SessionEpreuve.stagiaire_id == s.stagiaire_id,
        SessionEpreuve.categorie == s.categorie).first() if jour else None
    if not ep or ep.obtenue is None:
        continue
    if bool(ep.obtenue) != base_reussie:
        sess = db.query(SessionModel).filter(SessionModel.id == jour.session_id).first() if jour else None
        stag = db.query(Stagiaire).filter(Stagiaire.id == s.stagiaire_id).first()
        nom = ("%s %s" % (stag.nom, stag.prenom)) if stag else str(s.stagiaire_id)
        detail = " | ".join("%s=%s(%s/%s)" % (b.get("variante") or "base",
                            "OK" if b["reussi"] else "ECHEC", b["note_globale"], b["note_max"])
                            for b in (res.get("bases") or []))
        divergences.append((s.id, nom, (sess.famille if sess else "?"), s.categorie,
                            (sess.reference if sess and sess.reference else (jour.session_id if jour else "?")),
                            bool(ep.obtenue), base_reussie, detail))

print("=== Saisies VALIDÉES incohérentes avec les notes : %d ===" % len(divergences))
faux_obtenus = 0
for sid, nom, fam, cat, ses, obt, rec, det in divergences:
    if obt and not rec:
        faux_obtenus += 1; sens = "OBTENU alors que NOTES EN ECHEC  <== PRIORITAIRE (certif a revoir)"
    else:
        sens = "NON obtenu alors que NOTES OK  (a recontroler)"
    print("saisie %s | %s | %s cat %s | session %s | stocke=%s / recalcul=%s | %s | %s" % (
        sid, nom, fam, cat, ses, obt, rec, det, sens))
print("\nResume : %d divergence(s), dont %d 'obtenu a tort' (prioritaires)." % (len(divergences), faux_obtenus))
if not divergences:
    print("=> Aucun verdict valide en contradiction avec les notes. RAS.")
if non_calculables:
    print("\n[!] %d saisie(s) non recalculable(s) (verif manuelle) :" % len(non_calculables))
    for sid, e in non_calculables: print("  saisie %s : %s" % (sid, e))
db.close()
