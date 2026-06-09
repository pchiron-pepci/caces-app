# NORYX Engins — Documentation projet

Application de pilotage CACES® & Autorisation de conduite pour PEPCI Formation.

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
| `cartes_caces.py` | `/api/cartes-caces` | Cartes CACES® (préparation, émission, annulation) |
| *(main.py)* | `/verifier/{numero_carte}` | Page publique de vérification — pas de login requis |

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
- Jamais écrasés — chaque passage crée un nouvel enregistrement (`ResultatTheorie`)
- Traçabilité totale : tous les passages sont conservés
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

---

## Règles métier

1. **UT testeur** : max 6 UT/testeur/jour
2. **Machines** : alerte si > 7 UT/catégorie/jour → `ceil(UT/7)` machines recommandées
1b. **UT options** : chaque option planifiée/réalisée ajoute **0.5 UT** au total du jour — calculé dans `session_detail.js:calculerRecapUT()` (options cochées `jp-opt-{id}-{cat}`), `main.py` (total_ut planifié + ut_planifie_candidat via `options_planifiees`), `sessions.py:add_epreuve` (ut = cat.ut_pratique + nb_options × 0.5) ; affiché dans Cartographie admin comme lignes ↳ rattachées à leur catégorie (0.5 UT chacune)
3. **Résultats théorie** : jamais écrasés, traçabilité totale
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
| `Famille` | `familles` | R482, R483, R484, R485, R486, R487, R489, R490 |
| `Categorie` | `categories` | `ut_pratique`, `pepci_habilite`, `est_option` |
| `Session` | `sessions` | `famille`, `lieu_id`, `statut`, `reference` |
| `JourTest` | `jours_test` | `type` = theorie/pratique, `grille_id` |
| `JourTestCandidat` | `jours_test_candidats` | `categories` en CSV ; `options_planifiees` JSON Text `{"CAT": ["PE","TEL"], ...}` — options sélectionnées à la planification |
| `SessionEpreuve` | `sessions_epreuves` | résultat pratique par catégorie ; `options_obtenues` VARCHAR(200) CSV ; `bloque` Boolean défaut False — positionné lors d'une annulation CACES® avec motif "Non conforme"/"CACES® annulé" + case cochée, empêche la re-création auto du CacesObtenu ; suppression hard delete via `DELETE /api/sessions/{session_id}/epreuves/{epreuve_id}?pin=1505` |
| `ResultatTheorie` | `resultats_theorie` | jamais écrasé ; `bloque` Boolean défaut False — positionné comme SE, empêche la recherche de théorie dans `calculer_et_synchroniser` |
| `HabilitationTesteur` | `habilitations_testeurs` | hard delete ; `option_pe`/`option_tel` legacy — remplacés par `HabilitationOption` |
| `OptionCategorie` | `option_categorie` | table de référence des options disponibles par famille/catégorie ; codes : PE=Porte-engins, TEL=Télécommande, CC=Conduite cabine, TR=Translation sur rails, CEC=Circulation en charge ; peuplé par `init_options.py` |
| `HabilitationOption` | `habilitation_option` | options actives par habilitation (habilitation_id FK, code_option) ; modifiable avec PIN 1505 via `PUT /admin/habilitation/{id}/options` |
| `Testeur` | `testeurs` | soft delete (`actif`) ; `etat` : actif/suspendu/sorti — modifiable avec PIN 1505 via `PUT /api/testeurs/{id}/etat`, défaut actif à la création ; docs PDF en base64 : `attestation_prevention_pdf/nom/date`, `visite_medicale_pdf/nom/visite_medicale_date`, `evaluation_pdf/nom/evaluation_date`, `autorisation_conduite_pdf/nom`, `carte_pdf/carte_nom_fichier` (legacy) |
| `CarteTesteur` | `carte_testeur` | multi-cartes par testeur, soft delete (`actif`) ; champs : `famille`, `nom_fichier`, `contenu_pdf` base64, `date_upload` |
| `ConfigOrganisme` | `config_organisme` | singleton (1 ligne) ; `nom_organisme`, `logo_base64` (image base64), `logo_nom` ; `adresse` Text, `siret` VARCHAR(20), `email` VARCHAR(200), `telephone` VARCHAR(50) ; `signataire_nom`, `signataire_prenom`, `signataire_qualite` VARCHAR(100) ; `signature_base64` Text, `signature_nom` VARCHAR(200) (image signature upload) ; `url_verification_caces` VARCHAR(500) (optionnel, si non renseigné → défaut `https://caces-app.onrender.com/verifier/`) — utilisé par `_build_verify_url()` pour construire `verify_url = base + numero_carte` passé dans `config.verify_url` au frontend JS (QR code recto) ; `audit_interne_date`, `audit_externe_date`, `revue_direction_date` (Date nullable) ; `pin_formateur` VARCHAR(20) défaut "1234" — PIN saisi par le formateur pour débloquer "Ce n'est pas moi" dans test_theorie.html, vérifié via `POST /admin/config/verifier-pin-formateur`, modifiable dans Administration → Paramètres avec PIN admin 1505 ; `prochain_numero_caces` Integer défaut 1 — prochain numéro attribué lors de la validation d'un CACES® (affiché sur 4 chiffres : 0001, 0002…), incrémenté auto à chaque `POST /api/caces-obtenus/valider/{id}`, configurable dans Administration → Paramètres ; routes : `POST /admin/config-organisme/signature` + `DELETE /admin/config-organisme/signature` (upload/suppression image signature, PIN 1505) ; affiché via Jinja2 globals `nom_organisme()`, `logo_organisme()`, `get_config_organisme()` |
| `Stagiaire` | `stagiaires` | soft delete (`actif`) |
| `CacesObtenu` | `caces_obtenus` | statut : `a_valider`/`valide`/`annule` ; `numero_ordre` (Integer unique, attribué à la validation) ; `motif_annulation` Text nullable ; UNIQUE(stagiaire_id, session_id, categorie) ; routes : GET `/api/caces-obtenus/a-valider` (sync + liste), GET `/api/caces-obtenus/valides` (trié : validé en haut, annulé en bas), POST `/api/caces-obtenus/valider/{id}?pin=` (attribue numéro incrémental, bouton "📜 Émettre le CACES®"), POST `/api/caces-obtenus/annuler/{id}?pin=` body `{motif, bloquer_pratique: bool, bloquer_theorie: bool}` (statut→`annule`, si `bloquer_pratique` → `SessionEpreuve.bloque=True`, si `bloquer_theorie` → `ResultatTheorie.bloque=True` pour tous les RT obtenue=True du stagiaire dans la session, motif "Erreur administrative" : ne bloque rien + recréation auto au prochain /a-valider), PATCH `/api/caces-obtenus/{id}/motif?pin=` body `{motif}` (mise à jour motif_annulation) ; au prochain appel `/a-valider` les records `annule` repassent en `a_valider` seulement si SE/RT non bloqués ; modal annulation : select obligatoire (Erreur administrative / Non conforme / CACES® annulé / Autre) + cases à cocher visibles pour Non conforme et CACES® annulé uniquement ; service `app/services/caces_obtenus.py` → `calculer_et_synchroniser(db)` (filtre `SE.bloque != True` et `RT.bloque != True`) |
| `CarteCaces` | `carte_caces` | `stagiaire_id` FK, `famille`, `numero_carte` (unique, format `PEPCI-{YY}-{NNNNN}`, incrément annuel remis à zéro), `date_generation`, `statut` (`en_preparation` legacy/`emise`/`remplacee`/`annulee`), `motif_annulation`, `caces_json` Text (snapshot JSON des CacesObtenu au moment de l'émission : liste [{categorie, categorie_libelle, numero_ordre, options_obtenues, date_obtention, date_echeance, testeur_nom}]) — **une carte émise est figée définitivement** : le snapshot `caces_json` stocké à l'émission est la source de vérité ; les CACES® validés/annulés après l'émission n'affectent pas cette carte ; pour une carte à jour → générer une nouvelle carte (l'ancienne passe en `remplacee`) ; **pas de blocage de l'annulation CACES® par une carte émise** — une carte est une photo statique, l'organisme est responsable de réémettre si nécessaire ; page `/cartes-caces` — workflow : select stagiaire → familles filtrées → tableau CACES® validés → bouton Générer et imprimer (PIN) → fenêtre impression CR80 (≤4 cats, 85.6×54mm) ou A5 landscape (>4 cats) — à l'impression la carte passe en `emise`, l'ancienne `emise` passe en `remplacee` ; section Cartes émises : ▶/▼ déplie snapshot, boutons 🖨️ réimprimer + ❌ annuler uniquement sur `emise` ; badges : ✅ Émise / 📷 Remplacée / ❌ Annulée ; routes : `GET /stagiaires`, `GET /familles/{stag_id}`, `GET /caces-valides/{stag_id}/{famille}`, `POST /emettre/{stag_id}/{famille}?pin=`, `GET /{id}/caces` (retourne snapshot ou fallback legacy), `GET /reimprimer/{id}`, `GET /emises`, `POST /annuler/{id}?pin=` body {motif}, `GET /{id}/pdf` (PDF CR80 recto/verso protégé — WeasyPrint (rendu HTML CR80 identique au template JS) + pypdf (permissions_flag=2052, impression seule), téléchargement direct) ; **page publique** : `GET /verifier/{numero_carte}` (main.py, pas de login) — template `verifier.html` standalone (pas de base.html) — affiche titulaire + tableau CACES® si `emise`, bandeau avertissement si `annulee`/`remplacee`, message d'erreur si introuvable |
| `DocumentOfficiel` | `document_officiel` | singleton par type (`certificat_organisme`, `attestation_assurance`, `procedure_interne`) ; champs : `contenu_pdf` base64, `nom_fichier`, `date_validite`, `numero_certificat` (certificat_organisme uniquement) ; Jinja2 globals `numero_certificat()`, `date_validite_certificat()` (retourne date formatée dd/mm/YYYY ou "") |
| `GrilleTheorie` | `grilles_theorie` | grilles INRS |
| `ReponseGrille` | `reponses_grille` | questions par grille |
| `NonConformite` | `non_conformites` | journal des non-conformités et réclamations ; champs : `reference` (String unique, format "NC-AAAA-NNN", généré auto à la création, incrément annuel remis à zéro chaque année), `date`, `declarant_id` (FK Utilisateur), `origine` (interne/reclamation_client/reclamation_apprenant/audit), `type_nc` (incident/non-conformite/observation), `nature` (documentaire/materiel/organisationnel, nullable), `titre`, `description`, `action_preventive`, `action_corrective`, `justificatif_pdf` base64, `justificatif_nom`, `statut` (ouvert/en_cours/cloture/sans_objet, défaut ouvert ; badges : rouge/orange/vert/gris), `date_cloture` ; liens optionnels `session_id`, `testeur_id`, `stagiaire_id` (FK nullable) ; routes : POST `/api/non-conformites`, PUT `/api/non-conformites/{id}` (403 si statut cloture/sans_objet — rouvrir d'abord), PATCH `/api/non-conformites/{id}/cloturer` (PIN 1505), PATCH `/api/non-conformites/{id}/sans-objet` (PIN 1505, pose aussi `date_cloture`), PATCH `/api/non-conformites/{id}/rouvrir` (PIN 1505, remet statut à `ouvert` et efface `date_cloture`), GET `/api/non-conformites/{id}/justificatif` ; page `/non-conformites` dans nav après Statistiques ; liste dépliable (référence, date, titre, badge statut) ; carte dépliable avec actions préventive/corrective stylisées, justificatif PDF téléchargeable ; dashboard : carte "Non-conformités ouvertes" dans la grille 2-col + ligne 3-col en dessous |

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
| Basse | Responsive mobile (CSS media queries) | à faire |
| Basse | UT options = 0.5 par option planifiée/réalisée | ✅ fait |
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

### Chantier en cours : suppression habilitation (hard delete)
Objectif : ajouter un bouton 🗑️ dans la modal de modification d'un testeur existant pour supprimer définitivement une habilitation (hard delete SQL + PIN 1505).

Fichiers à modifier :
- `app/routers/admin.py` — route `DELETE /admin/habilitation/{id}` : ajouter `pin`, vérification PIN, remplacer soft delete par `db.delete()`
- `templates/admin.html` — `demanderPin()` : passer `pin` au callback ; `desactiverHabTesteur()` : transmettre `?pin=` à l'API
- `templates/testeurs.html` — ajouter divs cachés `#habs-{id}` + section `#section-habs-modal` dans la modal
- `static/js/testeurs.js` — `editer()` : peupler la liste habilitations ; ajouter `supprimerHab()` + handler `supprimer-hab`
