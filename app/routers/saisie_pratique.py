@router.post("/{session_id}/pratique/saisie/{jour_test_id}/{stagiaire_id}/{categorie}/ouvrir")
def ouvrir_saisie(session_id: int, jour_test_id: int, stagiaire_id: int, categorie: str,
                  engin2: str = None,
                  db: DBSession = Depends(get_db)):
    """Ouvre (ou reprend) la saisie pour un test PLANIFIE : jour + candidat + categorie.
    A partir de la categorie programmee, va chercher la grille base + les grilles
    d'options planifiees pour ce candidat.

    Cat A multi-engins (R.482) : 2 blocs base. Engin N°1 = PH (toujours), engin N°2
    = MB/CH/CP passe en query param `engin2` (choisi par le testeur a l'ouverture).
    Aucun SessionEpreuve cree a ce stade (cree a la validation, comme le manuel).
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

    # Cat A multi-engins : engin N°1 fige (PH) + engin N°2 au choix (MB/CH/CP).
    EST_CAT_A = (reco == "R.482" and (categorie or "").upper() == "A")
    ENGINS_N2_VALIDES = {"MB", "CH", "CP"}
    engin2_norm = (engin2 or "").strip().upper() or None

    # Reprise : saisie en cours existante pour (jour, candidat, categorie) ?
    saisie = db.query(SaisiePratique).filter(
        SaisiePratique.jour_test_id == jour_test_id,
        SaisiePratique.stagiaire_id == stagiaire_id,
        SaisiePratique.categorie == categorie,
    ).first()
    reprise = saisie is not None

    # A l'ouverture INITIALE d'une cat A, l'engin N°2 est obligatoire.
    if EST_CAT_A and not reprise:
        if engin2_norm not in ENGINS_N2_VALIDES:
            raise HTTPException(422, "Engin N°2 requis pour la categorie A (MB, CH ou CP).")

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
            # Bloc base 1 : PH (toujours)
            g_ph = _grille_base("PH")
            if not g_ph:
                raise HTTPException(404, "Grille base PH introuvable pour %s A" % reco)
            db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_ph.id, type="base"))
            # Bloc base 2 : engin choisi
            g_n2 = _grille_base(engin2_norm)
            if not g_n2:
                raise HTTPException(404, "Grille base %s introuvable pour %s A" % (engin2_norm, reco))
            db.add(SaisieBloc(saisie_id=saisie.id, grille_id=g_n2.id, type="base"))
        else:
            # Bloc base unique : grille de la categorie programmee
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
        # RESYNC a la reprise : la planification prime (options uniquement).
        # Les blocs base ne sont JAMAIS retouches a la reprise (engin deja fige).
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