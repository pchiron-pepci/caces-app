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

    // --- Sélect stagiaire → si homonymes, montrer select DDN, sinon charger familles ---
    document.getElementById('sel-stagiaire').addEventListener('change', function () {
        const nomPrenom = this.value;
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
            // Plusieurs homonymes → proposer le choix de la DDN
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

    // --- Délégation clics ---
    document.addEventListener('click', function (e) {

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
    const sel = document.getElementById('sel-stagiaire');
    try {
        const r = await fetch('/api/cartes-caces/stagiaires');
        if (!r.ok) return;
        const data = await r.json();
        // Construire les groupes
        data.forEach(function (s) {
            const key = s.nom + ' ' + s.prenom;
            if (!_stagiairesParNom[key]) _stagiairesParNom[key] = [];
            _stagiairesParNom[key].push({ id: s.id, ddn: s.date_naissance || null });
        });
        // Une seule option par nom unique (la valeur = clé nom+prénom)
        Object.keys(_stagiairesParNom).sort().forEach(function (nom) {
            const opt = document.createElement('option');
            opt.value = nom;
            opt.textContent = nom;
            sel.appendChild(opt);
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
                    + '<td style="font-family:monospace; font-size:13px; padding:8px 10px;"><span style="background:#e8eaf6; padding:2px 8px; border-radius:4px;">' + _noFormate(co.numero_ordre) + '</span></td>'
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
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096; padding:16px;">Aucune carte émise.</p>';
            return;
        }
        const rows = data.map(_renderEmise).join('');
        el.innerHTML = '<table class="table"><thead><tr>'
            + '<th style="width:32px;"></th>'
            + '<th>N° Carte</th><th>Stagiaire</th><th>Famille</th><th>Date</th><th>Statut</th><th></th>'
            + '</tr></thead><tbody>' + rows + '</tbody></table>';
    } catch (_) {
        el.innerHTML = '<p style="color:red; text-align:center; padding:24px;">Erreur de chargement</p>';
    }
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

    const actionsHtml = emise
        ? '<div style="display:flex;gap:6px;">'
            + '<button data-action="reimprimer-carte" data-id="' + carte.id + '" title="Réimprimer" '
            + 'style="background:none;border:1px solid #1a237e;color:#1a237e;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">🖨️</button>'
            + '<button data-action="annuler-carte" data-id="' + carte.id + '" data-num="' + carte.numero_carte + '" title="Annuler" '
            + 'style="background:none;border:1px solid #c62828;color:#c62828;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">❌</button>'
            + '</div>'
        : '';

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
                + '<td style="font-family:monospace;font-size:12px;padding:5px 10px;"><span style="background:#e8eaf6;padding:1px 7px;border-radius:3px;">' + _noFormate(co.numero_ordre) + '</span></td>'
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
    setTimeout(function () { w.print(); }, 700);
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
    // Numéros CACES® formattés (0427-0429-...)
    const numsCaces = data.caces
        .map(function (co) { return co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : ''; })
        .filter(Boolean).join('-');

    // Signataire complet
    const sigNom = [cfg.signataire_prenom, cfg.signataire_nom].filter(Boolean).join(' ');
    const sigLigne = [sigNom, cfg.signataire_qualite].filter(Boolean).join(' - ');

    // Options présentes sur la carte
    const allOpts = {};
    data.caces.forEach(function (co) {
        if (co.options_obtenues) {
            co.options_obtenues.split(',').forEach(function (o) { allOpts[o.trim()] = true; });
        }
    });
    const optLabels = { 'PE': 'Porte-engin', 'TE': 'Télécommande', 'TEL': 'Télécommande', 'CC': 'Conduite cabine', 'TR': 'Translation rails', 'CEC': 'Circulation en charge' };
    const optLegend = Object.keys(allOpts).map(function (k) { return k + ' : ' + (optLabels[k] || k); }).join(' - ');

    // RECTO — lignes du tableau verso
    const versoRows = data.caces.map(function (co) {
        const no = co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—';
        const opts = co.options_obtenues || '';
        const libelle = co.categorie_libelle || '';
        return '<tr>'
            + '<td class="vfam">' + data.famille + '</td>'
            + '<td class="vcat">' + co.categorie + '</td>'
            + '<td class="vno">' + no + '</td>'
            + '<td class="vopt">' + opts + '</td>'
            + '<td class="vdt">' + _fmtDateCourt(co.date_obtention) + '</td>'
            + '<td class="vval">' + _fmtDateCourt(co.date_echeance) + '</td>'
            + '<td class="vtest">' + (co.testeur_nom || '') + '</td>'
            + '<td class="vlib">' + libelle + '</td>'
            + '</tr>';
    }).join('');

    const css = [
        '* { margin:0; padding:0; box-sizing:border-box; }',
        '@page { size: 85.6mm 54mm; margin: 0; }',
        'html, body { width:85.6mm; height:108mm; font-family:Arial,sans-serif; font-size:5.5pt; background:white; }',
        '.page { width:85.6mm; height:54mm; overflow:hidden; position:relative; }',
        '.page + .page { page-break-before: always; }',
        /* RECTO */
        '.recto { padding:1.5mm 2mm; display:flex; flex-direction:column; }',
        '.r-top { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:0.5mm; }',
        '.r-logo { height:8.5mm; width:auto; max-width:21mm; object-fit:contain; }',
        '.r-logo-am { height:9.5mm; width:auto; max-width:24mm; object-fit:contain; }',
        '.r-titre { font-size:5.8pt; font-weight:bold; text-align:center; color:#333; margin-bottom:1mm; }',
        '.r-body { display:flex; align-items:flex-start; gap:1.5mm; flex:1; }',
        '.r-left { flex:1; min-width:0; }',
        '.r-fam { font-size:6pt; font-weight:bold; color:#1a237e; margin-bottom:0.5mm; }',
        '.r-titulaire { margin-bottom:0.4mm; }',
        '.r-titulaire .label { font-size:5pt; color:#666; }',
        '.r-titulaire .val { font-size:5.5pt; font-weight:bold; font-style:italic; color:#111; }',
        '.r-titulaire .ddn { font-size:5pt; font-style:italic; color:#555; }',
        '.r-nums { font-size:5pt; margin-bottom:0.4mm; }',
        '.r-nums .label { color:#666; }',
        '.r-nums .val { font-style:italic; font-weight:600; color:#333; }',
        '.r-carte { font-size:5pt; margin-bottom:0.2mm; }',
        '.r-carte .org { font-weight:bold; }',
        '.r-siret { font-size:4.8pt; color:#444; margin-bottom:0.4mm; }',
        '.r-sign { font-size:4.8pt; color:#444; display:flex; align-items:center; gap:1mm; margin-bottom:0.5mm; }',
        '.r-sign img { height:4mm; width:auto; max-width:9mm; object-fit:contain; opacity:0.85; }',
        '.r-legal { font-size:4.2pt; color:#666; font-style:italic; font-weight:bold; text-align:center; margin-top:auto; line-height:1.3; }',
        '.r-photo { width:9mm; height:12mm; object-fit:cover; border:0.3mm solid #bbb; flex-shrink:0; display:block; }',
        '.r-photo-ph { width:9mm; height:12mm; background:#f0f0f0; border:0.3mm solid #bbb; flex-shrink:0; }',
        /* VERSO */
        '.verso { padding:1.5mm 2mm; display:flex; flex-direction:column; }',
        '.v-head { font-size:6pt; font-weight:bold; color:#1a237e; margin-bottom:0.5mm; }',
        '.v-sub { font-size:4.8pt; color:#555; margin-bottom:0.3mm; }',
        '.v-opt-legend { font-size:4.5pt; color:#555; margin-bottom:1mm; }',
        'table { width:100%; border-collapse:collapse; }',
        'thead tr { background:#1a237e; color:white; }',
        'th { font-size:4pt; padding:0.5mm 0.5mm; text-align:left; white-space:nowrap; }',
        'td { font-size:4.8pt; padding:0.4mm 0.5mm; border-bottom:0.15mm solid #e8e8e8; }',
        '.vfam, .vcat { font-weight:bold; color:#1a237e; }',
        '.vno { font-family:monospace; }',
        '.vval { font-weight:bold; color:#2e7d32; }',
        '.vtest { color:#666; font-size:4.2pt; }',
        '.vlib { color:#555; font-size:4.2pt; }',
        '.v-footer { font-size:4.2pt; color:#666; font-style:italic; font-weight:bold; text-align:center; margin-top:auto; padding-top:1mm; line-height:1.3; }',
        '@media print { html,body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }',
    ].join('\n');

    const logoHtml = cfg.logo_uri
        ? '<img class="r-logo" src="' + cfg.logo_uri + '" />'
        : '<span style="font-size:5pt;font-weight:bold;color:#1a237e;">' + (cfg.nom_organisme || '') + '</span>';

    const photoHtml = data.photo_url
        ? '<img class="r-photo" src="' + data.photo_url + '" />'
        : '<div class="r-photo-ph"></div>';

    const signHtml = cfg.signature_uri
        ? '<img src="' + cfg.signature_uri + '" style="height:4mm;width:auto;max-width:9mm;object-fit:contain;opacity:0.85;" /> '
        : '';

    const organisme = cfg.nom_organisme || 'PEPCI Formation';
    const adresse = cfg.adresse || '';
    const carteDelivree = adresse
        ? 'Carte délivrée par <span class="org">' + organisme + '</span> - ' + adresse
        : 'Carte délivrée par <span class="org">' + organisme + '</span>';
    const siretLine = [
        cfg.siret ? 'Siret : ' + cfg.siret : '',
        cfg.email ? 'email : ' + cfg.email : '',
        cfg.telephone ? 'Tél. : ' + cfg.telephone : '',
    ].filter(Boolean).join(' - ');

    const versoLegend = optLegend
        ? '<div class="v-opt-legend">*Option(s) = ' + optLegend + '</div>'
        : '';

    const versoSubR482 = data.famille === 'R482'
        ? '<div class="v-sub">Option réseaux : Ne permet pas la délivrance d\'une AIPR</div>'
        : '';

    const verificationLine = cfg.url_verification_caces || cfg.email || '';

    return '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>' + css + '</style></head><body>'

        // ===== RECTO =====
        + '<div class="page recto">'
        + '<div class="r-top">'
        + logoHtml
        + '<img class="r-logo-am" src="/static/img/assurance_maladie_caces.jpeg" />'
        + '</div>'
        + '<div class="r-titre">Certificat d\'aptitude à la conduite en sécurité</div>'
        + '<div class="r-body">'
        + '<div class="r-left">'
        + '<div class="r-fam">CACES® - ' + data.famille + (data.famille_libelle ? ' - ' + data.famille_libelle.toUpperCase() : '') + '</div>'
        + '<div class="r-titulaire"><span class="label">Titulaire : </span><span class="val">' + data.stagiaire_nom + ' ' + data.stagiaire_prenom + '</span>'
        + (data.stagiaire_ddn ? ' <span class="ddn">- ' + data.stagiaire_ddn + '</span>' : '') + '</div>'
        + (numsCaces ? '<div class="r-nums"><span class="label">N° certificats : </span><span class="val">' + numsCaces + '</span></div>' : '')
        + '<div class="r-carte">' + carteDelivree + '</div>'
        + (siretLine ? '<div class="r-siret">' + siretLine + '</div>' : '')
        + (sigLigne ? '<div class="r-sign">' + signHtml + sigLigne + '</div>' : '')
        + '</div>'
        + photoHtml
        + '</div>'
        + '<div class="r-legal">La marque CACES® est protégée (INPI n° 03.3237295)<br>Document recto/verso. Toute copie doit comporter les 2 faces.</div>'
        + '</div>'

        // ===== VERSO =====
        + '<div class="page verso">'
        + '<div class="v-head">CACES® ' + data.famille + ' - Titulaire : ' + data.stagiaire_nom + ' ' + data.stagiaire_prenom + '</div>'
        + versoSubR482
        + versoLegend
        + '<table>'
        + '<thead><tr><th>Famille</th><th>Cat.</th><th>N° CACES®</th><th>Options</th><th>Obtention</th><th>Validité</th><th>Testeur</th><th>Libellé</th></tr></thead>'
        + '<tbody>' + versoRows + '</tbody>'
        + '</table>'
        + '<div class="v-footer">'
        + (verificationLine ? 'Vérification : ' + verificationLine + '<br>' : '')
        + 'Document recto/verso. Toute copie doit comporter les 2 faces.'
        + '</div>'
        + '</div>'

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
        const no = co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—';
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
        + '.carte { width:210mm; height:148mm; padding:8mm; display:flex; flex-direction:column; }'
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
