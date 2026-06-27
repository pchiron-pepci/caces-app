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


@router.post("/{session_id}/pratique/saisie/{jour_test_id}/{stagiaire_id}/{categorie}/ouvrir")
def ouvrir_saisie(session_id: int, jour_test_id: int, stagiaire_id: int, categorie: str,
                  db: DBSession = Depends(get_db)):
    """Ouvre (ou reprend) la saisie pour un test PLANIFIE : jour + candidat + categorie.
    Le bon adressage : a partir de la categorie programmee, va chercher la grille base
    + les grilles d'options planifiees (obligatoires ou facultatives) pour ce candidat.
    Aucun SessionEpreuve cree a ce stade (cree a la validation, comme le manuel)."""
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

    # Reprise : saisie en cours existante pour (jour, candidat, categorie) ?
    saisie = db.query(SaisiePratique).filter(
        SaisiePratique.jour_test_id == jour_test_id,
        SaisiePratique.stagiaire_id == stagiaire_id,
        SaisiePratique.categorie == categorie,
    ).first()
    reprise = saisie is not None

    # Options actuellement planifiees pour CETTE categorie (source de verite)
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

    if not saisie:
        saisie = SaisiePratique(
            jour_test_id=jour_test_id, stagiaire_id=stagiaire_id, categorie=categorie,
            mode=_mode_saisie(db), statut="en_cours",
        )
        db.add(saisie)
        db.flush()

        # Bloc base : grille de la categorie programmee
        grille_base = db.query(GrillePratique).filter(
            GrillePratique.recommandation == reco,
            GrillePratique.categorie == categorie,
            GrillePratique.type == "base", GrillePratique.actif == True,
        ).first()
        if not grille_base:
            raise HTTPException(404, "Aucune grille pratique pour %s %s" % (reco, categorie))
        db.add(SaisieBloc(saisie_id=saisie.id, grille_id=grille_base.id, type="base"))

        for code in codes_planif:
            g_opt = _grille_option(code)
            if g_opt:
                db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_opt.id, type="option"))
        db.commit()
    else:
        # RESYNC a la reprise : la planification prime.
        blocs_opt = {}
        for b in db.query(SaisieBloc).filter(SaisieBloc.saisie_id == saisie.id, SaisieBloc.type == "option").all():
            g = db.query(GrillePratique).filter(GrillePratique.id == b.grille_id).first()
            if g and g.code_option:
                blocs_opt[g.code_option] = b

        # (a) Ajouter les options planifiees qui n'ont pas de bloc
        for code in codes_planif:
            if code not in blocs_opt:
                g_opt = _grille_option(code)
                if g_opt:
                    db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_opt.id, type="option"))

        # (b) Retirer les blocs d'options qui ne sont plus planifies — la planification prime,
        # hard delete systematique (notes comprises), sans confirmation.
        for code, b in blocs_opt.items():
            if code not in codes_planif:
                db.query(SaisieItemNote).filter(SaisieItemNote.bloc_id == b.id).delete()
                db.query(SaisieEliminatoire).filter(SaisieEliminatoire.bloc_id == b.id).delete()
                db.delete(b)
        db.commit()

    # Construire la reponse : blocs + grilles + notes deja saisies (reprise)
    blocs_out = []
    for bloc in db.query(SaisieBloc).filter(SaisieBloc.saisie_id == saisie.id).all():
        grille = db.query(GrillePratique).filter(GrillePratique.id == bloc.grille_id).first()
        notes = {n.item_id: n.note for n in db.query(SaisieItemNote).filter(
            SaisieItemNote.bloc_id == bloc.id).all()}
        elim = [e.critere_id for e in db.query(SaisieEliminatoire).filter(
            SaisieEliminatoire.bloc_id == bloc.id).all()]
        blocs_out.append({
            "bloc_id": bloc.id, "grille": _grille_dict(grille, db),
            "notes_saisies": notes, "eliminatoires_coches": elim,
        })

    return {
        "saisie_id": saisie.id, "mode": saisie.mode, "statut": saisie.statut,
        "reprise": reprise, "blocs": blocs_out,
    }


class NoteItem(BaseModel):
    item_id: int
    note: Optional[float] = None


class EnregistrerLot(BaseModel):
    bloc_id: int
    notes: List[NoteItem] = []
    eliminatoires: List[int] = []   # critere_id coches pour ce bloc


@router.post("/{session_id}/pratique/saisie/{saisie_id}/enregistrer")
def enregistrer_lot(session_id: int, saisie_id: int, data: EnregistrerLot,
                    db: DBSession = Depends(get_db)):
    """Sauvegarde fil de l'eau : upsert d'un lot de notes + eliminatoires pour UN bloc.
    Appele automatiquement par l'ecran (si reseau) ou au bouton Enregistrer."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    bloc = db.query(SaisieBloc).filter(
        SaisieBloc.id == data.bloc_id, SaisieBloc.saisie_id == saisie_id).first()
    if not bloc:
        raise HTTPException(404, "Bloc introuvable pour cette saisie")

    # Upsert des notes
    for n in data.notes:
        existing = db.query(SaisieItemNote).filter(
            SaisieItemNote.bloc_id == bloc.id,
            SaisieItemNote.item_id == n.item_id).first()
        if existing:
            existing.note = n.note
        else:
            db.add(SaisieItemNote(bloc_id=bloc.id, item_id=n.item_id, note=n.note))

    # Remplace l'ensemble des eliminatoires coches pour ce bloc
    db.query(SaisieEliminatoire).filter(SaisieEliminatoire.bloc_id == bloc.id).delete()
    for crit_id in data.eliminatoires:
        db.add(SaisieEliminatoire(bloc_id=bloc.id, critere_id=crit_id))

    db.commit()
    return {"message": "Enregistre", "bloc_id": bloc.id}


@router.get("/{session_id}/pratique/saisie/{saisie_id}/calculer")
def calculer(session_id: int, saisie_id: int, db: DBSession = Depends(get_db)):
    """Appelle le moteur et renvoie la proposition detaillee (sans rien valider).
    Sert a l'affichage live de la proposition dans l'ecran."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")
    res = calculer_saisie(saisie, db)
    return res


class ValiderSaisie(BaseModel):
    testeur_id: int
    testeur_nom: Optional[str] = None
    observations: Optional[str] = None
    justification_ecart: Optional[str] = None
    # decision testeur (peut differer de la proposition)
    decision_base: bool
    decisions_options: dict = {}   # { "PE": true, "TEL": false }


@router.post("/{session_id}/pratique/saisie/{saisie_id}/valider")
def valider(session_id: int, saisie_id: int, data: ValiderSaisie,
            db: DBSession = Depends(get_db)):
    """Validation testeur : calcule, ecrit la synthese dans les blocs, ecrit le
    resultat dans SessionEpreuve (comme la voie manuelle), exige une justification si echec."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    # Testeur obligatoire et habilite famille + categorie + TOUTES les options du candidat
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

    # Calcule et ecrit la synthese dans les SaisieBloc (verdict du moteur)
    res = appliquer_resultats(saisie, db)

    # GARDE REGLEMENTAIRE : pas de repechage. Le testeur ne transforme jamais un echec calcule en reussite.
    if res["base"] and (not res["base"]["reussi"]) and data.decision_base:
        raise HTTPException(422,
            "Echec au test : le resultat ne peut pas etre transforme en reussite. "
            "NORYX n'autorise jamais le repechage d'un echec calcule.")
    for opt in res["options"]:
        code = opt.get("code_option")
        if code and (not opt["reussi"]) and data.decisions_options.get(code) is True:
            raise HTTPException(422,
                "Echec a l'option %s : le resultat ne peut pas etre transforme en reussite." % code)

    # Justification obligatoire pour TOUT echec (calcule ou decide par le testeur)
    echec = (not data.decision_base) or any(v is False for v in data.decisions_options.values())
    if res["base"] and not res["base"]["reussi"]:
        echec = True
    if any(not o["reussi"] for o in res["options"]):
        echec = True
    if echec and not (data.justification_ecart or "").strip():
        raise HTTPException(422, "Justification (commentaire testeur) obligatoire en cas d'echec.")

    saisie.testeur_nom = data.testeur_nom
    saisie.observations = data.observations
    saisie.justification_ecart = data.justification_ecart
    saisie.resultat_propose = res["base_reussie"] if res["base"] else None
    saisie.resultat_valide = data.decision_base
    saisie.statut = "valide"
    saisie.date_validation = datetime.utcnow()

    # Ecriture dans SessionEpreuve (meme champs que la voie manuelle)
    # Recherche par (session, stagiaire, categorie) — la saisie ne stocke plus d'epreuve_id
    jour = db.query(JourTest).filter(JourTest.id == saisie.jour_test_id).first()
    epreuve = None
    if jour:
        epreuve = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == jour.session_id,
            SessionEpreuve.stagiaire_id == saisie.stagiaire_id,
            SessionEpreuve.categorie == saisie.categorie,
        ).first()
    if epreuve:
        epreuve.testeur_id = data.testeur_id
        epreuve.obtenue = data.decision_base
        # options acquises = decisions testeur True ET base obtenue
        codes_acquis = []
        if data.decision_base:
            for code, ok in data.decisions_options.items():
                if ok:
                    codes_acquis.append(code)
        epreuve.options_obtenues = ",".join(codes_acquis) if codes_acquis else None
        # note testeur = note globale de la base
        if res["base"]:
            epreuve.note_testeur = "Saisie en ligne - base %s/%s" % (
                res["base"]["note_globale"], res["base"]["note_max"])
        # recalcul UT (base + options facultatives acquises)
        fam = epreuve.famille
        famille_obj = db.query(Famille).filter(Famille.code == fam).first()
        cat = db.query(Categorie).filter(
            Categorie.famille_id == (famille_obj.id if famille_obj else 0),
            Categorie.code == epreuve.categorie).first()
        incluse_codes = {
            o.code_option for o in db.query(OptionCategorie).filter(
                OptionCategorie.famille == fam,
                OptionCategorie.categorie == epreuve.categorie,
                OptionCategorie.incluse == True).all()
        }
        nb_fac = len([c for c in codes_acquis if c not in incluse_codes])
        epreuve.ut = (cat.ut_pratique if cat and cat.ut_pratique else 1.0) + nb_fac * 0.5
    else:
        # L'epreuve n'existe pas encore : la creer depuis la planification (comme le manuel)
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
        ut = (cat.ut_pratique if cat and cat.ut_pratique else 1.0) + nb_fac * 0.5
        note_t = None
        if res["base"]:
            note_t = "Saisie en ligne - base %s/%s" % (res["base"]["note_globale"], res["base"]["note_max"])
        epreuve = SessionEpreuve(
            session_id=(_jour.session_id if _jour else session_id),
            stagiaire_id=saisie.stagiaire_id,
            testeur_id=data.testeur_id,
            date=(_jour.date if _jour else None),
            famille=_fam,
            categorie=saisie.categorie,
            ut=ut,
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
    """Supprime la saisie (cascade blocs/notes/eliminatoires) et reinitialise
    le resultat dans SessionEpreuve. Protege par PIN admin (dans le corps)."""
    if not data.pin or data.pin != get_pin_admin(db):
        raise HTTPException(403, "Code PIN administrateur incorrect")
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    jour = db.query(JourTest).filter(JourTest.id == saisie.jour_test_id).first()
    if jour:
        epreuve = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == jour.session_id,
            SessionEpreuve.stagiaire_id == saisie.stagiaire_id,
            SessionEpreuve.categorie == saisie.categorie,
        ).first()
        if epreuve:
            epreuve.obtenue = None
            epreuve.options_obtenues = None
            epreuve.note_testeur = None

    db.delete(saisie)   # cascade sur blocs -> notes / eliminatoires
    db.commit()
    return {"message": "Supprimee"}
