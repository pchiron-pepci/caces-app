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
from app.models.option_categorie import OptionCategorie
from app.models.categorie import Categorie, Famille
from app.models.grille_pratique import (
    GrillePratique, ThemePratique, PointEvaluation, ItemPratique, CritereEliminatoire,
    SaisiePratique, SaisieBloc, SaisieItemNote, SaisieEliminatoire,
)
from app.models.config_organisme import ConfigOrganisme
from app.services.calcul_pratique import calculer_saisie, appliquer_resultats
from app.config_utils import get_pin_formateur

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


@router.post("/{session_id}/pratique/saisie/{epreuve_id}/ouvrir")
def ouvrir_saisie(session_id: int, epreuve_id: int, db: DBSession = Depends(get_db)):
    """Cree (ou recupere) la saisie en cours pour une epreuve. Genere les blocs
    base + options effectivement planifiees pour le candidat."""
    epreuve = db.query(SessionEpreuve).filter(SessionEpreuve.id == epreuve_id).first()
    if not epreuve:
        raise HTTPException(404, "Epreuve introuvable")

    # Garde "une voie" : si un justificatif manuel existe deja, on bloque
    if epreuve.justificatif_cle:
        raise HTTPException(409, "Cette epreuve a deja un justificatif manuel. Supprimez-le pour saisir en ligne.")

    reco = _recommandation_from_famille(epreuve.famille)

    # Reprise : saisie en cours existante ?
    saisie = db.query(SaisiePratique).filter(
        SaisiePratique.session_epreuve_id == epreuve_id).first()
    reprise = saisie is not None

    if not saisie:
        saisie = SaisiePratique(
            session_epreuve_id=epreuve_id, mode=_mode_saisie(db), statut="en_cours",
        )
        db.add(saisie)
        db.flush()

        # Bloc base
        grille_base = db.query(GrillePratique).filter(
            GrillePratique.recommandation == reco,
            GrillePratique.categorie == epreuve.categorie,
            GrillePratique.type == "base", GrillePratique.actif == True,
        ).first()
        if not grille_base:
            raise HTTPException(404, "Aucune grille pratique pour %s %s" % (reco, epreuve.categorie))
        db.add(SaisieBloc(saisie_id=saisie.id, grille_id=grille_base.id, type="base"))

        # Blocs options planifiees pour ce candidat
        codes_planif = set()
        if epreuve.option_pe:
            codes_planif.add("PE")
        if epreuve.option_tel:
            codes_planif.add("TEL")
        for code in (epreuve.options_obtenues or "").split(","):
            if code.strip():
                codes_planif.add(code.strip())
        for code in codes_planif:
            g_opt = db.query(GrillePratique).filter(
                GrillePratique.recommandation == reco,
                GrillePratique.categorie == epreuve.categorie,
                GrillePratique.type == "option", GrillePratique.code_option == code,
                GrillePratique.actif == True,
            ).first()
            if g_opt:
                db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_opt.id, type="option"))
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
    if saisie.statut == "valide":
        raise HTTPException(409, "Saisie deja validee. Rouvrez-la pour modifier.")

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

    # Justification obligatoire si la decision base est un echec
    echec = (not data.decision_base) or any(v is False for v in data.decisions_options.values())
    if echec and not (data.justification_ecart or "").strip():
        raise HTTPException(422, "Justification obligatoire en cas d'echec.")

    # Calcule et ecrit la synthese dans les SaisieBloc
    res = appliquer_resultats(saisie, db)

    saisie.testeur_nom = data.testeur_nom
    saisie.observations = data.observations
    saisie.justification_ecart = data.justification_ecart
    saisie.resultat_propose = res["base_reussie"] if res["base"] else None
    saisie.resultat_valide = data.decision_base
    saisie.statut = "valide"
    saisie.date_validation = datetime.utcnow()

    # Ecriture dans SessionEpreuve (meme champs que la voie manuelle)
    epreuve = db.query(SessionEpreuve).filter(
        SessionEpreuve.id == saisie.session_epreuve_id).first()
    if epreuve:
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


@router.delete("/{session_id}/pratique/saisie/{saisie_id}")
def supprimer(session_id: int, saisie_id: int, db: DBSession = Depends(get_db)):
    """Supprime la saisie (cascade blocs/notes/eliminatoires) et reinitialise
    le resultat dans SessionEpreuve."""
    saisie = db.query(SaisiePratique).filter(SaisiePratique.id == saisie_id).first()
    if not saisie:
        raise HTTPException(404, "Saisie introuvable")

    epreuve = db.query(SessionEpreuve).filter(
        SessionEpreuve.id == saisie.session_epreuve_id).first()
    if epreuve:
        epreuve.obtenue = None
        epreuve.options_obtenues = None
        epreuve.note_testeur = None

    db.delete(saisie)   # cascade sur blocs -> notes / eliminatoires
    db.commit()
    return {"message": "Supprimee"}
