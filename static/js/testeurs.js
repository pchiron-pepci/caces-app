document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('search').addEventListener('keyup', filtrer);
    document.getElementById('btn-nouveau-testeur').addEventListener('click', ouvrirFormulaire);
    document.getElementById('btn-sauvegarder').addEventListener('click', sauvegarder);
    document.getElementById('btn-fermer-modal').addEventListener('click', fermerModal);
    document.getElementById('btn-fermer-pin').addEventListener('click', fermerPin);
    document.getElementById('btn-fermer-prevention').addEventListener('click', fermerPrevention);
    document.getElementById('btn-fermer-controle').addEventListener('click', fermerControle);
    document.getElementById('btn-fermer-ajouter-carte').addEventListener('click', function() {
        document.getElementById('modal-ajouter-carte').style.display = 'none';
    });
    document.getElementById('btn-modal-ajouter-carte').addEventListener('click', function() {
        carteAjouterTesteurId = document.getElementById('testeur-id').value;
        document.getElementById('ajouter-carte-famille').value = 'R482';
        document.getElementById('ajouter-carte-file').value = '';
        document.getElementById('ajouter-carte-pin').value = '';
        document.getElementById('ajouter-carte-error').style.display = 'none';
        document.getElementById('modal-ajouter-carte').style.display = 'flex';
    });

    document.getElementById('btn-upload-prevention').addEventListener('click', function() {
        document.getElementById('modal-prev-file').click();
    });
    document.getElementById('modal-prev-file').addEventListener('change', function() {
        const testeurId = document.getElementById('testeur-id').value;
        ouvrirModalPrevention(testeurId, this);
    });

    document.getElementById('btn-suppr-prev').addEventListener('click', function() {
        const testeurId = document.getElementById('testeur-id').value;
        const nomFichier = document.getElementById('modal-prev-info').textContent;
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
    });

    document.getElementById('ajouter-carte-confirm').addEventListener('click', async function() {
        const famille = document.getElementById('ajouter-carte-famille').value;
        const pin = document.getElementById('ajouter-carte-pin').value;
        const fileInput = document.getElementById('ajouter-carte-file');
        const errEl = document.getElementById('ajouter-carte-error');
        if (!fileInput.files || fileInput.files.length === 0) {
            errEl.textContent = '❌ Sélectionnez un fichier PDF.';
            errEl.style.display = 'block';
            return;
        }
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        const resp = await fetch(
            `/api/upload/cartes-testeur/${carteAjouterTesteurId}?pin=${encodeURIComponent(pin)}&famille=${famille}`,
            { method: 'POST', body: formData }
        );
        if (resp.ok) {
            document.getElementById('modal-ajouter-carte').style.display = 'none';
            location.reload();
        } else {
            errEl.textContent = '❌ PIN incorrect ou fichier invalide.';
            errEl.style.display = 'block';
        }
    });

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        if (btn.dataset.action === 'editer') {
            editer(btn.dataset.id, btn.dataset.nom, btn.dataset.prenom, btn.dataset.statut,
                btn.dataset.entreprise, btn.dataset.inrs, btn.dataset.email, btn.dataset.tel,
                btn.dataset.habilitation, btn.dataset.expiration, btn.dataset.visite,
                btn.dataset.formation, btn.dataset.controle, btn.dataset.note,
                btn.dataset.hasPrev, btn.dataset.prevNom);
        }
        if (btn.dataset.action === 'archiver') {
            archiver(btn.dataset.id, btn.dataset.nom);
        }
        if (btn.dataset.action === 'supprimer-hab') {
            supprimerHab(btn.dataset.habId, btn.dataset.habLabel);
        }
        if (btn.dataset.action === 'carte-ajouter') {
            carteAjouterTesteurId = btn.dataset.id;
            document.getElementById('ajouter-carte-famille').value = 'R482';
            document.getElementById('ajouter-carte-file').value = '';
            document.getElementById('ajouter-carte-pin').value = '';
            document.getElementById('ajouter-carte-error').style.display = 'none';
            document.getElementById('modal-ajouter-carte').style.display = 'flex';
        }
        if (btn.dataset.action === 'carte-modal-supprimer') {
            const carteId = btn.dataset.carteId;
            document.getElementById('pin-message').textContent = 'Supprimer définitivement cette carte CACES® ?';
            document.getElementById('pin-input').value = '';
            document.getElementById('pin-error').style.display = 'none';
            document.getElementById('modal-pin').style.display = 'flex';
            document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
                const pin = document.getElementById('pin-input').value;
                const resp = await fetch(`/api/upload/carte/${carteId}?pin=${pin}`, { method: 'DELETE' });
                if (resp.ok) { fermerPin(); location.reload(); }
                else document.getElementById('pin-error').style.display = 'block';
                this.removeEventListener('click', handler);
            });
        }
        if (btn.dataset.action === 'controle-editer') {
            const testeurId = btn.dataset.id;
            document.getElementById('controle-date-input').value = btn.dataset.controle;
            document.getElementById('modal-controle').style.display = 'flex';
            document.getElementById('controle-confirm-btn').onclick = async function() {
                const dateVal = document.getElementById('controle-date-input').value || null;
                const editBtn = document.querySelector(`[data-action="editer"][data-id="${testeurId}"]`);
                const d = editBtn ? editBtn.dataset : {};
                const resp = await fetch(`/api/testeurs/${testeurId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        nom: d.nom || '',
                        prenom: d.prenom || '',
                        statut: d.statut || 'interne',
                        entreprise: d.entreprise || null,
                        email: d.email || null,
                        telephone: d.tel || null,
                        numero_inrs: d.inrs || null,
                        date_habilitation: d.habilitation || null,
                        date_expiration_habilitation: d.expiration || null,
                        visite_medicale: d.visite || null,
                        formation_continue: d.formation || null,
                        date_prochain_controle: dateVal,
                        note: d.note || null
                    })
                });
                if (resp.ok) { fermerControle(); location.reload(); }
            };
        }
    });
});

let idAArchiver = null;
let idHabASupprimer = null;
let carteAjouterTesteurId = null;

function ouvrirFormulaire() {
    document.getElementById('modal-title').textContent = 'Nouveau testeur';
    document.getElementById('testeur-id').value = '';
    ['nom','prenom','entreprise','email','tel','inrs','note','habilitation','expiration','visite','formation','controle'].forEach(f => {
        document.getElementById('f-' + f).value = '';
    });
    document.getElementById('f-statut').value = 'interne';
    document.getElementById('section-documents').style.display = 'none';
    document.getElementById('modal-prev-file').value = '';
    document.getElementById('modal').style.display = 'flex';
}

function editer(id, nom, prenom, statut, entreprise, inrs, email, tel, habilitation, expiration, visite, formation, controle, note, hasPrev, prevNom) {
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

    document.getElementById('section-documents').style.display = 'block';
    document.getElementById('modal-prev-file').value = '';

    if (hasPrev === 'true') {
        document.getElementById('modal-prev-info').textContent = prevNom || 'attestation.pdf';
        document.getElementById('btn-suppr-prev').style.display = '';
    } else {
        document.getElementById('modal-prev-info').textContent = 'Aucune attestation';
        document.getElementById('btn-suppr-prev').style.display = 'none';
    }

    const cartesList = document.getElementById('modal-cartes-list');
    cartesList.innerHTML = '';
    const cartesContainer = document.getElementById('cartes-' + id);
    const cartesDivs = cartesContainer ? cartesContainer.querySelectorAll('[data-carte-id]') : [];
    if (cartesDivs.length === 0) {
        cartesList.innerHTML = '<span style="font-size:12px;color:#888;">Aucune carte</span>';
    } else {
        cartesDivs.forEach(function(c) {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex; align-items:center; gap:8px;';
            row.innerHTML =
                '<span style="font-size:12px;color:#2e7d32;">' + c.dataset.famille + ' : ' + c.dataset.nom + '</span>' +
                '<a href="/api/upload/carte/' + c.dataset.carteId + '/download" class="btn btn-secondary" style="padding:3px 8px;font-size:11px;" target="_blank">📥</a>' +
                '<button class="btn btn-danger" style="padding:3px 8px;font-size:11px;"' +
                ' data-action="carte-modal-supprimer" data-carte-id="' + c.dataset.carteId + '">🗑️</button>';
            cartesList.appendChild(row);
        });
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

function fermerControle() { document.getElementById('modal-controle').style.display = 'none'; }

function filtrer() {
    const q = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.testeur-card').forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}
