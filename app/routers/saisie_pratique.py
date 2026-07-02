"""Routes de la saisie pratique EN LIGNE (usage testeur, mobile).
Voie alternative au justificatif manuel. Une epreuve = une voie.
Toutes les routes d'ecriture sont derriere le PIN formateur (gere par le middleware).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.session_epreuve import SessionEpreuve
from app.models.jour_test import JourTest, JourTestCandidat
import json
from app.models.option_categorie import OptionCategorie
from app.models.categorie import Categorie, Famille
from app.models.grille_pratique import (
    GrillePratique, ThemePratique, PointEvaluation, ItemPratique, CritereEliminatoire,
    SaisiePratique, SaisieBloc, SaisieItemNote, SaisieEliminatoire,
)
from app.models.config_organisme import ConfigOrganisme
from app.services.calcul_pratique import calculer_saisie, appliquer_resultats
from app.config_utils import get_pin_formateur, get_pin_admin

router = APIRouter(prefix="/api/sessions", tags=["saisie_pratique"])

# Categories dont TOUTES les variantes base sont imposees et cumulees (pas de choix a l'ouverture).
# Ex R.482 G : engin a chenilles (CH) + engin a pneu/cylindre (PC), les deux passes a la suite.
CATEGORIES_CUMUL_TOTAL = {("R.482", "G")}


def _recommandation_from_famille(famille: str) -> str:
    """famille stockee type 'R482' -> recommandation grille 'R.482'."""
    f = (famille or "").upper().replace(".", "").replace(" ", "")
    if f.startswith("R") and len(f) >= 4:
        return "R." + f[1:]
    return famille


def _mode_saisie(db) -> str:
    cfg = db.query(ConfigOrganisme).first()
    return (cfg.mode_saisie_pratique if cfg and cfg.mode_saisie_pratique else "binaire")


def jour_session_famille(jour, db) -> str:
    """Recupere la famille (ex. 'R482') depuis la session du jour de test."""
    from app.models.session import Session as _S
    sess = db.query(_S).filter(_S.id == jour.session_id).first()
    return sess.famille if sess else ""


def _grille_dict(grille, db) -> dict:
    """Serialise une grille (themes -> PE -> items) pour l'ecran de saisie."""
    themes = []
    for th in db.query(ThemePratique).filter(
            ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre).all():
        points = []
        for pe in db.query(PointEvaluation).filter(
                PointEvaluation.theme_id == th.id).order_by(PointEvaluation.ordre).all():
            items = []
            for it in db.query(ItemPratique).filter(
                    ItemPratique.pe_id == pe.id).order_by(ItemPratique.ordre).all():
                items.append({
                    "id": it.id, "libelle": it.libelle,
                    "bareme_max": it.bareme_max, "descriptif_seul": it.descriptif_seul,
                    "critere_evaluation": it.critere_evaluation,
                })
            points.append({
                "id": pe.id, "numero": pe.numero,
                "libelle_chapeau": pe.libelle_chapeau, "items": items,
            })
        themes.append({
            "id": th.id, "libelle": th.libelle,
            "bareme_theme": th.bareme_theme, "seuil": th.bareme_theme / 2.0,
            "points": points,
        })
    elims = [{"id": c.id, "libelle": c.libelle}
             for c in db.query(CritereEliminatoire).filter(
                 CritereEliminatoire.grille_id == grille.id).order_by(CritereEliminatoire.ordre).all()]
    return {
        "grille_id": grille.id, "type": grille.type, "code_option": grille.code_option,
        "libelle": grille.libelle, "note_min": grille.note_min, "note_max": grille.note_max,
        "themes": themes, "eliminatoires": elims,
    }


@router.get("/{session_id}/pratique/saisie/{jour_test_id}/{stagiaire_id}/{categorie}/variantes")
def variantes_categorie(session_id: int, jour_test_id: int, stagiaire_id: int, categorie: str,
                        db: DBSession = Depends(get_db)):
    """Liste les variantes de grille base d'une categorie (choix exclusif d'engin).
    Renvoie [] si grille unique. Le cas A (cumul) est signale a part via 'mode'."""
    jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
    if not jour:
        raise HTTPException(404, "Jour de test introuvable")
    reco = _recommandation_from_famille(jour_session_famille(jour, db))
    est_cat_a = (reco == "R.482" and (categorie or "").upper() == "A")

    grilles = db.query(GrillePratique).filter(
        GrillePratique.recommandation == reco,
        GrillePratique.categorie == categorie,
        GrillePratique.type == "base", GrillePratique.actif == True,
    ).order_by(GrillePratique.ordre).all()

    variantes = [
        {"variante": g.variante, "libelle": g.libelle}
        for g in grilles if g.variante
    ]
    est_cumul_total = (reco, (categorie or "").upper()) in CATEGORIES_CUMUL_TOTAL
    if est_cat_a:
        mode = "cumul"
    elif est_cumul_total and len(variantes) >= 2:
        mode = "cumul_total"
    elif len(variantes) >= 2:
        mode = "exclusif"
    else:
        mode = "unique"
    return {"mode": mode, "variantes": variantes}


@router.post("/{session_id}/pratique/saisie/{jour_test_id}/{stagiaire_id}/{categorie}/ouvrir")
def ouvrir_saisie(session_id: int, jour_test_id: int, stagiaire_id: int, categorie: str,
                  engin2: str = None, variante: str = None,
                  db: DBSession = Depends(get_db)):
    """Ouvre (ou reprend) la saisie pour un test PLANIFIE : jour + candidat + categorie.
    Cat A multi-engins (R.482) : 2 blocs base. Engin N1 = PH (toujours), engin N2
    = MB/CH/CP passe en query param engin2 (choisi par le testeur a l'ouverture).
    """
    jour = db.query(JourTest).filter(JourTest.id == jour_test_id).first()
    if not jour:
        raise HTTPException(404, "Jour de test introuvable")
    jtc = db.query(JourTestCandidat).filter(
        JourTestCandidat.jour_test_id == jour_test_id,
        JourTestCandidat.stagiaire_id == stagiaire_id,
        JourTestCandidat.actif == True,
    ).first()
    if not jtc:
        raise HTTPException(404, "Candidat non planifie sur ce jour")

    reco = _recommandation_from_famille(jour_session_famille(jour, db))

    EST_CAT_A = (reco == "R.482" and (categorie or "").upper() == "A")
    ENGINS_N2_VALIDES = {"MB", "CH", "CP"}
    engin2_norm = (engin2 or "").strip().upper() or None
    variante_norm = (variante or "").strip().upper() or None
    # Detection variantes exclusives (categorie != A avec >=2 grilles base variantes)
    grilles_base_cat = db.query(GrillePratique).filter(
        GrillePratique.recommandation == reco,
        GrillePratique.categorie == categorie,
        GrillePratique.type == "base", GrillePratique.actif == True,
    ).all()
    variantes_dispo = {g.variante for g in grilles_base_cat if g.variante}
    EST_CUMUL_TOTAL = ((reco, (categorie or "").upper()) in CATEGORIES_CUMUL_TOTAL) and len(variantes_dispo) >= 2
    EST_VARIANTE_EXCLUSIVE = (not EST_CAT_A) and (not EST_CUMUL_TOTAL) and len(variantes_dispo) >= 2

    saisie = db.query(SaisiePratique).filter(
        SaisiePratique.jour_test_id == jour_test_id,
        SaisiePratique.stagiaire_id == stagiaire_id,
        SaisiePratique.categorie == categorie,
    ).first()
    reprise = saisie is not None

    if EST_CAT_A and not reprise:
        if engin2_norm not in ENGINS_N2_VALIDES:
            raise HTTPException(422, "Engin N2 requis pour la categorie A (MB, CH ou CP).")
    if EST_VARIANTE_EXCLUSIVE and not reprise:
        if variante_norm not in variantes_dispo:
            raise HTTPException(422, "Variante d'engin requise pour la categorie %s (%s)." % (
                categorie, ", ".join(sorted(variantes_dispo))))

    codes_planif = set()
    if jtc.options_planifiees:
        try:
            opts_map = json.loads(jtc.options_planifiees)
            for code in (opts_map.get(categorie) or []):
                if code and str(code).strip():
                    codes_planif.add(str(code).strip())
        except Exception:
            pass

    def _grille_option(code):
        return db.query(GrillePratique).filter(
            GrillePratique.recommandation == reco,
            GrillePratique.categorie == categorie,
            GrillePratique.type == "option", GrillePratique.code_option == code,
            GrillePratique.actif == True,
        ).first()

    def _grille_base(variante=None):
        q = db.query(GrillePratique).filter(
            GrillePratique.recommandation == reco,
            GrillePratique.categorie == categorie,
            GrillePratique.type == "base", GrillePratique.actif == True,
        )
        if variante is not None:
            q = q.filter(GrillePratique.variante == variante)
        return q.first()

    if not saisie:
        saisie = SaisiePratique(
            jour_test_id=jour_test_id, stagiaire_id=stagiaire_id, categorie=categorie,
            mode=_mode_saisie(db), statut="en_cours",
        )
        db.add(saisie)
        db.flush()

        if EST_CAT_A:
            g_ph = _grille_base("PH")
            if not g_ph:
                raise HTTPException(404, "Grille base PH introuvable pour %s A" % reco)
            db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_ph.id, type="base"))
            g_n2 = _grille_base(engin2_norm)
            if not g_n2:
                raise HTTPException(404, "Grille base %s introuvable pour %s A" % (engin2_norm, reco))
            db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_n2.id, type="base"))
        elif EST_CUMUL_TOTAL:
            grilles_cumul = db.query(GrillePratique).filter(
                GrillePratique.recommandation == reco,
                GrillePratique.categorie == categorie,
                GrillePratique.type == "base", GrillePratique.actif == True,
            ).order_by(GrillePratique.ordre).all()
            if not grilles_cumul:
                raise HTTPException(404, "Aucune grille base pour %s %s" % (reco, categorie))
            for g_cumul in grilles_cumul:
                db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_cumul.id, type="base"))
        elif EST_VARIANTE_EXCLUSIVE:
            grille_base = _grille_base(variante_norm)
            if not grille_base:
                raise HTTPException(404, "Grille %s introuvable pour %s %s" % (variante_norm, reco, categorie))
            db.add(SaisieBloc(saisie_id=saisie.id, grille_id=grille_base.id, type="base"))
        else:
            grille_base = _grille_base()
            if not grille_base:
                raise HTTPException(404, "Aucune grille pratique pour %s %s" % (reco, categorie))
            db.add(SaisieBloc(saisie_id=saisie.id, grille_id=grille_base.id, type="base"))

        for code in codes_planif:
            g_opt = _grille_option(code)
            if g_opt:
                db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_opt.id, type="option"))
        db.commit()
    else:
        blocs_opt = {}
        for b in db.query(SaisieBloc).filter(SaisieBloc.saisie_id == saisie.id, SaisieBloc.type == "option").all():
            g = db.query(GrillePratique).filter(GrillePratique.id == b.grille_id).first()
            if g and g.code_option:
                blocs_opt[g.code_option] = b

        for code in codes_planif:
            if code not in blocs_opt:
                g_opt = _grille_option(code)
                if g_opt:
                    db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_opt.id, type="option"))

        for code, b in blocs_opt.items():
            if code not in codes_planif:
                db.query(SaisieItemNote).filter(SaisieItemNote.bloc_id == b.id).delete()
                db.query(SaisieEliminatoire).filter(SaisieEliminatoire.bloc_id == b.id).delete()
                db.delete(b)
        db.commit()

    blocs_out = []
    for bloc in db.query(SaisieBloc).filter(SaisieBloc.saisie_id == saisie.id).all():
        grille = db.query(GrillePratique).filter(GrillePratique.id == bloc.grille_id).first()
        notes = {n.item_id: n.note for n in db.query(SaisieItemNote).filter(
            SaisieItemNote.bloc_id == bloc.id).all()}
        elim = [e.critere_id for e in db.query(SaisieEliminatoire).filter(
            SaisieEliminatoire.bloc_id == bloc.id).all()]
        gd = _grille_dict(grille, db)
        gd["variante"] = grille.variante
        blocs_out.append({
            "bloc_id": bloc.id, "grille": gd,
            "notes_saisies": notes, "eliminatoires_coches": elim,
        })

    return {
        "saisie_id": saisie.id, "mode": saisie.mode, "statut": saisie.statut,
        "reprise": reprise, "blocs": blocs_out,
        "testeur_id": saisie.testeur_id,
        "testeur_nom": saisie.testeur_nom,
        "signature_testeur": saisie.signature_testeur,
        "observations": saisie.observations,
        "justification_ecart": saisie.justification_ecart,
    }


class NoteItem(BaseModel):
    item_id: int
    note: Optional[float] = None


class EnregistrerLot(BaseModel):
    bloc_id: int
    notes: List[NoteItem] = []
    eliminatoires: List[int] = []


@router.get("/{session_id}/pratique/saisie/{saisie_id}/testeurs-habilites")
def testeurs_habilites_saisie(session_id: int, saisie_id: int,
                              db: DBSession = Depends(get_db),
                              famille: str = "", categorie: str = None, options: str = None):
    """Liste des testeurs habilites pour la saisie en ligne (terrain, PIN formateur)."""
    from app.models.testeur import Testeur
    from app.models.habilitation_testeur import HabilitationTesteur as _HT
    if not famille:
        raise HTTPException(422, "Parametre famille requis")
    req = set(o.strip().upper() for o in (options or "").split(",") if o.strip())
    cats_requises = set()
    if categorie:
        cats_requises.add(categorie)
    for o in req:
        cats_requises.add("OPT-" + o)

    rows = (
        db.query(Testeur, _HT)
        .join(_HT, _HT.testeur_id == Testeur.id)
        .filter(
            _HT.famille == famille,
            _HT.actif == True,
            Testeur.actif == True,
            Testeur.etat == "actif",
        )
        .order_by(Testeur.nom, Testeur.prenom)
        .all()
    )

    cats_par_testeur = {}
    testeur_info = {}
    for t, hab in rows:
        cats_par_testeur.setdefault(t.id, set()).add(hab.categorie)
        testeur_info[t.id] = t

    out = []
    for tid, cats in cats_par_testeur.items():
        if cats_requises.issubset(cats):
            t = testeur_info[tid]
            out.append({"id": t.id, "nom": t.nom, "prenom": t.prenom})
    return out


@router.post("/{session_id}/pratique/saisie/{saisie_id}/enregistrer")
def enregistrer_lot(session_id: int, saisie_id: int, data: EnregistrerLot,
                    db: DBSession = Depends(get_db)):
    """Sauvegarde fil de l'eau : upsert d'un lot de notes + eliminatoires pour UN bloc."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    bloc = db.query(SaisieBloc).filter(
        SaisieBloc.id == data.bloc_id, SaisieBloc.saisie_id == saisie_id).first()
    if not bloc:
        raise HTTPException(404, "Bloc introuvable pour cette saisie")

    for n in data.notes:
        existing = db.query(SaisieItemNote).filter(
            SaisieItemNote.bloc_id == bloc.id,
            SaisieItemNote.item_id == n.item_id).first()
        if existing:
            existing.note = n.note
        else:
            db.add(SaisieItemNote(bloc_id=bloc.id, item_id=n.item_id, note=n.note))

    db.query(SaisieEliminatoire).filter(SaisieEliminatoire.bloc_id == bloc.id).delete()
    for crit_id in data.eliminatoires:
        db.add(SaisieEliminatoire(bloc_id=bloc.id, critere_id=crit_id))

    db.commit()
    return {"message": "Enregistre", "bloc_id": bloc.id}


@router.get("/{session_id}/pratique/saisie/{saisie_id}/calculer")
def calculer(session_id: int, saisie_id: int, db: DBSession = Depends(get_db)):
    """Appelle le moteur et renvoie la proposition detaillee (sans rien valider)."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")
    res = calculer_saisie(saisie, db)
    return res


@router.get("/{session_id}/pratique/resultat/{jour_test_id}/{stagiaire_id}/{categorie}/pdf")
def pdf_resultat_pratique(session_id: int, jour_test_id: int, stagiaire_id: int,
                          categorie: str, request: Request,
                          db: DBSession = Depends(get_db)):
    """PDF de resultat pratique (genere a la volee, jamais stocke)."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO as _BIO
    from app.services.pdf_resultat_pratique import generer_pdf_resultat_pratique
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    saisie = (
        db.query(SaisiePratique)
        .filter(
            SaisiePratique.jour_test_id == jour_test_id,
            SaisiePratique.stagiaire_id == stagiaire_id,
            SaisiePratique.categorie == categorie,
            SaisiePratique.statut == "valide",
        )
        .order_by(SaisiePratique.id.desc())
        .first()
    )
    if not saisie:
        raise HTTPException(status_code=404,
                            detail="Aucun resultat pratique valide en ligne pour ce candidat / cette categorie")
    try:
        pdf_bytes = generer_pdf_resultat_pratique(saisie.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur generation PDF : {e}")
    return StreamingResponse(
        _BIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=resultat_pratique_{stagiaire_id}_{categorie}.pdf"},
    )


class ValiderSaisie(BaseModel):
    testeur_id: int
    testeur_nom: Optional[str] = None
    signature_testeur: str
    observations: Optional[str] = None
    justification_ecart: Optional[str] = None
    decision_base: bool
    decisions_options: dict = {}


@router.post("/{session_id}/pratique/saisie/{saisie_id}/valider")
def valider(session_id: int, saisie_id: int, data: ValiderSaisie,
            db: DBSession = Depends(get_db)):
    """Validation testeur : calcule, ecrit la synthese dans les blocs, ecrit le
    resultat dans SessionEpreuve, exige une justification si echec."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    from app.models.habilitation_testeur import HabilitationTesteur as _HT
    from app.models.session import Session as _Sess
    _jour = db.query(JourTest).filter(JourTest.id == saisie.jour_test_id).first()
    _sess = db.query(_Sess).filter(_Sess.id == _jour.session_id).first() if _jour else None
    _fam = _sess.famille if _sess else ""
    hab = db.query(_HT).filter(
        _HT.testeur_id == data.testeur_id,
        _HT.famille == _fam,
        _HT.categorie == saisie.categorie,
        _HT.actif == True,
    ).first()
    if not hab:
        raise HTTPException(422, "Testeur non habilite pour %s %s." % (_fam, saisie.categorie))
    _codes_opt = set()
    for _b in db.query(SaisieBloc).filter(SaisieBloc.saisie_id == saisie.id, SaisieBloc.type == "option").all():
        _g = db.query(GrillePratique).filter(GrillePratique.id == _b.grille_id).first()
        if _g and _g.code_option:
            _codes_opt.add(_g.code_option)
    if "PE" in _codes_opt and not hab.option_pe:
        raise HTTPException(422, "Testeur non habilite pour l'option Porte-engins (PE).")
    if "TEL" in _codes_opt and not hab.option_tel:
        raise HTTPException(422, "Testeur non habilite pour l'option Telecommande (TEL).")

    if not (data.signature_testeur or "").strip():
        raise HTTPException(422, "Signature du testeur obligatoire.")

    res = appliquer_resultats(saisie, db)

    if res["base"] and (not res["base"]["reussi"]) and data.decision_base:
        raise HTTPException(422,
            "Echec au test : le resultat ne peut pas etre transforme en reussite. "
            "NORYX n'autorise jamais le repechage d'un echec calcule.")
    for opt in res["options"]:
        code = opt.get("code_option")
        if code and (not opt["reussi"]) and data.decisions_options.get(code) is True:
            raise HTTPException(422,
                "Echec a l'option %s : le resultat ne peut pas etre transforme en reussite." % code)

    echec = (not data.decision_base) or any(v is False for v in data.decisions_options.values())
    if not res["base_reussie"]:
        echec = True
    if any(not o["reussi"] for o in res["options"]):
        echec = True
    if echec and not (data.justification_ecart or "").strip():
        raise HTTPException(422, "Justification (commentaire testeur) obligatoire en cas d'echec.")

    saisie.testeur_id = data.testeur_id
    saisie.testeur_nom = data.testeur_nom
    saisie.signature_testeur = data.signature_testeur
    saisie.observations = data.observations
    saisie.justification_ecart = data.justification_ecart
    saisie.resultat_propose = res["base_reussie"]
    saisie.resultat_valide = data.decision_base
    saisie.statut = "valide"
    saisie.date_validation = datetime.utcnow()

    jour = db.query(JourTest).filter(JourTest.id == saisie.jour_test_id).first()
    epreuve = None
    if jour:
        epreuve = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == jour.session_id,
            SessionEpreuve.stagiaire_id == saisie.stagiaire_id,
            SessionEpreuve.categorie == saisie.categorie,
        ).first()
    codes_acquis = []
    if data.decision_base:
        for code, ok in data.decisions_options.items():
            if ok:
                codes_acquis.append(code)
    famille_obj = db.query(Famille).filter(Famille.code == _fam).first()
    cat = db.query(Categorie).filter(
        Categorie.famille_id == (famille_obj.id if famille_obj else 0),
        Categorie.code == saisie.categorie).first()
    incluse_codes = {
        o.code_option for o in db.query(OptionCategorie).filter(
            OptionCategorie.famille == _fam,
            OptionCategorie.categorie == saisie.categorie,
            OptionCategorie.incluse == True).all()
    }
    nb_fac = len([c for c in codes_acquis if c not in incluse_codes])
    ut_val = (cat.ut_pratique if cat and cat.ut_pratique else 1.0) + nb_fac * 0.5
    note_t = "Saisie en ligne - base %s/%s" % (
        res["base"]["note_globale"], res["base"]["note_max"]) if res["base"] else None

    if epreuve:
        epreuve.testeur_id = data.testeur_id
        epreuve.obtenue = data.decision_base
        epreuve.options_obtenues = ",".join(codes_acquis) if codes_acquis else None
        epreuve.note_testeur = note_t
        epreuve.ut = ut_val
    else:
        epreuve = SessionEpreuve(
            session_id=(_jour.session_id if _jour else session_id),
            stagiaire_id=saisie.stagiaire_id,
            testeur_id=data.testeur_id,
            date=(_jour.date if _jour else None),
            famille=_fam,
            categorie=saisie.categorie,
            ut=ut_val,
            obtenue=data.decision_base,
            note_testeur=note_t,
            options_obtenues=",".join(codes_acquis) if codes_acquis else None,
        )
        db.add(epreuve)

    db.commit()
    return {"message": "Validee", "resultat": res}


@router.post("/{session_id}/pratique/saisie/{saisie_id}/rouvrir")
def rouvrir(session_id: int, saisie_id: int, db: DBSession = Depends(get_db)):
    """Rouvre une saisie validee pour modification (statut -> en_cours)."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")
    saisie.statut = "en_cours"
    saisie.date_validation = None
    db.commit()
    return {"message": "Reouverte", "saisie_id": saisie.id}


class SupprimerSaisie(BaseModel):
    pin: str


@router.delete("/{session_id}/pratique/saisie/{saisie_id}")
def supprimer(session_id: int, saisie_id: int, data: SupprimerSaisie,
              db: DBSession = Depends(get_db)):
    """Supprime la saisie (cascade) et reinitialise le resultat dans SessionEpreuve. PIN admin."""
    if not data.pin or data.pin != get_pin_admin(db):
        raise HTTPException(403, "Code PIN administrateur incorrect")
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    # Hard delete symetrique a la voie manuelle (delete_epreuve) :
    # on supprime completement la SessionEpreuve liee (meme triplet),
    # au lieu de la vider et laisser une ligne d'epreuve fantome.
    jour = db.query(JourTest).filter(JourTest.id == saisie.jour_test_id).first()
    epreuve_supprimee = False
    if jour:
        epreuve = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == jour.session_id,
            SessionEpreuve.stagiaire_id == saisie.stagiaire_id,
            SessionEpreuve.categorie == saisie.categorie,
        ).first()
        if epreuve:
            db.delete(epreuve)
            epreuve_supprimee = True

    db.delete(saisie)  # cascade ORM -> blocs, notes, eliminatoires
    db.commit()
    return {"message": "Supprimee", "epreuve_supprimee": epreuve_supprimee}
