from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.jour_test import JourTest, ResultatTheorie
from app.models.session_epreuve import SessionEpreuve
from app.models.session import Session as SessionModel
from app.models.caces_obtenu import CacesObtenu
from app.models.session_candidat import SessionCandidat


def _date_echeance(famille: str, date_obt: date) -> date:
    ans = 10 if famille == "R482" else 5
    try:
        return date(date_obt.year + ans, date_obt.month, date_obt.day) - timedelta(days=1)
    except ValueError:
        return date(date_obt.year + ans, 3, 1) - timedelta(days=1)


def _date_initiale_depuis_echeance(famille: str, date_ech: date) -> date:
    """
    Inverse exact de _date_echeance : retrouve la date d'obtention du CACES INITIAL
    a partir de la date d'echeance. Vrai pour un initial (retombe sur sa date d'obtention)
    comme pour une extension (retombe sur la date du CACES initial, car l'extension herite
    de l'echeance de l'initial). Permet de tester la dispense des 12 mois sans distinguer
    initial/extension.
    miroir de _date_echeance : echeance = date_obt + N ans - 1j  =>  date_obt = echeance - N ans + 1j
    """
    ans = 10 if famille == "R482" else 5
    try:
        return date(date_ech.year - ans, date_ech.month, date_ech.day) + timedelta(days=1)
    except ValueError:
        # 29 fevrier inexistant en (annee - ans) → 1er mars
        return date(date_ech.year - ans, 3, 1)


def _chercher_theorie_autre_session(db, stagiaire_id, session_id_pratique, famille, date_pratique, statut_filtre):
    """
    Cherche un ResultatTheorie.obtenue=True hors de la session de pratique,
    même famille, théorie dans les 12 mois précédant la pratique
    (date_theo <= date_prat et >= date_prat - 1 an + 1 jour).
    statut_filtre : "ouvert" (statut != terminee) ou "terminee".
    """
    try:
        limite_avant = date(date_pratique.year - 1, date_pratique.month, date_pratique.day) + timedelta(days=1)
    except ValueError:
        # 29 février inexistant en année-1 → 1er mars année-1
        limite_avant = date(date_pratique.year - 1, 3, 1)

    q = (
        db.query(ResultatTheorie)
        .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
        .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
        .filter(
            ResultatTheorie.stagiaire_id == stagiaire_id,
            ResultatTheorie.obtenue == True,
            ResultatTheorie.bloque != True,
            ResultatTheorie.session_id != session_id_pratique,
            SessionModel.famille == famille,
            JourTest.date >= limite_avant,
            JourTest.date <= date_pratique,
        )
    )
    if statut_filtre == "ouvert":
        q = q.filter(SessionModel.statut != "terminee")
    else:
        q = q.filter(SessionModel.statut == "terminee")

    return q.order_by(JourTest.date.desc(), ResultatTheorie.id.desc()).first()


def _calculer_pour_epreuve(ep: SessionEpreuve, db) -> dict | None:
    """
    Calcule date_obtention, date_echeance et post_cloture pour une épreuve pratique réussie.
    Retourne None si aucune théorie réussie n'est trouvée.

    Priorités de recherche théorie :
      1. Même session
      2. Autre session ouverte (statut != terminee), même famille, ±12 mois → continuité
      3. Autre session clôturée (statut == terminee), même famille, ±12 mois → extension

    Règles de calcul (appliquées dans cet ordre) :
      Cas 3 : théorie > pratique (TOUTES priorités, y compris extension)
                → date_obtention = date_theo
                → date_echeance = _date_echeance(famille, date_theo)
      Cas 1/2 : théorie ≤ pratique, non-extension
                → date_obtention = date_prat
                → date_echeance = _date_echeance(famille, date_prat)
      Cas 4 : extension (session clôturée, post_cloture=True) + théorie ≤ pratique
                → date_obtention = date_prat
                → date_echeance = None (déterminée en passe 2 via caces_initial)
    """
    # --- Cas DISPENSE EXTERNE : dates saisies par l'operateur, pas de theorie interne ---
    sc = (
        db.query(SessionCandidat)
        .filter(
            SessionCandidat.session_id == ep.session_id,
            SessionCandidat.stagiaire_id == ep.stagiaire_id,
            SessionCandidat.actif == True,
        )
        .first()
    )
    if sc and sc.theorie_dispensee and sc.dispense_origine == "externe":
        if not sc.dispense_echeance:
            return None  # securite : echeance non saisie (ne devrait pas arriver, garde-fou au save)
        return {
            "date_obtention":         ep.date,
            "date_echeance":          sc.dispense_echeance,
            "options_obtenues":       ep.options_obtenues,
            "post_cloture":           False,
            "resultat_theorie_id":    None,
            "theorie_source_id":      None,
            "dispense_externe_sc_id": sc.id,
        }

    # --- Selection de la theorie : la PLUS RECENTE parmi les 3 sources, portier 12 mois partout ---
    # Borne basse du portier (12 mois avant la pratique)
    try:
        _limite = date(ep.date.year - 1, ep.date.month, ep.date.day) + timedelta(days=1)
    except ValueError:
        _limite = date(ep.date.year - 1, 3, 1)

    def _date_rt(_rt):
        if not _rt:
            return None
        _jt = db.query(JourTest).filter(JourTest.id == _rt.jour_test_id).first()
        return _jt.date if _jt and _jt.date else None

    # P1 : meme session (mono-famille), AVEC portier 12 mois
    rt_p1 = (
        db.query(ResultatTheorie)
        .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
        .filter(
            ResultatTheorie.stagiaire_id == ep.stagiaire_id,
            ResultatTheorie.session_id == ep.session_id,
            ResultatTheorie.obtenue == True,
            ResultatTheorie.bloque != True,
            JourTest.date >= _limite,
            JourTest.date <= ep.date,
        )
        .order_by(JourTest.date.desc(), ResultatTheorie.id.desc())
        .first()
    )
    # P2 : autre session ouverte / P3 : autre session clôturee
    rt_p2 = _chercher_theorie_autre_session(db, ep.stagiaire_id, ep.session_id, ep.famille, ep.date, "ouvert")
    rt_p3 = _chercher_theorie_autre_session(db, ep.stagiaire_id, ep.session_id, ep.famille, ep.date, "terminee")

    # Arbitrage : la plus recente. Egalite -> P1 puis P2 puis P3.
    candidats = []
    if rt_p1: candidats.append((_date_rt(rt_p1), 0, rt_p1, False))  # source 0 = meme session
    if rt_p2: candidats.append((_date_rt(rt_p2), 1, rt_p2, False))  # source 1 = autre ouverte
    if rt_p3: candidats.append((_date_rt(rt_p3), 2, rt_p3, True))   # source 2 = autre clôturee (post_cloture)
    candidats = [c for c in candidats if c[0] is not None]

    rt = None
    post_cloture = False
    if candidats:
        # tri : date desc, puis priorite source asc (P1<P2<P3) pour departager les egalites
        candidats.sort(key=lambda c: (c[0], -c[1]), reverse=True)
        _, _src, rt, post_cloture = candidats[0]

    if not rt:
        # Cas 6 (spec unifiee) — CACES existant comme base d'extension (echeance heritee)
        try:
            limite_avant = date(ep.date.year - 1, ep.date.month, ep.date.day) + timedelta(days=1)
        except ValueError:
            limite_avant = date(ep.date.year - 1, 3, 1)
        caces_source = None
        for c in (
            db.query(CacesObtenu)
            .filter(
                CacesObtenu.stagiaire_id == ep.stagiaire_id,
                CacesObtenu.famille == ep.famille,
                CacesObtenu.statut.in_(["valide", "a_valider"]),
                CacesObtenu.date_echeance.isnot(None),
                CacesObtenu.session_id != ep.session_id,
            )
            .order_by(CacesObtenu.date_echeance.desc())
            .all()
        ):
            origine = _date_initiale_depuis_echeance(c.famille, c.date_echeance)
            if limite_avant <= origine <= ep.date:
                caces_source = c
                break
        if caces_source is None:
            return None
        return {
            "date_obtention":         ep.date,
            "date_echeance":          caces_source.date_echeance,
            "options_obtenues":       ep.options_obtenues,
            "post_cloture":           False,
            "resultat_theorie_id":    None,
            "theorie_source_id":      None,
            "dispense_externe_sc_id": None,
            "caces_source_id":        caces_source.id,
        }

    jour_theo = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
    if not jour_theo or not jour_theo.date:
        return None

    date_theo = jour_theo.date
    date_prat = ep.date

    if date_theo > date_prat:
        # Cas 3 : théorie après pratique (toutes priorités) → tout depuis date_theo
        date_obtention = date_theo
        echeance = _date_echeance(ep.famille, date_theo)
    elif post_cloture:
        # Cas 4 : extension + théorie ≤ pratique → date pratique, écheance déterminée en passe 2
        date_obtention = date_prat
        echeance = None
    else:
        # Cas 1/2/5 : theorie <= pratique. Chercher un CACES de base d'une AUTRE session
        # (natif ou reprise) dont l'origine reconstituee est dans les 12 mois ET non posterieure
        # a la theorie native -> alors EXTENSION (echeance heritee, cas 5/6). Sinon calcul (cas 2).
        date_obtention = date_prat
        _caces_base = None
        for _c in (
            db.query(CacesObtenu)
            .filter(
                CacesObtenu.stagiaire_id == ep.stagiaire_id,
                CacesObtenu.famille == ep.famille,
                CacesObtenu.statut.in_(["valide", "a_valider"]),
                CacesObtenu.date_echeance.isnot(None),
                CacesObtenu.session_id != ep.session_id,
            )
            .order_by(CacesObtenu.date_echeance.desc())
            .all()
        ):
            _orig = _date_initiale_depuis_echeance(_c.famille, _c.date_echeance)
            # origine du CACES de base dans la fenetre 12 mois ET non posterieure a la theorie native
            if _limite <= _orig <= ep.date and _orig <= date_theo:
                _caces_base = _c
                break
        if _caces_base is not None:
            # EXTENSION : echeance heritee (resolue en passe 2 via caces_source_id)
            return {
                "date_obtention":         date_prat,
                "date_echeance":          _caces_base.date_echeance,
                "options_obtenues":       ep.options_obtenues,
                "post_cloture":           True,
                "resultat_theorie_id":    None,
                "theorie_source_id":      rt.id if rt else None,
                "dispense_externe_sc_id": None,
                "caces_source_id":        _caces_base.id,
            }
        # Cas 2 pur : pas de CACES de base autre session -> calcul normal
        echeance = _date_echeance(ep.famille, date_prat)

    return {
        "date_obtention":         date_obtention,
        "date_echeance":          echeance,
        "options_obtenues":       ep.options_obtenues,
        "post_cloture":           post_cloture,
        "resultat_theorie_id":    (rt.id if (rt and not post_cloture) else None),
        "theorie_source_id":      (rt.id if rt else None),
        "dispense_externe_sc_id": None,
    }


def _appliquer_caces(db, ep, calc, caces_initial_id=None):
    existing = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == ep.stagiaire_id,
        CacesObtenu.session_id == ep.session_id,
        CacesObtenu.categorie == ep.categorie,
    ).first()
    if existing:
        if existing.statut == "a_valider":
            existing.date_obtention         = calc["date_obtention"]
            existing.date_echeance          = calc["date_echeance"]
            existing.options_obtenues       = calc["options_obtenues"]
            existing.post_cloture           = calc["post_cloture"]
            existing.resultat_theorie_id    = calc["resultat_theorie_id"]
            existing.caces_initial_id       = caces_initial_id
            existing.dispense_externe_sc_id = calc["dispense_externe_sc_id"]
        elif existing.statut == "annule":
            existing.statut                 = "a_valider"
            existing.numero_ordre           = None
            existing.date_obtention         = calc["date_obtention"]
            existing.date_echeance          = calc["date_echeance"]
            existing.options_obtenues       = calc["options_obtenues"]
            existing.post_cloture           = calc["post_cloture"]
            existing.resultat_theorie_id    = calc["resultat_theorie_id"]
            existing.caces_initial_id       = caces_initial_id
            existing.dispense_externe_sc_id = calc["dispense_externe_sc_id"]
        return
    db.add(CacesObtenu(
        stagiaire_id=ep.stagiaire_id,
        session_id=ep.session_id,
        famille=ep.famille,
        categorie=ep.categorie,
        options_obtenues=calc["options_obtenues"],
        date_obtention=calc["date_obtention"],
        date_echeance=calc["date_echeance"],
        statut="a_valider",
        post_cloture=calc["post_cloture"],
        resultat_theorie_id=calc["resultat_theorie_id"],
        caces_initial_id=caces_initial_id,
        dispense_externe_sc_id=calc["dispense_externe_sc_id"],
    ))


def calculer_et_synchroniser(db: Session) -> list:
    """
    Deux passes :
    - Passe 1 : non-extensions (post_cloture=False) → crée/met à jour + commit
    - Passe 2 : extensions (post_cloture=True) → retrouve le CACES initial via
      resultat_theorie_id, applique son écheance, remplit caces_initial_id

    Comportement statuts identique dans les deux passes :
    - a_valider → recalcule et met à jour
    - annule → remet en a_valider avec nouvelles dates
    - valide → intouchable

    Appelé automatiquement lors de la clôture d'une session.
    """
    epreuves_ok = db.query(SessionEpreuve).filter(
        SessionEpreuve.obtenue == True,
        SessionEpreuve.bloque != True,
    ).all()

    extensions_differees = []  # (ep, calc) à traiter en passe 2

    # --- PASSE 1 : non-extensions ---
    for ep in epreuves_ok:
        calc = _calculer_pour_epreuve(ep, db)
        if calc is None:
            continue
        if calc["post_cloture"]:
            extensions_differees.append((ep, calc))
            continue
        caces_init_id = calc.pop("caces_source_id", None)
        _appliquer_caces(db, ep, calc, caces_initial_id=caces_init_id)

    db.commit()  # tous les non-extensions ont leur resultat_theorie_id en base

    # --- PASSE 2 : extensions ---
    for ep, calc in extensions_differees:
        initial = (
            db.query(CacesObtenu)
            .filter(
                CacesObtenu.resultat_theorie_id == calc["theorie_source_id"],
                CacesObtenu.post_cloture == False,
                CacesObtenu.statut.in_(["a_valider", "valide"]),
            )
            .first()
        )
        if initial:
            calc["date_echeance"] = initial.date_echeance
            caces_init_id = initial.id
        else:
            # fallback : initial introuvable (incohérence/annulé) → calcul normal
            calc["date_echeance"] = _date_echeance(ep.famille, calc["date_obtention"])
            caces_init_id = None
        _appliquer_caces(db, ep, calc, caces_initial_id=caces_init_id)

    db.commit()

    # --- NETTOYAGE : supprimer les CACES a_valider ORPHELINS ---
    # Un a_valider est orphelin si son (stagiaire, session, categorie) ne correspond
    # plus a aucune epreuve obtenue (ex : epreuve repassee en echec = erreur de saisie).
    # On ne touche JAMAIS les 'valide' ni les 'annule'.
    triplets_ok = {
        (e.stagiaire_id, e.session_id, e.categorie) for e in epreuves_ok
    }
    for co in db.query(CacesObtenu).filter(CacesObtenu.statut == "a_valider").all():
        if (co.stagiaire_id, co.session_id, co.categorie) not in triplets_ok:
            db.delete(co)
    db.commit()

    return (
        db.query(CacesObtenu)
        .filter(CacesObtenu.statut == "a_valider")
        .order_by(CacesObtenu.id.desc())
        .all()
    )


def limite_12_mois(date_ref):
    """Date limite de validite des 12 mois : date_ref + 1 an - 1 jour (gere le 29 fevrier)."""
    try:
        return date(date_ref.year + 1, date_ref.month, date_ref.day) - timedelta(days=1)
    except ValueError:
        return date(date_ref.year + 1, 3, 1) - timedelta(days=1)


def detecter_base_theorique(db, stagiaire_id, famille, session_id=None):
    """
    Détecte la base de dispense théorique la plus récente pour un stagiaire/famille.
    3 sources (règle 12 mois = base + 1 an - 1 jour >= aujourd'hui) :
      R1   : CACES non-extension, valide/a_valider, même famille
      R2-a : théorie de la session courante (si session_id fourni)
      R2-b : théorie orpheline d'une autre session (aucun CacesObtenu.resultat_theorie_id pointant dessus)
    Retourne {"possible": False} ou {"possible": True, "type", "date_origine",
    "reference", "date_limite_dispense", "lien", "source"}.
    NE COCHE RIEN — pure lecture/info.
    """
    candidates = []  # liste de dicts {date, type, reference, source, lien, source_id}
    today = date.today()

    # --- Source R1 : CACES (initial OU extension), meme famille, valide/a_valider, theorie initiale < 12 mois ---
    caces_list = (
        db.query(CacesObtenu)
        .filter(
            CacesObtenu.stagiaire_id == stagiaire_id,
            CacesObtenu.famille == famille,
            CacesObtenu.statut.in_(["valide", "a_valider"]),
        )
        .all()
    )
    for c in caces_list:
        if not c.date_echeance:
            continue
        date_initiale = _date_initiale_depuis_echeance(c.famille, c.date_echeance)
        if limite_12_mois(date_initiale) >= today:
            candidates.append({
                "date": date_initiale,
                "type": "caces",
                "reference": f"CACES {c.famille} cat {c.categorie}" + (f" n°{c.numero_ordre}" if c.numero_ordre else ""),
                "source": "R1",
                "source_id": c.id,
                "lien": "/caces-obtenus",
            })

    # --- Source R2-a : theorie de la SESSION COURANTE (si session_id fourni) ---
    if session_id:
        rt_courante = (
            db.query(ResultatTheorie)
            .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
            .filter(
                ResultatTheorie.stagiaire_id == stagiaire_id,
                ResultatTheorie.session_id == session_id,
                ResultatTheorie.obtenue == True,
                ResultatTheorie.bloque != True,
            )
            .order_by(JourTest.date.desc(), ResultatTheorie.id.desc())
            .first()
        )
        if rt_courante:
            jt = db.query(JourTest).filter(JourTest.id == rt_courante.jour_test_id).first()
            if jt and jt.date and limite_12_mois(jt.date) >= today:
                candidates.append({
                    "date": jt.date, "type": "theorie", "reference": "Theorie de la session courante",
                    "source": "R2-a", "source_id": rt_courante.id,
                    "lien": f"/sessions/{session_id}/projection/{rt_courante.jour_test_id}",
                })

    # --- Source R2-b : theorie ORPHELINE d'une autre session (aucun CACES rattache) ---
    rts = (
        db.query(ResultatTheorie)
        .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
        .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
        .filter(
            ResultatTheorie.stagiaire_id == stagiaire_id,
            ResultatTheorie.obtenue == True,
            ResultatTheorie.bloque != True,
            SessionModel.famille == famille,
        )
    )
    if session_id:
        rts = rts.filter(ResultatTheorie.session_id != session_id)
    for rt in rts.all():
        # orpheline = aucun CacesObtenu ne pointe vers ce ResultatTheorie
        a_un_caces = db.query(CacesObtenu).filter(CacesObtenu.resultat_theorie_id == rt.id).first()
        if a_un_caces:
            continue
        jt = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
        if jt and jt.date and limite_12_mois(jt.date) >= today:
            candidates.append({
                "date": jt.date, "type": "theorie", "reference": "Theorie (autre session)",
                "source": "R2-b", "source_id": rt.id,
                "lien": "",
            })

    if not candidates:
        return {"possible": False}

    # garder la PLUS RECENTE
    meilleure = max(candidates, key=lambda x: x["date"])
    return {
        "possible": True,
        "type": meilleure["type"],
        "date_origine": meilleure["date"].isoformat(),
        "reference": meilleure["reference"],
        "date_limite_dispense": limite_12_mois(meilleure["date"]).isoformat(),
        "lien": meilleure["lien"],
        "source": meilleure["source"],
        "source_id": meilleure["source_id"],
    }
