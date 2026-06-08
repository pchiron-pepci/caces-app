# CACES® Manager — Documentation projet

Application de gestion des certifications CACES® pour PEPCI Formation.

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
| `stagiaires.py` | `/api/stagiaires` | CRUD stagiaires |
| `sessions.py` | `/api/sessions` | Gestion sessions CACES® |
| `admin.py` | `/admin` | Catégories, habilitations, lieux |
| `auth.py` | `/auth` | Login JWT |
| `upload.py` | — | Import fichiers |
| `statistiques.py` | — | Stats/rapports |

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
- Utilisé pour : archiver un testeur, supprimer/activer des habilitations, clôturer une session, retirer un candidat
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

---

## Règles métier

1. **UT testeur** : max 6 UT/testeur/jour
2. **Machines** : alerte si > 7 UT/catégorie/jour → `ceil(UT/7)` machines recommandées
3. **Résultats théorie** : jamais écrasés, traçabilité totale
4. **Meilleur résultat réussi** affiché sur la carte CACES® avec sa date
5. **Grilles INRS** : règle 10-30% par thème, comptage sur jours actifs uniquement
6. **Identité candidat** : case à cocher (non bloquante) dans la modal saisie résultat pratique
7. **Suppression d'un jour** : supprime aussi les `ResultatTheorie` et `SessionEpreuve` liés
8. **Retrait candidat d'un jour** : supprime `ResultatTheorie` ET `SessionEpreuve` des catégories du jour
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
| `SessionEpreuve` | `sessions_epreuves` | résultat pratique par catégorie ; `options_obtenues` VARCHAR(200) CSV — options obtenues lors de l'épreuve ; suppression hard delete via `DELETE /api/sessions/{session_id}/epreuves/{epreuve_id}?pin=1505` |
| `ResultatTheorie` | `resultats_theorie` | jamais écrasé |
| `HabilitationTesteur` | `habilitations_testeurs` | hard delete ; `option_pe`/`option_tel` legacy — remplacés par `HabilitationOption` |
| `OptionCategorie` | `option_categorie` | table de référence des options disponibles par famille/catégorie ; codes : PE=Porte-engins, TEL=Télécommande, CC=Conduite cabine, TR=Translation sur rails, CEC=Circulation en charge ; peuplé par `init_options.py` |
| `HabilitationOption` | `habilitation_option` | options actives par habilitation (habilitation_id FK, code_option) ; modifiable avec PIN 1505 via `PUT /admin/habilitation/{id}/options` |
| `Testeur` | `testeurs` | soft delete (`actif`) ; `etat` : actif/suspendu/sorti — modifiable avec PIN 1505 via `PUT /api/testeurs/{id}/etat`, défaut actif à la création ; docs PDF en base64 : `attestation_prevention_pdf/nom/date`, `visite_medicale_pdf/nom/visite_medicale_date`, `evaluation_pdf/nom/evaluation_date`, `autorisation_conduite_pdf/nom`, `carte_pdf/carte_nom_fichier` (legacy) |
| `CarteTesteur` | `carte_testeur` | multi-cartes par testeur, soft delete (`actif`) ; champs : `famille`, `nom_fichier`, `contenu_pdf` base64, `date_upload` |
| `ConfigOrganisme` | `config_organisme` | singleton (1 ligne) ; `nom_organisme`, `logo_base64` (image base64), `logo_nom` ; `audit_interne_date`, `audit_externe_date`, `revue_direction_date` (Date nullable) ; affiché via Jinja2 globals `nom_organisme()`, `logo_organisme()`, `get_config_organisme()` |
| `Stagiaire` | `stagiaires` | soft delete (`actif`) |
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
| Haute | Cartes CACES® PDF (format CR80, reportlab) | à faire |
| Haute | Annuler/supprimer résultat épreuve pratique (avec PIN) | ✅ fait |
| Haute | Jours de formation (nouveau type, UT personnalisés) | à faire |
| Haute | Journal non-conformités/réclamations — page /non-conformites + modèle NonConformite + carte dashboard | ✅ fait |
| Haute | Options CACES® (PE, TEL, CC, TR, CEC) sur épreuves pratiques — planification + résultats | ✅ fait |
| Moyenne | Externaliser JS inline de admin.html (contrainte CSP) | à faire |
| Moyenne | Grilles R486, R489 (scripts init à créer) | à faire |
| Moyenne | Multi-tenant (subdomain routing, database-per-tenant) | à faire |

### Décision architecturale : multi-tenant Cloudinary
**Option A retenue — un compte Cloudinary distinct par tenant.**
- Credentials `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` stockés dans les variables d'environnement de chaque instance Render, ou dans une table `tenant_config` en base.
- Au provisioning d'un nouveau tenant : créer un compte Cloudinary gratuit et renseigner les 3 credentials.
| Basse | Responsive mobile (CSS media queries) | à faire |
| Basse | UT options = 0 (actuellement 0.5 par défaut) | à faire |
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

### Note : doublons date_habilitation / date_expiration_habilitation
`Testeur.date_habilitation` et `Testeur.date_expiration_habilitation` sont des doublons avec `HabilitationTesteur` — à supprimer dans une passe de nettoyage ultérieure après vérification qu'ils ne sont utilisés nulle part (modèle, routes, templates, migrations).

### Chantier en cours : suppression habilitation (hard delete)
Objectif : ajouter un bouton 🗑️ dans la modal de modification d'un testeur existant pour supprimer définitivement une habilitation (hard delete SQL + PIN 1505).

Fichiers à modifier :
- `app/routers/admin.py` — route `DELETE /admin/habilitation/{id}` : ajouter `pin`, vérification PIN, remplacer soft delete par `db.delete()`
- `templates/admin.html` — `demanderPin()` : passer `pin` au callback ; `desactiverHabTesteur()` : transmettre `?pin=` à l'API
- `templates/testeurs.html` — ajouter divs cachés `#habs-{id}` + section `#section-habs-modal` dans la modal
- `static/js/testeurs.js` — `editer()` : peupler la liste habilitations ; ajouter `supprimerHab()` + handler `supprimer-hab`
