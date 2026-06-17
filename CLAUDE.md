# NORYX Engins — Documentation projet

Application de pilotage CACES® & Autorisation de conduite pour PEPCI Formation.

---

## ⚠️ Règle permanente — tenue du MP

**À la fin de chaque chantier** (nouvelle fonctionnalité, correction, décision architecturale, migration), mettre à jour ce fichier CLAUDE.md **AVANT** de considérer la tâche terminée :

- Consigner ce qui a été fait (modèles/routes/templates touchés, règles métier nouvelles ou modifiées).
- Mettre à jour le tableau "Chantiers en cours / À faire" (statut à jour).
- Noter toute décision tranchée (réversibilité, gel, exceptions) pour qu'une conversation ultérieure n'ait pas à la redemander.

**Présenter en fin de réponse un court résumé "MP mis à jour :" listant les lignes ajoutées ou modifiées.**

---

## Stack technique

```
Backend    : FastAPI + SQLAlchemy ORM
Templates  : Jinja2 (rendu serveur, pas de SPA)
Base       : PostgreSQL (Render) — SQLite acceptable en dev local
Auth       : JWT via python-jose, token stocké dans localStorage
Images     : Cloudinary
Hébergement: Render.com (app caces-app, Frankfurt, Starter $7/mois)
JS         : Fichiers statiques dans static/js/ (contrainte CSP)
```

**Repo :** `github.com/pchiron-pepci/caces-app` — branch `main`
**Dev local :** Windows 11, VS Code, Python 3.14, venv
**Déploiement :** `git push` → Render redéploie automatiquement

---

## Contrainte critique : CSP

Render bloque les `onclick=` inline et les scripts inline. Toute la logique JS doit être dans `static/js/`.

**Pattern obligatoire pour tout nouveau code JS :**

```html
<!-- HTML : données dynamiques via data-* attributes -->
<button data-action="monAction" data-id="{{ item.id }}" data-nom="{{ item.nom }}">Cliquer</button>

<!-- JS : dans static/js/monfichier.js -->
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action="monAction"]');
        if (btn) maFonction(btn.dataset.id, btn.dataset.nom);
    });
});
```

Ne jamais utiliser `eval()`, `new Function()`, `setTimeout(string)`, `setInterval(string)`.

**Fichiers JS existants :**
- `static/js/testeurs.js` — CRUD testeurs
- `static/js/session_detail.js` — gestion détail session (données injectées via `data-*` sur `<div id="session-data">`)

Les pages admin.html et les pages dédiées utilisent encore des `onclick=` inline (chantier ouvert).

---

## Architecture

### Structure app/
```
app/
├── main.py          ← routes GET/POST → TemplateResponse (pages HTML)
├── database.py      ← connexion SQLAlchemy + get_db
├── models/          ← modèles ORM SQLAlchemy
├── routers/         ← routes API JSON (prefix /api/ ou /admin/)
├── schemas/         ← schémas Pydantic
└── services/        ← logique métier (tirage grilles INRS)
```

### Séparation pages / API
- `main.py` : routes qui renvoient du HTML (TemplateResponse)
- `routers/` : routes JSON utilisées par le JS frontend

### Routers
| Fichier | Prefix | Rôle |
|---|---|---|
| `testeurs.py` | `/api/testeurs` | CRUD testeurs |
| `stagiaires.py` | `/stagiaires` | CRUD stagiaires + GET `/{id}/historique` (sessions + résultats théorie/pratique) + GET `/{id}/caces-valides` (CacesObtenu valides avec testeur) + GET `/{id}/cartes-emises` (CarteCaces statut=emise : numero_carte, famille, date_generation) |
| `sessions.py` | `/api/sessions` | Gestion sessions CACES® |
| `admin.py` | `/admin` | Catégories, habilitations, lieux |
| `auth.py` | `/auth` | Login JWT |
| `upload.py` | — | Import fichiers |
| `statistiques.py` | — | Stats/rapports |
| `cartes_caces.py` | `/api/cartes-caces` | Cartes CACES® (préparation, émission, annulation) + `GET /{id}/pdf` (WeasyPrint → PDF CR80 protégé pypdf) |
| *(main.py)* | `/verifier/{token}` | Page publique de vérification (token = UUID4 `token_verification`, fallback `numero_carte`) — pas de login requis |

---

## Décisions architecturales

### Soft delete vs hard delete
- **Testeurs** : soft delete (`actif = False`), appelé "archiver" — les données historiques doivent rester liées
- **Habilitations testeur** (`HabilitationTesteur`) : hard delete SQL (`db.delete()`) — pas d'historique nécessaire
- **Autres entités** : soft delete par défaut

### Authentification
- Token JWT stocké dans `localStorage`
- Intercepteur `window.fetch` dans `base.html` qui injecte `Authorization: Bearer <token>` sur toutes les requêtes
- Redirection vers `/login` si pas de token (côté client)

### PIN admin
- Code PIN : **1505**
- Utilisé pour : archiver un testeur, supprimer/activer des habilitations, clôturer une session, retirer un candidat d'un jour, supprimer un candidat de la session
- Vérifié **côté serveur** sur les routes sensibles (paramètre query `?pin=`)
- `admin.html` valide aussi côté client dans `demanderPin()` avant d'appeler l'API

### Résultats théorie
- **Un seul `ResultatTheorie` par couple `(jour_test_id, stagiaire_id)`** — contrainte UNIQUE en base `uq_resultat_theorie_jour_stagiaire`
- Un candidat peut repasser sur un **autre jour** (même session) → nouvelle ligne (couple différent)
- Mode `numerique` : test numérique `test_theorie.html` → reprise par écrasement si déjà existant (guard dans `soumettre_reponses_theorie`)
- Mode `degrade` : saisie manuelle par thème (à implémenter) → 409 si un résultat numérique existe déjà pour ce jour
- Correction = écrasement assumé, toujours sous PIN formateur
- Affichage : meilleur résultat réussi en priorité, sinon le plus récent

### Grilles INRS (théorie)
- Tirage Phase 2 : règle 10-30% par thème sur les grilles actives
- Comptage des utilisations sur jours actifs uniquement (`actif == True`)

### Pages dédiées sans JS inline
Certaines actions complexes utilisent des pages GET/POST dédiées plutôt qu'une modal JS :
- `/sessions/{id}/modifier` — modification des dates cadre + responsable
- `/sessions/{id}/jours/{jour_id}/modifier` — modification d'un jour test

### Test théorique — routes
- `GET /test/theorie/{session_id}/{jour_id}` — tablette testeur : affiche `test_theorie.html` avec sélection candidat (écran 1→2→3→4)
- `GET /test/theorie/{jour_test_id}/{stagiaire_id}/start` — QR code candidat : démarre directement le test (skip écrans sélection/identité/consignes) ; `jour_test_id` est l'id du `JourTest` (pas `session_id`) ; contexte supplémentaire : `start_direct=True`, `start_stagiaire_id`, `start_nom`, `start_prenom` ; QR générés dans `session_detail.js` via `qrcode.js` (CDN cdnjs) sur `.qr-container[data-qr-url]`

### Middleware _verifier_role (main.py) — périmètre rôle terrain

Le middleware bloque le rôle terrain sur toutes les routes d'écriture `/api/sessions/*` sauf whitelist explicite. Routes whitelistées pour terrain (état après correctifs 2026-06-17) :

| Route | Méthode | Raison |
|---|---|---|
| `/api/sessions/\d+/jours(-formation)?/\d+/note-privee` | PUT, DELETE | Note privée du testeur principal |
| `/api/sessions/\d+/epreuves` | POST | Saisie résultat pratique |
| `/api/sessions/\d+/cloturer-terrain` | POST | Clôture terrain (PIN formateur requis) |
| `/api/sessions/\d+/jours/\d+/candidats/\d+/identite` | PUT | Toggle identité candidat à l'accueil |
| `/api/sessions/\d+/epreuves/\d+` | DELETE | Annulation résultat erroné |
| `/api/sessions/\d+/theorie/reponses` | POST | Public (_PUBLIC_PATTERNS), bypass total |
| `/api/sessions/\d+/theorie/reponses/\d+/\d+` | DELETE | Public, PIN formateur dans body |
| `/api/sessions/\d+/theorie/reouvrir/\d+/\d+` | POST | Public, PIN formateur dans body |

`rouvrir-terrain` n'est PAS whitelisté — réservé admin/utilisateur.

---

## Règles métier

1. **UT testeur** : max 6 UT/testeur/jour
2. **Machines** : alerte si > 7 UT/catégorie/jour → `ceil(UT/7)` machines recommandées
1b. **UT options** : seules les options **facultatives** (`OptionCategorie.incluse=False`) ajoutent **+0.5 UT** ; les options **incluses** (`incluse=True`) sont déjà comptées dans l'UT de base de la catégorie — ne jamais les additionner en plus.
   - R482/A : `ut_pratique=1.5` (PE incluse), TEL facultative
   - R482/G : `ut_pratique=1.2` (TEL incluse), PE facultative
   - R482/B2 : TEL incluse (conducteur accompagnant)
   - Calcul dans `session_detail.js:calculerRecapUT()` : skip options avec `data-incluse="1"`
   - Calcul dans `main.py` (total_ut jour + ut_planifie_candidat) : filtre via `opt_incluse_set = {(categorie, code_option)}`
   - Calcul dans `sessions.py:add_epreuve` : filtre `incluse_codes` avant `options_count * 0.5`
   - Cartographie admin : options incluses masquées des sous-lignes, annotation `incl. XX obligatoire` sur la ligne catégorie via `options_incluses_map` (route GET /admin)
3. **Résultats théorie** : un seul par `(jour_test_id, stagiaire_id)`, reprise par écrasement sous PIN formateur ; plusieurs jours = plusieurs lignes
4. **Meilleur résultat réussi** affiché sur la carte CACES® avec sa date
5. **Grilles INRS** : règle 10-30% par thème, comptage sur jours actifs uniquement
6. **Identité candidat** : case à cocher (non bloquante) dans la modal saisie résultat pratique
7. **Suppression d'un jour** : supprime aussi les `ResultatTheorie` et `SessionEpreuve` liés
8. **Retrait candidat d'un jour pratique** : bloqué (400) si des `SessionEpreuve` existent pour ce candidat/jour (l'utilisateur doit d'abord supprimer les résultats via "Annuler le résultat") ; sinon hard delete `JourTestCandidat`
8b. **Retrait candidat d'un jour théorique** : si un `ResultatTheorie` existe → avertissement modal → confirmation → PIN 1505 vérifié côté serveur → hard delete `ResultatTheorie` + `JourTestCandidat` ; si pas de `ResultatTheorie` → PIN → hard delete `JourTestCandidat` direct ; GET `/{session_id}/jours/{jour_id}/candidats/{stagiaire_id}/check-theorie` retourne `{"has_resultat": bool}`
12. **Décochage catégorie dans modal jour pratique** : bloqué si une `SessionEpreuve` existe déjà pour ce candidat/catégorie/jour — message "Supprimez d'abord le résultat de la catégorie X avant de la retirer" ; vérifié côté client (JS, sur l'événement `change`) ET côté serveur (`add_candidats_jour` renvoie 400) ; `j.candidats_epreuves = {stagiaire_id: [cat_list]}` calculé dans `main.py` et passé à `ouvrirModifierJourPratique` comme 6e paramètre
11. **Suppression candidat de la session** : vérifie d'abord qu'aucun `JourTestCandidat` n'existe pour cette session (sinon 400) ; soft delete `SessionCandidat.actif = False` ; PIN 1505 requis côté serveur via `DELETE /api/sessions/{id}/candidats/{sc_id}?pin=`
9. **Dates session** : vérification que les jours planifiés restent dans l'intervalle lors d'une modification
10. **Statuts session** : `planifiee` → `en_cours` → `terminee` (ou `annulee`)

---

## Modèles principaux

| Modèle | Table | Notes |
|---|---|---|
| `Famille` | `familles` | R482, R483 (Grues mobiles — cats A, B), R484, R485 (cats 1, 2), R486 (cats A, B, C), R487 (Grues à tour — cats 1, 2, 3), R489 (cats 1A, 1B, 2A, 2B, 3, 4, 5, 6, 7), R490 (cat 1 unique) |
| `Categorie` | `categories` | `ut_pratique`, `pepci_habilite`, `est_option` |
| `Session` | `sessions` | `famille`, `lieu_id`, `statut`, `reference`, `date_cloture_terrain` (DateTime nullable — clôture terrain) |
| `JourTest` | `jours_test` | `type` = theorie/pratique, `grille_id` |
| `JourTestCandidat` | `jours_test_candidats` | `categories` en CSV ; `options_planifiees` JSON Text `{"CAT": ["PE","TEL"], ...}` — options sélectionnées à la planification |
| `SessionEpreuve` | `session_epreuves` | résultat pratique par catégorie ; `options_obtenues` VARCHAR(200) CSV ; `bloque` Boolean défaut False — positionné lors d'une annulation CACES® avec motif "Non conforme"/"CACES® annulé" + case cochée, empêche la re-création auto du CacesObtenu ; suppression hard delete via `DELETE /api/sessions/{session_id}/epreuves/{epreuve_id}?pin=1505` |
| `ResultatTheorie` | `resultats_theorie` | UNIQUE `(jour_test_id, stagiaire_id)` ; `mode` VARCHAR(12) NOT NULL DEFAULT 'numerique' ('numerique'/'degrade') ; `bloque` Boolean défaut False — positionné comme SE, empêche la recherche de théorie dans `calculer_et_synchroniser` ; reprise par écrasement si mode='numerique', 409 si mode='degrade' |
| `HabilitationTesteur` | `habilitations_testeurs` | hard delete ; `option_pe`/`option_tel` legacy — remplacés par `HabilitationOption` |
| `OptionCategorie` | `option_categorie` | table de référence des options disponibles par famille/catégorie ; codes : PE=Porte-engins, TEL=Télécommande, CC=Conduite cabine, TR=Translation sur rails, CEC=Circulation en charge ; `incluse` Boolean (défaut False) : option obligatoire incluse dans l'UT de la catégorie (pas de +0.5 UT) vs option facultative ; peuplé par `init_options.py` |
| `HabilitationOption` | `habilitation_option` | options actives par habilitation (habilitation_id FK, code_option) ; modifiable avec PIN 1505 via `PUT /admin/habilitation/{id}/options` |
| `Testeur` | `testeurs` | soft delete (`actif`) ; `etat` : actif/suspendu/sorti — modifiable avec PIN 1505 via `PUT /api/testeurs/{id}/etat`, défaut actif à la création ; docs PDF en base64 : `attestation_prevention_pdf/nom/date`, `visite_medicale_pdf/nom/visite_medicale_date`, `evaluation_pdf/nom/evaluation_date`, `autorisation_conduite_pdf/nom`, `carte_pdf/carte_nom_fichier` (legacy) |
| `CarteTesteur` | `carte_testeur` | multi-cartes par testeur, soft delete (`actif`) ; champs : `famille`, `nom_fichier`, `contenu_pdf` base64, `date_upload` |
| `ConfigOrganisme` | `config_organisme` | singleton (1 ligne) ; `nom_organisme`, `logo_base64` (image base64), `logo_nom` ; `adresse` Text, `siret` VARCHAR(20), `email` VARCHAR(200), `telephone` VARCHAR(50) ; `signataire_nom`, `signataire_prenom`, `signataire_qualite` VARCHAR(100) ; `signature_base64` Text, `signature_nom` VARCHAR(200) (image signature upload) ; `url_verification_caces` VARCHAR(500) (optionnel, si non renseigné → défaut `https://caces-app.onrender.com/verifier/`) — utilisé par `_build_verify_url()` pour construire `verify_url = base + token_verification` (fallback `numero_carte`) passé dans `config.verify_url` au frontend JS (QR code recto) ; `audit_interne_date`, `audit_externe_date`, `revue_direction_date` (Date nullable) ; `pin_formateur` VARCHAR(20) défaut "1234" — PIN saisi par le formateur pour débloquer "Ce n'est pas moi" dans test_theorie.html ET pour clôturer terrain, vérifié via `POST /admin/config/verifier-pin-formateur` ou dans le handler `cloturer-terrain`, modifiable dans Administration → Paramètres avec PIN admin 1505 ; `prochain_numero_caces` Integer défaut 1 — prochain numéro attribué lors de la validation d'un CACES® (affiché sur 4 chiffres : 0001, 0002…), incrémenté auto à chaque `POST /api/caces-obtenus/valider/{id}`, configurable dans Administration → Paramètres ; routes : `POST /admin/config-organisme/signature` + `DELETE /admin/config-organisme/signature` (upload/suppression image signature, PIN 1505) ; affiché via Jinja2 globals `nom_organisme()`, `logo_organisme()`, `get_config_organisme()` |
| `Stagiaire` | `stagiaires` | soft delete (`actif`) ; `photo_base64` Text — photo stockée en base64 PostgreSQL (upload via `POST /stagiaires/photo/{id}`, prioritaire sur `photo`) ; `photo` String(500) — chemin fichier legacy conservé pour rétro-compatibilité |
| `CacesObtenu` | `caces_obtenus` | statut : `a_valider`/`valide`/`annule` ; `numero_ordre` (Integer unique, attribué à la validation) ; `motif_annulation` Text nullable ; UNIQUE(stagiaire_id, session_id, categorie) ; routes : GET `/api/caces-obtenus/a-valider` (sync + liste), GET `/api/caces-obtenus/valides` (trié : validé en haut, annulé en bas), POST `/api/caces-obtenus/valider/{id}?pin=` (attribue numéro incrémental, bouton "📜 Émettre le CACES®"), POST `/api/caces-obtenus/annuler/{id}?pin=` body `{motif, bloquer_pratique: bool, bloquer_theorie: bool}` (statut→`annule`, si `bloquer_pratique` → `SessionEpreuve.bloque=True`, si `bloquer_theorie` → `ResultatTheorie.bloque=True` pour tous les RT obtenue=True du stagiaire dans la session, motif "Erreur administrative" : ne bloque rien + recréation auto au prochain /a-valider), PATCH `/api/caces-obtenus/{id}/motif?pin=` body `{motif}` (mise à jour motif_annulation) ; au prochain appel `/a-valider` les records `annule` repassent en `a_valider` seulement si SE/RT non bloqués ; modal annulation : select obligatoire (Erreur administrative / Non conforme / CACES® annulé / Autre) + cases à cocher visibles pour Non conforme et CACES® annulé uniquement ; service `app/services/caces_obtenus.py` → `calculer_et_synchroniser(db)` (filtre `SE.bloque != True` et `RT.bloque != True`) |
| `CarteCaces` | `carte_caces` | `stagiaire_id` FK, `famille`, `numero_carte` (unique, format `PEPCI-{YY}-{NNNNN}`, incrément annuel remis à zéro), `token_verification` (String 36, UUID4 unique, généré à l'émission, utilisé dans l'URL /verifier/{token}), `date_generation`, `statut` (`en_preparation` legacy/`emise`/`remplacee`/`annulee`), `motif_annulation`, `caces_json` Text (snapshot JSON des CacesObtenu au moment de l'émission : liste [{categorie, categorie_libelle, numero_ordre, options_obtenues, date_obtention, date_echeance, testeur_nom}]) — **une carte émise est figée définitivement** : le snapshot `caces_json` stocké à l'émission est la source de vérité ; les CACES® validés/annulés après l'émission n'affectent pas cette carte ; pour une carte à jour → générer une nouvelle carte (l'ancienne passe en `remplacee`) ; **pas de blocage de l'annulation CACES® par une carte émise** — une carte est une photo statique, l'organisme est responsable de réémettre si nécessaire ; page `/cartes-caces` — workflow : select stagiaire → familles filtrées → tableau CACES® validés → bouton Générer et imprimer (PIN) → fenêtre impression CR80 (≤4 cats, 85.6×54mm) ou A5 landscape (>4 cats) — à l'impression la carte passe en `emise`, l'ancienne `emise` passe en `remplacee` ; section Cartes émises : ▶/▼ déplie snapshot, boutons 🖨️ réimprimer + ❌ annuler uniquement sur `emise` ; badges : ✅ Émise / 📷 Remplacée / ❌ Annulée ; routes : `GET /stagiaires`, `GET /familles/{stag_id}`, `GET /caces-valides/{stag_id}/{famille}`, `POST /emettre/{stag_id}/{famille}?pin=`, `GET /{id}/caces` (retourne snapshot ou fallback legacy), `GET /reimprimer/{id}`, `GET /emises`, `POST /annuler/{id}?pin=` body {motif}, `GET /{id}/pdf` (PDF CR80 recto/verso protégé — WeasyPrint (rendu HTML CR80 identique au template JS) + pypdf (permissions_flag=2052, impression seule), téléchargement direct) ; **page publique** : `GET /verifier/{token}` (main.py, pas de login) — token = `token_verification` UUID4 (fallback `numero_carte` pour rétro-compatibilité) ; **anonymisation RGPD obligatoire côté serveur** : la route ne passe JAMAIS `s.prenom` ni `s.date_naissance` bruts au template — uniquement `stagiaire_prenom = prenom[0] + "."` et `stagiaire_ddn_annee = date_naissance.year` — template `verifier.html` standalone (pas de base.html) — affiche titulaire + tableau CACES® si `emise`, bandeau avertissement si `annulee`/`remplacee`, message d'erreur si introuvable |
| `DocumentOfficiel` | `document_officiel` | singleton par type (`certificat_organisme`, `attestation_assurance`, `procedure_interne`) ; champs : `contenu_pdf` base64, `nom_fichier`, `date_validite`, `numero_certificat` (certificat_organisme uniquement) ; Jinja2 globals `numero_certificat()`, `date_validite_certificat()` (retourne date formatée dd/mm/YYYY ou "") |
| `GrilleTheorie` | `grilles_theorie` | grilles INRS |
| `ReponseGrille` | `reponses_grille` | questions par grille |
| `NonConformite` | `non_conformites` | journal des non-conformités et réclamations ; champs : `reference` (String unique, format "NC-AAAA-NNN", généré auto à la création, incrément annuel remis à zéro chaque année), `date`, `declarant_id` (FK Utilisateur), `origine` (interne/reclamation_client/reclamation_apprenant/audit), `type_nc` (incident/non-conformite/observation), `nature` (documentaire/materiel/organisationnel, nullable), `titre`, `description`, `action_preventive`, `action_corrective`, `justificatif_pdf` base64, `justificatif_nom`, `statut` (ouvert/en_cours/cloture/sans_objet, défaut ouvert ; badges : rouge/orange/vert/gris), `date_cloture` ; liens optionnels `session_id`, `testeur_id`, `stagiaire_id` (FK nullable) ; routes : POST `/api/non-conformites`, PUT `/api/non-conformites/{id}` (403 si statut cloture/sans_objet — rouvrir d'abord), PATCH `/api/non-conformites/{id}/cloturer` (PIN 1505), PATCH `/api/non-conformites/{id}/sans-objet` (PIN 1505, pose aussi `date_cloture`), PATCH `/api/non-conformites/{id}/rouvrir` (PIN 1505, remet statut à `ouvert` et efface `date_cloture`), GET `/api/non-conformites/{id}/justificatif` ; page `/non-conformites` dans nav après Statistiques ; liste dépliable (référence, date, titre, badge statut) ; carte dépliable avec actions préventive/corrective stylisées, justificatif PDF téléchargeable ; dashboard : carte "Non-conformités ouvertes" dans la grille 2-col + ligne 3-col en dessous |

---

## Scripts de migration disponibles

| Script | Description | Statut prod |
|---|---|---|
| `migrate_photo_base64.py` | `ALTER TABLE stagiaires ADD COLUMN photo_base64 TEXT` | à exécuter |
| `migrate_option_incluse.py` | `ALTER TABLE option_categorie ADD COLUMN incluse BOOLEAN DEFAULT FALSE` | à exécuter |
| `migrate_ut_categories.py` | R482/A `ut_pratique=1.5`, R482/G `ut_pratique=1.2` | à exécuter |
| `migrate_token_verification.py` | `ALTER TABLE carte_caces ADD COLUMN token_verification VARCHAR(36)` + backfill UUID | à exécuter |
| `migrate_r483_r487_r490.py` | Swap libellés R483↔R487, déplace cats A/B vers R483, crée cats 1/2/3 sous R487, supprime cats parasites R483 et R490/2-3/OPT-TEL | à exécuter |
| `migrate_cloture_terrain.py` | `ALTER TABLE sessions ADD COLUMN date_cloture_terrain TIMESTAMP` | **à exécuter sur prod (Render Shell)** |

Ordre d'exécution sur prod (toutes migrations puis init_options) :
```
python migrate_photo_base64.py
python migrate_option_incluse.py
python migrate_ut_categories.py
python migrate_token_verification.py
python migrate_r483_r487_r490.py
python init_options.py
python migrate_cloture_terrain.py
```

---

## Infrastructure Render

- **App** : `caces-app` — Starter $7/mois, Frankfurt
- **DB** : `caces-db` — Free tier, **expire le 05/07/2026** → upgrader avant cette date
- **Variables d'environnement** : `DATABASE_URL`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_CLOUD_NAME`

### Initialisation base (avec External URL Render)
```bash
$env:DATABASE_URL="postgresql://..."
python init_db.py
python init_data.py
python init_admin.py
python init_grilles_r482.py
python init_questions_r482.py
```

---

## Chantiers en cours / À faire

| Priorité | Item | Statut |
|---|---|---|
| URGENT | Upgrader caces-db Render avant 05/07/2026 | en attente |
| Haute | Grille statuts sessions 4 états (Ouverte / À réutiliser / Validée terrain / Clôturée) | ✅ fait |
| Haute | Bouton + route clôture terrain (POST /sessions/{id}/cloturer-terrain, PIN) | ✅ fait |
| Haute | Harmoniser affichage statut sessions dans dashboard.html (actuellement logique séparée inline) | ✅ fait |
| Haute | Suppression habilitation testeur — hard delete avec PIN (modal testeurs) | en cours |
| Haute | Cartes CACES® PDF (format CR80, WeasyPrint) | ✅ fait |
| Haute | Annuler/supprimer résultat épreuve pratique (avec PIN) | ✅ fait |
| Haute | CACES® Obtenus — calcul auto + validation + page /caces-obtenus | ✅ fait |
| Haute | Jours de formation (nouveau type, UT personnalisés) | à faire |
| Haute | Journal non-conformités/réclamations — page /non-conformites + modèle NonConformite + carte dashboard | ✅ fait |
| Haute | Historique sessions par stagiaire — bouton ▶ dans page stagiaires, lazy load GET /stagiaires/{id}/historique | ✅ fait |
| Haute | Options CACES® (PE, TEL, CC, TR, CEC) sur épreuves pratiques — planification + résultats | ✅ fait |
| Moyenne | Externaliser JS inline de admin.html (contrainte CSP) | à faire |
| Moyenne | Grilles R486, R489 (scripts init à créer) | à faire |
| Moyenne | Multi-tenant (subdomain routing, database-per-tenant) | à faire |

### Décision architecturale : multi-tenant Cloudinary
**Option A retenue — un compte Cloudinary distinct par tenant.**
- Credentials `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` stockés dans les variables d'environnement de chaque instance Render, ou dans une table `tenant_config` en base.
- Au provisioning d'un nouveau tenant : créer un compte Cloudinary gratuit et renseigner les 3 credentials.

| Haute | Photos stagiaires — migration filesystem éphémère → base64 PostgreSQL (`photo_base64` Text) | ✅ fait |
| Haute | Token vérification UUID (`token_verification`) + anonymisation RGPD sur `/verifier/{token}` | ✅ fait |
| Haute | Options incluse/facultative (`OptionCategorie.incluse`) + calcul UT filtré | ✅ fait |
| Basse | Responsive mobile (CSS media queries) | à faire |
| Basse | UT options facultatives = +0.5 UT (incluses déjà dans UT catégorie) | ✅ fait |
| Basse | Supprimer `date_habilitation` et `date_expiration_habilitation` du modèle `Testeur` (doublons avec `HabilitationTesteur`) | à faire |

### Dashboard — route GET /
Variables de contexte passées au template `dashboard.html` :
- `stats` : dict (stagiaires, cartes, sessions, expirations)
- `testeurs` : testeurs actifs avec habilitations chargées
- `docs` : dict type→DocumentOfficiel
- `today` : date du jour
- `referents` : Utilisateur avec role_referent renseigné et actif
- `nc_ouvertes` : NonConformite statut in (ouvert, en_cours) desc date
- `sessions_actives` : Session statut in (planifiee, en_cours) order by date_theorie/date_pratique_debut
- `alertes_testeurs` : liste de `{"testeur": Testeur, "alertes": [{"label": str, "couleur": "rouge"|"orange"}]}` — attestation prévention (absente→rouge, >4ans→orange), visite médicale (absente→rouge, >2ans→orange), date_prochain_controle dépassée→rouge
- `caces_a_valider` : liste de dicts `{id, stagiaire_nom, stagiaire_prenom, famille, categorie}` — CacesObtenu statut=a_valider

Carte **⚡ À traiter** (pleine largeur, grid-column 1/-1) regroupe en sections séparées par trait grisé : Sessions non clôturées, CACES® à valider, Non-conformités ouvertes, Alertes testeurs, Candidats sans photo. Chaque section affiche le compteur et "✅ Aucun" si vide. Remplace les anciennes cartes séparées "Sessions non clôturées", "Non-conformités ouvertes" et "Alertes".

### Règles de calcul CACES® Obtenus

Déclencheur : `GET /api/caces-obtenus/a-valider` appelle `calculer_et_synchroniser(db)` qui parcourt tous les `SessionEpreuve.obtenue == True` et crée les `CacesObtenu` manquants en statut `a_valider`.

**Recherche de la théorie (3 priorités) :**
1. Même session (`ResultatTheorie.session_id == epreuve.session_id AND obtenue == True`)
2. Autre session **ouverte** (`statut != "terminee"`), même famille, `abs(date_theo - date_prat) ≤ 365j` → **continuité** (`post_cloture = False`)
3. Autre session **clôturée** (`statut == "terminee"`), même famille, `abs(date_theo - date_prat) ≤ 365j` → **extension** (`post_cloture = True`)

**Calcul date_obtention / date_echeance :**
| Cas | Condition | date_obtention | date_echeance |
|---|---|---|---|
| 1 | Théorie == pratique (même jour) | date pratique | +10 ans −1j (R482) ou +5 ans −1j |
| 2 | Théorie < pratique | date pratique | idem |
| 3 | Théorie > pratique (sessions ouvertes, priorités 1 et 2) | date théorie | idem |
| 4 | Extension — théorie session clôturée (priorité 3) | date pratique | échéance du 1er `CacesObtenu.valide` dans cette famille pour ce stagiaire, sinon calcul normal |

**Numéro d'ordre :** incrémental unique toutes familles confondues (`max(numero_ordre) + 1` au moment de la validation).

**Protection doublon :** UNIQUE(stagiaire_id, session_id, categorie) — un enregistrement annulé bloque la re-création automatique.

**Recalcul à la clôture :** `POST /api/sessions/{id}/cloturer` appelle `calculer_et_synchroniser(db)` après `statut = "terminee"`. Les enregistrements `a_valider` dont la théorie provenait de cette session (mode continuité) voient leurs dates recalculées en mode extension (priorité 3 → `post_cloture = True` → `date_echeance` = échéance CACES® initial). Les records `valide`/`annule` ne sont jamais modifiés.

### Note : doublons date_habilitation / date_expiration_habilitation
`Testeur.date_habilitation` et `Testeur.date_expiration_habilitation` sont des doublons avec `HabilitationTesteur` — à supprimer dans une passe de nettoyage ultérieure après vérification qu'ils ne sont utilisés nulle part (modèle, routes, templates, migrations).

### ✅ Chantier terminé : clôture terrain (2026-06-17)

**Nouveaux éléments :**
- `Session.date_cloture_terrain` (DateTime nullable) — migration : `migrate_cloture_terrain.py` (idempotent, **à exécuter sur prod via Render Shell**)
- `get_pin_formateur(db)` dans `app/config_utils.py` — lit `ConfigOrganisme.pin_formateur` (défaut "1234")
- Helper `assert_modifiable_terrain(session, role)` dans `sessions.py` — bloque role=="terrain" si session gélée terrain (403)
- Route `POST /api/sessions/{id}/cloturer-terrain` — tous rôles, PIN formateur, idempotent
- Route `POST /api/sessions/{id}/rouvrir-terrain` — admin/utilisateur uniquement, PIN admin
- `current_user` ajouté sur 15 routes de modification (candidats ×3, equipements ×3, jours ×3, candidats_jour ×2, toggle_identite, update_session, modifier_jour, epreuves ×2)
- Route publique `POST /api/sessions/{session_id}/theorie/reponses` : check direct `if session.date_cloture_terrain is not None: 403`
- UX `session_detail.html` : bouton "🔐 Clôturer terrain" (tous rôles), badge "🔐 Validée terrain" + titre date, bouton "🔓 Rouvrir terrain" (admin/utilisateur seulement)
- `data-terrain-gele` + `data-user-role` sur `#session-data`
- `session_detail.js` : fonctions `cloturerTerrain()` + `rouvrirTerrain()`, masquage visuel conditionné à `USER_ROLE === 'terrain'`

**Correctifs post-push (2026-06-17) :**
- Bug : middleware `_verifier_role` bloquait terrain sur `POST /cloturer-terrain` (catch-all sessions) → affichage "Code PIN incorrect" à tort (JS montrait #pin-error pour tout 4xx)
- Ajout de 3 exceptions dans `_verifier_role` pour rôle terrain : `POST /cloturer-terrain`, `PUT /jours/{j}/candidats/{s}/identite`, `DELETE /epreuves/{eid}`
- JS `cloturerTerrain()` + `rouvrirTerrain()` : lecture `data.detail` au lieu de texte en dur dans `#pin-error`
- Trou UX : bouton 🚀 (lancement test théorique) affiché même sur session clôturée terrain → conditionné sur `date_cloture_terrain is none` dans `session_detail.html` (tous rôles), badge "🔐 Tests clos" sinon
- Garde-fou GET : `GET /test/theorie/{session_id}/{jour_id}` et `GET /test/theorie/{jour_test_id}/{stagiaire_id}/start` passent `terrain_gele=True` si `date_cloture_terrain` renseignée ; `test_theorie.html` affiche écran bloquant "Session clôturée terrain" à la place du test
- Masquage terrain : `querySelectorAll('[data-action]')` restreint à `div.content` (plus `document`) — corrige disparition hamburger + déconnexion en vue mobile
- Badges détail session : suppression badge "Figée / Libre" (doublon avec "✅ Tirage fait" pour back-office, inutile pour terrain) ; badge statut brut (`planifiee/en_cours…`) remplacé par `statut_affichage_session` calculé dans la route détail (mêmes 4 états et couleurs que la liste : Ouverte/Validée terrain/À réutiliser/Clôturée/Annulée)
- Dashboard section "À traiter" : libellé "Sessions ouvertes" → "Sessions non clôturées" ; badge statut primitif (planifiee→Ouverte / else→En cours) remplacé par `statut_affichage_session` via préchargement groupé anti-N+1 (`_dash_avec_epreuve`, `_dash_avec_rt`) ; `statuts_affichage` dict passé au template ; filtre `statut.in_([planifiee, en_cours])` confirmé correct (exclut terminee et annulee)

**Décision :** gel LARGE (toutes routes de modification Terrain), PIN formateur pour clôture (tous rôles), PIN admin pour réouverture (back-office uniquement). `rouvrir-terrain` non whitelisté dans le middleware.

**À faire** : `python migrate_cloture_terrain.py` dans Render Shell (prod).

### ✅ Chantier terminé : avertissement clôture définitive session "À réutiliser" (2026-06-17)

**Contexte :** quand une session est "À réutiliser" (tirage déclenché + aucun résultat saisi), la clôturer définitivement (`POST /cloturer`) la fige inutilement et perd le tirage. Un avertissement explicite s'impose avant confirmation.

**Implémentation :**
- `app/main.py` (route `page_session_detail`) : calcul `session_sans_resultat = tirage_declenche and not _a_epreuve and not _a_rt` (zéro requête supplémentaire — variables déjà présentes) ; passé dans le contexte template
- `templates/session_detail.html` : `data-sans-resultat` sur `#session-data` ; nouvelle modal `#modal-avert-cloture` avec texte explicite ("Cette session a une grille tirée mais aucun résultat saisi..."), bouton "Confirmer la clôture" (`data-action="confirmer-avert-cloture"`) et bouton "Annuler" (`data-action="fermer-avert-cloture"`)
- `static/js/session_detail.js` : `window.SESSION_SANS_RESULTAT` lu depuis `#session-data` ; `_executerCloture()` = point unique du fetch `POST /cloturer` ; `cloturerSession()` redirige vers `#modal-avert-cloture` si `SESSION_SANS_RESULTAT`, sinon `demanderConfirmation` habituel — les deux chemins aboutissent à `_executerCloture()` ; listeners `data-action` propres (CSP)

**Note architecture :** `POST /cloturer` n'exige **pas de PIN** (auth JWT seule). C'est délibéré (admin/utilisateur sont authentifiés) mais à noter si un niveau supplémentaire est souhaité.

### ✅ Chantier terminé : numérotation sessions robuste aux suppressions (2026-06-17)

**Bug :** `create_session` utilisait `COUNT(sessions de l'année) + 1` → une suppression creuse un trou dans la séquence, le prochain numéro calculé retombait sur un numéro déjà pris → doublon silencieux (pas de contrainte unique en base).

**Correction :**
- `app/routers/sessions.py` (route `POST /`) : passage au **MAX numérique** — regex `-(\d+)$` sur toutes les refs `SESSION-{annee}-%`, parse int de chacune (ignore formats non conformes), `max + 1` ou `1` si aucune. Robuste aux formats mélangés (`01` et `002` coexistants → max=2 → prochain=003).
- `app/main.py` (startup) : `CREATE UNIQUE INDEX IF NOT EXISTS uq_session_reference ON sessions (reference) WHERE reference IS NOT NULL` — avec **vérification explicite** post-création (pg_indexes/sqlite_master) et affichage non-silencieux si l'index n'existe pas après création.

**Contexte prod :** doublon `SESSION-2026-006` supprimé manuellement avant création de l'index. Format mixte `SESSION-2026-01` / `SESSION-2026-002` confirmé en dev — raison pour laquelle le tri DESC alphabétique a été écarté.

### ✅ Chantier terminé : uniformisation drapeau NC 🚩 (2026-06-17)

**Avant :** trois rendus différents — `⚑` texte noir sans couleur (dashboard/sessions), `🚩` rouge `color:#cc0000` inline (dashboard/NC ouvertes), `🚩` masqué desktop via `display:none` (page NC).

**Standard retenu :** `🚩` emoji triangulaire rouge natif, visible partout (desktop + mobile), `title` au survol précisant le sens.

**Modifications :**
- `dashboard.html:85` (section sessions) : `⚑ .nc-flag aria-label` → `🚩 .nc-flag title="Non-conformité(s) non soldée(s)"`
- `dashboard.html:140` (section NC ouvertes) : suppression `color:#cc0000` (sans effet sur emoji) ; title → "NC liée à une session"
- `non_conformites.html:77` : suppression `style="display:none;"` (bug desktop) ; title → "NC liée à une session" — `.nc-flag-cell` conservé pour le positionnement flex mobile

### ✅ Chantier terminé : fondation test théorique — unicité, mode, anti-doublon, réouverture/suppression (2026-06-17)

**Contexte :** prépare les évolutions du test numérique (mode dégradé hors-ligne, réouverture sous PIN, correction assumée).

**Modèle `ResultatTheorie` (resultats_theorie) :**
- Colonne `mode VARCHAR(12) NOT NULL DEFAULT 'numerique'` ajoutée — valeurs : `'numerique'` / `'degrade'`
- Migration startup : `ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS mode VARCHAR(12) NOT NULL DEFAULT 'numerique'` (PostgreSQL prod idempotent)
- Index unique `uq_resultat_theorie_jour_stagiaire ON resultats_theorie (jour_test_id, stagiaire_id)` — non silencieux, vérifié au démarrage
- **ATTENTION prod** : avant déploiement, refaire `SELECT jour_test_id, stagiaire_id, COUNT(*) FROM resultats_theorie GROUP BY jour_test_id, stagiaire_id HAVING COUNT(*) > 1` sur prod et résoudre (rule : garder le plus récent = id max, supprimer tous les autres)

**Résolution doublons (réutilisable prod) :**
```python
# Pour chaque couple (jour_test_id, stagiaire_id) en doublon : garder id_max, supprimer les autres
SELECT jour_test_id, stagiaire_id FROM resultats_theorie GROUP BY ... HAVING COUNT(*) > 1
# → pour chaque couple : DELETE WHERE id != max(id) AND jour_test_id=X AND stagiaire_id=Y
```

**Garde anti-doublon dans `soumettre_reponses_theorie` (sessions.py) :**
- Existe + `mode='numerique'` → REPRISE : update du résultat existant (recalcul + écrasement `reponses_json`/notes/obtenue)
- Existe + `mode='degrade'` → 409 "Un résultat saisi manuellement existe pour ce jour — supprimez-le d'abord."
- N'existe pas → créer (comportement antérieur)

**Nouvelles routes (socle serveur — UI à câbler ultérieurement) :**
- `POST /api/sessions/{id}/theorie/reouvrir/{stagiaire_id}/{jour_test_id}` — PIN formateur dans body (`TheoriePinBody`), public (_PUBLIC_PATTERNS) ; retourne `{resultat_id, mode, reponses, note_totale, obtenue}` sans rien supprimer
- `DELETE /api/sessions/{id}/theorie/reponses/{stagiaire_id}/{jour_test_id}` — PIN formateur dans body, public ; supprime le `ResultatTheorie` (sert à vider une saisie dégradée erronée ou changer de mode)

**Principes métier validés :**
- Unicité par jour, pas par session (plusieurs jours = plusieurs lignes légitimes)
- Numérique et dégradé coexistent le même jour, candidat par candidat
- Correction = écrasement assumé, toujours sous PIN formateur
- Reprise numérique = réouverture + update (jamais de delete avant fin, `reponses_json` préservé même si page fermée)

### Chantier en cours : suppression habilitation (hard delete)
Objectif : ajouter un bouton 🗑️ dans la modal de modification d'un testeur existant pour supprimer définitivement une habilitation (hard delete SQL + PIN 1505).

Fichiers à modifier :
- `app/routers/admin.py` — route `DELETE /admin/habilitation/{id}` : ajouter `pin`, vérification PIN, remplacer soft delete par `db.delete()`
- `templates/admin.html` — `demanderPin()` : passer `pin` au callback ; `desactiverHabTesteur()` : transmettre `?pin=` à l'API
- `templates/testeurs.html` — ajouter divs cachés `#habs-{id}` + section `#section-habs-modal` dans la modal
- `static/js/testeurs.js` — `editer()` : peupler la liste habilitations ; ajouter `supprimerHab()` + handler `supprimer-hab`
