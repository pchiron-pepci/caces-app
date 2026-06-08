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
            ouvrirMotif('Motif de l\'annulation du CACES® de ' + nom, '', function (motif) {
                fermerMotif();
                ouvrirPin('Confirmer l\'annulation du CACES® de ' + nom + ' ?', async function (pin) {
                    const r = await fetch('/api/caces-obtenus/annuler/' + id + '?pin=' + encodeURIComponent(pin), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motif: motif }),
                    });
                    if (r.ok) _apresAnnulation(id, motif);
                    return r;
                });
            });
            return;
        }

        // Voir / modifier motif (ligne annulée)
        const btnMotif = e.target.closest('[data-action="voir-motif"]');
        if (btnMotif) {
            const id = parseInt(btnMotif.dataset.id);
            const nom = btnMotif.dataset.nom || '';
            const motifActuel = (_validesData[id] && _validesData[id].motif_annulation) || '';
            ouvrirMotif('Motif d\'annulation' + (nom ? ' — ' + nom : ''), motifActuel, function (motif) {
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
const _carteData = {};
const _validesData = {};

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
function ouvrirMotif(titre, motifInitial, onConfirme) {
    _motifCallback = onConfirme;
    document.getElementById('motif-titre').textContent = titre;
    document.getElementById('motif-input').value = motifInitial || '';
    document.getElementById('motif-erreur').textContent = '​';
    document.getElementById('modal-motif').style.display = 'flex';
    setTimeout(function () { document.getElementById('motif-input').focus(); }, 50);
}

function fermerMotif() {
    document.getElementById('modal-motif').style.display = 'none';
    _motifCallback = null;
}

function _confirmerMotif() {
    const motif = document.getElementById('motif-input').value.trim();
    if (!motif) {
        document.getElementById('motif-erreur').textContent = '⚠️ Le motif est obligatoire.';
        return;
    }
    if (_motifCallback) _motifCallback(motif);
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
    const refTheorie = co.session_ref_theorie;
    const boutonsHtml = co.statut === 'annule'
        ? `<span style="background:#fff3e0;color:#e65100;border:2px solid #e65100;border-radius:10px;padding:10px 16px;font-size:13px;font-weight:700;">↩ En révision — actualisez pour recalculer</span>`
        : `<button data-action="revision-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="background:#fff;border:2px solid #e65100;color:#e65100;border-radius:10px;padding:10px 16px;font-size:13px;font-weight:700;cursor:pointer;">
                ↩ Révision
            </button>
            <button data-action="valider-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="background:#2e7d32;color:#fff;border:none;border-radius:10px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;">
                📜 Émettre le CACES®
            </button>`;

    return `
    <div id="caces-card-${co.id}" style="border:1px solid #e0e0e0;border-radius:12px;padding:18px 20px;margin-bottom:12px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">
            <div>
                <div style="font-size:16px;font-weight:700;color:#1a237e;"><a href="/stagiaires#${co.stagiaire_id}" target="_blank" style="color:inherit;text-decoration:none;">${nomComplet}</a></div>
                <div style="margin-top:4px;display:flex;align-items:center;gap:8px;">
                    <span style="font-weight:700;color:#1a237e;font-size:13px;">${co.famille}</span>
                    <span style="background:#1a237e;color:#fff;border-radius:6px;padding:2px 10px;font-size:14px;font-weight:800;">${co.categorie}</span>
                    ${options}
                </div>
            </div>
            <div style="text-align:right;font-size:11px;color:#999;">#${co.id}</div>
        </div>
        <div style="background:#f8f9ff;border-radius:8px;padding:10px 14px;margin-bottom:14px;display:flex;flex-direction:column;gap:6px;">
            <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
                <span style="width:70px;color:#666;font-weight:600;">🎓 Théorie</span>
                <a href="/sessions/${co.session_id_theorie}" target="_blank" style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;" title="${co.session_ref_theorie}">${refTheorie}</a>
                <span style="color:#444;white-space:nowrap;">${fmtDate(co.date_theorie)}</span>
                <span style="color:#2e7d32;font-weight:700;">✅</span>
                ${co.testeur_nom_theorie ? `<span style="font-size:12px;color:#555;margin-left:4px;">| Testeur&nbsp;: <strong>${co.testeur_nom_theorie}</strong></span>` : ''}
            </div>
            <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
                <span style="width:70px;color:#666;font-weight:600;">🔧 Pratique</span>
                <a href="/sessions/${co.session_id_pratique}" target="_blank" style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;" title="${co.session_ref_pratique}">${co.session_ref_pratique}</a>
                <span style="color:#444;white-space:nowrap;">${fmtDate(co.date_pratique)}</span>
                <span style="color:#2e7d32;font-weight:700;">✅</span>
                <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span>
                ${optionsPratique ? `<span style="display:flex;gap:3px;">${optionsPratique}</span>` : ''}
                ${co.testeur_nom ? `<span style="font-size:12px;color:#555;margin-left:4px;">| Testeur&nbsp;: <strong>${co.testeur_nom}</strong></span>` : ''}
            </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <div style="display:flex;gap:20px;font-size:13px;">
                <div><span style="color:#666;">Obtention</span><span style="font-weight:700;color:#1a237e;margin-left:6px;">${fmtDate(co.date_obtention)}</span></div>
                <div><span style="color:#666;">Échéance</span><span style="font-weight:700;color:#388e3c;margin-left:6px;">${fmtDate(co.date_echeance)}</span></div>
            </div>
            <div id="caces-card-${co.id}-actions" style="display:flex;gap:10px;align-items:center;">
                ${boutonsHtml}
            </div>
        </div>
    </div>`;
}

// ===== RENDU LIGNE VALIDÉS =====
const _COLS = '70px 1fr 110px 130px 80px 110px 110px 80px 90px';

function _renderLigne(co) {
    const annule = co.statut === 'annule';
    const nomComplet = co.stagiaire_nom + ' ' + co.stagiaire_prenom;
    const noOrdre = co.numero_ordre ? '#' + String(co.numero_ordre).padStart(4, '0') : '—';
    const motifBtn = annule
        ? `<button data-action="voir-motif" data-id="${co.id}" data-nom="${nomComplet}"
                title="${co.motif_annulation ? 'Motif : ' + co.motif_annulation.replace(/"/g, '&quot;') : 'Aucun motif'}"
                style="background:none;border:none;cursor:pointer;font-size:14px;padding:2px 4px;"
                >📝</button>`
        : `<button data-action="annuler-caces" data-id="${co.id}" data-nom="${nomComplet}"
                style="background:#fff;border:2px solid #c62828;color:#c62828;border-radius:8px;padding:4px 10px;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap;">
                ↩ Annuler
            </button>`;
    return `<div data-caces-id="${co.id}" style="display:grid;grid-template-columns:${_COLS};gap:8px;padding:10px 14px;border-bottom:1px solid #f0f0f0;align-items:center;${annule ? 'opacity:0.55;' : ''}">
        <span style="font-weight:700;font-family:monospace;color:#1a237e;font-size:13px;${annule ? 'text-decoration:line-through;' : ''}">${noOrdre}</span>
        <span style="font-weight:600;${annule ? 'text-decoration:line-through;' : ''}">${nomComplet}</span>
        <span style="font-size:12px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${co.session_reference || ''}">${co.session_reference || '—'}</span>
        <span><strong style="color:#1a237e;">${co.famille}</strong> <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span></span>
        <span style="font-size:11px;color:#666;">${co.options_obtenues || '—'}</span>
        <span style="font-size:12px;">${fmtDate(co.date_obtention)}</span>
        <span style="font-size:12px;">${fmtDate(co.date_echeance)}</span>
        ${badgeStatut(co.statut)}
        <span>${motifBtn}</span>
    </div>`;
}

function _enteteValides() {
    return `<div id="valides-entete" style="display:grid;grid-template-columns:${_COLS};gap:8px;padding:7px 14px;background:#f0f2fa;border-radius:8px;margin-bottom:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#555;">
        <span>N° Ordre</span><span>Stagiaire</span><span>Session</span><span>Famille / Cat.</span><span>Options</span><span>Obtention</span><span>Échéance</span><span>Statut</span><span></span>
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
        _ajouterLigneValide(co);
    }
}

function _apresRevisionCarte(id) {
    const actionsEl = document.getElementById('caces-card-' + id + '-actions');
    if (actionsEl) {
        actionsEl.innerHTML = '<span style="background:#fff3e0;color:#e65100;border:2px solid #e65100;border-radius:10px;padding:10px 16px;font-size:13px;font-weight:700;">↩ En révision — actualisez pour recalculer</span>';
    }
}

function _apresAnnulation(id, motif) {
    if (_validesData[id]) _validesData[id].motif_annulation = motif;
    const el = document.getElementById('liste-valides');
    if (!el) return;
    const row = el.querySelector('[data-caces-id="' + id + '"]');
    if (row) row.remove();
    const co = _validesData[id];
    if (!co) return;
    co.statut = 'annule';
    co.motif_annulation = motif;
    el.appendChild(_creerNoeudLigne(co));
}

function _ajouterLigneValide(co) {
    const el = document.getElementById('liste-valides');
    if (!el) return;
    _validesData[co.id] = co;
    const entete = document.getElementById('valides-entete');
    if (entete) {
        entete.insertAdjacentHTML('afterend', _renderLigne(co));
    } else {
        el.innerHTML = _enteteValides() + _renderLigne(co);
    }
}

function _creerNoeudLigne(co) {
    const div = document.createElement('div');
    div.innerHTML = _renderLigne(co);
    return div.firstElementChild;
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
    const el = document.getElementById('liste-valides');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement...</p>';
    Object.keys(_validesData).forEach(k => delete _validesData[k]);
    try {
        const r = await fetch('/api/caces-obtenus/valides');
        if (!r.ok) throw new Error('Erreur ' + r.status);
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Aucun CACES® validé.</p>';
            return;
        }
        // Trier : validés en haut (par numéro desc), annulés en bas
        data.sort(function (a, b) {
            if (a.statut !== b.statut) return a.statut === 'valide' ? -1 : 1;
            return (b.numero_ordre || 0) - (a.numero_ordre || 0);
        });
        data.forEach(co => { _validesData[co.id] = co; });
        el.innerHTML = _enteteValides() + data.map(_renderLigne).join('');
    } catch (err) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}
