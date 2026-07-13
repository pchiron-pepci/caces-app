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

        // Plier / déplier une carte
        const btnToggleV = e.target.closest('[data-action="toggle-caces-valide"]');
        if (btnToggleV && !e.target.closest('a')) {
            const id = btnToggleV.dataset.id;
            const body = document.getElementById('caces-valide-body-' + id);
            const chevron = btnToggleV.querySelector('.co-valide-chevron');
            if (!body) return;
            const isOpen = body.style.display !== 'none';
            body.style.display = isOpen ? 'none' : 'flex';
            if (chevron) chevron.textContent = isOpen ? '▶' : '▼';
            return;
        }
        const btnToggle = e.target.closest('[data-action="toggle-caces-card"]');
        if (btnToggle && !e.target.closest('a')) {
            const id = btnToggle.dataset.id;
            const body = document.getElementById('caces-card-body-' + id);
            const chevron = btnToggle.querySelector('.co-card-chevron');
            if (!body) return;
            const isOpen = body.style.display !== 'none';
            body.style.display = isOpen ? 'none' : 'flex';
            if (chevron) chevron.textContent = isOpen ? '▶' : '▼';
            return;
        }

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

        const btnJustif = e.target.closest('[data-action="ouvrir-justif-dispense"]');
        if (btnJustif) {
            const sid = btnJustif.dataset.sessionId;
            const scId = btnJustif.dataset.scId;
            if (sid && scId) window.open('/api/sessions/' + sid + '/candidats/' + scId + '/dispense-fichier', '_blank');
        }
    });

    document.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'recherche-valides') {
            appliquerFiltresValides();
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
let _critereValides = 'obtention';
let _anneeValides = String(new Date().getFullYear());

function _peuplerMenuAnnees() {
    const sel = document.getElementById('filtre-annee');
    if (!sel) return;
    const attr = _critereValides === 'obtention' ? 'date_obtention' : 'date_echeance';
    const annees = [...new Set(_validesArray.map(co => (co[attr] || '').slice(0, 4)).filter(Boolean))].sort().reverse();
    const courante = String(new Date().getFullYear());
    if (annees.indexOf(_anneeValides) === -1 && _anneeValides !== 'toutes') {
        _anneeValides = (annees.indexOf(courante) !== -1) ? courante : 'toutes';
    }
    sel.innerHTML = '<option value="toutes">Toutes les années</option>'
        + annees.map(a => '<option value="' + a + '"' + (a === _anneeValides ? ' selected' : '') + '>' + a + '</option>').join('');
    sel.value = _anneeValides;
}

function appliquerFiltresValides() {
    const input = document.getElementById('recherche-valides');
    const q = input ? input.value.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim() : '';
    const dataAttr = _critereValides === 'obtention' ? 'anneeObt' : 'anneeEch';
    let visibles = 0;
    document.querySelectorAll('#liste-valides [data-search]').forEach(function (row) {
        const matchSearch = !q || (row.dataset.search || '').includes(q);
        const matchAnnee = (_anneeValides === 'toutes') || (row.dataset[dataAttr] === _anneeValides);
        const ok = matchSearch && matchAnnee;
        row.classList.toggle('co-hidden', !ok);
        if (ok) visibles++;
    });
    let vide = document.getElementById('valides-filtre-vide');
    const total = document.querySelectorAll('#liste-valides [data-search]').length;
    if (visibles === 0 && total > 0) {
        if (!vide) {
            vide = document.createElement('p');
            vide.id = 'valides-filtre-vide';
            vide.style.cssText = 'color:#718096;text-align:center;padding:24px;';
            document.getElementById('liste-valides').appendChild(vide);
        }
        const crit = _critereValides === 'obtention' ? 'délivré' : 'arrivant à échéance';
        vide.textContent = (_anneeValides === 'toutes')
            ? 'Aucun CACES® ne correspond à la recherche.'
            : 'Aucun CACES® ' + crit + ' en ' + _anneeValides + '.';
        vide.style.display = '';
    } else if (vide) {
        vide.style.display = 'none';
    }
}

document.addEventListener('click', function (e) {
    const btn = e.target.closest('.crit-btn');
    if (!btn) return;
    _critereValides = btn.dataset.critere;
    document.querySelectorAll('.crit-btn').forEach(function (b) {
        const on = b.dataset.critere === _critereValides;
        b.style.background = on ? '#1a237e' : '#fff';
        b.style.color = on ? '#fff' : '#555';
    });
    _peuplerMenuAnnees();
    appliquerFiltresValides();
});

document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'filtre-annee') {
        _anneeValides = e.target.value;
        appliquerFiltresValides();
    }
});

let _validesArray = [];
let _sortKey = 'numero_ordre';
let _sortDir = -1; // -1 = desc

// col definitions : key=sortKey (null=non triable), label, w=width fixe ou flex:true
const _SORT_COLS = [
    { key: 'numero_ordre',   label: 'N°',          w: '68px'  },
    { key: 'statut',         label: 'Statut',       w: '82px'  },
    { key: 'stagiaire',      label: 'Stagiaire',    flex: true  },
    { key: 'famille',        label: 'Fam. · Cat.',  w: '116px' },
    { key: null,             label: 'Options',      w: '84px'  },
    { key: null,             label: 'Testeur',      w: '132px' },
    { key: 'date_obtention', label: 'Obtention',    w: '88px'  },
    { key: 'date_echeance',  label: 'Échéance',     w: '88px'  },
    { key: null,             label: '',             w: '120px' },
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
function _abrevTesteur(nom) {
    if (!nom) return '';
    const p = nom.trim().split(/\s+/);
    if (p.length < 2) return p[0].slice(0, 4).toUpperCase();
    return p[1][0].toUpperCase() + '. ' + p[0].slice(0, 3).toUpperCase();
}

function _nomDdn(co) {
    let label = co.stagiaire_nom + ' ' + co.stagiaire_prenom;
    if (co.stagiaire_ddn) {
        const p = co.stagiaire_ddn.split('-');
        label += ' (' + p[2] + '/' + p[1] + '/' + p[0] + ')';
    }
    return label;
}

function fmtDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y;
}

function ligneDispense(co) {
    if (!co.dispense) return '';
    const d = co.dispense;
    const estExt = d.origine === 'externe';
    const libelle = estExt ? 'externe' : 'interne';
    const couleur = estExt ? '#e65100' : '#2e7d32';
    let detail = libelle + (d.date_base ? ' · base du ' + fmtDate(d.date_base) : '');
    if (estExt && d.echeance) detail += ' · éch. ' + fmtDate(d.echeance);
    let justif = '';
    if (estExt) {
        justif = d.justif
            ? `<span data-action="ouvrir-justif-dispense" data-session-id="${co.session_id_pratique}" data-sc-id="${d.sc_id}" style="color:#2e7d32;cursor:pointer;" title="Ouvrir le justificatif">📎</span>`
            : '<span style="color:#e65100;" title="Justificatif manquant">⚠️</span>';
    }
    return `
            <div style="display:flex;align-items:center;gap:8px;font-size:12px;margin-top:2px;">
                <span style="width:64px;flex-shrink:0;color:#666;font-weight:600;white-space:nowrap;">🪪 Dispense</span>
                <div style="display:flex;align-items:center;gap:6px;min-width:0;flex-wrap:wrap;">
                    <span style="color:${couleur};font-weight:700;white-space:nowrap;">${detail}</span>
                    ${justif}
                </div>
            </div>`;
}

function badgeDispense(co) {
    if (!co.dispense) return '';
    const estExt = co.dispense.origine === 'externe';
    const txt = estExt ? 'Disp. ext.' : 'Disp. int.';
    const bg = estExt ? '#fff3e0' : '#e8f5e9';
    const fg = estExt ? '#e65100' : '#2e7d32';
    const warn = (estExt && !co.dispense.justif) ? ' ⚠️' : '';
    const cliquable = (estExt && co.dispense.justif);
    const dataAttrs = cliquable
        ? ` data-action="ouvrir-justif-dispense" data-session-id="${co.session_id_pratique}" data-sc-id="${co.dispense.sc_id}"`
        : '';
    const curseur = cliquable ? 'cursor:pointer;' : '';
    const titre = cliquable
        ? 'Ouvrir le justificatif'
        : `Dispense ${estExt ? 'externe' : 'interne'}${warn ? ' — justificatif manquant' : ''}`;
    return `<span${dataAttrs} title="${titre}" style="background:${bg};color:${fg};border-radius:3px;padding:0 5px;font-size:10px;font-weight:700;white-space:nowrap;margin-left:6px;${curseur}">${txt}${warn}</span>`;
}

function badgeStatut(statut) {
    if (statut === 'valide') return '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">Validé</span>';
    if (statut === 'annule') return '<span class="badge" style="background:#fde8e8;color:#c62828;">Annulé</span>';
    return '';
}

// ===== TRI & RENDU VALIDÉS =====

function _colBaseStyle(col) {
    return col.flex
        ? 'flex:1;min-width:130px;max-width:300px;overflow:hidden;'
        : 'width:' + col.w + ';min-width:' + col.w + ';';
}

function _renderHeaderValides(wNo) {
    const cells = _SORT_COLS.map(function (col) {
        const base = col.key === 'numero_ordre'
            ? 'width:' + wNo + ';min-width:' + wNo + ';'
            : _colBaseStyle(col);
        if (!col.key || !col.label) {
            return '<div style="' + base + 'font-size:11px;color:#aaa;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">' + col.label + '</div>';
        }
        const active = _sortKey === col.key;
        const arrow = active ? (_sortDir === 1 ? '▲' : '▼') : '↕';
        return '<div data-action="sort-valides" data-key="' + col.key + '" '
            + 'style="' + base + 'font-size:11px;color:' + (active ? '#1a237e' : '#888') + ';font-weight:' + (active ? '800' : '600') + ';'
            + 'text-transform:uppercase;letter-spacing:0.5px;cursor:pointer;user-select:none;'
            + 'display:flex;align-items:center;gap:3px;">'
            + col.label
            + '<span style="font-size:9px;color:' + (active ? '#1a237e' : '#ccc') + ';">' + arrow + '</span>'
            + '</div>';
    }).join('');
    return '<div style="display:flex;align-items:center;background:#f0f2f7;border-bottom:1px solid #dde3f0;padding:9px 16px;gap:0;">' + cells + '</div>';
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

    headerEl.innerHTML = '';

    if (!_validesArray.length) {
        listEl.innerHTML = '<p style="color:#718096; text-align:center; padding:24px;">Aucun CACES® validé.</p>';
        return;
    }

    const sorted = _sortValides(_validesArray);
    const _noMax = Math.max(2, ...sorted.map(co => _formatNo(co).length));
    const _wNo = Math.max(56, _noMax * 9 + 20) + 'px';
    listEl.innerHTML =
        '<div class="co-scroll-wrap">'
        + '<div style="border:1px solid #c8d8f0;border-radius:12px;overflow:hidden;min-width:910px;">'
        + _renderHeaderValides(_wNo)
        + sorted.map(function (co, i) { return _renderLigne(co, i, _wNo); }).join('')
        + '</div>'
        + '</div>'
        + '<div class="co-cards-wrap">'
        + _validesArray.map(function (co) { return _renderCarteValide(co); }).join('')
        + '</div>';
    _peuplerMenuAnnees();
    appliquerFiltresValides();
}

// ===== RENDU CARTE À VALIDER =====
function renderCarteAValider(co) {
    _carteData[co.id] = co;
    const nomComplet = _nomDdn(co);

    let ddnHtml = '';
    if (co.stagiaire_ddn) {
        const p = co.stagiaire_ddn.split('-');
        ddnHtml = `<span class="co-card-ddn">(${p[2]}/${p[1]}/${p[0]})</span>`;
    }

    const options = co.options_obtenues
        ? co.options_obtenues.split(',').map(o => `<span style="background:#e8eaf6;color:#283593;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;">${o.trim()}</span>`).join(' ')
        : '';
    const optionsPratique = co.options_pratique
        ? co.options_pratique.split(',').map(o => `<span style="background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:1px 5px;font-size:11px;">${o.trim()}</span>`).join(' ')
        : '';

    const footerHtml = co.statut === 'annule'
        ? `<span style="background:#fff3e0;color:#e65100;border:2px solid #e65100;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;">↩ En révision</span>`
        : `<button data-action="revision-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="min-width:130px;background:#fff;border:2px solid #e65100;color:#e65100;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;">
                ↩ À réviser
            </button>
            <button data-action="valider-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="min-width:130px;background:#607d8b;color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;">
                📜 Émettre
            </button>`;

    return `
    <div id="caces-card-${co.id}" class="co-valider-card" style="border:1px solid #c8d8f0;border-radius:12px;overflow:hidden;margin-bottom:12px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,0.06);">

        <!-- Header (clic pour plier/déplier) -->
        <div data-action="toggle-caces-card" data-id="${co.id}"
             style="background:#f0f2f7;border-bottom:1px solid #dde3f0;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;cursor:pointer;user-select:none;">
            <span class="co-card-chevron" style="margin-right:8px;font-size:12px;color:#aaa;flex-shrink:0;">▶</span>
            <a href="/stagiaires#${co.stagiaire_id}" target="_blank"
               style="font-size:15px;font-weight:700;color:#1a237e;text-decoration:none;">${co.stagiaire_nom} ${co.stagiaire_prenom}</a>
            ${ddnHtml}
            <span style="font-weight:700;color:#555;font-size:13px;background:#e8eaf6;padding:2px 8px;border-radius:4px;">${co.famille}</span>
            <span style="background:#1a237e;color:#fff;border-radius:6px;padding:2px 10px;font-size:13px;font-weight:800;">${co.categorie}</span>
            ${options}
        </div>

        <!-- Body vertical -->
        <div id="caces-card-body-${co.id}" style="padding:14px 16px;display:none;flex-direction:column;gap:10px;">

            <!-- Dates en ligne -->
            <div style="display:flex;gap:24px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">📅 Obtention</div>
                    <div style="font-size:15px;font-weight:800;color:#1a237e;">${fmtDate(co.date_obtention)}</div>
                </div>
                <div>
                    <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">⏳ Échéance</div>
                    <div style="font-size:14px;font-weight:700;color:#2e7d32;">${fmtDate(co.date_echeance)}</div>
                </div>
            </div>

            <!-- Théorie -->
            <div style="display:flex;flex-direction:column;gap:3px;font-size:12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="width:64px;flex-shrink:0;color:#666;font-weight:600;white-space:nowrap;">🎓 Théorie</span>
                    <div style="display:flex;align-items:center;gap:8px;min-width:0;flex-wrap:wrap;">
                        <a href="/sessions/${co.session_id_theorie}" target="_blank"
                           style="color:#1a237e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;">${co.session_ref_theorie || '—'}</a>
                        <span style="color:#555;white-space:nowrap;">${fmtDate(co.date_theorie)}</span>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;padding-left:72px;">
                    ${co.testeur_nom_theorie ? `<span style="font-size:11px;color:#aaa;white-space:nowrap;">${_abrevTesteur(co.testeur_nom_theorie)}</span>` : ''}
                </div>
            </div>
            ${ligneDispense(co)}

            <!-- Pratique -->
            <div style="display:flex;flex-direction:column;gap:3px;font-size:12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="width:64px;flex-shrink:0;color:#666;font-weight:600;white-space:nowrap;">🔧 Pratique</span>
                    <div style="display:flex;align-items:center;gap:8px;min-width:0;flex-wrap:wrap;">
                        <a href="/sessions/${co.session_id_pratique}" target="_blank"
                           style="color:#1a237e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;">${co.session_ref_pratique || '—'}</a>
                        <span style="color:#555;white-space:nowrap;">${fmtDate(co.date_pratique)}</span>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;padding-left:72px;flex-wrap:wrap;">
                    <span class="cat-pratique-badge" style="background:#1a237e;color:#fff;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:700;">${co.categorie}</span>
                    ${optionsPratique ? `<span style="display:flex;gap:3px;">${optionsPratique}</span>` : ''}
                    ${co.testeur_nom ? `<span style="font-size:11px;color:#aaa;white-space:nowrap;">${_abrevTesteur(co.testeur_nom)}</span>` : ''}
                </div>
            </div>

            <!-- Pied : boutons action -->
            <div id="caces-card-footer-${co.id}" style="display:flex;gap:8px;border-top:1px solid #e8eef8;padding-top:12px;margin-top:2px;flex-wrap:wrap;">
                ${footerHtml}
            </div>

        </div>

    </div>`;
}

// ===== RENDU CARTE VALIDÉS =====

function _formatNo(co) {
    return co.ancien_numero ? co.ancien_numero : (co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—');
}

function _renderCarteValide(co) {
    const annule = co.statut === 'annule';
    const nomComplet = _nomDdn(co);
    const noFormate = _formatNo(co);

    const noBadge = annule
        ? `<span style="font-family:monospace;font-size:12px;font-weight:700;text-decoration:line-through;color:#bbb;">${noFormate}</span>`
        : `<span style="background:#1a237e;color:#fff;border-radius:5px;padding:2px 9px;font-size:12px;font-weight:700;font-family:monospace;">${noFormate}</span>`;

    const statutBadge = annule
        ? `<span style="background:#fff3e0;color:#e65100;border-radius:5px;padding:2px 9px;font-size:11px;font-weight:700;">Annulé</span>`
        : `<span style="background:#e8f5e9;color:#2e7d32;border-radius:5px;padding:2px 9px;font-size:11px;font-weight:700;">Validé</span>`;

    const catBg = annule ? '#888' : '#1a237e';

    const options = co.options_obtenues
        ? co.options_obtenues.split(',').map(o => `<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:1px 5px;font-size:10px;font-weight:700;">${o.trim()}</span>`).join(' ')
        : '';

    const actionHtml = annule
        ? `<button data-action="voir-motif" data-id="${co.id}" data-nom="${nomComplet}"
                title="${co.motif_annulation ? co.motif_annulation.replace(/"/g, '&quot;') : 'Aucun motif'}"
                style="background:none;border:none;cursor:pointer;font-size:12px;color:#999;font-weight:600;">📝 Motif</button>`
        : `<button data-action="annuler-caces" data-id="${co.id}" data-nom="${nomComplet}" data-categorie="${co.categorie}" data-famille="${co.famille}"
                style="background:none;border:none;cursor:pointer;font-size:12px;color:#e65100;font-weight:600;">↩ Annuler</button>`;

    const _search = (
        (co.stagiaire_nom || '') + ' ' + (co.stagiaire_prenom || '') + ' ' +
        (co.famille || '') + ' ' + (co.categorie || '') + ' ' +
        _formatNo(co) + ' ' +
        (co.date_obtention || '') + ' ' + (co.date_echeance || '')
    ).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

    return `
    <div data-caces-id="${co.id}" data-search="${_search}" data-annee-obt="${(co.date_obtention || '').slice(0,4)}" data-annee-ech="${(co.date_echeance || '').slice(0,4)}" class="co-valide-card" style="border:1px solid #c8d8f0;border-radius:12px;overflow:hidden;margin-bottom:12px;background:${annule ? '#f7f7f7' : '#fff'};${annule ? 'opacity:0.7;' : ''}box-shadow:0 1px 4px rgba(0,0,0,0.06);">
        <div data-action="toggle-caces-valide" data-id="${co.id}"
             style="background:#f0f2f7;border-bottom:1px solid #dde3f0;padding:10px 14px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;cursor:pointer;user-select:none;">
            <span class="co-valide-chevron" style="font-size:12px;color:#aaa;flex-shrink:0;">▶</span>
            ${noBadge}
            ${statutBadge}
            <a href="/stagiaires#${co.stagiaire_id}" target="_blank" style="font-size:15px;font-weight:700;color:${annule ? '#888' : '#1a237e'};text-decoration:none;${annule ? 'text-decoration:line-through;' : ''}">${nomComplet}</a>${badgeDispense(co)}
        </div>
        <div id="caces-valide-body-${co.id}" style="padding:12px 14px;display:none;flex-direction:column;gap:10px;">
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <span style="font-size:12px;color:#555;font-weight:700;">${co.famille}</span>
                <span style="font-size:10px;color:#bbb;">·</span>
                <span style="font-size:12px;background:${catBg};color:#fff;border-radius:4px;padding:0 6px;font-weight:800;">${co.categorie}</span>
                ${options ? `<span style="display:flex;gap:3px;margin-left:4px;">${options}</span>` : ''}
            </div>
            <div style="display:flex;gap:24px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">Obtention</div>
                    <div style="font-size:14px;font-weight:800;color:#1a237e;">${fmtDate(co.date_obtention)}</div>
                </div>
                <div>
                    <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">Échéance</div>
                    <div style="font-size:14px;font-weight:700;color:#2e7d32;">${fmtDate(co.date_echeance)}</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#555;">
                <span style="color:#666;font-weight:600;">Testeur</span>
                <span>${co.testeur_nom || '—'}</span>
            </div>
            <div style="border-top:1px solid #eef0f6;padding-top:10px;text-align:right;">
                ${actionHtml}
            </div>
        </div>
    </div>`;
}

function _renderLigne(co, idx, wNo) {
    const annule = co.statut === 'annule';
    const nomComplet = _nomDdn(co);
    const noFormate = _formatNo(co);
    const bg = annule ? '#f7f7f7' : (idx % 2 === 0 ? '#fff' : '#f5f7ff');

    const noBadge = annule
        ? `<span style="font-family:monospace;font-size:12px;font-weight:700;text-decoration:line-through;color:#bbb;">${noFormate}</span>`
        : `<span style="background:#1a237e;color:#fff;border-radius:5px;padding:1px 8px;font-size:12px;font-weight:700;font-family:monospace;">${noFormate}</span>`;

    const options = co.options_obtenues
        ? co.options_obtenues.split(',').map(o =>
            `<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:1px 4px;font-size:10px;font-weight:700;">${o.trim()}</span>`
          ).join(' ')
        : `<span style="color:#ccc;font-size:11px;">—</span>`;

    const actionHtml = annule
        ? `<button data-action="voir-motif" data-id="${co.id}" data-nom="${nomComplet}"
                title="${co.motif_annulation ? co.motif_annulation.replace(/"/g, '&quot;') : 'Aucun motif'}"
                style="background:none;border:none;cursor:pointer;font-size:11px;color:#999;font-weight:600;padding:0;">📝 Motif</button>`
        : `<button data-action="annuler-caces" data-id="${co.id}" data-nom="${nomComplet}" data-categorie="${co.categorie}" data-famille="${co.famille}"
                style="background:none;border:none;cursor:pointer;font-size:11px;color:#e65100;font-weight:600;padding:0;white-space:nowrap;">↩ Annuler</button>`;

    const _search = (
        (co.stagiaire_nom || '') + ' ' + (co.stagiaire_prenom || '') + ' ' +
        (co.famille || '') + ' ' + (co.categorie || '') + ' ' +
        _formatNo(co) + ' ' +
        (co.date_obtention || '') + ' ' + (co.date_echeance || '')
    ).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

    return `<div data-caces-id="${co.id}" data-search="${_search}" data-annee-obt="${(co.date_obtention || '').slice(0,4)}" data-annee-ech="${(co.date_echeance || '').slice(0,4)}"
         style="display:flex;align-items:center;padding:9px 16px;background:${bg};${annule ? 'opacity:0.65;' : ''}border-bottom:1px solid #eef0f6;gap:0;">
        <div style="width:${wNo};min-width:${wNo};">${noBadge}</div>
        <div style="width:82px;min-width:82px;">${badgeStatut(co.statut)}</div>
        <div style="flex:1;min-width:130px;max-width:300px;overflow:hidden;padding-right:10px;display:flex;flex-direction:column;justify-content:center;${annule ? 'text-decoration:line-through;' : ''}">
            <div style="display:flex;align-items:center;font-size:13px;font-weight:700;color:#1a237e;overflow:hidden;"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${co.stagiaire_nom} ${co.stagiaire_prenom}</span>${badgeDispense(co)}</div>
            ${co.stagiaire_ddn ? `<span style="font-size:10px;color:#999;font-weight:400;line-height:1.1;margin-top:1px;">${co.stagiaire_ddn.split('-').reverse().join('/')}</span>` : ''}
        </div>
        <div style="width:116px;min-width:116px;display:flex;flex-direction:row;align-items:center;gap:5px;padding-right:6px;flex-wrap:nowrap;">
            <span style="font-size:11px;color:#555;font-weight:700;white-space:nowrap;">${co.famille}</span>
            <span style="font-size:10px;color:#bbb;">·</span>
            <span style="font-size:11px;background:#1a237e;color:#fff;border-radius:4px;padding:0 5px;font-weight:800;white-space:nowrap;">${co.categorie}</span>
        </div>
        <div style="width:84px;min-width:84px;display:flex;flex-wrap:wrap;gap:2px;align-items:center;">${options}</div>
        <div style="width:132px;min-width:132px;font-size:12px;color:#555;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:6px;">${co.testeur_nom || '<span style="color:#ccc;">—</span>'}</div>
        <div style="width:88px;min-width:88px;font-size:12px;font-weight:700;color:#1a237e;">${fmtDate(co.date_obtention)}</div>
        <div style="width:88px;min-width:88px;font-size:12px;font-weight:700;color:#2e7d32;">${fmtDate(co.date_echeance)}</div>
        <div style="width:120px;min-width:120px;text-align:right;">${actionHtml}</div>
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
    const footerEl = document.getElementById('caces-card-footer-' + id);
    if (footerEl) {
        footerEl.innerHTML = '<span style="background:#fff3e0;color:#e65100;border:2px solid #e65100;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;">↩ En révision — actualisez pour recalculer</span>';
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
