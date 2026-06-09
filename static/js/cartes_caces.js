document.addEventListener('DOMContentLoaded', function () {

    chargerTout();

    document.getElementById('btn-refresh').addEventListener('click', chargerTout);

    // --- PIN modal ---
    document.getElementById('btn-pin-carte-annuler').addEventListener('click', _fermerPin);
    document.getElementById('pin-carte-input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') document.getElementById('btn-pin-carte-confirmer').click();
    });
    document.getElementById('modal-pin-carte').addEventListener('click', function (e) {
        if (e.target === this) _fermerPin();
    });

    // --- Récap modal ---
    document.getElementById('btn-recap-annuler').addEventListener('click', _fermerRecap);
    document.getElementById('modal-recap').addEventListener('click', function (e) {
        if (e.target === this) _fermerRecap();
    });
    document.getElementById('btn-recap-confirmer').addEventListener('click', function () {
        const stagId = this.dataset.stagId;
        const famille = this.dataset.famille;
        _fermerRecap();
        _ouvrirPin('Préparer la carte ' + famille + ' ?', async function (pin) {
            const r = await fetch('/api/cartes-caces/preparer/' + stagId + '/' + encodeURIComponent(famille) + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
            if (r.ok) { chargerTout(); }
            return r;
        });
    });

    // --- Motif modal ---
    document.getElementById('btn-motif-carte-annuler').addEventListener('click', _fermerMotif);
    document.getElementById('modal-motif-carte').addEventListener('click', function (e) {
        if (e.target === this) _fermerMotif();
    });

    // --- Délégation clics ---
    document.addEventListener('click', function (e) {

        // Préparer la carte (à préparer)
        const btnPreparer = e.target.closest('[data-action="preparer-carte"]');
        if (btnPreparer) {
            const stagId = btnPreparer.dataset.stagId;
            const famille = btnPreparer.dataset.famille;
            const nom = btnPreparer.dataset.nom;
            const cacesJson = btnPreparer.dataset.caces;
            _ouvrirRecap(stagId, famille, nom, JSON.parse(cacesJson));
            return;
        }

        // Émettre (en préparation)
        const btnEmettre = e.target.closest('[data-action="emettre-carte"]');
        if (btnEmettre) {
            const id = btnEmettre.dataset.id;
            const num = btnEmettre.dataset.num;
            _ouvrirPin('Émettre la carte ' + num + ' ?', async function (pin) {
                const r = await fetch('/api/cartes-caces/emettre/' + id + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
                if (r.ok) { chargerTout(); }
                return r;
            });
            return;
        }

        // Annuler (en préparation ou émise)
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
                    if (r.ok) { chargerTout(); }
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

// ===== RÉCAP MODAL =====
function _ouvrirRecap(stagId, famille, nom, caces) {
    document.getElementById('recap-titre').textContent = '📋 Récapitulatif — ' + nom + ' · ' + famille;
    const btn = document.getElementById('btn-recap-confirmer');
    btn.dataset.stagId = stagId;
    btn.dataset.famille = famille;

    const rows = caces.map(function (co) {
        const no = co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—';
        const testeur = co.testeur_nom ? '<span style="font-size:11px;color:#666;">| ' + co.testeur_nom + '</span>' : '';
        return '<tr>'
            + '<td style="font-size:13px;font-weight:700;padding:6px 8px;">' + co.categorie + '</td>'
            + '<td style="padding:6px 8px;"><span style="font-family:monospace;font-size:12px;background:#e8eaf6;padding:2px 6px;border-radius:4px;">' + no + '</span></td>'
            + '<td style="font-size:12px;color:#555;padding:6px 8px;">' + _fmtDate(co.date_obtention) + '</td>'
            + '<td style="font-size:12px;color:#2e7d32;padding:6px 8px;">' + _fmtDate(co.date_echeance) + ' ' + testeur + '</td>'
            + '</tr>';
    }).join('');

    document.getElementById('recap-body').innerHTML = '<table style="width:100%;border-collapse:collapse;">'
        + '<thead><tr style="background:#f0f2f7;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#555;">'
        + '<th style="padding:6px 8px;text-align:left;">Cat.</th><th style="padding:6px 8px;text-align:left;">N° CACES®</th>'
        + '<th style="padding:6px 8px;text-align:left;">Obtention</th><th style="padding:6px 8px;text-align:left;">Échéance</th>'
        + '</tr></thead><tbody>' + rows + '</tbody></table>';

    document.getElementById('modal-recap').style.display = 'flex';
}

function _fermerRecap() {
    document.getElementById('modal-recap').style.display = 'none';
}

// ===== UTILITAIRES =====
function _fmtDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y;
}

// ===== RENDU =====
function _renderAPreparer(item) {
    const photoBadge = item.photo_manquante
        ? '<span class="badge" style="background:#ffebee;color:#c62828;font-size:11px;">📷 Photo manquante</span>'
        : '';
    const cacesResume = item.caces.map(function (co) {
        const no = co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—';
        return '<span style="font-size:12px;margin-right:8px;">'
            + '<strong>' + co.categorie + '</strong>'
            + ' <span style="font-family:monospace;color:#1a237e;">' + no + '</span>'
            + ' <span style="color:#888;">' + _fmtDate(co.date_obtention) + '</span>'
            + '</span>';
    }).join('');
    const cacesJson = JSON.stringify(item.caces).replace(/"/g, '&quot;');
    const nomComplet = item.stagiaire_nom + ' ' + item.stagiaire_prenom;
    const disabled = item.photo_manquante ? 'disabled title="Photo manquante — impossible d\'émettre"' : '';
    const btnStyle = item.photo_manquante
        ? 'background:#e0e0e0;color:#999;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;cursor:not-allowed;'
        : 'background:#1a237e;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;';

    return '<div style="border:1px solid #c8d8f0;border-radius:12px;padding:14px 18px;margin-bottom:10px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.05);">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">'
        + '<div style="flex:1;min-width:0;">'
        + '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">'
        + '<span style="font-size:15px;font-weight:700;color:#1a237e;">' + nomComplet + '</span>'
        + '<span style="background:#1a237e;color:#fff;border-radius:6px;padding:2px 10px;font-size:13px;font-weight:800;">' + item.famille + '</span>'
        + photoBadge
        + '</div>'
        + '<div style="flex-wrap:wrap;display:flex;gap:4px;">' + cacesResume + '</div>'
        + '</div>'
        + '<button ' + disabled + ' ' + btnStyle + ' data-action="preparer-carte" data-stag-id="' + item.stagiaire_id + '" data-famille="' + item.famille + '" data-nom="' + nomComplet + '" data-caces="' + cacesJson + '">'
        + '📇 Préparer la carte'
        + '</button>'
        + '</div>'
        + '</div>';
}

function _renderEnPreparation(carte) {
    const nomComplet = carte.stagiaire_nom + ' ' + carte.stagiaire_prenom;
    return '<div style="border:1px solid #ffe082;border-radius:12px;padding:12px 18px;margin-bottom:8px;background:#fffde7;box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">'
        + '<div>'
        + '<span style="font-family:monospace;font-size:15px;font-weight:700;color:#1a237e;margin-right:10px;">' + carte.numero_carte + '</span>'
        + '<span style="font-size:14px;font-weight:600;">' + nomComplet + '</span>'
        + ' <span style="background:#1a237e;color:#fff;border-radius:6px;padding:2px 8px;font-size:12px;font-weight:800;margin-left:4px;">' + carte.famille + '</span>'
        + '<span style="font-size:12px;color:#888;margin-left:10px;">Préparée le ' + _fmtDate(carte.date_generation) + '</span>'
        + '</div>'
        + '<div style="display:flex;gap:8px;">'
        + '<button data-action="emettre-carte" data-id="' + carte.id + '" data-num="' + carte.numero_carte + '" '
        + 'style="background:#2e7d32;color:#fff;border:none;border-radius:8px;padding:7px 16px;font-size:13px;font-weight:700;cursor:pointer;">✅ Émettre</button>'
        + '<button data-action="annuler-carte" data-id="' + carte.id + '" data-num="' + carte.numero_carte + '" '
        + 'style="background:#fff;border:2px solid #c62828;color:#c62828;border-radius:8px;padding:7px 12px;font-size:13px;font-weight:700;cursor:pointer;">❌ Annuler</button>'
        + '</div>'
        + '</div>';
}

function _renderEmise(carte) {
    const nomComplet = carte.stagiaire_nom + ' ' + carte.stagiaire_prenom;
    const annulee = carte.statut === 'annulee';
    const badgeHtml = annulee
        ? '<span class="badge" style="background:#ffebee;color:#c62828;">Annulée</span>'
        : '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">Émise</span>';
    const motifHtml = annulee && carte.motif_annulation
        ? '<div style="font-size:11px;color:#888;margin-top:2px;font-style:italic;">' + carte.motif_annulation + '</div>'
        : '';
    const actionsHtml = annulee ? '' :
        '<div style="display:flex;gap:6px;">'
        + '<button data-action="annuler-carte" data-id="' + carte.id + '" data-num="' + carte.numero_carte + '" '
        + 'title="Annuler cette carte" style="background:none;border:1px solid #c62828;color:#c62828;border-radius:6px;padding:3px 8px;font-size:11px;cursor:pointer;">❌ Annuler</button>'
        + '</div>';

    return '<tr style="' + (annulee ? 'opacity:0.55;' : '') + '">'
        + '<td style="font-family:monospace;font-size:13px;font-weight:700;color:#1a237e;white-space:nowrap;' + (annulee ? 'text-decoration:line-through;' : '') + '">' + carte.numero_carte + '</td>'
        + '<td style="font-weight:600;font-size:13px;">' + nomComplet + motifHtml + '</td>'
        + '<td><span style="background:#1a237e;color:#fff;border-radius:5px;padding:2px 8px;font-size:12px;font-weight:800;">' + carte.famille + '</span></td>'
        + '<td style="font-size:12px;color:#666;white-space:nowrap;">' + _fmtDate(carte.date_generation) + '</td>'
        + '<td>' + badgeHtml + '</td>'
        + '<td>' + actionsHtml + '</td>'
        + '</tr>';
}

// ===== CHARGEMENT =====
function chargerTout() {
    chargerAPreparer();
    chargerEnPreparation();
    chargerEmises();
}

async function chargerAPreparer() {
    const el = document.getElementById('liste-a-preparer');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement…</p>';
    try {
        const r = await fetch('/api/cartes-caces/a-preparer');
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#2e7d32;padding:16px;">✅ Aucune carte à préparer.</p>';
            return;
        }
        el.innerHTML = data.map(_renderAPreparer).join('');
    } catch (_) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}

async function chargerEnPreparation() {
    const el = document.getElementById('liste-en-preparation');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement…</p>';
    try {
        const r = await fetch('/api/cartes-caces/en-preparation');
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096;padding:16px;">Aucune carte en préparation.</p>';
            return;
        }
        el.innerHTML = data.map(_renderEnPreparation).join('');
    } catch (_) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}

async function chargerEmises() {
    const el = document.getElementById('liste-emises');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement…</p>';
    try {
        const r = await fetch('/api/cartes-caces/emises');
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096;padding:16px;">Aucune carte émise.</p>';
            return;
        }
        // Triées : émises en haut, annulées en bas
        data.sort(function (a, b) {
            if (a.statut !== b.statut) return a.statut === 'emise' ? -1 : 1;
            return a.date_generation < b.date_generation ? 1 : -1;
        });
        el.innerHTML = '<table class="table"><thead><tr>'
            + '<th>N° Carte</th><th>Stagiaire</th><th>Famille</th><th>Date émission</th><th>Statut</th><th></th>'
            + '</tr></thead><tbody>'
            + data.map(_renderEmise).join('')
            + '</tbody></table>';
    } catch (_) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}
