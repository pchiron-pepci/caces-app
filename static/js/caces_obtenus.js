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

        const btnRevision = e.target.closest('[data-action="revision-caces"]');
        if (btnRevision) {
            const id = btnRevision.dataset.id;
            const nom = btnRevision.dataset.nom;
            ouvrirPin('Remettre en révision le CACES® de ' + nom + ' ?', async function (pin) {
                return fetch('/api/caces-obtenus/remettre-en-revision/' + id + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
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
    if (statut === 'valide')  return '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">Validé</span>';
    if (statut === 'annule')  return '<span class="badge" style="background:#fafafa;color:#999;text-decoration:line-through;">Annulé</span>';
    return '';
}

function renderCarteAValider(co) {
    const nomComplet = co.stagiaire_nom + ' ' + co.stagiaire_prenom;
    const options = co.options_obtenues
        ? co.options_obtenues.split(',').map(o => `<span style="background:#e8eaf6;color:#283593;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;">${o.trim()}</span>`).join(' ')
        : '';
    const optionsPratique = co.options_pratique
        ? co.options_pratique.split(',').map(o => `<span style="background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:1px 5px;font-size:11px;">${o.trim()}</span>`).join(' ')
        : '';

    const refTheorie = co.post_cloture
        ? `${co.session_ref_theorie} <span style="background:#fff3e0;color:#e65100;border-radius:4px;padding:1px 5px;font-size:10px;">post-clôture</span>`
        : co.session_ref_theorie;

    return `
    <div style="border:1px solid #e0e0e0; border-radius:12px; padding:18px 20px; margin-bottom:12px; background:#fff; box-shadow:0 1px 4px rgba(0,0,0,0.06);">

        <!-- En-tête : stagiaire + famille/catégorie -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px;">
            <div>
                <div style="font-size:16px; font-weight:700; color:#1a237e;"><a href="/stagiaires#${co.stagiaire_id}" target="_blank" style="color:inherit;text-decoration:none;">${nomComplet}</a></div>
                <div style="margin-top:4px; display:flex; align-items:center; gap:8px;">
                    <span style="font-weight:700; color:#1a237e; font-size:13px;">${co.famille}</span>
                    <span style="background:#1a237e; color:#fff; border-radius:6px; padding:2px 10px; font-size:14px; font-weight:800;">${co.categorie}</span>
                    ${options}
                </div>
            </div>
            <div style="text-align:right; font-size:11px; color:#999;">#${co.id}</div>
        </div>

        <!-- Lignes théorie / pratique -->
        <div style="background:#f8f9ff; border-radius:8px; padding:10px 14px; margin-bottom:14px; display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; align-items:center; gap:10px; font-size:13px;">
                <span style="width:70px; color:#666; font-weight:600;">🎓 Théorie</span>
                <a href="/sessions/${co.session_id_theorie}" target="_blank" style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;" title="${co.session_ref_theorie}">${refTheorie}</a>
                <span style="color:#444; white-space:nowrap;">${fmtDate(co.date_theorie)}</span>
                <span style="color:#2e7d32; font-weight:700;">✅</span>
            </div>
            <div style="display:flex; align-items:center; gap:10px; font-size:13px;">
                <span style="width:70px; color:#666; font-weight:600;">🔧 Pratique</span>
                <a href="/sessions/${co.session_id_pratique}" target="_blank" style="color:#1a237e;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:none;" title="${co.session_ref_pratique}">${co.session_ref_pratique}</a>
                <span style="color:#444; white-space:nowrap;">${fmtDate(co.date_pratique)}</span>
                <span style="color:#2e7d32; font-weight:700;">✅</span>
                <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span>
                ${optionsPratique ? `<span style="display:flex;gap:3px;">${optionsPratique}</span>` : ''}
                ${co.testeur_nom ? `<span style="font-size:12px;color:#555;margin-left:4px;">| Testeur&nbsp;: <strong>${co.testeur_nom}</strong></span>` : ''}
            </div>
        </div>

        <!-- Dates calculées + boutons -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; gap:20px; font-size:13px;">
                <div>
                    <span style="color:#666;">Obtention</span>
                    <span style="font-weight:700; color:#1a237e; margin-left:6px;">${fmtDate(co.date_obtention)}</span>
                </div>
                <div>
                    <span style="color:#666;">Échéance</span>
                    <span style="font-weight:700; color:#388e3c; margin-left:6px;">${fmtDate(co.date_echeance)}</span>
                </div>
            </div>
            <div style="display:flex; gap:10px; align-items:center;">
                <button
                    data-action="revision-caces"
                    data-id="${co.id}"
                    data-nom="${nomComplet}"
                    style="background:#fff; border:2px solid #e65100; color:#e65100; border-radius:10px; padding:10px 16px; font-size:13px; font-weight:700; cursor:pointer;">
                    ↩ Révision
                </button>
                <button
                    data-action="valider-caces"
                    data-id="${co.id}"
                    data-nom="${nomComplet}"
                    style="background:#2e7d32; color:#fff; border:none; border-radius:10px; padding:10px 20px; font-size:13px; font-weight:700; cursor:pointer;">
                    📜 Émettre le CACES®
                </button>
            </div>
        </div>

    </div>`;
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
        el.innerHTML = data.map(renderCarteAValider).join('');
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
        <div style="display:grid;grid-template-columns:70px 1fr 110px 130px 80px 110px 110px 80px 70px;gap:8px;padding:7px 14px;background:#f0f2fa;border-radius:8px;margin-bottom:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#555;">
            <span>N° Ordre</span><span>Stagiaire</span><span>Session</span><span>Famille / Cat.</span><span>Options</span><span>Obtention</span><span>Échéance</span><span>Statut</span><span></span>
        </div>`;
        const lignes = data.map(function (co) {
            const annule = co.statut === 'annule';
            const nomComplet = co.stagiaire_nom + ' ' + co.stagiaire_prenom;
            return `<div style="display:grid;grid-template-columns:70px 1fr 110px 130px 80px 110px 110px 80px 70px;gap:8px;padding:10px 14px;border-bottom:1px solid #f0f0f0;align-items:center;${annule ? 'opacity:0.5;' : ''}">
                <span style="font-weight:700;font-family:monospace;color:#1a237e;font-size:13px;">${co.numero_ordre ? '#' + String(co.numero_ordre).padStart(4, '0') : '—'}</span>
                <span style="font-weight:600;${annule ? 'text-decoration:line-through;' : ''}">${nomComplet}</span>
                <span style="font-size:12px;color:#666;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${co.session_reference}">${co.session_reference}</span>
                <span><strong style="color:#1a237e;">${co.famille}</strong> <span style="font-size:13px;font-weight:700;background:#e8eaf6;color:#283593;padding:1px 6px;border-radius:4px;">${co.categorie}</span></span>
                <span style="font-size:11px;color:#666;">${co.options_obtenues || '—'}</span>
                <span style="font-size:12px;">${fmtDate(co.date_obtention)}</span>
                <span style="font-size:12px;">${fmtDate(co.date_echeance)}</span>
                ${badgeStatut(co.statut)}
                <span>
                    ${!annule ? `<button data-action="revision-caces" data-id="${co.id}" data-nom="${nomComplet}" style="background:#fff;border:2px solid #e65100;color:#e65100;border-radius:8px;padding:4px 10px;font-size:11px;font-weight:700;cursor:pointer;">↩</button>` : ''}
                </span>
            </div>`;
        }).join('');
        el.innerHTML = entete + lignes;
    } catch (err) {
        el.innerHTML = '<p style="color:red;text-align:center;padding:24px;">Erreur de chargement</p>';
    }
}
