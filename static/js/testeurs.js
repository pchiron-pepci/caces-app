document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('search').addEventListener('keyup', filtrer);
    document.getElementById('btn-nouveau-testeur').addEventListener('click', ouvrirFormulaire);
    document.getElementById('btn-sauvegarder').addEventListener('click', sauvegarder);
    document.getElementById('btn-fermer-modal').addEventListener('click', fermerModal);
    document.getElementById('btn-fermer-pin').addEventListener('click', fermerPin);
    document.getElementById('btn-fermer-prevention').addEventListener('click', fermerPrevention);

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        if (btn.dataset.action === 'editer') {
            editer(btn.dataset.id, btn.dataset.nom, btn.dataset.prenom, btn.dataset.statut,
                btn.dataset.entreprise, btn.dataset.inrs, btn.dataset.email, btn.dataset.tel,
                btn.dataset.habilitation, btn.dataset.expiration, btn.dataset.visite,
                btn.dataset.formation, btn.dataset.controle, btn.dataset.note);
        }
        if (btn.dataset.action === 'archiver') {
            archiver(btn.dataset.id, btn.dataset.nom);
        }
        if (btn.dataset.action === 'supprimer-hab') {
            supprimerHab(btn.dataset.habId, btn.dataset.habLabel);
        }
        if (btn.dataset.action === 'prevention-supprimer') {
            const testeurId = btn.dataset.id;
            const nomFichier = btn.dataset.nomFichier;
            document.getElementById('pin-message').textContent = `Supprimer l'attestation "${nomFichier}" ?`;
            document.getElementById('pin-input').value = '';
            document.getElementById('pin-error').style.display = 'none';
            document.getElementById('modal-pin').style.display = 'flex';
            document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
                const pin = document.getElementById('pin-input').value;
                const resp = await fetch(`/api/upload/attestation-prevention/${testeurId}?pin=${pin}`, { method: 'DELETE' });
                if (resp.ok) { fermerPin(); location.reload(); }
                else document.getElementById('pin-error').style.display = 'block';
                this.removeEventListener('click', handler);
            });
        }
        if (btn.dataset.action === 'carte-supprimer') {
            const testeurId = btn.dataset.id;
            const nomFichier = btn.dataset.nomFichier;
            document.getElementById('pin-message').textContent = `Supprimer la carte "${nomFichier}" ?`;
            document.getElementById('pin-input').value = '';
            document.getElementById('pin-error').style.display = 'none';
            document.getElementById('modal-pin').style.display = 'flex';
            document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
                const pin = document.getElementById('pin-input').value;
                const resp = await fetch(`/api/upload/carte-testeur/${testeurId}?pin=${pin}`, { method: 'DELETE' });
                if (resp.ok) { fermerPin(); location.reload(); }
                else document.getElementById('pin-error').style.display = 'block';
                this.removeEventListener('click', handler);
            });
        }
    });
});

let idAArchiver = null;
let idHabASupprimer = null;

function ouvrirFormulaire() {
    document.getElementById('modal-title').textContent = 'Nouveau testeur';
    document.getElementById('testeur-id').value = '';
    ['nom','prenom','entreprise','email','tel','inrs','habilitation','expiration','visite','formation','controle','note'].forEach(f => {
        document.getElementById('f-' + f).value = '';
    });
    document.getElementById('f-statut').value = 'interne';
    document.getElementById('modal').style.display = 'flex';
}

function editer(id, nom, prenom, statut, entreprise, inrs, email, tel, habilitation, expiration, visite, formation, controle, note) {
    document.getElementById('modal-title').textContent = 'Modifier testeur';
    document.getElementById('testeur-id').value = id;
    document.getElementById('f-nom').value = nom;
    document.getElementById('f-prenom').value = prenom;
    document.getElementById('f-statut').value = statut;
    document.getElementById('f-entreprise').value = entreprise;
    document.getElementById('f-inrs').value = inrs;
    document.getElementById('f-email').value = email;
    document.getElementById('f-tel').value = tel;
    document.getElementById('f-habilitation').value = habilitation;
    document.getElementById('f-expiration').value = expiration;
    document.getElementById('f-visite').value = visite;
    document.getElementById('f-formation').value = formation;
    document.getElementById('f-controle').value = controle;
    document.getElementById('f-note').value = note;

    const habContainer = document.getElementById('modal-habs');
    habContainer.innerHTML = '';
    const habSource = document.getElementById('habs-' + id);
    const sectionHabs = document.getElementById('section-habs-modal');
    if (habSource && habSource.children.length > 0) {
        Array.from(habSource.children).forEach(div => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex; align-items:center; gap:8px; margin-bottom:6px;';
            const badge = document.createElement('span');
            badge.className = 'badge blue';
            badge.textContent = div.dataset.habLabel;
            const btnDel = document.createElement('button');
            btnDel.type = 'button';
            btnDel.className = 'btn btn-danger';
            btnDel.style.cssText = 'padding:4px 8px; font-size:12px;';
            btnDel.textContent = '🗑️';
            btnDel.dataset.action = 'supprimer-hab';
            btnDel.dataset.habId = div.dataset.habId;
            btnDel.dataset.habLabel = div.dataset.habLabel;
            row.appendChild(badge);
            row.appendChild(btnDel);
            habContainer.appendChild(row);
        });
        sectionHabs.style.display = 'block';
    } else {
        sectionHabs.style.display = 'none';
    }

    document.getElementById('modal').style.display = 'flex';
}

function fermerModal() { document.getElementById('modal').style.display = 'none'; }

async function sauvegarder() {
    const id = document.getElementById('testeur-id').value;
    const data = {
        nom: document.getElementById('f-nom').value.toUpperCase(),
        prenom: document.getElementById('f-prenom').value,
        statut: document.getElementById('f-statut').value,
        entreprise: document.getElementById('f-entreprise').value || null,
        email: document.getElementById('f-email').value || null,
        telephone: document.getElementById('f-tel').value || null,
        numero_inrs: document.getElementById('f-inrs').value || null,
        date_habilitation: document.getElementById('f-habilitation').value || null,
        date_expiration_habilitation: document.getElementById('f-expiration').value || null,
        visite_medicale: document.getElementById('f-visite').value || null,
        formation_continue: document.getElementById('f-formation').value || null,
        date_prochain_controle: document.getElementById('f-controle').value || null,
        note: document.getElementById('f-note').value || null
    };
    if (!data.nom || !data.prenom) { alert('Nom et prénom sont obligatoires !'); return; }
    const url = id ? `/api/testeurs/${id}` : '/api/testeurs/';
    const method = id ? 'PUT' : 'POST';
    const resp = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) { fermerModal(); location.reload(); }
    else alert('Erreur lors de la sauvegarde !');
}

function archiver(id, nom) {
    idAArchiver = id;
    document.getElementById('pin-message').textContent = `Archiver "${nom}" ?`;
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch(`/api/testeurs/${idAArchiver}?pin=${pin}`, { method: 'DELETE' });
        if (resp.ok) { fermerPin(); location.reload(); }
        else document.getElementById('pin-error').style.display = 'block';
        this.removeEventListener('click', handler);
    });
}

function supprimerHab(habId, label) {
    idHabASupprimer = habId;
    document.getElementById('pin-message').textContent = `Supprimer l'habilitation "${label}" ?`;
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch(`/admin/habilitation/${idHabASupprimer}?pin=${pin}`, { method: 'DELETE' });
        if (resp.ok) { fermerPin(); location.reload(); }
        else document.getElementById('pin-error').style.display = 'block';
        this.removeEventListener('click', handler);
    });
}

function fermerPin() { document.getElementById('modal-pin').style.display = 'none'; }

function ouvrirModalPrevention(testeurId, input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    document.getElementById('prevention-message').textContent = `Uploader "${file.name}" pour ce testeur ?`;
    document.getElementById('prevention-date').value = '';
    document.getElementById('prevention-pin').value = '';
    document.getElementById('prevention-error').style.display = 'none';
    document.getElementById('modal-prevention').style.display = 'flex';
    document.getElementById('prevention-confirm-btn').addEventListener('click', async function handler() {
        const dateVal = document.getElementById('prevention-date').value;
        const pin = document.getElementById('prevention-pin').value;
        if (!dateVal) {
            document.getElementById('prevention-error').style.display = 'block';
            return;
        }
        const formData = new FormData();
        formData.append('file', file);
        const resp = await fetch(`/api/upload/attestation-prevention/${testeurId}?pin=${pin}&date_attestation=${dateVal}`, {
            method: 'POST',
            body: formData
        });
        if (resp.ok) { fermerPrevention(); input.value = ''; location.reload(); }
        else document.getElementById('prevention-error').style.display = 'block';
        this.removeEventListener('click', handler);
    });
}

function fermerPrevention() { document.getElementById('modal-prevention').style.display = 'none'; }

function uploadCarte(testeurId, input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    document.getElementById('pin-message').textContent = `Uploader "${file.name}" pour ce testeur ?`;
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
        const pin = document.getElementById('pin-input').value;
        const formData = new FormData();
        formData.append('file', file);
        const resp = await fetch(`/api/upload/carte-testeur/${testeurId}?pin=${pin}`, {
            method: 'POST',
            body: formData
        });
        if (resp.ok) { fermerPin(); input.value = ''; location.reload(); }
        else document.getElementById('pin-error').style.display = 'block';
        this.removeEventListener('click', handler);
    });
}

function filtrer() {
    const q = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.testeur-card').forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}