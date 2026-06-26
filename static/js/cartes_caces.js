var _emiseData = [];
var _emiseSort = { col: 4, asc: false }; // par défaut : date desc
var _emiseFilter = '';
var _emiseShowAll = false;

document.addEventListener('DOMContentLoaded', function () {

    chargerStagiaires();
    chargerEmises();

    let _resolvedStagId = null; // ID résolu après sélection (+DDN si homonymes)

    function _resetFamille() {
        const sel = document.getElementById('sel-famille');
        sel.innerHTML = '<option value="">— —</option>';
        sel.disabled = true;
        sel.style.color = '#aaa';
        sel.style.borderColor = '#ddd';
        sel.style.background = '#f7f7f7';
    }

    function _chargerFamilles(stagId) {
        const selFamille = document.getElementById('sel-famille');
        fetch('/api/cartes-caces/familles/' + stagId)
            .then(r => r.json())
            .then(function (familles) {
                if (!familles.length) {
                    selFamille.innerHTML = '<option value="">Aucun CACES® validé</option>';
                    return;
                }
                selFamille.innerHTML = '<option value="">— Famille —</option>';
                familles.forEach(function (f) {
                    const opt = document.createElement('option');
                    opt.value = f; opt.textContent = f;
                    selFamille.appendChild(opt);
                });
                selFamille.disabled = false;
                selFamille.style.color = '#1a237e';
                selFamille.style.borderColor = '#c8d8f0';
                selFamille.style.background = '#fff';
            });
    }

    // --- Recherche stagiaire (autocomplete) ---
    function _selectionnerStagiaire(nomPrenom) {
        const inp = document.getElementById('sel-stagiaire-input');
        const list = document.getElementById('sel-stagiaire-list');
        inp.value = nomPrenom;
        list.style.display = 'none';
        _resolvedStagId = null;
        _resetFamille();
        document.getElementById('section-caces').style.display = 'none';
        document.getElementById('resultats-placeholder').style.display = 'flex';
        document.getElementById('ddn-section').style.display = 'none';
        if (!nomPrenom) return;
        const groupe = _stagiairesParNom[nomPrenom] || [];
        if (groupe.length === 1) {
            _resolvedStagId = groupe[0].id;
            _chargerFamilles(_resolvedStagId);
        } else {
            const selDdn = document.getElementById('sel-ddn');
            selDdn.innerHTML = '<option value="">— Choisir la date de naissance —</option>';
            groupe.forEach(function (p) {
                const opt = document.createElement('option');
                opt.value = p.id;
                if (p.ddn) {
                    const parts = p.ddn.split('-');
                    opt.textContent = parts[2] + '/' + parts[1] + '/' + parts[0];
                } else {
                    opt.textContent = 'Date inconnue';
                }
                selDdn.appendChild(opt);
            });
            document.getElementById('ddn-section').style.display = 'block';
        }
    }

    document.getElementById('sel-stagiaire-input').addEventListener('input', function () {
        const q = this.value.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
        const list = document.getElementById('sel-stagiaire-list');
        if (!q) { list.style.display = 'none'; list.innerHTML = ''; return; }
        const matches = Object.keys(_stagiairesParNom).filter(function (nom) {
            return nom.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(q);
        }).slice(0, 20);
        if (!matches.length) { list.style.display = 'none'; list.innerHTML = ''; return; }
        list.innerHTML = matches.map(function (nom) {
            return '<div data-nom="' + nom.replace(/"/g, '&quot;') + '" style="padding:8px 12px;font-size:13px;font-weight:600;color:#2d2d2d;cursor:pointer;border-bottom:1px solid #eef0f6;">' + nom + '</div>';
        }).join('');
        list.style.display = 'block';
    });

    document.getElementById('sel-stagiaire-list').addEventListener('click', function (e) {
        const item = e.target.closest('[data-nom]');
        if (item) _selectionnerStagiaire(item.dataset.nom);
    });

    document.addEventListener('click', function (e) {
        if (!e.target.closest('#sel-stagiaire-input') && !e.target.closest('#sel-stagiaire-list')) {
            document.getElementById('sel-stagiaire-list').style.display = 'none';
        }
    });

    // --- PIN modal ---
    document.getElementById('btn-pin-carte-annuler').addEventListener('click', _fermerPin);
    document.getElementById('pin-carte-input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') document.getElementById('btn-pin-carte-confirmer').click();
    });
    document.getElementById('modal-pin-carte').addEventListener('click', function (e) {
        if (e.target === this) _fermerPin();
    });

    // --- Motif modal ---
    document.getElementById('btn-motif-carte-annuler').addEventListener('click', _fermerMotif);
    document.getElementById('modal-motif-carte').addEventListener('click', function (e) {
        if (e.target === this) _fermerMotif();
    });

    // --- Recherche + toggle statut cartes émises ---
    document.addEventListener('input', function (e) {
        if (e.target && e.target.id === 'recherche-emises') {
            _emiseFilter = e.target.value;
            _renderTableEmises();
        }
    });
    document.addEventListener('change', function (e) {
        if (e.target && e.target.id === 'chk-emises-all') {
            _emiseShowAll = e.target.checked;
            var lbl = document.getElementById('lbl-emises-all');
            if (lbl) {
                lbl.style.background = _emiseShowAll ? '#e3f2fd' : '#f0f2f7';
                lbl.style.borderColor = _emiseShowAll ? '#1565c0' : '#c8d8f0';
            }
            _renderTableEmises();
        }
    });

    // --- Délégation clics ---
    document.addEventListener('click', function (e) {

        // Tri tableau cartes émises
        const thSort = e.target.closest('#liste-emises th[data-sort-col]');
        if (thSort) {
            const col = parseInt(thSort.dataset.sortCol, 10);
            if (_emiseSort.col === col) { _emiseSort.asc = !_emiseSort.asc; }
            else { _emiseSort.col = col; _emiseSort.asc = true; }
            _renderTableEmises();
            return;
        }

        // Confirmer DDN (sélection parmi les homonymes)
        const btnDdn = e.target.closest('[data-action="confirmer-ddn"]');
        if (btnDdn) {
            const val = document.getElementById('sel-ddn').value;
            if (!val) return;
            _resolvedStagId = parseInt(val, 10);
            document.getElementById('ddn-section').style.display = 'none';
            _chargerFamilles(_resolvedStagId);
            return;
        }

        // Voir les CACES®
        const btnVoir = e.target.closest('[data-action="voir-caces"]');
        if (btnVoir) {
            const famille = document.getElementById('sel-famille').value;
            if (!_resolvedStagId || !famille) {
                alert('Choisissez un stagiaire et une famille.');
                return;
            }
            _chargerCacesValides(_resolvedStagId, famille);
            return;
        }

        // Émettre (génère + imprime)
        const btnEmettre = e.target.closest('[data-action="emettre-carte"]');
        if (btnEmettre) {
            const stagId = btnEmettre.dataset.stagId;
            const famille = btnEmettre.dataset.famille;
            const nom = btnEmettre.dataset.nom || '';
            _ouvrirPin('Générer la carte ' + famille + ' pour ' + nom + ' ?', async function (pin) {
                const r = await fetch('/api/cartes-caces/emettre/' + stagId + '/' + encodeURIComponent(famille) + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
                if (r.ok) {
                    const data = await r.json();
                    chargerEmises();
                    _ouvrirImpressionCarte(data);
                }
                return r;
            });
            return;
        }

        // Télécharger PDF protégé
        const btnPdf = e.target.closest('[data-action="telecharger-pdf"]');
        if (btnPdf) {
            window.open('/api/cartes-caces/' + btnPdf.dataset.id + '/pdf', '_blank');
            return;
        }

        // Réimprimer
        const btnReimprimer = e.target.closest('[data-action="reimprimer-carte"]');
        if (btnReimprimer) {
            const id = btnReimprimer.dataset.id;
            fetch('/api/cartes-caces/reimprimer/' + id)
                .then(r => r.ok ? r.json() : Promise.reject(r))
                .then(function (data) { _ouvrirImpressionCarte(data); })
                .catch(function () { alert('Erreur lors de la récupération des données.'); });
            return;
        }

        // Toggle détail CACES® d'une carte émise
        const btnToggle = e.target.closest('[data-action="toggle-caces-carte"]');
        if (btnToggle) {
            const carteId = btnToggle.dataset.carteId;
            const detailRow = document.getElementById('detail-carte-' + carteId);
            const detailDiv = document.getElementById('detail-caces-' + carteId);
            const isOpen = detailRow.style.display !== 'none';
            if (isOpen) {
                detailRow.style.display = 'none';
                btnToggle.textContent = '▶';
            } else {
                detailRow.style.display = '';
                btnToggle.textContent = '▼';
                if (btnToggle.dataset.loaded === '0') {
                    btnToggle.dataset.loaded = '1';
                    _chargerCacesCarte(carteId, detailDiv);
                }
            }
            return;
        }

        // Annuler carte
        const btnAnnuler = e.target.closest('[data-action="annuler-carte"]');
        if (btnAnnuler) {
            const id = btnAnnuler.dataset.id;
            const num = btnAnnuler.dataset.num;
            _ouvrirMotif(function (motif) {
                _fermerMotif();
                _ouvrirPin('Annuler la carte ' + num + ' ?', async function (pin) {
                    const r = await fetch('/api/cartes-caces/annuler/' + id + '?pin=' + encodeURIComponent(pin), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motif: motif }),
                    });
                    if (r.ok) chargerEmises();
                    return r;
                });
            });
            return;
        }
    });
});

// ===== ÉTAT =====
let _pinCallback = null;
let _motifCallback = null;

// ===== PIN MODAL =====
function _ouvrirPin(titre, callback) {
    _pinCallback = callback;
    document.getElementById('pin-carte-titre').textContent = titre;
    document.getElementById('pin-carte-input').value = '';
    document.getElementById('pin-carte-erreur').textContent = '';
    document.getElementById('modal-pin-carte').style.display = 'flex';
    setTimeout(function () { document.getElementById('pin-carte-input').focus(); }, 50);

    document.getElementById('btn-pin-carte-confirmer').onclick = async function () {
        const pin = document.getElementById('pin-carte-input').value.trim();
        if (!pin) return;
        const btn = this;
        btn.disabled = true; btn.textContent = '…';
        try {
            const r = await _pinCallback(pin);
            if (r.ok) {
                _fermerPin();
            } else {
                const d = await r.json().catch(() => ({}));
                document.getElementById('pin-carte-erreur').textContent = d.detail || 'Erreur';
            }
        } finally {
            btn.disabled = false; btn.textContent = 'Confirmer';
        }
    };
}

function _fermerPin() {
    document.getElementById('modal-pin-carte').style.display = 'none';
    _pinCallback = null;
}

// ===== MOTIF MODAL =====
function _ouvrirMotif(onConfirme) {
    _motifCallback = onConfirme;
    document.getElementById('motif-carte-input').value = '';
    document.getElementById('motif-carte-erreur').textContent = '​';
    document.getElementById('modal-motif-carte').style.display = 'flex';
    setTimeout(function () { document.getElementById('motif-carte-input').focus(); }, 50);

    document.getElementById('btn-motif-carte-confirmer').onclick = function () {
        const motif = document.getElementById('motif-carte-input').value.trim();
        if (!motif) {
            document.getElementById('motif-carte-erreur').textContent = '⚠️ Le motif est obligatoire.';
            return;
        }
        if (_motifCallback) _motifCallback(motif);
    };
}

function _fermerMotif() {
    document.getElementById('modal-motif-carte').style.display = 'none';
    _motifCallback = null;
}

// ===== UTILITAIRES =====
function _fmtDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y;
}

function _fmtDateCourt(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y.slice(2);
}

function _noFormate(n) {
    return n ? String(n).padStart(4, '0') : '—';
}

// ===== CHARGEMENT STAGIAIRES =====
// Groupes par nom+prénom pour la résolution des homonymes
const _stagiairesParNom = {};

async function chargerStagiaires() {
    try {
        const r = await fetch('/api/cartes-caces/stagiaires');
        if (!r.ok) return;
        const data = await r.json();
        data.forEach(function (s) {
            const key = s.nom + ' ' + s.prenom;
            if (!_stagiairesParNom[key]) _stagiairesParNom[key] = [];
            _stagiairesParNom[key].push({ id: s.id, ddn: s.date_naissance || null });
        });
    } catch (_) {}
}

// ===== AFFICHAGE CACES VALIDES =====
async function _chargerCacesValides(stagId, famille) {
    const section = document.getElementById('section-caces');
    const infoEl = document.getElementById('info-stagiaire');
    const tableEl = document.getElementById('tableau-caces');
    const btnEmettre = document.getElementById('btn-emettre');

    infoEl.innerHTML = '<p style="color:#718096; padding:8px;">Chargement…</p>';
    tableEl.innerHTML = '';
    document.getElementById('resultats-placeholder').style.display = 'none';
    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
        const r = await fetch('/api/cartes-caces/caces-valides/' + stagId + '/' + encodeURIComponent(famille));
        if (!r.ok) throw new Error();
        const data = await r.json();

        // Info stagiaire
        const photoBadge = data.photo_manquante
            ? '<span style="background:#ffebee; color:#c62828; border-radius:6px; padding:3px 10px; font-size:12px; font-weight:700;">📷 Photo manquante — impression bloquée</span>'
            : '<span style="background:#e8f5e9; color:#2e7d32; border-radius:6px; padding:3px 10px; font-size:12px; font-weight:700;">📷 Photo disponible</span>';
        infoEl.innerHTML = '<div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">'
            + '<span style="font-size:16px; font-weight:700; color:#1a237e;">' + data.stagiaire_nom + ' ' + data.stagiaire_prenom + '</span>'
            + '<span style="background:#1a237e; color:#fff; border-radius:6px; padding:2px 10px; font-size:14px; font-weight:800;">' + famille + '</span>'
            + photoBadge
            + '</div>';

        // Tableau CACES®
        if (!data.caces.length) {
            tableEl.innerHTML = '<p style="color:#718096; padding:12px;">Aucun CACES® validé pour cette famille.</p>';
            btnEmettre.style.display = 'none';
        } else {
            const rows = data.caces.map(function (co) {
                const opts = co.options_obtenues
                    ? co.options_obtenues.split(',').map(o => '<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:1px 5px;font-size:11px;font-weight:700;">' + o.trim() + '</span>').join(' ')
                    : '—';
                return '<tr>'
                    + '<td style="font-size:13px; color:#333; padding:8px 10px;">' + (co.categorie_libelle || '—') + '</td>'
                    + '<td style="font-weight:700; color:#1a237e; padding:8px 10px; white-space:nowrap;">' + co.categorie + '</td>'
                    + '<td style="padding:8px 10px;">' + opts + '</td>'
                    + '<td style="font-family:monospace; font-size:13px; padding:8px 10px;"><span style="background:#e8eaf6; padding:2px 8px; border-radius:4px;">' + (co.ancien_numero ? co.ancien_numero : _noFormate(co.numero_ordre)) + '</span></td>'
                    + '<td style="font-size:13px; color:#444; padding:8px 10px; white-space:nowrap;">' + _fmtDate(co.date_obtention) + '</td>'
                    + '<td style="font-size:13px; color:#2e7d32; font-weight:700; padding:8px 10px; white-space:nowrap;">' + _fmtDate(co.date_echeance) + '</td>'
                    + '<td style="font-size:12px; color:#666; padding:8px 10px;">' + (co.testeur_nom || '—') + '</td>'
                    + '</tr>';
            }).join('');
            tableEl.innerHTML = '<table class="table">'
                + '<thead><tr>'
                + '<th>Libellé</th><th>Cat.</th><th>Options</th><th>N° CACES®</th><th>Obtention</th><th>Échéance</th><th>Testeur</th>'
                + '</tr></thead><tbody>' + rows + '</tbody></table>';

            // Bouton émettre
            btnEmettre.dataset.stagId = stagId;
            btnEmettre.dataset.famille = famille;
            btnEmettre.dataset.nom = data.stagiaire_nom + ' ' + data.stagiaire_prenom;
            if (data.photo_manquante) {
                btnEmettre.disabled = true;
                btnEmettre.style.background = '#bdbdbd';
                btnEmettre.style.color = '#fff';
                btnEmettre.style.cursor = 'not-allowed';
                btnEmettre.style.boxShadow = 'none';
                btnEmettre.title = 'Photo manquante — ajoutez une photo au stagiaire avant d\'imprimer';
            } else {
                btnEmettre.disabled = false;
                btnEmettre.style.background = '#2e7d32';
                btnEmettre.style.color = '#fff';
                btnEmettre.style.cursor = 'pointer';
                btnEmettre.style.boxShadow = '0 3px 8px rgba(46,125,50,0.3)';
                btnEmettre.title = '';
            }
            btnEmettre.style.display = '';
        }
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (_) {
        infoEl.innerHTML = '<p style="color:red; padding:8px;">Erreur de chargement</p>';
    }
}

// ===== CARTES ÉMISES =====
async function chargerEmises() {
    const el = document.getElementById('liste-emises');
    el.innerHTML = '<p style="color:#718096; text-align:center; padding:24px;">Chargement…</p>';
    try {
        const r = await fetch('/api/cartes-caces/emises');
        if (!r.ok) throw new Error();
        _emiseData = await r.json();
        if (!_emiseData.length) {
            el.innerHTML = '<p style="color:#718096; padding:16px;">Aucune carte émise.</p>';
            return;
        }
        _renderTableEmises();
    } catch (_) {
        el.innerHTML = '<p style="color:red; text-align:center; padding:24px;">Erreur de chargement</p>';
    }
}

function _emiseSortKey(carte, col) {
    switch (col) {
        case 1: return (carte.numero_carte || '').toLowerCase();
        case 2: return (carte.stagiaire_nom + ' ' + carte.stagiaire_prenom).toLowerCase();
        case 3: return (carte.famille || '').toLowerCase();
        case 4: return carte.date_generation || '';
        case 5: return carte.statut || '';
        default: return '';
    }
}

function _renderTableEmises() {
    const el = document.getElementById('liste-emises');
    if (!el) return;

    const _q = _emiseFilter.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
    const sorted = _emiseData.slice().sort(function (a, b) {
        const va = _emiseSortKey(a, _emiseSort.col);
        const vb = _emiseSortKey(b, _emiseSort.col);
        const cmp = va < vb ? -1 : va > vb ? 1 : 0;
        return _emiseSort.asc ? cmp : -cmp;
    }).filter(function (c) {
        if (!_emiseShowAll && c.statut !== 'emise') return false;
        if (!_q) return true;
        const s = ((c.stagiaire_nom || '') + ' ' + (c.stagiaire_prenom || '') + ' ' + (c.famille || '') + ' ' + (c.numero_carte || ''))
            .toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
        return s.includes(_q);
    });

    const defs = [
        { label: '',          sortable: false, style: 'width:32px;' },
        { label: 'N° Carte',  sortable: true,  col: 1 },
        { label: 'Stagiaire', sortable: true,  col: 2 },
        { label: 'Famille',   sortable: true,  col: 3 },
        { label: 'Date',      sortable: true,  col: 4 },
        { label: 'Statut',    sortable: true,  col: 5 },
        { label: '',          sortable: false },
    ];
    const ths = defs.map(function (d) {
        if (!d.sortable) return '<th' + (d.style ? ' style="' + d.style + '"' : '') + '></th>';
        const arrow = d.col === _emiseSort.col ? (_emiseSort.asc ? ' ↑' : ' ↓') : '';
        return '<th data-sort-col="' + d.col + '" style="cursor:pointer;user-select:none;">'
            + d.label + '<span class="emise-sort-arrow">' + arrow + '</span></th>';
    }).join('');

    el.innerHTML = '<table class="table"><thead><tr>' + ths + '</tr></thead>'
        + '<tbody>' + sorted.map(_renderEmise).join('') + '</tbody></table>';
}

function _renderEmise(carte) {
    const nomComplet = carte.stagiaire_nom + ' ' + carte.stagiaire_prenom;
    const emise = carte.statut === 'emise';
    const remplacee = carte.statut === 'remplacee';
    const annulee = carte.statut === 'annulee';

    const badgeHtml = emise
        ? '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">✅ Émise</span>'
        : remplacee
        ? '<span class="badge" style="background:#f5f5f5;color:#888;">📷 Remplacée</span>'
        : '<span class="badge" style="background:#ffebee;color:#c62828;">❌ Annulée</span>';

    const motifHtml = (annulee || remplacee) && carte.motif_annulation
        ? '<div style="font-size:11px;color:#888;margin-top:2px;font-style:italic;">' + carte.motif_annulation + '</div>'
        : '';

    const actionsHtml = '<div style="display:flex;gap:6px;">'
        + '<button data-action="reimprimer-carte" data-id="' + carte.id + '" title="Réimprimer" '
        + 'style="background:none;border:1px solid #1a237e;color:#1a237e;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">🖨️</button>'
        + '<button data-action="telecharger-pdf" data-id="' + carte.id + '" title="Télécharger PDF protégé" '
        + 'style="background:none;border:1px solid #2e7d32;color:#2e7d32;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">📥 PDF</button>'
        + (emise
            ? '<button data-action="annuler-carte" data-id="' + carte.id + '" data-num="' + carte.numero_carte + '" title="Annuler" '
              + 'style="background:none;border:1px solid #c62828;color:#c62828;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">❌</button>'
            : '')
        + '</div>';

    const opacity = emise ? '' : 'opacity:0.5;';
    const strike = emise ? '' : 'text-decoration:line-through;';

    const toggleBtn = '<button data-action="toggle-caces-carte" data-carte-id="' + carte.id + '" data-loaded="0" '
        + 'style="background:none;border:none;cursor:pointer;font-size:12px;color:#2d2d2d;padding:2px 6px;line-height:1;" '
        + 'title="Voir les CACES® de cette carte">▶</button>';

    const mainRow = '<tr style="' + opacity + '">'
        + '<td style="text-align:center;padding:8px 4px;">' + toggleBtn + '</td>'
        + '<td style="font-family:monospace;font-size:13px;font-weight:700;color:#1a237e;white-space:nowrap;' + strike + '">' + carte.numero_carte + '</td>'
        + '<td style="font-weight:600;font-size:13px;">' + nomComplet + (carte.stagiaire_ddn ? '<span style="font-weight:400;color:#888;font-size:12px;"> (' + _fmtDate(carte.stagiaire_ddn) + ')</span>' : '') + motifHtml + '</td>'
        + '<td><span style="background:#1a237e;color:#fff;border-radius:5px;padding:2px 8px;font-size:12px;font-weight:800;">' + carte.famille + '</span></td>'
        + '<td style="font-size:12px;color:#666;white-space:nowrap;">' + _fmtDate(carte.date_generation) + '</td>'
        + '<td>' + badgeHtml + '</td>'
        + '<td>' + actionsHtml + '</td>'
        + '</tr>';

    const detailRow = '<tr id="detail-carte-' + carte.id + '" style="display:none;">'
        + '<td style="padding:0;border-top:none;"></td>'
        + '<td colspan="6" style="padding:0;border-top:none;">'
        + '<div id="detail-caces-' + carte.id + '" style="padding:10px 12px 14px; background:#f7f8fc; border-top:1px solid #e8eef8;">'
        + '<span style="color:#888;font-size:12px;">Chargement…</span>'
        + '</div></td></tr>';

    return mainRow + detailRow;
}

// ===== DÉTAIL CACES® D'UNE CARTE =====
async function _chargerCacesCarte(carteId, el) {
    try {
        const r = await fetch('/api/cartes-caces/' + carteId + '/caces');
        if (!r.ok) throw new Error();
        const caces = await r.json();
        if (!caces.length) {
            el.innerHTML = '<span style="color:#888;font-size:12px;font-style:italic;">Aucun CACES® valide actuel pour cette famille.</span>';
            return;
        }
        const rows = caces.map(function (co) {
            const opts = co.options_obtenues
                ? co.options_obtenues.split(',').map(function (o) {
                    return '<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:1px 5px;font-size:10px;font-weight:700;">' + o.trim() + '</span>';
                  }).join(' ')
                : '—';
            return '<tr>'
                + '<td style="font-size:12px;color:#444;padding:5px 10px;">' + (co.categorie_libelle || '—') + '</td>'
                + '<td style="font-weight:700;color:#1a237e;font-size:12px;padding:5px 10px;">' + co.categorie + '</td>'
                + '<td style="padding:5px 10px;">' + opts + '</td>'
                + '<td style="font-family:monospace;font-size:12px;padding:5px 10px;"><span style="background:#e8eaf6;padding:1px 7px;border-radius:3px;">' + (co.ancien_numero ? co.ancien_numero : _noFormate(co.numero_ordre)) + '</span></td>'
                + '<td style="font-size:12px;color:#444;white-space:nowrap;padding:5px 10px;">' + _fmtDate(co.date_obtention) + '</td>'
                + '<td style="font-size:12px;color:#2e7d32;font-weight:700;white-space:nowrap;padding:5px 10px;">' + _fmtDate(co.date_echeance) + '</td>'
                + '<td style="font-size:11px;color:#666;padding:5px 10px;">' + (co.testeur_nom || '—') + '</td>'
                + '</tr>';
        }).join('');
        el.innerHTML = '<table style="width:100%;border-collapse:collapse;">'
            + '<thead><tr style="border-bottom:1px solid #dde3f0;">'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">Libellé</th>'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">Cat.</th>'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">Options</th>'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">N° CACES®</th>'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">Obtention</th>'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">Échéance</th>'
            + '<th style="font-size:10px;text-transform:uppercase;color:#888;padding:4px 10px;font-weight:700;text-align:left;">Testeur</th>'
            + '</tr></thead><tbody>' + rows + '</tbody></table>';
    } catch (_) {
        el.innerHTML = '<span style="color:#c62828;font-size:12px;">Erreur de chargement.</span>';
    }
}

// ===== IMPRESSION =====
function _ouvrirImpressionCarte(data) {
    const nbCats = data.caces.length;
    const format = nbCats <= 4 ? 'cr80' : 'a5';
    const w = window.open('', '_blank');
    if (!w) {
        alert('Autorisez les popups pour imprimer.');
        return;
    }
    w.document.write(_buildCarteHtml(data, format));
    w.document.close();
    w.focus();
    // Délai augmenté pour laisser le temps au CDN qrcode.js + images
    setTimeout(function () { w.print(); }, 1500);
}

function _buildCarteHtml(data, format) {
    const isCr80 = format === 'cr80';
    const cfg = data.config || {};

    if (isCr80) {
        return _buildCr80Html(data, cfg);
    } else {
        return _buildA5Html(data, cfg);
    }
}

function _buildCr80Html(data, cfg) {
    const numsCaces = data.caces
        .map(function (co) { return co.ancien_numero ? co.ancien_numero : (co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : ''); })
        .filter(Boolean).join(' – ');

    const sigNom = [cfg.signataire_prenom, cfg.signataire_nom].filter(Boolean).join(' ');
    const sigLigne = [sigNom, cfg.signataire_qualite].filter(Boolean).join(' — ');

    const allOpts = {};
    data.caces.forEach(function (co) {
        if (co.options_obtenues) {
            co.options_obtenues.split(',').forEach(function (o) { allOpts[o.trim()] = true; });
        }
    });
    const optLabels = { PE: 'Porte-engin', TE: 'Télécommande', TEL: 'Télécommande', CC: 'Conduite cabine', TR: 'Translation rails', CEC: 'Circulation en charge' };
    const optLegend = Object.keys(allOpts).map(function (k) { return k + ' : ' + (optLabels[k] || k); }).join(' — ');

    const organisme = cfg.nom_organisme || '';
    const adresse = cfg.adresse || '';
    const delivreePar = adresse ? organisme + ' — ' + adresse : organisme;
    const siretLine = [
        cfg.siret ? 'SIRET ' + cfg.siret : '',
        cfg.email || '',
        cfg.telephone ? 'Tél. ' + cfg.telephone : '',
    ].filter(Boolean).join(' · ');

    const verifyUrl = cfg.verify_url || '';
    const numeroCert = cfg.numero_certificat || '';

    // Verso rows — Options next to Cat.
    const versoRows = data.caces.map(function (co) {
        const no = co.ancien_numero ? co.ancien_numero : (co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—');
        const opts = co.options_obtenues
            ? co.options_obtenues.split(',').map(function (o) {
                return '<span class="vopt-badge">' + o.trim() + '</span>';
              }).join(' ')
            : '<span style="color:#bbb;">—</span>';
        const mainRow = '<tr' + (co.testeur_nom ? ' class="vhastest"' : '') + '>'
            + '<td class="vfam">' + data.famille + '</td>'
            + '<td class="vcat">' + co.categorie + '</td>'
            + '<td class="vopt">' + opts + '</td>'
            + '<td class="vno">' + no + '</td>'
            + '<td class="vdt">' + _fmtDateCourt(co.date_obtention) + '</td>'
            + '<td class="vval">' + _fmtDateCourt(co.date_echeance) + '</td>'
            + '<td class="vlib">' + (co.categorie_libelle || '') + '</td>'
            + '</tr>';
        const testeurRow = co.testeur_nom
            ? '<tr><td colspan="7" class="vtestcell">Testeur : ' + co.testeur_nom + '</td></tr>'
            : '';
        return mainRow + testeurRow;
    }).join('');

    const ddn = data.stagiaire_ddn
        ? ' <span class="v-hddn">(' + data.stagiaire_ddn + ')</span>'
        : '';

    const ANT = '#2b2b2b';
    const RED = '#c62828';

    const css = [
        '* { margin:0; padding:0; box-sizing:border-box; }',
        '@page { size:85.6mm 54mm; margin:0; }',
        'html,body { width:85.6mm; height:108mm; font-family:Arial,Helvetica,sans-serif; font-size:5.5pt; background:#fff;',
        '  -webkit-print-color-adjust:exact; print-color-adjust:exact; }',
        '.page { width:85.6mm; height:54mm; overflow:hidden; display:flex; flex-direction:column; position:relative; }',
        '.page + .page { page-break-before:always; }',
        '.wm { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; overflow:hidden; z-index:50; pointer-events:none; }',
        '.wm-inner { transform:rotate(-30deg); text-align:center; }',
        '.wm-txt { font-size:13pt; font-weight:900; color:rgba(204,0,0,0.35); letter-spacing:0.5mm; white-space:nowrap; font-style:italic; }',
        '.wm-sub { font-size:5pt; color:rgba(204,0,0,0.45); white-space:nowrap; margin-top:0.7mm; }',
        '.r-hdr { background:#fff; height:15mm; display:flex; align-items:center; padding:0 2.5mm;',
        '  justify-content:space-between; flex-shrink:0; gap:1.5mm; border-bottom:0.5mm solid ' + RED + '; }',
        '.r-hdr-left { display:flex; flex-direction:column; align-items:flex-start; gap:0.5mm; }',
        '.r-logo  { height:11mm; width:auto; max-width:26mm; object-fit:contain; }',
        '.r-logo-am { height:13mm; width:auto; max-width:30mm; object-fit:contain; }',
        '.r-dekra { font-size:4pt; color:' + ANT + '; font-weight:800; letter-spacing:0.05mm; }',
        '.r-subhdr { background:#fff; border-bottom:0.3mm solid #e4e4e4; padding:0.55mm 2.5mm;',
        '  display:flex; align-items:center; flex-shrink:0; }',
        '.r-subhdr-title { font-size:6.5pt; color:' + ANT + '; font-style:italic; }',
        '.r-body { display:flex; flex:1; padding:1.2mm 2.5mm 0; gap:2mm; min-height:0; overflow:hidden; }',
        '.r-left { flex:1; min-width:0; display:flex; flex-direction:column; }',
        '.r-right { width:14.5mm; flex-shrink:0; display:flex; flex-direction:column; align-items:center; gap:0.7mm; padding-top:0.2mm; }',
        '.r-fam-badge { display:inline-block; background:' + RED + '; color:#fff; font-size:6.5pt; font-weight:900;',
        '  padding:0.4mm 2mm; border-radius:0.7mm; margin-bottom:0.7mm; letter-spacing:0.1mm; white-space:nowrap; }',
        '.r-nums { font-size:8pt; color:' + RED + '; font-weight:800; margin-top:1.5mm; margin-bottom:0.4mm; letter-spacing:0.2mm; }',
        '.r-nums .lbl { font-weight:400; color:' + ANT + '; font-size:6.5pt; }',
        '.r-titulaire { font-size:9pt; font-weight:900; font-style:italic; color:' + ANT + '; margin-bottom:0.3mm; line-height:1.2; }',
        '.r-ddn { font-size:7pt; color:' + ANT + '; font-style:italic; }',
        '.r-spacer { flex:1; min-height:0.5mm; }',
        '.r-org { font-size:6pt; color:' + ANT + '; font-weight:700; line-height:1.25; margin-bottom:0.25mm; }',
        '.r-siret { font-size:5pt; color:' + ANT + '; margin-bottom:0.35mm; line-height:1.3; }',
        '.r-sign { font-size:5.2pt; color:' + ANT + '; display:flex; align-items:center; gap:0.8mm; padding-bottom:0.4mm; }',
        '.r-sign img { height:3.5mm; width:auto; max-width:8mm; object-fit:contain; }',
        '.r-photo { width:11mm; height:12mm; object-fit:cover; border:0.4mm solid #bbb; display:block; border-radius:0.6mm; }',
        '.r-photo-ph { width:11mm; height:12mm; background:#eee; border:0.4mm solid #bbb; border-radius:0.6mm; }',
        '.r-sep { width:11mm; height:0.25mm; background:#d0d0d0; margin:0.4mm 0 0.2mm; flex-shrink:0; }',
        '#qr canvas, #qr img { width:10mm !important; height:10mm !important; display:block; }',
        '.r-qr-text { font-size:3.8pt; color:' + ANT + '; text-align:center; line-height:1.25; font-style:italic; max-width:11mm; }',
        '.r-ftr { flex-shrink:0; background:#f0f0f0; border-top:0.3mm solid #d0d0d0;',
        '  padding:0.7mm 2.5mm; font-size:5.2pt; color:#111; font-style:italic;',
        '  text-align:center; line-height:1.3; }',
        '.v-hdr { background:#fff; border-bottom:0.7mm solid ' + RED + '; padding:0.6mm 2.5mm; flex-shrink:0; display:flex; align-items:center; justify-content:space-between; gap:1mm; }',
        '.v-hdr-info { flex:1; min-width:0; }',
        '.v-logo2 { height:6mm; width:auto; max-width:14mm; object-fit:contain; flex-shrink:0; }',
        '.v-htitle { font-size:6pt; font-weight:900; color:' + ANT + '; line-height:1.2; }',
        '.v-hddn { font-size:4.3pt; font-weight:400; color:' + ANT + '; font-style:italic; }',
        '.v-hcarte { font-size:5.2pt; color:' + RED + '; font-weight:700; font-family:monospace; margin-top:0.2mm; }',
        '.v-hdate { color:' + ANT + '; font-weight:400; font-family:Arial,sans-serif; font-size:4.5pt; }',
        '.v-notices { padding:0.5mm 2.5mm; font-size:4.3pt; color:' + ANT + '; line-height:1.3; flex-shrink:0; border-bottom:0.15mm solid #e0e0e0; }',
        '.v-tbl { flex:1; padding:0 2.5mm; overflow:hidden; }',
        'table { width:100%; border-collapse:collapse; }',
        'thead tr { background:' + ANT + '; }',
        'th { font-size:3.8pt; font-weight:700; color:#fff; text-transform:uppercase; padding:0.5mm 0.4mm;',
        '  text-align:left; white-space:nowrap; letter-spacing:0.04mm; }',
        'tbody tr:nth-child(even) { background:#f5f5f5; }',
        'td { font-size:5.2pt; padding:0.4mm 0.4mm; border-bottom:0.1mm solid #ebebeb; vertical-align:middle; color:' + ANT + '; }',
        '.vfam { font-weight:800; color:' + RED + '; font-size:5pt; white-space:nowrap; }',
        '.vcat { font-weight:900; color:' + ANT + '; font-size:5.2pt; white-space:nowrap; }',
        '.vno { font-family:monospace; font-weight:800; font-size:5pt; white-space:nowrap; color:' + ANT + '; }',
        '.vopt-badge { display:inline-block; background:#e6e6e6; color:' + ANT + '; font-size:3.8pt;',
        '  font-weight:600; padding:0.1mm 0.5mm; border-radius:0.4mm; white-space:nowrap; border:0.15mm solid #c0c0c0; }',
        '.vdt { font-size:4.8pt; white-space:nowrap; color:' + ANT + '; font-weight:700; }',
        '.vval { font-weight:700; font-size:4.8pt; color:' + ANT + '; white-space:nowrap; }',
        '.vopt { max-width:9mm; overflow:hidden; }',
        '.vlib { color:' + ANT + '; font-size:4.2pt; font-style:italic; font-weight:600; }',
        '.vhastest td { border-bottom:none !important; }',
        '.vtestcell { padding:0.3mm 0.4mm 0.5mm !important; font-size:3.8pt; color:' + ANT + '; font-style:italic; font-weight:600; vertical-align:middle; border-bottom:0.15mm solid #d8d8d8 !important; }',
        '.v-ftr { flex-shrink:0; background:#f0f0f0; border-top:0.3mm solid #d0d0d0;',
        '  padding:0.6mm 2.5mm; font-size:5.2pt; color:#111; font-style:italic;',
        '  text-align:center; line-height:1.3; }',
    ].join('\n');

    let wmHtml = '';
    if (data.watermark) {
        const wm = data.watermark;
        let inner = '<div class="wm-txt">' + (wm.label || '') + '</div>';
        if (wm.sub) inner += '<div class="wm-sub">' + wm.sub + '</div>';
        if (wm.sub2) inner += '<div class="wm-sub">' + wm.sub2 + '</div>';
        wmHtml = '<div class="wm"><div class="wm-inner">' + inner + '</div></div>';
    }

    const logoHtml = cfg.logo_uri
        ? '<img class="r-logo" src="' + cfg.logo_uri + '" />'
        : '<span style="font-size:5.5pt;font-weight:900;color:' + ANT + ';">' + (organisme || 'CACES®') + '</span>';

    const photoHtml = data.photo_url
        ? '<img class="r-photo" src="' + data.photo_url + '" />'
        : '<div class="r-photo-ph"></div>';

    const signHtml = cfg.signature_uri
        ? '<img src="' + cfg.signature_uri + '" style="height:3.5mm;width:auto;max-width:8mm;object-fit:contain;" /> '
        : '';

    const versoNotices = [
        data.famille === 'R482' ? 'Option réseaux : Ne permet pas la délivrance d\'une AIPR' : '',
        optLegend ? 'Options : ' + optLegend : '',
    ].filter(Boolean).join(' — ');

    return '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        + '<style>' + css + '</style>'
        + '<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"><\/script>'
        + '</head><body>'
        + '<div class="page">'
        +   wmHtml
        +   '<div class="r-hdr">'
        +     '<div class="r-hdr-left">'
        +       logoHtml
        +       (numeroCert ? '<div class="r-dekra">Cert. DEKRA n° ' + numeroCert + '</div>' : '')
        +     '</div>'
        +     '<img class="r-logo-am" src="/static/img/assurance_maladie_caces.jpeg" />'
        +   '</div>'
        +   '<div class="r-subhdr">'
        +     '<span class="r-subhdr-title">Certificat d\'aptitude à la conduite en sécurité</span>'
        +   '</div>'
        +   '<div class="r-body">'
        +     '<div class="r-left">'
        +       '<span class="r-fam-badge">CACES® ' + data.famille
                    + (data.famille_libelle ? ' — ' + data.famille_libelle.toUpperCase() : '') + '</span>'
        +       (numsCaces ? '<div class="r-nums"><span class="lbl">N° CACES® </span>' + numsCaces + '</div>' : '')
        +       '<div class="r-titulaire">' + data.stagiaire_nom + ' ' + data.stagiaire_prenom + '</div>'
        +       (data.stagiaire_ddn ? '<div class="r-ddn">Né(e) le ' + data.stagiaire_ddn + '</div>' : '')
        +       '<div class="r-spacer"></div>'
        +       (delivreePar ? '<div class="r-org">' + delivreePar + '</div>' : '')
        +       (siretLine ? '<div class="r-siret">' + siretLine + '</div>' : '')
        +       (sigLigne ? '<div class="r-sign">' + signHtml + sigLigne + '</div>' : '')
        +     '</div>'
        +     '<div class="r-right">'
        +       photoHtml
        +       '<div class="r-sep"></div>'
        +       '<a href="' + (verifyUrl || '') + '" target="_blank" style="display:block;text-decoration:none;">'
        +         '<div id="qr" data-url="' + (verifyUrl || data.numero_carte) + '"></div>'
        +       '</a>'
        +       '<div class="r-qr-text">Scanner · Vérifier</div>'
        +     '</div>'
        +   '</div>'
        +   '<div class="r-ftr">La marque CACES® est protégée (INPI n° 03.3237295) · Document recto/verso obligatoire</div>'
        + '</div>'
        + '<div class="page">'
        +   wmHtml
        +   '<div class="v-hdr">'
        +     '<div class="v-hdr-info">'
        +       '<div class="v-htitle">CACES® ' + data.famille + ' — ' + data.stagiaire_nom + ' ' + data.stagiaire_prenom + ddn + '</div>'
        +       '<div class="v-hcarte">N° ' + data.numero_carte + (data.date_generation ? ' <span class="v-hdate">· Édition du ' + _fmtDateCourt(data.date_generation) + '</span>' : '') + '</div>'
        +     '</div>'
        +     (cfg.logo2_uri ? '<img class="v-logo2" src="' + cfg.logo2_uri + '" />' : '')
        +   '</div>'
        +   (versoNotices ? '<div class="v-notices">' + versoNotices + '</div>' : '')
        +   '<div class="v-tbl">'
        +     '<table>'
        +       '<thead><tr>'
        +         '<th>Famille</th><th>Cat.</th><th>Opt.</th><th>N° CACES®</th>'
        +         '<th>Obtention</th><th>Validité</th><th>Libellé</th>'
        +       '</tr></thead>'
        +       '<tbody>' + versoRows + '</tbody>'
        +     '</table>'
        +   '</div>'
        +   '<div class="v-ftr">'
        +     (verifyUrl ? 'Vérification : <a href="' + verifyUrl + '" target="_blank" style="color:inherit;">' + verifyUrl + '</a> — ' : '')
        +     'Document recto/verso. Toute copie doit comporter les 2 faces.'
        +   '</div>'
        + '</div>'
        + '<script>window.onload=function(){'
        +   'var el=document.getElementById("qr");'
        +   'if(el&&el.dataset.url&&typeof QRCode!=="undefined"){'
        +     'new QRCode(el,{text:el.dataset.url,width:42,height:42,colorDark:"' + ANT + '",colorLight:"#ffffff"});'
        +   '}'
        + '};<\/script>'
        + '</body></html>';
}

function _buildA5Html(data, cfg) {
    const logoHtml = cfg.logo_uri
        ? '<img src="' + cfg.logo_uri + '" style="height:14mm;width:auto;max-width:28mm;object-fit:contain;" />'
        : '';

    const photoHtml = data.photo_url
        ? '<img src="' + data.photo_url + '" style="width:28mm;height:36mm;object-fit:cover;border:0.5mm solid #ccc;border-radius:1mm;display:block;" />'
        : '<div style="width:28mm;height:36mm;background:#f0f0f0;border:0.5mm solid #ccc;border-radius:1mm;display:flex;align-items:center;justify-content:center;"><span style="font-size:9pt;color:#aaa;">Photo</span></div>';

    const hasOpts = data.caces.some(function (co) { return co.options_obtenues; });

    const caceRows = data.caces.map(function (co) {
        const no = co.ancien_numero ? co.ancien_numero : (co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—');
        const opts = co.options_obtenues || '—';
        return '<tr>'
            + '<td style="font-weight:700;color:#1a237e;">' + co.categorie + '</td>'
            + '<td style="font-size:10pt;">' + (co.categorie_libelle || '—') + '</td>'
            + '<td style="font-family:monospace;">' + no + '</td>'
            + '<td>' + opts + '</td>'
            + '<td>' + _fmtDate(co.date_obtention) + '</td>'
            + '<td style="color:#2e7d32;font-weight:700;">' + _fmtDate(co.date_echeance) + '</td>'
            + '<td style="color:#666;">' + (co.testeur_nom || '') + '</td>'
            + '</tr>';
    }).join('');

    return '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>'
        + '* { margin:0; padding:0; box-sizing:border-box; }'
        + '@page { size: A5 landscape; margin: 0; }'
        + 'body { width:210mm; height:148mm; font-family:Arial,sans-serif; background:white; overflow:hidden; }'
        + '.carte { width:210mm; height:148mm; padding:8mm; display:flex; flex-direction:column; position:relative; }'
        + '.wm { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; overflow:hidden; z-index:50; pointer-events:none; }'
        + '.wm-inner { transform:rotate(-30deg); text-align:center; }'
        + '.wm-txt { font-size:36pt; font-weight:900; color:rgba(204,0,0,0.35); letter-spacing:2mm; white-space:nowrap; font-style:italic; }'
        + '.wm-sub { font-size:10pt; color:rgba(204,0,0,0.45); white-space:nowrap; margin-top:3mm; }'
        + '.header { display:flex; align-items:center; justify-content:space-between; margin-bottom:4mm; }'
        + '.org { font-size:11pt; font-weight:bold; color:#1a237e; flex:1; text-align:center; padding:0 4mm; }'
        + '.num-carte { font-size:9pt; font-family:monospace; color:#1a237e; font-weight:bold; white-space:nowrap; }'
        + '.divider { height:0.5mm; background:#1a237e; margin-bottom:4mm; }'
        + '.body { display:flex; gap:6mm; flex:1; min-height:0; }'
        + '.info { flex:1; min-width:0; }'
        + '.nom { font-size:14pt; font-weight:bold; color:#1a237e; }'
        + '.prenom { font-size:11pt; color:#555; margin-bottom:3mm; }'
        + '.famille-badge { display:inline-block; background:#1a237e; color:white; font-size:10pt; font-weight:bold; padding:1mm 3mm; border-radius:2mm; margin-bottom:3mm; }'
        + 'table { width:100%; border-collapse:collapse; }'
        + 'th { font-size:8pt; text-transform:uppercase; color:#666; text-align:left; padding:2mm 2.5mm; border-bottom:0.4mm solid #ccc; background:#f5f5f5; }'
        + 'td { font-size:10pt; padding:2mm 2.5mm; border-bottom:0.2mm solid #f0f0f0; }'
        + '.footer { font-size:8pt; color:#aaa; text-align:center; margin-top:3mm; border-top:0.3mm solid #eee; padding-top:2mm; }'
        + '@media print { body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }'
        + '</style></head><body>'
        + '<div class="carte">'
        + (data.watermark ? (function(wm){ let i='<div class="wm-txt">'+(wm.label||'')+'</div>'; if(wm.sub) i+='<div class="wm-sub">'+wm.sub+'</div>'; if(wm.sub2) i+='<div class="wm-sub">'+wm.sub2+'</div>'; return '<div class="wm"><div class="wm-inner">'+i+'</div></div>'; })(data.watermark) : '')
        + '  <div class="header">'
        + '    ' + logoHtml
        + '    <span class="org">' + (cfg.nom_organisme || 'Certificat CACES®') + '</span>'
        + '    <span class="num-carte">' + data.numero_carte + '</span>'
        + '  </div>'
        + '  <div class="divider"></div>'
        + '  <div class="body">'
        + '    <div>' + photoHtml + '</div>'
        + '    <div class="info">'
        + '      <div class="nom">' + data.stagiaire_nom + '</div>'
        + '      <div class="prenom">' + data.stagiaire_prenom + (data.stagiaire_ddn ? ' <span style="font-size:9pt;color:#888;font-weight:400;">- ' + data.stagiaire_ddn + '</span>' : '') + '</div>'
        + '      <span class="famille-badge">' + data.famille + (data.famille_libelle ? ' – ' + data.famille_libelle : '') + '</span>'
        + '      <table>'
        + '        <thead><tr><th>Cat.</th><th>Libellé</th><th>N° CACES®</th><th>Options</th><th>Obtention</th><th>Échéance</th><th>Testeur</th></tr></thead>'
        + '        <tbody>' + caceRows + '</tbody>'
        + '      </table>'
        + '    </div>'
        + '  </div>'
        + (cfg.url_verification_caces ? '<div class="footer">Vérification : ' + cfg.url_verification_caces + '</div>' : '')
        + '</div>'
        + '</body></html>';
}
