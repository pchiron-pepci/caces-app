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

## Charte graphique NORYX (référence — appliquer à tous les nouveaux écrans)

**Principe directeur :** anthracite pour la structure, blanc dominant pour respirer, ardoise pour le secondaire, rouge en accent RARE. Identité "soft, pro, moderne" — l'anthracite ne doit jamais être en aplat partout (austère), le rouge jamais disséminé (agressif).

**Palette :**
- Anthracite `#2d2d2d` : structure — en-têtes/bandeaux, boutons d'action principaux, titres forts. C'est la signature visuelle.
- Blanc `#fff` : fond dominant du contenu, respiration.
- Ardoise `#4a5568` : textes secondaires, libellés discrets, boutons secondaires (contour), liens type "Voir tout".
- Rouge NORYX `#cc0000` : accent RARE uniquement — bouton d'action le plus important d'une page (ex. "+ Nouvelle session"), ou chiffre/élément qui doit alerter (ex. "3 à clôturer"). Jamais en aplat de fond, jamais disséminé.
- Gris clair `#f4f5f6` / `#f0efef` : fonds de pastilles, surfaces secondaires.
- Bordures : `0.5px solid #e0e3e6`.

**Boutons :**
- Principal : fond anthracite `#2d2d2d`, texte blanc, pilule (border-radius 999px).
- Action critique/CTA : fond rouge `#cc0000` (usage rare, 1 par écran max).
- Secondaire : contour ardoise (`border:1px solid #d0d4d8`, texte `#4a5568`), fond transparent.

**Badges de statut (réutiliser les codes existants) :** teal `#E1F5EE`/`#0F6E56` (validé), jaune/amber `#FAEEDA`/`#854F0B` (en cours/ouvert), rouge `#FCEBEB`/`#A32D2D` (à traiter/alerte).

**Règle d'accessibilité (public à faible littératie) maintenue :** dans les contextes où une couleur pourrait être lue comme "bon/mauvais" (réponses de test), ne jamais utiliser vert/rouge comme jugement — voir chantier refonte test théorique. La charte couleur ci-dessus s'applique à la structure/navigation, pas aux signaux de réponse candidat.

**Pictos :** privilégier CSS pur (caractères Unicode sobres, chiffres dans pastilles) plutôt que des emojis ou une police d'icônes externe — fiabilité en salle (connexion non garantie). Pas d'emoji sur les écrans certifiants.

**Logo :** non figé définitivement à ce jour — sur pastille blanche dans les bandeaux anthracite. Tagline : "Pilotage CACES® & Autorisation de conduite".

**État de déploiement :** charte validée. Module test théorique = encore en bleu marine (#1a237e) / ardoise sur QCM+récap. Bascule anthracite à dérouler écran par écran (ordre suggéré : header commun → écran consignes → QCM/récap → écrans sélection/identité → écran résultat). Reste du site (dashboard, listes, etc.) à aligner progressivement sur cette charte.

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
- Mode `degrade` : saisie manuelle par thème → 409 si un résultat numérique existe déjà pour ce jour
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
| `/api/sessions/\d+/theorie/reponses/\d+/\d+` | DELETE | middleware cookie + PIN formateur dans body — tous rôles (terrain whitelisté _verifier_role) |
| `/api/sessions/\d+/theorie/reouvrir/\d+/\d+` | POST | middleware cookie + PIN formateur dans body — terrain+admin+utilisateur (whitelisté _verifier_role) |
| `/api/sessions/\d+/theorie/reponses-degrade` | POST | middleware cookie + PIN formateur dans body — testeur corrige papier et saisit les notes (whitelisté _verifier_role) |
| `/api/sessions/\d+/theorie/justificatif/\d+/\d+` | POST | middleware cookie + PIN formateur dans body — upload justificatif PDF (terrain + back-office, whitelisté _verifier_role) |

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
| `ResultatTheorie` | `resultats_theorie` | UNIQUE `(jour_test_id, stagiaire_id)` ; `mode` VARCHAR(12) NOT NULL DEFAULT 'numerique' ('numerique'/'degrade') ; `bloque` Boolean défaut False — positionné comme SE, empêche la recherche de théorie dans `calculer_et_synchroniser` ; reprise par écrasement si mode='numerique', 409 si mode='degrade' ; `justificatif_pdf` Text nullable (base64) ; `justificatif_nom` VARCHAR(255) nullable — ajoutés par migration startup + `migrate_justificatif_theorie.py` ; update notes ne touche JAMAIS justificatif (opérations indépendantes) |
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
| `migrate_justificatif_theorie.py` | `ALTER TABLE resultats_theorie ADD COLUMN justificatif_pdf TEXT` + `justificatif_nom VARCHAR(255)` | **à exécuter sur prod (Render Shell)** |

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
| Haute | Export ZIP session (récap PDF + justificatifs + consentements/neutralité) — étape 1/3 + récap date/testeur faits | en cours |
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
- `POST /api/sessions/{id}/theorie/reouvrir/{stagiaire_id}/{jour_test_id}` — **JWT requis** + PIN formateur dans body (`TheoriePinBody`) ; retourne `{resultat_id, mode, reponses, note_totale, obtenue}` sans rien supprimer ; **terrain+admin+utilisateur** (whitelisté dans `_verifier_role` — récupération validation accidentelle en salle)
- `DELETE /api/sessions/{id}/theorie/reponses/{stagiaire_id}/{jour_test_id}` — **JWT requis** + PIN formateur dans body ; supprime le `ResultatTheorie` ; **admin/utilisateur uniquement** (terrain bloqué catch-all — acte irréversible = back-office)
- **La soumission `POST /theorie/reponses` reste seule publique** (action candidat sans compte)

**Principes métier validés :**
- Unicité par jour, pas par session (plusieurs jours = plusieurs lignes légitimes)
- Numérique et dégradé coexistent le même jour, candidat par candidat
- Correction = écrasement assumé, toujours sous PIN formateur
- Reprise numérique = réouverture + update (jamais de delete avant fin, `reponses_json` préservé même si page fermée)

### ✅ Chantier terminé : garde-fou lancement test théorique sans tirage (2026-06-17)

- **Cause** : `get_questions_phase2` lève `ValueError` → `HTTPException(400)` si `UtilisationTheme` vide pour la session — le JS plantait sur `data.themes[1]` au lieu d'afficher l'erreur.
- **Couche 1 — UI** : 🚀 dans `session_detail.html` remplacé par `<span>` désactivé (opacity 0.45, cursor not-allowed, tooltip explicatif) quand `not tirage_declenche` — l'utilisateur ne peut pas lancer le test sans tirage.
- **Couche 2 — Page test** : `test_theorie.html` affiche écran bloquant "Tirage non déclenché" si `tirage_declenche | default(false)` est faux (fail-safe : `default(false)` bloque si variable absente). `tirage_declenche` passé par les deux routes GET (`page_test_theorie` et `page_test_theorie_start`).
- **Couche 3 — JS** : `chargerQuestions()` vérifie `resp.ok`, lit `err.detail` et affiche le message dans `#msg-erreur-grille` (div rouge dans ecran-selection) — plus de crash sur `data.themes[1]`, plus de `alert()`.
- **Route serveur** : `GET /{session_id}/jours/{jour_id}/grille` — message déjà clair : "Le tirage n'a pas encore été déclenché..." — inchangé (source de vérité).

### ✅ Chantier terminé : génération PDF test théorique — sujet vierge + corrigé (2026-06-17)

**Nouveau service `app/services/pdf_test_theorie.py` :**
- `_construire_questions(session_id, famille, db)` : requête `UtilisationTheme` → `GrilleTheorie` + `ReponseGrille` directs, retourne `{theme_int: [{numero, points, texte, image, grille_numero, reponse_correcte}]}`
- `_build_html(session, nom_organisme, logo_data, themes_questions, avec_corrige)` : HTML WeasyPrint complet — en-tête (logo, titre, badge SUJET/CORRIGÉ, date + réf.), une `div.theme-block` par thème (grille n°X), table VRAI/FAUX — sujet : cases vides 16×16px ; corrigé : ✓ sur la bonne colonne, bandeau confidentiel rouge-orange
- `generer_sujet_vierge(session_id, db)` et `generer_corrige(session_id, db)` → bytes PDF via WeasyPrint

**Deux routes GET dans `main.py` (avant `@app.get("/")`) :**
| Route | Accès | Mécanisme |
|---|---|---|
| `GET /api/sessions/{id}/theorie/pdf/sujet` | Tous rôles connectés | `if not user: raise 401` (fail-closed) |
| `GET /api/sessions/{id}/theorie/pdf/corrige` | Tous rôles connectés (terrain inclus — le testeur corrige les copies) | `if not user: raise 401` (fail-closed) |

Auth via cookie `access_token` (middleware) — `window.open()` suffit, pas besoin de fetch+blob.
La route corrigé était initialement bloquée terrain (403) — décision révisée : le testeur a besoin du corrigé pour noter les copies papier.
Le catch-all terrain `method != GET and /api/sessions/*` ne bloque PAS les routes GET → pas de whitelist nécessaire dans `_verifier_role`.

**UX `session_detail.html` + `session_detail.js` :**
- Boutons `📄 Sujet PDF` et `📝 Corrigé PDF` dans le **card-header "CACES® Épreuve théorique"**, conditionnés sur `tirage_declenche` uniquement (visibles tous rôles)
- Listeners `data-action="pdf-sujet-theorie"` et `data-action="pdf-corrige-theorie"` → `window.open(url, '_blank')`

**Principe de sécurité appliqué :** garde fail-closed dans chaque route (`if not user: raise 401`) — protège même si le path se retrouvait accidentellement dans `_PUBLIC_PATTERNS`.

### ✅ Chantier terminé : page de projection collective test théorique (2026-06-17)

**Objectif :** afficher les questions à l'écran pour les candidats papier, sans jamais exposer la bonne réponse.

**Route `GET /sessions/{session_id}/projection/{jour_id}` (main.py) :**
- Garde fail-closed `if not user: raise 401` (même pattern routes PDF)
- Autorisée même si `date_cloture_terrain` non null (affichage pur, rien ne s'enregistre)
- Appelle `get_questions_phase2` (lecture seule, n'inclut pas `reponse_correcte`)
- Aplatissement en liste séquentielle 1→N dans l'ordre des thèmes (seq, theme, texte, image — jamais reponse_correcte)
- `ValueError` (pas de tirage) → `tirage_ok=False` → écran bloquant dans le template
- Passe `questions` (liste Python) au template, rendu via `tojson|forceescape` sur `#projection-data`

**Template `templates/projection_theorie.html` (standalone, pas base.html) :**
- Données injectées `data-questions` sur `#projection-data` (CSP-safe, pas d'inline JS)
- Boutons VRAI/FAUX : gris, `pointer-events:none` — décoratifs, aucune indication de réponse
- En-tête fixe bleu marine : réf/famille | Q{i}/{N}+Thème | chrono MM:SS (rouge si ≤60 s)
- Contrôles bas : ⏮ Précédent | ▶ Lecture | ⏭ Suivant | ⟳ Reset (tous `data-action`, CSP)
- Overlay fin : "⏰ Temps écoulé", bouton Reset
- Écran bloquant orange si `tirage_ok=False`

**JS `static/js/projection_theorie.js` :**
- **Chrono monotone INRS** : `chronoStartTs` (timestamp du 1er Lecture) ; `getElapsedMs() = Date.now() - chronoStartTs` — ne s'arrête JAMAIS une fois démarré (ni en pause). Seul Reset le remet à null.
- **`playing`** : booléen séparé ; contrôle uniquement le défilement auto et la voix. `pause()` bascule `playing=false` sans toucher au chrono.
- `interval` (250 ms) : lancé au 1er Lecture, tourne en continu (même en pause). `tick()` appelle `renderTimer()` toujours ; n'avance les questions que si `playing=true`.
- **Créneau par question `slotStartTs` (commit 6350771)** : `slotStartTs` (play-time seulement) + `pauseBeganAt`. `slotElapsedMs()` retourne le temps de LECTURE sur la question courante (pause non comptée). Auto-avance quand `slotElapsedMs() >= DUR_MS`. `resetSlot()` appelé sur auto-avance, ⏭, ⏮ → la question suivante repart TOUJOURS pour un créneau plein.
- **`lastAutoStep` supprimé** : l'auto-avance ne se base PLUS sur `floor(elapsed_global/DUR_MS)`.
- **Pause-awareness** : `pause()` enregistre `pauseBeganAt = Date.now()`. Reprise dans `play()` : `slotStartTs += Date.now() - pauseBeganAt` (décale le départ, préserve le temps restant du créneau). `resetSlot()` depuis pause : `pauseBeganAt = Date.now()` → créneau gelé à 0 jusqu'à reprise.
- **⏮/⏭ manuels** : `resetSlot()` après `currentIdx--/++` — créneau plein indépendamment du chrono global.
- Fin à 0:00 : `clearInterval` dans `tick()` + overlay. Exactement 1h après le 1er Lecture, quelles que soient les pauses.
- **Primauté absolue du chrono global (commit a39f34b)** : `tick()` vérifie `remainingMs() <= 0` EN PREMIER, avant tout auto-advance. Si le global atteint 0:00 pendant qu'une question a encore du "créneau" devant elle (DUR_MS non épuisé), l'overlay est déclenché **immédiatement**, sans attendre la fin du créneau. Le créneau (`Math.floor(elapsed/DUR_MS)`) est purement calculé — il n'existe pas de timer vivant `slotStartTs`. Naviguer manuellement juste avant 0:00 ne prolonge PAS la session : le global tick suivant (≤ 250 ms) coupe net. `prev`/`next` ont un guard `if (!finished)` — ils refusent toute action après la fin.
- ⟳ Reset : seul point qui remet `chronoStartTs=null`, `lastAutoStep=0`, `currentIdx=0`, `clearInterval`.
- AUCUN fetch, AUCUN enregistrement
- **Synthèse vocale** : `speak()` config `fr-FR / rate 0.9` identique à `test_theorie.html` ; contournement bug Chrome cancel→speak : `setTimeout(fn, 100)` CSP-safe + `clearTimeout(_speakTimer)` anti-chevauchement sur auto-avances ; `cancelSpeech()` annule aussi le timer pending ; lecture auto sur `play()` + auto-avance + prev/next en mode lecture ; `cancelSpeech()` sur pause / reset / fin chrono ; bouton `🔊 Relire` dans la barre de contrôles (`data-action="relire"`, CSP-safe)

**UX session_detail.html :**
- Les 3 boutons 📽️/📄/📝 sont dans le **card-header "CACES® Épreuve théorique"** (hors boucle) — `{% set _jour_theorie = (jours_test | default([])) | selectattr('type', 'equalto', 'theorie') | first | default(none) %}` avant la carte ; 📽️ conditionné `tirage_declenche and _jour_theorie`, `data-jour-id="{{ _jour_theorie.id }}"` ; 📄/📝 conditionnés `tirage_declenche` seul
- Visible tous rôles, disponible même si session terrain clôturée
- Listener `window.open('/sessions/'+sid+'/projection/'+jourId, '_blank')` dans `session_detail.js`

### ✅ Chantier terminé : saisie dégradée test théorique (toutes sections)

**Principe directeur (révisé — voir chantier scoring ci-dessous) :** le mode dégradé court-circuite `calculer_resultat_theorie_phase2` (collision de clés) et calcule directement `note_theme = sum(q.points for q in qs[:n_bonnes])`. Le mode numérique passe bien par `calculer_resultat_theorie_phase2` mais avec clé composite `"{theme}_{numero}"` désormais.

**Sections terminées (commits 53fc22c + 81a38d1) :**

*Section 1 — Migration justificatif :*
- `ResultatTheorie` : +`justificatif_pdf` (Text) +`justificatif_nom` (VARCHAR 255)
- Startup migrations + `migrate_justificatif_theorie.py` (idempotent, **à exécuter sur prod**)

*Section 2 — Route POST `/api/sessions/{id}/theorie/reponses-degrade` :*
- JWT requis, PIN formateur dans le body (`NotesParThemeCreate`)
- Body : `{jour_test_id, stagiaire_id, pin, notes_par_theme: {str: int}}` — nb bonnes réponses par thème
- Totaux par thème depuis le tirage réel (UtilisationTheme + ReponseGrille), pas les valeurs hardcodées templates
- Validation : `0 ≤ note ≤ len(questions_du_theme)` (0 = thème entièrement raté = valide)
- Reponses synthétiques : N premières questions = correctes, reste = incorrectes → `calculer_resultat_theorie_phase2`
- 409 si résultat numérique existant ; écrasement dégradé sans toucher justificatif
- Terrain accessible (whitelisté dans `_verifier_role`)

*Section 3 — Modal choix test sur bouton 🚀 (session_detail.html) :*
- `<a href="/test/theorie/...">` → `<button data-action="choix-test" data-session-id data-jour-id>`
- Modal `#modal-choix-test` : boutons `data-action="choix-test-numerique"` et `data-action="choix-test-degrade"`
- Contexte stocké sur `modal.dataset` (sid, jid) ; fermeture sur cancel ou choix
- `choix-test-numerique` → `window.open('/test/theorie/{sid}/{jid}', '_blank')`
- `choix-test-degrade` → `window.open('/sessions/{sid}/theorie/saisie-degrade/{jid}', '_blank')`
- Guards Jinja inchangés : `session.date_cloture_terrain is none` + `tirage_declenche`

*Section 4 — Page saisie dégradée :*
- Route `GET /sessions/{session_id}/theorie/saisie-degrade/{jour_id}` (main.py) — guard `request.state.user` ou 401
- Passe : `candidats` (avec `rt_data.notes = {str: int}` pour pré-remplissage, `rt_data.mode`), `themes` (tirage réel : `{num, nom, total}`)
- Template `templates/saisie_degrade.html` standalone : formulaire par candidat, blocage si mode numérique, pré-remplissage si dégradé existant, warning si pas de tirage
- `static/js/saisie_degrade.js` : auth Bearer (localStorage) + cookie (credentials same-origin) — double chemin auth pour page standalone (hors intercepteur base.html)
- `collecterNotes()` : `val === '' || Number.isNaN(parseInt(val, 10))` — 0 accepté (valide métier), champ vide rejeté
- Erreurs PIN : dans `#pin-error` DOM (aucun alert()), modal reste ouverte sur 403 et autres erreurs HTTP
- `afficherResultat()` : lit `resultat.notes_themes/max_themes/themes_ok` — zéro navigation DOM fragile

*Correctifs (commit 81a38d1) :*
- Terrain recevait 403 sur `reponses-degrade` : catch-all middleware bloquait → ajout exception dans `_verifier_role`
- Anticipation Section 6 : exception aussi ajoutée pour `POST theorie/justificatif/\d+/\d+`
- `Number.isNaN` (explicite, sans coercition) remplace `isNaN` dans `collecterNotes`

**Section 5 terminée (2026-06-18) :**

*Loupe numérique + correction qui atterrit sur le récap + suppression dégradée :*
- `td-th-result` dans `session_detail.html` : remplace Detail + ✏️ + 🗑️ par **🔍 loupe** (`data-action="loupe-theorie"`) uniquement si `rt.mode == 'numerique'` ; dégradé n'a pas de loupe (correction/suppression via saisie_degrade)
- `data-cloture="{{ '1' if session.statut == 'terminee' else '0' }}"` sur la loupe
- Modal `#modal-loupe-theorie` dans `session_detail.html` : 3 boutons (👁️ Visualiser / ✏️ Modifier / 🗑️ Supprimer) — Modifier masqué si `cloture=='1'`, Supprimer visible **tous rôles** (PIN formateur requis côté serveur)
- `session_detail.js` : nouveau bloc listener `loupe-theorie` (remplace les anciens `corriger-theorie`/`supprimer-theorie`) ; Visualiser → `window.open Detail` ; Modifier → PIN → POST reouvrir → localStorage `corriger_rt_*` → `window.open /start` ; Supprimer → PIN → DELETE reponses → reload
- `test_theorie.html` : `MODE_CORRECTION` (bool synchrone, lu avant `chargerQuestions()`) → si true, ne pas afficher `#ecran-identite` au démarrage ; en fin de pré-remplissage dans `chargerQuestions()` : met à jour la grille récap + appelle `afficherRecap()` → atterrit directement sur `#ecran-recap` pré-rempli, pas de timer
- `saisie_degrade.html` : bouton 🗑️ "Supprimer ce résultat" (`data-action="supprimer-degrade"`) visible si `cand.rt.mode == 'degrade'` — **tous rôles** (PIN formateur requis)
- `saisie_degrade.js` : `ouvrirPinSupprimer()`, `supprimerDegrade()`, dispatch action dans listener PIN (`_pending.action`) et dans keydown Enter

**Section 6 terminée (2026-06-18) :**

*Justificatif PDF — routes + UI session_detail + UI saisie_degrade :*
- `POST /api/sessions/{id}/theorie/justificatif/{stag}/{jour}` (sessions.py) : JWT + PIN formateur (`JustificatifBody`), stocke `fichier_base64` → `rt.justificatif_pdf` + `fichier_nom` → `rt.justificatif_nom`. Whitelist terrain déjà posée dans `_verifier_role` (commit 81a38d1).
- `GET /api/sessions/{id}/theorie/justificatif/{stag}/{jour}` (sessions.py) : JWT, `StreamingResponse` PDF ou 404. GET non bloqué par catch-all middleware.
- `main.py` (`page_saisie_degrade`) : `justificatif_nom` ajouté dans `rt_data` (dict candidat → template)
- `session_detail.html` : cellule `td-th-result` mode dégradé → 📎 vert si `rt.justificatif_nom` (`justif-voir`), 📎 gris sinon (`justif-upload`). Input caché `#justif-file-input`.
- `session_detail.js` : listener `justif-voir` → `window.open GET justificatif` ; listener `justif-upload` → stocke contexte, déclenche file input ; handler `change` sur `#justif-file-input` → FileReader → base64 → PIN modal → POST upload → reload.
- `saisie_degrade.html` : bouton 📎 (voir/upload) dans result-zone dégradé, tous rôles. Input caché `#sd-justif-file-input`.
- `saisie_degrade.js` : `uploadJustificatif()`, listener `sd-justif-file-input`, dispatch `action === 'justif'` dans `pin-confirmer` et `keydown Enter`.
- Accordéon cartes candidat (commit 4feb40e) : `cand-body` replié par défaut (`display:none`) ; `cand-head` cliquable (`data-action="toggle-carte-candidat"`, `data-stagiaire-id`) ; flèche `▶`/`▼` (`span.cand-arrow`) dans le premier div de l'en-tête (séparé du div badges pour ne pas être écrasé par `afficherResultat`) ; toggle indépendant par carte ; après enregistrement la carte reste ouverte (pas de reload, `cand-body` inchangé).

**Correctifs post-Section 5/6 (2026-06-18) :**

*Bug 1 — `Depends(get_utilisateur_courant)` → 403 "Not authenticated" (commit 62050fd) :*
- `OAuth2PasswordBearer` (utilisé par `get_utilisateur_courant`) lève `HTTPException(403, "Not authenticated")` si aucun header `Authorization: Bearer` — même si le cookie httponly est valide.
- `session_detail.js` envoie le Bearer depuis `localStorage.getItem('token')` — absent si localStorage vidé (nettoyage navigateur, données de navigation effacées, token expiré + reconnexion partielle).
- Résultat : `POST reouvrir`, `DELETE reponses`, `POST justificatif` renvoyaient 403 même PIN correct — `current_user` était déclaré mais jamais utilisé dans le body de ces 3 handlers.
- **Fix** : suppression de `current_user: Utilisateur = Depends(get_utilisateur_courant)` dans `reouvrir_theorie`, `supprimer_resultat_theorie`, `upload_justificatif_theorie`. Le middleware cookie assure l'auth ; le PIN assure l'autorisation.
- **Pattern désormais actif** : tous les handlers PIN (reouvrir/supprimer/justificatif) n'ont **plus** besoin de Bearer — identique au pattern GET justificatif corrigé précédemment.

*Bug 2 — SyntaxError `const opt` dupliqué (commit 2bdf712) :*
- `allerConfirmation()` dans `test_theorie.html` déclarait `const opt` deux fois dans le même scope (ligne 885 pour le check `data-a-resultat`, ligne 910 pour lire nom/prenom — même valeur, même sélecteur).
- `SyntaxError: Identifier 'opt' has already been declared` → **tout le script s'arrêtait au parse** : MODE_CORRECTION jamais évalué, aucun log [CORR], atterrissage cassé.
- **Fix** : suppression de la deuxième déclaration (ligne 910). `opt` déclaré ligne 885 reste valide sur tout le scope de la fonction.

*Logs de diagnostic temporaires (commit ebf871f — à supprimer après vérification) :*
- `test_theorie.html` : 4 `console.log('[CORR] ...')` après détection MODE_CORRECTION (SESSION_ID, JOUR_ID, START_STAGIAIRE_ID, clé lue, valeur localStorage, MODE_CORRECTION).
- `session_detail.js` : 1 `console.log('[CORR] cle ecrite ...')` avant `localStorage.setItem` dans le handler loupe-modifier.
- **À retirer** une fois la cause de MODE_CORRECTION=false confirmée.

*Bug 4 — badge RÉUSSI/ÉCHEC absent en mode numérique dans saisie_degrade.html (commit 6afb730) :*
- En-tête carte candidat : dégradé affichait "Saisie papier" + RÉUSSI/ÉCHEC, numérique affichait "Numérique" seul (pas de badge pass/fail).
- `rt.obtenue` est renseigné identiquement pour les deux modes (même `calculer_resultat_theorie_phase2`).
- **Fix** : bloc RÉUSSI/ÉCHEC sorti du `if degrade` → s'applique aux deux modes. "En attente" et "Dispensé" inchangés.

*Bug 3 — `btn-voir-recap` invisible hors dernière question (commit 411339b) :*
- En MODE_CORRECTION, cliquer une question depuis le récap → QCM ; le bouton "Voir le récap" était caché (condition `recapDebloque` = true seulement après la Q100 en passation normale) → impossible de revenir au récap sans tout parcourir.
- **Fix** : `afficherQuestion()` → `(MODE_CORRECTION || recapDebloque) ? 'block' : 'none'`. En passation normale : comportement inchangé.

### ✅ Chantier terminé : accordéon dashboard 4 cartes (commit c2ef021)

- `templates/dashboard.html` : 4 en-têtes de carte rendus cliquables (`data-action="toggle-dash-carte"`, `data-carte="{nom}"`, `cursor:pointer`), flèche `▶/▼` (`<span class="dash-arrow">`), corps wrappé dans `<div class="dash-card-body" style="display:none;">`.
- `static/js/dashboard.js` : nouveau fichier IIFE. `appliquerEtat()` au DOMContentLoaded lit localStorage, toggle au clic écrit localStorage. Clés : `dash_replie_cartographie`, `dash_replie_organisation`, `dash_replie_testeurs`, `dash_replie_documents`. Valeur `'false'` = déplié (défaut = replié).
- **Cartes NON touchées** : `⚡ À traiter`, `📊 Statistiques`.
- Clic sur `<a>` ou `<button>` dans l'en-tête (ex. "Voir tout" Testeurs) ne déclenche PAS le toggle.

### ✅ Chantier terminé : dashboard responsive — 4 cartes réaffichées mobile (commit eaff678)

- Suppression de `.dash-grid > .card:not(.dash-a-traiter) { display: none; }` dans la `@media (max-width: 1023px)` de `dashboard.html`.
- Les 4 cartes accordéon s'affichent sur tablette/mobile repliées par défaut → compact.
- Effet de bord accepté : la carte Statistiques (placeholder "Indicateurs à venir") réapparaît aussi sur mobile.
- **Blocage terrain intact** : middleware `_verifier_role` dans `main.py` ligne 514 redirige `GET /` vers `/sessions` côté serveur — non modifié.

### ✅ Chantier terminé : accordéon sous-sections "À traiter" (commit 49a174b)

- 5 sous-sections de la carte `⚡ À traiter` repliées par défaut : Sessions non clôturées, CACES® à valider, Non-conformités ouvertes, Alertes testeurs, Candidats sans photo.
- `data-action="toggle-dash-section"` + `data-section="{nom}"` sur chaque en-tête de section ; `dash-section-body` wrappant le `{% if %}...{% else %}✅ Aucun{% endif %}` complet.
- `dashboard.js` étendu : `SECTIONS` array, `clefSection()`, toggle via `head.nextElementSibling` (body est toujours le frère immédiat).
- Clés localStorage : `dash_section_replie_sessions`, `_caces`, `_nc`, `_alertes`, `_photos`. Valeur `'false'` = déplié.
- La carte "À traiter" elle-même reste toujours visible (pas de toggle carte-niveau).

### ✅ Chantier terminé (partiel) : export ZIP session — corrigé + récap + justificatifs (commit 73251cf)

**Règles d'accès :**
- Disponible quel que soit le statut de la session
- Bouton visible back-office uniquement (admin/utilisateur) — masqué terrain
- PIN admin 1505 requis, vérifié côté serveur

**`app/services/export_zip_session.py` :**
- `generer_zip_session(session_id, db) -> bytes` — BytesIO + zipfile.ZIP_DEFLATED, aucun fichier disque
- `corrige.pdf` : `generer_corrige()`, `recap_resultats.pdf` : `generer_recap_resultats()`
- `justificatifs/{nom}` : tous les `ResultatTheorie` ayant `justificatif_pdf is not None`, décodés base64
- Chaque pièce dans un `try/except` indépendant : un échec partiel n'annule pas le reste

**Route `GET /sessions/{session_id}/export-zip?pin=` (main.py) :**
- Auth cookie, terrain → 403, PIN `!= "1505"` → 403, session introuvable → 404
- `StreamingResponse` `application/zip` ; `Content-Disposition: attachment; filename=session-{ref}.zip`

**UX :**
- Bouton violet 📦 "Exporter le dossier (ZIP)" dans les actions session (back-office uniquement)
- Listener `data-action="export-zip"` → modal PIN admin existante → `window.open GET export-zip?pin=` → téléchargement direct

**`app/services/pdf_recap_session.py` (étape 1/3 — commit 7bfca47) :**
- `generer_recap_resultats(session_id, db) -> bytes` — PDF WeasyPrint A4
- Candidats actifs (SessionCandidat JOIN Stagiaire, tri nom/prénom)
- Théorie : dernier RT par candidat (`id DESC`) — diffère volontairement de l'affichage (qui prend le meilleur réussi)
- Badge Acquis/Échec/En attente indépendant par partie ; `page-break-inside: avoid` par bloc

**`app/services/pdf_detail_theorie.py` (créé) :**
- `generer_pdf_detail_theorie(rt_id, db) -> bytes` — PDF WeasyPrint A4, mode='numerique' uniquement
- `_collecter_donnees(rt, db)` : même logique que `page_detail_theorie` (main.py:1910–1948), pas de N+1 ; clé composite `{theme}_{numero}` (comme le scoring)
- Colonnes : N° · Question · Pts · Réponse candidat (VRAI/FAUX/—) · Résultat (✅/❌)
- **SANS** colonne "Bonne réponse" — le corrigé est un fichier séparé du ZIP
- En-tête : nom candidat, badge RÉUSSI/ÉCHEC + note totale, session + date + famille + logo
- Score par thème dans le header bleu (note/max + ✅/❌) ; `break-inside: avoid` par thème
- Non encore branché au ZIP (prochaine étape)

**`app/services/pdf_consentement_neutralite.py` (créé) :**
- `generer_pdf_consentement(consentement_id, db) -> bytes` — PDF WeasyPrint A4
  En-tête session + logo ; 3 cases OUI/NON (rgpd_accepte, photo_accepte, plaintes_atteste) ; vérificateur ; horodatage ; img signature
- `generer_pdf_neutralite(attestation_id, db) -> bytes` — PDF WeasyPrint A4
  Rejoint session via `AttestationNeutralite.jour_test_id → JourTest.session_id` ; vérificateur ; horodatage ; img signature
- `signature_base64` : data URI canvas JS (`data:image/...;base64,...`) → utilisée directement comme src ; fallback PNG si base64 brut
- Nullables : horodatage null → "Non signé" ; signature absente → texte "Non signé"

**ZIP — contenu FINAL (export_zip_session.py — ✅ COMPLET) :**
```
session-REF.zip
├── corrige.pdf
├── recap_resultats.pdf
├── justificatifs/{nom_upload}.pdf              ← mode dégradé avec justificatif scanné
├── tests_numeriques/{NOM_Prenom}.pdf           ← mode numérique avec reponses_json
├── consentements/consentement_{NOM_Prenom}.pdf ← ConsentementRGPD par candidat
└── neutralite/neutralite_{NOM_Prenom}.pdf      ← AttestationNeutralite par candidat
```
- Batch-load unique stagiaires : union des stag_ids depuis RT + ConsentementRGPD + AttestationNeutralite
- JourTest batch : `JourTest.id` WHERE `session_id == session_id` → jt_ids → AttestationNeutralite.jour_test_id.in_(jt_ids)
- try/except indépendant par pièce ; `_sanitize()` remplace `/\:*?"<>| ` dans les noms de fichiers
- Helper `_nom_candidat(stagiaire_id, stagiaires)` → `NOM_Prenom` ou `stagXXX`

### Chantier en cours : suppression habilitation (hard delete)
Objectif : ajouter un bouton 🗑️ dans la modal de modification d'un testeur existant pour supprimer définitivement une habilitation (hard delete SQL + PIN 1505).

Fichiers à modifier :
- `app/routers/admin.py` — route `DELETE /admin/habilitation/{id}` : ajouter `pin`, vérification PIN, remplacer soft delete par `db.delete()`
- `templates/admin.html` — `demanderPin()` : passer `pin` au callback ; `desactiverHabTesteur()` : transmettre `?pin=` à l'API
- `templates/testeurs.html` — ajouter divs cachés `#habs-{id}` + section `#section-habs-modal` dans la modal
- `static/js/testeurs.js` — `editer()` : peupler la liste habilitations ; ajouter `supprimerHab()` + handler `supprimer-hab`

### ✅ Chantier terminé : page detail_theorie.html — header redesigné + bouton impression (commit 5927e82)

**Objectif :** supprimer le titre répété, mettre en avant le candidat, ajouter les infos de session, ajouter l'impression navigateur.

**Modifications :**
- `app/main.py` (route `page_detail_theorie`) : ajout de `"session": session_obj` dans le contexte template — expose `session.reference` et `session.date_theorie`.
- `templates/detail_theorie.html` : titre "Détail du test théorique" supprimé ; nom candidat promu en `h1` (Barlow Condensed 32px, bleu marine `#1a237e`) ; ligne meta "Session {ref} · {date}" + badge RÉUSSI/ÉCHEC ; bouton `🖨️ Imprimer` (`data-action="imprimer-detail"`, `.no-print`, `.btn.btn-secondary`, `align-self:flex-start`) ; `<style>@media print>` masque `.sidebar`, `.topbar`, `.no-print`, met `.main {margin-left:0}`, `tr {page-break-inside:avoid}`, `print-color-adjust:exact` sur lignes colorées et badges.
- `static/js/detail_theorie.js` : créé — IIFE, listener `data-action="imprimer-detail"` → `window.print()`. CSP-safe.

**Règle print :** `.no-print` masque le lien retour et le bouton imprimer. `.main {margin-left:0}` supprime le décalage sidebar en impression.

### ✅ Chantier terminé : renommage UX 'dégradé'/'papier' → 'manuelle' (commit 6b56584)

**Règle permanente (NE PAS revenir en arrière) :**
- La valeur `mode='degrade'` en base, les noms de routes (`/reponses-degrade`), les noms de fichiers (`saisie_degrade.html`, `saisie_degrade.js`) et les noms de variables/fonctions sont **inchangés**.
- Seul le **texte visible par l'utilisateur** utilise "manuelle" / "manuel" à la place de "dégradé" / "papier".

Occurrences modifiées :
- `saisie_degrade.html` : `<title>`, en-tête `sd-title`, avertissement `sd-warning`, badge `Saisie papier` → `Saisie manuelle`, message blocage numérique.
- `saisie_degrade.js` : badge dynamique dans `afficherResultat()` après enregistrement.
- `session_detail.html` : label bouton "Saisie manuelle (papier)" → "Saisie manuelle", sous-titre.
- `test_theorie.html` : option dropdown (`— ✍️ manuel`), deux messages blocage (`Une saisie manuelle a déjà été enregistrée`).
- `sessions.py` (HTTP 409) : "Un résultat de saisie manuelle existe pour ce jour — supprimez-le d'abord (Corriger/Supprimer sous PIN)."

### ✅ Chantier terminé : double bug de scoring théorique numérique + dégradé (commits 930583d + 627b2ca)

**Symptôme :** totaux faux dans les deux modes — +1 bonne réponse = +4 points en numérique ; 4/4/4/4/4 donnait 39 au lieu de 20 en dégradé.

**Bug 1 — collision de clés (×4) :**
- `q.numero_question` est LOCAL au thème (T1 : 1–12, T2 : 1–28, T3 : 1–44…). Le dict de réponses `{"1": bool, …}` avait au maximum 44 clés pour 100 questions — les thèmes s'écrasaient mutuellement. Au scoring, chaque thème interrogeait la même clé "1" → une réponse comptée dans plusieurs thèmes → ×4.
- **Fix :** clé composite **`"{theme}_{numero}"`** (ex. `"2_7"`), globalement unique sur tout le test. Appliqué en 4 endroits synchronisés :
  - `templates/test_theorie.html` — `valider()` : `reponsesFinales[String(q.theme)+'_'+String(q.numero)]`
  - `templates/test_theorie.html` — pre-fill mode correction : même format
  - `app/services/tirage_grille.py` — `calculer_resultat_theorie_phase2` : `str(ut.theme)+"_"+str(q.numero_question)`
  - `app/main.py` — `page_detail_theorie` : `str(ut.theme)+"_"+str(r.numero_question)`

**Bug 2 — calcul dégradé via comparaison synthétique :**
- `calculer_resultat_theorie_phase2` était appelée en mode dégradé avec un dict synthétique (`reponses_synthetique`) construit thème par thème. Même avec `not q.reponse_correcte` pour les mauvaises réponses, les collisions de clés (T5 écrasait T1–T4 sur les clés "1"–"4") produisaient des coïncidences parasites (+15 sur T2 avec n_bonnes=4).
- **Fix :** court-circuit complet — le dégradé ne passe plus par `calculer_resultat_theorie_phase2`. Calcul direct dans le handler `soumettre_reponses_theorie_degrade` : `note_theme = sum(q.points for q in qs[:n_bonnes])` pour chaque thème.

**⚠️ Principes à ne jamais casser :**
1. La clé d'une réponse est composite `{theme}_{numero}`, unique sur tout le test. JS (construction) et Python (scoring + detail_theorie) utilisent le MÊME format.
2. Une question NON RÉPONDUE (absente du dict) = 0 point sans comparaison. Ne jamais mettre une valeur par défaut (false) à une non-réponse → coïncidences.
3. "Répondu FAUX" (présent, valeur false) ≠ "Non répondu" (absent). Un candidat qui coche FAUX sur une question dont la bonne réponse est FAUX obtient +1 légitime.
4. Numérique et dégradé partagent `calculer_resultat_theorie_phase2` pour le numérique seulement. Toute modif du scoring doit être testée dans les deux modes.

**Tests de non-régression :**
- Numérique : 1 seule bonne réponse → total 1 (1 seule ligne `[DIAG CALC] ... => CORRECT`).
- Numérique : +1 bonne réponse → +1 point (PAS +4 : sinon collision revenue).
- Numérique : répondre FAUX à une question dont la bonne réponse est FAUX → +1.
- Numérique : ne rien répondre → total 0.
- Dégradé : 4/4/4/4/4 → total 20, notes_themes={4,4,4,4,4}.
- Dégradé : 1/1/1/1/1 → total 5.

**Logs temporaires à retirer** (commits 06f7641 + 7d5fc0f + 627b2ca) : `[DIAG DEGRADE]`, `[DIAG NUMERIQUE]`, `[DIAG CALC]` dans `sessions.py` et `tirage_grille.py`. Et `[CORR]` de commit `ebf871f` dans `test_theorie.html` + `session_detail.js`.

### ✅ Chantier terminé : enrichissement récap résultats — date + testeur par épreuve

**Fichier modifié :** `app/services/pdf_recap_session.py`

**`_collecter_donnees` — requêtes groupées anti-N+1 :**
- 1 requête groupée `JourTest.id.in_([rt.jour_test_id …])` pour tous les RT de la session → dict `{jt.id: JourTest}`.
- 1 requête groupée `Testeur.id.in_(ids)` pour l'union des testeur_id théorie (via JourTest) + pratique (via SessionEpreuve) → dict `{t.id: "Nom Prénom"}`.
- Aucun N+1, aucune jointure ORM implicite.

**Champs ajoutés par épreuve :**
| Épreuve | date | testeur |
|---|---|---|
| Théorie | `JourTest.date` via `rt.jour_test_id` | `JourTest.testeur_id → Testeur.nom+prenom` (nullable → `None`) |
| Pratique | `SessionEpreuve.date` (direct, NOT NULL) | `SessionEpreuve.testeur_id → Testeur.nom+prenom` (NOT NULL) |

**`testeurs_sup` (`JourTest.testeurs_sup TEXT`) :** parsé via `json.loads` → liste de strings → concaténé avec `" + "` après le testeur principal. Champ jamais écrit (NULL partout en prod) — gestion défensive uniquement.

**Rendu PDF :**
- Helper `_meta_str(date, testeur)` → `<span style='color:#888; font-size:9px;'>jj/mm/aaaa · Nom Prénom</span>` (ou `"—"` si testeur_id NULL côté théorie).
- Inséré à la fin de `ep-detail` pour la ligne théorie ET chaque ligne pratique.

**Imports ajoutés :** `import json`, `from app.models.jour_test import JourTest`, `from app.models.testeur import Testeur`.

### ✅ Chantier terminé : récap PDF — enrichissement Formation (commit f673bde)

**`_collecter_donnees` → retourne maintenant `(candidats, formation_meta)` (tuple).**

Requêtes groupées anti-N+1 ajoutées :
1. `JourFormation.session_id == session_id, actif=True` → `jf_ids`
2. `AffectationFormation.jour_formation_id.in_(jf_ids)` + `Utilisateur.id.in_(user_ids)` → formateurs (Utilisateur, PAS Testeur)
3. `PlanningApprenant.jour_formation_id.in_(jf_ids), actif=True` → heures par stagiaire_id

**`formation_meta = {"has_formation": bool, "formateurs": str}` :**
- `has_formation` = True si au moins un JourFormation actif → contrôle l'affichage (section omise si False)
- `formateurs` = "Nom Prénom (principal), Nom Prénom" — dédupliqué : si un Utilisateur est principal sur AU MOINS un jour, classé "principal"

**`heures_formation` par candidat :** `heures_theorie + sum(heures_par_cat.values()) + heures_libre` sur tous ses PlanningApprenant de la session. `None` si absent (affiché "—").

**Affichage dans `_build_html` :**
- En-tête session (`.doc-meta`) : ligne `Formateurs :` si `has_formation and formateurs_str`
- Bloc candidat : ligne `Formation | | X h` AVANT Théorie et Pratique, uniquement si `has_formation`

**`generer_recap_resultats`** : dépaquette le tuple → `candidats, formation = _collecter_donnees(...)` → `_build_html(..., formation)`.

**Modèles utilisés (tables) :** `jours_formation`, `affectations_formation`, `planning_apprenants`, `utilisateurs`.

### ✅ Chantier terminé : récap PDF — formateurs rôles agrégés TH/PRAT (commit 49bc8f4)

**Contexte :** l'en-tête du récap affichait "(principal)" pour les formateurs — remplacé par les rôles réels agrégés sur toute la session.

**Règle affichage :** pour chaque `Utilisateur` formateur de la session, on OR les booléens `AffectationFormation.theorie` et `.pratique` sur TOUS ses jours. Label :
- `(TH + PRAT)` si les deux
- `(TH)` si théorie seule
- `(PRAT)` si pratique seule
- rien si aucun booléen vrai

**Fichier :** `app/services/pdf_recap_session.py` — section `_collecter_donnees`. Remplacement des dicts `principal_ids/autre_ids` par `user_theorie/user_pratique` (dict `{uid: bool}`) agrégés par `or`. Tri alphabétique par nom. `formateurs_label` rejoint les labels avec `", "`.

**Champ supprimé :** colonne `principal` d'`AffectationFormation` — plus jamais utilisée dans ce service (son usage UX dans d'autres vues est inchangé).

### ✅ Chantier terminé : export ZIP — UX fond-de-tâche + toast (commits 49bc8f4 + 1f624e7)

**Comportement :** au clic "Confirmer" (PIN saisi), la modal se ferme immédiatement, un toast "Téléchargement en cours…" apparaît 2 s, le fetch tourne en arrière-plan, le fichier se télécharge sans bloquer l'UI.

**Pattern JS (`session_detail.js`) :**
1. `fermerPin()` immédiat
2. `afficherSuccesToast('Téléchargement en cours…')`
3. `fetch('/sessions/{sid}/export-zip?pin=…', {credentials:'same-origin'})` — pas de `Bearer` (cookie suffit)
4. Succès : blob → `URL.createObjectURL` → `<a download>` → click → `removeChild` → `setTimeout(revokeObjectURL, 100)`
5. Erreur HTTP : `resp.json()` → `afficherErreur(data.detail || 'Erreur N')` (modal-alerte)
6. Erreur réseau : `console.error` + `afficherErreur('Erreur réseau…')`

**Contrainte auth :** `credentials:'same-origin'` envoie le cookie `access_token`. Ne pas ajouter `Authorization: Bearer` (absent de localStorage si session renouvelée → 403 `get_utilisateur_courant`).

### ✅ Chantier terminé : PDF détail test numérique — date via JourTest (commit c5c4c80)

**Bug :** la date en haut à droite du PDF n'était pas affichée — `_build_html` utilisait `session.date_theorie` qui est souvent `None`.

**Cause racine :** `ResultatTheorie` n'a pas de champ `date`. La date vit sur `JourTest.date` via `rt.jour_test_id`.

**Fix (`app/services/pdf_detail_theorie.py`) :**
1. Import : ajout `JourTest` dans `from app.models.jour_test import ResultatTheorie, JourTest`
2. `_collecter_donnees` : requête `JourTest.id == rt.jour_test_id` ; `date_str = jour.date.strftime("%d/%m/%Y") if jour and jour.date else "—"` ; inclus dans le dict retourné
3. `_build_html` : `date_str = donnees["date_str"]` (remplace le calcul via `session.date_theorie`)
4. Template (ligne 291) : `{date_str}` inchangé — déjà correct

**Règle :** ne jamais utiliser `session.date_theorie` pour la date du test théorique — utiliser `JourTest.date` via FK.

### ✅ Chantier terminé : testeur théorique par candidat — étapes 1-5 (commits 7168ae5, 3f937bf, c5716c1, 7e1af14 + étape 5 sans commit distinct)

**Objectif :** stocker et afficher le testeur **par candidat** sur le test théorique (numérique + manuel), distinct du testeur du jour.

**Étape 1 — Migration `ResultatTheorie.testeur_id` :**
- `ResultatTheorie` : +`testeur_id INTEGER REFERENCES testeurs(id)` (nullable)
- `migrate_testeur_theorie.py` (idempotent) + migration startup (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`)
- **À exécuter sur prod :** `python migrate_testeur_theorie.py` dans Render Shell

**Étape 2 — Endpoint `GET /api/testeurs/habilites?famille=` :**
- Route dans `app/routers/testeurs.py` — déclarée AVANT `GET /{id}` (sinon FastAPI tente de caster "habilites" en int → 422)
- Filtre : `HabilitationTesteur.famille == famille, actif==True, Testeur.actif==True, Testeur.etat=="actif"` — distinct, tri nom/prenom
- Auth : middleware cookie (`request.state.user`)

**Étape 3 — Saisie numérique (`test_theorie.html`) :**
- Voie tablette : select `#card-testeur-select` (habilités pour la famille), obligatoire dans `allerConfirmation()`
- Voie QR (`START_DIRECT`) : `testeurId = TESTEUR_ID_JOUR` hérité du JourTest (pas de select)
- Pré-sélection : RT existant > testeur du jour > unique habilité
- `POST /api/sessions/{id}/theorie/reponses` : `testeur_id` dans le body et dans le `ResultatTheorie`

**Étape 4 — Saisie manuelle (`saisie_degrade.html` + `saisie_degrade.js`) :**
- Select `sd-select-testeur` par candidat, obligatoire avant enregistrement
- Pré-sélection : RT existant > testeur du jour > unique habilité
- `POST /api/sessions/{id}/theorie/reponses-degrade` : `testeur_id` dans le body et dans le `ResultatTheorie`

**Étape 5 — Report dans les PDF :**
- `pdf_recap_session.py` : `rt.testeur_id` des tous les RT ajoutés au batch `testeur_ids` (anti-N+1) ; ligne théorie : `testeurs.get(rt.testeur_id) if rt.testeur_id else _testeur_label(jt)` (fallback testeur du jour — anciens résultats)
- `pdf_detail_theorie.py` : `_collecter_donnees` résout `rt.testeur_id` ou fallback `jour.testeur_id` → `testeur_str` ; `_build_html` affiche `<div><strong>Testeur :</strong> {_esc(testeur_str or '—')}</div>` dans `.doc-meta`

**Règle de fallback :** si `rt.testeur_id` est NULL (résultats antérieurs au chantier), on retombe sur le testeur du jour (`JourTest.testeur_id`). Un candidat saisi après le déploiement aura toujours son testeur propre.

**Migrations prod à exécuter (dans Render Shell) :**
```
python migrate_justificatif_theorie.py
python migrate_cloture_terrain.py
python migrate_testeur_theorie.py
```

**Compléments post-étapes 1-5 (commits a2f1967, 6e6cbaa) :**

- **QR test théorique sans testeur du jour** : dans le listener `select-candidat` de `test_theorie.html`, si `TESTEUR_ID_JOUR` est null → avertissement non bloquant dans `#msg-bloque-select` ("Vous n'avez pas indiqué de testeur pour ce jour."), QR généré quand même. La voie QR hérite du testeur du jour (`TESTEUR_ID_JOUR`) ; si absent, le RT est enregistré sans testeur (le testeur est désigné par candidat sur la voie tablette, pas sur la voie QR).

- **Testeur modifiable en correction numérique** (loupe → Modifier → récap) :
  - `reouvrir_theorie` (sessions.py) : ajoute `"testeur_id": rt.testeur_id` dans la réponse JSON
  - `session_detail.js` (handler `loupe-modifier`) : stocke `localStorage['testeur_corr_{sid}_{jid}_{stag}'] = data.testeur_id ?? ''`
  - `test_theorie.html` `#ecran-recap` : bloc `#bloc-testeur-corr` masqué (select + label), affiché en `MODE_CORRECTION` uniquement
  - En `MODE_CORRECTION` (après `afficherRecap()`) : fetch habilités, peuplement select, pré-sélection sur testeur actuel, listener `change` → `testeurId`
  - `valider()` envoie déjà `testeur_id: testeurId || null` — inchangé
  - **Non bloquant** : laisser vide → `null` envoyé → `if data.testeur_id is not None` échoue → ancien testeur conservé en base

- **Fix `_get_theorie_pratique` (`caces_obtenus.py`)** (commit 730d641) : le testeur théorie affiché dans CACES® Obtenus lisait `jour_theo.testeur_id` en priorité, ignorant `rt.testeur_id`. Corrigé : `testeur_theo_id = (rt.testeur_id if rt else None) or (jour_theo.testeur_id if jour_theo else None)`.

### ✅ Chantier terminé : refonte layout cartes CACES® à valider (commit 7c9e67d)

**Fichier modifié :** `static/js/caces_obtenus.js`

**`renderCarteAValider` — abandon du layout 3 colonnes (dates | sources | actions) au profit d'un layout vertical :**
- `flex-direction:column` sur le corps de carte (supprime `co-scroll-wrap` du body, le layout vertical est nativement responsive)
- Ligne dates : obtention + échéance côte à côte (`display:flex;gap:24px;flex-wrap:wrap`)
- Ligne théorie : `🎓 Théorie` + lien session + date + ✅ + testeur
- Ligne pratique : `🔧 Pratique` + lien session + date + ✅ + options + testeur
- Pied de carte `id="caces-card-footer-{id}"` : bouton "↩ Révision" (`flex:1`, bordure orange) + bouton "📜 Émettre" (`flex:2`, fond vert) côte à côte ; si `statut==='annule'` → badge orange "En révision"

**`_apresRevisionCarte` — mise à jour du sélecteur DOM :**
- Avant : `document.getElementById('caces-card-' + id + '-actions')`
- Après : `document.getElementById('caces-card-footer-' + id)`

### ✅ Chantier terminé : refonte visuelle bloc question test théorique (écran QCM)

**Périmètre :** intérieur de `#ecran-qcm` uniquement dans `templates/test_theorie.html`. Header (logo, titre, chrono, barre progression), écrans 1/2/3, récap et logique de scoring : NON touchés. Bascule identité anthracite NORYX + restyle des autres écrans = chantier ultérieur (faire tout d'un bloc, pas d'état hybride).

**HTML (`#ecran-qcm`) :**
- Migration des 5 boutons `onclick` inline → `data-action` (CSP-safe, listener délégué) : `relire-question`, `repondre` (`data-valeur` true/false), `precedent`, `suivant`, `voir-recap`
- Image `#q-image` : suppression du fond gris (retrait `max-height:200px` + `background:#f0f2f7` + `object-fit:contain` figé) → `width:100%`, `height:auto`, `object-fit:contain`, photo plein largeur au ratio réel (1:1 majoritaire), zéro bande grise
- Bouton "🔊 Relire" → "▶ Écouter la question" (`.btn-ecouter`, pilule)
- Énoncé `.question-text` agrandi à 21px
- VRAI/FAUX en `.btn-reponse` avec pictos pouce (👍 VRAI / 👎 FAUX), 104px de haut

**Règle ergonomique VRAI/FAUX (public lisant difficilement) — NE PAS revenir en arrière sans raison :**
- Au repos : VRAI vert (`#1D9E75`/`#E1F5EE`), FAUX rouge (`#E24B4A`/`#FCEBEB`) — sert UNIQUEMENT à distinguer les deux boutons avant réponse
- Au clic : le bouton choisi passe au **JAUNE** (`#EF9F27`/`#FAEEDA`/`#854F0B`), IDENTIQUE pour VRAI et FAUX ; l'autre s'estompe (`opacity 0.45`). Le jaune ne signifie jamais "bon/mauvais" — juste "voici ton choix". Évite que le candidat lise vert=correct / rouge=erreur.
- Mécanique : classe `.selected` sur `#btn-vrai`/`#btn-faux` (inchangée) + classe `.a-repondu` sur `.reponse-grid` (nouvelle) qui déclenche l'estompage de l'autre via `.reponse-grid.a-repondu .btn-reponse:not(.selected)`
- Décision : possibilité de tester avec candidats réels et basculer vers neutre (jaune/anthracite au repos) si réflexe "cliquer le vert" observé — la règle de couleur est isolée dans le CSS, modifiable en un point

**JS :**
- `repondre(valeur)` : ajout de `classList.add('a-repondu')` sur `.reponse-grid`
- `afficherQuestion(idx)` : reset/réapplication de `a-repondu` selon état coché ; suppression des `btnS.onclick` dynamiques (`afficherRecap`/`suivant`) remplacés par `btnS.dataset.dernier` (`'1'` sur dernière question, `'0'` sinon)
- Listener délégué sur `#ecran-qcm` : route `data-action` → `repondre`/`precedent`/`suivant`/`relire-question`/`voir-recap` ; double rôle Suivante géré via `data-dernier` (`='1'` → `afficherRecap`, sinon `suivant`)

**Navigation :** Précédente discrète (lien), Suivante pilule bleu marine `#1a237e` (cohérent avec l'existant — pas d'anthracite cette passe).

**Note CSP corrigée dans les faits :** la CSP réellement posée (`app/main.py`) est `script-src * 'unsafe-inline' 'unsafe-eval'` — les `onclick` inline étaient autorisés, contrairement à la note "Render bloque les `onclick` inline". Migration `data-action` faite quand même sur ce bloc (conformité à la règle projet + anticipation d'un durcissement CSP futur). Chantier à prévoir : durcir la CSP + migrer tout le inline restant (`admin.html`, autres écrans `test_theorie.html`).

### ✅ Chantier terminé : refonte visuelle bloc question test théorique (écran QCM)

**Périmètre :** intérieur de #ecran-qcm dans templates/test_theorie.html uniquement. Header (logo, titre, chrono, barre progression), écrans 1/2/3, récap et logique de scoring : NON touchés. Bascule identité anthracite NORYX du header + refonte des autres écrans = chantier ultérieur, à faire d'un seul bloc (pas d'état hybride).

**CORRECTIONS D'ÉCARTS DOC/CODE découverts pendant ce chantier (la doc affirmait des choses non implémentées) :**
- .question-image avait TOUJOURS max-height:200px + background:#f0f2f7 → le fond gris n'avait jamais été supprimé malgré la doc. CORRIGÉ : width:100%, height:auto, object-fit:contain, border-radius:12px, box-shadow léger, plus aucun fond. Photo plein largeur au ratio réel (1:1 majoritaire, 167 caractères max sur les énoncés).
- La règle CSS d'estompage du bouton non sélectionné (.reponse-grid.a-repondu) était documentée mais N'EXISTAIT PAS dans le fichier. Le JS posait bien la classe a-repondu, sans effet. CORRIGÉ : règle ajoutée (ci-dessous).
- Note CSP rectifiée : la CSP réellement posée dans app/main.py est "script-src * 'unsafe-inline' 'unsafe-eval'" — les onclick inline étaient AUTORISÉS, contrairement à la note "Render bloque les onclick inline". Migration data-action faite quand même sur ce bloc (conformité règle projet + anticipation durcissement CSP futur). Chantier futur à prévoir : durcir la CSP + migrer tout le inline restant (admin.html, autres écrans de test_theorie.html).

**HTML #ecran-qcm :**
- 5 boutons migrés onclick inline → data-action (listener délégué sur #ecran-qcm) : relire-question, repondre (data-valeur true/false), precedent, suivant, voir-recap
- Bouton réécouter : icône haut-parleur 🔊 + texte "Réécouter", discret aligné à gauche (.btn-reecouter, sans fond ni bordure) — plus de bouton pleine largeur. data-action="relire-question" inchangé.
- VRAI/FAUX : .btn-reponse avec pictos pouce (👍 VRAI / 👎 FAUX), structure <span class="rep-ico"> + <span class="rep-mot">, hauteur 104px
- Bouton récap déplacé DANS .navigation entre Précédente et Suivante (id="btn-voir-recap" + data-action="voir-recap" conservés). Pilule gris ardoise #4a5568 texte blanc, même forme que Suivante (.btn-recap-mini).

**Règle ergonomique VRAI/FAUX (public lisant difficilement) — NE PAS revenir en arrière sans test terrain :**
- Au repos : VRAI vert (#1D9E75/#E1F5EE), FAUX rouge (#E24B4A/#FCEBEB) — sert UNIQUEMENT à distinguer les deux boutons avant réponse.
- Au clic : le bouton choisi passe au JAUNE (#EF9F27/#FAEEDA/#854F0B), IDENTIQUE pour VRAI et FAUX ; l'autre passe en GRIS estompé (#f5f5f5/#9e9e9e, opacity 0.5). Le jaune ne signifie jamais "bon/mauvais", juste "voici ton choix" — évite que le candidat lise vert=correct / rouge=erreur.
- Mécanique CSS : .btn-vrai.selected / .btn-faux.selected = jaune (règles spécifiques car elles doivent battre le vert/rouge du repos) ; .reponse-grid.a-repondu .btn-vrai:not(.selected) / .btn-faux:not(.selected) = gris (idem, spécificité nécessaire). Les anciennes règles .selected vert foncé #33691e / rouge foncé #b71c1c ont été SUPPRIMÉES (elles écrasaient le jaune).
- Mécanique JS : classe .selected sur #btn-vrai/#btn-faux (inchangée) + classe .a-repondu sur .reponse-grid posée dans repondre() et gérée dans afficherQuestion() selon état coché.
- Décision : couleur isolée dans le CSS, modifiable en un point si le réflexe "cliquer le vert" est observé en test réel → bascule vers version neutre.

**Énoncé .question-text :** font-size 21px, hauteur fixe min-height:130px (≈4 lignes, marge pour évolution des textes), display:flex align-items:center justify-content:flex-start text-align:left (aligné à gauche, centré verticalement) → VRAI/FAUX ne se déplacent plus entre questions courtes et longues. Couleur passée en gris ardoise #4a5568 (était #1a237e — choix assumé malgré contraste plus faible, réversible en une ligne).

**Ancrage zone réponse en bas (option B mobile) :** .qcm-card en display:flex flex-direction:column min-height:calc(100vh - 150px) box-sizing:border-box ; .reponse-grid margin-top:auto pousse VRAI/FAUX + navigation vers le bas. #ecran-qcm padding-bottom:12px (anti-scroll questions courtes). Les questions à grande photo peuvent encore scroller (volontaire, min-height pas height).

**Couleurs ardoise #4a5568 appliquées :** énoncé, bouton réécouter, badge thème (.theme-badge fond clair #edf0f3 + texte #4a5568, était #e8eaf6/#3949ab). Header non touché.

**JS :**
- repondre(valeur) : ajout classList.add('a-repondu') sur .reponse-grid
- afficherQuestion(idx) : reset/réapplication de a-repondu selon état coché ; suppression des btnS.onclick dynamiques (remplacés par btnS.dataset.dernier = '1' sur dernière question, '0' sinon)
- Listener délégué sur #ecran-qcm : route data-action → repondre/precedent/suivant/relire-question/voir-recap ; double rôle Suivante via data-dernier ('1' → afficherRecap, sinon suivant)
- Ligne d'affichage du bouton récap : 'block' remplacé par 'inline-flex' (pour que align-items de la pilule s'applique)

**Navigation :** Précédente discrète (lien), Suivante pilule bleu marine #1a237e (inchangé cette passe), Récap pilule ardoise au centre.

**Reste en suspens (non bloquant) :** le "titre Thème 1 - xxxx" n'a pas été identifié/tranché (badge déjà en ardoise ; vérifier s'il s'agissait d'un autre élément récap/consignes). Les alert() du chrono (10 min / 5 min) restent en place — à traiter avec le header.

---

### ✅ Chantier terminé : page d'aide /aide V1 (commit 2285595)

**Fichiers créés :**
- `templates/aide.html` — étend `base.html` ; bandeau anthracite `#2d2d2d`, barre de recherche, grille 10 cartes, 10 sections accordéon (3 avec contenu : Démarrage, Sessions, Tirage INRS ; 7 avec placeholder)
- `static/css/aide.css` — identité NORYX `#2d2d2d`/`#cc0000`, responsive 3 breakpoints (768px / 480px / 400px)
- `static/js/aide.js` — accordéons (data-action, addEventListener), clic carte → scroll + déplie section, recherche client filtre sections + cartes ; CSP-safe (aucun onclick inline)

**`app/main.py`** : route `GET /aide` (auth guard `_RedirectResponse("/login")` si non connecté), avant `/profil`.

**`templates/base.html`** : lien ❓ Aide ajouté dans la sidebar avant Administration, visible tous rôles.

**Responsive :**
- ≤768px : grille `minmax(140px,1fr)`, padding header réduit
- ≤480px : grille `1fr` (1 colonne), cartes en ligne (icône + label horizontal), `font-size:16px` sur input recherche (anti-zoom iOS), `min-height:48px` sur section-header
- ≤400px : `.aide-header-top` passe en `flex-wrap:wrap` (picto + titre en colonne si trop serré), padding/typo réduits
- `overflow-wrap:break-word` sur `.aide-section-body` (anti-débordement horizontal)

---

### ✅ Chantier terminé : refonte écran récap test théorique + ergonomie fin de test

**Périmètre :** #ecran-recap dans templates/test_theorie.html + bloc navigation de fin dans afficherQuestion(). Header non touché (réservé bascule anthracite). Logique de scoring/correction inchangée.

**En-tête récap — deux états (remplace l'ancien #recap-nb + label "questions repondues sur 100") :**
- État incomplet (#recap-etat-incomplet, .recap-cadres) : deux cadres sur une ligne — cadre gris "X sans réponse" (#recap-nb-sans, chiffre rouge #E24B4A) + cadre jaune "Y répondu" (#recap-nb, chiffre #854F0B). Pastilles carrées rappelant le code couleur.
- État complet (#recap-etat-complet, .recap-complet) : bandeau teal pâle #E1F5EE/#0F6E56 + check ✓ (CSS pur, U+2713 dans pastille ronde verte #1D9E75) "Toutes les questions sont répondues — 100/100". Affiché quand nbSans <= 0.
- Bascule gérée dans afficherRecap() : calcule nbRep/total/nbSans, affiche l'un OU l'autre (display flex/none).

**Bandeau aide (.recap-aide) :** "Cliquez sur une question pour y revenir et compléter ou modifier votre réponse." — texte ardoise #4a5568, fond gris clair #f4f5f6, accent border-left 3px ardoise (pas d'icône, CSS pur, zéro dépendance externe).

**Pastilles de question (.recap-q) :** jaune = répondu (.repondue : #FAC775/#854F0B, même jaune que la sélection QCM), gris = à répondre (.vide : #eceff1/#90a4ae). Le jaune garde un sens unique sur les deux écrans ("il y a une réponse"). Anciennes couleurs (#bbdefb bleu / #fff9c4 jaune pâle) remplacées.

**Bouton Valider (.btn-valider) :** pilule gris ardoise #4a5568, courte et centrée (wrap .recap-valider-wrap), check ✓ CSS pur, "Valider mes réponses". Ancien style pleine largeur bleu #1a237e supprimé (commentaire inerte laissé ligne ~444). Migré onclick → data-action="valider-test".

**Migration data-action (CSP) :**
- Pastilles : onclick="allerQuestion(t,i)" → data-action="aller-question" data-theme/data-idx (rendu Jinja).
- Bouton valider : data-action="valider-test".
- Listener délégué sur #ecran-recap : route aller-question (parseInt theme/idx → allerQuestion) et valider-test (→ valider).

**Ergonomie fin de test (anti-redondance Q100) :**
- Avant : sur la dernière question, DEUX déclencheurs vers le récap (pilule centrale "Récap" + bouton Suivante devenu "Voir recap →"). Confus pour primo-arrivant.
- Maintenant : sur la dernière question, bouton Suivante = "Mes réponses →" (seul déclencheur), pilule centrale masquée. Sur les autres questions, pilule réapparaît si MODE_CORRECTION || recapDebloque.
- Vocabulaire harmonisé : "Récap" → "Mes réponses" partout (plus parlant que le jargon "récap"). Choix : "Mes réponses" plutôt que "Terminer"/"J'ai fini" car le bouton mène à la vérification, pas à la validation définitive (qui se fait sur Valider du récap).
- Pilotage du bouton récap unifié : suppression de l'ancienne ligne btnVR dans afficherQuestion() (qui contredisait le bloc navigation). Le bloc navigation (btnRecapMini) est désormais la SEULE source de vérité. recapDebloque préservé.

**Note dépendances :** tout le récap est en CSS pur (pas de Tabler ni police externe) — choix délibéré pour fiabilité en salle d'examen (connexion non garantie sur tablettes).

---

### ✅ Chantier terminé : écran 3 (consignes) refonte charte anthracite

**Périmètre :** #ecran-consignes dans templates/test_theorie.html. Premier écran basculé en charte anthracite NORYX (#383b40). Les écrans 1, 2 et le QCM/récap restent en bleu/ardoise pour l'instant — effet "îlot" anthracite assumé temporairement, le temps de basculer le reste (header en priorité ensuite).

**HTML (réécrit, était tout en inline) :**
- Classes CSS dédiées créées : .cons-duree-wrap, .cons-duree-label, .cons-timer, .cons-titre-box, .cons-titre-test, .cons-titre-sous, .cons-regles-label, .cons-item, .cons-ico, .cons-ico-num, .cons-ico-rouge, .cons-txt, .cons-btn
- Emojis remplacés par pictos CSS pur : chiffres dans pastilles (100, 5), symboles Unicode sobres (⏱ U+9201, ◎ U+9678, ✕ U+10005). Zéro emoji, zéro police externe (fiabilité salle).
- Les 5 consignes : 100 questions / 60 minutes / 5 thèmes 50% / note globale min / aucune aide extérieure.
- ✕ "aucune aide extérieure" en rouge NORYX #cc0000 (.cons-ico-rouge) — seule touche rouge, accent sur la consigne interdictive.
- Bouton "Commencer le test" : onclick="demarrerTest()" → data-action="demarrer-test" (CSP), pilule anthracite #383b40.

**Couleur :** anthracite #383b40 (valeur de charte adoucie depuis #2d2d2d, voir section Charte). Distinct de l'ardoise #4a5568 pour préserver la hiérarchie structure/secondaire.

**JS :** listener délégué sur #ecran-consignes route data-action="demarrer-test" → demarrerTest(). demarrerTest() inchangé (charge questions si besoin, cache consignes, affiche QCM, lance le chrono).

**Note à traiter plus tard :** le titre "Test théorique CACES® R.482" est codé EN DUR dans le HTML. À rendre dynamique (passer la famille depuis le serveur) si les tests portent sur d'autres familles (R.489, R.490…). Comportement inchangé dans ce chantier (déjà en dur avant).

---

### ✅ Chantier terminé : header commun + QCM en charte anthracite

**Header commun (.header, partagé par tous les écrans de test_theorie.html) :**
- Fond #1a237e → #383b40 (anthracite de charte). Le header étant commun, la bascule unifie le haut de TOUS les écrans d'un coup.
- Titre corrigé : "CACES® R.482 - Theorie" → "Théorie R.482" (accent ajouté, libellé court). Toujours codé EN DUR — à rendre dynamique (famille) plus tard, comme l'écran 3.
- Chrono #timer : couleur de repos #64b5f6 → #fff (blanc sur anthracite). Reset (changement de candidat, ligne ~1247) aussi passé #64b5f6 → #fff.
- Barre de progression (.progress-fill) : #64b5f6 → #fff. (.progress-bar-wrap rgba(255,255,255,0.2) inchangé, marche sur anthracite.)
- Emoji ⏱ du chrono CONSERVÉ (choix utilisateur) devant l'heure.

**Chrono — suppression des alert() bloquants :**
- Les 2 alert() de tickTimer() (à 600s "10 minutes" et 300s "5 minutes") SUPPRIMÉS. En plein test chronométré, une popup système bloque le candidat — la couleur du chrono suffit comme alerte.
- Transitions de couleur CONSERVÉES : #ff9800 (orange) à 600s, #f44336 (rouge) à 300s, #f44336 + valider(true) (soumission auto) à 0s. Mécanique du chrono intacte.
- 3 alert() restants AILLEURS (non touchés, à traiter avec écrans 1/2) : ligne ~1211 sélection candidat manquante (allerConfirmation), ~1309 identité non confirmée (allerConsignes), ~1322 erreur chargement questions (demarrerTest).

**QCM — bascule anthracite :**
- Bouton Suivante (.btn-suiv) : #1a237e → #383b40, hover #283593 → #2a2c30. Seule occurrence de bleu dans l'écran QCM (le reste déjà en ardoise/jaune depuis la refonte précédente).
- Nettoyage dette : règles CSS orphelines .recap-score-big et .recap-score-label (ancien en-tête récap, plus référencées depuis la refonte) SUPPRIMÉES.

**État charte anthracite (déploiement) :**
- ✅ FAIT : header commun, écran 3 (consignes), QCM, récap. Tout le parcours PENDANT le test est unifié en anthracite #383b40.
- RESTE : écrans 1 (sélection candidat) et 2 (identité) — lourds, tout en inline, 3 alert() + bouton "Lire à voix haute" bleu ; écran 6 (résultat, non diagnostiqué) ; modale de confirmation (1 bouton bleu ligne ~1552). 12 occurrences de #1a237e restantes, toutes hors parcours de test (écrans 1/2/6 + QR config + modale).
