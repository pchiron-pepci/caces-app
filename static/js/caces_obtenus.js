document.addEventListener('DOMContentLoaded', function () {

    chargerAValider();
    chargerValides();

    document.getElementById('btn-refresh').addEventListener('click', function () {
        chargerAValider();
        chargerValides();
    });

    document.getElementById('btn-pin-annuler').addEventListener('click', fermerPin);

    document.getElementById('pin-input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') document.getElementById('btn-pin-confirmer').click();
    });

    document.getElementById('modal-pin').addEventListener('click', function (e) {
        if (e.target === this) fermerPin();
    });

    document.addEventListener('click', function (e) {
        const btnValider = e.target.closest('[data-action="valider-caces"]');
        if (btnValider) {
            const id = btnValider.dataset.id;
            const nom = btnValider.dataset.nom;
            ouvrirPin('Valider le CACES® de ' + nom + ' ?', async function (pin) {
                return fetch('/api/caces-obtenus/valider/' + id + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
            });
        }

        const btnAnnuler = e.target.closest('[data-action="annuler-caces"]');
        if (btnAnnuler) {
            const id = btnAnnuler.dataset.id;
            const nom = btnAnnuler.dataset.nom;
            ouvrirPin('Annuler le CACES® de ' + nom + ' ?', async function (pin) {
                return fetch('/api/caces-obtenus/annuler/' + id + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
            });
        }
    });
});

let _pinCallback = null;

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
                chargerAValider();
                chargerValides();
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

function fmtDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y;
}

function badgeStatut(statut) {
    if (statut === 'valide') return '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">Validé</span>';
    if (statut === 'annule') return '<span class="badge" style="background:#fafafa;color:#999;text-decoration:line-through;">Annulé</span>';
    return '';
}

async function chargerAValider() {
    const el = document.getElementById('liste-a-valider');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement...</p>';
    try {
        const r = await fetch('/api/caces-obtenus/a-valider');
        if (!r.ok) throw new Error('Erreur ' + r.status);
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Aucun CACES® en attente de validation.</p>';
            return;
        }
        const entete = `
        <div style="display:grid;grid-template-columns:1fr 110px 120px 80px 110px 110px 80px;gap:8px;padding:7px 14px;background:#f0f2fa;border-radius:8px;margin-bottom:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#555;">
            <span>Stagiaire</span><span>Session</span><span>Famille / Cat.</span><span>Options</span><span>Obtention</span><span>Échéance</span><span>Actions</span>
        </div>`;
        const lignes = data.map(function (co) {
            return `<div style="display:grid;grid-template-columns:1fr 110px 120px 80px 110px 110px 80px;gap:8px;padding:10px 14px;border-bottom:1px solid #f0f0f0;align-items:center;">
                <span style="font-weight:600;">${co.stagiaire_nom} ${co.stagiaire_prenom}</span>
                <span style="font-size:12px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${co.session_reference}">${co.session_reference}</span>
                <span><strong style="color:#1a237e;">${co.famille}</strong> <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span></span>
                <span style="font-size:11px;color:#666;">${co.options_obtenues || '—'}</span>
                <span style="font-size:12px;">${fmtDate(co.date_obtention)}</span>
                <span style="font-size:12px;">${fmtDate(co.date_echeance)}</span>
                <span style="display:flex;gap:4px;">
                    <button class="btn btn-primary" data-action="valider-caces" data-id="${co.id}" data-nom="${co.stagiaire_nom} ${co.stagiaire_prenom}" style="padding:4px 8px;font-size:11px;" title="Valider">✅</button>
                    <button class="btn btn-danger" data-action="annuler-caces" data-id="${co.id}" data-nom="${co.stagiaire_nom} ${co.stagiaire_prenom}" style="padding:4px 8px;font-size:11px;" title="Annuler">❌</button>
                </span>
            </div>`;
        }).join('');
        el.innerHTML = entete + lignes;
    } catch (err) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}

async function chargerValides() {
    const el = document.getElementById('liste-valides');
    el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Chargement...</p>';
    try {
        const r = await fetch('/api/caces-obtenus/valides');
        if (!r.ok) throw new Error('Erreur ' + r.status);
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096;text-align:center;padding:24px;">Aucun CACES® validé.</p>';
            return;
        }
        const entete = `
        <div style="display:grid;grid-template-columns:70px 1fr 110px 120px 80px 110px 110px 80px 70px;gap:8px;padding:7px 14px;background:#f0f2fa;border-radius:8px;margin-bottom:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#555;">
            <span>N° Ordre</span><span>Stagiaire</span><span>Session</span><span>Famille / Cat.</span><span>Options</span><span>Obtention</span><span>Échéance</span><span>Statut</span><span></span>
        </div>`;
        const lignes = data.map(function (co) {
            const annule = co.statut === 'annule';
            return `<div style="display:grid;grid-template-columns:70px 1fr 110px 120px 80px 110px 110px 80px 70px;gap:8px;padding:10px 14px;border-bottom:1px solid #f0f0f0;align-items:center;${annule ? 'opacity:0.5;' : ''}">
                <span style="font-weight:700;font-family:monospace;color:#1a237e;font-size:13px;">${co.numero_ordre ? '#' + co.numero_ordre : '—'}</span>
                <span style="font-weight:600;${annule ? 'text-decoration:line-through;' : ''}">${co.stagiaire_nom} ${co.stagiaire_prenom}</span>
                <span style="font-size:12px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${co.session_reference}">${co.session_reference}</span>
                <span><strong style="color:#1a237e;">${co.famille}</strong> <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span></span>
                <span style="font-size:11px;color:#666;">${co.options_obtenues || '—'}</span>
                <span style="font-size:12px;">${fmtDate(co.date_obtention)}</span>
                <span style="font-size:12px;">${fmtDate(co.date_echeance)}</span>
                ${badgeStatut(co.statut)}
                <span>
                    ${!annule ? `<button class="btn btn-danger" data-action="annuler-caces" data-id="${co.id}" data-nom="${co.stagiaire_nom} ${co.stagiaire_prenom}" style="padding:4px 8px;font-size:11px;" title="Annuler">❌</button>` : ''}
                </span>
            </div>`;
        }).join('');
        el.innerHTML = entete + lignes;
    } catch (err) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}
