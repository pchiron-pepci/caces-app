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
| `sessions.py` | `/api/sessions` | Gestion sessions CACES® + justificatif théorie + justificatif grille pratique (`POST`/`GET /{session_id}/pratique/justificatif/{epreuve_id}`) |
| `admin.py` | `/admin` | Catégories, habilitations, lieux |
| `auth.py` | `/auth` | Login JWT |
| `upload.py` | — | Import fichiers |
| `statistiques.py` | — | Stats/rapports |
| `cartes_caces.py` | `/api/cartes-caces` | Cartes CACES® (préparation, émission, annulation) + `GET /{id}/pdf` (WeasyPrint → PDF CR80 protégé pypdf) |
| `saisie_pratique.py` | `/api/sessions` | Évaluation pratique en ligne — 6 routes sous `/{jour_test_id}/{stagiaire_id}/{categorie}/` : `POST /ouvrir`, `POST /enregistrer`, `POST /calculer`, `POST /valider`, `POST /rouvrir`, `DELETE /supprimer` |
| *(main.py)* | `/verifier/{token}` | Page publique de vérification (token = UUID4 `token_verification`, fallback `numero_carte`) — pas de login requis |

---

## Décisions architecturales

### Soft delete vs hard delete
- **Testeurs** : soft delete (`actif = False`), appelé "archiver" — les données historiques doivent rester liées
- **Habilitations testeur** (`HabilitationTesteur`) : hard delete SQL (`db.delete()`) — pas d'historique nécessaire
- **SessionCandidat** : hard delete SQL (`db.delete()`) depuis 2026-06-22 — un candidat retiré (erreur de saisie, changement de session) ne laisse aucune trace ; purges manuelles avant `db.delete` : fichier R2 (`storage.delete_fichier`) + `ConsentementRGPD` (couple `session_id`+`stagiaire_id`)
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
| `/api/sessions/\d+/pratique/justificatif/\d+` | POST | middleware cookie + PIN formateur dans body — upload justificatif grille pratique (même whitelist _verifier_role que théorie) |

`rouvrir-terrain` n'est PAS whitelisté — réservé admin/utilisateur.

**Blocage complémentaire (2026-07-06, commit `d771013`) : écriture `/api/upload/*` interdite au terrain.** Toute méthode `!= GET` vers un chemin commençant par `/api/upload` (upload/suppression d'attestation prévention, visite médicale, évaluation, autorisation de conduite, carte testeur, `PATCH` date d'expiration…) est bloquée pour le rôle terrain — le `GET .../download` reste autorisé (lecture seule). Vérifié avant application qu'aucun fichier/template accessible au terrain (`session_detail.js`, `saisie_pratique.js`, `saisie_degrade.js`, `test_theorie.html`, `saisie_degrade.html`, `session_detail.html`) ne référence `/api/upload` — tous les uploads légitimes du terrain (dispense, justificatifs formation/théorie/pratique) passent par `/api/sessions/*`, un préfixe distinct et déjà géré par ses propres exceptions ci-dessus. Aucune régression attendue.

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
11. **Suppression candidat de la session** : vérifie d'abord qu'aucun `JourTestCandidat` n'existe pour cette session (sinon 400) ; **hard delete** `db.delete(sc)` + purge fichier R2 (`dispense_fichier_cle`) + purge `ConsentementRGPD` (couple `session_id`+`stagiaire_id`) ; PIN 1505 requis côté serveur via `DELETE /api/sessions/{id}/candidats/{sc_id}?pin=`
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
| `SessionCandidat` | `session_candidats` | Inscription d'un stagiaire à une session ; `stagiaire_id`, `theorie_dispensee` Boolean, `dispense_note` Text, `dispense_fichier_cle` VARCHAR(500) (clé R2, JAMAIS le binaire), `dispense_fichier_nom` VARCHAR(255), `dispense_fichier_type` VARCHAR(100), `dispense_date` DATE (date obtention CACES externe justifiant la dispense — futur calcul validité 12 mois), `actif` Boolean (legacy — hard delete depuis 2026-06-22) |
| `SessionEpreuve` | `session_epreuves` | résultat pratique par catégorie ; `options_obtenues` VARCHAR(200) CSV ; `bloque` Boolean défaut False — positionné lors d'une annulation CACES® avec motif "Non conforme"/"CACES® annulé" + case cochée, empêche la re-création auto du CacesObtenu ; suppression hard delete via `DELETE /api/sessions/{session_id}/epreuves/{epreuve_id}?pin=1505` ; `justificatif_cle` VARCHAR(500) nullable (clé R2) + `justificatif_nom` VARCHAR(255) nullable — grille d'évaluation pratique par candidat/catégorie, 1 fichier (remplacement à chaque upload), multi-format (PDF/Excel/Word/images, 10 Mo max), stocké R2 (préfixe `justificatifs/pratique`), content_type déduit de l'extension, lecture inline pour PDF/images sinon attachment ; ajoutés par migration startup `ALTER TABLE session_epreuves ADD COLUMN IF NOT EXISTS` |
| `ResultatTheorie` | `resultats_theorie` | UNIQUE `(jour_test_id, stagiaire_id)` ; `mode` VARCHAR(12) NOT NULL DEFAULT 'numerique' ('numerique'/'degrade') ; `bloque` Boolean défaut False — positionné comme SE, empêche la recherche de théorie dans `calculer_et_synchroniser` ; reprise par écrasement si mode='numerique', 409 si mode='degrade' ; `justificatif_pdf` Text nullable (base64) ; `justificatif_nom` VARCHAR(255) nullable — ajoutés par migration startup + `migrate_justificatif_theorie.py` ; update notes ne touche JAMAIS justificatif (opérations indépendantes) |
| `HabilitationTesteur` | `habilitations_testeurs` | hard delete ; `option_pe`/`option_tel` legacy — remplacés par `HabilitationOption` |
| `OptionCategorie` | `option_categorie` | table de référence des options disponibles par famille/catégorie ; codes : PE=Porte-engins, TEL=Télécommande, CC=Conduite cabine, TR=Translation sur rails, CEC=Circulation en charge ; `incluse` Boolean (défaut False) : option obligatoire incluse dans l'UT de la catégorie (pas de +0.5 UT) vs option facultative ; peuplé par `init_options.py` |
| `HabilitationOption` | `habilitation_option` | options actives par habilitation (habilitation_id FK, code_option) ; modifiable avec PIN 1505 via `PUT /admin/habilitation/{id}/options` |
| `Testeur` | `testeurs` | soft delete (`actif`) ; `etat` : actif/suspendu/sorti — modifiable avec PIN 1505 via `PUT /api/testeurs/{id}/etat`, défaut actif à la création ; docs PDF en base64 : `attestation_prevention_pdf/nom/date`, `visite_medicale_pdf/nom/visite_medicale_date`, `evaluation_pdf/nom/evaluation_date`, `autorisation_conduite_pdf/nom`, `carte_pdf/carte_nom_fichier` (legacy) ; `numero_nda` VARCHAR(50) nullable + `rcp_cle/rcp_nom/rcp_date` (RCP = assurance Responsabilité Civile Professionnelle du testeur, fichier R2) — ajoutés 2026-07-06, migration `migrate_testeur_nda_rcp.py` **à exécuter sur prod** ; champs UI dans la modale (`templates/testeurs.html`, commit `08eae1a`) + JS complet (`static/js/testeurs.js`, commit `8956523` : lecture/remplissage `editer()`, handlers upload/suppr RCP calqués sur évaluation, `numero_nda` dans le payload de sauvegarde, reset à l'ouverture) + `numero_nda` déclaré dans `TesteurCreate`/`TesteurResponse` (commit `0687476`, sans quoi `data.model_dump()` l'aurait silencieusement ignoré à chaque sauvegarde) ; routes backend RCP `POST/GET download/DELETE /api/upload/rcp/{id}` créées (commit `e1f3adb`, `app/routers/upload.py`) — **volontairement SANS PIN** (document interne, même logique que `PATCH .../date-expiration` sur `carte_testeur`) ; JS RCP mis à jour en cohérence (retrait du `ouvrirPinAction`, fetch direct + `location.reload()`) — **fonctionnalité NDA/RCP complète de bout en bout** (modèle, migration, UI modale, JS, routes) ; affichage repris aussi dans la carte testeur dépliée (commit `9e1fd02`) : N° NDA sur une ligne au-dessus des Habilitations CACES®, RCP sous Dernière évaluation avec pastille couleur (seuils 90/180 jours restants → rouge/orange/vert, même logique que l'expiration des cartes CACES® testeur) |
| `CarteTesteur` | `carte_testeur` | multi-cartes par testeur, soft delete (`actif`) ; champs : `famille`, `nom_fichier`, `cle` VARCHAR(500) R2, `date_upload` — migration R2 Lot 2 (2026-06-30) |
| `ConfigOrganisme` | `config_organisme` | singleton (1 ligne) ; `nom_organisme`, `logo_base64` (image base64), `logo_nom` ; `adresse` Text, `siret` VARCHAR(20), `email` VARCHAR(200), `telephone` VARCHAR(50) ; `signataire_nom`, `signataire_prenom`, `signataire_qualite` VARCHAR(100) ; `signature_base64` Text, `signature_nom` VARCHAR(200) (image signature upload) ; `url_verification_caces` VARCHAR(500) (optionnel, si non renseigné → défaut `https://caces-app.onrender.com/verifier/`) — utilisé par `_build_verify_url()` pour construire `verify_url = base + token_verification` (fallback `numero_carte`) passé dans `config.verify_url` au frontend JS (QR code recto) ; `audit_interne_date`, `audit_externe_date`, `revue_direction_date` (Date nullable) ; `pin_formateur` VARCHAR(20) défaut "1234" — PIN saisi par le formateur pour débloquer "Ce n'est pas moi" dans test_theorie.html ET pour clôturer terrain, vérifié via `POST /admin/config/verifier-pin-formateur` ou dans le handler `cloturer-terrain`, modifiable dans Administration → Paramètres avec PIN admin 1505 ; `prochain_numero_caces` Integer défaut 1 — prochain numéro attribué lors de la validation d'un CACES® (affiché sur 4 chiffres : 0001, 0002…), incrémenté auto à chaque `POST /api/caces-obtenus/valider/{id}`, configurable dans Administration → Paramètres ; routes : `POST /admin/config-organisme/signature` + `DELETE /admin/config-organisme/signature` (upload/suppression image signature, PIN 1505) ; affiché via Jinja2 globals `nom_organisme()`, `logo_organisme()`, `get_config_organisme()` |
| `Stagiaire` | `stagiaires` | soft delete (`actif`) ; `photo_base64` Text — photo stockée en base64 PostgreSQL (upload via `POST /stagiaires/photo/{id}`, prioritaire sur `photo`) ; `photo` String(500) — chemin fichier legacy conservé pour rétro-compatibilité |
| `CacesObtenu` | `caces_obtenus` | statut : `a_valider`/`valide`/`annule` ; `numero_ordre` (Integer unique, attribué à la validation) ; `motif_annulation` Text nullable ; `organisme_externe` VARCHAR(200) nullable — OF émetteur si CACES externe (marque le CACES comme externe, Carte 1/3 2026-07-02) ; `justificatif_cle` VARCHAR(500) nullable — clé R2 du fichier preuve (CACES externe) ; `justificatif_nom` VARCHAR(255) nullable — nom original du fichier preuve ; UNIQUE(stagiaire_id, session_id, categorie) ; routes : GET `/api/caces-obtenus/a-valider` (sync + liste), GET `/api/caces-obtenus/valides` (trié : validé en haut, annulé en bas), POST `/api/caces-obtenus/valider/{id}?pin=` (attribue numéro incrémental, bouton "📜 Émettre le CACES®"), POST `/api/caces-obtenus/annuler/{id}?pin=` body `{motif, bloquer_pratique: bool, bloquer_theorie: bool}` (statut→`annule`, si `bloquer_pratique` → `SessionEpreuve.bloque=True`, si `bloquer_theorie` → `ResultatTheorie.bloque=True` pour tous les RT obtenue=True du stagiaire dans la session, motif "Erreur administrative" : ne bloque rien + recréation auto au prochain /a-valider), PATCH `/api/caces-obtenus/{id}/motif?pin=` body `{motif}` (mise à jour motif_annulation) ; au prochain appel `/a-valider` les records `annule` repassent en `a_valider` seulement si SE/RT non bloqués ; modal annulation : select obligatoire (Erreur administrative / Non conforme / CACES® annulé / Autre) + cases à cocher visibles pour Non conforme et CACES® annulé uniquement ; service `app/services/caces_obtenus.py` → `calculer_et_synchroniser(db)` (filtre `SE.bloque != True` et `RT.bloque != True`) |
| `CarteCaces` | `carte_caces` | `stagiaire_id` FK, `famille`, `numero_carte` (unique, format `PEPCI-{YY}-{NNNNN}`, incrément annuel remis à zéro), `token_verification` (String 36, UUID4 unique, généré à l'émission, utilisé dans l'URL /verifier/{token}), `date_generation`, `statut` (`en_preparation` legacy/`emise`/`remplacee`/`annulee`), `motif_annulation`, `caces_json` Text (snapshot JSON des CacesObtenu au moment de l'émission : liste [{categorie, categorie_libelle, numero_ordre, options_obtenues, date_obtention, date_echeance, testeur_nom}]) — **une carte émise est figée définitivement** : le snapshot `caces_json` stocké à l'émission est la source de vérité ; les CACES® validés/annulés après l'émission n'affectent pas cette carte ; pour une carte à jour → générer une nouvelle carte (l'ancienne passe en `remplacee`) ; **pas de blocage de l'annulation CACES® par une carte émise** — une carte est une photo statique, l'organisme est responsable de réémettre si nécessaire ; page `/cartes-caces` — workflow : select stagiaire → familles filtrées → tableau CACES® validés → bouton Générer et imprimer (PIN) → fenêtre impression CR80 (≤4 cats, 85.6×54mm) ou A5 landscape (>4 cats) — à l'impression la carte passe en `emise`, l'ancienne `emise` passe en `remplacee` ; section Cartes émises : ▶/▼ déplie snapshot, boutons 🖨️ réimprimer + ❌ annuler uniquement sur `emise` ; badges : ✅ Émise / 📷 Remplacée / ❌ Annulée ; routes : `GET /stagiaires`, `GET /familles/{stag_id}`, `GET /caces-valides/{stag_id}/{famille}`, `POST /emettre/{stag_id}/{famille}?pin=`, `GET /{id}/caces` (retourne snapshot ou fallback legacy), `GET /reimprimer/{id}`, `GET /emises`, `POST /annuler/{id}?pin=` body {motif}, `GET /{id}/pdf` (PDF CR80 recto/verso protégé — WeasyPrint (rendu HTML CR80 identique au template JS) + pypdf (permissions_flag=2052, impression seule), téléchargement direct) ; **page publique** : `GET /verifier/{token}` (main.py, pas de login) — token = `token_verification` UUID4 (fallback `numero_carte` pour rétro-compatibilité) ; **anonymisation RGPD obligatoire côté serveur** : la route ne passe JAMAIS `s.prenom` ni `s.date_naissance` bruts au template — uniquement `stagiaire_prenom = prenom[0] + "."` et `stagiaire_ddn_annee = date_naissance.year` — template `verifier.html` standalone (pas de base.html) — affiche titulaire + tableau CACES® si `emise`, bandeau avertissement si `annulee`/`remplacee`, message d'erreur si introuvable |
| `DocumentOfficiel` | `document_officiel` | singleton par type (`certificat_organisme`, `attestation_assurance`, `procedure_interne`) ; champs : `cle` VARCHAR(500) R2, `nom_fichier`, `date_validite`, `numero_certificat` (certificat_organisme uniquement) — migration R2 Lot 2 (2026-06-30) ; Jinja2 globals `numero_certificat()`, `date_validite_certificat()` (retourne date formatée dd/mm/YYYY ou "") |
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
| `migrate_carte_testeur_expiration.py` | `ALTER TABLE carte_testeur ADD COLUMN IF NOT EXISTS date_expiration DATE` (2026-07-06, commit `f8c520a`) | **à exécuter sur prod (Render Shell)** — voir note ci-dessous |
| `migrate_testeur_nda_rcp.py` | `ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS numero_nda VARCHAR(50)` + `rcp_cle VARCHAR(500)` + `rcp_nom VARCHAR(200)` + `rcp_date DATE` (2026-07-06, commit `6644587`) | **à exécuter sur prod (Render Shell)** — même incohérence de pattern, voir note ci-dessous |

**⚠️ Incohérence de pattern à noter (`carte_testeur.date_expiration`, 2026-07-06) :** cette table a déjà une migration `cle VARCHAR(500)` intégrée dans `_MIGRATIONS` (`app/main.py`), qui s'exécute automatiquement à chaque démarrage de l'app — pattern majoritaire pour les colonnes récentes du projet. `date_expiration` a été demandée comme script **autonome** à lancer manuellement, rompant avec cette convention pour cette même table. Conséquence concrète : contrairement à `cle`, cette nouvelle colonne **ne sera pas créée automatiquement en prod** au prochain déploiement — `python migrate_carte_testeur_expiration.py` doit être lancé explicitement sur Render Shell, sans quoi tout code lisant/écrivant `CarteTesteur.date_expiration` échouera en base (colonne inexistante).

**⚠️ Même incohérence, 2e occurrence (`testeurs.numero_nda` + `rcp_*`, 2026-07-06) :** la table `testeurs` a **la totalité** de ses colonnes ajoutées via `_MIGRATIONS` dans `app/main.py` (carte, attestation prévention, visite médicale, évaluation, autorisation de conduite, état, utilisateur_id — 14 lignes `ALTER TABLE testeurs` déjà présentes, toutes auto-exécutées au démarrage). `numero_nda`/`rcp_cle`/`rcp_nom`/`rcp_date` ont de nouveau été demandés comme script autonome, rompant la convention pour cette table déjà 100% alignée sur le pattern startup. **Ces 4 colonnes ne seront pas créées automatiquement en prod** — `python migrate_testeur_nda_rcp.py` doit être lancé explicitement sur Render Shell avant toute utilisation de `Testeur.numero_nda`/`Testeur.rcp_*`, sans quoi toute lecture/écriture échouera en base (colonnes inexistantes).

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
- **Variables d'environnement** : `DATABASE_URL`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_CLOUD_NAME`, `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`

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
| Haute | Suppression habilitation testeur — hard delete avec PIN (modal testeurs) | ❌ abandonné (voir note ci-dessous) |
| Haute | Cartes CACES® PDF (format CR80, WeasyPrint) | ✅ fait |
| Haute | Annuler/supprimer résultat épreuve pratique (avec PIN) | ✅ fait |
| Haute | CACES® Obtenus — calcul auto + validation + page /caces-obtenus | ✅ fait |
| Haute | Jours de formation (nouveau type, UT personnalisés) | à faire |
| Haute | Journal non-conformités/réclamations — page /non-conformites + modèle NonConformite + carte dashboard | ✅ fait |
| Haute | Historique sessions par stagiaire — bouton ▶ dans page stagiaires, lazy load GET /stagiaires/{id}/historique | ✅ fait |
| Haute | Options CACES® (PE, TEL, CC, TR, CEC) sur épreuves pratiques — planification + résultats | ✅ fait |
| Haute | Évaluation pratique en ligne (grille INRS sur tablette) — modèles, moteur, router, UI mobile | ✅ fait (init grille prod à exécuter) |
| Haute | Cartographie habilitations dates (entrée/sortie) — Categorie.date_sortie + routes PIN + frontend modal | ✅ fait |
| Haute | CACES externe (dispense tracée) — Carte 1/3 : modèle + migration (organisme_externe / justificatif_cle / justificatif_nom sur CacesObtenu) | ✅ fait (commit 6a1bd3d, 2026-07-02) |
| Haute | CACES externe — Carte 2/3 : routes backend (POST création multipart + exploitabilité, GET justificatif, DELETE) | ✅ fait (commit 09fbea8, 2026-07-02) |
| Haute | CACES externe — Carte 3/3 : UI (affichage, badge "Externe", justificatif cliquable) | ✅ fait (commit 300db66, 2026-07-02) |
| Haute | detecter_base_theorique — distinguer CACES externe (origine, organisme, lien adapté) | ✅ fait (2026-07-02) |
| Haute | Simplification modale candidat Carte 2/3 (JS) — nettoyer refs champs supprimés (origine, date, écheance, justificatif) | ✅ fait (2026-07-02) |
| Haute | Simplification modale candidat Carte 2b/3 (JS) — ouvrirAjout/editer/sauvegarder + neutraliser _verifierQ2/_verifierEcheance | ✅ fait (2026-07-02) |
| Moyenne | Externaliser JS inline de admin.html (contrainte CSP) | à faire |
| Moyenne | Grilles R486, R489 (scripts init à créer) | à faire |
| Moyenne | Multi-tenant (subdomain routing, database-per-tenant) | à faire |

### Décision architecturale : multi-tenant Cloudinary
**Option A retenue — un compte Cloudinary distinct par tenant.**
- Credentials `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` stockés dans les variables d'environnement de chaque instance Render, ou dans une table `tenant_config` en base.
- Au provisioning d'un nouveau tenant : créer un compte Cloudinary gratuit et renseigner les 3 credentials.

---

## Doctrine de stockage : R2 vs base64

Regle de decision pour tout nouveau champ fichier :

**Cloudflare R2** (colonne `_cle VARCHAR(500)`, helper `app/services/storage.py`) — pour les gros fichiers qui se multiplient et se telechargent via une route dediee :
- PDF testeurs : carte, attestation prevention, visite medicale, evaluation, autorisation (Lot 1)
- Cartes CACES multi-familles `CarteTesteur.cle` (Lot 2)
- Documents officiels `DocumentOfficiel.cle` : certificat, assurance, procedure
- Justificatifs pratique/theorie, dispenses (deja `_cle` anterieurement)

Pattern R2 : upload = `storage.upload_fichier` + purge ancienne cle ; download = `RedirectResponse(storage.generer_url_presignee(...))` ; delete = `storage.delete_fichier`.

**base64 en base** (colonne `_base64 TEXT`) — pour les petites images embarquees inline dans les pages Jinja et les PDF WeasyPrint, ou un acces local immediat prime sur le stockage distant :
- Logos + signature organisme (`config_organisme`) : injectes en `data:` URI dans 7 generateurs PDF
- Photos stagiaires (`stagiaire.photo_base64`) : ~60 Ko/photo, affichage inline massif (4 templates + 4 points PDF), gelees en base64 dans le snapshot `caces_json` des cartes emises
- Signatures de production : neutralite, consentement RGPD, saisie pratique

Critere : **gros fichier a route de telechargement -> R2** ; **petite image au plus pres du rendu (page ou PDF) -> base64**.

Note photos stagiaires : ~80 Mo a 1000 stagiaires, gerable par PostgreSQL. Si la charge devient un sujet, optimiser via `defer(Stagiaire.photo_base64)` sur les requetes qui n'affichent pas la photo, sans changer le stockage.

---

| Haute | Photos stagiaires — migration filesystem éphémère → base64 PostgreSQL (`photo_base64` Text) | ✅ fait |
| Haute | Token vérification UUID (`token_verification`) + anonymisation RGPD sur `/verifier/{token}` | ✅ fait |
| Haute | Options incluse/facultative (`OptionCategorie.incluse`) + calcul UT filtré | ✅ fait |
| Basse | Responsive mobile (CSS media queries) | à faire |
| Basse | UT options facultatives = +0.5 UT (incluses déjà dans UT catégorie) | ✅ fait |
| Basse | Supprimer `date_habilitation` et `date_expiration_habilitation` du modèle `Testeur` (doublons avec `HabilitationTesteur`) | à faire |
| Haute | Justificatif formation (table générique, multi-fichiers, indicateur, menu) | ✅ fait |
| Haute | Onglet Documents de session (document_session + libelle + puces + responsive) | ✅ fait |
| Haute | Stockage R2 + storage.py (+ images jpg/png/heic) | ✅ fait |
| Haute | Suppression justificatifs par rôle (uploade_par_role) — cadré, 5 étapes | ✅ fait |
| Haute | Réduction images côté client avant upload (1600px/JPEG 80%) | ✅ fait |
| Haute | Détection dispense interne/externe (modale candidat) | ✅ fait |
| Haute | Brancher dispense externe au moteur caces_obtenus.py | ✅ fait |
| Haute | Affichage origine dispense dans CACES obtenus (ligne + badge + justif cliquable) | ✅ fait |
| Haute | Stabilisation parcours dispense en ajout (3 fixes : reset, externe forcé, écheance prématurée) | ✅ fait |
| Haute | Module REPRISE D'HISTORIQUE (H1-H5 : CacesObtenu repris, théories/pratiques orphelines) | ✅ H1-H5 tous faits (suppression incluse — CHANTIER 5) |
| Moyenne | Convergence justificatif dispense → table Justificatif (fichier seulement) | ÉCARTÉ (non-convergence assumée) |
| Moyenne | Corrections couleur pastille FORM. ardoise + footer Actions en ligne | à faire |
| Haute | Migration justificatif théorie base64 → R2 | ✅ fait |
| Haute | Migration R2 Lot 2 : CarteTesteur.contenu_pdf → cle (R2) | ✅ fait (2026-06-30) |
| Haute | Migration R2 Lot 2 : DocumentOfficiel.contenu_pdf → cle (R2) | ✅ fait (2026-06-30) |
| Haute | Justificatif grille d'évaluation pratique par candidat/catégorie (R2 multi-format, badge 📎/⚠ sur la ligne sous l'option, PIN formateur, rappel fixe dans la modale) | ✅ fait |
| Haute | Export ZIP enrichi (formation + documents + dispense) | ✅ fait |
| Haute | Moteur CACES — écart A corrigé (théorie la plus récente, date desc) | ✅ fait |
| Haute | Moteur CACES — écart B (fenêtre 12 mois sens unique) | ✅ fait |
| Haute | Moteur CACES — écart C (choix CACES initial extension) | à examiner |
| Haute | Détection dispense — étape 0 : persister post_cloture sur CacesObtenu | ✅ fait |
| Haute | Détection dispense — étape A : proposition vérifiable dans modale candidat | ✅ fait |
| Moyenne | Migrer justificatif théorie (ResultatTheorie.justificatif_pdf base64) vers R2 | ✅ fait |
| Note | Notice utilisateur Justificatifs/Documents (.docx) générée pour PEPCI | fait (hors repo) |

### Dashboard — route GET /
Variables de contexte passées au template `dashboard.html` :
- `stats` : dict (stagiaires, cartes, sessions, expirations)
- `testeurs` : testeurs actifs avec habilitations chargées
- `docs` : dict type→DocumentOfficiel
- `today` : date du jour
- `referents` : Utilisateur avec role_referent renseigné et actif
- `nc_ouvertes` : NonConformite statut in (ouvert, en_cours) desc date
- `sessions_actives` : Session statut in (planifiee, en_cours) order by date_theorie/date_pratique_debut
- `alertes_testeurs` : liste de `{"testeur": Testeur, "alertes": [{"label": str, "couleur": "rouge"|"orange"}]}` — attestation prévention (absente→rouge, >4ans→orange), visite médicale (absente→rouge, >2ans→orange), date_prochain_controle dépassée→rouge, carte(s) CACES® testeur avec `date_expiration` renseignée (2026-07-06, commit `bf40c27`) : échéance <90j→rouge, <180j→orange (une entrée par carte concernée, libellé `"Carte {famille} expire le JJ/MM/AAAA"`), RCP testeur (2026-07-06, commits `e785cb9` puis `f30a0a1`) : `rcp_cle` absent (aucun fichier joint) → **"RCP manquante"** rouge, sinon `rcp_date` dépassée→rouge, <60j→orange (seuils différents des cartes CACES® — 2 mois au lieu de 3/6 mois — décision assumée, RCP jugée plus urgente à renouveler) ; contrairement aux autres alertes de ce bloc (attestation/visite), l'ABSENCE de fichier RCP est désormais elle-même une alerte, pas seulement sa date
- `caces_a_valider` : liste de dicts `{id, stagiaire_nom, stagiaire_prenom, famille, categorie}` — CacesObtenu statut=a_valider
- `user_role` (2026-07-06, commit `57964aa`) : rôle de l'utilisateur courant (`_u_dash.role if _u_dash else None`), utilisé par le template pour filtrer l'affichage pour le rôle terrain

Carte **⚡ À traiter** (pleine largeur, grid-column 1/-1) regroupe en sections séparées par trait grisé : Sessions non clôturées, CACES® à valider, Non-conformités ouvertes, Alertes testeurs, Candidats sans photo. Chaque section affiche le compteur et "✅ Aucun" si vide. Remplace les anciennes cartes séparées "Sessions non clôturées", "Non-conformités ouvertes" et "Alertes".

**Dashboard accessible au terrain en lecture (2026-07-06, commits `57964aa` + `9f53c0e`) :** la redirection `/` → `/sessions` pour le rôle terrain a été retirée de `_verifier_role` (`app/main.py`), et l'entrée "Dashboard" est réapparue dans la sidebar (`/` retiré de `cachePrefixes` dans `templates/base.html`). **Point de vigilance découvert et corrigé avant application** : le script fourni supposait à tort que `dashboard.html` filtrait déjà son contenu par rôle ("blocs filtrés dans le template") — au moment de l'ouverture de la route, `user_role` n'apparaissait NULLE PART dans ce template ; ouvrir la route sans filtrage aurait exposé tout le dashboard back-office (Organisation, Testeurs opérationnels, bloc "⚡ À traiter" avec CACES à valider/NC ouvertes/alertes testeurs...) au rôle terrain. Signalé à l'utilisateur avant d'exécuter, qui a demandé le filtrage. 3 blocs masqués au terrain via `{% if user_role != 'terrain' %}` : carte "⚡ À traiter" (entière), carte "Testeurs opérationnels" (entière), sous-bloc "Prochains audits" dans la carte "Organisation" (audits interne/externe, revue de direction — infos de pilotage qualité, pas pertinentes terrain). **Restent visibles au terrain** : Cartographie, le reste d'Organisation (référents), Documents, Statistiques (placeholder).

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

### ❌ Chantier abandonné : suppression habilitation depuis la modal testeurs (2026-07-06)

**Objectif initial (jamais complété) :** ajouter un bouton 🗑️ dans la modal de modification d'un testeur existant pour supprimer définitivement une habilitation (hard delete SQL + PIN 1505). Une version partielle avait été codée dans `static/js/testeurs.js` (`supprimerHab()` + dispatcher `supprimer-hab`, section `#section-habs-modal` dans `templates/testeurs.html`).

**Décision inverse prise (commit `088b41d`) :** plutôt que de terminer ce chantier, la modale testeurs passe les habilitations en **lecture seule** — une ligne par famille (ex. "R.482 : A, B, C, F"), sans aucun bouton d'action, avec une mention explicite "(gestion dans Administration › Habilitations testeurs)". La gestion des habilitations (activer/désactiver/supprimer) est **entièrement centralisée dans Administration → Habilitations testeurs**, qui dispose déjà d'un mécanisme complet et fonctionnel (`admin.html` : `desactiverHabTesteur()`/`supprimerHabTesteur()`, indépendant de tout ce qui précède) — la modal testeurs n'a donc jamais eu besoin de sa propre suppression.

**Code mort résiduel, non nettoyé (à faire si besoin un jour) :** `static/js/testeurs.js` conserve `supprimerHab()` (fonction, ~ligne 408) et le dispatcher `if (btn.dataset.action === 'supprimer-hab')` (~ligne 171) — plus aucun bouton dans le DOM ne déclenche ce chemin depuis le retrait du 🗑️ de cette modale. Inoffensif (jamais atteint), mais à supprimer par cohérence lors d'un futur ménage de ce fichier.

**Fichiers concernés par le changement final :** `templates/testeurs.html` (attributs `data-hab-famille`/`data-hab-categorie` séparés + mention d'aide sous le titre), `static/js/testeurs.js` (rendu regroupé par famille, catégories triées et dédupliquées, sans bouton).

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

### ✅ Chantier terminé : migration justificatif théorie base64 → R2 (2026-06-23)

**Contexte :** `ResultatTheorie.justificatif_pdf` était le DERNIER vestige de stockage binaire en base (Text base64), d'avant R2. Migré vers R2. Version PROPRE (base de dev vidée bientôt) : pas de cohabitation, pas de script de migration des anciens, suppression franche du base64.

**Modèle `ResultatTheorie` (`jour_test.py`) :** `justificatif_pdf` (Text base64) REMPLACÉ par `justificatif_cle` (String 500, clé R2). `justificatif_nom` conservé.
**Migration startup (`main.py`) :** `ADD COLUMN justificatif_cle VARCHAR(500)` + `DROP COLUMN IF EXISTS justificatif_pdf`. Pas de CREATE TABLE séparé (géré par `Base.metadata.create_all()`).
**Route POST `upload_justificatif_theorie` :** front INCHANGÉ (JSON + `fichier_base64` + PIN formateur). Le serveur décode le base64 reçu → `storage.upload_fichier(contenu, cle="justificatifs/theorie/...", "application/pdf")` → stocke `justificatif_cle`. Purge ancien fichier R2 si remplacement.
**Route GET `get_justificatif_theorie` :** `storage.get_fichier(rt.justificatif_cle)` → StreamingResponse (au lieu de `base64.b64decode`).
**Export ZIP :** lit depuis R2 (`storage.get_fichier(rt.justificatif_cle)`).
**NON TOUCHÉ :** `NonConformite.justificatif_pdf` (homonyme, table différente, base64 conservé — autre chantier).
**Résultat :** plus AUCUN justificatif de session en base64 (dispense, formation, documents, théorie = tous R2). Vestiges base64 restants (non-conformités, docs testeurs, signature config…) = ménage séparé pour plus tard.

### ✅ Chantier terminé : enrichissement export ZIP (formation + documents + dispense) (2026-06-23)

**Contexte :** l'export ZIP datait d'avant la table Justificatif et l'onglet Documents — il ne contenait ni les justificatifs de formation, ni les documents de session, ni la dispense. Complété.

**3 nouvelles boucles dans `generer_zip_session` (`export_zip_session.py`), même pattern que l'existant (try/except par pièce, `storage.get_fichier`, `zf.writestr`) :**
- `formation/{candidat}/{fichier}` : table Justificatif `type='formation'`, multi-fichiers, par candidat (helper `_sc_to_stag` pour résoudre `session_candidat_id` → `stagiaire_id`)
- `documents/{libelle_fichier}` : table Justificatif `type='document_session'`, niveau session (préfixe = libellé sanitizé)
- `dispense/{candidat}.ext` : colonnes plates `SessionCandidat.dispense_fichier_cle` (mono-fichier — la dispense N'EST PAS dans la table Justificatif, décision de non-convergence)

**Imports ajoutés :** `Justificatif`, `SessionCandidat`.
**Batch-load stagiaires élargi :** inclut les `stag_ids` des `SessionCandidat` (sinon un candidat n'ayant QUE formation/dispense, sans RT/consentement, sortait mal nommé).

**Structure ZIP finale :** `corrige.pdf`, `recap_resultats.pdf`, `justificatifs/` (théorie dégradé), `tests_numeriques/`, `consentements/`, `neutralite/`, `formation/`, `documents/`, `dispense/`.

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

### ✅ Chantier terminé : écran 1 (sélection candidat) — fixes logique QR + restyle anthracite + header centré

**Deux corrections de LOGIQUE (comportement métier) :**

1. QR conditionné aux DEUX selects : avant, le QR s'affichait dès la sélection du candidat, sans testeur. Le select testeur n'avait aucun handler 'change'. Refonte : fonction evaluerQR() centralise l'affichage avec 4 cas — (0) pas de candidat → QR masqué ; (1) candidat déjà un résultat → QR masqué + message "déjà passé / saisie manuelle" ; (2) candidat OK mais PAS de testeur → QR masqué + message "⚠️ Sélectionnez aussi le testeur" ; (3) candidat ET testeur → génère + affiche le QR. evaluerQR() appelée par : change select-candidat, change select-testeur (nouveau listener), et fin du .then() de pré-sélection testeur. Le select testeur peut être vide (erreur réseau, ou plusieurs habilités sans testeur du jour).

2. Fix affichage #msg-bloque-select : div avec fond orange + display:none par défaut. evaluerQR() ne pilotait que textContent, jamais display → fond orange restait collé après sélection du testeur. Corrigé : display='' quand message posé (cas 1, 2), display='none' quand effacé (cas 0, 3).

Détails : id conteneur QR = qr-box (alignement fait, pas qr-container). data-a-resultat → dataset.aResultat. URL QR = origin + '/test/theorie/' + JOUR_ID + '/' + val + '/start'. colorDark QR #1a237e → #383b40.

**Restyle anthracite (classes .sel1-*) :**
- Tout l'inline de l'écran 1 → 13 classes CSS .sel1-* (sel1-header, sel1-titre, sel1-sous, sel1-select-wrap, sel1-select, sel1-select-fleche, sel1-grille-info/badge/texte, sel1-msg-chargement, sel1-qr/-ico/-texte/-box, sel1-msg-erreur, sel1-msg-warning).
- En-tête écran 1 : titre "Sélection du candidat" + sous-titre "Test théorique CACES® R.482" (EN DUR). LOGO RETIRÉ de l'en-tête écran 1 (était redondant — déjà présent dans le header commun). La classe .sel1-logo existe encore mais n'est plus utilisée (inerte).
- Selects natifs HABILLÉS (pas custom) : bordure #d0d4d8, appearance:none + flèche custom ▼. Choix : natifs habillés = simple + fiable mobile.
- Badge grille : .sel1-grille-info a flex-wrap:wrap (sur mobile, le badge "Phase 2 — Tirage par thème" + "100 questions · VRAI ou FAUX · 60 minutes" s'empilent au lieu de déborder).
- Section QR : box-shadow bleu + texte #1a237e + emoji 📱 → habillage charte (picto CSS, texte ardoise). #qr-section garde style="display:none;" inline (piloté par evaluerQR).
- Messages : erreur grille (rouge charte), warning tous_notes + msg-bloque-select (ambre charte). Emojis → picto Unicode. display:none inline conservé sur les 2 messages pilotés JS.
- Bouton "Préparer le test" : onclick="allerConfirmation()" → data-action="preparer-test" + listener délégué sur #ecran-selection.

**Header commun — centrage du titre :**
- Le titre "THÉORIE R.482" était décalé (flex justify-content:space-between → titre centré dans l'espace restant après le logo, pas au centre de la page).
- Corrigé : .header-row1 passé de flex à grid (grid-template-columns: 1fr auto 1fr). Titre en grid-column:2 + text-align:center → centre absolu de la page. Bloc chrono (wrapper timer+candidat) reçoit justify-self:end. Logo en colonne 1 (gauche). Le titre est désormais centré quelle que soit la largeur du logo, sur tous les écrans.

**IDs préservés (JS) :** select-candidat (+ data-nom/prenom/naissance/a-resultat/mode), select-testeur, card-testeur-select, msg-testeur-chargement, qr-section, qr-box, msg-erreur-grille, msg-bloque-select.

**État charte anthracite :** ✅ header (+ titre centré), écran 3 (consignes), QCM, récap, écran 1 (sélection). RESTE : écran 2 (identité — 3 alert(), bouton "Lire à voix haute" bleu, zone PIN formateur), écran 6 (résultat), modale de confirmation (~ligne 1552).

**Leçon méthode :** tester sur mobile au fur et à mesure (pas à la fin) — l'écran 1 a demandé plusieurs allers-retours (logo dédoublé, badge débordant, titre décalé) qui auraient été vus plus tôt avec une vérif mobile immédiate.

### ✅ Chantier terminé : écran 2 (identité candidat) — restyle anthracite + date FR + lecture ralentie

**Restyle anthracite (classes .sel2-*) :** tout l'inline de l'écran 2 → 14 classes CSS .sel2-* (sel2-tete, sel2-emoji, sel2-question, identite-nom, identite-info, sel2-voix-wrap, sel2-voix-btn, checkbox-confirm + input + span, sel2-pin + titre/texte/label/input/error/actions).
- Emojis CONSERVÉS (choix utilisateur — plus convivial, public faible littératie) : 👤 🔊 🔒 ❌. Seules couleurs/disposition en anthracite.
- Carte candidat : 👤 + "Êtes-vous bien :" + nom en gros anthracite (identite-nom) + date (identite-info) + bouton 🔊 pilule grise + checkbox engagement encadré #f9fafb (accent-color anthracite).
- Zone PIN formateur (#zone-pas-moi) : orange inline → ambre charte #FFF4E0/#F0C775. Garde display:none inline (piloté JS). #pin-formateur-error garde display:none inline.

**Migration 5 onclick → data-action (listener délégué sur #ecran-identite) :** lire-voix (lireIdentiteVoixHaute), confirmer-identite (allerConsignes), pas-moi (demanderPinFormateur), pin-debloquer (verifierPinFormateur), pin-annuler (annulerPinFormateur). Logique PIN strictement intacte.

**Nettoyage doublons CSS :** .identite-nom, .identite-info, .checkbox-confirm étaient définies 2 fois (anciennes en bleu #1a237e/#f0f2f7/28px + nouvelles .sel2-* anthracite). Anciennes SUPPRIMÉES.

**Date FR :** date de naissance arrivait en ISO YYYY-MM-DD, affichée brute. Helper formaterDateFr(str) (regex ISO → jj/mm/aaaa) appliqué aux 2 voies de remplissage de identite-info : voie QR (START_DDN) et voie tablette (data-naissance).

**Lecture vocale :** rate = 0.8 (tentative 0.9 annulée sur demande). ÉCART DOC/CODE RÉSOLU : claude.mp documentait 0.9, code réel était 0.8 — désormais aligné à 0.8 partout.

**IDs préservés (JS) :** identite-nom, identite-info, confirm-identite, zone-pas-moi, pin-formateur-input, pin-formateur-error.

### ✅ Chantier terminé : variables CSS dans test_theorie.html (option A — couleurs de marque)

**Objectif :** permettre un changement de couleur en cascade (modifier une ligne :root → tout le fichier suit). Périmètre LIMITÉ à test_theorie.html (le reste du site = chantier dédié ultérieur, fichier par fichier).

**Bloc :root** (en haut du <style>) définit 14 variables : --noryx-anthracite (#383b40), --noryx-anthracite-fonce (#2a2c30), --noryx-ardoise (#4a5568), --noryx-gris (#888), --noryx-gris-clair (#f0efef), --noryx-surface (#f4f5f6), --noryx-blanc (#fff), --noryx-rouge (#cc0000), --noryx-rouge-erreur (#c62828), --noryx-ambre-fond (#FFF4E0), --noryx-ambre-bordure (#F0C775), --noryx-ambre-texte (#854F0B), --noryx-ambre-texte-pin (#7A5600), --noryx-ambre-pastille (#FAC775).

**FAIT (complet) :** toutes les couleurs de marque variabilisées via sed/Git Bash — anthracite (#383b40, 18 occ.), hover (#2a2c30), ardoise (#4a5568, 10 occ.), gris-clair (#f0efef), surface (#f4f5f6), rouge-erreur (#c62828), et les 5 ambres (#FFF4E0, #F0C775, #854F0B, #7A5600, #FAC775). NON variabilisés volontairement (option A) : #fff blanc, #888 gris générique. Bleu résiduel #1a237e/#f0f2f7 (écrans 6/modale) laissé en dur, disparaîtra à leur restyle. Changer une couleur de marque = modifier une ligne dans :root, tout le fichier suit.

**⚠️ RÈGLES CRITIQUES apprises (NE PAS recasser) :**
1. JAMAIS PowerShell Set-Content sur ce fichier — il corrompt l'UTF-8 (accents → mojibake "Ã©"), ajoute un BOM (EF BB BF), et convertit LF→CRLF. Utiliser EXCLUSIVEMENT sed/str_replace via Git Bash. Un commit PowerShell a dû être annulé (restauration depuis commit sain f516c71).
2. Le JS NE RÉSOUT PAS les variables CSS. Toute couleur en JavaScript (colorDark du QR ligne ~1308, timerEl.style.color du chrono) DOIT rester en hex en dur. Un sed global a remplacé colorDark par var(--noryx-anthracite) → QR invisible. Remis en '#383b40'.
3. Après un sed global sur une couleur, la définition dans :root est aussi remplacée (auto-référence circulaire --noryx-X: var(--noryx-X)) → la variable ne résout plus → fond transparent. TOUJOURS remettre la ligne :root en hex après chaque sed (via str_replace pour éviter le piège des parenthèses regex non échappées).
4. Encodage cible : UTF-8 SANS BOM, LF. Vérifier après chaque passe : file -i (charset=utf-8, pas de BOM) + head -c 3 | xxd (ne doit PAS être ef bb bf) + grep "Théorie\|Sélection" (accents corrects).

**État charte anthracite :** ✅ header (titre centré), écrans 1/2/3, QCM, récap. RESTE : écran 6 (résultat, #1a237e ~946/962), modale confirmation (~1595/1704). Sécurité logo header : #test-logo a height fixe (40px/28px) + max-width (150px/110px) + object-fit:contain → tout format de logo sans casser le header.

### ✅ Chantier terminé : écran 6 (résultat) — restyle anthracite + reformulation phrase fin (commit 7caaf78)

**Périmètre :** #ecran-resultat dans templates/test_theorie.html (lignes ~1095–1118). 24 lignes HTML uniquement.

**Couleurs migrées :**
- h2 titre "Bravo et merci…" : color:#1a237e → color:var(--noryx-anthracite)
- 2× `<p>` corps de carte : color:#333 → color:var(--noryx-ardoise)
- `<p>` mention résultats : color:#666 → color:var(--noryx-gris)
- phrase tablette : color:#1a237e → color:var(--noryx-anthracite)

**Reformulation phrase finale :**
- "REMETTEZ LA TABLETTE AU TESTEUR" (uppercase 2.4rem) → "Prévenez votre testeur que vous avez terminé" (1.6rem — réduit car nouvelle phrase plus longue)
- Ton moins impératif ; text-transform:uppercase conservé ; reste du style intact (gras, centrage, anthracite).

### ✅ Chantier terminé : modale de confirmation — restyle + migration onclick (commit 878088f)

**Périmètre :** #modal-confirm dans templates/test_theorie.html (lignes ~1722–1731). Modale unique, s'ouvre uniquement quand questions sans réponse (valider() avec force=false).

**Couleurs migrées :**
- #confirm-message : color:#1a237e → color:var(--noryx-rouge) (titre alerte rouge — c'est un avertissement "questions sans réponse")
- "Cette action est irréversible." : color:#888 → color:var(--noryx-gris)

**Migration onclick → data-action :**
- Bouton "← Revenir au test" : onclick="fermerConfirm()" → data-action="fermer-confirm" type="button"
- Listener délégué ajouté sur #modal-confirm (plus précis qu'un listener global document)
- confirm-ok-btn.onclick (JS dynamique, callback variable) : INTENTIONNELLEMENT conservé — légitime

**État charte anthracite :** ✅ COMPLET sur test_theorie.html — header (titre centré), écrans 1/2/3/6, QCM, récap, modale confirmation. #1a237e résiduel uniquement dans le CSS QCM (boutons réponse, options, navigation) — chantier CSS QCM bleu distinct.

### ✅ Chantier terminé : suivi live session — route + polling (commits 46a2b84, 745b949)

**Route `GET /api/sessions/{id}/etat-live` (sessions.py) :** état temps réel par candidat — `theorie` (passe/en_attente/dispense), `pratique` (complet/partiel/en_attente), `neutralite` (signee/en_attente). 5 requêtes batch, auth cookie, 401 si non authentifié. Double dispense : `sc.theorie_dispensee OR rt.dispense`. Résultats bloqués exclus (`rt.bloque`, `ep.bloque`).

**Polling `static/js/session_detail.js` (IIFE en fin de fichier) :** toutes les 30 s, compare une signature `stagiaire_id:theorie:pratique:neutralite` — si différente et aucune modale ouverte → `location.reload()`. Suspendu si `document.hidden`. Première réponse = référence (pas de reload au démarrage). 12 modales surveillées via `style.display === 'flex'`.

### ✅ Chantier terminé : route GET /api/sessions/{id}/etat-live (commit 46a2b84)

**Objectif :** état temps réel par candidat pour un tableau de bord live de session.

**Réponse JSON :**
```json
{ "session_id": 42, "ts": "2026-06-22T14:30:00Z",
  "candidats": [{ "stagiaire_id": 7, "nom": "DUPONT", "prenom": "Jean",
    "theorie": "passe|en_attente|dispense",
    "pratique": "complet|partiel|en_attente",
    "neutralite": "signee|en_attente" }] }
```

**Règles métier :**
- `theorie` : `dispense` si `rt.dispense OR sc.theorie_dispensee` ; `passe` si `rt` existe, non bloqué, `obtenue is not None` ; sinon `en_attente`
- `pratique` : compare `cats_faites` (SessionEpreuve non bloquées) vs `cats_planifiees` (JourTestCandidat actifs, jours pratique) — `complet/partiel/en_attente`
- `neutralite` : `signee` si AttestationNeutralite existe avec `signature_base64 non null` (via jours théorie de la session)

**Anti-N+1 :** 5 requêtes batch quel que soit le nombre de candidats. Auth : middleware cookie (401 si non authentifié).

### ✅ Chantier terminé : nettoyage CSS orphelines test_theorie.html (commit 713a967)

- 6 classes CSS pré-restyle écran 1 supprimées (remplacées par .sel1-*) : `.selection-logo-circle`, `.selection-titre`, `.grille-info`, `.grille-badge`, `.grille-texte`, `.timer-display`. Contenaient encore des `#1a237e` / `#e8eaf6` / `#3949ab` inutilisés.
- `select:focus { border-color: #1a237e }` → `var(--noryx-anthracite)` (seule règle `select:focus` encore active sur les selects natifs).
- **Résultat :** zéro `#1a237e` dans test_theorie.html. 52 lignes supprimées.

### ✅ Chantier terminé : suivi live session (polling + auto-reload)

**Besoin :** sur session_detail.html, voir les résultats tomber sans recharger manuellement (un testeur dépose une note → le back-office/terrain la voit apparaître). Théorie et pratique ne sont jamais simultanées (axes distincts dans le temps), donc PAS de bandeau de synthèse séparé — on rafraîchit la page existante.

**Approche retenue (après arbitrage) :** auto-reload discret conditionnel, PAS de mise à jour DOM ciblée (trop complexe à reconstruire fidèlement : 5 badges T1-T5, note, RÉUSSI/ÉCHEC). Le reload complet est plus simple et fiable, et comme les résultats arrivent espacés (jamais 50 d'un coup), un reload occasionnel est imperceptible.

**Route serveur — GET /api/sessions/{id}/etat-live (sessions.py) :**
- Auth cookie (request.state.user, 401 sinon). Renvoie {session_id, ts, candidats:[{stagiaire_id, nom, prenom, theorie, pratique, neutralite}]}.
- Statuts : theorie = "dispense" (rt.dispense OU sc.theorie_dispensee) / "passe" (rt non bloqué + obtenue non null) / "en_attente". pratique = "complet" (toutes catégories planifiées faites, hors bloquées) / "partiel" / "en_attente". neutralite = "signee" (signature_base64 non null) / "en_attente".
- ANTI-N+1 : 5 requêtes batch quelle que soit la taille de session (candidats, ResultatTheorie, SessionEpreuve, JourTestCandidat planifiées, AttestationNeutralite via jt_ids).
- Subtilités gérées : double dispense (inscription + résultat), exclusion des résultats bloque=True (théorie ET pratique), AttestationNeutralite sans FK réelle (jointure manuelle via jour_test_id des jours théorie).

**Polling client — fin de static/js/session_detail.js (IIFE) :**
- Intervalle 30 s (page admin, pas de hot path). window.SESSION_ID lu depuis #session-data.
- Comparaison par SIGNATURE : sérialise l'état candidats (stagiaire_id:theorie:pratique:neutralite). Reload SEULEMENT si la signature change vs la référence. 1er appel = établit la référence sans reload (pas de boucle).
- Garde-fous (non-intrusif) : (1) suspendu si document.hidden (onglet caché) ; (2) si changement détecté MAIS une modale est ouverte → ne met PAS à jour la référence et ne recharge pas → reload différé jusqu'à fermeture de la modale (changement jamais perdu) ; (3) erreur réseau → console.warn, pas de crash, réessai au cycle suivant.
- MODAL_IDS liste les modales surveillées (modal-pin, modal-jour-theorie/pratique, modal-candidat, modal-loupe-theorie, etc.) ; détection via style.display === 'flex'.
- Tous rôles (terrain + back-office). node -c validé (syntaxe OK — important car une erreur casserait tout le JS de la page).

**Scalabilité :** ~100 organismes simultanés = ~3 req/s à 30 s d'intervalle, négligeable. Multi-tenant (base par tenant) répartira la charge. Réévaluer SSE seulement si charge explose.

### ✅ Chantier terminé : audio questions — étape 1/3 (colonne + migration) (commit adec9be)

**Besoin :** permettre l'association d'un fichier audio MP3 (hébergé Cloudinary) à chaque question de grille théorique, avec fallback speech synthesis navigateur. Étape 1 = infrastructure BDD uniquement (pas encore d'upload ni de lecture).

**Modèle — `app/models/grille_theorie.py` :**
- `ReponseGrille` : `audio_url = Column(String(500), nullable=True)` ajouté après `image_url`.
- Nullable : la plupart des questions resteront sans audio au début.

**Migration — deux vecteurs :**
1. `migrate_audio_question.py` : script idempotent (inspire des migrations existantes), détecte le dialecte SQLite/PostgreSQL, skip si colonne déjà présente. À exécuter manuellement sur Render si besoin. Colonne confirmée localement via SQLite PRAGMA.
2. `app/main.py` — `_run_startup_migrations()` : `"ALTER TABLE reponses_grilles ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)"` ajouté en fin de liste. Géré automatiquement au démarrage sur Render.

**Rappels étapes suivantes :**
- Étape 3 : `get_questions_phase2` → ajouter `"audio": q.audio_url` ; `test_theorie.html` → jouer MP3 si `q.audio` présent, sinon `SpeechSynthesisUtterance(rate=0.8)` (fallback déjà en place).

### ✅ Chantier terminé : audio questions étape 2/3 — routes Cloudinary (commit 65fdcad)

**Routes ajoutées dans `app/routers/upload.py` (fin de fichier) :**
- `POST /api/upload/question-audio` — upload batch MP3 → Cloudinary `resource_type="video"` (Cloudinary classe les MP3 sous "video"), `public_id = caces_questions/audio/{nom_sans_extension}`
- `POST /api/upload/associer-audios?pin=` — liste Cloudinary `prefix="caces_questions/audio/"`, parse `R482_G1_T2_Q1` (underscores), met à jour `rq.audio_url`
- `DELETE /api/upload/supprimer-audio?filename=&pin=` — `cloudinary.uploader.destroy(public_id, resource_type="video")` — le `resource_type="video"` est obligatoire (sans ça Cloudinary cherche une image et renvoie "not found")
- `GET /api/upload/liste-audios` — liste `prefix="caces_questions/audio/"` avec `resource_type="video"`

**Convention de nommage uniformisée (images ET audio) :** `R482_G1_T2_Q1` (underscores). La route `associer-images` existante a été corrigée de `split("-")` → `split("_")` dans le même commit.

### ✅ Chantier terminé : audio questions étape 3/3 — lecture MP3 + fallback voix (commit ab8aa57)

**`app/services/tirage_grille.py` — `get_questions_phase2` :**
- Clé `"audio": q.audio_url` ajoutée dans le dict question (après `"image"`). `None` si pas d'audio.

**`templates/test_theorie.html` — 4 modifications :**
1. Globals : `var _audioUrlCourante = null` + `var _audioQuestionEnCours = null` (niveau script)
2. `_couperAudioEnCours()` : pause/reset `Audio` en cours + `speechSynthesis.cancel()`
3. `_lireTexteSysteme(texte)` : `SpeechSynthesisUtterance` `rate=0.8`, `lang=fr-FR`
4. `lireQuestion(audioUrl, texte)` : priorité MP3 (`new Audio(audioUrl).play()`), fallback `onerror` + `.catch()` → `_lireTexteSysteme`. Si pas d'audioUrl → directement synthèse.
- Bloc auto-lecture dans `afficherQuestion` remplacé par `_audioUrlCourante = q.audio || null; lireQuestion(…)`
- `relireQuestion()` remplacé par `lireQuestion(_audioUrlCourante, texte_dom)`
- `lireIdentiteVoixHaute()` (écran identité) inchangé — pas de question, pas d'audio Cloudinary

**Fix connexe 2 (commit eb3e89b) :** champ `audio` absent du `questions.push()` JS (ligne ~1146 de `test_theorie.html`) — l'API renvoyait `audio_url` correctement mais le JS ne le copiait pas dans l'objet `questions[]`, donc `q.audio` était toujours `undefined` → toujours fallback voix. Corrigé : `audio: q.audio || null` ajouté après `image`.

**Flux complet :** MP3 nommé `R482_G1_T2_Q1.mp3` uploadé via admin → `POST /associer-audios?pin=` → `audio_url` sur `ReponseGrille` → servi dans `get_questions_phase2` → `data.themes[t]` → `questions.push({audio: q.audio||null})` → `_audioUrlCourante = q.audio || null` → `lireQuestion` joue le MP3, fallback voix si absent ou erreur réseau.

**Indicateur "Dernière association" audio (commit 61633e4) :**
- Nouveau modèle `app/models/association_audio_log.py` : `AssociationAudioLog` (`id`, `date_association`, `nb_audios`) — table `association_audio_log` créée par `create_all()` au démarrage (import dans `main.py` ligne 29)
- `associer_audios` : log `AssociationAudioLog(date_association=now(), nb_audios=updated)` après commit (calque exact `associer-images`)
- Route `GET /api/upload/derniere-association-audio` : dernier log + count Cloudinary `prefix="caces_questions/audio/"` `resource_type="video"` → `{date, nb_audios, total_cloudinary}`
- UI `admin_images.html` : `<span id="derniere-assoc-audio">` après bouton associer, `chargerDerniereAssociationAudio()` appelée après association réussie ET à l'ouverture de l'onglet Audio

**Fix connexe 1 (commit cf857c0) :** crash JS `null.addEventListener` sur `/start` — `modal-confirm` était définie à la ligne 1694 (après `</script>` ligne 1691), donc `getElementById('modal-confirm')` retournait `null` au moment de l'exécution du script. Corrigé en attachant le listener à `document` (délégation) au lieu de `#modal-confirm` — `document` existe toujours, `closest('[data-action="fermer-confirm"]')` filtre correctement. Ce crash bloquait l'exécution complète du script, y compris les fonctions audio.

**UI admin dans `templates/admin_images.html` :**
- Commit 5a51f8d : section audio ajoutée (drop-zone MP3, bouton associer, liste `<audio controls>`, suppression)
- Commit 68889c6 : page transformée en 2 onglets "🖼️ Images" / "🔊 Audio" — titre renommé "Médias des questions", lazy load audio (chargerAudios() déclenché à la première ouverture de l'onglet Audio, pas au chargement initial), listener `data-action="onglet-medias"` CSP-safe
- Commit bb802e3 : bouton admin.html renommé "🎬 Médias des questions", `<title>` admin_images.html mis à jour
- PIN via `demanderPin()` (modale custom, pas `prompt()`) pour associer et supprimer
- Liste audios : `GET /api/upload/liste-audios` → rendu `<audio controls>` + 🗑️ → `DELETE /api/upload/supprimer-audio`
- Init : `chargerAudios()` appelé au chargement de la page aux côtés de `chargerImages()`

### ✅ Chantier terminé : audio MP3 par question (TTS) avec fallback voix système

**Besoin :** chaque question peut avoir un MP3 (généré TTS/IA). Au test : si MP3 dispo → on le joue ; sinon → synthèse vocale navigateur (rate 0.8). MP3 prioritaire.

**Stockage :** Cloudinary resource_type="video" (Cloudinary classe l'audio en vidéo). Convention de nommage UNIFORMISÉE en underscores : R482_G1_T1_Q001.mp3 (famille_grille_theme_question). Le parsing images est AUSSI passé en underscores (split("_")) — une seule convention pour tout.

**Étape 1 — modèle :** ReponseGrille (table reponses_grilles) + colonne audio_url VARCHAR(500). Migration migrate_audio_question.py (idempotent) + startup.

**Étape 2 — upload admin (upload.py) :** 4 routes calquées sur les images : POST /question-audio (batch MP3 → Cloudinary video, public_id caces_questions/audio/{nom}), POST /associer-audios (parse nom underscores → audio_url, PIN admin), DELETE /supprimer-audio (destroy avec resource_type="video" OBLIGATOIRE sinon "not found"), GET /liste-audios (prefix caces_questions/audio/, resource_type="video"). UI : admin_images.html renommée "Médias des questions" avec ONGLETS Images/Audio (lazy load audio, évite de scroller 5000 images). Bouton admin renommé "🎬 Médias des questions".

**Étape 3 — lecture :** get_questions_phase2 (tirage_grille.py) ajoute "audio": q.audio_url. test_theorie.html : 3 fonctions (_couperAudioEnCours, _lireTexteSysteme, lireQuestion) — MP3 prioritaire, coupure du précédent, double fallback (onerror MP3 cassé + catch autoplay rejeté). _audioUrlCourante au niveau script (partagé auto-lecture + relireQuestion).

**3 BUGS RÉSOLUS (longue session de debug) :**
1. Crash JS : listener sur #modal-confirm via getElementById().addEventListener() — l'élément est défini APRÈS le </script>, donc null au moment de l'exécution → crash qui tuait tout le bas du script. Fix : délégation sur document (document.addEventListener('click', ...) + closest('[data-action="fermer-confirm"]')).
2. Champ audio perdu dans le JS : la route /jours/{}/grille transmet bien "audio" (vérifié dans le JSON), mais le push questions[] (test_theorie.html ~ligne 1145) recopiait les champs en OUBLIANT audio → q.audio undefined → toujours fallback voix. Fix : ajout de "audio: q.audio || null" au push.
3. Projection collective (main.py ~665) : questions_flat construit sans audio — PAS corrigé (la projection n'a pas besoin d'audio, c'est un affichage vidéoprojecteur).

**Couverture par thème :** une grille de test est assemblée par TIRAGE de thèmes issus de grilles différentes (INRS). Donc sonoriser "la grille 1" ne sonorise QUE les questions de grille 1 qui sortent au tirage. Les thèmes tirés d'autres grilles non sonorisées → fallback voix système (normal).

**Réglage vitesse MP3 :** PAS de playbackRate dans l'app (dégrade la voix). Les MP3 étant générés TTS, on RÉGÉNÈRE à la bonne vitesse à la source + réupload (overwrite=True écrase, audio_url inchangé, pas besoin de réassocier).

**Indicateur "Dernière association" audio :** table dédiée AssociationAudioLog (date_association, nb_audios) créée par create_all() au boot (pas de migration manuelle). Route GET /derniere-association-audio. UI : span #derniere-assoc-audio sous le bouton, "Dernière association : JJ/MM/AAAA HH:MM (N/M)".

### ✅ Chantier terminé : options incluses pilotées par résultat pratique (commit 13ab4af)

**Besoin :** dans la modale de résultat pratique (#modal-pratique), les options incluses (opt.incluse=true) doivent se cocher automatiquement si RÉUSSI et se décocher si ÉCHEC. Les options facultatives restent libres.

**Fichier :** static/js/session_detail.js uniquement.

**Détails :**
- `saisirResultatPratique` (~ligne 645) : boucle `displayOpts.forEach` distingue incluses/facultatives. Incluses → `data-incluse="1" disabled` + style gris + span `(incluse)`. Facultatives → unchanged.
- Fonction `synchroniserOptionsIncluses()` : lit `[name="pratique-resultat"]:checked`, coche/décoche les `[data-incluse="1"]` selon `value === 'true'`. Appelée à l'ouverture de la modale ET sur changement radio via délégation `document.addEventListener('change', ...)`.
- `sauvegarderPratique` inchangé : `querySelectorAll('[name="pratique-option"]:checked')` inclut nativement les `disabled` cochés → les incluses cochées (RÉUSSI) sont bien envoyées ; les décochées (ÉCHEC) sont absentes.

**Radio résultat :** name=`pratique-resultat`, valeurs `"true"` (RÉUSSI) / `"false"` (ÉCHEC).

### ✅ Chantier terminé : justificatif dispense théorie sur R2 (chantier pilote R2)

**Contexte :** la dispense de théorie existe (`SessionCandidat.theorie_dispensee` + `dispense_note`). On ajoute un fichier justificatif stocké sur Cloudflare R2 — la BDD ne stocke que la clé + métadonnées, jamais le binaire.

**Étape 2/5 terminée (commit c43c4f1) :** 3 colonnes ajoutées sur `session_candidats` :
- `dispense_fichier_cle VARCHAR(500)` — clé objet R2, ex: `pepci/dispenses/{uuid}.pdf`
- `dispense_fichier_nom VARCHAR(255)` — nom original du fichier uploadé
- `dispense_fichier_type VARCHAR(100)` — type MIME, ex: `application/pdf`
- Migration startup idempotente ajoutée dans `main.py` (pattern `ADD COLUMN IF NOT EXISTS`)

**Étape 4/5 terminée (commit 1088616) :** module `app/services/storage.py` créé + `boto3>=1.34.0` ajouté à requirements.txt (converti UTF-16→UTF-8 via iconv dans Git Bash — NE JAMAIS utiliser PowerShell Set-Content/Add-Content sur requirements.txt, corrompt l'encodage).
- `_client()` : client S3 pointé sur R2 via `R2_ENDPOINT` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`, signature s3v4, region "auto"
- `_bucket()` : lit `R2_BUCKET`
- `construire_cle(prefixe, nom)` → `pepci/{prefixe}/{uuid}.{ext}`
- `upload_fichier(bytes, cle, content_type)`, `get_fichier(cle)`, `delete_fichier(cle)`
- `test_connexion()` : write/read/delete selftest, retourne `{"ok": bool, ...}`
- Constantes : `EXTENSIONS_AUTORISEES`, `MIME_AUTORISES`, `TAILLE_MAX = 10 Mo`
- TENANT = "pepci" en dur (mono-tenant pilote)

**Variables env R2 câblées sur Render :** `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` (NB : pas R2_BUCKET_NAME, juste R2_BUCKET).

**Étape 5a/5 terminée (commit 0541119) :** 3 routes FastAPI ajoutées en fin de `app/routers/sessions.py` :
- `POST /{session_id}/candidats/{sc_id}/dispense-fichier` — upload multipart → R2, valide ext + taille, supprime l'ancien objet si existant, met à jour `dispense_fichier_cle/nom/type` sur `SessionCandidat`
- `GET /{session_id}/candidats/{sc_id}/dispense-fichier` — StreamingResponse depuis R2, auth cookie (`request.state.user`)
- `DELETE /{session_id}/candidats/{sc_id}/dispense-fichier` — supprime R2 + nullifie les 3 colonnes en BDD
- Imports ajoutés en tête : `UploadFile, File`, `StreamingResponse`, `BytesIO`, `from app.services import storage`
- Type DB : `DBSession` (alias `sqlalchemy.orm.Session`) — conforme au standard du fichier

**Étape 5b/5 terminée (commit bee2d0e) :** UI modale candidat — champ justificatif de dispense.
- `session_detail.html` : bloc `#field-dispense-fichier` inséré après `#field-dispense-note` — `input[type=file]` caché, bouton 📎 Joindre, span nom, boutons 👁️ Voir + 🗑️ Retirer (masqués si aucun fichier), div msg feedback.
- `session_detail.js` — 4 modifications :
  1. `_syncDispenseNote()` : affiche/masque aussi `#field-dispense-fichier` selon RÉUSSI/ÉCHEC
  2. `ouvrirAjoutCandidat()` : appel `_majAffichageJustif('')` à l'ouverture en mode création
  3. `editerCandidat()` : 5e param `fichierNom`, appel `_majAffichageJustif(fichierNom||'')` avant affichage modale
  4. Bloc complet en fin de fichier : `_majAffichageJustif`, `_justifMsg`, `_assurerCandidatEnregistre` (crée le candidat si mode création et capture `sc.id`), `_uploaderJustif` (FormData POST → R2), listeners délégués `click` (joindre/voir/retirer) + `change` (sc-justif-input → upload)
- Branchement `data-fichier-nom` (commit f2ce031) : `data-fichier-nom="{{ sc.dispense_fichier_nom or '' }}"` ajouté sur le bouton ✏️ ET sur la pastille `Disp.` (rendue cliquable avec `data-action="editer-candidat"` + `cursor:pointer` + title enrichi). Listener JS ligne 199 : 5e arg `btn.dataset.fichierNom` passé à `editerCandidat()`.

**Chantier pilote R2 — COMPLET** (commits c43c4f1 → 5ae06fb).

**Bug fix post-livraison (commit 5ae06fb) :** `editerCandidat()` n'affichait pas `#field-dispense-fichier` en mode édition (seul `_syncDispenseNote` le gérait, pas appelé à l'ouverture). Ajout d'une ligne miroir : `getElementById('field-dispense-fichier').style.display = theorie_dispensee ? 'block' : 'none'` juste après la même ligne pour `field-dispense-note`.

### ✅ Chantier terminé : date de dispense (dispense_date)

**Étape 1/2 terminée (commit d1b94a9) :** colonne `dispense_date DATE` ajoutée sur `session_candidats` (nullable, après `dispense_fichier_type`). Migration startup idempotente ajoutée dans `main.py`. Représente la date d'obtention de la théorie/CACES justifiant la dispense (utile pour futur calcul de validité CACES).

**Étape 2/2 terminée (commit 2957dcf) :** champ date dans la modale candidat + persistance.
- `sessions.py` : `dispense_date: Optional[date] = None` dans `SessionCandidatCreate` ; `sc.dispense_date = data.dispense_date if data.theorie_dispensee else None` dans `update_candidat` ; `add_candidat` inchangé (model_dump propage automatiquement).
- `session_detail.html` : bloc `#field-dispense-date` inséré avant `#field-dispense-note` (input[type=date] id=sc-dispense-date) ; `data-dispense-date` ajouté sur pastille Disp. et bouton ✏️.
- `session_detail.js` : 5 modifications — `_syncDispenseNote` (affiche/masque field-dispense-date), `ouvrirAjoutCandidat` (vide sc-dispense-date), `editerCandidat` (6e param dispenseDate + display + pré-remplissage), listener (6e arg btn.dataset.dispenseDate), `sauvegarderCandidat` (dispense_date dans data{}).

**Chantier date de dispense — COMPLET** (commits d1b94a9 → 2957dcf).

### ✅ Chantier terminé : pilote stockage objet R2 + justificatif/date de dispense + permissions terrain + hard delete candidat

**DÉCISION ARCHITECTURALE MAJEURE :** FICHIERS (PDF/Word/Excel) sur **Cloudflare R2** (objet S3-compatible), JAMAIS base64 en base. Cloudinary reste pour les IMAGES (photos/logo/signature). R2 = cible multi-tenant (un bucket par tenant à terme). Bucket `noryx-documents` (WEUR, privé). Tier gratuit 10 Go + egress gratuit.

**Variables env Render :** `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

**Module `app/services/storage.py` (boto3) :** `construire_cle(prefixe, nom)` → `{TENANT}/{prefixe}/{uuid}.{ext}` (TENANT="pepci" en dur) ; `upload_fichier` / `get_fichier` / `delete_fichier` / `test_connexion` ; `EXTENSIONS_AUTORISEES` pdf/doc/docx/xls/xlsx ; `TAILLE_MAX` 10 Mo ; s3v4, region auto. boto3>=1.34.0 dans requirements.

**`SessionCandidat` +4 colonnes (migrations startup `ADD COLUMN IF NOT EXISTS`) :** `dispense_fichier_cle/nom/type` + `dispense_date` DATE.

**3 routes justificatif dispense (`sessions.py`, auth cookie `request.state.user`, PAS de PIN, multipart FormData PAS base64) :** `POST`/`GET`/`DELETE` `/api/sessions/{sid}/candidats/{sc_id}/dispense-fichier`. GET = StreamingResponse R2.

**Permissions terrain (`_verifier_role` dans `main.py`) :** terrain UPLOAD (`POST`) autorisé — whitelisté ligne ~559 (cas : apprenant apporte CACES externe le jour du test) ; terrain VOIT (`GET`, jamais bloqué par le catch-all) ; terrain NE SUPPRIME PAS (`DELETE` tombe dans catch-all → 403, back-office only, anti-erreur).

**Modale candidat (CSP-safe) :** zone dispense (si théorie="dispense") = champ date + note + justificatif. Upload immédiat ; en création `_assurerCandidatEnregistre()` crée le candidat (`add_candidat` renvoie `id`) puis uploade. Pré-remplissage via `data-fichier-nom` + `data-dispense-date` (5e/6e args `editerCandidat`). Crayon ✏️ = édite. **Pastille "Disp." = ouvre DIRECTEMENT le justificatif** (`data-action="dispense-fichier-direct"`), toast info ardoise "Aucun justificatif joint" si absent (`afficherInfoToast`, `#4a5568`). NON BLOQUANT.

**`remove_candidat` : SOFT → HARD DELETE.** `db.delete(sc)` au lieu de `actif=False`. Philosophie : retrait par erreur/changement de session = AUCUNE trace. Protection ligne 307 CONSERVÉE (refus 400 si `JourTestCandidat` planifié — garantit pas d'épreuve/résultat/CACES). Purges manuelles AVANT `db.delete` (pas de FK cascade) : fichier R2 (`storage.delete_fichier`) + `ConsentementRGPD` (couple `session_id`+`stagiaire_id`).

**RÈGLES ANTI-RÉGRESSION (permanentes) :**
- Ne JAMAIS stocker de binaire en base → `storage.py` R2, persister que la clé. Justificatif théorie existant (`ResultatTheorie.justificatif_pdf` base64) à migrer vers R2 plus tard.
- Le fichier R2 ne part JAMAIS seul → purge explicite `storage.delete_fichier()` AVANT `db.delete`.
- Variables `--noryx-*` CSS définies seulement dans `test_theorie.html` (PAS globales) → rester inline en dur hors test_theorie tant que CSS non centralisé.
- JAMAIS éditer requirements.txt/Python via PowerShell (UTF-16 → build cassé). iconv/sed Git Bash ou VS Code (UTF-8).

### ✅ Chantier terminé : détection dispense étape A — proposition vérifiable dans modale candidat (2026-06-23)

**Objectif :** quand l'opérateur coche "Théorie dispensée" pour un candidat, le système détecte automatiquement s'il existe une base de dispense (CACES ou théorie < 12 mois) et AFFICHE UNE PROPOSITION INFO. Le système NE COCHE RIEN, NE REMPLIT RIEN automatiquement — l'opérateur valide toujours.

**Fichiers modifiés :** `app/services/caces_obtenus.py`, `app/routers/stagiaires.py`, `app/routers/sessions.py`, `app/models/session_candidat.py`, `app/main.py`, `templates/session_detail.html`, `static/js/session_detail.js`.

**Étape R1 — service `detecter_base_theorique` (`app/services/caces_obtenus.py`, lignes 235-342) :**
- Fonction pure (lecture seule, pas de side effect), 3 sources (règle 12 mois = base + 1 an − 1 jour >= today) :
  - **R1** : `CacesObtenu` non-extension (`post_cloture==False`), statut `valide`/`a_valider`, même famille, `date_obtention` dans la fenêtre.
  - **R2-a** : `ResultatTheorie` `obtenue==True` de la session courante (si `session_id` fourni) — continuité §8.
  - **R2-b** : `ResultatTheorie` `obtenue==True` d'une autre session, même famille, ORPHELINE (aucun `CacesObtenu.resultat_theorie_id` ne pointe dessus), dans la fenêtre.
- Retourne `{"possible": False}` ou `{"possible": True, "type" ("theorie"/"caces"), "date_origine", "reference", "date_limite_dispense", "lien", "source" ("R1"/"R2-a"/"R2-b"), "source_id"}`.
- Candidat le plus récent gagne (`max(candidates, key=lambda x: x["date"])`). Pattern `_limite_dispense(d)` avec gestion 29 fév.

**Étape A1 — route `GET /stagiaires/{stag_id}/base-theorique?famille=&session_id=` (`app/routers/stagiaires.py`, ligne 354) :**
- Wrapper mince appelant `detecter_base_theorique`. Auth middleware cookie.

**Étape A2 — modale candidat (`templates/session_detail.html` + `static/js/session_detail.js`) :**
- `<div id="dispense-proposition">` (infobox bleue, `display:none` par défaut) dans le bloc dispense.
- `window._scStagiaireId` mémorisé dans `_selectionnerCandidatStagiaire()`.
- `_syncDispenseNote()` appelle `_detecterDispense()` à chaque changement du select théorie.
- `_detecterDispense()` : fetch `/stagiaires/{id}/base-theorique?…` → si `data.possible`, affiche la proposition (type, référence, dates, lien vérification) ; sinon message "Aucune base". NE COCHE RIEN.

**Étape B-colonnes — 3 colonnes traçabilité sur `SessionCandidat` (`app/models/session_candidat.py`, lignes 23-25) :**
- `dispense_origine VARCHAR(20)` : `'interne'` (base détectée) ou `'externe'` (pas de base, justificatif manuel).
- `dispense_source_type VARCHAR(20)` : `'theorie'` ou `'caces'` (NULL si externe).
- `dispense_source_id INTEGER` : id `ResultatTheorie` ou `CacesObtenu` (NULL si externe).
- Migrations startup (`main.py`) : 3 `ALTER TABLE session_candidats ADD COLUMN IF NOT EXISTS`.

**Étape B-save — calcul serveur (`app/routers/sessions.py`) :**
- Dans `add_candidat` (après `sc = SessionCandidat(…)`, avant `db.add(sc)`) : si `data.theorie_dispensee`, appel `detecter_base_theorique` → remplit `dispense_origine`/`source_type`/`source_id`. Interne si `possible`, externe sinon.
- Dans `update_candidat` (après `sc.dispense_date`) : même logique + reset à `None` si `theorie_dispensee=False`.
- **JAMAIS depuis le client** : ces 3 champs ABSENTS du schéma Pydantic `SessionCandidatCreate` — le JS ne les transmet jamais.

**Règle permanente** : `_detecterDispense` NE COCHE RIEN (side-effect zéro côté client). La décision appartient à l'opérateur. La traçabilité est calculée côté serveur au moment du save.

### ✅ Chantier terminé : dispense externe — garde-fous serveur (C1-serveur) (2026-06-23)

**Contexte :** une dispense est "externe" quand le serveur ne trouve AUCUNE base interne (autre organisme, ou vieux CACES PEPCI hors base). `dispense_origine='externe'` est posé au save (étape B). C1-serveur ajoute les garde-fous réglementaires durs.

**Helper réutilisable `limite_12_mois(date_ref)` (`app/services/caces_obtenus.py`, module-level, ligne 235) :**
- Calcul "+1 an −1 jour" avec gestion 29 février (fallback 1er mars année+1).
- Remplace la fonction imbriquée `_limite_dispense` de `detecter_base_theorique` (4 appels internes basculés : R1, R2-a, R2-b, retour dict). Source unique du calcul des 12 mois pour la dispense.
- `_date_echeance` (5/10 ans CACES) reste séparée — autre calcul, autre usage.

**Garde-fous au save (`add_candidat` + `update_candidat`, `sessions.py`) :**
- Après le bloc traçabilité, AVANT `db.add`/`db.commit` : si `sc.dispense_origine == "externe"` :
  - date manquante (`not data.dispense_date`) → HTTP 400 "Dispense externe : la date d'obtention justifiant la dispense est obligatoire."
  - `limite_12_mois(data.dispense_date) < date.today()` → HTTP 400 "Dispense externe : la base invoquee a plus de 12 mois (theorie perimee)."
- Rejet AVANT enregistrement (aucune donnée partielle en base).
- L'interne (`dispense_origine='interne'`) n'est PAS contrôlé ici : sa date est validée par `detecter_base_theorique` (qui a déjà vérifié la fenêtre 12 mois).
- `date` et `HTTPException` déjà importés en tête de `sessions.py` — aucun import de tête ajouté.

### ✅ Chantier terminé : dispense externe — indicateur visuel (C1-UI) (2026-06-23)

**Contexte :** le justificatif d'une dispense externe s'uploade par un appel SÉPARÉ (`POST /candidats/{sc_id}/dispense-fichier`), APRÈS le save du candidat — l'`sc_id` n'existe pas avant le save, donc impossible d'exiger le fichier comme garde-fou dur au save. Décision : alerte de vigilance NON BLOQUANTE (cohérent avec l'alerte "⚠️ Formation" existante).

**Implémentation (purement template, aucun JS, aucune migration) :**
- `templates/session_detail.html`, cellule TH de la table candidats : pastille ⚠️ ajoutée APRÈS le span "Disp." si `sc.dispense_origine == 'externe' and not sc.dispense_fichier_cle`.
- `title` : "Dispense externe : justificatif manquant (à joindre)".
- `sc.dispense_origine` lisible directement (objet ORM passé au template via `session_candidats`).
- Le span "Disp." existant (`data-action="dispense-fichier-direct"`) reste strictement inchangé.

**Rendu :** externe sans justif → "Disp. ⚠️" ; externe avec justif → "Disp." ; interne → "Disp." (l'alerte ne concerne QUE l'externe).

**Bilan étape C1 (garde-fous dispense externe) — COMPLET :**
- Date obligatoire + contrôle 12 mois → GARANTIS SERVEUR (rejet au save, C1-serveur)
- Justificatif → alerte visuelle ⚠️ non bloquante (C1-UI)
- Réserve : si blocage dur du justificatif souhaité un jour → le poser à la CLÔTURE de session (jalon où l'`sc_id` existe et le dossier doit être complet), pas au save. Chantier à part, seulement si le besoin se confirme.

**RESTE étape C : C2-moteur** — la dispense externe (date saisie + justif) devient une 4e source que `caces_obtenus.py` sait utiliser comme base théorique pour calculer les dates du futur CACES. Morceau délicat (touche au moteur refond), à cadrer à part. À faire à tête fraîche.

### ✅ Chantier terminé : D0 — verrou réglementaire dispense (2026-06-24)

**Règle :** interdire toute modification de la dispense (bool + date + note) d'un candidat si un CACES `statut='valide'` repose dessus. Statut `a_valider` ne bloque pas.

**Implémentation (`app/routers/sessions.py`, route `update_candidat`) :**
- Requête `CacesObtenu` avec `statut=='valide'` sur le couple `(stagiaire_id, session_id)` du candidat.
- Si trouvé : calcul `_dispense_change` (3 champs : bool/date/note) → si changement réel → `HTTPException(409, detail="Un CACES delivre repose sur cette base de dispense. Annulez d'abord le CACES (page CACES obtenus) avant de modifier la dispense de ce candidat.")`.
- `CacesObtenu` déjà importé ligne 16 — aucun import supplémentaire.
- Positionné EN PREMIER dans `update_candidat`, avant toute écriture.

**Note : `a_valider` non bloquant** — délibéré : le CACES n'est pas encore livré, la dispense reste corrigeable.

---

### ✅ Chantier terminé : D1 — override externe dispense (2026-06-24)

**Besoin :** permettre à l'opérateur de forcer `dispense_origine='externe'` même quand une base interne est détectable (ex. CACES d'un autre organisme saisi manuellement = inconnu de la base). Sans override, le serveur choisirait toujours `interne`.

**4 parties dans `app/routers/sessions.py` :**

1. **Schéma `SessionCandidatCreate`** : `dispense_origine_choisie: Optional[str] = None` ajouté après `dispense_date`. Champ optionnel, valeur attendue : `"externe"` ou `None`.

2. **Helper module-level `_appliquer_tracabilite_dispense(sc, data, db, stagiaire_id, famille, session_id)`** (avant `router = APIRouter(…)`) :
   - `not data.theorie_dispensee` → efface origine/source_type/source_id.
   - `data.dispense_origine_choisie == "externe"` → force `externe`, source_type/source_id à None, return.
   - Sinon : appel `detecter_base_theorique` → `interne` si trouvé, `externe` sinon.
   - IDs EXPLICITES en paramètres (add passe `data.stagiaire_id` + `session_id` de route ; update passe `sc.stagiaire_id` + `sc.session_id`). Pas de `source_id` venant du client.

3. **`add_candidat`** : `SessionCandidat(**data.model_dump(exclude={"dispense_origine_choisie"}))` (exclut le champ non-colonne) + `_appliquer_tracabilite_dispense(sc, data, db, data.stagiaire_id, s.famille, session_id)` (remplace l'ancien bloc if/else). Garde-fous date+12 mois inchangés après.

4. **`update_candidat`** : verrou D0 en premier (inchangé) → écriture 3 champs (inchangée) → `_appliquer_tracabilite_dispense(sc, data, db, sc.stagiaire_id, s.famille, sc.session_id)` (remplace l'ancien bloc if/else/else) → garde-fous date+12 mois inchangés.

**Invariants maintenus :** `source_id` jamais du client ; `exclude={"dispense_origine_choisie"}` sur add pour ne pas passer le champ à l'ORM ; verrou D0 en premier dans update ; garde-fous une seule fois par route.

### ✅ Chantier terminé : D2 — UI override externe (2026-06-24)

**Objectif :** permettre à l'opérateur de choisir l'origine en modale candidat (interne détectée vs externe forcée), avec cohérence en édition et avertissement si la date externe est antérieure à la base interne.

**Fichiers modifiés :** `templates/session_detail.html` + `static/js/session_detail.js`

**5 parties :**
1. **HTML** : bloc `#field-dispense-origine` (radios `interne`/`externe` + `#dispense-q2-warning`) inséré entre `#dispense-proposition` et `#field-dispense-date`. Affiché/masqué avec les autres champs dispense.
2. **`_syncDispenseNote`** : affiche/masque `#field-dispense-origine` avec les autres champs dispense.
3. **`_detecterDispense`** : déclare `radioInt`/`radioExt` + reset `window._dispenseDateInterne = null` en tête. Cas `!data.possible` : grise interne, force externe. Cas `data.possible` : active les deux, mémorise `window._dispenseDateInterne = data.date_origine`, pré-coche interne si rien n'est coché (`!radioInt.checked && !radioExt.checked`), puis appelle `_appliquerVisibiliteOrigine()`.
4. **Nouvelles fonctions** : `_appliquerVisibiliteOrigine()` (masque encart proposition si externe choisi, appelle `_verifierQ2`) ; `_verifierQ2()` (avertissement amber si date externe < date interne). Listener `change` sur `dispense-origine` et `sc-dispense-date` dans DOMContentLoaded.
5. **`editerCandidat`** : paramètre `origine` ajouté (7e). `data-dispense-origine="{{ sc.dispense_origine or '' }}"` sur le bouton HTML. Le listener passe `btn.dataset.dispenseOrigine || ''`. La fonction pré-coche la radio AVANT `_detecterDispense()` → la garde `!radioInt.checked && !radioExt.checked` ne re-coche pas interne si externe déjà coché.
6. **`sauvegarderCandidat`** : `dispense_origine_choisie` ajouté au payload JSON via `document.querySelector('input[name="dispense-origine"]:checked').value || null`. Null si rien coché → serveur fait la détection auto (rétrocompat).

### ✅ Chantier terminé : correctifs post-test dispense + override externe (2026-06-24)

**Correctifs UI (suite aux tests) :**
- Proposition de dispense déclenchée dès la **sélection du nom** (avant de choisir "Dispense"), plus seulement au changement du select théorie. `_detecterDispense()` appelée dans `_selectionnerCandidatStagiaire` + à l'ouverture en édition.
- Proposition **persistante en réouverture/édition** : `editerCandidat` pose `window._scStagiaireId` et appelle `_detecterDispense()`.
- `_detecterDispense` affiche la proposition même en mode "À tester" (suggestion, ne coche rien).
- Dates de la proposition au format FR (helper `_dateFr`, JJ/MM/AAAA) au lieu d'ISO.
- **Onglet actif conservé** après reload (`sessionStorage 'sessionDetailTab'` écrit dans `showTab`, restauré au `DOMContentLoaded`) — couvre TOUS les onglets, pas que candidats.
- Lien "Vérifier" de la source R1 (CACES) corrigé : pointe vers `/caces-obtenus` (la carte peut ne pas être émise) au lieu de `/cartes-caces`.

**D0 — Verrou réglementaire (`sessions.py`, `update_candidat`) :**
- Si un `CacesObtenu` `statut='valide'` existe sur `(stagiaire_id, session_id)` ET que la dispense change (bool/date/note différents) → `HTTPException 409` "Annulez d'abord le CACES". En PREMIER, avant toute écriture.
- `'a_valider'` ne bloque PAS (proposition recalculable — fenêtre de correction).

**D1 — Override externe (serveur, `sessions.py`) :**
- Schéma `SessionCandidatCreate` : `+dispense_origine_choisie` (`Optional[str]`, `'interne'`|`'externe'`|`None`).
- Helper module-level `_appliquer_tracabilite_dispense(sc, data, db, stagiaire_id, famille, session_id)` : si choix=`'externe'` → force externe sans pointeur (même si interne existe) ; sinon détection serveur. IDS EXPLICITES en paramètres (`add` : `data.stagiaire_id` + `session_id` route ; `update` : `sc.stagiaire_id` + `sc.session_id`). `source_id` JAMAIS du client.
- `add_candidat` : `SessionCandidat(**data.model_dump(exclude={"dispense_origine_choisie"}))` — exclusion OBLIGATOIRE (champ non-colonne, sinon TypeError ORM).
- Garde-fous date+12 mois inchangés, une seule fois par route.

**D2 — Override externe (UI, `session_detail.html` + `.js`) :**
- Radios "Base interne / Base externe" (`#field-dispense-origine`), visibles quand dispense cochée.
- `_detecterDispense` : mémorise `window._dispenseDateInterne` (pour Q2) ; base trouvée → interne activable + préselectionné si rien coché ; AUCUNE base → interne GRISÉ (`disabled`), externe forcé.
- `_appliquerVisibiliteOrigine` : masque l'encart proposition si externe ; champ date **GRISÉ + pré-rempli** (date détectée) en interne, **ACTIF** en externe (saisie libre).
- `_verifierQ2` : avertissement NON BLOQUANT si externe coché ET date saisie ANTÉRIEURE à la base interne (la plus récente devrait primer). Réactif (au `change` de la radio OU de la date).
- **Cohérence édition** : `editerCandidat` reçoit `data-dispense-origine` (7e param) et pré-coche la radio selon l'origine STOCKÉE avant `_detecterDispense` (la garde `!checked && !checked` préserve le choix). Un externe forcé reste externe à la réouverture.
- `sauvegarderCandidat` : transmet `dispense_origine_choisie` (radio cochée ou `null` → rétrocompat détection auto).

**Règle confirmée :** en interne, la date est INFORMATIVE (le serveur utilise la source détectée, jamais `dispense_date` du client). En externe, date saisie + garde-fous serveur.

**C2 (moteur + socle) → voir section dédiée ci-dessous.**

### ✅ Chantier terminé : modale candidat en lecture seule pour le terrain (2026-06-24)

**Règle :** le terrain peut VOIR et JOINDRE un justificatif de dispense, mais ne peut pas modifier les données du candidat (inscription, dispense, origine, date, note). Le serveur protège déjà (`POST/PUT /candidats` = 403 terrain) — ce chantier aligne l'UI sur cette réalité.

**Implémentation (`static/js/session_detail.js` + `templates/session_detail.html`) :**
- `_appliquerRoleModaleCandidat()` (nouvelle fonction) : si `window.USER_ROLE === 'terrain'`, griser les 6 champs (`sc-stagiaire-search`, `sc-theorie`, `dispense-origine-interne`, `dispense-origine-externe`, `sc-dispense-date`, `sc-dispense-note`), masquer le bouton "Sauvegarder", remplacer "Annuler" par "Fermer".
- Appelée en fin de `editerCandidat` (après `_detecterDispense()`).
- `ouvrirAjoutCandidat` : garde terrain en tête — `afficherErreur` + `return` avant affichage modale (double sécurité, le bouton est déjà masqué).
- Bouton 👥 "ajouter candidat" (`data-action="ouvrir-ajout-candidat"`) enveloppé dans `{% if user_role != 'terrain' %}`.
- Le bouton 📎 "Joindre justificatif" reste actif (route `POST /dispense-fichier` whitelistée terrain).

### ✅ Chantier terminé : ergonomie date dispense + droits terrain (2026-06-24)

**Ergonomie du champ date (`session_detail.js`, `_appliquerVisibiliteOrigine`) :**
- Base interne : champ date GRISÉ (`disabled`) + pré-rempli avec la date détectée (`window._dispenseDateInterne`). Informatif uniquement (le serveur utilise la source détectée, jamais `dispense_date` du client).
- Base externe : champ ACTIF. En basculant interne→externe, le champ se VIDE (la garde `if (champDate.disabled)` ne vide qu'à la transition, pas à chaque refresh → ne détruit pas une saisie en cours). Saisie volontaire assumée : sans date, rejet serveur 400.
- Retour externe→interne : re-grise + re-rempli avec la date détectée.
- Avertissement Q2 (`_verifierQ2`) : si externe coché ET date saisie ANTÉRIEURE à `_dispenseDateInterne` → message orange non bloquant. Réactif (`change` radio OU date).

**Droits TERRAIN sur la dispense (UI uniquement — le serveur protège déjà) :**
- Constat : `POST/PUT` candidat sont DÉJÀ 403 pour terrain (catch-all `_verifier_role`) ; `POST dispense-fichier` est whitelisté terrain ; `DELETE dispense-fichier` réservé back-office. La garantie serveur existait déjà — seule l'UI était incohérente (terrain voyait des champs éditables puis 403 au save).
- Règle métier : le terrain CONSULTE la dispense en lecture seule (voit le "pourquoi") et peut UNIQUEMENT joindre un justificatif manquant. Il ne peut ni inscrire un candidat, ni paramétrer/modifier la dispense.
- `_appliquerRoleModaleCandidat()` (`session_detail.js`) : si `USER_ROLE==='terrain'` → grise `sc-stagiaire-search`, `sc-theorie`, `dispense-origine-interne/externe`, `sc-dispense-date`, `sc-dispense-note` ; masque le bouton Sauvegarder ; renomme Annuler→Fermer. Le bouton 📎 Joindre reste actif (route whitelistée, fonctionne en mode édition car `sc_id` connu → pas de POST candidat). Appelée en fin de `editerCandidat`.
- Garde dans `ouvrirAjoutCandidat` : terrain → message "inscription réservée au back-office" + ne pas ouvrir la modale.
- Bouton 👥 "ajouter candidat" masqué pour terrain (`{% if user_role != 'terrain' %}` dans `session_detail.html`).
- **IMPORTANT :** le 📎 marche pour le terrain UNIQUEMENT en mode édition (`sc_id` existant → saute le POST candidat bloqué, va direct sur `dispense-fichier` whitelistée). En mode ajout le terrain est de toute façon bloqué (inscription back-office only).

**Notice utilisateur "Dispense de théorie" générée (.docx, charte NORYX)** : 8 points (règle 12 mois, proposition, origine interne/externe + override, date, avertissement Q2, justificatif + pastille, verrou CACES délivré, tableau récap). Rôles corrigés : back-office paramètre tout, terrain consulte + justificatif seul.

### ✅ Chantier terminé : dispense externe comme base de calcul CACES (C2) — complet (C2a + C2b + C2c + contrôle date)

**Principe métier validé :** pour une dispense EXTERNE, l'humain RECOPIE les dates du CACES externe (il ne calcule pas). Le candidat obtient la catégorie CHEZ NOUS :
- date d'obtention = date de la pratique réussie chez nous (le moteur la connaît : `SessionEpreuve.date`) — RIEN à saisir.
- date d'échéance = celle qui figure sur le CACES externe, SAISIE à la main par l'opérateur (cas extension ET primo confondus, puisqu'on saisit l'échéance).
- Pas de recherche de théorie interne ; pas de mécanisme deux passes (les dates ne sont pas héritées d'un CACES initial interne).

**C2a — 2 champs (faits, en prod) :**
- `SessionCandidat.dispense_echeance` (Date) — échéance reportée du CACES externe.
- `CacesObtenu.dispense_externe_sc_id` (Integer, FK `session_candidats.id`) — traçabilité POSITIVE : ce CACES est fondé sur la dispense externe de ce `SessionCandidat` (pendant de `resultat_theorie_id` pour l'interne). FK ORM seulement, ALTER SQL = INTEGER sans contrainte (comme `caces_initial_id`).
- Migrations startup `_MIGRATIONS`, vérifiées en prod.

**C2b — saisie échéance (faite) :**
- Schéma `SessionCandidatCreate` : `+dispense_echeance (Optional[date])`.
- `add_candidat` + `update_candidat` : écriture `sc.dispense_echeance = data.dispense_echeance` SI (`theorie_dispensee` ET `origine=='externe'`), sinon `None` (nullifie hors externe).
- Garde-fou serveur : si `origine=='externe'` et pas de `dispense_echeance` → HTTPException 400 (à côté des contrôles date + 12 mois). OBLIGATOIRE comme date+justif.
- Verrou D0 étendu : `dispense_echeance` ajouté à `_dispense_change` (modifier l'échéance d'un candidat à CACES délivré = bloqué 409).
- UI : champ `#field-dispense-echeance` "Date d'échéance (reportée du CACES externe)" visible UNIQUEMENT en mode externe (`_appliquerVisibiliteOrigine` : `block` si externe, `none` si interne ; `_syncDispenseNote` : masque si pas dispense). Transmis au payload `sauvegarderCandidat`. Grisé pour le terrain (`_appliquerRoleModaleCandidat`). Pré-rempli en édition (`editerCandidat` 8e param, `data-dispense-echeance` sur le bouton).

**C2c — intégration moteur (fait, en prod) :**
- `app/services/caces_obtenus.py` : import `SessionCandidat`.
- Dans `_calculer_pour_epreuve`, AVANT la recherche de théorie interne : si le `SessionCandidat` (`session_id`+`stagiaire_id`, actif) est `theorie_dispensee` + `dispense_origine=='externe'` → retourne directement `{date_obtention: ep.date` (pratique chez nous), `date_echeance: sc.dispense_echeance` (saisie), `options_obtenues: ep.options_obtenues`, `post_cloture: False`, `resultat_theorie_id: None`, `theorie_source_id: None`, `dispense_externe_sc_id: sc.id}`. Si `dispense_echeance` manquante → `return None` (sécurité, ne devrait pas arriver vu le garde-fou au save).
- Clé `"dispense_externe_sc_id": None` ajoutée au dict de retour des cas INTERNES (anti-`KeyError` dans `_appliquer_caces`).
- `_appliquer_caces` : écrit `existing/new.dispense_externe_sc_id = calc["dispense_externe_sc_id"]` aux 3 endroits (màj `a_valider`, màj `annule`, création).
- L'externe a `post_cloture=False` → traité en PASSE 1, jamais en passe 2, aucune interaction avec l'héritage d'échéance interne. Cas test validé : base externe 10/01/2026, échéance saisie 14/03/2030, pratique R489 cat5 20/06/2026 → CACES obtention=20/06/2026, échéance=14/03/2030, `dispense_externe_sc_id` rempli.

**C-date — contrôle de cohérence de l'échéance externe (fait, en prod) :**
Référence = `dispense_date` (date de la base externe). N = 10 ans (R482) / 5 ans sinon. Réutilise `_date_echeance(famille, dispense_date)` qui calcule exactement date + N ans − 1 jour (= borne haute).
- **Borne haute (BLOQUANTE, serveur + UI)** : `dispense_echeance` ≤ `dispense_date + N ans − 1 jour`. Au-delà → impossible.
  - Serveur (`sessions.py`, `add_candidat` + `update_candidat`, dans le bloc `origine=='externe'`, après le contrôle échéance obligatoire) : `_borne_haute = _date_echeance(s.famille, data.dispense_date)` ; if `dispense_echeance <= dispense_date` → 400 "doit être postérieure à la date de base" ; if `dispense_echeance > _borne_haute` → 400 "dépasse la durée maximale".
- **Borne basse (AVERTISSEMENT, UI seulement)** : `dispense_echeance` ≥ `dispense_date + (N-1) ans − 1 jour`. En-dessous → suspect non bloquant.
- UI (`session_detail.js`) : helpers `_dateMoinsUnJour(y,m,d)` (gère 29 fév) + `_bornesEcheance(dateBaseIso)` `{haute, basse}` (N selon `SESSION_FAMILLE`). Fonction `_verifierEcheance()` : rouge si ≤ base ou > haute (le serveur refusera), orange si < basse (non bloquant), masque sinon ; actif en mode externe uniquement. Div `#dispense-echeance-warning` sous `#sc-dispense-echeance`. Listeners `change` sur `sc-dispense-date` (+ `_verifierQ2`) et `sc-dispense-echeance` ; appel aussi dans `_appliquerVisibiliteOrigine` et `editerCandidat`. `_isoFromDate(dt)` pour formater les bornes affichées.
- Cohérence : la borne haute UI utilise la MÊME formule que le serveur → l'avertissement rouge apparaît pile quand le serveur rejette.

---

### 🔧 État schéma CacesObtenu (pré-chantier 1 — à ré-arbitrer)

> L'ancien cadrage moteur (modèle « post_cloture / extension par session clôturée / deux passes / écart C ») a été **remplacé par la SPEC MOTEUR unifiée** (voir plus bas + document confidentiel v1.0). L'ancien raisonnement reste dans l'historique git.

**Colonnes réellement présentes sur `CacesObtenu`** (à confronter à la spec unifiée au CHANTIER 1, pas à réutiliser aveuglément) :
- `post_cloture` (Boolean) — ancien déclencheur d'extension. Plus utilisé par la spec unifiée (arbitrage par origine). Probablement à abandonner.
- `resultat_theorie_id` (FK ResultatTheorie, nullable) — théorie ayant fondé le CACES. Utile : détecter une théorie orpheline.
- `caces_initial_id` (FK CacesObtenu auto-réf, nullable) — CACES initial dont une extension hérite l'échéance. Utile : héritage d'échéance.
- `dispense_externe_sc_id` (FK SessionCandidat, nullable) — base externe (cas 0).

**Commits moteur déjà en place** : écart A `1d8a380`, écart B (fenêtre 12 mois sens unique), R1 amélioré `60de332`. À revérifier contre la spec unifiée.
### ✅ Chantier terminé : table générique Justificatif — modèle + routes + permissions (2026-06-22)

**Besoin déclencheur :** justificatif de FORMATION préalable par apprenant (feuille de présence). Le document PEPCI-49-01 impose la conservation des émargements 10 ans + preuve de formation au dossier.

**Implémenté ✅ (backend complet + UI indicateur + menu multi-fichiers) :**
- `app/models/justificatif.py` : modèle ORM (type, session_id, session_candidat_id nullable, fichier_cle/nom/type, date_upload, uploade_par, **libelle** VARCHAR(300) nullable — ajouté post-déploiement via ALTER TABLE)
- `CREATE TABLE IF NOT EXISTS justificatifs` dans `_run_startup_migrations()` (main.py) + import `Justificatif`
- 4 routes dans `app/routers/sessions.py` : `POST /{session_id}/justificatifs` (upload, Form: type + session_candidat_id + **libelle** + fichier), `GET` liste (filtrable, retourne aussi `libelle`), `GET /{justif_id}` (StreamingResponse R2), `DELETE /{justif_id}` (purge R2 + db.delete). Types valides : `formation` / `dispense` / `presence_session` / **`document_session`**.
- `app/services/storage.py` : extensions autorisées élargies à `jpg`, `jpeg`, `png`, `heic` (+ MIME `image/jpeg`, `image/png`, `image/heic`) — profite à tous les types de justificatifs.
- `page_session_detail` (main.py ~l.1794) : calcul groupé anti-N+1 → `sc.passe_epreuve` (bool, stagiaire_id dans candidats_ids d'au moins un JourTest) + `sc.nb_justif_formation` (int, 1 requête groupée par session_candidat_id). Accessible dans le template via `{{ sc.passe_epreuve }}` / `{{ sc.nb_justif_formation }}`.
- Permissions terrain : POST whitelisté dans `_verifier_role` (ligne ~583 main.py) ; DELETE non whitelisté → catch-all → 403 terrain, back-office uniquement
- `session_detail.html` : colonne `FORM.` dans thead (toujours visible) + `<td data-label="FORM.">` dans tbody : badge vert 📋 N si justif présent, badge ambre ⚠️ Formation si 0, `—` gris si candidat ne passe pas d'épreuve. data-action=`justif-formation-menu` sur les deux badges. Mobile : `td[data-label="Actions"]` en footer de carte (`order:5`, `flex-direction:row`, `flex-wrap:nowrap`, fond bleu ardoise pâle `#e8edf5`, `border-radius:0 0 8px 8px`) — label `flex:1 1 auto` à gauche, boutons `flex:0 0 auto` à droite sur une seule ligne. Pastille FORM. "présente" en ardoise `#4a5568` (HTML + `_majPastilleFormation` JS synchronisés).
- `session_detail.js` (fin fichier, IIFE) : menu multi-fichiers `justif-formation-*` — overlay dynamique créé au clic (pas d'input file dans le template), liste via GET, bouton Voir → `window.open`, bouton + Ajouter → input createElement + FormData POST, bouton 🗑️ Supprimer → DELETE (back-office uniquement, corbeille discrète). **Modale reste ouverte** après ajout/suppression ; pastille FORM. mise à jour en direct via `_majPastilleFormation()` (1 GET groupé, pas de reload). Charte NORYX anthracite `#2d2d2d` sur bouton Ajouter et header.


**Modèle décidé : table générique `Justificatif` (multi-fichiers, une ligne par fichier), Option A (un seul modèle, 2 niveaux via nullable) :**
- `id`
- `type` : `'formation'` / `'dispense'` / `'presence_session'` (extensible)
- `session_id` : FK `sessions`, TOUJOURS rempli
- `session_candidat_id` : FK `session_candidats`, NULLABLE (rempli formation/dispense = niveau candidat ; NULL pour `presence_session` = niveau session)
- `fichier_cle` / `fichier_nom` / `fichier_type` : R2
- `date_upload` / `uploade_par` : traçabilité audit

**Purges (pas de FK cascade, manuel) :** hard delete candidat → purger `Justificatif` où `session_candidat_id = X` (+ R2) ; suppression session → purger où `session_id = Y` (+ R2).

**Justificatif FORMATION — comportement :**
- Document(s) par apprenant, indépendant du module formation interne (`JourFormation`). Couvre 80% des cas.
- Permissions IDENTIQUES à la dispense : terrain upload + voit, back-office supprime.
- INDICATEUR tableau candidats : affiché pour tout candidat passant AU MOINS une épreuve (théorie OU pratique inscrite). Dispensé-théorie qui passe la pratique = garde l'indicateur. Candidat ne passant rien = pas d'indicateur.
- Avec justificatif → icône cliquable ouvre le doc. Sans → icône ALERTE FORTE NON BLOQUANTE (le testeur vérifie, décide).
- Multi-fichiers → clic sur l'icône ouvre un MENU (voir fichiers / ajouter) plutôt qu'une action simple. Pas de surcharge de la modale candidat.

**Convergence future :** migrer la dispense (colonnes plates actuelles) vers cette table générique (dette technique assumée). La table prévoit déjà `type='dispense'`.

### ✅ Chantier terminé : onglet "Documents" de session (niveau session)

**5e onglet "📁 Docs."** dans la page session (à côté de Séq./Cand./UT/Mat.). Pattern onglet : bouton `data-tab="documents"` + panneau `id="tab-documents"` + `'documents'` ajouté à la liste EN DUR du `forEach` de `showTab` (3 touches synchronisées obligatoires — sinon la bascule casse).

**Périmètre :** UNIQUEMENT documents niveau session (`type='document_session'`, `session_candidat_id NULL`). Ne mélange PAS les justificatifs candidats (formation/dispense) — décision anti-confusion : justificatifs candidats dans le tableau candidats, documents de session dans l'onglet.

**UI :**
- Zone d'ajout = champ libellé libre + **boutons-puces** (Feuille de présence / VGP / Matériel / Photo / Convention / Autre) qui remplissent le champ au clic — REMPLACENT la `<datalist>` (inopérante sur mobile : s'affiche mais le choix ne s'inscrit pas dans le champ). Champ fichier (`accept` PDF/Word/Excel/images).
- Liste en **cartes flex responsive** (pas de table — débordait sur mobile) ; nom de fichier tronqué sur une ligne (`text-overflow:ellipsis` + `min-width:0` sur le parent + `title` au survol). Badge libellé ardoise `#4a5568`.

**JS :** IIFE dédiée dans `static/js/session_detail.js`. `_docChargerListe` (chargée à l'ouverture de l'onglet via listener `show-tab[documents]`), `_docAjouter` (POST FormData, reset inputs, rechargement liste sans reload), `_docSupprimer` (confirm + DELETE + rechargement). CSP-safe, pas de `location.reload`.

**Permissions :** POST `/justificatifs$` déjà whitelisté terrain ; DELETE `/justificatifs/{id}` → catch-all → back-office only. Bouton 🗑️ visible uniquement si `_docEstBackOffice()` (`role == 'admin' || role == 'utilisateur'`).

---

### ✅ Chantier terminé : suppression des justificatifs par RÔLE (2026-06-23)

**Règle :** "uploadé par le terrain → supprimable par le terrain ; back-office (admin/utilisateur) → accès total à tout". Distinction par RÔLE (pas par personne : un testeur terrain peut supprimer ce qu'un autre testeur terrain a uploadé). Périmètre : table Justificatif (formation + documents de session). La dispense (colonnes plates) suivra à la convergence.

**Matrice :**
| Qui supprime | Fichier 'terrain' | Fichier back-office | Ancien (rôle NULL) |
|---|---|---|---|
| Back-office | oui | oui | oui |
| Terrain | oui | 403 | 403 |

**5 étapes réalisées :**
1. Colonne `uploade_par_role VARCHAR(20)` nullable sur justificatifs (modèle + ALTER startup + CREATE TABLE). En prod (11 colonnes).
2. Upload renseigne le rôle : `uploade_par_role=(user.role if getattr(user,"role",None) else None)` dans le constructeur Justificatif.
3. Route DELETE supprimer_justificatif : `est_back_office = role in ("admin","utilisateur")` ; si pas back-office et `j.uploade_par_role != "terrain"` → 403. Back-office supprime tout sans condition.
4. Middleware `_verifier_role` : `DELETE ^/api/sessions/\d+/justificatifs/\d+$` whitelisté pour terrain (placé APRÈS le POST `justificatifs$`, AVANT le catch-all). Le terrain atteint la route ; la route filtre.
5. Front (2 listes) : `_peutSuppr(j)` (formation) et `_docPeutSuppr(j)` (documents) = `_estBackOffice() || j.uploade_par_role === 'terrain'`. Corbeille affichée selon ce prédicat. `lister_justificatifs` renvoie `uploade_par_role` dans le dict.

**Double sécurité :** affichage front (corbeille conditionnée) + garde serveur (403 dans la route). Un terrain qui forcerait l'API prend 403.
**Valeurs rôle :** `"admin"`/`"utilisateur"` = back-office ; tout le reste = terrain. Via `request.state.user.role` / `data-user-role` côté front.
**Anciens fichiers** (uploade_par_role NULL) : seul back-office peut les supprimer.

---

### ✅ Chantier terminé : réduction des images côté navigateur avant upload (2026-06-23)

**Objectif :** éviter l'explosion du stockage R2 (photos iPhone ~3-5 Mo × centaines de sessions). Réduction AVANT upload = moins de stockage ET upload plus rapide en 4G terrain.

**Fonction commune `reduireImage(file)` (`static/js/session_detail.js`, scope global, ligne 3, async/Promise) :**
- Si pas une image (`file.type` ne commence pas par `'image/'`) → renvoie le fichier inchangé (PDF/Word/Excel passent tels quels).
- Si image : charge dans un canvas, redimensionne à MAX 1600px sur le plus grand côté, re-encode en JPEG qualité 0.8, renomme en `.jpg`.
- Garde-fou : si le blob réduit n'est pas plus petit que l'original (`blob.size >= file.size`) → garde l'original.
- Fallback gracieux : `img.onerror` (HEIC non décodable par le canvas) → renvoie le fichier original sans bloquer.

**Branchement dans les 3 uploads** (`await reduireImage` avant `fd.append('fichier', ...)`) :
- `_uploaderJustif` (dispense) — déjà async
- `_uploaderFormation` (formation) — **passée async** pour l'occasion
- `_docAjouter` (documents) — déjà async

**Résultat typique :** photo iPhone 4 Mo → 200-400 Ko. PDF/Word/Excel intacts.
**Limite HEIC :** un HEIC non décodable part en pleine taille (fallback), pas de blocage. iPhone convertit souvent en JPEG au partage, donc cas rare.

---

### ❌ DÉCISION TRANCHÉE : non-convergence dispense → table Justificatif (2026-06-23)

La convergence du justificatif de dispense vers la table `Justificatif` est **ÉCARTÉE**. La dispense reste en colonnes plates `SessionCandidat` (`dispense_fichier_cle`/`nom`/`type` + `dispense_date` + `dispense_note`) car c'est un objet métier spécifique (date, origine, note) distinct d'un simple fichier. L'export ZIP lit déjà `dispense_fichier_cle` directement depuis `SessionCandidat`. **Ne PAS reproposer ce chantier.**

---

### ⚠️ Corrections couleur NON appliquées (commit 0f74a86 au message trompeur — code jamais modifié)

**LEÇON : ne JAMAIS se fier au message de commit — toujours `grep` sur le fichier réel après modif.**

- **Pastille FORM. "présente" :** encore `#1a7a3a` (vert) dans HTML (`session_detail.html` ~1592) ET JS (`_majPastilleFormation` ~2392). À passer en `#4a5568` (ardoise) aux DEUX endroits (sinon le JS repeint en vert après chaque rechargement).
- **Footer Actions mobile :** boutons crayon+corbeille s'empilent (capture confirmée) au lieu d'être en ligne. Manque `flex-direction:row` + `flex-wrap:nowrap` + groupement. Fond à passer en `#e8edf5` (ardoise pâle).

---

### ✅ Chantier terminé : affichage origine dispense dans CACES obtenus (2026-06-24)

**Backend — `app/routers/caces_obtenus.py`, `_get_theorie_pratique` :**
- Bloc `dispense_info` ajouté : requête `SessionCandidat` (session_id + stagiaire_id du CACES) → expose `{origine, date_base, echeance, justif, sc_id}` ou `None`. Import `SessionCandidat` en tête du fichier.
- Champ `"dispense": dispense_info` dans le `return`, présent dans `/api/caces-obtenus/a-valider` et `/valides`.

**Frontend — `static/js/caces_obtenus.js` :**
- `ligneDispense(co)` : ligne complète "🪪 Dispense" dans les cartes à valider — vert si interne, orange si externe ; date de base, échéance externe, 📎 cliquable si justif / ⚠️ si absent. Retourne `''` si `co.dispense == null` (CACES normaux inchangés).
- `badgeDispense(co)` : badge compact "Disp. int./ext." dans la liste valides. Cliquable si externe + justif.
- `${ligneDispense(co)}` inséré dans `renderCarteAValider` après le bloc Théorie ; `${badgeDispense(co)}` dans `_renderLigne` à côté du nom (div `display:flex` pour préserver l'ellipsis du span nom sans tronquer le badge).

**Justificatif cliquable (CSP-safe) :**
- `data-action="ouvrir-justif-dispense"` sur 📎 et badge externe-avec-justif.
- Listener délégué existant → `window.open('/api/sessions/{session_id_pratique}/candidats/{sc_id}/dispense-fichier', '_blank')` (auth cookie suffit, pas de fetch+blob).

---

### ✅ Chantier terminé : stabilisation parcours dispense en AJOUT candidat — 3 fixes (2026-06-24)

Le champ échéance externe (`#field-dispense-echeance`) avait plusieurs bugs en ajout (`static/js/session_detail.js`) :

**Fix 1 — Reset incomplet (`ouvrirAjoutCandidat`) :**
`ouvrirAjoutCandidat` ne réinitialisait pas l'état dispense → valeurs résiduelles si on éditait un externe puis ouvrait Ajouter. Fix : reset complet (`sc-dispense-echeance`, radios origine décochées, sous-champs masqués, warnings vidés, `window._dispenseDateInterne = null`). Garde terrain conservé après le reset, avant `modal.style.display = 'flex'`.

**Fix 2 — Échéance jamais affichée en externe forcé (`_detecterDispense`) :**
La branche "aucune base trouvée" forçait `radioExt.checked = true` programmatiquement (ne déclenche PAS l'event `change` → listener l.369 muet) mais n'appelait PAS `_appliquerVisibiliteOrigine` → champ échéance restait masqué → save bloqué (échéance obligatoire serveur). Fix : ajout de `_appliquerVisibiliteOrigine()` avant le `return` de cette branche.

**Fix 3 — Échéance prématurée (`_appliquerVisibiliteOrigine`) :**
Le champ apparaissait dès la sélection du stagiaire (hors mode dispense) car `_appliquerVisibiliteOrigine` ne testait que `estExterne`. Fix : condition `(estDispense && estExterne)` — `estDispense = (sc-theorie.value === 'dispense')`.

**Règle finale :** champ échéance visible UNIQUEMENT si dispense sélectionnée ET origine externe cochée. Cohérent avec `_syncDispenseNote` (masque si `!isDispense`, l.807) et `editerCandidat` (affiche si `theorie_dispensee && origine === 'externe'`, l.993). `_appliquerVisibiliteOrigine` est le seul point d'affichage du champ → couvre tous les chemins (sélection stagiaire, changement origine, branche aucune-base, édition).

---

### ✅ Module REPRISE D'HISTORIQUE — H1+H2+H5 terminés (H3/H4 à venir)

**Besoin :** à la bascule vers NORYX sans reprise auto de l'historique, permettre de saisir les CACES déjà obtenus chez PEPCI pour qu'ils soient exploités par le moteur (dispense interne, extension) et figurent sur les cartes rééditées (doc PEPCI §6).

**Principe : historique "vivant" en base.** Un CACES repris = un CacesObtenu réel que le moteur traite comme un natif.

**Décisions clés verrouillées :**
- **Numéro** : un CACES repris N'A PAS de numéro NORYX (`numero_ordre` reste NULL pour TOUJOURS). Il a son `ancien_numero` PEPCI (audité, déjà sur le certificat du titulaire). Règle d'affichage PARTOUT : `ancien_numero` si présent, sinon `numero_ordre` formaté. Le moteur lit les DATES, jamais le numéro.
- **Session technique** : les enregistrements repris sont rattachés à une `Session` `type='reprise'` (1 par candidat, référence `"REPRISE-{stagiaire_id}"`, `famille="REPRISE"` sentinelle, `lieu_id=0`, `statut="terminee"`). Invisible des listes opérationnelles (filtre `(type != 'reprise') | (type IS NULL)` — le OR NULL est OBLIGATOIRE car les anciennes sessions ont `type NULL`, sinon elles disparaîtraient).
- **Marqueur repris** = `ancien_numero` rempli + rattachement session technique (pas de flag dédié).
- Le moteur `calculer_et_synchroniser` est PUREMENT ADDITIF (ne supprime rien) → un CACES repris `valide` survit sans risque.

**H1 — fondation (commit c10c15d) :**
- `CacesObtenu.ancien_numero` (String(50), nullable) + migration startup.
- `app/services/reprise_historique.py` : `get_or_create_session_reprise(stagiaire_id, db)` → cherche/crée la session technique du candidat (idempotent).
- Filtres `(type != 'reprise') | (type IS NULL)` dans `main.py` l.1165 (liste sessions), `sessions.py` l.183 (search) + l.191 (liste API).

**H2a — backend (commit ab811c7, `app/routers/stagiaires.py`) :**
- `GET /{id}/reprises` : liste les CACES repris du candidat (lookup session technique SANS création → `[]` si absente).
- `POST /{id}/reprises` : crée un CACES repris sous PIN admin. Schéma `CacesRepriseCreate` (famille, catégorie, options, date_obtention, date_echeance, ancien_numero, testeur_id, pin). Crée DEUX enregistrements : `CacesObtenu(statut='valide', numero_ordre=None, ancien_numero rempli, session technique)` + `SessionEpreuve(obtenue=True, testeur_id)` — la SE porte le testeur (lu via SE comme pour un natif). Gardes : PIN (403), `date_echeance > date_obtention` (400), 409 si catégorie déjà reprise (contrainte UNIQUE stagiaire+session+catégorie → 1 repris par catégorie).

**H2b — UI (commit 4b1ef5f) :**
- `stagiaires.js` : section "🪪 Historique repris" dans l'accordéon (`renderReprisesHistorique`, 4e fetch `/reprises`) + bouton "+ Ajouter".
- Modale `#modal-reprise` (`stagiaires.html`) : selects famille (injectée via `data-familles` depuis le contexte `page_stagiaires` → `familles_reprise`) + catégorie (cascade fetch `/admin/categories/{fam}`) + testeur (fetch `/api/testeurs/` tous actifs, PAS filtre habilités car historique) + dates + `ancien_numero` + PIN. `ouvrirModalReprise` / `confirmerAjoutReprise`. Après ajout : invalide `body.dataset.loaded` + retoggle l'accordéon.
- `page_stagiaires` (`main.py`) : charge les familles actives → contexte `familles_reprise`.

**H5 — affichage `ancien_numero` partout (commits 28c99d5, 46c36ab, 56c69b7) :**
Règle appliquée : `ancien_numero` sinon `numero_ordre` formaté. Zones :
- Tableau sélection carte : `cartes_caces.py` `get_caces_valides` (`+ancien_numero` au dict) + `cartes_caces.js` l.350.
- Historique stagiaire : `stagiaires.py` `get_caces_valides_stagiaire` (`+ancien_numero`) + `stagiaires.js` `renderCacesValides` (l.364) + `chargerCacesCarteStag` (l.492).
- Carte imprimée : snapshot `caces_json` d'`emettre_carte` (`+ancien_numero` figé → carte émise garde le bon numéro pour toujours, rétrocompat : vieux snapshots sans `ancien_numero` retombent sur `numero_ordre`) + `_render_cr80_html` recto (l.512, filtre ÉLARGI à `ancien_numero OR numero_ordre` pour ne pas exclure les repris) + verso (l.555) + `cartes_caces.js` 4 points (l.522 réimpression, l.572 recto `numsCaces` `.map` avant `.filter(Boolean)`, l.601 verso, l.812 vue A5).
- Page CACES obtenus (H5-1c) : `caces_obtenus.py` `_enrich_base` (`+ancien_numero`, partagé a-valider+valides) + `caces_obtenus.js` `_renderLigne`. Affichage du numéro repris correct PARTOUT : sélection carte, historique stagiaire, carte imprimée (snapshot+recto/verso), CACES obtenus.

**RESTE (H3/H4/divers) :**
- H3 : théories orphelines reprises (`ResultatTheorie` créé à la main → POINT DÉLICAT : `jour_test_id` + `session_id` obligatoires → rattacher à la session technique, mais `ResultatTheorie` a besoin d'un `jour_test_id` → créer un `JourTest` technique dans la session reprise ?).
- H4 : pratiques orphelines reprises (`SessionEpreuve` seule, sans CACES — pour les pratiques en attente de théorie).
- Vérifier autres vues affichant le numéro d'un CACES (page CACES obtenus : un repris valide y montrerait-il `'—'` ? à contrôler).
- Suppression d'un CACES repris (DELETE) : non encore fait — règle : supprimable seulement si pas sur une carte émise ET pas référencé comme `caces_initial_id` par une extension.

### ✅ Chantier terminé : amélioration moteur — source R1 de detecter_base_theorique (2026-06-25)

**Fichier :** `app/services/caces_obtenus.py`

**Nouvelle fonction `_date_initiale_depuis_echeance(famille, date_ech)` (l.18–32) :**
Miroir exact de `_date_echeance` : `echeance = date_obt + N ans − 1j` ↔ `date_obt = echeance − N ans + 1j`. Même N par famille (10 ans R482, 5 ans sinon), même gestion 29 février (fallback 1er mars année−N). Permet de remonter à la date de théorie initiale depuis n'importe quel CACES (initial ou extension, les deux ayant la même échéance si liés).

**Modification source R1 de `detecter_base_theorique` :**
- Avant : filtre `post_cloture == False` (extensions exclues) + test `limite_12_mois(c.date_obtention)` + candidate.date = `date_obtention`.
- Après : filtre `post_cloture` supprimé (initiaux ET extensions inclus) + `date_initiale = _date_initiale_depuis_echeance(c.famille, c.date_echeance)` + test `limite_12_mois(date_initiale)` + candidate.date = `date_initiale`. Skip si `date_echeance` NULL.

**Pourquoi :** une extension hérite l'échéance de son CACES initial → `_date_initiale_depuis_echeance(echeance_extension)` retombe exactement sur la date du CACES initial, qui est la vraie date de théorie. Exclure les extensions de R1 était donc FAUX : un candidat avec une extension récente (théorie < 12 mois) ne voyait pas de base proposée.

**Invariant :** `post_cloture == False` subsiste uniquement à la l.256 (passe 2 de `calculer_et_synchroniser`, recherche du CACES initial pour hériter l'échéance — légitime et non touché).

---

### ✅ H3/H4 — orphelines reprises + exclusivite affinee (TERMINE, en prod)

**Besoin :** candidat ayant passé UNE seule épreuve chez PEPCI (théorie OU pratique), vient passer l'AUTRE chez NORYX → le moteur recombine en CACES (flux normal).

**Architecture :**
- Sessions receptacles orphelines : reference "REPRISE-{id}-{famille}" (tiret + famille), Session.type='reprise', Session.famille=famille reelle (le moteur filtre par famille). DISTINCTE de la sentinelle CACES complets "REPRISE-{id}" (sans famille).
- helper get_or_create_session_reprise(stagiaire_id, db, famille="REPRISE") : famille optionnelle. Defaut → sentinelle H2. famille reelle → receptacle orpheline.

**Backend (app/routers/stagiaires.py) :**
- Schemas TheorieRepriseCreate (famille, date_obtention, testeur_id, pin), PratiqueRepriseCreate (+ categorie, options_obtenues).
- POST /{id}/reprises/theorie : PIN admin → 3 gardes → JourTest technique (type='theorie', grille_id=None) + flush + ResultatTheorie(obtenue=True, mode='degrade', testeur_id).
- POST /{id}/reprises/pratique : PIN admin → 3 gardes → SessionEpreuve(obtenue=True, testeur_id, famille, categorie, options).
- GET /{id}/reprises/orphelines : {theories, pratiques} des receptacles (filtre reference.like("REPRISE-{id}-%")).

**REGLE D'EXCLUSIVITE — tableau des 6 gardes (VERROUILLE, ne pas re-elargir) :**

Principe directeur : theorie = par FAMILLE (commune a toute la famille), pratique = par CATEGORIE. L'exclusivite croisee (theorie<->pratique) ne joue QU'ENTRE DEUX REPRISES (sessions receptacles, sess.id), JAMAIS contre une epreuve NATIVE NORYX (une orpheline reprise doit pouvoir se recombiner avec une epreuve native — c'est le but). Les doublons (theorie<->theorie, pratique<->pratique meme cat) couvrent native ET reprise.

| Route | Garde | Filtre | Portee |
|---|---|---|---|
| theorie | 1 | CacesObtenu.famille + ancien_numero | CACES complet repris (famille) → bloque |
| theorie | 2 | JOIN SessionModel.famille == famille, obtenue=True | doublon theorie (native OU reprise) → bloque |
| theorie | 3 | SessionEpreuve.session_id == sess.id, obtenue=True | pratique orpheline REPRISE seulement (croise) → bloque |
| pratique | 1 | CacesObtenu.famille + categorie + ancien_numero | CACES complet repris (MEME categorie) → bloque |
| pratique | 2 | ResultatTheorie.session_id == sess.id | theorie orpheline REPRISE seulement (croise) → bloque |
| pratique | 3 | SessionEpreuve.famille + categorie + obtenue | doublon pratique MEME categorie (native OU reprise) → bloque |

Cas legitimes qui DOIVENT passer (ne jamais re-bloquer) : theorie native R482 + pratique cat F → ajouter pratique orpheline cat A (la theorie famille couvre toutes les categories) ; pratique native + theorie orpheline meme famille. Seul vrai blocage croise : theorie orpheline REPRISE + pratique orpheline REPRISE meme categorie = CACES complet deguise (a saisir en H2).

Regle reglementaire sous-jacente : une epreuve SEULE passee dans un autre organisme n'est JAMAIS reconnue/transferable (seul un CACES complet l'est). Donc une orpheline reprise est TOUJOURS de l'historique INTERNE pre-NORYX → pas de condition de date dans les gardes.

**Moteur (app/services/caces_obtenus.py) — amelioration R1 :**
- _date_initiale_depuis_echeance(famille, date_ech) : miroir EXACT de _date_echeance. date_obt = echeance - N ans + 1j (N=10 R482 sinon 5). Retrouve la date du CACES INITIAL (initial OU extension qui herite de l'echeance de l'initial).
- detecter_base_theorique source R1 : post_cloture==False RETIRE (extensions incluses) ; dispense testee sur date_initiale calculee. Reste informatif (l'operateur tranche les cas limites). post_cloture==False subsiste seulement en passe 2 de calculer_et_synchroniser (non touche).

**Frontend (static/js/stagiaires.js + templates/stagiaires.html) :**
- renderHistoriqueDeReprise(reprises, orphelines, id) : bloc repliable "🗂️ Historique de reprise" (anthracite #2d2d2d, fleche ▶, replie par defaut, data-action="toggle-historique-reprise") enveloppant les 2 sous-sections : "🪪 Historique repris" (CACES complets, violet #7b1fa2) + "🧩 Orphelines reprises" (ambre #e65100, sous-blocs 🎓 Theories / 🔧 Pratiques).
- Modale #modal-orpheline : choix theorie/pratique puis formulaire adapte (categorie+options masques pour theorie). Boutons "+ Ajouter" harmonises.

**RESTE :**
- Tests de recombinaison approfondis (theorie orpheline + pratique NORYX → CACES flux normal ; et inverse). Pas encore fait de bout en bout.
- DELETE orpheline : non code.
- Responsivite : reportee a la toute fin.

Commits : H3 (20c8f34, c9245d1), H4 (2520e55), moteur R1 (60de332), GET orphelines (ff5baa6), UI-1/UI-2, gardes elargis puis affines (33fcbe3, 5308acf), UI groupee (ca07e8a), libelle bouton (53af4c2).

---

### 📐 SPEC MOTEUR CACES — modèle unifié (VERROUILLÉ 2026-06-26, NE PAS RE-DÉBATTRE)

> **SOURCE DE VÉRITÉ = document confidentiel « Spécification du moteur de calcul CACES® » v1.0** (hors repo, charte NORYX, 15 p.). En cas de divergence, **le document fait foi**. Ce bloc est le condensé opérationnel pour coder et vérifier sans rouvrir le document.

**PRINCIPE CARDINAL** : NORYX propose (`a_valider`), l'opérateur valide (`valide`, figé). Aucune émission automatique.

**LA BRIQUE** : toute catégorie = couple (théorie × pratique), même implicite.
- Brique pratique = pratique réussie LA PLUS RÉCENTE de CETTE catégorie (catégories indépendantes).
- Brique théorique = base LA PLUS FAVORABLE (= origine la plus récente) parmi les bases VIVANTES.
- date_obtention = max(date pratique retenue, date origine de la brique théorique).
- date_echeance = **héritée** si base = CACES (zéro calcul) ; **calculée** `origine + N − 1j` si base = théorie.
- N = 10 (R.482) / 5 (autres). Inverse : `origine = échéance − N ans + 1j` (miroir strict, gestion 29 fév identique).

**INVARIANT N°0 — PORTIER DES 12 MOIS (surplombe tout, zéro exception)** :
Les 2 briques d'un couple doivent être à < 12 mois l'une de l'autre, quel que soit l'ordre. Sinon brique morte, couple refusé. Vaut PARTOUT, même en session unique (une session de 2 ans ne dispense JAMAIS du délai). Le portier conditionne UNIQUEMENT le rôle de base, JAMAIS la présence d'un CACES valide sur la carte.

**ARBITRAGE BASE THÉORIQUE** : (1) filtrer = ne garder que les bases vivantes (théorie < 12 mois de la pratique ; CACES dont origine reconstituée < 12 mois). (2) arbitrer = origine la plus récente gagne. Gagnante théorie → échéance calculée ; gagnante CACES → échéance héritée. Théories empilées → la plus récente.

**TABLEAU DES CAS** :
| # | Situation | Obtention | Échéance | Réf PEPCI |
|---|---|---|---|---|
| 1 | Théorie + pratique même jour (même session) | date pratique | calculée | Q7 |
| 2 | Même session, théorie AVANT pratiques | date de chaque pratique | calculée par cat | Q8.1 |
| 3 | Même session, théorie APRÈS pratiques | date théorie (commune) | calculée depuis théorie | Q8.3 |
| 4 | Sessions diff., théorie antérieure, 1 pratique | date pratique | calculée depuis pratique | Q8.2 |
| 4bis | Sessions diff., pratique antérieure, théorie postérieure | date théorie (dernière brique) | calculée depuis théorie | sym. Q8.3 |
| 5 | Sessions diff., théorie antérieure, PLUSIEURS pratiques | date de chaque pratique | 1er calculé → suivants HÉRITENT | Q8.1+Q9 |
| 6 | Extension via CACES de base (autre cycle, vivant) | date nouvelle pratique | héritée du CACES de base | Q9 |
| 8 | Théorie + récente orpheline ET vivante dispo | max(pratique, théorie) | recalculée sur théorie récente (favorable) | principe |
| 9 | Ajout d'une OPTION à une catégorie déjà possédée | héritée de la cat support | héritée de la cat support | chap. 6bis |

**SOUS-CAS ABSORBÉ (ex-cas 7)** : repassage pratique d'une cat déjà couverte = cas 6 (extension sur base éligible). Obtention màj, échéance héritée (« ne pousse pas la date »). N'arrivera jamais mais NE DOIT PAS PLANTER.

**PRIORITÉ** : cas 8 (théorie orpheline récente vivante) l'emporte TOUJOURS sur l'héritage 5/6, sous réserve du portier.

**PREMIER CRÉE / SUIVANTS HÉRITENT** (cœur cas 5) : 1er CACES du paquet (obtention la + ancienne) = échéance calculée → suivants héritent de SON échéance. SAUF si théorie + récente orpheline et vivante déplace la base (cas 8). C'est ce qui impose le garde-fou 2.

**OPTIONS (chap. 6bis)** : attribut d'une catégorie, jamais autonome. (1) rattachement obligatoire à une cat support préexistante (CACES de base ou pratique validée). (2) AUCUNE date propre → hérite obtention+échéance de la cat support. (3) preuve = épreuve pratique passée AVEC l'option (jamais administratif). (4) si différée, portier 12 mois sur le CACES support. Le moteur de dates ne calcule rien de spécifique : il vérifie la légitimité du rattachement.

**PROVENANCE (3 types, 2 droits)** :
- NORYX natif → sur carte OUI ; base OUI si portier.
- Repris d'avant-NORYX, MÊME OF → sur carte OUI (c'est son CACES) ; base OUI si portier ; traité comme natif.
- Externe, AUTRE OF (cas 0) → sur carte **JAMAIS** (on ne certifie pas ce qu'on n'a pas testé, Q3) ; base OUI si portier ET **acceptation opérateur obligatoire**. Base potentielle INVISIBLE.

**GARDE-FOUS** :
- **G1 saisie** : bloquer (409) épreuve datée AVANT un CACES VALIDÉ/figé de la famille. Autoriser si `a_valider` (recompose). Pas de blocage en session unique ouverte. Msg : « épreuve antérieure à un CACES déjà délivré — annulez d'abord le CACES concerné. NORYX ne rattrape jamais automatiquement. »
- **G2 émission** : sessions différentes → émission forcée du + ancien au + récent. Bloquer validation tant qu'un CACES antérieur (même candidat/famille/base) est `a_valider` (les suivants héritent du 1er). Msg : « validez d'abord le CACES catégorie X (plus ancien). »
- **Même session ouverte** : recomposition libre, rien figé, recalcul initiaux groupés. Pas d'ordre forcé.
- **Émis = intouchable** : correction = annulation + réémission nouveau numéro (Q5/Q6).

**ÉTAT IMPLÉMENTATION** :
- CHANTIER 1 — extension via CACES existant (échéance héritée) : FAIT + testé OK — commit 42ea39f (`app/services/caces_obtenus.py`).
- CHANTIER 2 — G1 anti-incohérence saisie (épreuve antérieure à un CACES valide inter-sessions, même famille) : FAIT — commits 92a2527 + e634c3c (`app/routers/sessions.py`).
- CHANTIER 3 — G2 ordre de validation (base théorique partagée : même théorie fondatrice ou même `caces_initial_id`) : FAIT + testé OK — commit 61ec4ee (`app/routers/caces_obtenus.py`).
- CHANTIER 4 — fiabilité liens `caces_initial_id` / `resultat_theorie_id` : vérifié par lecture (3 branches `_appliquer_caces`, réécriture systématique sur `a_valider`, pas de cache obsolète). Inspection des données réelles non faite (base dev jetable).
- SÉLECTION THÉORIE — la plus récente toutes sources (P1 même session / P2 autre ouverte / P3 autre clôturée) + portier 12 mois appliqué AUSSI à la même-session : FAIT — commit f4f1c27 (`_calculer_pour_epreuve`, arbitrage par date inter-branches).
- ARBITRAGE théorie-vs-CACES : SANS OBJET — un CACES de base ne peut avoir une origine plus récente qu'une théorie vivante (il en découle). Le greffe séquentiel (théorie d'abord, CACES sinon) est correct. Pas de chantier à ouvrir.
- AFFICHAGE — `_get_theorie_pratique` (router) lit `resultat_theorie_id` stocké au lieu de recalculer : FAIT — commit e6286c6 (fin de la cascade dupliquée, convergence dispense/théorie).
- CHANTIER 5 — suppression reprises (3 routes POST + UI) : FAIT — commits a666f69, b0cccef, 354fd57, 4ed7102.
  - `POST /stagiaires/{id}/reprises/pratique/{ep_id}/supprimer` — supprime `SessionEpreuve` orpheline (session REPRISE-{id}-{famille}) ; bloqué si CACES valide associé.
  - `POST /stagiaires/{id}/reprises/theorie/{rt_id}/supprimer` — supprime `ResultatTheorie` orpheline (+ `JourTest` si dernier) ; bloqué si CACES valide lié à ce résultat théorie.
  - `POST /stagiaires/{id}/reprises/caces/{co_id}/supprimer` — supprime CACES repris (`ancien_numero` requis, session sentinelle REPRISE-{id}) + ses `SessionEpreuve` ; bloqué si extension valide dérivée.
  - UI : modal `#modal-suppr-reprise` (PIN, erreur inline) ; bouton "Supprimer" sur chaque ligne CACES repris + théorie orpheline + pratique orpheline ; 3 handlers dans listener délégué (`ouvrir-suppr-reprise`, `suppr-reprise-annuler`, `suppr-reprise-confirmer`).
  - Sécurité : PIN jamais dans l'URL (body JSON `{ pin }`), `SuppressionData(BaseModel)`.
- CHANTIER 6 — cas 5 : extension avec théorie native (branche `else` de `_calculer_pour_epreuve`) : FAIT — commit 609d81e.
  - Si théorie ≤ pratique ET pas post_cloture : cherche un CACES de base autre-session dont l'origine reconstituée est dans la fenêtre 12 mois ET ≤ date théorie.
  - Si trouvé → retourne extension (`post_cloture=True`, `caces_source_id`, échéance héritée). Sinon → cas 2 pur (calcul normal).
- CHANTIER 7 — affichage dispense implicite pour extensions cas 5/6 : FAIT — commit fc175b0 (`app/routers/caces_obtenus.py`), puis corrigé commit 724d4e8.
  - Fallback dans `_get_theorie_pratique` : si `dispense_info is None` et `co.caces_initial_id` rempli, construit une dispense à partir du CACES de base.
  - Origine DYNAMIQUE (fix 724d4e8) : `_est_ext = bool(_base.organisme_externe)` → `"externe"` si le CACES de base est externe, `"interne"` sinon. L'ancien code hardcodait toujours `"interne"` même pour un CACES de base externe.
  - Affiché par `ligneDispense()` JS avec badge interne (vert) ou externe (orange) selon l'origine.
- RESTE À FAIRE — Options (cas 9 / chap. 6bis) : règles verrouillées dans la spec, implémentation NON CODÉE.
- `detecter_base_theorique` (suggestion UI) : R1 amélioré FAIT — commit 60de332.

---

### ✅ Chantiers UX terminés (2026-06-25 / 2026-06-26)

#### CACES® Obtenus (`caces_obtenus.js` + `caces_obtenus.html`)

- **Cartes à-valider repliées par défaut** : corps `#caces-card-body-{id}` en `display:none` au rendu initial ; chevron `▶`/`▼` placé en premier enfant du header (`margin-right:8px`) ; toggle via `data-action="toggle-caces-card"` — commit `ece56bd`.
- **Colonne N° adaptative** : `_formatNo(co)` = `ancien_numero || numero_ordre.padStart(4,'0') || '—'` ; `_wNo = max(56, _noMax*9+20)+'px'` calculé sur le max des valeurs rendues ; signatures `_renderHeaderValides(wNo)` et `_renderLigne(co,idx,wNo)` — commits `20df44d`, `ac595cd`.
- **Colonne Stagiaire max-width** : `_colBaseStyle` branche flex → `max-width:300px` ; `_renderLigne` div Stagiaire → `max-width:300px;overflow:hidden` — commit `5a20093`.
- **Champ de recherche CACES validés** : `class="search-input"` + `🔍` dans placeholder, wrap `.toolbar/.toolbar-left` ; listener sur `#recherche-valides` filtre les lignes via `data-search` (nom+prénom+famille+catégorie+n°+dates, normalize NFD) — commits `5a20093`, `9a4abf5`.

#### Cartes CACES® (`cartes_caces.js` + `cartes_caces.html`)

- **Autocomplete stagiaire** : remplace `<select id="sel-stagiaire">` par `input#sel-stagiaire-input` + dropdown `#sel-stagiaire-list` ; `_stagiairesParNom` dict keyed `nom+prenom` → `[{id,ddn}]` (support homonymes avec section DDN) ; listeners `input`/`click`/`document.click` — commit `3b21b7f`.
- **Champ de recherche Cartes émises** : `class="search-input"` + `🔍` ; `var _emiseFilter` persiste à travers les tris ; filtre dans `_renderTableEmises()` après le sort — commit `5873784`.
- **Toggle oeil Cartes émises** : `var _emiseShowAll = false` ; par défaut seules les cartes `statut==='emise'` sont affichées ; `#chk-emises-all` + `#lbl-emises-all` ; listener `change` met à jour `_emiseShowAll` + style actif bleu — commit `88537fa`.

#### Sessions (`sessions.html`)

- **Responsive — label STATUT masqué** : retrait de `data-label="Statut"` sur `td.ses-statut` → le pseudo-élément `::before` ne génère plus "STATUT" dans la barre bleue — commit `bb43e9f`.
- **Responsive — date clôture terrain masquée** : `.table-sessions .cloture-terrain-date { display:none }` dans `@media (max-width:1023px)` — commit `8eb7eb0`.
- **Badges raccourcis** : "Validée terrain" → "🔒 terrain" (commit `f530242`) puis "fin terrain" (commit `369d46e`) ; "Clôturée" → "Close" — commit `369d46e`.
- **Toggle sessions Clôturées** : `data-statut="cloturee"` sur les `<tr>` Jinja ; par défaut masquées (`filtrer()` appelé au chargement) ; `#chk-cloturees` + `#lbl-cloturees` (oeil) dans toolbar ; `filtrer()` gère le filtre texte ET l'état oeil — commit `c88696d`.
- **Responsive toolbar** : `@media (max-width:767px)` → `.toolbar-left { display:flex; gap:8px }` + `#search { flex:1; min-width:0 }` pour garder l'oeil sur la même ligne que la recherche — commit `ea71007`.

#### Stagiaires (`stagiaires.js` + `stagiaires.html` + `main.py`)

- **Toggle stagiaires inactifs** : `main.py/page_stagiaires` calcule `actifs_ids` (stagiaires dans ≥1 session `statut NOT IN ['terminee','annulee']`) via jointure `SessionCandidat⋈Session` ; `data-inactif="1"` sur les `<tr>` hors actifs ; par défaut seuls les actifs sont visibles ; `filtrer()` extrait (remplace le listener inline) gère texte + oeil ; `#chk-inactifs` + `#lbl-inactifs` — commit `be7df80`.
- **Responsive toolbar** : même correctif `flex:1` sur `#search` — commit `3771034`.

### ✅ Chantiers terminés (2026-06-27)

#### Toolbar sticky (recherche/œil/création figée au scroll)

- **Classe opt-in `.toolbar-sticky`** ajoutée dans `static/style.css` (commit `fc6b5e8`) : `position:sticky`, fond `var(--bg, #f5f6fa)`, `margin:0 -32px` (déborde le padding `.content`), `@media (max-width:1023px)` → `margin:0 -16px`.
- **Correctif calage sous topbar** (commit `16b1720`) : la `.topbar` étant elle-même `sticky top:0 z-index:50`, la toolbar se figeait derrière. Corrigé en `top:64px` (hauteur topbar) + `z-index:49` (sous la topbar).
- **Activée sur stagiaires + sessions** (`fc6b5e8`), puis **non-conformités** (`30ea201`, qui retire aussi le `<h1>` interne « Journal des non-conformités » faisant doublon avec le titre topbar).
- `.toolbar` reste partagée par 6 pages : approche opt-in retenue (pas de sticky global) car cartes-caces/caces-obtenus ont une toolbar imbriquée dans une `.card` avec onglets (à cadrer séparément si besoin).

#### Dashboard — onglet « À traiter » toujours replié au démarrage

- `static/js/dashboard.js` (commit `94cb63b`) : boucle SECTIONS force `var ouvert = false` au lieu de lire `localStorage` → les 5 sous-sections sont systématiquement repliées à chaque chargement (déterministe, ignore l'historique). Le toggle au clic reste fonctionnel pour la session. **Boucle CARTES non touchée** (garde sa restauration localStorage).

#### Non-conformités — refonte ligne + filtres (`non_conformites.html` + `non_conformites.js`)

- **Drapeau 🚩 repositionné** (commit `53a6b63`) : déplacé d'entre nature/statut vers une colonne dédiée 22px entre la flèche ▶ et la référence. Grille passée de 8 à 9 colonnes (`20px 22px 120px 100px 1fr 120px 150px 130px 100px`) sur header + ligne. `.nc-flag-cell` toujours présent (vide si pas de `session_id`) pour garder l'alignement. Mobile : retrait du `margin-left:auto` qui le poussait à droite.
- **Titre en pleine largeur** (commits `a8aba07`, `2d46c81`) : colonne « Titre » retirée du header de tri (le champ recherche couvre déjà le titre) → grille à 8 colonnes (`1fr` retiré). La cellule titre (`.nc-titre-fullrow`) est **déplacée en dernier enfant de la grille** (après le badge statut) avec `grid-column:1/-1` → toutes les colonnes restent ligne 1, titre seul ligne 2. CSS dans `@media (min-width:768px)` uniquement (mobile inchangé). `padding-left:50px` pour aligner sous la référence. JS de tri inchangé et défensif (`if (arrowEl)`), `attrMap.titre` devenu inutilisé sans danger.
- **Œil filtre statut** (commit `a480501`) : `#chk-toutes-nc` + `#lbl-toutes-nc` à côté de la recherche (pattern stagiaires). Œil fermé (défaut) = NC non soldées (`ouvert` + `en_cours`) ; œil ouvert = tout. Fonction unique `appliquerFiltresNC()` combine recherche (`data-search`) ET statut (`data-statut`) — les deux filtres ne se marchent plus dessus. Couleur active harmonisée bleu clair `#e3f2fd`/`#1565c0` (commit `9252227`, identique stagiaires/cartes).
- **Message liste vide** (commit `02de60c`) : si le filtrage masque toutes les cartes (et qu'il y a des NC en base), affiche `#nc-filtre-vide` contextuel — « Aucune non-conformité non soldée… » (œil fermé) ou « …ne correspond à la recherche » (œil ouvert). Le message serveur `{% if not non_conformites %}` (aucune NC en base) reste indépendant.
- **Recherche flex responsive** (commit `9252227`) : `@media (max-width:767px)` → `.toolbar-left {display:flex; gap:8px}` + `#nc-search {flex:1; min-width:0}` pour garder l'œil sur la même ligne que la recherche.

#### CACES® Obtenus — cartes mobiles, filtre année, DDN (`caces_obtenus.js` + `caces_obtenus.html` + `style.css`)

- **Cartes mobiles pliables** (commit `094411b`) : en dessous de 1024px le tableau `.co-scroll-wrap` est masqué et `.co-cards-wrap` (accordéon) prend le relais. CSS dans `style.css` : `.co-scroll-wrap` et `.co-cards-wrap` togglés via `@media (max-width:1023px)`. `_renderValides` génère désormais les deux blocs ; `_renderCarteValide(co)` fabrique chaque carte pliable (chevron `▶`/`▼`, `data-action="toggle-caces-valide"`). Tri desktop only (boutons `▲`/`▼` absents des cartes).
- **Filtre par année** (commit `43537e1`) : toolbar `.toolbar-left` enrichie d'un toggle critère (📅 Obtention / ⏳ Échéance, style radio bouton) et d'un `<select id="filtre-annee">`. État : `_critereValides` + `_anneeValides` (défaut = année en cours). `data-annee-obt` et `data-annee-ech` portés sur les lignes tableau ET les cartes. `_peuplerMenuAnnees()` collecte les années présentes selon le critère actif. `appliquerFiltresValides()` combine recherche texte + filtre année, appelée après chaque render. Hauteurs toolbar uniformisées à 39px (commit `5214660`). Menu année compact sur petit écran `<768px` via `@media` (commit `024b8af`).
- **Classe `.co-hidden`** (commit `002419c`) : le filtre utilisait `row.style.display='none'` ce qui écrasait le `display:flex` inline des corps de cartes. Corrigé par `row.classList.toggle('co-hidden', !ok)` + règle CSS `.co-hidden { display:none!important }` ajoutée dans `style.css`.
- **DDN sous le nom** (commit `6557dbd`) : dans `_renderLigne`, la cellule Stagiaire est restructurée en colonne flex (`flex-direction:column`) — ligne 1 : NOM Prénom + badge dispense ; ligne 2 : DDN en `font-size:10px; color:#999` si `co.stagiaire_ddn`. Dans les cartes mobiles, `.co-card-ddn` passe de `display:none` à `display:inline` dans le bloc responsive `@media (max-width:1023px)`.

---

### ✅ Chantier terminé : évaluation pratique en ligne (saisie INRS sur tablette) — commit `50b343f`

**Objectif :** permettre au testeur de remplir la grille d'évaluation INRS directement sur tablette (en ligne), en alternative à la saisie manuelle papier + justificatif scanné.

**Modèles (`app/models/grille_pratique.py`) — 9 entités :**
- `GrillePratique` — grille par famille (ex. R482/F base, R482/F PE, R482/F TEL)
- `ThemePratique` — thème (ex. "Prise en main", "Manœuvres")
- `PointEvaluation` (PE) — unité d'évaluation avec règle de seuil propre
- `ItemPratique` — item INRS, mode de saisie (`binaire`/`partiel_entier`/`partiel_demi`), barème
- `CritereEliminatoire` — critères rédhibitoires (coche = éliminé)
- `SaisiePratique` — ancre `(jour_test_id, stagiaire_id, categorie)` — 1 saisie par candidat/catégorie/jour
- `SaisieBloc` — résultats calculés par bloc (base/option)
- `SaisieItemNote` — notes saisies par item
- `SaisieEliminatoire` — critères éliminatoires cochés

**Décision d'ancrage :** `SaisiePratique` sur `(jour_test_id, stagiaire_id, categorie)` (planification), PAS sur `session_epreuve_id` (résultat). La `SessionEpreuve` n'existe qu'à la validation finale.

**Service de calcul (`app/services/calcul_pratique.py`) :**
- `calculer_bloc(bloc, db)` : note_globale ≥ note_min AND chaque thème ≥ barème/2 AND chaque PE ≥ barème_PE/2 AND 0 éliminatoires
- `calculer_saisie(saisie, db)` : calcul global + subordination option (ACQUISE seulement si bloc base réussi)
- `appliquer_resultats(saisie, db)` : calcule ET écrit dans `SaisieBloc`

**Router (`app/routers/saisie_pratique.py`) — 6 routes sous `/api/sessions/{jour_test_id}/{stagiaire_id}/{categorie}/` :**
- `POST /ouvrir` — crée ou récupère la `SaisiePratique` + charge la grille
- `POST /enregistrer` — sauvegarde les notes item + critères éliminatoires (fil de l'eau)
- `POST /calculer` — calcul live (appelé en debounce 700 ms côté JS)
- `POST /valider` — crée la `SessionEpreuve` (résultat final), met la saisie en statut `validee`
- `POST /rouvrir` — repasse en `en_cours` pour corrections
- `DELETE /supprimer` — supprime la `SaisiePratique` et la `SessionEpreuve` associée (PIN)

**Page dédiée (`main.py`) :** `GET /sessions/{session_id}/pratique/saisie-en-ligne/{jour_test_id}/{stagiaire_id}/{categorie}` — standalone (pas de topbar), auth cookie.

**Template (`templates/saisie_pratique.html`) :** standalone mobile-first, `<body data-session-id data-jour-test-id data-stagiaire-id data-categorie>`, header sticky anthracite, barre de progression, zones blocs/proposition/actions fixes.

**JS (`static/js/saisie_pratique.js`) — 3 IIFEs :**
- Bloc 1 : init (lit `JOUR_ID`/`STAGIAIRE_ID`/`CATEGORIE` depuis `body.dataset`), fetch `/ouvrir`, `renderBloc`, contrôles par mode (binaire/paliers/stepper)
- Bloc 2 : `setNote`, `syncBloc` (debounce 600 ms), `syncAll`, `runCalc` (debounce 700 ms), `renderPropo`, `majProgression`, `majScores` ; délégation événements CSP-safe
- Bloc 3 : `ouvrirModalValidation` (récap + radios réussi/échec + justification + testeur), `POST /valider`

**Intégration `session_detail.html` + `session_detail.js` :**
- Modale de choix `#modal-choix-pratique` : 2 boutons — "📱 Saisie en ligne" → `window.open` saisie en ligne ; "✍️ Enregistrement manuel" → ancienne modale pratique
- Boutons `modifier-epreuve-pratique` (vert et rouge) + bouton `+` (nouveau résultat) : tous redirigés vers la modale de choix avec `data-jour-test-id="{{ j.id }}"` — `window._pratiqueCtx.jourTestId` stocké pour construire l'URL

**Middleware `_verifier_role` :** exceptions terrain pour les routes saisie pratique (chemin réel : `/api/sessions/{session_id}/pratique/saisie/{jour}/{stagiaire}/{categorie}/action`) — pattern whitelist corrigé en `\d+/\d+/[^/]+/ouvrir` (fix 2026-07-02 : l'ancien `\d+/ouvrir` ne matchait pas) ; route `variantes` (GET) whitelistée en même temps.

**Scripts init grille :**
- `init_grille_pratique_r482a.py` + `_options.py` — grilles A multi-engins (PH/MB/CH/CP, 100 pts), option TEL — déployé prod
- `init_grille_pratique_r482f.py` + `_options.py` — grille R482/F base (100 pts) + options PE/TEL (50 pts) — déployé prod
- `init_grille_pratique_r482b1.py` + `_options.py` + `patch_criteres_r482b1.py` — grille R482/B1 — **déployé prod (2026-06-30)**
- `init_grille_pratique_r482c1.py` + `_options.py` + `patch_criteres_r482c1.py` — grille R482/C1 (multi-variantes CH/CP) — **déployé prod (2026-07-01)**
- `init_grille_pratique_r482d.py` + `_options.py` + `patch_criteres_r482d.py` — grille R482/D (compactage) — **déployé prod (2026-07-01)**
- `init_grille_pratique_r482e.py` + `_options.py` + `patch_criteres_r482e.py` — grille R482/E (tombereau) — **déployé prod (2026-07-01)**
- `init_grille_pratique_r482g.py` + `_options.py` + `patch_criteres_r482g.py` + `fix_libelle_g.py` — grille R482/G (porte-engins, cumul_total) — **déployé prod (2026-07-01)**
- `init_grille_pratique_r482c2.py` + `_options.py` + `patch_criteres_r482c2.py` + `fix_libelle_c2.py` — grille R482/C2 (réglage) — **déployé prod (2026-07-01)**
- `init_grille_pratique_r482c3.py` + `_options.py` + `patch_criteres_r482c3.py` + `fix_libelle_c3.py` — grille R482/C3 (nivellement) — **déployé prod (2026-07-01)**
- `init_grille_pratique_r482b3.py` + `_options.py` + `patch_criteres_r482b3.py` + `fix_libelle_b3.py` — grille R482/B3 (rail-route) — **déployé prod (2026-07-02)**
- `init_grille_pratique_r482b2.py` + `_options.py` + `patch_criteres_r482b2.py` + `fix_libelle_b2.py` — grille R482/B2 (forage, variantes CA/CP) — **déployé prod (2026-07-02)**
- Tous idempotents, à exécuter sur Render Shell avec `DATABASE_URL` réel

**✅ R.482 COMPLET — 11 catégories déployées prod (2026-07-02).** Récap structures : A (cumul PH+N2 au choix), B1 (unique, avec levage), B2 (exclusif CA/CP forage, TEL intégrée dans CA), B3 (unique rail-route, 5 thèmes dont levage), C1 (exclusif CH/CP), C2 (unique réglage), C3 (unique nivellement), D (unique compactage), E (unique tombereau), F (unique), G (cumul-total CH+PC). Le mécanisme de saisie à **4 modes** (`unique` / `cumul` / `exclusif` / `cumul_total`) couvre toutes les configurations — aucune catégorie R.482 ne nécessite désormais de nouveau code de saisie. Règle : seuil par thème = barème/2 strict (y compris demi-points, ex. B3 Prise /17 → seuil 8.5). Les libellés `init_data.py` de plusieurs catégories étaient erronés et ont été corrigés via scripts `fix_libelle_*.py` (init_data ne modifie pas l'existant en base) : B2 → "Engins de forage à déplacement séquentiel", B3 → "Engins rail-route à déplacement séquentiel", C2 → "Engins de réglage à déplacement alternatif", C3 → "Engins de nivellement à déplacement alternatif", G → "Conduite des engins hors production". Toutes les options TEL manquantes dans `init_options.py` (C2, C3, E) ont été ajoutées ; B2 = `[("PE", False)]` (TEL intégrée dans la variante CA, pas un module).

**Grille pratique B2 R.482 (déployée 2026-07-02) — MULTI-VARIANTES + TEL INTÉGRÉE :** engins de forage, 2 grilles base exclusives asymétriques (items ET barèmes différents entre variantes). CA = conducteur accompagnant, **télécommande intégrée dans la grille base** (items télécommande dans la Prise de poste, pas de module TEL séparé — même logique que le PE inclus du A). CP = conducteur porté (poste de conduite classique). Chaque variante 100 pts : Prise /16 + Conduite /32 + Travaux /40 [forage] + Fin /12. Option PE facultative commune (50 pts). Pas d'option TEL. Scripts : `init_grille_pratique_r482b2.py` (variantes CA/CP via colonne `variante`), `_options.py` (PE seul), `patch_criteres_r482b2.py` (CA 34 + CP 35 + PE, 0 miss). Source : Excel OTC 'Pratique B2 - CA' et '- CP' + grille officielle INRS.

**Grille pratique B3 R.482 (déployée 2026-07-02) — RAIL-ROUTE :** engins rail-route à déplacement séquentiel, mono-grille 100 pts, 5 thèmes : Prise /17 (items spécifiques rail : accessoires levage, mécanismes montée/descente lorries, groupe de secours), Conduite /23 (mode route/rail, manœuvres enraillement/déraillement), Travaux /30, Opération de levage /18, Fin /12 (6 items dont "Mettre l'engin à l'arrêt"). Seuils impairs stricts : Prise 8.5, Conduite 11.5 (barème/2, pas d'arrondi INRS). Options PE + TEL facultatives. `init_options.py` : ligne B3 ajoutée (était absente) = `[("PE", False), ("TEL", False)]`. Scripts : `init_grille_pratique_r482b3.py`, `_options.py`, `patch_criteres_r482b3.py` (35 base dont 6 rail-route + PE + TEL, 0 miss). Source : grille officielle INRS B3.

**Grilles pratiques C2 / C3 / D / E R.482 (déployées 2026-07-01) — mono-grilles :** toutes structure Prise /16 + Conduite /42 + Travaux /30 + Fin /12 = 100 pts, options PE + TEL facultatives. C2 (réglage) : Travaux = 2 PE (réglage plate-forme + déblai/remblai). C3 (nivellement) : Travaux = 2 PE (réglage plate-forme + talus/fossé lame déportée). D (compactage) : Travaux = 1 PE (compactage plate-forme). E (tombereau) : Travaux = 3 PE (positionner chargement/parcours test/positionner déchargement), Conduite /42. Seuil Prise = 8 (coquille Excel "min.9" ignorée, règle moitié maintenue). TEL conservée pour E malgré absence pratique de tombereau télécommandé (référentiel INRS la liste, coût nul).

**Grille pratique B1 R.482 (déployée 2026-06-30) :** base 100 pts, 5 thèmes (Prise de poste /16, Conduite et circulation /24, Travaux de base /30 [3 PE : charger/déblai-remblai/tranchée], Opération de levage /18, Fin de poste /12 ; seuil par thème = moitié du barème) + 5 critères éliminatoires (saut, sécurité piétons, charge en hauteur, levage sans dispositifs, quitter sans arrêter moteur). Options Porte-Engins (PE) et Télécommande (TEL) **facultatives**, 50 pts / seuil 35 / 0,5 UT chacune. UT base B1 = 1,0 (déjà en base via `init_data.py`, options déclarées dans `init_options.py` ligne 26 : `[("PE", False), ("TEL", False)]`). `patch_criteres_r482b1.py` : 58 consignes d'échec (colonne L INRS), matching par libellé normalisé, idempotent. Source : Excel OTC 'Pratique B1'.

**Grille pratique C1 R.482 (déployée 2026-07-01) — MULTI-VARIANTES :** catégorie a 2 grilles base exclusives (choix d'un seul engin, pas de cumul). CH = Chargeuse (100 pts, sans levage : Prise /16 + Conduite /32 + Travaux /40 [charger + déblai-remblai] + Fin /12). CP = Chargeuse-pelleteuse (100 pts, avec levage : Prise /16 + Conduite /24 + Travaux /32 [charger + tranchée] + Levage /16 + Fin /12). Options PE + TEL facultatives (50 pts chacune). `init_options.py` ligne 28 corrigée : C1 = `[("PE", False), ("TEL", False)]`. Scripts : `init_grille_pratique_r482c1.py` (variantes CH/CP), `_options.py`, `patch_criteres_r482c1.py` (86 critères, 0 miss). Source : Excel OTC 'Pratique C1 - CH' et '- CP'.

### ✅ Grilles pratiques R.486 (PEMP) — A/B/C + option PE — scripts créés (2026-07-06, commit `c4a80a5`)

**Fichiers (8, tous idempotents) :** `init_grille_pratique_r486a.py` + `_options.py`, `init_grille_pratique_r486b.py` + `_options.py`, `init_grille_pratique_r486c.py` (pas d'`_options` séparé), `patch_criteres_r486a/b/c.py`. **À exécuter sur Render Shell** (non encore déployés prod à ce stade) : `python init_grille_pratique_r486a.py` → `..._r486a_options.py` → `..._r486b.py` → `..._r486b_options.py` → `..._r486c.py` → `patch_criteres_r486a/b/c.py`.

**Structure (mono-grille par catégorie, pas de variantes/cumul — R.486 est plus simple que R.482) :**
- **A** (PEMP à élévation verticale, types 1 et 3) : base 100 pts, 5 thèmes (Prise de poste et mise en service /15, Adéquation /6, Mise en place-conduite-manœuvres (1A) /35, Manœuvres et conduite (3A) /34, Fin de poste /10). Option PE facultative 50 pts (chargement/préparation transport/arrimage/déchargement sur porte-engins).
- **B** (PEMP à élévation multidirectionnelle, types 1 et 3) : même structure que A, thèmes adaptés (translation multidirectionnelle). Option PE facultative 50 pts, structure identique à celle de A.
- **C** (conduite hors production des PEMP) : base 100 pts, 6 thèmes incluant **chargement/déchargement sur porte-engins intégré directement dans la base** (pas d'option PE séparée — cohérent avec `init_options.py` ligne R486/C déjà existante : `[("PE", True)]`, PE incluse dans l'UT).

**Cohérence vérifiée AVANT commit avec le système de planification déjà existant** (`init_options.py` lignes 39-41, `init_data.py` — familles/habilitations R486 déjà en base) : PE facultative pour A et B, PE incluse pour C — exactement le découpage retenu pour les grilles d'évaluation (A et B ont un fichier `_options.py` séparé, C n'en a pas). Aucun script `init_options.py`/`init_data.py` modifié par ce chantier — uniquement les grilles d'évaluation pratique (table `grille_pratique` et dépendances), la planification (catégories/options sélectionnables) existait déjà.

**Aucun critère éliminatoire transversal** pour R.486 (`ELIMINATOIRES = []` dans les 3 scripts base) — absent du référentiel INRS pour cette recommandation, contrairement à R.482 (B1/D/F ont 5 critères éliminatoires chacun).

**Vérifications effectuées avant application (hors exécution en base, calcul pur sur les structures Python) :** (1) somme des barèmes de chaque thème = valeur déclarée, sur les 5 grilles (A base/option, B base/option, C base) — 100% conforme, aucun écart. (2) couverture du dictionnaire `CRITERES` de chaque script `patch_criteres_r486*.py` contre la liste réelle des items notés — **1 item manquant trouvé et corrigé avant commit** : "Positionner la PEMP sous une paroi plane horizontale" (thème "Manœuvres et conduite (3A)", PE 8 de la grille A base) n'avait pas d'entrée dans `patch_criteres_r486a.py` — seule la variante quasi-identique "Positionner la **plate-forme** sous une paroi plane horizontale" (PE 6) y figurait. Sans correctif, cet item aurait affiché un critère d'échec vide (bouton "œil") en silence, sans erreur ni crash — ajouté avec le même critère que son quasi-doublon. Après correctif : 0 manquant, 0 orphelin sur les 3 grilles (A : 52 items/47 critères après regroupement de doublons, B : 53/47, C : 33/33).

### ✅ Grille théorique R.486 — 5 grilles complètes (500 questions) — script créé (2026-07-06, commits `3a09861` grille 1 puis `26289d6` grilles 2-5)

**Fichier :** `init_questions_r486.py` (idempotent — supprime puis recrée toutes les grilles `famille="R486"` avant réinsertion, purge aussi les `UtilisationGrille` liées). Structure 4 thèmes fixes (14/26/54/6 = 100 questions) répliquée sur chaque grille, poids uniforme 1 pt/question (`POINTS_THEME`). Convention image/audio `R486_G{grille}_T{theme}_Q{numero}` (underscores), identique au pattern déjà en place pour les autres familles (`upload.py`, `split("_")`).

**✅ Livraison complète (commit `26289d6`) :** les 5 grilles sont renseignées (`GRILLES_R486 = {1..5}`), soit 500 questions. Le tirage Phase 2 pour R.486 pioche désormais dans le pool complet des 5 grilles (mécanisme de tirage inchangé). La livraison précédente (grille 1 seule, commit `3a09861`) était une étape assumée, désormais soldée.

**Vérifications effectuées avant commit (hors exécution en base) :** `ast.literal_eval` de `GRILLES_R486` → 5 grilles × 100 questions = 500, répartition 14/26/54/6 conforme sur chacune, 0 question mal formée (chaque item est bien `(numero:int, texte:str, reponse:bool)`), syntaxe OK (`ast.parse`). Réponses = corrigé officiel INRS croisé (0 divergence, cf. docstring du script). Pas de vérification automatisée possible du couple question/réponse vs source INRS (contenu métier).

**Mécanisme générique de variantes (saisie pratique) :** 4 configurations detectees automatiquement a l'ouverture d'une saisie. (1) grille unique (B1, F...) : ouverture directe. (2) variantes CUMULEES = cat A uniquement (engin N1 PH fixe + engin N2 MB/CH/CP au choix, 2 blocs). (3) variantes EXCLUSIVES (C1 et futures) : >=2 grilles base, choix d'UNE variante, 1 bloc. (4) variantes CUMUL_TOTAL (G et futures) : TOUTES les grilles base imposees et cumulees, AUCUN choix a l'ouverture — voir `CATEGORIES_CUMUL_TOTAL`. Route `GET .../variantes` renvoie `{mode: cumul|exclusif|cumul_total|unique, variantes[]}`. `ouvrir_saisie` accepte param `variante`. Front `saisie_pratique.js` : `afficherChoixVariante()` generique (libelles lus du back, aucun engin code en dur). Les futures categories multi-variantes ne necessitent AUCUN code supplementaire.

**Grille pratique D R.482 (compactage, scripts commit c64e03c, prod a executer) :** base 100 pts, 5 themes (Prise de poste /16, Conduite et circulation /40, Travaux de base /20 [bourrage-compactage + scarification], Operations specifiques /12, Fin de poste /12 ; seuil = moitie bareme). 5 eliminatoires identiques F/B1. Options PE et TEL facultatives (50 pts, seuil 35, 0,5 UT). UT base D = 1,0. Scripts : `init_grille_pratique_r482d.py`, `init_grille_pratique_r482d_options.py`, `patch_criteres_r482d.py`. `init_options.py` ligne D : `[("PE", False), ("TEL", False)]`.
**A executer sur Render Shell :** `python init_options.py` → `python init_grille_pratique_r482d.py` → `python init_grille_pratique_r482d_options.py` → `python patch_criteres_r482d.py`.

**Grille pratique E R.482 (tombereau, scripts commit 937e489, prod a executer) :** base 100 pts, 5 themes (Prise de poste /16, Conduite et circulation /40, Travaux de base /20 [chargement + deblai/remblai], Operations specifiques /12, Fin de poste /12 ; seuil = moitie bareme). 5 eliminatoires. Options PE et TEL facultatives (50 pts, seuil 35, 0,5 UT) — TEL prevue au referentiel. UT base E = 1,0. Scripts : `init_grille_pratique_r482e.py`, `init_grille_pratique_r482e_options.py`, `patch_criteres_r482e.py`. `init_options.py` ligne E : `[("PE", False), ("TEL", False)]`.
**A executer sur Render Shell :** `python init_options.py` → `python init_grille_pratique_r482e.py` → `python init_grille_pratique_r482e_options.py` → `python patch_criteres_r482e.py`.

**Grille pratique G R.482 (scripts crées 2026-07-01, prod a executer) :** 2 engins CUMULES sans choix (mode cumul_total). CH = chenilles, PC = pneumatiques/cylindre ; chacun 100 pts, meme structure : Prise de poste /16 + Conduite et circulation /40 + Chargement/dechargement sur porte-engins /32 (3 PE : chargement + preparation transport + arrimage + dechargement) + Fin de poste /12. Seuil = moitie du bareme par theme. 5 eliminatoires : sauter, pietons, charge en hauteur, levage sans dispositifs, quitter sans arreter moteur. Option TEL facultative (50 pts, seuil 35, 0,5 UT). Pas d'option PE (G EST le porte-engins). UT base G = 1,2 (deja en base). `CATEGORIES_CUMUL_TOTAL = {("R.482", "G")}` dans `saisie_pratique.py`.
Scripts : `init_grille_pratique_r482g.py`, `init_grille_pratique_r482g_options.py`, `patch_criteres_r482g.py`, `fix_libelle_g.py` (corrige libelle en prod), `init_options.py` (TEL facultative, pas de PE).
**A executer sur Render Shell (ordre) :** `python fix_libelle_g.py` → `python init_options.py` → `python init_grille_pratique_r482g.py` → `python init_grille_pratique_r482g_options.py` → `python patch_criteres_r482g.py`.

**UX saisie pratique — bandeau testeur (2026-07-01) :** le select testeur est un bandeau pleine largeur dedie (sorti de l'en-tete). Bascule couleur : rouge (#3a2020 + bordure #cc0000 + ⚠) tant qu'aucun testeur choisi, vert (#1e3320 + #2e9e56 + ✓) une fois selectionne. `majBandeauTesteur()` + listener change delegue dans saisie_pratique.js.

**Règles métier INRS :**
- Mode saisie adaptatif : binaire → 2 boutons ✓/✗ ; partiel + barème ≤ 3 → boutons paliers ; partiel + barème > 3 → stepper +/-
- Bloc réussi : note_globale ≥ note_min ET chaque thème ≥ barème/2 ET chaque PE ≥ barème_PE/2 ET 0 éliminatoires
- Subordination : option ACQUISE seulement si bloc base réussi
- Sauvegarde fil de l'eau : auto debounce 600 ms par bloc + bouton Enregistrer manuel
- Calcul live : debounce 700 ms après chaque changement de note

---

## ✅ SESSION 2026-06-27/28 — Évaluation pratique en ligne (finalisation) + test théorique numérique robuste

### ✅ Chantier terminé : critères d'évaluation pratique (2026-06-27)
Champ `ItemPratique.critere_evaluation` (Text nullable) + migration `ADD COLUMN`. Script `patch_criteres_r482f.py` (racine, idempotent, matching libellé désaccentué NFD) → 58 critères en prod (commande nue `python patch_criteres_r482f.py` sur Shell Render). Affichage logique A : critère masqué par défaut (`.sp-crit{display:none}`), bouton oeil global `data-action="toggle-criteres"` dans le header bascule `body.sp-show-crit` (affiche TOUS d'un coup). Bandeau ambre `#faeeda`/lisere `#e0a93f` sous chaque ligne notée. Routeur `_grille_dict` renvoie `critere_evaluation`. Commits `0be0a63`, `f4be80b`, `29414c9`, `49715a8`.

### ✅ Chantier terminé : anti-repêchage validation pratique (2026-06-27)
Le testeur peut RECALER (forcer échec si moteur=réussite) mais JAMAIS REPÉCHER (forcer réussite si moteur=échec). Front : bouton "Réussi" grisé/disabled dans modale si `echecMoteur`. Serveur : route `valider` calcule `appliquer_resultats` AVANT vérifs, refuse 422 si `res["base"]["reussi"]==False` et `data.decision_base==True` (idem options). Justification testeur OBLIGATOIRE pour TOUT échec (calculé ou décidé). Commit `85a0051`.

### ✅ Chantier terminé : options PE/TEL planifiables sur catégorie F (2026-06-27)
Catégorie F était ABSENTE de `init_options.py` → ajout ligne `("R482", "F", [("PE", False), ("TEL", False)])` (PE+TEL facultatives +0,5 UT chacune). `init_options.py` fait DELETE global puis recrée (idempotent, source de vérité unique). Relancé en prod (commande nue) → 35 options. Commit `dca1498`.

### ✅ Chantier terminé : resync options à la reprise — planification souveraine (2026-06-27)
Route `ouvrir` : à la reprise, compare `codes_planif` (depuis `JourTestCandidat.options_planifiees` JSON `{"F":["PE","TEL"]}`) aux blocs existants. Ajoute blocs options manquants, HARD DELETE systématique des blocs options déplanifiés (notes comprises, sans protection). La planification est souveraine. Commits `6ed48d7`, `644196c`.

### ✅ Chantier terminé : bouton supprimer saisie pratique (PIN admin) (2026-06-27)
Bouton "Supprimer cette saisie" (danger zone), modale PIN admin (`#sp-pin-overlay`), PIN dans le body. Route `DELETE .../{saisie_id}` avec `SupprimerSaisie(pin)`, vérifie `get_pin_admin(db)`. Supprime saisie + cascade + réinitialise résultat SessionEpreuve.

### ✅ Chantier terminé : testeur habilité obligatoire sur la saisie (2026-06-27)
Sélecteur testeur dans le HEADER de l'écran de saisie (vide au départ, OBLIGATOIRE pour valider, front + back). Modèle `HabilitationTesteur` (`app/models/habilitation_testeur.py`). **Famille stockée sans point** ("R482" = `Famille.code` = `session.famille`). Route page : `recommandation = session.famille` (PAS jour.famille qui n'existe pas). Modèle `ValiderSaisie.testeur_id: int` obligatoire. La branche `else` créant l'épreuve si absente MANQUAIT dans `valider` (expliquait le bug pastille UT) → ajoutée. Commits `23aebbc`, `6b4860b`.

### ✅ Chantier terminé : signature testeur sur la saisie pratique (2026-06-27/28)
Modèle : `SaisiePratique.signature_testeur` (Text, base64 PNG) + `testeur_id` + migrations `ADD COLUMN`. Modale de validation : champ "Nom du testeur" texte libre RETIRÉ (redondant avec le sélecteur header) → remplacé par encadré ambre avec mention + canvas signature OBLIGATOIRE (bloque Valider si vide, front + serveur 422). Apostrophe dans le JS via entité HTML `&#39;`. Stockée base64, affichée plus tard sur PDF. Commits `d3dccae` et suivants.

**BUG signature résolu (portée JS) :** fonctions `initSignature`/`clearSignature`/`signatureData` étaient dans une IIFE, appelées depuis une AUTRE IIFE (portées hermétiques). Solution : déplacer le bloc dans l'IIFE qui contient les appels. LEÇON : sur ce fichier multi-IIFE, toujours colocaliser définition et appel.

### ✅ Chantier terminé : fix liste testeurs vide + options = lignes distinctes (2026-06-28)
**Fix 1 (liste vide) :** route dédiée `GET .../testeurs-habilites` dans `saisie_pratique.py`, whitelisée middleware PIN (la route admin était inaccessible depuis le PIN formateur).

**Fix 2 (options) :** les options NE SONT PAS des booléens `option_pe`/`option_tel` (toujours False) mais des **LIGNES d'habilitation distinctes** : `categorie='OPT-PE'`, `categorie='OPT-TEL'`. Logique corrigée : `cats_requises.issubset(cats)` — un testeur est valide s'il a toutes les lignes requises. Commit `35a6c1b`.

### ✅ Chantier terminé : test théorique numérique — anti-perte des réponses (2026-06-27/28)
Modèle `BrouillonTheorie` (table `brouillons_theorie`) : sauvegarde fil-de-l'eau SANS calcul. Routes `POST/GET /theorie/brouillon` whitelisées publiques. Front : sauvegarde à chaque réponse, reprise sur le récap avec bandeau vert rassurant. Commits `344c408` et suivants.

### ✅ Chantier terminé : chrono serveur inviolable + finalisation auto des tests abandonnés (2026-06-28)
GET/POST brouillon renvoient `temps_restant_s` (calculé serveur depuis `date_debut`) + `expire`. Front repart du temps serveur. Auto-validation si expiré à la reprise. Finalisation auto via polling `etat-live` : `_finaliser_brouillons_expires` crée le `ResultatTheorie` pour tout brouillon expiré sans résultat. Commits `bdceb65`, `77732dd`.

### Note de cohérence à traiter plus tard
Interface de création d'habilitation (`HabilitationCreate` dans `admin.py`) propose encore les booléens `option_pe`/`option_tel` — incohérence non bloquante, à nettoyer.

### ✅ Chantier terminé : modes de saisie pratique configurables (2026-06-28)
Colonne `config_organisme.mode_saisie_pratique` (VARCHAR(20) default `binaire`) + migration `main.py` + getter `_mode_saisie(db)` PRÉEXISTAIENT (créés avec le moteur de calcul). Valeurs : `binaire` (tout ou rien par point) | `partiel_entier` (pas de 1) | `partiel_demi` (pas de 0,5). Effet CÔTÉ FRONT saisie (`saisie_pratique.js` lignes 51-57 : granularité des contrôles), pas côté calcul. Mode FIGÉ à la création de la saisie (`mode=_mode_saisie(db)`), renvoyé via `data.mode`. **Ce chantier a seulement branché l'INTERFACE** : sélecteur 3 options ajouté, modèle pydantic `ConfigOrganismeUpdate.mode_saisie_pratique`, route PUT `/config-organisme` applique le champ (garde valeur valide), GET renvoie le mode. Commit `b49e7b4`.

### ✅ Chantier terminé : réorganisation admin Paramètres + PIN serveur uniquement (2026-06-28)
**Problème :** boutons de sauvegarde incohérents (un au milieu carte config, un sous calendrier appelant la MÊME fonction `sauvegarderConfigOrganisme` qui sauve tout ; un bouton MENTEUR `sauvegarderParametres()` = `alert()` sans rien sauver). PIN admin `'1505'` codé EN DUR dans le front (2 endroits : `demanderPin` + `confirmerUploadDoc`) → bloquait toute sauvegarde si le vrai PIN ≠ 1505, rendant inutile l'écran de changement de PIN.
**Décisions (validées par maquette) :** mode de saisie DÉPLACÉ dans carte « Paramètres système » (sa place logique ; les 4 autres champs UT max/% hors CDT/année restent décoratifs, non câblés, AUCUNE colonne en base — à câbler un jour). Bouton menteur SUPPRIMÉ. **Un seul bouton « Enregistrer tous les paramètres »** en bas (sauve config + calendrier, PIN demandé une fois). Bouton « Modifier le PIN admin » conservé à part. **PIN validé UNIQUEMENT côté serveur** (retrait des deux `1505` en dur ; le serveur via `get_pin_admin(db)` tranche, 403 si incorrect). Commits `5e38f9b`, `8dabffa`, `f4c9c8c`.

### ✅ Chantier terminé : ergonomie saisie pratique (libellé + avertissements) (2026-06-28)
- **Libellé des points agrandi** : `.sp-item-lib` 13px → **16px gras** (lisibilité terrain quand le testeur suit le candidat). Aides inchangées (desc 12px, crit 12px, barème 11px). Commit `a23994c`.
- **Avertissement non bloquant points sans note** : à la validation, `_itemsSansNote()` compte les items notables vides (`b.notes[it.id] == null`), `window.confirm` propose de valider quand même ou revenir (cas légitime : candidat arrêté en cours, démotivé). **Les éliminatoires sont HORS comptage** (cases à cocher : non-coché = pas de faute = réponse valide, jamais un oubli). Commit `2a47608`.
- **Vérification testeur en amont** : le faux bug « bouton Confirmer inerte » = le garde `if(!testeurId) return` en fin de modale. Ajout vérification du sélecteur testeur (header) AVANT ouverture de la modale (toast + focus + outline rouge 2,5 s), pour ne pas remplir signature/commentaire puis se faire bloquer. Commit `8711dfe`.

### ✅ Chantier terminé : PDF résultat pratique (2026-06-28)
Service `app/services/pdf_resultat_pratique.py` (WeasyPrint, charte NORYX), fonction `generer_pdf_resultat_pratique(saisie_id, db)`. Contenu : en-tête candidat + organisme/logo, verdict global (CATÉGORIE ACQUISE/NON ACQUISE, vert/rouge), **encadré critères éliminatoires déclenchés** (si présents), détail par bloc (base + options) avec note globale/seuil/badge, notes par thème, **détail des points d'évaluation**, observations + justification de la décision par le testeur, signature testeur (base64), pied de page NORYX. **Génération à la volée, JAMAIS stockée** : le PDF est une vue des données vivantes → si la saisie est supprimée, plus de PDF, rien à nettoyer. Signature laissée en base64 dans la saisie.
**Accès 1 (consultation)** : route `GET /{session_id}/pratique/resultat/{jour_test_id}/{stagiaire_id}/{categorie}/pdf` (retrouve la SaisiePratique validée, auth cookie comme les autres PDF, GET non whitelisté = passe). Bouton « 📄 PDF résultat » dans la modale de choix pratique (`#choix-pratique-pdf-zone`), affiché SEULEMENT sur reclic d'une UT déjà validée (`modifier-epreuve-pratique` montre la zone, `nouveau-resultat-pratique` la cache), ouvre dans un onglet.
**Accès 2 (ZIP)** : `export_zip_session.py` boucle sur les saisies pratiques validées de la session → sous-dossier `resultats_pratiques/{nom}_{cat}.pdf`, généré à la volée.
**LEÇON (Claude Code) :** Claude Code a régénéré SON propre service (520 lignes, AVEC critères) au lieu d'utiliser le fichier fourni (302 lignes, sans critères) validé visuellement. Toujours vérifier `wc -l` + présence d'un marqueur (`grep "NE figurent PAS"`) avant commit quand un fichier vient de Claude Code. Commit `5806208`.

### ✅ Chantier terminé : rendu PE groupé par thème avec détail items (2026-06-28)
Commit `0aa9f00`.

**`app/services/calcul_pratique.py` :** enrichissement de `pes_detail` dans `calculer_bloc` — chaque dict PE contient désormais `libelle_chapeau` (PE.libelle_chapeau ou `""`) et `items` (liste de dicts `{libelle, descriptif_seul, note, bareme}`). Pour chaque item : si `descriptif_seul=True` → pas de note/barème ; si `bareme_max` → note = saisie réelle (0.0 si absent).

**`app/services/pdf_resultat_pratique.py` :** remplacement du rendu PE en table plate (`pe_rows`/`table.grid`) par un rendu hiérarchique :
- Regroupement des PE par thème (`themes_vus` dict ordered)
- Pour chaque groupe thème → `<div class="th-grp">` + `<div class="th-grp-titre">`
- Pour chaque PE → `<div class="pe-block">` avec titre `PE N° + score + badge` + chapeau italique si présent + items en flex `<div class="it-row"><span class="it-lib">/<span class="it-note">` ; items descriptifs seuls en `<div class="it-desc">`
- 10 nouvelles classes CSS : `.th-grp`, `.th-grp-titre`, `.pe-block`, `.pe-titre`, `.pe-chapeau`, `.it-row`, `.it-row:last-child`, `.it-lib`, `.it-note`, `.it-desc`

### ✅ Chantier terminé : critères éliminatoires dans le PDF résultat pratique (2026-06-28)
Commit `334781d`.

**`app/services/pdf_resultat_pratique.py` :** ajout d'un encadré orange `.elim-zone` affiché juste après le bandeau verdict ACQUISE/NON ACQUISE et avant le détail des blocs. La zone n'est rendue que si `all_elim` est non vide.
- `all_elim` : agrège `calcul["base"]["eliminatoires_coches"]` + tous `opt["eliminatoires_coches"]` (libelles texte)
- CSS : `.elim-zone` fond `#fff3cd` + bordure `#f0ad4e`, `.elim-titre` brun, `.elim-list li` rouge gras, `page-break-inside: avoid`
- Libellés issus du champ `CritereEliminatoire.libelle` (via `calculer_bloc` → `elim_detail`)

### Précision options PE/TC sur la fiche de reco (acté 2026-06-28)
S'appuie sur `OptionCategorie.incluse` (règle déjà en place, cf. §UT options) :
- **Option facultative** (`incluse=False`) qui échoue, base réussie → DISTINGUER : « catégorie obtenue, option PE/TC à repasser » (mention à part). Le candidat garde la base.
- **Option incluse** (`incluse=True`) qui échoue → fait partie intégrante de la catégorie → échec = catégorie entière à repasser, pas de distinction.
- À l'étape 1 (calcul) : pour chaque catégorie échouée, déterminer si l'échec vient de la base ou d'une option, et si option consulter `incluse` pour l'affichage.

### ✅ Fiche reco — ÉTAPE 1 TERMINÉE : service de calcul (2026-06-28, commit 9aba6d0)
app/services/calcul_fiche_reco.py — fonction calculer_fiche_reco(session_id, stagiaire_id, db) (lecture seule). Agrège théorie + toutes les pratiques du candidat (multi-catégories, dédupliquées par catégorie via id max). Détecte les causes (théorie : thèmes themeN_ok==False ; pratique : élimination via PE à 0 ou éliminatoire coché / thème insuffisant / total < 70). Calcule les durées par défaut (logique TESTÉE conforme : théo >=50->3h sinon 6h ; pratique élim->2h, sinon 2h×nb thèmes plafonné 6h). Gère les options via OptionCategorie.incluse (facultative échouée base OK -> options_a_repasser ; incluse échouée -> categorie_entiere_par_option=catégorie entière). Constantes isolées en tête (DUREES_THEORIE, DUREES_PRATIQUE, SEUIL_THEORIE_COURTE=50, HEURES_PAR_THEME=2, PLAFOND_PRATIQUE_H=6, HEURES_ELIMINATION=2) pour config admin future. Renvoie dict candidat / theorie_obtenue / theorie_echec / pratiques_echec[] / pratiques_obtenues[] / a_des_echecs.
**Reste : étape 2 (modèle FicheRecommandation + migration), étape 3 (écran onglet candidat), étape 4 (PDF imprimable).**

### ✅ FICHE DE RECOMMANDATION — TERMINÉE (étapes 1 à 4 + ZIP, 2026-06-28)
Document officiel remis au candidat en échec (théorie et/ou pratiques). Preuve QU'UNE reco a été faite (pas de versionnement, pas de snapshot immuable). Toujours recalculée depuis les résultats à jour.

**Fichiers :**
- `app/services/calcul_fiche_reco.py` — calculer_fiche_reco(session_id, stagiaire_id, db). Agrège théorie + pratiques multi-catégories (dédup id max). Bloc `session` (reference, famille, dates, categories_echouees). Bloc `candidat`. observations_testeur = justification PUIS observations par catégorie échouée.
- `app/services/pdf_fiche_reco.py` — generer_pdf_fiche_reco. WeasyPrint, charte NORYX. En-tête + n° INRS (champ ABSENT de ConfigOrganisme à ce jour → à ajouter), bloc session, bloc validité, blocs théorie/pratiques par thème, fautes éliminatoires, total anthracite, cases testeur, rappel CNAM.
- `app/routers/fiches_reco.py` — GET charger (calcul+brouillon), POST brouillon, GET .../pdf (génère + marque statut="finalisee" + date_finalisation).
- `app/models/fiche_recommandation.py` — table fiche_recommandation.
- Écran : modale `#modal-fiche-reco` + bouton `#fr-btn-pdf` ; JS construireFormFicheReco/genererPdfFicheReco dans session_detail.js.
- Accès via mini-modale `#modal-choix-doc` (commit a96ac38, 2026-07-02) : bouton 📄 ligne candidat (`data-action="choix-doc-candidat"`) ouvre un choix entre "Bilan de compétences" (→ PDF attestation-reussite) et "Fiche de recommandation" (→ `ouvrirFicheReco`). Ancien bouton `#sc-btn-fiche-reco` dans la modale candidat SUPPRIMÉ.
- ZIP : sous-dossier `recommandations/recommandation_{NOM_Prenom}.pdf` par candidat en échec.

**RÈGLE DURÉES (cumul, sans plafond figé) — paramétrable admin (constantes en tête de calcul_fiche_reco.py) :**
- Théorie : note >= 50 → 2h (HEURES_THEORIE_COURTE) ; < 50 → 4h (HEURES_THEORIE_LONGUE).
- Pratique : 1,5h × nb thèmes qui comptent (HEURES_PAR_THEME_PRATIQUE) + 1h forfait si >=1 faute éliminatoire (HEURES_FAUTE_ELIMINATOIRE).
- Un thème "compte" si : moyenne insuffisante OU contient un PE à 0.
- Affichage par thème : PE à 0 (rouge, "note éliminatoire") + PE sous moyenne (ambre, note < bareme/2) distingués. + encadré fautes éliminatoires.
- Durées éditables par le testeur (input number) avec total recalculé live.
- PAS de cumul entre catégories : chaque catégorie a son bloc et sa durée propre.

**RESTE À FAIRE :**
- Écran ADMIN pour paramétrer les durées (HEURES_PAR_THEME_PRATIQUE=1,5 / HEURES_FAUTE_ELIMINATOIRE=1 / HEURES_THEORIE_COURTE=2 / HEURES_THEORIE_LONGUE=4) — constantes prêtes à migrer vers une table de paramètres.
- Ajouter un champ n° INRS / numéro d'enregistrement OTC dans ConfigOrganisme (le PDF le cherche déjà, absent à ce jour).
- Notice : préciser que modifier une évaluation = ROUVRIR + REVALIDER (sinon le calcul lit l'ancien état).

### 🔄 FICHE DE RECOMMANDATION — MISE À JOUR FINALE (2026-06-29) — remplace les specs durées précédentes

**RÈGLE DURÉES DÉFINITIVE (durée ajustable PAR THÈME) :**
- Pratique : un champ modifiable PAR THÈME (1,5h défaut = HEURES_PAR_THEME_PRATIQUE) + un champ forfait éliminatoire modifiable (1h défaut = HEURES_FAUTE_ELIMINATOIRE) si >=1 faute éliminatoire.
- Un thème "compte" si : moyenne insuffisante OU contient un PE à 0. Sous chaque thème : PE à 0 (rouge "note éliminatoire") + PE sous moyenne (ambre, note < bareme/2).
- Sous-total par catégorie = somme auto des thèmes + forfait (non éditable, recalcul live). Total général = somme catégories + théorie (non éditable).
- Théorie : un seul champ modifiable (2h si note>=50, sinon 4h).
- Le testeur ajuste UNIQUEMENT au niveau thème/forfait ; sous-totaux et total se recalculent.
- Front : _frInputDuree (champ + data-fr-cat), _frSommeCat, _frRecalcTotal (sous-totaux data-fr-soustotal + total), _frCollectSaisies (enregistre le sous-total par catégorie dans saisies_json).

**COULEURS (écran + PDF) :** rouge réservé aux PE à 0 et à l'encadré fautes éliminatoires. "Moyenne du thème insuffisante" en gris neutre. PE sous moyenne en ambre.

**MODALE de préparation :** PAS d'encadré bleu de rappel (inutile pour le testeur). L'encadré n'est que sur le PDF.

**PDF (pdf_fiche_reco.py) — contenu validé :**
- En-tête organisme + n° INRS (champ ABSENT de ConfigOrganisme — à ajouter).
- Bloc session (référence, famille, dates, catégories non obtenues en rouge).
- Encadré bleu en HAUT : "Validité des épreuves obtenues" (théorie ET pratique = tout ou rien, ajournée = repassée intégralement, options PE/TC = repasser catégorie entière) + "Durée de formation recommandée" (proposée organisme+testeur, ni psychologues ni psychotechniciens, heures effectives pouvant nécessiter plusieurs journées de planning).
- Blocs par thème, durée PAR CATÉGORIE (sous-total) + total (PAS de détail par thème sur le PDF — épuré pour le candidat).
- Rappel CNAM en encadré GRIS en BAS (dispositif d'évaluation non de formation, formation préalable obligatoire, responsabilité des commanditaires).
- PIED DE PAGE RÉCURRENT sur chaque page : "Nom candidat | Session ref (famille) | Recommandation de formation" + numéro de page (identification si feuilles imprimées séparées).

**RESTE À FAIRE :**
- Écran ADMIN paramétrage durées (HEURES_PAR_THEME_PRATIQUE, HEURES_FAUTE_ELIMINATOIRE, HEURES_THEORIE_COURTE, HEURES_THEORIE_LONGUE) — constantes prêtes en tête de calcul_fiche_reco.py.
- Champ n° INRS dans ConfigOrganisme (le PDF le cherche, absent à ce jour).
- Notice : modifier une évaluation = ROUVRIR + REVALIDER.

### ✅ ÉCRAN ADMIN — DURÉES STANDARDS FICHE RECO — TERMINÉ (2026-06-29)

Les 5 paramètres de durée de la fiche de recommandation sont désormais modifiables en admin (carte "Paramètres système"), persistés en base, et lus par le calcul.

**Chaîne complète (back → front) :**
- `ConfigOrganisme` : 5 colonnes Float — reco_h_theme_pratique (1.5), reco_h_forfait_elim (1.0), reco_h_theorie_courte (2.0), reco_h_theorie_longue (4.0), reco_seuil_theorie (50.0). Migrations ALTER TABLE ... ADD COLUMN IF NOT EXISTS DOUBLE PRECISION dans main.py.
- `admin.py` : schéma ConfigOrganismeUpdate (5 champs Optional[float]) + GET /config-organisme (renvoie avec fallback) + PUT (sauvegarde conditionnelle, PIN admin).
- `calcul_fiche_reco.py` : `_charger_params(db)` lit la config (fallback sur les constantes HEURES_* en tête de fichier). `_params` passé à `_theorie_echec`/`_pratique_echec` → fonctions de durée. Les constantes restent les valeurs par défaut.
- `templates/admin.html` : section "⏱️ Durées standards — fiche de recommandation" dans la carte "Paramètres système" (5 champs config-reco-*), chargée au GET et envoyée au PUT via sauvegarderConfigOrganisme(). Bouton "Enregistrer tous les paramètres" commun.

**Vérifié :** modification en admin → fiche de reco recalcule avec les nouvelles durées.

**RESTE (fiche reco) :**
- Champ n° INRS / numéro OTC dans ConfigOrganisme (le PDF le cherche via _get_num_inrs, absent à ce jour → en-tête sans numéro).
- Notice utilisateur : modifier une évaluation = ROUVRIR + REVALIDER (sinon le calcul lit l'ancien état).

### ✅ CATÉGORIE A R.482 MULTI-ENGINS — TERMINÉ (2026-06-29)

La catégorie A R.482 se déroule sur DEUX engins : Engin N°1 = TOUJOURS la pelle hydraulique compacte (PH, avec thème exclusif "Opération de levage") + Engin N°2 au choix parmi MB (motobasculeur) / CH (chargeuse) / CP (compacteur). **Règle de réussite : les DEUX engins doivent passer** (échec d'un seul = catégorie A échouée). Une seule catégorie cartographiée (1,5 UT), pas de sous-catégories. Engin N°2 choisi À L'OUVERTURE de la saisie (overlay), pas à la planification. Porte-engins INCLUS dans la base ; seule option facultative = TEL (télécommande, +0,5 UT).

**Modèle** : `GrillePratique.variante` (String(10), nullable) = PH/MB/CH/CP pour cat A, NULL sinon. Migration ALTER idempotente dans l'init.

**Grilles (créées en prod via Shell Render)** : 4 grilles base A (PH/MB/CH/CP, 100 pts chacune via `init_grille_pratique_r482a.py`) + option TEL (50 pts via `init_grille_pratique_r482a_options.py`). Thèmes communs : Prise de poste (14), Conduite (PH=22 / autres=38), Travaux de base (24, PE spécifiques par engin), Porte-engins (16), Fin de poste (8) ; PH ajoute Opération de levage (16).

**Critères d'évaluation (bouton œil)** : `patch_criteres_r482a.py` remplit `ItemPratique.critere_evaluation` (colonne L Excel INRS) sur les 4 engins + TEL. Matching par libellé normalisé (gère ligature œ→oe, accents). 200 critères écrits, 0 manquant. **Même mécanisme que F (`patch_criteres_r482f.py`).**

**Moteur** (`calcul_pratique.py` réécrit) : `calculer_saisie` gère N blocs base (clé `bases[]` + compat `base`=1er), `categorie_acquise = all(bases réussis)`. `appliquer_resultats` écrit tous les blocs.

**Saisie** (`saisie_pratique.py` router + `saisie_pratique.js`) : `ouvrir_saisie` reçoit query param `engin2`, crée 2 blocs base (PH + engin2), retourne 422 si engin2 manquant sur saisie neuve cat A. Front : overlay choix engin N°2 (`afficherChoixEngin2`, `ouvrirOuDemander` sonde 422 pour distinguer neuf/reprise) + en-têtes visuels "ENGIN N°1/N°2 — [nom] (variante)" via `ENGIN_LABELS` dans `renderBloc`.

**PDF résultat (`pdf_resultat_pratique.py`) — GABARIT UNIFIÉ pour TOUTES les catégories** : synthèse N colonnes en tête (1 colonne cat F, N colonnes = bases + options pour cat A) avec "—" si thème non applicable, note globale + verdict par colonne, options en teinte bleue. Puis détail PE par PE empilé par engin (titres "ENGIN N°1/N°2" anthracite/rouge). Fonctions `_synthese_html`, `_titre_bloc`, `ENGIN_LABELS`. F et A = deux instances du même gabarit (chaque future catégorie en hérite).

**Fiche de reco (`calcul_fiche_reco.py`)** : `_pratique_echec` boucle sur `bases[]`, préfixe texte "[Engin N°2 · CP]" devant chaque thème. **Durée comptée PAR ENGIN** (un thème raté sur les 2 engins = 2 × 1,5h, PAS de déduplication — décision finale Patrice).

### ✅ RESET DES COMPTEURS DE TIRAGE PAR FAMILLE — TERMINÉ (2026-06-29)

**Remplace le tri par année civile** des statistiques de tirage. Modèle multi-OF : on trie par PÉRIODE ENTRE DEUX RESETS, pas par année. Un OF peut remettre ses compteurs à zéro quand il veut (le jour de son audit externe), tout en conservant les données.

**Principe directeur : ZÉRO suppression de données.** Le reset est seulement une borne temporelle datée. Tous les `UtilisationTheme` sont conservés.

**Reset PAR FAMILLE** (R482, R489 indépendamment). **Le reset borne AUSSI le tirage, pas seulement les stats** : après un reset R482, l'algo de priorité ne compte QUE les tirages postérieurs au reset (fin du perpétuel pour cette famille). Biais de sur-tirage temporaire post-reset accepté ("sur le long terme ça se gomme").

**Critère = `date_tirage` fait foi.** Tous les thèmes d'une session sont tirés en UNE fois (même date) → une session tombe entièrement sur une période, jamais éclatée. Contrainte unique `(session, famille, theme)` → pas de double comptage. Les tirages sans `date_tirage` (anciens) sont EXCLUS après un reset (forcément antérieurs) mais inclus dans "Tout l'historique".

**Modèle `reset_tirage.py`** : `ResetTirage(id, famille, date_reset, declenche_par_id)`, empilable, jamais purgé. Helpers `dernier_reset(famille, db)` et `resets_famille(famille, db)`. Table créée auto par `create_all` (nouvelle table) → IMPORTÉ dans main.py avant create_all.

**Tirage (`tirage_grille.py`)** : `tirer_themes_phase2` borne le comptage de priorité sur `date_tirage > dernier_reset(famille)`. Aucun reset → tout l'historique (comportement initial).

**Stats (`statistiques.py` + `statistiques.html`)** : `_build_stats(famille, debut, fin, db)` filtre sur l'intervalle (debut, fin]. `_periodes_famille` construit les périodes bornées par resets ("Période en cours depuis JJ/MM" / "Période JJ/MM → JJ/MM" / "Depuis le démarrage → JJ/MM" / "Tout l'historique"). Sélecteur de période PAR FAMILLE (chaque bloc R482, R489 a le sien) qui recharge via `?periode_<FAMILLE>=<id>`. Défaut = période en cours.

**Bouton reset (route POST `/statistiques/reset` + modale front) — 3 VERROUS** :
1. `ConfigOrganisme.audit_externe_date == date.today()` (jour exact, STRICT) sinon blocage "Réinitialisation impossible, modifiez votre date d'audit dans Administration → Calendrier qualité".
2. PIN admin (dans le corps POST, jamais en URL).
3. Confirmation explicite + case à cocher "irréversible".
PIN/confirmation gérés front ; audit + PIN revérifiés serveur. Pas de consommation de la date d'audit après reset (2e reset même jour = sans incidence, compteurs déjà à zéro).

### ✅ HISTORIQUE DE TIRAGE — DOUBLE FILTRE FAMILLE + PÉRIODE (2026-06-29)

L'historique reste UN SEUL tableau commun (toutes familles, colonne Famille) — choix ergonomique : un historique par famille décalerait les blocs des autres familles. Mais il gagne DEUX sélecteurs en tête : **Famille** (Toutes / R482 / R489…) + **Période**. Choisir une famille active le sélecteur de période avec les bornes de reset de CETTE famille ; "Toutes les familles" désactive la période. Filtrage côté JS (les lignes portent `data-famille` et `data-date` ISO ; `PERIODES_HIST` = `periodes_json` JSON-safe injecté via `tojson`). Cohérent avec le tri par période des 2 tableaux du haut.

**PIÈGE IDE RÉSOLU** : VS Code avec "organize imports on save" (Pylance/Ruff) supprimait `ConfigOrganisme` et `date` de statistiques.py à chaque Ctrl+S (vus comme inutilisés). → Désactiver `source.organizeImports` dans settings.json. Symptôme : `NameError: name 'ConfigOrganisme' is not defined` au chargement de /statistiques.
### ✅ BLOCAGE DU TIRAGE PENDANT L'AUDIT — TERMINÉ (2026-06-30)

**EN PROD (chantier complet, déployé et testé) :**

- **Bandeau dashboard** (orange clignotant). Texte : "Date de votre audit externe : le JJ/MM/AAAA. Le déclenchement des tirages est suspendu jusqu'à la réinitialisation des compteurs. Une fois votre audit terminé, réinitialisez les tirages des familles concernées pour rouvrir le tirage. Si cette date ne correspond pas à un audit, corrigez-la dans Administration → Calendrier qualité." + lien "Réinitialiser les compteurs →" vers /statistiques#tab-grilles.

- **Helper partagé** `audit_reset_requis(db) -> date | None` dans `app/models/reset_tirage.py`. Renvoie la date d'audit si un reset est requis (bandeau affiché + tirage bloqué), sinon None. Règle : reset requis si `ConfigOrganisme.audit_externe_date <= aujourd'hui` ET aucun ResetTirage à cette date (`func.date(date_reset) == audit_externe_date`). Se résout dès qu'un reset est fait le jour de l'audit OU que l'OF repousse sa date d'audit. Import local de ConfigOrganisme (évite les cycles). CE MÊME HELPER pilote le bandeau ET le blocage (une seule source de vérité).

- **Blocage du tirage** dans `app/routers/sessions.py`, route `POST /{id}/declencher-tirage` : après la vérif "session clôturée", si `audit_reset_requis(db)` renvoie une date → `HTTPException(409, "Déclenchement des tirages suspendu : votre date d'audit externe (JJ/MM/AAAA) est atteinte...")`.

- **main.py** (route dashboard) refactoré : `audit_rappel_date = audit_reset_requis(db)` (remplace l'ancien calcul inline). Imports de `audit_reset_requis` placés DANS les fonctions (main.py + sessions.py) pour contourner "organize imports on save" de VS Code.

**DÉCISIONS ACTÉES :**
- Blocage PORTE SUR TOUT TIRAGE (toutes familles) — on ne peut pas deviner quelle famille est auditée à partir d'une seule date d'audit.
- DEUX SORTIES pour débloquer : soit l'utilisateur reset (n'importe quelle famille, le message s'éteint et le tirage rouvre), soit il corrige sa date d'audit (s'il n'était pas concerné).
- Bandeau orange clignotant TOUT LE TEMPS où il est actif (pas de distinction de couleur jour J vs audit passé).
- "Familles concernées" reste GÉNÉRAL dans le message (l'OF a saisi une seule date d'audit, c'est à lui de savoir ce qui est audité/resetable). Pas de liste de familles.

**POINT 2 ABANDONNÉ (sessions antérieures au reset) :** fausse inquiétude. Le logiciel enregistre chaque tirage à sa `date_tirage` réelle (jour du tirage, donc postérieur au reset), donc les stats sont forcément justes peu importe la date de la session. Aucun garde-fou nécessaire sur les sessions antérieures. Le vrai garde-fou est le blocage du tirage ci-dessus.

**IMPORTS LOCAUX OBLIGATOIRES** (dans les fonctions, pas en tête de fichier) pour `audit_reset_requis` dans main.py et sessions.py → contourne le piège "organize imports on save" de VS Code qui supprime les imports vus comme inutilisés.

**Helper audit_reset_requis testé (logique validée sur 5 cas) :** sans config → None ; audit futur → None ; audit aujourd'hui sans reset → date (BLOQUE) ; audit + reset fait ce jour → None (DÉBLOQUE) ; audit passé sans reset → date (BLOQUE, persiste).

### ✅ Chantier terminé : mode cumul_total + grilles D/E (saisie pratique) (2026-07-01)

**Commit `2e6dfb6` + `937e489` + `c64e03c` :**
- `saisie_pratique.py` : `CATEGORIES_CUMUL_TOTAL = {("R.482", "G")}` ; route `variantes_categorie` → `mode = "cumul_total"` si catégorie dans le set et ≥2 variantes ; `ouvrir_saisie` : `EST_CUMUL_TOTAL` = set + ≥2 ; bloc création cumul_total = toutes grilles base imposées et cumulées (pas de choix).
- `saisie_pratique.js` : branche explicite `if (info.mode === "cumul_total")` → `lancerOuverture(null)` directement (pas de modale de choix).
- Grille D R.482 (compactage) : `init_grille_pratique_r482d.py` + `_options.py` + `patch_criteres_r482d.py` — idempotents, prod à exécuter.
- Grille E R.482 (tombereau) : `init_grille_pratique_r482e.py` + `_options.py` + `patch_criteres_r482e.py` ; `init_options.py` ligne E corrigée : `[("PE", False), ("TEL", False)]` (TEL ajoutée) — idempotents, prod à exécuter.

### ✅ Chantier terminé : responsive admin — cartographie + habilitations testeurs (2026-07-02)

**Périmètre :** `templates/admin.html` + `static/style.css`.

**Dates FR sur la cartographie :** affichage `{{ c.date_habilitation.strftime('%d/%m/%Y') }}` ; boutons crayon conservent l'ISO (`isoformat()` → `input[type=date]`). Tableaux cartographie : `<div class="carto-table-wrap carto-desktop">` + `<table class="carto-table">` + `<colgroup>` col widths (9/8/34/13/16/20%).

**Bascule tableau ↔ cartes (< 1024px) :** `.carto-desktop { display:block; }` / `.carto-cards { display:none; }` + swap dans `@media (max-width:1023px)`. Pas de scroll horizontal — deux rendus distincts.

**Cartes mobiles — HABILITÉES :** `{% set nsc = namespace(prev_famille='') %}` + séparateur `.carto-fam-sep` (titre famille) + `.carto-card` avec options facultatives, dates FR, boutons ✏️/🔒.

**Habilitations testeurs desktop :** 2 colonnes dates fusionnées → 1 colonne "Période intégration" (`<span style="display:block;">entrée : …</span><span>sortie : …</span>`). Boutons emojis nus (`background:none; border:none; padding:4px 6px; font-size:17px`).

**Cartes mobiles — habilitations testeurs :** `{% set nsh = namespace(prev_famille='') %}` + séparateur trait `.carto-fam-trait` (sans titre, sauf première famille — `{% if nsh.prev_famille and nsh.prev_famille != h.famille %}`). En-tête inline sur une ligne : `<div style="display:flex; align-items:center; gap:8px;">` → span famille+catégorie + badge statut + icônes (margin-left:auto). Sous-section période d'intégration + bouton ➕ Habilitation = `<span class="hab-add-link">`.

**CSS `.hab-add-link` :** `color:#2d2d2d; font-size:14px; font-weight:600; cursor:pointer; white-space:nowrap; padding:4px 6px;` + hover + mobile (12px/2px 4px).
**CSS `.carto-fam-trait` :** `border-top:2px solid #1a237e; margin:14px 0 12px;`.

**Structure HTML testeur (équilibre div vérifié par `python3 -c "... zone.count('<div') vs zone.count('</div>') ..."`) :** `<div class="testeur-body">` → `<div class="carto-desktop">` (table) → `</div>` → `<div class="carto-cards">` (cartes) → `</div>` → `</div>` (testeur-body) → `</div>` (card). 16/16 divs équilibrés.

**Onglets admin compacts (< 1024px) :** `.tab-long` / `.tab-short` dans chaque bouton onglet (`.admin-tabs-bar` flex no-wrap). Style inline `@media (max-width:1023px)` : `.tab-long { display:none; }` / `.tab-short { display:inline; }` / `.tab-btn { padding:8px 10px; font-size:13px; }` / `.admin-tabs-bar { gap:2px !important; }`.

### ✅ Chantier terminé : Cartographie habilitations dates (entrée/sortie) (2026-07-01, commit 9b49255)

**4 fichiers, 125 insertions :**

**Modèle + migration :**
- `app/models/categorie.py` : `date_sortie = Column(Date, nullable=True)` après `date_habilitation`.
- `app/main.py` : migration `ALTER TABLE categories ADD COLUMN IF NOT EXISTS date_sortie DATE` dans `_MIGRATIONS`.

**Backend (`app/routers/admin.py`) :**
- `ActiverCategorieBody` : `pin: str` + `date_habilitation: Optional[date]` — activer_categorie met à jour `date_habilitation` et repasse `date_sortie = None`.
- `DesactiverCategorieBody` : `pin: str` + `date_sortie: Optional[date]` — desactiver_categorie enregistre `date_sortie`.
- `DatesHabilitationBody` + route `POST /categorie/{id}/dates` : édite les deux dates ; guard 422 si `date_sortie < date_habilitation` ; `None` efface la date.
- PIN admin vérifié sur les 3 routes via `get_pin_admin(db)`.

**Frontend (`templates/admin.html`) :**
- Tableau HABILITÉES : `date_sortie` en rouge sous `date_habilitation` + bouton ✏️ Dates.
- Tableau NON HABILITÉES : colonne "Dernière période" (dates historiques).
- `activerHabilitation` / `desactiverHabilitation` : prompt date + envoi JSON `{pin, date_*}`.
- Modale `#modal-dates-hab` : 2 inputs date (entrée + sortie) + check client-side cohérence + `POST /admin/categorie/{id}/dates`.
- Fonction `modifierDatesHabilitation(id, nom, dateEntree, dateSortie)` avant `activerHabilitation`.

### ✅ Chantier terminé : verdict saisie pratique verrouillé — règle 130% intégrée (2026-07-03, commit 36306d9)

**Fichier :** `static/js/saisie_pratique.js`

**Règle métier :** si cumul(pp+mn+fp) en secondes ≥ 1,30 × ref d'un compteur → dépassement → échec forcé sur ce compteur/option, et échec global si la catégorie ou une option est concernée.

**1ère IIFE :**
- Ajout `_depassement130(gkey)` : calcule `{depasse, cumul, ref, aTemps}` à partir de `state.horaires[gkey]` et `g.ref`.
- Export `window._SP` : `dureeEnSecondes` remplacé par `depassement130: _depassement130`.

**2ème IIFE (verdict + affichage) :**
- `_dep(gk)` appelle `_SP.depassement130` ; `_depCat` pour la catégorie, `_optDep` pour chaque option.
- `baseReussi` = résultat base ET pas de dépassement CAT.
- Options dépassées → `o.reussi = false; o.acquis = false`.
- `echecGlobal` = `!baseReussi || option.reussi === false`.
- `_spDecisions` figé sur verdict calculé (plus modifiable par l'utilisateur).
- `_etatTempsHtml(groupKey)` : affiche "Temps dépassé (>130%)" en rouge ou "Temps conforme" en vert via `_SP.depassement130`.
- `blocRecap` : radios Réussi/Échec supprimées → div verdict non modifiable ("✓ RÉUSSI" / "✗ ÉCHEC — verdict calculé, non modifiable").

### ✅ Chantier terminé : habilitation option testeur valable sur toute la famille (2026-07-03, commit bc8890b)

**Fichier :** `app/routers/saisie_pratique.py`

**Bug 1 — liste testeurs habilités :** la route comparait des pseudo-catégories `"OPT-PE"` / `"OPT-TEL"` à des catégories réelles → aucun testeur proposé dès qu'une option est requise.

**Correctif liste :** `opts_requises` séparé de `cats_requises`. Accumulation des options via `opts_par_testeur[tid]` sur **toutes** les lignes de la famille (`getattr(hab, "option_pe", False)` / `option_tel`). Filtrage final : `cats_requises.issubset(cats) and opts_requises.issubset(opts_par_testeur.get(tid, set()))`.

**Bug 2 — validation :** vérifiait l'option uniquement sur la ligne de la catégorie testée → refus à tort si option détenue via une autre catégorie de la famille.

**Correctif validation :** `_habs_fam` = toutes les habilitations actives du testeur dans la famille (sans filtre catégorie). `_a_pe = any(option_pe for h in _habs_fam)`, idem TEL. Guard 422 si option requise manquante.

### ✅ Chantier terminé : normalisation format famille — R.482 == R482 (2026-07-03, commit 4c37465)

**Fichier :** `app/routers/saisie_pratique.py`

**Cause :** le front/grilles utilisent `"R.482"` (avec point, issu de `Famille.code`) ; `habilitations_testeurs.famille` stocke `"R482"` (sans point). Le filtre `_HT.famille == famille` ne matchait jamais → liste vide.

**Helper :** `_norm_fam(v)` = `(v or "").replace(".", "").replace(" ", "").upper()` — `"R.482"` et `"R482"` → `"R482"`.

**Route liste :** filtre SQL famille retiré ; query charge toute la table (filtre actif/actif/etat) puis filtre Python `[(t, hab) for ... if _norm_fam(hab.famille) == _fam_norm]`.

**Route validation :**
- `_fam_n = _norm_fam(_fam)`.
- `_habs_cat` : query sans filtre famille + `next(h for h if _norm_fam(h.famille) == _fam_n)`.
- `_habs_fam` : idem, filtre Python sur `_fam_n`.

### ✅ Chantier terminé : arrêt de tous les chronos à la validation finale (saisie pratique) (2026-07-04)

**Fichier :** `static/js/saisie_pratique.js`

**Problème :** à la validation finale d'une saisie pratique, un chronomètre (catégorie de base ou option) resté en cours d'exécution continuait de tourner après la fermeture de l'épreuve, sans être figé ni persisté en pause.

**Correctif :** nouvelle fonction `_arreterTousChronos()` (juste après `_persistChrono`, ligne ~167) — parcourt `state.chronos`, arrête tout chrono `run`/`timer` actif (`clearInterval` + `_persistChrono(key, "pause")`). Appelée juste avant le `POST .../valider` (après le contrôle de signature obligatoire, ligne ~1551) : plus aucun chrono ne peut rester actif une fois la validation déclenchée.

### ✅ Chantier terminé : nettoyage des champs testeur au changement de testeur (saisie pratique) (2026-07-04)

**Fichier :** `app/routers/saisie_pratique.py` — route `POST /{session_id}/pratique/saisie/{saisie_id}/testeur`

**Règle :** les observations, la justification d'écart, la signature et le nom du testeur sont des données PROPRES à la personne du testeur — si le testeur sélectionné change en cours de saisie, ces 4 champs sont réinitialisés (`None`) pour éviter qu'une signature/justification d'un premier testeur reste attribuée à tort à un second. Les notes par item et les temps (chronos) NE SONT PAS touchés (données objectives de l'évaluation, indépendantes du testeur).

**Implémentation :** comparaison `saisie.testeur_id != nouveau` AVANT d'écraser `saisie.testeur_id` ; si différent → `observations`, `justification_ecart`, `signature_testeur`, `testeur_nom` mis à `None`. Aucun changement si le testeur reposté est le même (évite un reset systématique à chaque fil-de-l'eau).

**Complément front (2026-07-04, `static/js/saisie_pratique.js`) :** le serveur effaçait bien les 4 champs en base, mais l'état JS déjà chargé en mémoire (`state.repriseObservations`, `state.repriseJustification`, `state.repriseSignature` — utilisés lignes ~1472-1484 pour pré-remplir le formulaire de validation à la reprise) restait affiché à l'écran tant que la page n'était pas rechargée. Le listener `change` sur `#sp-testeur-select` (~ligne 976) vide désormais ces 3 clés `state.*` dès la sélection d'un nouveau testeur, avant l'appel `POST .../testeur`.

### ✅ Chantier terminé : cache-busting des fichiers JS statiques (timestamp de fichier) (2026-07-04)

**Besoin :** un déploiement modifiant un fichier `static/js/*.js` pouvait rester en cache navigateur/CDN, faisant tourner une version obsolète du script après un correctif poussé en prod.

**Implémentation :**
- `app/main.py` (~ligne 543) : helper `_static_mtime(relpath)` — `int(os.path.getmtime(os.path.join("static", relpath)))`, retourne `""` si le fichier est introuvable (`OSError`). Exposé comme global Jinja2 : `templates.env.globals['static_mtime'] = _static_mtime`.
- `templates/saisie_pratique.html` : `<script src="/static/js/saisie_pratique.js?v={{ static_mtime('js/saisie_pratique.js') }}"></script>` — le paramètre `?v=` change automatiquement à chaque modification du fichier, invalidant le cache sans action manuelle.

**Portée de ce chantier :** uniquement `saisie_pratique.html`/`saisie_pratique.js` pour l'instant. Le pattern `static_mtime('js/xxx.js')` est réutilisable sur n'importe quel autre template incluant un script statique — à étendre au reste du site si le besoin se confirme (pas fait par défaut pour limiter le changement à ce qui a été demandé).

### ✅ Chantier terminé : correction de la vraie cause de `_arreterTousChronos` (portée inter-IIFE, pas le cache) (2026-07-04)

**Fichier :** `static/js/saisie_pratique.js`

**Diagnostic revu :** le cache-busting mtime (chantier précédent) était une amélioration légitime mais NE RÉSOLVAIT PAS le bug réel signalé — `_arreterTousChronos` était définie dans la 1ère IIFE (ligne ~167) et appelée depuis la 3e IIFE (ligne ~1551, bloc validation), deux portées JS hermétiques (cf. leçon déjà consignée sur la signature testeur, même fichier, même piège : « toujours colocaliser définition et appel sur ce fichier multi-IIFE »). L'appel levait une `ReferenceError` silencieuse côté navigateur, jamais un problème de cache.

**Correctif :** `_arreterTousChronos` reste définie dans la 1ère IIFE mais est exposée globalement via `window._spArreterTousChronos = _arreterTousChronos;` (juste après sa définition). L'appel dans la 3e IIFE devient `if (window._spArreterTousChronos) window._spArreterTousChronos();` (garde défensive si l'ordre de chargement venait à changer).

**Règle à retenir (fichier multi-IIFE `saisie_pratique.js`) :** toute fonction définie dans une IIFE et appelée depuis une autre DOIT être explicitement exposée sur `window._sp*` — jamais supposer une portée partagée entre les 3 IIFE de ce fichier.

### ✅ Chantier terminé : dashboard — carte Référents en grille 2×2 responsive (2026-07-04, remplace la version "empilement simple")

**Fichier :** `templates/dashboard.html`

**Historique :** une 1re version (même jour) fusionnait téléphone+email dans un seul `<td class="ref-contact">` avec deux `<span>` empilés en `display:block` sous 640px. Un défaut cosmétique avait été noté (séparateur « · » toujours affiché même sans téléphone). **Cette version est REMPLACÉE** par une grille 2×2, plus structurée.

**Version actuelle :** 4 `<td>` distinctes (nom, rôle, `.ref-tel`, `.ref-mail`), inchangées en desktop. Sous 640px, `.table-referents tr` devient `display:grid; grid-template-columns:1fr 1fr` : ligne 1 = Nom (col.1) + Rôle (col.2, gris `#888`) ; ligne 2 = Téléphone (col.1) + Email (col.2, `word-break:break-all` pour les adresses longues). `border:none` + `padding:0` sur les `<td>` (mise en page pilotée entièrement par la grille du `<tr>`), séparateur visuel `border-bottom` sur la ligne entière.

**Avantage vs version précédente :** alignement en tableau 2 colonnes (plus lisible qu'un simple empilement vertical), et plus de bug de séparateur fantôme (les deux cellules sont indépendantes, pas de pseudo-élément `::before` conditionnel).

### ✅ Chantier terminé : dashboard — retrait des emojis ✅ décoratifs (2026-07-04)

**Fichier :** `templates/dashboard.html`

**Correctif :** suppression des 8 occurrences de l'emoji ✅ devant des mentions courtes (« Aucun » dans les 5 sections de la carte « À traiter », badges « Actif » et dates de validité). Conforme à la règle de charte déjà en place : « privilégier CSS pur (caractères Unicode sobres, chiffres dans pastilles) plutôt que des emojis ». Les autres emojis du dashboard (👥, 🪪, 📋, ⚠️, ⚡, 🚩...) sont conservés — ce chantier ne visait que ✅.

### ✅ Chantier terminé : garde-fous suppression CACES externe — extension et dispense dépendantes (2026-07-04)

**Fichier :** `app/routers/stagiaires.py`, route `DELETE` (`supprimer_caces_externe`, ~ligne 876)

**Problème :** la suppression d'un CACES externe faisait un hard delete direct, sans vérifier si ce CACES servait de FONDATION à autre chose. Deux risques :
1. Un autre `CacesObtenu` peut être une **extension** héritant son échéance de celui-ci (`caces_initial_id` pointant dessus) — le supprimer aurait laissé l'extension orpheline (échéance sans origine).
2. Un `SessionCandidat` peut avoir une **dispense de théorie** fondée sur ce CACES (`dispense_source_type == "caces"`, `dispense_source_id` pointant dessus) — le supprimer aurait laissé une dispense sans justification traçable.

**Correctif :** 2 vérifications AVANT le hard delete, chacune levant `HTTPException(409)` si une dépendance existe :
- `db.query(CacesObtenu).filter(CacesObtenu.caces_initial_id == co.id).first()` → « ce CACES sert de base à une extension (famille cat. catégorie). Supprimez d'abord l'extension. »
- `db.query(SessionCandidat).filter(dispense_source_type=="caces", dispense_source_id==co.id).first()` → « ce CACES fonde une dispense de théorie pour un candidat en session. Retirez d'abord la dispense. »

**Correction apportée en cours d'application (script fourni buggé) :** le message d'erreur de l'extension utilisait `ext.recommandation`, champ INEXISTANT sur `CacesObtenu` (le modèle n'a que `famille` et `categorie`) → aurait levé une `AttributeError` au premier cas réel de blocage. Remplacé par `ext.famille`.

**Extension à 3 cas (2026-07-04) :** 3e garde-fou ajouté — `CarteCaces` (import local `from app.models.carte_caces import CarteCaces`, dans la fonction) : si une carte `statut == "emise"` existe pour `(stagiaire_id, famille)`, blocage 409 « une carte CACES active (n. X) a été émise pour cette famille et peut inclure ce CACES. Annulez ou remplacez d'abord la carte. ». Champs `CarteCaces` vérifiés (`stagiaire_id`, `famille`, `statut`, `numero_carte`). Le 2e script fourni pour cette extension réintroduisait la même coquille `ext.recommandation` dans son bloc de remplacement — corrigée à nouveau en `ext.famille` lors de l'application, pour rester cohérent avec le correctif déjà en place.

**Même garde-fous portés sur `supprimer_reprise_caces` (module H5, CHANTIER 5 — reprise d'historique, 2026-07-04) :** la route `POST /stagiaires/{id}/reprises/caces/{co_id}/supprimer` (~ligne 660) n'avait qu'un seul verrou (extension valide dérivée, ligne 673-682). Ajout des 2 mêmes verrous que sur `supprimer_caces_externe`, insérés juste après le verrou extension existant :
- **VERROU DISPENSE** : `SessionCandidat.dispense_source_type == "caces"` + `dispense_source_id == co.id` → 409 si une dispense de théorie en cours en dépend.
- **VERROU CARTE** : `CarteCaces` `statut == "emise"` pour `(stagiaire_id=id, famille=co.famille)` → 409 si une carte active en dépend.

Les deux routes de suppression de CACES (externe et repris) partagent désormais la même logique de protection à 3 niveaux (extension / dispense / carte émise), avec des messages d'erreur identiques en substance.

### ✅ Chantier terminé : route PUT modification d'un CACES repris (module H5) (2026-07-04)

**Fichier :** `app/routers/stagiaires.py` — nouvelle route `PUT /{id}/reprises/caces/{co_id}` (~ligne 724), juste après `supprimer_reprise_caces`.

**Reprend le schéma `CacesRepriseCreate`** déjà utilisé par `POST /{id}/reprises/caces` (H2a) : `famille`, `categorie`, `options_obtenues`, `date_obtention`, `date_echeance`, `ancien_numero`, `testeur_id`, `pin`.

**Gardes (dans l'ordre) :**
1. PIN admin (403).
2. `date_echeance > date_obtention` (400).
3. CACES introuvable / pas une reprise (`ancien_numero` vide) → 404/400.
4. **Les 3 mêmes verrous que la suppression** (extension valide dérivée / dispense de théorie en cours / carte émise) → 409 — un CACES repris déjà exploité ne peut pas être modifié tant que la dépendance n'est pas levée, cohérence avec la règle de suppression.
5. Si la catégorie change : vérifie qu'aucun autre CACES repris de la même session sentinelle n'occupe déjà la nouvelle catégorie (409 sinon).

**Mise à jour synchronisée :** le `CacesObtenu` ET la `SessionEpreuve` associée (même session sentinelle, retrouvée via l'ANCIENNE catégorie avant écrasement — `ancienne_cat` capturée avant modif) sont mis à jour ensemble, pour rester cohérents avec le pattern déjà en place à la création (H2a) et à la suppression (CHANTIER 5).

### ✅ Chantier terminé : UI — bouton modifier sur les lignes CACES repris (module H5) (2026-07-05)

**Fichier :** `static/js/stagiaires.js` (`renderReprisesHistorique`, `ouvrirModalReprise`, dispatcher de clic, `confirmerAjoutReprise`).

**Objectif :** brancher la route `PUT /{id}/reprises/caces/{co_id}` (chantier précédent) sur un bouton ✏️ dans le tableau "🪪 Historique repris", en réutilisant la modale d'ajout existante en mode édition.

**Bug bloquant corrigé pendant l'application (script fourni cassé) :** le script proposait d'encoder le payload JSON du CACES repris dans un attribut `data-reprise` délimité par des guillemets simples ÉCHAPPÉS (`\'`). Après les 3 couches d'échappement traversées (Python triple-quoted string → JS → attribut HTML), les backslashes disparaissaient et le JS généré contenait deux littéraux de chaîne adjacents sans opérateur (`data-reprise='' + _frReprToAttr(r) + ''...`) → `SyntaxError` au chargement de la page (vérifié en appliquant le remplacement sur une copie jetable du fichier et en inspectant les octets réels produits, pas seulement en relisant le script source). **Corrigé** en repassant l'attribut en guillemets DOUBLES (convention déjà utilisée par tous les autres `data-*` de ce bouton, ex. `data-stag="..."`) et en échappant les guillemets doubles du JSON en `&quot;` dans `_frReprToAttr` (au lieu d'échapper les apostrophes en `&#39;`). Le navigateur décode automatiquement `&quot;` → `"` à la lecture via `getAttribute`, donc `JSON.parse` fonctionne sans décodage manuel.

**2e bug corrigé (logique, pas de syntaxe) :** le script ne réinitialisait jamais le titre de la modale après un passage en mode édition — `#modal-reprise h3` serait resté bloqué sur "Modifier un CACES repris" pour tous les ajouts suivants. Corrigé en ajoutant la réinitialisation du titre (`🪪 Ajouter un CACES repris`) directement dans `ouvrirModalReprise()`, qui s'exécute AVANT le passage en mode édition (`ouvrirModalModifReprise` appelle `ouvrirModalReprise` puis écrase le titre ensuite) — donc aucun conflit d'ordre.

**Fonctionnement :** `_repriseEditId` (variable module-level) distingue ajout (`null`) d'édition (id du CACES). `ouvrirModalModifReprise(stagiaireId, r)` pré-remplit tous les champs (famille déclenche le `change` pour charger les catégories, puis sélection différée de 350 ms le temps du fetch catégories). `confirmerAjoutReprise()` bascule `POST .../reprises` (ajout) vs `PUT .../reprises/caces/{id}` (édition) selon `_repriseEditId`.

**Règle à retenir (échappements multi-couches) :** ne jamais faire confiance à un script d'échappement imbriqué (Python string → JS string → attribut HTML) sans vérifier les OCTETS RÉELS produits dans le fichier cible — la relecture du script source ne suffit pas, les backslashes peuvent disparaître silencieusement à travers les couches. Préférer systématiquement les guillemets doubles pour les attributs HTML contenant du JSON (échappement `&quot;` uniquement), cohérent avec la convention déjà en place dans ce fichier.

### ✅ Chantier terminé : pré-sélection du testeur en édition d'un CACES repris (2026-07-05)

**Besoin :** le formulaire d'édition d'un CACES repris (chantier précédent) pré-remplissait famille/catégorie/dates/ancien numéro, mais pas le testeur (`#rep-testeur`) — champ pourtant obligatoire côté serveur (`CacesRepriseCreate.testeur_id`).

**Back (`app/routers/stagiaires.py`, route `GET /{id}/reprises`, ~ligne 359-386) :** ajout de `"testeur_id": (ep.testeur_id if ep else None)` dans le dict retourné, à côté de `testeur_nom` déjà présent. **Attention route homonyme :** ce fichier a une 2e fonction avec un bloc de retour très similaire (`GET /familles/{stag_id}/...` ou équivalent, ~ligne 396-430) qui a déjà `testeur_id` — bien vérifier qu'on cible la route consommée par `fetch('/stagiaires/' + id + '/reprises')` (celle du tableau "🪪 Historique repris"), pas l'autre.

**Front (`static/js/stagiaires.js`) :**
- `_frReprToAttr(r)` : `testeur_id: r.testeur_id || ""` ajouté au JSON encodé dans l'attribut `data-reprise` (garde l'échappement `&quot;` déjà en place depuis le chantier précédent, PAS `&#39;`).
- `ouvrirModalModifReprise` : après le `setTimeout` de pré-remplissage (350 ms, le temps du chargement async des catégories), un `setInterval` (100 ms, 20 tentatives max = 2 s) attend que l'option `<option value="{testeur_id}">` existe dans `#rep-testeur` (le fetch `/api/testeurs/` est lui-même asynchrone et peut ne pas être terminé à 350 ms) avant de faire `sTest.value = String(r.testeur_id)`. Auto-arrêt si l'option n'apparaît jamais (garde-fou anti-boucle infinie).

**Piège évité en appliquant ce chantier :** le script fourni pour cette étape ciblait encore l'ancien échappement `.replace(/'/g, "&#39;")` dans `_frReprToAttr` — obsolète depuis la correction du chantier précédent (`&quot;`). Adapté pour insérer `testeur_id` dans le JSON SANS revenir à l'échappement simple-guillemet cassé.

### ✅ Chantier terminé (back uniquement) : justificatif R2 pour un CACES repris interne (2026-07-05)

**Fichier :** `app/routers/stagiaires.py`

**Route ajoutée :** `POST /{id}/reprises/caces/{co_id}/justificatif` (~ligne 970, juste avant `GET /{id}/caces-externe/{caces_id}/justificatif`) — PIN admin, upload multipart (`UploadFile`/`File`/`Form`, déjà importés en tête de fichier), mêmes gardes que l'upload externe (`storage.EXTENSIONS_AUTORISEES`, `storage.TAILLE_MAX`, fichier vide rejeté). Purge l'ancien `justificatif_cle` R2 avant remplacement. Clé construite avec le préfixe dédié `"caces-reprises"` (`storage.construire_cle`), distinct de `"caces-externes"` déjà utilisé — même bucket, préfixes séparés pour s'y retrouver.

**Lecture : PAS de nouvelle route GET.** `GET /{id}/caces-externe/{caces_id}/justificatif` (existante) filtre uniquement sur `CacesObtenu.id == caces_id AND stagiaire_id == id`, sans distinction d'origine (externe vs repris) — directement réutilisable pour lire le justificatif d'un CACES repris en lui passant son `co.id`. Le nom de la route reste trompeur ("caces-externe") mais fonctionne pour toute origine.

**Retour enrichi :** `GET /{id}/reprises` (H2a, tableau "🪪 Historique repris") renvoie désormais aussi `justificatif_nom` et `a_justificatif` (bool), à côté de `testeur_id`/`testeur_nom` déjà ajoutés au chantier précédent.

**RESTE À FAIRE (non couvert par ce chantier) :** aucun bouton front (`static/js/stagiaires.js` / `templates/stagiaires.html`) ne déclenche encore cet upload/cette lecture sur les lignes "Historique repris" — ce chantier n'a livré que le socle serveur, sur le modèle du justificatif dispense (Carte 2/3 → 3/3, cf. section dédiée plus haut) qui avait suivi la même séquence back-puis-front.

### ✅ Chantier terminé (front) : consulter / joindre le justificatif sur une ligne "Historique repris" (2026-07-05)

**Fichier :** `static/js/stagiaires.js` — branche le back du chantier précédent (`POST .../reprises/caces/{co_id}/justificatif`, lecture via `GET .../caces-externe/{caces_id}/justificatif`).

**Ligne CACES repris enrichie :** entre le nom du testeur et le bouton ✏️ Modifier, ajout de :
- si `r.a_justificatif` : lien `📎 {justificatif_nom}` (`target="_blank"`, ouvre la lecture directement, cookie suffit) ;
- sinon : mention ambre `⚠️ Sans justificatif` (non bloquant, même esprit que le badge dispense externe sans justificatif) ;
- bouton `📤` (`data-action="joindre-justif-reprise"`) — libellé au survol adaptatif ("Joindre" ou "Remplacer" selon `a_justificatif`).

**`joindreJustifReprise(stagiaireId, coId)` :** crée un `<input type="file">` dynamique (accept PDF/Word/Excel), déclenche la sélection, PIN admin via `window.prompt` (pas de modale dédiée — cohérent avec la simplicité de l'action), `FormData` + `fetch POST`. En cas de succès : invalide le cache de l'historique (`delete body.dataset.loaded`) et rappelle `toggleHistorique` pour recharger la ligne à jour (même pattern que `confirmerAjoutReprise`).

**Bug d'échappement multi-couches recontré UNE 3e FOIS et corrigé :** `'Erreur lors de l\\'envoi'` dans le script fourni — le même piège que `data-reprise=\\'` (chantiers précédents) : le `\\'` censé produire l'apostrophe échappée `\'` en JS s'effondre en un simple `'` après les couches d'échappement Python, cassant la chaîne (`node -c` a immédiatement détecté l'erreur : `missing ) after argument list`). **Corrigé** en passant cette chaîne JS particulière en guillemets doubles (`"Erreur lors de l'envoi"`) plutôt qu'en tentant d'échapper l'apostrophe dans une chaîne à guillemets simples. **Constat cumulé sur 3 chantiers consécutifs** (data-reprise, ext.recommandation non lié mais même séance, et maintenant ce message d'erreur) : les scripts Python générant du JS avec des apostrophes littérales à l'intérieur de chaînes à guillemets simples sont systématiquement à re-vérifier via `node -c` avant de considérer la tâche terminée — ne jamais se fier à la relecture du script source.

### ✅ Chantier terminé : responsive de la ligne "Historique repris" (2026-07-05)

**Fichiers :** `static/js/stagiaires.js` (`renderReprisesHistorique`), `templates/stagiaires.html` (CSS).

**Avant :** la ligne d'un CACES repris était un unique `flex` avec `flex-wrap:wrap` — sur petit écran, les éléments s'enroulaient de façon désordonnée (numéro, dates, actions mélangés selon la largeur disponible).

**Correctif :** la ligne (`.repr-row`) est désormais structurée en 3 sous-groupes explicites via des `<span>` en `display:flex` :
- `.repr-ident` : ancien numéro, famille, catégorie, options ;
- `.repr-dates` : date d'obtention → date d'échéance ;
- `.repr-actions` : testeur, justificatif (lien ou avertissement), boutons 📤/✏️/🗑️ (`margin-left:auto` en desktop pour les pousser à droite).

**Responsive (`templates/stagiaires.html`, `@media (max-width: 1023px)`) :** `.repr-row` passe en `flex-direction:column`, les 3 sous-groupes s'empilent chacun en pleine largeur (`margin-left:0 !important`, `width:100%`), `.repr-actions` repasse en alignement à gauche (`justify-content:flex-start`) au lieu d'être poussé à droite.

**Appliqué sans bug d'échappement cette fois** (`node -c` valide directement) — contrairement aux 2 chantiers précédents sur ce même fichier le jour même.

### ✅ Chantier terminé : réagencement boutons ligne "Historique repris" — modifier/supprimer avec le numéro (2026-07-05)

**Fichiers :** `static/js/stagiaires.js`, `templates/stagiaires.html`.

**Changement :** les boutons ✏️ Modifier et 🗑️ Supprimer, jusque-là dans `.repr-actions` (à droite, avec le justificatif), sont déplacés dans `.repr-ident` (groupe du numéro/famille/catégorie/options), via un sous-groupe `.repr-ident-btns` (`margin-left:6px` en desktop). `.repr-actions` ne contient plus que testeur + justificatif + bouton 📤.

**Logique :** rapprocher les actions de modification/suppression de l'identifiant du CACES qu'elles affectent, plutôt que de les regrouper avec l'action justificatif (nature différente). En responsive (`@media max-width:1023px`), `.repr-ident` passe en `justify-content:space-between` et `.repr-ident-btns` garde `margin-left:auto !important` — les boutons restent poussés à droite de la ligne numéro même en colonne empilée.

### ✅ Chantier terminé : bouton "+ Ajouter" collé au titre des 3 rubriques d'historique (2026-07-05)

**Fichier :** `static/js/stagiaires.js`

**Correctif :** les 3 en-têtes de rubrique de la fiche stagiaire — "🪪 Historique CACES internes", et les 2 rubriques homologues externe/orphelines — utilisaient `justify-content:space-between`, poussant le bouton `+ Ajouter` tout à droite du bloc, loin du titre. Remplacé par `justify-content:flex-start;gap:12px` (au lieu de `gap:8px`) sur les 3 en-têtes identiques : le bouton colle désormais juste après le titre, avec un espacement légèrement agrandi pour la lisibilité.

### ✅ Chantier terminé : boutons modifier/supprimer à droite en desktop, sur la ligne du n° en mobile (2026-07-05)

**Fichiers :** `static/js/stagiaires.js`, `templates/stagiaires.html`.

**Retour en arrière partiel sur le chantier précédent** ("boutons regroupés avec le numéro") : en DESKTOP, ✏️/🗑️ reviennent dans `.repr-actions` (groupe de droite, avec le justificatif) — plus lisible en ligne large. En MOBILE, un DUPLICATA des mêmes boutons reste sur la ligne du numéro (`.repr-ident-btns`), car en colonne empilée les regrouper avec le justificatif les éloignait trop de l'identifiant.

**Mécanisme :** deux jeux de boutons identiques existent dans le DOM — `.repr-ident-btns` (caché par défaut, `display:none`) et `.repr-actions-btns` (visible par défaut, `display:flex`, dans `.repr-actions`). Le média-query `@media (max-width:1023px)` inverse les deux : `.repr-ident-btns { display:flex !important }` / `.repr-actions-btns { display:none !important }`. Pas de JS conditionnel — bascule purement CSS selon la largeur d'écran.

**Piège évité en appliquant ce script (bash, pas JS cette fois) :** le script fourni utilisait `'''...''''` (une chaîne Python se terminant par un caractère `'` littéral suivi des 3 guillemets de fermeture) — cette construction a fait planter le parseur `bash` du heredoc (`unexpected EOF`), alors même que `<< 'PYEOF'` aurait dû neutraliser toute interprétation de guillemets côté shell. **Contournement :** écriture du script Python dans un fichier temporaire via l'outil `Write` (pas de heredoc bash) puis exécution par `python3 fichier.py` — élimine tout risque d'interaction entre les niveaux de citation bash/Python. Fichier temporaire supprimé après usage.

**Constat mineur :** l'ancre du script fourni contenait aussi une espace finale parasite (`+ '</span>' ` avec espace, vs `+ '</span>'` réel dans le fichier) — détecté par un diagnostic ligne-par-ligne (`s.count(ligne)` sur chaque ligne de l'ancre) avant d'exécuter le remplacement complet, plutôt que de découvrir l'échec après coup.

### ✅ Chantier terminé : mini-modale justificatif CACES repris (joindre / remplacer / supprimer) (2026-07-05)

**Fichiers :** `app/routers/stagiaires.py`, `templates/stagiaires.html`, `static/js/stagiaires.js`.

**Remplace l'ancien flux (chantier `0ad8c65`)** : `window.prompt()` pour le PIN + input file volant, sans possibilité de retirer un justificatif déjà joint. Passage à une vraie mini-modale.

**Back — nouvelle route `DELETE /{id}/reprises/caces/{co_id}/justificatif`** (~ligne 969, juste avant la route `POST` existante) : PIN admin (`SuppressionData`, déjà utilisé ailleurs dans ce fichier), 404 si CACES introuvable ou si `justificatif_cle` déjà vide, purge R2 (`storage.delete_fichier`, `try/except` silencieux comme les autres suppressions), remet `justificatif_cle`/`justificatif_nom` à `None`. Le CACES lui-même n'est jamais touché.

**Template — modale `#modal-justif-reprise`** (juste avant `#modal-suppr-reprise`, z-index 1100 — au-dessus des modales standards) : zone "fichier actuel" dynamique, input file, input PIN, zone erreur, bouton "Supprimer le fichier" (masqué par défaut, affiché seulement si un fichier existe déjà), boutons Annuler/Enregistrer.

**Front — `joindreJustifReprise(stagiaireId, coId, aFichier, nomFichier)`** remplace l'ancienne version à `prompt()` : ouvre la modale, adapte le texte et l'affichage du bouton Supprimer selon `aFichier`. `_justifReprEnvoyer()` (POST FormData) et `_justifReprSupprimer()` (DELETE JSON body) partagent `_rechargerHistoStag(sid)` (invalide le cache d'historique + rappelle `toggleHistorique`, même pattern que `confirmerAjoutReprise`). Le bouton 📤 transmet désormais `data-a-fichier` et `data-nom-fichier` (au lieu de rien) pour préremplir la modale à l'ouverture.

**Méthode de vérification renforcée suite aux bugs répétés du jour :** avant d'appliquer le script complet, un diagnostic dédié (`s.count()` sur chaque ancre séparément, y compris la fonction `joindreJustifReprise` extraite par regex) a confirmé qu'exactement UNE ancre (`old_btn`, le bouton 📤) portait le même défaut d'espace finale parasite déjà rencontré 2 fois plus tôt dans la journée — corrigée avant application, pas après échec.

### ✅ Chantier terminé : durcissement du sélecteur CSS de bascule mobile des boutons (2026-07-05)

**Fichier :** `templates/stagiaires.html`

**Correctif :** `.repr-row .repr-ident-btns` / `.repr-row .repr-actions-btns` (chantier `b6ed6ed`) remplacés par des sélecteurs plus spécifiques `.repr-row .repr-ident .repr-ident-btns` / `.repr-row .repr-actions .repr-actions-btns` — précise que le sous-groupe de boutons visé est bien celui imbriqué dans `.repr-ident` (resp. `.repr-actions`), pas une classe homonyme isolée qui pourrait apparaître ailleurs dans le DOM à l'avenir. `display:inline-flex` (au lieu de `flex`) sur `.repr-ident-btns` en mobile, cohérent avec son usage en `<span>` inline. Comportement fonctionnel inchangé (les règles `!important` l'emportent sur les styles inline de toute façon) — durcissement défensif, pas un correctif de bug observé.

### ✅ Chantier terminé : testeur déplacé de `.repr-actions` vers `.repr-dates` (2026-07-05)

**Fichier :** `static/js/stagiaires.js`

**Correctif :** le nom du testeur (`r.testeur_nom`) était affiché en tête de `.repr-actions` (groupe de droite, avec justificatif + boutons) — regroupement peu logique (le testeur n'est pas une "action"). Déplacé en fin de `.repr-dates` (juste après la date d'échéance, `margin-left:8px`), à côté des autres informations factuelles de la ligne. `.repr-actions` ne contient plus que justificatif + boutons ✏️/🗑️ (desktop) / 📤.

**Piège d'espace parasite rencontré une 4e fois et anticipé cette fois** (diagnostic `s.count()` par ancre AVANT application, comme établi au chantier précédent) : l'ancre `repr-dates` fournie se terminait par `+ '</span>' ` (espace final) au lieu de `+ '</span>'` réel — `.rstrip()` appliqué systématiquement sur les 2 ancres avant de lancer le remplacement, zéro échec à l'exécution.

### ✅ Chantier terminé : responsive de la ligne "CACES externes" (2026-07-05)

**Fichiers :** `static/js/stagiaires.js` (`renderCacesExternes`), `templates/stagiaires.html` (CSS).

**Même traitement que la ligne "Historique repris"** (chantier `45b5b98`) mais appliqué à la rubrique CACES externes (`🌐 organisme`). Structure en 3 sous-groupes explicites via `<span>` :
- `.cext-ident` : famille, catégorie, bouton 🗑️ Supprimer (`.cext-suppr`, collé à droite du groupe via `margin-left:auto`) ;
- `.cext-dates` : date d'obtention → date d'échéance ;
- `.cext-orga` (🌐 nom de l'organisme externe) et `.cext-justif` (lien/avertissement justificatif) : deux groupes séparés, pas fusionnés.

**Responsive (`@media max-width:1023px`) :** `.cext-row` passe en `flex-direction:column`, `.cext-ident` reste sur une ligne interne (`justify-content:space-between`, le bouton supprimer file à droite), `.cext-orga` et `.cext-justif` s'empilent chacun en pleine largeur (`margin-left:0 !important; width:100%`).

**Différence avec "Historique repris" :** pas de duplication de boutons desktop/mobile ici — un seul bouton 🗑️ Supprimer, déjà placé dans `.cext-ident` (pas besoin de le faire remonter en mobile, il y est déjà). Anchor JS validé d'un seul bloc au diagnostic préalable (`s.count(old) == 1` directement, aucun défaut d'espace cette fois).

### ✅ Chantier terminé : modification d'un CACES externe (route PUT + UI ✏️/📤) (2026-07-05)

**Fichiers :** `app/routers/stagiaires.py`, `static/js/stagiaires.js`.

**Back — `PUT /{id}/caces-externe/{caces_id}`** (~ligne 1027, juste avant la route GET justificatif) : miroir de `creer_caces_externe` (POST, déjà existante) — PIN admin, validation date, mêmes 3 gardes que les autres routes de modification/suppression CACES de la journée (extension valide dérivée / dispense en cours / carte émise), contrôle d'unicité si la catégorie change, recalcule `date_obtention` via `_date_initiale_depuis_echeance(famille, ech)` (déjà importée en tête de fichier, utilisée par `creer_caces_externe`) — cohérent avec la règle "l'origine est recalculée automatiquement" affichée dans la modale. Met à jour `CacesObtenu` ET la `SessionEpreuve` associée (même pattern que la route reprise interne).

**Front — bouton ✏️ + 📤 dans `.cext-ident`** (à côté de 🗑️, avant `.cext-dates`) : `_cextToAttr(r)` encode `{id, organisme, famille, categorie, date_echeance}` en JSON, échappement `&quot;` (attribut en guillemets doubles, cohérent avec la convention posée au chantier `0ad8c65`). `ouvrirModalModifExterne` réutilise `ouvrirModalCacesExterne` (reset) puis pré-remplit + bascule le titre en "Modifier". `confirmerCacesExterne` bascule POST/PUT selon `_cextEditId`.

**Réutilisation du bouton 📤 justificatif :** le même `data-action="joindre-justif-reprise"` / `joindreJustifReprise()` que pour les CACES repris internes est réutilisé tel quel pour les CACES externes — vérifié que les routes `POST`/`DELETE .../reprises/caces/{co_id}/justificatif` (chantiers précédents) ne filtrent que sur `CacesObtenu.id`/`stagiaire_id`, SANS test sur `ancien_numero` (contrairement à la route de suppression du CACES lui-même) — donc génériques malgré leur nom et leur docstring ("CACES repris interne"), utilisables tel quel pour un CACES externe.

**3 écarts corrigés par rapport au script fourni (diagnostiqués AVANT exécution, méthode désormais systématique) :**
1. Le script supposait une variable module-level `_cextStagiaireId` — le code réel utilise `window._cextStagiaireId` lu dans une variable locale `stagiaireId` à l'intérieur de `confirmerCacesExterne`. Ancre de remplacement du fetch reconstruite sur le code réel.
2. Le fetch réel n'a pas de virgule finale après `body: fd` (le script en supposait une) — ancre corrigée en conséquence.
3. Le script comptait sur **2 occurrences** de `function ouvrirModalCacesExterne(stagiaireId) {` après insertion des helpers (pour cibler "la bonne" par index) — logiquement impossible : un `.replace()` qui insère du texte AVANT une ancre en réutilisant cette même ancre comme suffixe ne crée jamais de duplicata, il en reste exactement UNE. Remplacé par une insertion directe et non ambiguë de `_cextEditId = null;` juste après la ligne de signature réelle (seule occurrence, confirmée par `grep` avant modification).

### ✅ Chantier terminé : ligne "CACES externes" alignée sur le patron responsive "Historique repris" (2026-07-05)

**Fichiers :** `static/js/stagiaires.js`, `templates/stagiaires.html`.

**Remplace/complète le chantier `8c52909`** ("responsive de la ligne CACES externes", qui affirmait "pas de duplication de boutons desktop/mobile" — affirmation désormais **obsolète**, l'ajout des boutons ✏️/📤 au chantier `d206185` a changé la donne).

**Nouvelle structure, identique au patron "Historique repris" (`b6ed6ed`) :**
- `.cext-ident` : famille, catégorie, `.cext-ident-btns` (✏️/🗑️, caché par défaut `display:none`, visible en mobile) ;
- `.cext-dates` : dates + 🌐 organisme externe (déplacé depuis son ancien groupe `.cext-orga` autonome, fusionné ici) ;
- `.cext-actions` : justificatif + 📤 + `.cext-actions-btns` (✏️/🗑️, visible par défaut `display:flex`, caché en mobile).

**CSS (`@media max-width:1023px`) :** même bascule que `.repr-ident-btns`/`.repr-actions-btns` — `.cext-ident .cext-ident-btns { display:inline-flex !important }` / `.cext-actions .cext-actions-btns { display:none !important }`. Les 2 boutons `.cext-suppr` distincts (l'ancienne classe dédiée) ont été retirés — chaque instance de bouton supprimer n'a plus besoin de classe propre puisqu'elle est désormais dans un groupe dupliqué nommé.

**Bilan des 2 lignes (interne + externe) :** patron unifié, mêmes noms de classes logiques (`-ident`, `-dates`, `-actions`, `-ident-btns`, `-actions-btns`), seul le préfixe change (`repr-` vs `cext-`).

### ✅ Chantier terminé : options sur le CACES externe (POST + PUT + affichage) (2026-07-05)

**Fichiers :** `app/routers/stagiaires.py`, `templates/stagiaires.html`, `static/js/stagiaires.js`.

**Besoin :** le CACES externe n'avait pas de champ options (PE/TEL), à la différence du CACES repris interne qui en a un depuis le module H2a.

**Back :** `options: str = Form("")` ajouté aux signatures `creer_caces_externe` (POST) ET `modifier_caces_externe` (PUT). POST : `options_obtenues=(options.strip() or None)` à la création du `CacesObtenu`. PUT : `co.options_obtenues = options.strip() or None` + propagation sur la `SessionEpreuve` liée (`ep.options_obtenues`) — cohérent avec la mise à jour déjà faite pour famille/catégorie/date dans cette même route.

**Template :** champ `#cext-options` (texte libre, ex. "PE,TEL") ajouté dans la modale `#modal-caces-externe`, juste après le champ échéance.

**Front (`static/js/stagiaires.js`) :**
- `FormData` : `fd.append('options', ...)` dans `confirmerCacesExterne`.
- Reset création (`ouvrirModalCacesExterne`) et pré-remplissage édition (`ouvrirModalModifExterne`) du champ.
- `_cextToAttr(r)` : `options_obtenues` ajouté au JSON transporté par `data-ext` — **attention, l'échappement réel de cette fonction est `.replace(/"/g, "&quot;")` seul** (posé au chantier `d206185`), PAS le double `&#39;`/`&quot;` que le script fourni supposait à tort (déjà halluciné 2 fois aujourd'hui sur des fonctions différentes) — corrigé avant application, comme d'habitude désormais.
- Affichage sur la ligne : pastilles individuelles (une par code, séparateur `,`) juste après le badge catégorie dans `.cext-ident`, même style visuel que les options du CACES repris interne (fond `#e0f2f1`, texte `#00695c`).

### ✅ Chantier terminé : indicateur "sous-traitance" sur le CACES externe (2026-07-05)

**Fichiers :** `app/models/caces_obtenu.py`, `app/main.py` (migration), `app/routers/stagiaires.py`, `templates/stagiaires.html`, `static/js/stagiaires.js`.

**Besoin :** distinguer un CACES externe passé "par notre intermédiaire" (sous-traitance auprès d'un OF partenaire habilité) d'un CACES externe apporté indépendamment par le candidat (ex. ancien employeur).

**Modèle :** `CacesObtenu.sous_traitance` (`Boolean`, `nullable=False`, `default=False`) + migration startup idempotente `ALTER TABLE caces_obtenus ADD COLUMN IF NOT EXISTS sous_traitance BOOLEAN DEFAULT FALSE` dans `_MIGRATIONS` (`app/main.py`).

**Back :** `sous_traitance: bool = Form(False)` ajouté aux signatures POST (`creer_caces_externe`) et PUT (`modifier_caces_externe`), écrit sur `CacesObtenu` aux deux endroits. Exposé dans le retour de `GET /{id}/reprises` via `"sous_traitance": bool(getattr(co, "sous_traitance", False))` — `getattr` avec défaut plutôt qu'accès direct, filet de sécurité si un vieux `CacesObtenu` en base avait été chargé avant la migration (non nécessaire en pratique car `nullable=False` + `default=False`, mais coûte rien).

**Template :** case à cocher `#cext-soustraitance` dans un encadré bleu clair (`#e6f1fb`/`#0c447c`) sous le champ Options, avec texte explicatif complet (coché = passé par notre intermédiaire, décoché = obtenu indépendamment) — la nuance métier est écrite en toutes lettres pour éviter toute ambiguïté à la saisie.

**Front :** case envoyée dans le FormData (`'true'`/`'false'`), réinitialisée à la création, pré-cochée en édition selon `r.sous_traitance`. Badge `S/T` (fond bleu clair, cohérent avec l'encadré de la modale) affiché sur la ligne juste après les pastilles d'options, uniquement si `r.sous_traitance` est vrai.

**4 écarts corrigés par rapport au script fourni (diagnostiqués systématiquement avant exécution, comme pour tous les chantiers précédents de la journée) :**
1. L'ancre du modèle (`justificatif_nom = Column(...)`) omettait le commentaire final `# nom original du fichier preuve` déjà présent sur la ligne réelle. Un remplacement basé sur l'ancre tronquée aurait inséré la nouvelle colonne AU MILIEU de la ligne existante, laissant le commentaire orphelin accolé à la mauvaise colonne (`sous_traitance     # nom original du fichier preuve` — sémantiquement faux). Corrigé en incluant la ligne complète dans l'ancre.
2. Insertion dans `_MIGRATIONS` avec une indentation de 4 espaces au lieu des 8 espaces utilisés par toutes les entrées existantes de la liste — sans conséquence sur la validité Python (whitespace libre dans un littéral de liste) mais incohérent visuellement ; corrigé pour respecter la convention du fichier.
3. L'ancre du retour d'historique supposait `"organisme_externe": co.organisme_externe,` collée juste après `"options_obtenues"` — en réalité 3 autres clés s'intercalent (`date_obtention`, `date_echeance`, `ancien_numero`) ET la ligne réelle a un suffixe `or ""` absent de l'ancre fournie. Le `.replace()` du script n'avait PAS d'assertion sur ce point précis (contrairement aux autres étapes) → aurait échoué SILENCIEUSEMENT, laissant `sous_traitance` absent de l'API malgré un script "réussi" en apparence. Corrigé avec l'ancre réelle exacte.
4. `_cextToAttr` : 4e occurrence du même piège d'échappement halluciné (`&#39;`+`&quot;` au lieu du simple `&quot;` réellement en place depuis le chantier `d206185`).

**Constat méthodologique :** ce chantier est le premier où le script fourni contenait des étapes `s.replace()` SANS assertion de comptage (contrairement à tous les chantiers précédents qui utilisaient systématiquement `assert s.count(old) == 1`). Un remplacement non asserté qui ne matche pas échoue silencieusement — risque plus insidieux qu'un `AssertionError` qui arrête tout net. Réflexe retenu : ajouter un `print("label:", s.count(old))` sur CHAQUE remplacement avant l'écriture finale, assertion ou non dans le script d'origine.

### ⚠️ Règle permanente — apostrophe littérale dans une chaîne JS à guillemets simples (2026-07-05)

**Contexte :** renommage du titre "🏆 CACES® validés" → "🏆 CACES® de l'apprenant" (`static/js/stagiaires.js:423`) — remplacement textuel simple, sans aucune couche d'échappement Python/bash cette fois. Le script remplaçait juste une chaîne par une autre contenant une apostrophe FRANÇAISE LITTÉRALE ("l'apprenant"), insérée telle quelle dans une chaîne JS déjà délimitée par des guillemets SIMPLES (`html += '<div ...>...'`). Résultat : `SyntaxError: Unexpected identifier 'apprenant'` — la chaîne se refermait prématurément au niveau de l'apostrophe.

**Différence avec les bugs d'échappement précédents de la journée (data-reprise, ext.recommandation, etc.) :** ceux-là étaient des artefacts de transformation Python→JS (backslashes qui disparaissent à travers plusieurs couches). Celui-ci est plus basique : **toute apostrophe française insérée en dur dans un texte destiné à une chaîne JS à guillemets simples DOIT être échappée (`\'`)**, qu'il y ait ou non des couches d'échappement Python en jeu. `node -c` a immédiatement révélé le problème — validé et corrigé avant tout commit.

**Règle à appliquer systématiquement :** avant d'insérer un nouveau libellé français dans une chaîne JS à guillemets simples de ce fichier (très majoritaire dans `stagiaires.js`), vérifier s'il contient une apostrophe ("l'", "d'", "qu'", "aujourd'hui"...) et l'échapper en `\'` si oui — pas seulement dans les scripts Python générateurs, aussi lors d'une édition directe.

### ✅ Chantier terminé : `renderCacesValides` scindé en 3 sections (organisme / sous-traitance / externe) (2026-07-05)

**Fichiers :** `app/routers/stagiaires.py`, `static/js/stagiaires.js`.

**Besoin :** la liste "CACES® de l'apprenant" (fiche stagiaire) affichait tous les CACES validés en un seul tableau plat, sans distinguer leur origine (natif NORYX vs externe vs externe-sous-traitance).

**Bug backend trouvé et corrigé AVANT d'appliquer le script front :** `renderCacesValides` (nouvelle version) filtre sur `c.organisme_externe` et `c.sous_traitance` — mais ces données viennent de `GET /{id}/caces-valides` (route `get_caces_valides_stagiaire`), une route **différente** de `GET /{id}/reprises` déjà corrigée au chantier `4dae010`. `get_caces_valides_stagiaire` ne renvoyait NI `organisme_externe` NI `sous_traitance` → sans correctif, tous les CACES seraient tombés dans la section "CACES de l'organisme" et les 2 autres sections seraient toujours restées vides, quelle que soit la donnée réelle en base. Corrigé en ajoutant les 2 champs au dict retourné (`"organisme_externe": co.organisme_externe or ""`, `"sous_traitance": bool(getattr(co, "sous_traitance", False))`), même pattern que la route sœur.

**Front (`static/js/stagiaires.js`) :** `renderCacesValides` répartit désormais la liste en 3 sous-listes (`otc`/`st`/`ext` selon `organisme_externe`/`sous_traitance`) et délègue le rendu à une nouvelle fonction `_sectionCaces(titre, liste, colExterne)` factorisée — un tableau par section, masqué si vide (`if (!liste.length) return ''`). `colExterne` bascule la dernière colonne (Testeur ↔ Organisme émetteur) et la pastille de numéro (`N°` réel vs badge `S/T`/`EXT` coloré : vert `#0f6e56` si sous-traitance, gris `#5f5e5a` sinon).

**Leçon reconduite :** avant d'appliquer un script front qui lit de nouveaux champs sur un objet de données, toujours vérifier que la route API qui ALIMENTE cet objet expose bien ces champs — un script peut être syntaxiquement irréprochable et fonctionnellement muet si la donnée n'arrive jamais jusqu'au front.

### ✅ Chantier terminé : exclusion des CACES externes de l'émission de carte (2026-07-05)

**Fichier :** `app/routers/cartes_caces.py`

**Règle appliquée (cohérente avec la spec moteur déjà verrouillée, section "PROVENANCE") :** un CACES externe (`organisme_externe` renseigné, sous-traitance ou non) ne doit **jamais** apparaître sur une carte CACES® émise par NORYX — « on ne certifie pas ce qu'on n'a pas testé ». Filtre `CacesObtenu.organisme_externe.is_(None)` ajouté à 5 requêtes distinctes : `get_familles` (familles proposées à la sélection carte, ligne 180), `get_caces_valides` (tableau de sélection, ligne 192), 2 requêtes de fallback affichage carte déjà émise (lignes 244 et 354), et surtout **`emettre_carte`** (ligne 378 — la route qui fige réellement le snapshot `caces_json` à l'émission).

**Bug du script fourni détecté et corrigé AVANT exécution :** l'ancre censée cibler `emettre_carte` (repérée "ligne 376" dans le commentaire du script) était en réalité un DOUBLON de l'ancre `get_caces_valides` — même texte de requête, aucune occurrence distincte dans le fichier réel (vérifié par recherche de toutes les occurrences du texte, une seule trouvée, à la ligne de `get_caces_valides`). Appliquer les 2 remplacements séquentiellement sur cette ancre dupliquée aurait fait échouer le 2e (texte déjà transformé par le 1er) — via un `AssertionError` bloquant, sans corruption du fichier, mais la vraie route `emettre_carte` (celle qui compte le plus : c'est elle qui grave le CACES sur la carte) serait restée NON PROTÉGÉE si l'erreur n'avait pas été relevée avant exécution. Localisée manuellement la vraie requête (`.filter(...).all()` sans `.order_by()`, lignes 374-378) et construit une ancre correcte et unique à cet emplacement.

**Méthode de vérification qui a permis de l'attraper :** recherche de TOUTES les occurrences de chaque ancre (pas seulement `count() == 1` sur le fichier final, mais aussi les NUMÉROS DE LIGNE de chaque match) pour confirmer que les 5 ancres visent bien 5 emplacements distincts avant d'exécuter quoi que ce soit — pas seulement après échec.

---

### ✅ Chantier créé : registre CACES à plat — backend (2026-07-05, commit ab7e9c4)

**Fichiers :** `app/routers/registre_caces.py` (nouveau), `app/main.py` (2 lignes : import + `include_router`).

**Objectif :** une vue à plat de TOUS les `CacesObtenu` (hors `statut='annule'`), destinée à une page de relance/complément (societe, échéances, nature d'obtention) — pas encore de front à ce stade, back seul livré.

**Route `GET /api/registre-caces?seuil=6` :**
- `_nature(co)` : 3 valeurs — `"otc"` (interne, y compris CACES repris puisqu'ils n'ont pas `organisme_externe`), `"st"` (externe + `sous_traitance=True`), `"ext"` (externe sans sous-traitance). Réutilise les 2 champs posés au chantier `4dae010`.
- `_statut_echeance(ech, aujourdhui, seuil_mois)` : `"exp"` (échéance dépassée), `"ren"` (échéance dans les `seuil_mois` prochains mois, défaut 6), `"val"` (au-delà, ou `date_echeance` NULL — cas CACES repris legacy sans échéance connue).
- Anti-N+1 : `stagiaires` et `sessions` préchargés en dict `{id: obj}` avant la boucle sur les `CacesObtenu`.
- `numero` affiché : `ancien_numero` (reprise) sinon `numero_ordre` formaté sur 4 chiffres — même règle que partout ailleurs dans l'app (H5).
- Tri par défaut : échéance croissante, `None` (pas d'échéance) relégué en fin de liste.
- Réponse : `{seuil, aujourdhui, total, societes[], familles[], lignes[]}` — `societes`/`familles` = listes dédupliquées triées, destinées à peupler des menus déroulants côté front (à construire).

**Chemin d'exécution de la commande fourni corrigé avant lancement :** le script démarrait par `cd ~/caces-app` (racine parente contenant aussi des scripts Python hors-repo comme `calcul_fiche_reco.py`) au lieu de `~/caces-app/caces-app` (le vrai dépôt git, utilisé partout ailleurs dans cette session) — `git pull`, la création du fichier et les 2 `sed` sur `app/main.py` auraient tous visé le mauvais répertoire ou échoué. Corrigé en repartant du bon répertoire avant exécution.

**Faux échec de vérification (pas un bug réel) :** l'étape `python -c "ast.parse(open('app/main.py').read())"` du script fourni a levé `UnicodeDecodeError` — `open()` sans `encoding=` utilise `cp1252` par défaut sous Windows, incompatible avec les accents/emojis UTF-8 du fichier. Les 2 `sed -i` (edits réels) avaient déjà réussi et étaient corrects (`sed` traite les octets, insensible à l'encodage tant que motif/remplacement sont ASCII) — seule la vérification Python était en cause. Revérifié avec `io.open(..., encoding="utf-8")`, confirmé valide, poursuite manuelle du commit/push interrompu par le `&&` cassé.

**RESTE À FAIRE :** aucun front pour l'instant — page dédiée à construire (tableau + filtres société/famille/nature + surlignage selon `statut_echeance`).

### ✅ Chantier terminé : page `/registre-caces` — front complet (2026-07-05, commit 965554a)

**Fichiers :** `templates/registre_caces.html` (nouveau), `static/js/registre_caces.js` (nouveau, IIFE), `app/main.py` (route page + `_GESTION_PATHS` + garde `_verifier_role`), `templates/base.html` (entrée sidebar).

**Page :** tableau triable (colonnes cliquables `data-action="rc-sort"`), 3 filtres (société/famille/nature via `<select>` peuplés dynamiquement depuis la réponse API), recherche texte, 3 cases à cocher pour le statut d'échéance (Expiré/À renouveler/Valide — "Valide" décoché par défaut, les 2 autres cochés : la page s'ouvre centrée sur ce qui nécessite une action), 3 boutons de seuil de relance (3/6/12 mois) qui redéclenchent un fetch avec le nouveau seuil. Tout en CSP-safe (`data-action`, aucun `onclick` inline), cohérent avec la règle du projet.

**Accès :** page ajoutée à `_GESTION_PATHS` (comme `/statistiques`, `/caces-obtenus`...) → réservée admin/utilisateur, terrain redirigé. Garde symétrique sur l'API : `path.startswith("/api/registre-caces")` ajouté à la même condition dans `_verifier_role` — sans ce garde, un terrain authentifié aurait pu appeler l'API JSON directement même en étant bloqué sur la page HTML (incohérence déjà vue et corrigée sur d'autres routes du projet).

**Sidebar :** entrée "📇 Registre CACES®" insérée juste après "🏆 CACES® Obtenus", cohérent avec l'ordre logique (CACES obtenus → registre transversal → cartes).

**⚠️ Fonctionnalité non câblée à surveiller (RÉSOLU — voir chantier export ci-dessous) :** le bouton "⬇️ Exporter Excel" (`registre_caces.js:exporter()`) construit une URL vers `/api/registre-caces/export?...` — cette route n'existait pas côté serveur au moment de ce chantier front. Cliquer sur le bouton renvoyait un 404.

### ✅ Chantier terminé : export Excel `/api/registre-caces/export` (2026-07-05, commit 14b80b1)

**Fichiers :** `requirements.txt` (+`openpyxl==3.1.5`), `app/routers/registre_caces.py` (nouvelle route + imports `datetime`, `BytesIO`, `StreamingResponse`).

**Comble le trou signalé au chantier précédent :** le bouton front appelait déjà cette URL, qui renvoyait 404. Route ajoutée avec la même signature de filtres que le JS envoie (`seuil`, `soc`, `fam`, `nat`, `txt`, `exp`/`ren`/`val` en `"0"`/`"1"`).

**Fonctionnement :** appelle directement `registre_caces(seuil=seuil, db=db)` (fonction Python, pas une requête HTTP) pour récupérer le jeu complet, puis réapplique EXACTEMENT la même logique de filtrage que `registre_caces.js:render()` (société, famille, nature, texte, cases à cocher statut d'échéance) — les 2 implémentations (JS et Python) doivent rester synchronisées si les règles de filtrage changent un jour, sinon export et affichage écran divergeront silencieusement.

**Mise en forme du fichier Excel (`openpyxl`) :** en-tête fond anthracite `#2D2D2D`/texte blanc gras (charte NORYX), colonne Statut colorée par ligne (rouge `#A32D2D` expiré / ambre `#854F0B` à renouveler / vert `#3B6D11` valide — mêmes couleurs que les pastilles à l'écran), largeurs de colonnes fixées, `freeze_panes="A2"` (ligne d'en-tête figée au défilement), ligne de pied italique grise résumant les filtres actifs + horodatage + nombre de lignes exportées (traçabilité de ce qui a été extrait).

**Téléchargement :** `StreamingResponse` avec `Content-Disposition: attachment`, nom de fichier horodaté `registre_caces_{YYYYMMDD_HHMM}.xlsx` — cohérent avec le pattern déjà en place pour l'export ZIP session (`export-zip`).

**`openpyxl` installé et vérifié importable en environnement de dev** (`pip install openpyxl==3.1.5`, sans le flag `--break-system-packages` du script fourni — inutile sur ce Python Windows non « externally-managed », omis sans incident).

**Cette fois, aucun bug d'ancre côté front** (fichiers neufs, pas de remplacement dans du texte existant) — les seuls écueils rencontrés étaient d'infrastructure (répertoire de travail, heredoc bash imbriqué cassé sur les guillemets multiples de `registre_caces.js`, faux échec d'encodage Windows sur la vérification) — voir plus bas.

**Écueils d'infrastructure rencontrés et contournés :**
1. **Répertoire de travail erroné** (2e fois consécutive sur ce type de script) : la commande démarrait par `cd ~/caces-app` au lieu de `~/caces-app/caces-app`. Corrigé avant exécution.
2. **Heredoc bash cassé** sur la première tentative (`unexpected EOF`) — script unique combinant 2 `cat > fichier << EOF` (HTML + JS) et 4 blocs `python3 - << PYEOF` dans une seule commande bash compound trop longue et trop riche en guillemets/apostrophes imbriqués. Contourné en écrivant les 2 fichiers neufs via l'outil `Write` (pas de heredoc) et les 4 modifications `main.py`/`base.html` via un script Python unique dans un fichier temporaire exécuté séparément — aucune perte de contenu, juste une exécution mieux compartimentée. Rien n'avait été écrit avant l'échec (vérifié via `git status` — bash valide la syntaxe du compound command AVANT d'exécuter quoi que ce soit).
3. **Faux échec de vérification** : la commande de validation finale du script fourni utilisait `python -c "ast.parse(open(...).read())"` sans encodage — même piège `UnicodeDecodeError` (cp1252 Windows) déjà rencontré et documenté au chantier précédent. Corrigé préventivement cette fois en utilisant `io.open(..., encoding="utf-8")` dès le départ, sans attendre l'échec.

### ✅ Chantier terminé : téléphone + email dans l'export Excel du registre CACES (2026-07-05, commit d0c1fab)

**Fichier :** `app/routers/registre_caces.py`

**Ajout :** 2 colonnes "Telephone" et "Email" dans l'export Excel, entre "Societe" et "Famille" — lues directement sur `Stagiaire.telephone`/`Stagiaire.email` (déjà chargé dans le dict `stagiaires` de `registre_caces()`, aucune requête supplémentaire). Champs ajoutés au JSON de la vue `GET /api/registre-caces` (rétrocompatible — le front `registre_caces.js` ignore simplement ces nouvelles clés qu'il ne consomme pas encore, aucune régression d'affichage écran).

**3 ajustements mécaniques synchronisés (14 colonnes désormais au lieu de 12) :** liste `entetes` (+2 titres), tuple `ws.append([...])` (+2 valeurs à la même position), `largeurs` (+2 largeurs), et **décalage de l'index de la colonne colorée** (`cell_sta = ws.cell(..., column=11)` → `column=13`, puisque "Statut" est repoussé de la 11e à la 13e position). Vérifié par comptage : 14 en-têtes = 14 valeurs = 14 largeurs, colonne 13 = "Statut" (confirmé par position dans la liste `entetes`).

**Répétition des mêmes écueils d'infrastructure** (3e fois consécutive sur ce type de script) : répertoire de travail erroné (`~/caces-app` au lieu de `~/caces-app/caces-app`) et vérification finale sans encodage UTF-8 — les deux anticipés et corrigés avant exécution, sans incident cette fois (contrairement au chantier `965554a` où le 2e problème avait cassé le heredoc bash). Cette fois le script Python était appliqué via un fichier temporaire écrit par `Write`, pas un heredoc bash direct — plus aucun risque de ce type depuis l'adoption systématique de cette méthode.

### ✅ Chantier terminé : cartes mobiles stagiaires en grille 2 colonnes (2026-07-05, commit 6240289)

**Fichier :** `templates/stagiaires.html`

**Bug :** en mode carte responsive (`<1024px`), les 4 cellules `td[data-label]` (Né(e) le, Employeur, Email, Tél.) utilisaient `flex: 1 1 130px` — chaque cellule s'étirait pour occuper l'espace disponible plutôt que de former une grille régulière, donnant un rendu visuellement désorganisé (largeurs incohérentes selon le contenu).

**Correctif :** `flex: 0 0 50%` (au lieu de `1 1 130px`) + `box-sizing: border-box` + `max-width: 50%` — force exactement 2 cellules par ligne, sans étirement (le `0` en `flex-grow` empêche toute cellule de prendre plus de place que sa moitié, quel que soit son contenu). Padding vertical légèrement augmenté (5px → 6px) pour compenser visuellement la mise en grille.

**Séparateur visuel ajouté :** `border-left` sur `.stag-employeur` et `.stag-tel` (les 2 cellules de la colonne de droite dans l'ordre du DOM : Né(e)le|Employeur puis Email|Tél.) — liseré vertical `#e8f0f8` cohérent avec le `border-top` déjà en place entre les lignes, complète visuellement le quadrillage 2×2.

**Vérifié avant application :** `flex-wrap: wrap` déjà présent sur `.table-stagiaires tbody tr:not(.hist-row)` (posé lors d'un chantier antérieur) — condition nécessaire pour que `flex: 0 0 50%` produise effectivement 2 colonnes plutôt qu'un simple rétrécissement sur une seule ligne.

### ✅ Chantier terminé : dates Th./Pr. sous la référence de session en responsive (2026-07-05, commit c436859)

**Fichiers :** `static/js/stagiaires.js` (`renderHistorique`, ligne 406), `templates/stagiaires.html`.

**Contexte :** différent du chantier précédent (cartes de la table principale) — ici c'est l'en-tête cliquable de chaque session dans l'historique déplié d'un stagiaire (référence session, famille, badge statut, dates Théorie/Pratique), affiché sur une seule ligne `flex` avec `margin-left:auto` pour pousser les dates à droite.

**Bug :** en dessous de 1023px, le span des dates (`dates.join(' · ')`) restait poussé à droite sur la même ligne que la référence/famille/badge → débordement hors de la carte sur petit écran, la ligne étant trop chargée pour la largeur disponible.

**Correctif :** classe `sess-dates` ajoutée au span (JS) + règle CSS dans le `@media (max-width:1023px)` de `stagiaires.html` : `margin-left:0 !important` (annule le `margin-left:auto` inline qui poussait à droite), `flex:0 0 100%` (force le passage à la ligne, pleine largeur), séparateur visuel `border-top` en pointillés — les dates apparaissent désormais sous la ligne référence/famille/badge plutôt qu'à côté.

**Vérifié avant application :** un seul appel à `dates.join(' · ')` dans tout le fichier (confirmé par diagnostic), donc l'ajout de la classe ne pouvait toucher que ce span précis. Ancre CSS d'insertion (`.toolbar-left`/`#search`) confirmée être bien à l'intérieur du même bloc `@media (max-width:1023px)` que le reste des règles responsive de cette page (vérifié par recherche de l'accolade `@media` englobante avant application, pas juste par correspondance textuelle).

### ✅ Chantier terminé : scroll horizontal des tableaux à colonnes fixes en responsive (2026-07-05, commits 5d0b1b4 + ad677eb)

**Fichiers :** `static/js/stagiaires.js` (`_sectionCaces`, `renderCartesEmises`), `templates/stagiaires.html` (classe `.co-hscroll`).

**Bug :** `_sectionCaces` (tableaux "CACES de l'apprenant") et `renderCartesEmises` (tableau "Cartes émises") utilisent tous deux une structure à colonnes de largeur FIXE (`width:60px`, `flex:1`, `width:84px`...) — sur petit écran, ces colonnes se faisaient couper/chevaucher au lieu de s'adapter, aucun mécanisme de secours.

**Correctif :** classe `.co-hscroll` (CSS : `overflow-x:auto` + `-webkit-overflow-scrolling:touch` pour l'inertie tactile iOS, `> div { min-width:460px }` pour empêcher l'écrasement des colonnes) ajoutée en `<style>` dans `stagiaires.html`, juste avant le premier `@media`. Chaque tableau enveloppé d'une `<div class="co-hscroll">` supplémentaire autour de son conteneur `border:1px solid #c8d8f0...` existant — un scroll horizontal apparaît sous 460px de large plutôt qu'un rendu cassé.

**Portée volontairement limitée à 2 fonctions sur 4 candidates :** `renderCacesExternes` et `renderOrphelinesReprises` (les 2 rubriques "Historique de reprise") utilisent un patron structurellement DIFFÉRENT — des lignes `flex` avec `flex-wrap:wrap` (le même patron `.repr-ident`/`.repr-dates`/`.repr-actions` posé aux chantiers `45b5b98`/`a787633`) qui se replient déjà nativement sur petit écran, sans colonnes de largeur fixe à préserver. Les envelopper dans `.co-hscroll` n'aurait eu aucun effet utile (pas de contenu à faire défiler, puisque rien n'est tronqué) — vérifié par lecture du code des 2 fonctions avant de les exclure, pas par supposition.

**Piège de comptage anticipé :** le motif d'ouverture `border:1px solid #c8d8f0;border-radius:10px;overflow:hidden;` suivi de `display:flex;...background:#f0f2f7;...` existe à l'identique dans `_sectionCaces` ET `renderCartesEmises` (2 occurrences) — mais avec un détail différenciant (`gap:0;` présent uniquement dans `renderCartesEmises`), ce qui a permis de construire 2 ancres distinctes sans ambiguïté. Idem pour la fermeture (`html += '</div></div>';\n return html;\n }`, 2 occurrences avant traitement) — vérifié par recherche des NUMÉROS DE LIGNE de chaque occurrence pour confirmer qu'elles appartiennent bien à 2 fonctions séparées (443→488 pour `_sectionCaces`, 759→802 pour `renderCartesEmises`) avant tout remplacement séquentiel (`.replace(..., 1)` ne traite que la première occurrence trouvée — l'ordre d'apparition dans le fichier doit être connu à l'avance, pas supposé).

### ✅ Chantier terminé : confinement du scroll horizontal dans la carte stagiaire (2026-07-05, commit 7668894)

**Fichiers :** `static/js/stagiaires.js` (détail carte CACES, `chargerCacesCarteStag` ~l.841), `templates/stagiaires.html` (`.hist-body`, règles `.hist-row`).

**3e tableau à colonnes fixes trouvé et enveloppé :** le détail dépliable d'une carte CACES émise (liste des CACES de cette carte, affichée en cliquant ▶ sur une ligne de `renderCartesEmises`) avait la MÊME structure à colonnes fixes que les 2 tableaux traités au chantier précédent (`_sectionCaces`, `renderCartesEmises`) — mais générée par une fonction distincte (`chargerCacesCarteStag`, chargement asynchrone au clic), donc non couverte par les 2 premiers correctifs. Enveloppé dans `.co-hscroll` de la même façon.

**Confinement structurel additionnel (au-delà du simple wrapping) :** même avec les 3 tableaux enveloppés, le scroll horizontal pouvait déborder du cadre visuel de la carte stagiaire elle-même sur très petit écran, car `#hist-body-{{ s.id }}` (le conteneur qui héberge tout l'historique déplié) avait un padding fixe `12px 20px` (non responsive) et `tr.hist-row td` n'avait pas de `overflow:hidden` pour contenir un enfant plus large que lui. Corrigé par 3 règles ajoutées dans `@media (max-width:1023px)` : `overflow:hidden` sur `tr.hist-row td` (empêche tout débordement visuel du contenu enfant hors de la cellule), `.hist-body { padding:10px 8px !important }` (réduit l'espace perdu sur les bords, maximise la largeur utile pour le contenu et son scroll), `.table-stagiaires tbody tr.hist-row .co-hscroll { max-width:100% }` (borne explicitement chaque zone de scroll à la largeur du conteneur parent, jamais au-delà).

**Bilan du chantier `.co-hscroll` (3 commits cumulés : `5d0b1b4`, `ad677eb`, `7668894`) :** 3 tableaux à colonnes fixes protégés (`_sectionCaces`, `renderCartesEmises`, détail carte), scroll confiné dans le cadre visuel de la carte stagiaire sur mobile. `renderCacesExternes`/`renderOrphelinesReprises` restent exclus (patron flex-wrap déjà adéquat, cf. chantier précédent).

### ✅ Chantier terminé : confinement structurel `table/tbody/tr` en responsive (2026-07-05, commit a0c3a04)

**Fichier :** `templates/stagiaires.html`

**Dernier verrou du débordement mobile :** malgré les 3 tableaux internes protégés (chantier précédent), l'élément racine `<table class="table-stagiaires">` lui-même n'avait aucune contrainte de largeur en mode carte responsive — `thead{display:none}` et `tbody{display:block}` étaient posés, mais ni la `<table>` ni ses `<tr>` n'avaient de `max-width:100%`, laissant une voie de débordement résiduelle si un contenu interne (ex. un `.co-hscroll` mal contenu) forçait malgré tout la largeur du parent.

**Correctif (dans `@media max-width:1023px`) :** `.table-stagiaires { display:block; width:100%; max-width:100%; table-layout:fixed }`, `tbody { width:100%; max-width:100% }`, `tbody tr { max-width:100%; box-sizing:border-box }` — chaîne de contraintes de largeur du parent vers l'enfant, aucun maillon ne peut plus déborder. Renforcement symétrique de `.hist-body` et `.co-hscroll` (déjà posés au chantier précédent) : `width:100%; max-width:100%; box-sizing:border-box` ajoutés pour qu'ils respectent activement la largeur imposée plutôt que de simplement la plafonner passivement.

**Détail cosmétique relevé, non corrigé (inerte, pas un bug) :** `table-layout:fixed` est déclaré sur un sélecteur qui a par ailleurs `display:block` — cette propriété n'a d'effet que sur un élément affiché en `display:table` (ou apparenté). Sur cet élément passé en `block`, elle est silencieusement ignorée par le navigateur. Aucune conséquence fonctionnelle (les autres contraintes `width`/`max-width` font le travail), mais à savoir si ce sélecteur repasse un jour en affichage tableau.

### ✅ Chantier terminé : abandon du scroll horizontal au profit de cartes empilées, sur les 3 tableaux `.co-hscroll` (2026-07-05, commit 5c0ba6d)

**Fichiers :** `static/js/stagiaires.js` (`_sectionCaces`, `renderCartesEmises`, `chargerCacesCarteStag`), `templates/stagiaires.html` (CSS).

**Changement de stratégie :** le scroll horizontal posé sur 3 commits (`5d0b1b4`, `ad677eb`, `7668894`) est remplacé par un empilement en cartes (comme `.repr-row`/`.cext-row` avant lui) — plus de geste de scroll requis sur mobile, tout le contenu est visible verticalement.

**⚠️ Risque de régression détecté et corrigé AVANT de committer :** le script initial ne convertissait QUE `_sectionCaces` (classes `csec-*` + CSS dédiée) mais désactivait `.co-hscroll` **globalement** (`overflow-x:visible !important` sans scoping). Comme `renderCartesEmises` et `chargerCacesCarteStag` (détail d'une carte, popup au clic ▶) utilisent aussi `.co-hscroll` sans avoir reçu de classes de repli, cette désactivation globale aurait **supprimé leur protection existante sans rien pour la remplacer** — leurs colonnes à largeur fixe seraient revenues à un rendu cassé sur mobile, annulant silencieusement 2 des 3 chantiers précédents. Signalé à l'utilisateur avant application ; décision prise d'étendre le même traitement aux 2 tableaux restants plutôt que de scoper la règle CSS à `_sectionCaces` seul.

**Extension réalisée (au-delà du script fourni) :**
- `renderCartesEmises` (5 colonnes : toggle ▶, N° Carte, Famille, Émission, Statut) → classes `carte-head-row`/`carte-row`/`carte-toggle`/`carte-num`/`carte-fam`/`carte-em`/`carte-sta`.
- `chargerCacesCarteStag` (7 colonnes : Cat., Libellé, Options, N°, Obtention, Échéance, Testeur) → classes `cdet-head-row`/`cdet-row`/`cdet-cat`/`cdet-lib`/`cdet-opt`/`cdet-no`/`cdet-obt`/`cdet-ech`/`cdet-test`.
- CSS : approche volontairement plus simple que celle de `_sectionCaces` (pas de groupement 2-3 lignes pixel-perfect imposé) — reset générique des largeurs fixes (`width:auto !important; min-width:0 !important`) + `flex-wrap:wrap` + préfixes `::before` sur les champs secondaires (`data-label`) pour garder le contexte visuel une fois les colonnes reflow. Suffisant pour éliminer tout débordement/coupure, sans viser la même polish visuelle que le tableau CACES (qui avait un design explicite fourni).

**Ancre CSS mouvante (2e fois sur ce fichier le même jour) :** l'ancre `.toolbar-left`/`#search` fournie par le script ne correspondait plus au fichier réel — le chantier `c436859` (dates Th./Pr.) avait entretemps inséré `.sess-dates {...}` juste après `#search`, décalant la position de la accolade fermante `}` du bloc `@media`. Diagnostiqué par recherche de contenu (`grep`) avant application plutôt que blocage sur l'assertion — nouvelle ancre reconstruite sur le contenu réel (`.sess-dates {...}\n}`).

**Bilan cumulé responsive stagiaires.html (2026-07-05, 6 chantiers) :** grille 2 colonnes cartes (`6240289`) → dates Th./Pr. sous la référence (`c436859`) → scroll horizontal 3 tableaux (`5d0b1b4`+`ad677eb`) → confinement scroll dans la carte (`7668894`) → confinement structurel table/tbody/tr (`a0c3a04`) → **abandon du scroll pour un empilement en cartes sur les 3 mêmes tableaux (`5c0ba6d`)**. Le scroll horizontal aura été une étape intermédiaire, pas la solution finale retenue.

### ✅ Chantier terminé : lien de consultation manquant sur l'attestation prévention + uniformisation icônes documents testeur (2026-07-06, commit 7bfb441)

**Fichiers :** `templates/testeurs.html`, `static/js/testeurs.js`.

**Bug fonctionnel corrigé (pas seulement cosmétique) :** parmi les 4 blocs documents de la modale testeur (attestation prévention, visite médicale, évaluation, autorisation de conduite), 3 avaient déjà un lien 📥 "Consulter" (`modal-visite-dl`, `modal-eval-dl`, `modal-autorisation-dl`) — mais **l'attestation prévention n'en avait jamais eu** : upload et suppression étaient possibles, mais aucun moyen de consulter le fichier déjà enregistré. Ajouté `<a id="modal-prev-dl">` sur le modèle des 3 autres, branché dans `editer()` (`static/js/testeurs.js`) : `href` construit dynamiquement (`/api/upload/attestation-prevention/${id}/download`, route confirmée existante dans `app/routers/upload.py`), affiché/masqué en miroir de `btn-suppr-prev` selon `hasPrev`.

**Uniformisation visuelle des 4 blocs :** tous les boutons "Consulter" (📥), "Supprimer" (🗑️) et "Uploader" (📤) passent en icône seule sans fond (`background:none;border:none`), cohérent avec le style déjà adopté sur les autres boutons de cette page (crayon/corbeille de ligne, boutons "Nouveau"). Avant : mélange de classes `btn btn-secondary`/`btn btn-danger` avec texte, tailles de police (11px) et paddings incohérents entre les 4 blocs.

---

### ✅ Chantier terminé : date d'expiration optionnelle sur une carte testeur, à l'upload (2026-07-06, commit f8a2149)

**Fichiers :** `templates/testeurs.html` (modale "Ajouter une carte"), `app/routers/upload.py` (route `POST /cartes-testeur/{testeur_id}`), `static/js/testeurs.js`.

**Suite directe du chantier précédent** (`carte_testeur.date_expiration`, commit `f8c520a`) : le champ existe désormais en base, cette étape permet de le RENSEIGNER à l'upload et de le RENVOYER dans la liste des cartes (`GET .../cartes-testeur/{id}` → `"date_expiration": c.date_expiration.isoformat() if ... else None`).

**Back :** `date_expiration: str = Form(None)` ajouté à la signature (import `Form` ajouté à `from fastapi import ...`, absent jusque-là dans ce fichier). Parsing défensif : `date.fromisoformat(date_expiration)` dans un `try/except ValueError` → `None` si le format est invalide plutôt qu'un 500. Champ optionnel de bout en bout (aucun contrôle bloquant si absent).

**Bug fonctionnel corrigé, hors script fourni :** le script ne livrait que le champ HTML + la route backend — **le JS ne lisait ni n'envoyait jamais le nouveau champ** (`fd.append('file', ...)` seul dans le `FormData`, rien pour `date_expiration`). Sans ce correctif, la date saisie dans la modale ne serait JAMAIS arrivée au serveur : le paramètre `Form(None)` aurait systématiquement reçu `None`, la fonctionnalité aurait semblé exister visuellement tout en étant inopérante. Corrigé en ajoutant `fd.append('date_expiration', expiration)` (si renseigné) dans le handler `ajouter-carte-confirm`.

**2e point d'ouverture de la modale corrigé également :** la modale "Ajouter une carte" a DEUX déclencheurs distincts dans ce fichier — `btn-modal-ajouter-carte` (bouton dans la modale d'édition testeur) et `data-action="carte-ajouter"` (délégation globale, indentation différente donc non détecté par un simple remplacement textuel sur l'autre bloc). Les deux réinitialisent maintenant `ajouter-carte-expiration` à l'ouverture, pour éviter qu'une date saisie puis annulée ne persiste visuellement à la prochaine ouverture via l'autre chemin.

**Leçon reconduite (déjà notée au chantier `a16de65`) :** un script qui ajoute un champ de formulaire + une route backend n'est complet que si le lien JS entre les deux (lecture du champ, inclusion dans la requête) est aussi vérifié — la présence d'un champ HTML ne garantit jamais qu'il est effectivement transmis.

---

### ✅ Chantier terminé : affichage + édition inline de la date d'expiration carte testeur (2026-07-06, commit 2182186)

**Fichiers :** `app/routers/upload.py` (route `PATCH /carte/{carte_id}/date-expiration`), `templates/testeurs.html` (carte dépliée + template caché des cartes), `static/js/testeurs.js` (rendu modale + édition inline).

**Suite du chantier `f8a2149`** (date d'expiration à l'upload) : cette étape ajoute l'AFFICHAGE (pastille colorée sur la carte dépliée, seuils 90/180 jours restants → rouge/orange/vert) et l'ÉDITION après coup, sans passer par un ré-upload — clic sur la pastille dans la modale → `<input type="date">` inline → `PATCH` au blur/Enter, sans PIN (donnée jugée non critique, à la différence de la plupart des autres actions de cette page).

**Route `PATCH /carte/{carte_id}/date-expiration` :** corps JSON `{date_expiration: "AAAA-MM-JJ" | ""}` via `pydantic.BaseModel` (1er usage de Pydantic dans `upload.py` — import ajouté). Chaîne vide → `NULL` en base (permet d'effacer une date déjà saisie). Date invalide → 400 avec message clair, jamais un 500.

**⚠️ 3e chantier consécutif où le script fourni contenait un bug fonctionnel réel, cette fois un TYPE D'ERREUR NOUVEAU (pas une ancre décalée ni un JS non câblé, mais une garde de script trop générique) :** l'étape 2/4 (ajout de `data-expiration` sur le `<div data-carte-id="...">` caché, qui alimente `c.dataset.expiration` en JS) contenait une garde `if "data-expiration=" in t: skip`. Cette recherche de sous-chaîne a matché un attribut **totalement différent, déjà présent ailleurs dans le même fichier** (`data-expiration="{{ t.date_expiration_habilitation or '' }}"`, ligne 84 — l'expiration de l'HABILITATION du testeur, un champ sans rapport) → le script a conclu à tort que son propre ajout était "déjà présent" et a sauté l'écriture réelle. Résultat si non détecté : toute la fonctionnalité d'affichage/édition de la partie 4 (qui lit `c.dataset.expiration`) aurait semblé fonctionner (aucune erreur JS, aucun crash) tout en affichant systématiquement "exp. —" pour toutes les cartes, quelle que soit la donnée réelle en base — un bug **silencieux**, sans message d'erreur nulle part, détecté uniquement par relecture manuelle du fichier après exécution (`grep 'data-carte-id="{{ c.id }}"'` a montré l'attribut manquant). Corrigé en appliquant le remplacement directement via l'outil `Edit`.

**Généralisation de la leçon :** les gardes anti-double-application de type `if "<motif>" in fichier: skip` sont un piège dès que le motif recherché n'est pas EXCLUSIVEMENT lié au changement visé — toujours préférer une recherche du texte APRÈS remplacement complet (`new_string in fichier`) plutôt qu'un fragment générique (`"data-expiration=" in fichier`) qui peut matcher un homonyme ailleurs dans un fichier de 900+ lignes. Vérifier le résultat final par `grep` sur l'anchor MODIFIÉE (pas seulement sur l'absence d'erreur) reste la seule garantie fiable.

---

### ✅ Chantier terminé : crash JS bloquant en rôle terrain sur la page testeurs (2026-07-06, commit 3362a84)

**Fichier :** `static/js/testeurs.js`

**Bug réel diagnostiqué avant correction (pas supposé sur la seule foi du script fourni) :** `templates/testeurs.html` n'a que 3 blocs `{% if user_role != 'terrain' %}` (lignes 15, 66, 72) — dont un seul concerne un élément ciblé par `document.getElementById()` en JS : le bouton `btn-nouveau-testeur` (ligne 15-17). Pour le rôle terrain, ce bouton n'existe pas dans le DOM → `document.getElementById('btn-nouveau-testeur').addEventListener(...)` (ligne 8 du fichier JS, exécutée tôt dans le handler `DOMContentLoaded`) levait une `TypeError` non interceptée, qui **interrompait l'exécution de tout le reste du script** — y compris l'attache des listeners de dépliage de carte testeur (`toggle-carte`, en délégation plus loin dans le fichier). Symptôme observé : impossible de déplier une carte testeur en rôle terrain, sans message d'erreur visible côté utilisateur (seule la console navigateur montrait la `TypeError`).

**Correction :** chaque accès direct `document.getElementById(id).addEventListener(...)` sur les 8 boutons/éléments du haut de fichier (`search`, `btn-changer-etat`, `btn-nouveau-testeur`, `btn-sauvegarder`, `btn-fermer-modal`, `btn-fermer-pin`, `btn-fermer-prevention`, `btn-fermer-controle`) + le bloc "Attestation prévention" (`btn-upload-prevention`, `modal-prev-file`, `btn-suppr-prev`) passe par une variable intermédiaire avec garde `if (el) el.addEventListener(...)`.

**Précision importante (vérifiée avant application, pas après) :** sur les 9 accès sécurisés, **un seul était la cause réelle du crash** (`btn-nouveau-testeur`) — les 8 autres éléments existent TOUJOURS dans le DOM, quel que soit le rôle (aucun n'est dans un bloc conditionnel Jinja). Leur sécurisation est un durcissement défensif sans effet fonctionnel observable (les `if` sont systématiquement vrais), pas un correctif supplémentaire de bug. Distinction faite en amont via lecture complète des `{% if user_role %}` du template avant d'accepter le diagnostic du script tel quel.

**Règle à retenir pour ce fichier :** toute nouvelle condition `{% if user_role != 'terrain' %}` ajoutée autour d'un élément dans `testeurs.html` DOIT être accompagnée d'une garde `if (el)` sur l'`addEventListener` correspondant dans `testeurs.js`, sous peine de reproduire ce même crash silencieux pour le rôle terrain.

**Cas concret de cette règle appliquée dès le chantier suivant (2026-07-06, commit `584c8e8`) :** masquage de la barre de recherche `#search` + case "œil inactifs" pour le terrain (nouveau bloc `{% if user_role != 'terrain' %}` dans `.toolbar-left`). Avant d'appliquer, vérifié que `filtrer()` (`static/js/testeurs.js`) lit `document.getElementById('search').value` **sans garde**, et surtout qu'elle est appelée **sans condition dès `DOMContentLoaded`** (ligne 6, `filtrer();`) — donc AVANT même les gardes `if (el)` déjà posées sur les autres boutons. Sans le correctif jumeau (`const _s = document.getElementById('search'); if (!_s) return;`), masquer la barre de recherche aurait immédiatement reproduit le crash documenté ci-dessus, cette fois pour TOUS les rôles terrain dès le chargement de la page (pas seulement au clic sur un bouton). Les deux parties du script (template + JS) livrées et vérifiées dans le même commit — jamais l'une sans l'autre sur ce fichier.

---

## Sauvegarde base de données

**Filet de securite principal = Render natif** (dashboard base `caces-db` > Recovery) : Point-in-Time Recovery (3 jours Hobby, 7 jours Pro) + Export logique (retention 7j) + bouton "Restore database" integre. C'est la reference d'exploitation, rien a coder.

**Bouton `/admin/export-base` (usage ADMIN interne, editeur) :** `pg_dump` streame cote serveur (pas de fichier temporaire, RGPD). Securise par TOKEN a usage unique : POST `/admin/export-base/token` valide le PIN (dans le body) et renvoie un token ephemere (60s), le GET `/admin/export-base?token=...` telecharge. Le PIN ne transite JAMAIS dans l'URL. Limite : tokens en memoire (mono-instance) ; a migrer vers stockage partage si passage en autoscaling.

**ATTENTION multi-tenant :** `pg_dump` exporte TOUTE la base (tous schemas/tenants). NE PAS exposer ce bouton aux OTC clients tel quel (fuite inter-tenants). Reserve a l'admin editeur. Chantier futur : export par-tenant (`--schema=`) pour la portabilite RGPD client. Doctrine RGPD "par personne" (droit d'acces art.15, effacement art.17) = chantier distinct ; l'effacement bute sur l'immutabilite des cartes CACES emises (conservation legale) -> a arbitrer avec DPO.

## Maintenance — Reset des données de production

**Script :** `reset_donnees_of.py` (racine du dépôt) — remet à zéro les données liées à l'activité OF en **conservant le référentiel**. Idempotent (relancé sur base propre = « rien à supprimer »). Confirmation interactive obligatoire : taper `RESET`. Technique : `TRUNCATE ... RESTART IDENTITY CASCADE` (l'ordre des FK est géré par PostgreSQL ; aucune table conservée ne pointe vers une table vidée).

**Lancement :** `python reset_donnees_of.py` sur le Render Shell (après déploiement du script).

**CONSERVE (référentiel + comptes + fiches) :** `familles`, `categories`, `option_categorie`, `grilles_theorie`, `reponses_grilles`, grilles pratique (`grille_pratique`, `theme_pratique`, `point_evaluation`, `item_pratique`, `critere_eliminatoire`), `config_organisme`, `document_officiel`, `utilisateurs`, `lieux`, `stagiaires` (fiches sans historique), `testeurs`, `habilitations_testeurs`, `habilitation_option`, `lieu_habilitations`, `carte_testeur`, `association_log`, `association_audio_log`.

**VIDE (production + tirages) :** `sessions`, `jours_test`, `jour_test_candidats`, `resultats_theorie`, `brouillons_theorie`, `session_candidats`, `session_epreuves`, `caces_obtenus`, `carte_caces`, `fiche_recommandation`, `consentements_rgpd`, `attestations_neutralite`, `justificatifs`, `non_conformites`, `saisie_pratique`, `saisie_bloc`, `saisie_item_note`, `saisie_eliminatoire`, `jours_formation`, `affectations_formation`, `planning_apprenants`, `affectations_test`, `utilisations_grilles`, `utilisations_themes`, `reset_tirage`, `equipements`.

**Notes :**
- Les audios IA, images de questions et photos stagiaires sur Cloudinary ne sont **jamais** touchés (la base ne stocke que les URLs).
- `config_organisme` est conservé → le compteur `prochain_numero_caces` garde sa valeur. Remise à 1 = manuelle via Administration → Paramètres.
- Sauvegarde recommandée avant exécution : `pg_dump "$DATABASE_URL" --no-owner --no-acl -f /tmp/backup_$(date +%Y%m%d_%H%M).sql` sur le Render Shell.

---


### ✅ R.486 double voix (audio H/F) — chantier complet (2026-07-06)

**Principe :** chaque question théorique dispose de deux pistes audio — voix masculine (Rémi) et féminine (Léa), générées par Amazon Polly (neural, eu-west-3). Colonne `audio_url` = voix Homme (défaut), nouvelle colonne `audio_url_f` = voix Femme.

**Nommage fichiers :** `R486_G{grille}_T{theme}_Q{numero}_{H|F}.mp3` (suffixe voix en 5e position, lu par `upload.py` via `parts[4]`). Échantillons d'intro : `R486_ECHANTILLON_{H|F}.mp3`.

**Réglages génération (`generer_audio_r486.py`) :** SSML, débit 95%, sigles épelés à la française (PEMP, EPI, VGP, GPL, ROPS, FOPS, SMS, CE, AIPR), CACES prononcé « quacèsse », catégories A/B/C et types 1A/3B épelés, N→Newton, classe II→classe 2, km/h→kilomètre heure, kV→kilovolts, [1]→repère 1, [Carsat/Cramif/CGSS]→Carsat, CMU développé.

**Commits :** migration colonne (6952f2f), modèle ORM (33787fc), upload _H/_F (a5b7816), exposition audio_f (c886bd3), front tablette (d5aa1b7), projection salle (73ed447), script génération audio (0600544), auto-migration démarrage (bd4c034).

**Migration prod : automatique.** `audio_url_f` est dans `_run_startup_migrations` (`app/main.py`, à côté de `audio_url`) → la colonne est créée au prochain déploiement, aucune commande manuelle sur Render Shell requise. Le script `migrate_audio_url_f.py` reste dispo en secours/local (SQLite : les `ADD COLUMN IF NOT EXISTS` du démarrage échouent en WARN non-fatal, syntaxe non supportée par SQLite mais OK en PostgreSQL).

**Ergonomie :**
- Tablette (timer global) : choix de voix à l'écran d'identité (hors timer) + mini-switch 👨/👩 à côté de « Réécouter » pour réécouter une question dans l'autre voix. Le switch n'affecte pas le timer (global, pas par question).
- Projection salle (déroulé auto, timer par question) : boutons 👨 Homme / 👩 Femme dans la barre de contrôle, bouton actif surligné en rouge.
- Fallback : `_urlSelonVoix` retombe sur l'autre voix si la voulue manque, puis synthèse navigateur si aucun MP3.

**À faire pour étendre à R.482 :** aucune modif code (infra générique). Générer les MP3 `R482_..._{H|F}.mp3` + échantillons, uploader, associer.

