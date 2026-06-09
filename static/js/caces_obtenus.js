document.addEventListener('DOMContentLoaded', function () {

    chargerAValider();
    chargerValides();

    document.getElementById('btn-refresh').addEventListener('click', function () {
        chargerAValider();
        chargerValides();
    });

    // --- PIN modal ---
    document.getElementById('btn-pin-annuler').addEventListener('click', fermerPin);
    document.getElementById('pin-input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') document.getElementById('btn-pin-confirmer').click();
    });
    document.getElementById('modal-pin').addEventListener('click', function (e) {
        if (e.target === this) fermerPin();
    });

    // --- Motif modal ---
    document.getElementById('btn-motif-annuler').addEventListener('click', fermerMotif);
    document.getElementById('btn-motif-confirmer').addEventListener('click', _confirmerMotif);
    document.getElementById('modal-motif').addEventListener('click', function (e) {
        if (e.target === this) fermerMotif();
    });
    document.getElementById('motif-select').addEventListener('change', function () {
        const label = document.getElementById('motif-detail-label');
        const hint = document.getElementById('motif-hint');
        if (this.value === 'CACES® annulé') {
            label.innerHTML = 'Détail <span style="color:#888; font-weight:400;">(optionnel)</span>';
            hint.textContent = 'Le CACES® est invalidé suite à une décision réglementaire ou administrative. Vous pouvez bloquer les résultats sources pour empêcher toute re-certification automatique.';
        } else if (this.value === 'Autre') {
            label.innerHTML = 'Détail <span style="color:#c62828;">*</span>';
            hint.textContent = 'Décrivez le motif dans le champ ci-dessous. Les résultats sources restent valides — un nouveau CACES® sera recalculé automatiquement.';
        } else {
            label.innerHTML = 'Détail <span style="color:#888; font-weight:400;">(optionnel)</span>';
            hint.textContent = '';
        }
        const showBlocage = (this.value === 'CACES® annulé');
        document.getElementById('motif-blocage-section').style.display = showBlocage ? 'block' : 'none';
        if (!showBlocage) {
            document.getElementById('chk-bloquer-pratique').checked = false;
            document.getElementById('chk-bloquer-theorie').checked = false;
        }
        document.getElementById('motif-erreur').textContent = '​';
    });

    // --- Délégation clics ---
    document.addEventListener('click', function (e) {

        // Émettre le CACES® (carte à valider)
        const btnValider = e.target.closest('[data-action="valider-caces"]');
        if (btnValider) {
            const id = parseInt(btnValider.dataset.id);
            const nom = btnValider.dataset.nom;
            ouvrirPin('Émettre le CACES® de ' + nom + ' ?', async function (pin) {
                const r = await fetch('/api/caces-obtenus/valider/' + id + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
                if (r.ok) {
                    const data = await r.json();
                    _apresValider(id, data.numero_ordre);
                }
                return r;
            });
            return;
        }

        // Révision sans motif (carte à valider uniquement)
        const btnRevision = e.target.closest('[data-action="revision-caces"]');
        if (btnRevision) {
            const id = parseInt(btnRevision.dataset.id);
            const nom = btnRevision.dataset.nom;
            ouvrirPin('Remettre en révision le CACES® de ' + nom + ' ?', async function (pin) {
                const r = await fetch('/api/caces-obtenus/annuler/' + id + '?pin=' + encodeURIComponent(pin), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ motif: null }),
                });
                if (r.ok) _apresRevisionCarte(id);
                return r;
            });
            return;
        }

        // Annuler CACES® validé (liste validés — motif obligatoire)
        const btnAnnuler = e.target.closest('[data-action="annuler-caces"]');
        if (btnAnnuler) {
            const id = parseInt(btnAnnuler.dataset.id);
            const nom = btnAnnuler.dataset.nom;
            const categorie = btnAnnuler.dataset.categorie || '';
            const famille = btnAnnuler.dataset.famille || '';
            ouvrirMotif('Motif de l\'annulation du CACES® de ' + nom, '', function ({ motif, bloquerPratique, bloquerTheorie }) {
                fermerMotif();
                ouvrirPin('Confirmer l\'annulation du CACES® de ' + nom + ' ?', async function (pin) {
                    const r = await fetch('/api/caces-obtenus/annuler/' + id + '?pin=' + encodeURIComponent(pin), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motif: motif, bloquer_pratique: bloquerPratique, bloquer_theorie: bloquerTheorie }),
                    });
                    if (r.ok) _apresAnnulation(id, motif);
                    return r;
                });
            }, categorie, famille);
            return;
        }

        // Toggle sources validés
        const btnVToggle = e.target.closest('[data-action="toggle-vsources"]');
        if (btnVToggle) {
            const id = btnVToggle.dataset.id;
            const src = document.getElementById('vsources-' + id);
            const arr = document.getElementById('varrow-' + id);
            const ouvert = src.style.display === 'flex';
            src.style.display = ouvert ? 'none' : 'flex';
            arr.textContent = ouvert ? '▶' : '▼';
            return;
        }

        // Voir / modifier motif (ligne annulée)
        // Tri colonnes CACES® validés
        const btnSort = e.target.closest('[data-action="sort-valides"]');
        if (btnSort) {
            const key = btnSort.dataset.key;
            if (_sortKey === key) {
                _sortDir = -_sortDir;
            } else {
                _sortKey = key;
                _sortDir = (key === 'numero_ordre' || key === 'date_obtention' || key === 'date_echeance') ? -1 : 1;
            }
            _renderValides();
            return;
        }

        const btnMotif = e.target.closest('[data-action="voir-motif"]');
        if (btnMotif) {
            const id = parseInt(btnMotif.dataset.id);
            const nom = btnMotif.dataset.nom || '';
            const motifActuel = (_validesData[id] && _validesData[id].motif_annulation) || '';
            ouvrirMotif('Motif d\'annulation' + (nom ? ' — ' + nom : ''), motifActuel, function ({ motif }) {
                fermerMotif();
                ouvrirPin('Modifier le motif ?', async function (pin) {
                    const r = await fetch('/api/caces-obtenus/' + id + '/motif?pin=' + encodeURIComponent(pin), {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motif: motif }),
                    });
                    if (r.ok && _validesData[id]) _validesData[id].motif_annulation = motif;
                    return r;
                });
            });
        }
    });
});

// ===== ÉTAT =====
let _pinCallback = null;
let _motifCallback = null;
let _motifCategorie = '';
let _motifFamille = '';
const _carteData = {};
const _validesData = {};
let _validesArray = [];
let _sortKey = 'numero_ordre';
let _sortDir = -1; // -1 = desc

const _SORT_COLS = [
    { key: 'stagiaire',      label: 'Stagiaire' },
    { key: 'famille',        label: 'Famille' },
    { key: 'categorie',      label: 'Catégorie' },
    { key: 'numero_ordre',   label: 'N°' },
    { key: 'date_obtention', label: 'Obtention' },
    { key: 'date_echeance',  label: 'Échéance' },
    { key: 'statut',         label: 'Statut' },
];

// ===== PIN MODAL =====
function ouvrirPin(titre, callback) {
    _pinCallback = callback;
    document.getElementById('pin-titre').textContent = titre;
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-erreur').textContent = '';
    document.getElementById('modal-pin').style.display = 'flex';
    setTimeout(function () { document.getElementById('pin-input').focus(); }, 50);

    document.getElementById('btn-pin-confirmer').onclick = async function () {
        const pin = document.getElementById('pin-input').value.trim();
        if (!pin) return;
        const btn = document.getElementById('btn-pin-confirmer');
        btn.disabled = true;
        btn.textContent = '...';
        try {
            const r = await _pinCallback(pin);
            if (r.ok) {
                fermerPin();
            } else {
                const data = await r.json().catch(() => ({}));
                document.getElementById('pin-erreur').textContent = data.detail || 'Erreur';
            }
        } finally {
            btn.disabled = false;
            btn.textContent = 'Confirmer';
        }
    };
}

function fermerPin() {
    document.getElementById('modal-pin').style.display = 'none';
    _pinCallback = null;
}

// ===== MOTIF MODAL =====
const _MOTIF_OPTS = ['CACES® annulé'];

function _parseMotif(stored) {
    for (const opt of _MOTIF_OPTS) {
        if (stored === opt) return { select: opt, detail: '' };
        if (stored.startsWith(opt + ' — ')) return { select: opt, detail: stored.slice(opt.length + 3) };
    }
    return { select: stored ? 'Autre' : '', detail: stored || '' };
}

function ouvrirMotif(titre, motifInitial, onConfirme, categorie, famille) {
    _motifCallback = onConfirme;
    _motifCategorie = categorie || '';
    _motifFamille = famille || '';
    document.getElementById('motif-titre').textContent = titre;
    const parsed = _parseMotif(motifInitial || '');
    const sel = document.getElementById('motif-select');
    sel.value = parsed.select;
    document.getElementById('motif-input').value = parsed.detail;
    const label = document.getElementById('motif-detail-label');
    label.innerHTML = parsed.select === 'Autre'
        ? 'Détail <span style="color:#c62828;">*</span>'
        : 'Détail <span style="color:#888; font-weight:400;">(optionnel)</span>';
    const showBlocage = (parsed.select === 'CACES® annulé');
    document.getElementById('motif-blocage-section').style.display = showBlocage ? 'block' : 'none';
    const hint = document.getElementById('motif-hint');
    if (parsed.select === 'CACES® annulé') {
        hint.textContent = 'Le CACES® est invalidé suite à une décision réglementaire ou administrative. Vous pouvez bloquer les résultats sources pour empêcher toute re-certification automatique.';
    } else if (parsed.select === 'Autre') {
        hint.textContent = 'Décrivez le motif dans le champ ci-dessous.';
    } else {
        hint.textContent = '';
    }
    document.getElementById('chk-bloquer-pratique').checked = false;
    document.getElementById('chk-bloquer-theorie').checked = false;
    if (_motifCategorie) document.getElementById('chk-pratique-label').textContent = 'Bloquer le résultat pratique (catégorie ' + _motifCategorie + ')';
    if (_motifFamille) document.getElementById('chk-theorie-label').textContent = 'Bloquer le résultat théorique (famille ' + _motifFamille + ')';
    document.getElementById('motif-erreur').textContent = '​';
    document.getElementById('modal-motif').style.display = 'flex';
    setTimeout(function () { sel.focus(); }, 50);
}

function fermerMotif() {
    document.getElementById('modal-motif').style.display = 'none';
    _motifCallback = null;
}

function _confirmerMotif() {
    const sel = document.getElementById('motif-select').value;
    const detail = document.getElementById('motif-input').value.trim();
    if (!sel) {
        document.getElementById('motif-erreur').textContent = '⚠️ Veuillez choisir un motif.';
        return;
    }
    if (sel === 'Autre' && !detail) {
        document.getElementById('motif-erreur').textContent = '⚠️ Le détail est obligatoire pour "Autre".';
        return;
    }
    const motif = detail ? sel + ' — ' + detail : sel;
    const bloquerPratique = document.getElementById('chk-bloquer-pratique').checked;
    const bloquerTheorie = document.getElementById('chk-bloquer-theorie').checked;
    if (_motifCallback) _motifCallback({ motif, bloquerPratique, bloquerTheorie });
}

// ===== UTILITAIRES =====
function fmtDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y;
}

function badgeStatut(statut) {
    if (statut === 'valide') return '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">Validé</span>';
    if (statut === 'annule') return '<span class="badge" style="background:#fde8e8;color:#c62828;">Annulé</span>';
    return '';
}

// ===== TRI & RENDU VALIDÉS =====

function _renderHeaderValides() {
    const cols = _SORT_COLS.map(function (col) {
        const active = _sortKey === col.key;
        const arrow = active ? (_sortDir === 1 ? ' ▲' : ' ▼') : '';
        return '<span data-action="sort-valides" data-key="' + col.key + '" '
            + 'style="font-size:11px; font-weight:' + (active ? '800' : '600') + '; '
            + 'color:' + (active ? '#1a237e' : '#888') + '; '
            + 'cursor:pointer; user-select:none; text-transform:uppercase; letter-spacing:0.4px; '
            + 'padding:4px 8px; border-radius:4px; '
            + 'background:' + (active ? '#e8eaf6' : 'transparent') + '; '
            + 'white-space:nowrap;">'
            + col.label + arrow
            + '</span>';
    }).join('<span style="color:#ddd; margin:0 2px;">|</span>');

    return '<div style="display:flex; align-items:center; flex-wrap:wrap; gap:2px; '
        + 'background:#f7f8fc; border-radius:8px; padding:6px 10px; margin-bottom:10px; '
        + 'border:1px solid #e8eef8;">'
        + '<span style="font-size:10px; color:#aaa; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-right:6px;">Trier&nbsp;:</span>'
        + cols
        + '</div>';
}

function _sortValides(arr) {
    return arr.slice().sort(function (a, b) {
        let va, vb;
        switch (_sortKey) {
            case 'stagiaire':      va = (a.stagiaire_nom + ' ' + a.stagiaire_prenom).toLowerCase(); vb = (b.stagiaire_nom + ' ' + b.stagiaire_prenom).toLowerCase(); break;
            case 'famille':        va = a.famille || ''; vb = b.famille || ''; break;
            case 'categorie':      va = a.categorie || ''; vb = b.categorie || ''; break;
            case 'numero_ordre':   va = a.numero_ordre || 0; vb = b.numero_ordre || 0; break;
            case 'date_obtention': va = a.date_obtention || ''; vb = b.date_obtention || ''; break;
            case 'date_echeance':  va = a.date_echeance || ''; vb = b.date_echeance || ''; break;
            case 'statut':         va = a.statut || ''; vb = b.statut || ''; break;
            default:               va = 0; vb = 0;
        }
        if (va < vb) return -1 * _sortDir;
        if (va > vb) return  1 * _sortDir;
        return 0;
    });
}

function _renderValides() {
    const headerEl = document.getElementById('header-valides');
    const listEl = document.getElementById('liste-valides');
    if (!headerEl || !listEl) return;

    if (!_validesArray.length) {
        headerEl.innerHTML = '';
        listEl.innerHTML = '<p style="color:#718096; text-align:center; padding:24px;">Aucun CACES® validé.</p>';
        return;
    }

    headerEl.innerHTML = _renderHeaderValides();
    listEl.innerHTML = _sortValides(_validesArray).map(_renderLigne).join('');
}

// ===== RENDU CARTE À VALIDER =====
function renderCarteAValider(co) {
    _carteData[co.id] = co;
    const nomComplet = co.stagiaire_nom + ' ' + co.stagiaire_prenom;

    const options = co.options_obtenues
        ? co.options_obtenues.split(',').map(o => `<span style="background:#e8eaf6;color:#283593;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;">${o.trim()}</span>`).join(' ')
        : '';
    const optionsPratique = co.options_pratique
        ? co.options_pratique.split(',').map(o => `<span style="background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:1px 5px;font-size:11px;">${o.trim()}</span>`).join(' ')
        : '';

    const boutonsHtml = co.statut === 'annule'
        ? `<span style="background:#fff3e0;color:#e65100;border:2px solid #e65100;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;">↩ En révision — actualisez pour recalculer</span>`
        : `<button data-action="revision-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="background:#fff;border:2px solid #e65100;color:#e65100;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;">
                ↩ Révision
            </button>
            <button data-action="valider-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="background:#2e7d32;color:#fff;border:none;border-radius:8px;padding:8px 20px;font-size:13px;font-weight:700;cursor:pointer;">
                📜 Émettre le CACES®
            </button>`;

    return `
    <div id="caces-card-${co.id}" style="border:1px solid #c8d8f0;border-radius:12px;overflow:hidden;margin-bottom:12px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,0.06);">

        <!-- Header -->
        <div style="background:#f0f2f7;border-bottom:1px solid #dde3f0;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <a href="/stagiaires#${co.stagiaire_id}" target="_blank"
               style="font-size:15px;font-weight:700;color:#1a237e;text-decoration:none;">${nomComplet}</a>
            <span style="font-weight:700;color:#555;font-size:13px;background:#e8eaf6;padding:2px 8px;border-radius:4px;">${co.famille}</span>
            <span style="background:#1a237e;color:#fff;border-radius:6px;padding:2px 10px;font-size:13px;font-weight:800;">${co.categorie}</span>
            ${options}
        </div>

        <!-- Body 2 colonnes -->
        <div style="display:flex;align-items:stretch;">

            <!-- Gauche : dates -->
            <div style="width:190px;min-width:190px;padding:16px 18px;border-right:2px solid #e8eef8;background:#fafbff;display:flex;flex-direction:column;gap:14px;justify-content:center;">
                <div>
                    <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:4px;">📅 Obtention présumée</div>
                    <div style="font-size:18px;font-weight:800;color:#1a237e;">${fmtDate(co.date_obtention)}</div>
                </div>
                <div>
                    <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:4px;">⏳ Échéance</div>
                    <div style="font-size:16px;font-weight:700;color:#2e7d32;">${fmtDate(co.date_echeance)}</div>
                </div>
            </div>

            <!-- Droite : sources toujours visibles -->
            <div style="flex:1;padding:16px;display:flex;flex-direction:column;gap:8px;justify-content:center;">
                <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
                    <span style="width:70px;color:#666;font-weight:600;white-space:nowrap;">🎓 Théorie</span>
                    <a href="/sessions/${co.session_id_theorie}" target="_blank"
                       style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;font-size:12px;">${co.session_ref_theorie || '—'}</a>
                    <span style="color:#555;white-space:nowrap;font-size:12px;">${fmtDate(co.date_theorie)}</span>
                    <span style="color:#2e7d32;font-weight:700;">✅</span>
                    ${co.testeur_nom_theorie ? `<span style="font-size:11px;color:#777;white-space:nowrap;">| ${co.testeur_nom_theorie}</span>` : ''}
                </div>
                <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
                    <span style="width:70px;color:#666;font-weight:600;white-space:nowrap;">🔧 Pratique</span>
                    <a href="/sessions/${co.session_id_pratique}" target="_blank"
                       style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;font-size:12px;">${co.session_ref_pratique || '—'}</a>
                    <span style="color:#555;white-space:nowrap;font-size:12px;">${fmtDate(co.date_pratique)}</span>
                    <span style="color:#2e7d32;font-weight:700;">✅</span>
                    ${optionsPratique ? `<span style="display:flex;gap:3px;">${optionsPratique}</span>` : ''}
                    ${co.testeur_nom ? `<span style="font-size:11px;color:#777;white-space:nowrap;">| ${co.testeur_nom}</span>` : ''}
                </div>
            </div>

        </div>

        <!-- Footer : actions -->
        <div id="caces-card-${co.id}-actions"
             style="border-top:1px solid #f0f0f0;padding:10px 16px;display:flex;justify-content:flex-end;gap:10px;align-items:center;background:#fafbff;">
            ${boutonsHtml}
        </div>

    </div>`;
}

// ===== RENDU CARTE VALIDÉS =====

function _renderLigne(co) {
    const annule = co.statut === 'annule';
    const nomComplet = co.stagiaire_nom + ' ' + co.stagiaire_prenom;
    const noFormate = co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : null;

    const noBadge = noFormate
        ? (annule
            ? `<span style="font-family:monospace;font-size:13px;font-weight:700;text-decoration:line-through;color:#999;">${noFormate}</span>`
            : `<span style="background:#1a237e;color:#fff;border-radius:6px;padding:3px 8px;font-size:16px;font-weight:700;font-family:monospace;white-space:nowrap;">${noFormate}</span>`)
        : `<span style="color:#999;font-size:13px;">—</span>`;

    const options = co.options_obtenues
        ? co.options_obtenues.split(',').map(o => `<span style="background:#e8eaf6;color:#283593;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;">${o.trim()}</span>`).join(' ')
        : '';

    const testeurHtml = co.testeur_nom
        ? `<span style="font-size:12px;color:#555;">| Testeur&nbsp;: <strong>${co.testeur_nom}</strong></span>`
        : '';

    const actionHtml = annule
        ? `<button data-action="voir-motif" data-id="${co.id}" data-nom="${nomComplet}"
                title="${co.motif_annulation ? 'Motif : ' + co.motif_annulation.replace(/"/g, '&quot;') : 'Aucun motif'}"
                style="background:none;border:none;cursor:pointer;font-size:16px;padding:2px 4px;">📝</button>`
        : `<button data-action="annuler-caces" data-id="${co.id}" data-nom="${nomComplet}" data-categorie="${co.categorie}" data-famille="${co.famille}"
                style="background:#fff;border:2px solid #c62828;color:#c62828;border-radius:8px;padding:5px 12px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;">
                ↩ Annuler
            </button>`;

    const motifHtml = annule && co.motif_annulation
        ? `<div style="font-size:12px;color:#888;margin-top:4px;font-style:italic;">Motif : "${co.motif_annulation}"</div>`
        : '';

    const optionsPratique = co.options_pratique
        ? co.options_pratique.split(',').map(o => `<span style="background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:1px 5px;font-size:11px;">${o.trim()}</span>`).join(' ')
        : '';

    const sourcesHtml = `<div id="vsources-${co.id}" style="display:none;background:#f8f9ff;border-radius:8px;padding:10px 14px;margin-top:8px;flex-direction:column;gap:6px;">
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="width:70px;color:#666;font-weight:600;">🎓 Théorie</span>
            <a href="/sessions/${co.session_id_theorie}" target="_blank" style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;">${co.session_ref_theorie || '—'}</a>
            <span style="color:#444;white-space:nowrap;">${fmtDate(co.date_theorie)}</span>
            <span style="color:#2e7d32;font-weight:700;">✅</span>
            ${co.testeur_nom_theorie ? `<span style="font-size:12px;color:#555;">| Testeur&nbsp;: <strong>${co.testeur_nom_theorie}</strong></span>` : ''}
        </div>
        <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
            <span style="width:70px;color:#666;font-weight:600;">🔧 Pratique</span>
            <a href="/sessions/${co.session_id_pratique}" target="_blank" style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;">${co.session_ref_pratique || '—'}</a>
            <span style="color:#444;white-space:nowrap;">${fmtDate(co.date_pratique)}</span>
            <span style="color:#2e7d32;font-weight:700;">✅</span>
            <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span>
            ${optionsPratique ? `<span style="display:flex;gap:3px;">${optionsPratique}</span>` : ''}
            ${co.testeur_nom ? `<span style="font-size:12px;color:#555;">| Testeur&nbsp;: <strong>${co.testeur_nom}</strong></span>` : ''}
        </div>
    </div>`;

    const toggleHtml = `<button data-action="toggle-vsources" data-id="${co.id}"
            style="background:none;border:none;cursor:pointer;font-size:12px;color:#1a237e;font-weight:600;padding:0;display:flex;align-items:center;gap:4px;">
            <span id="varrow-${co.id}">▶</span> Voir les sources
        </button>`;

    return `<div data-caces-id="${co.id}" style="border:1px solid ${annule ? '#e8e8e8' : '#c8d8f0'};border-radius:12px;padding:10px 16px;margin-bottom:8px;background:#fff;${annule ? 'opacity:0.6;' : ''}box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            ${noBadge}
            ${badgeStatut(co.statut)}
            <span style="font-size:14px;font-weight:700;color:#1a237e;${annule ? 'text-decoration:line-through;' : ''}">${nomComplet}</span>
            <span style="font-weight:700;color:#1a237e;font-size:12px;">${co.famille}</span>
            <span style="background:#1a237e;color:#fff;border-radius:6px;padding:2px 8px;font-size:13px;font-weight:800;">${co.categorie}</span>
            ${options}
            ${testeurHtml}
            <span style="font-size:12px;color:#555;">📅 <strong>${fmtDate(co.date_obtention)}</strong></span>
            <span style="font-size:12px;color:#555;">⏳ <strong style="color:#2e7d32;">${fmtDate(co.date_echeance)}</strong></span>
            <span style="flex:1;"></span>
            ${toggleHtml}
            ${actionHtml}
        </div>
        ${motifHtml}
        ${sourcesHtml}
    </div>`;
}

// ===== MISES À JOUR DOM =====

function _apresValider(id, numeroOrdre) {
    const co = _carteData[id];
    const carte = document.getElementById('caces-card-' + id);
    if (carte) carte.remove();
    delete _carteData[id];
    const elAValider = document.getElementById('liste-a-valider');
    if (elAValider && !elAValider.querySelector('[id^="caces-card-"]')) {
        elAValider.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Aucun CACES® en attente de validation.</p>';
    }
    if (co) {
        co.numero_ordre = numeroOrdre;
        co.statut = 'valide';
        co.session_reference = co.session_ref_pratique || co.session_reference || '—';
        _validesData[co.id] = co;
        _validesArray.push(co);
        _renderValides();
    }
}

function _apresRevisionCarte(id) {
    const actionsEl = document.getElementById('caces-card-' + id + '-actions');
    if (actionsEl) {
        actionsEl.innerHTML = '<span style="background:#fff3e0;color:#e65100;border:2px solid #e65100;border-radius:10px;padding:10px 16px;font-size:13px;font-weight:700;">↩ En révision — actualisez pour recalculer</span>';
    }
}

function _apresAnnulation(id, motif) {
    const co = _validesData[id];
    if (co) {
        co.statut = 'annule';
        co.motif_annulation = motif;
    }
    _renderValides();
}


// ===== CHARGEMENT =====

async function chargerAValider() {
    const el = document.getElementById('liste-a-valider');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement...</p>';
    Object.keys(_carteData).forEach(k => delete _carteData[k]);
    try {
        const r = await fetch('/api/caces-obtenus/a-valider');
        if (!r.ok) throw new Error('Erreur ' + r.status);
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Aucun CACES® en attente de validation.</p>';
            return;
        }
        el.innerHTML = data.map(renderCarteAValider).join('');
    } catch (err) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}

async function chargerValides() {
    const listEl = document.getElementById('liste-valides');
    const headerEl = document.getElementById('header-valides');
    listEl.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement...</p>';
    if (headerEl) headerEl.innerHTML = '';
    Object.keys(_validesData).forEach(k => delete _validesData[k]);
    _validesArray = [];
    try {
        const r = await fetch('/api/caces-obtenus/valides');
        if (!r.ok) throw new Error('Erreur ' + r.status);
        const data = await r.json();
        data.forEach(co => { _validesData[co.id] = co; });
        _validesArray = data;
        _renderValides();
    } catch (err) {
        listEl.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}
