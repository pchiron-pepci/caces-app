document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('search').addEventListener('keyup', filtrer);
    const _chkInactifs = document.getElementById('chk-inactifs');
    if (_chkInactifs) _chkInactifs.addEventListener('change', filtrer);
    filtrer();
    document.getElementById('btn-changer-etat').addEventListener('click', changerEtatTesteur);
    document.getElementById('btn-nouveau-testeur').addEventListener('click', ouvrirFormulaire);
    document.getElementById('btn-sauvegarder').addEventListener('click', sauvegarder);
    document.getElementById('btn-fermer-modal').addEventListener('click', fermerModal);
    document.getElementById('btn-fermer-pin').addEventListener('click', fermerPin);
    document.getElementById('btn-fermer-prevention').addEventListener('click', fermerPrevention);
    document.getElementById('btn-fermer-controle').addEventListener('click', fermerControle);
    document.getElementById('btn-fermer-ajouter-carte').addEventListener('click', function() {
        document.getElementById('modal-ajouter-carte').style.display = 'none';
    });

    // --- Attestation prévention ---
    document.getElementById('btn-upload-prevention').addEventListener('click', function() {
        document.getElementById('modal-prev-file').click();
    });
    document.getElementById('modal-prev-file').addEventListener('change', function() {
        ouvrirModalPrevention(document.getElementById('testeur-id').value, this);
    });
    document.getElementById('btn-suppr-prev').addEventListener('click', function() {
        const testeurId = document.getElementById('testeur-id').value;
        const nom = document.getElementById('modal-prev-info').textContent;
        ouvrirPinAction(`Supprimer l'attestation "${nom}" ?`, async function(pin) {
            return fetch(`/api/upload/attestation-prevention/${testeurId}?pin=${pin}`, { method: 'DELETE' });
        });
    });

    // --- Visite médicale ---
    document.getElementById('btn-upload-visite').addEventListener('click', function() {
        const dateVal = document.getElementById('modal-visite-date').value;
        if (!dateVal) { alert('Veuillez saisir une date de visite.'); return; }
        document.getElementById('modal-visite-file').click();
    });
    document.getElementById('modal-visite-file').addEventListener('change', function() {
        if (!this.files || this.files.length === 0) return;
        const file = this.files[0];
        const testeurId = document.getElementById('testeur-id').value;
        const dateVal = document.getElementById('modal-visite-date').value;
        ouvrirPinAction(`Uploader "${file.name}" comme visite médicale ?`, async function(pin) {
            const fd = new FormData();
            fd.append('file', file);
            return fetch(`/api/upload/visite-medicale/${testeurId}?pin=${encodeURIComponent(pin)}&date_visite=${dateVal}`, { method: 'POST', body: fd });
        });
    });
    document.getElementById('btn-suppr-visite').addEventListener('click', function() {
        const testeurId = document.getElementById('testeur-id').value;
        const nom = document.getElementById('modal-visite-info').textContent;
        ouvrirPinAction(`Supprimer "${nom}" ?`, async function(pin) {
            return fetch(`/api/upload/visite-medicale/${testeurId}?pin=${pin}`, { method: 'DELETE' });
        });
    });

    // --- Évaluation ---
    document.getElementById('btn-upload-eval').addEventListener('click', function() {
        const dateVal = document.getElementById('modal-eval-date').value;
        if (!dateVal) { alert('Veuillez saisir une date d\'évaluation.'); return; }
        document.getElementById('modal-eval-file').click();
    });
    document.getElementById('modal-eval-file').addEventListener('change', function() {
        if (!this.files || this.files.length === 0) return;
        const file = this.files[0];
        const testeurId = document.getElementById('testeur-id').value;
        const dateVal = document.getElementById('modal-eval-date').value;
        ouvrirPinAction(`Uploader "${file.name}" comme évaluation ?`, async function(pin) {
            const fd = new FormData();
            fd.append('file', file);
            return fetch(`/api/upload/evaluation/${testeurId}?pin=${encodeURIComponent(pin)}&date_evaluation=${dateVal}`, { method: 'POST', body: fd });
        });
    });
    document.getElementById('btn-suppr-eval').addEventListener('click', function() {
        const testeurId = document.getElementById('testeur-id').value;
        const nom = document.getElementById('modal-eval-info').textContent;
        ouvrirPinAction(`Supprimer "${nom}" ?`, async function(pin) {
            return fetch(`/api/upload/evaluation/${testeurId}?pin=${pin}`, { method: 'DELETE' });
        });
    });

    // --- Autorisation de conduite ---
    document.getElementById('btn-upload-autorisation').addEventListener('click', function() {
        document.getElementById('modal-autorisation-file').click();
    });
    document.getElementById('modal-autorisation-file').addEventListener('change', function() {
        if (!this.files || this.files.length === 0) return;
        const file = this.files[0];
        const testeurId = document.getElementById('testeur-id').value;
        ouvrirPinAction(`Uploader "${file.name}" comme autorisation de conduite ?`, async function(pin) {
            const fd = new FormData();
            fd.append('file', file);
            return fetch(`/api/upload/autorisation-conduite/${testeurId}?pin=${encodeURIComponent(pin)}`, { method: 'POST', body: fd });
        });
    });
    document.getElementById('btn-suppr-autorisation').addEventListener('click', function() {
        const testeurId = document.getElementById('testeur-id').value;
        const nom = document.getElementById('modal-autorisation-info').textContent;
        ouvrirPinAction(`Supprimer "${nom}" ?`, async function(pin) {
            return fetch(`/api/upload/autorisation-conduite/${testeurId}?pin=${pin}`, { method: 'DELETE' });
        });
    });

    // --- Cartes CACES® ---
    document.getElementById('btn-modal-ajouter-carte').addEventListener('click', function() {
        carteAjouterTesteurId = document.getElementById('testeur-id').value;
        document.getElementById('ajouter-carte-famille').value = 'R482';
        document.getElementById('ajouter-carte-file').value = '';
        document.getElementById('ajouter-carte-pin').value = '';
        document.getElementById('ajouter-carte-error').style.display = 'none';
        document.getElementById('modal-ajouter-carte').style.display = 'flex';
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
        const fd = new FormData();
        fd.append('file', fileInput.files[0]);
        const resp = await fetch(
            `/api/upload/cartes-testeur/${carteAjouterTesteurId}?pin=${encodeURIComponent(pin)}&famille=${famille}`,
            { method: 'POST', body: fd }
        );
        if (resp.ok) {
            document.getElementById('modal-ajouter-carte').style.display = 'none';
            location.reload();
        } else {
            errEl.textContent = '❌ PIN incorrect ou fichier invalide.';
            errEl.style.display = 'block';
        }
    });

    // --- Délégation globale ---
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        if (btn.dataset.action === 'editer') {
            editer(btn.dataset.id, btn.dataset.nom, btn.dataset.prenom, btn.dataset.statut,
                btn.dataset.entreprise, btn.dataset.inrs, btn.dataset.email, btn.dataset.tel,
                btn.dataset.habilitation, btn.dataset.expiration, btn.dataset.visite,
                btn.dataset.formation, btn.dataset.controle, btn.dataset.note,
                btn.dataset.hasPrev, btn.dataset.prevNom,
                btn.dataset.hasVisite, btn.dataset.visiteNom,
                btn.dataset.hasEval, btn.dataset.evalNom, btn.dataset.evalDate,
                btn.dataset.visiteDate,
                btn.dataset.hasAutorisation, btn.dataset.autorisationNom,
                btn.dataset.etat, btn.dataset.utilisateurId);
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
            ouvrirPinAction('Supprimer définitivement cette carte CACES® ?', async function(pin) {
                return fetch(`/api/upload/carte/${carteId}?pin=${pin}`, { method: 'DELETE' });
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
                        nom: d.nom || '', prenom: d.prenom || '',
                        statut: d.statut || 'interne', entreprise: d.entreprise || null,
                        email: d.email || null, telephone: d.tel || null,
                        numero_inrs: d.inrs || null, date_habilitation: d.habilitation || null,
                        date_expiration_habilitation: d.expiration || null,
                        visite_medicale: d.visite || null, formation_continue: d.formation || null,
                        date_prochain_controle: dateVal, note: d.note || null,
                        utilisateur_id: d.utilisateurId ? parseInt(d.utilisateurId) : null
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

function ouvrirPinAction(message, actionFn) {
    document.getElementById('pin-message').textContent = message;
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').addEventListener('click', async function handler() {
        const pin = document.getElementById('pin-input').value;
        const resp = await actionFn(pin);
        if (resp.ok) { fermerPin(); location.reload(); }
        else document.getElementById('pin-error').style.display = 'block';
        this.removeEventListener('click', handler);
    });
}

function ouvrirFormulaire() {
    document.getElementById('modal-title').textContent = 'Nouveau testeur';
    document.getElementById('testeur-id').value = '';
    ['nom','prenom','entreprise','email','tel','inrs','note','habilitation','expiration','visite','formation','controle'].forEach(f => {
        document.getElementById('f-' + f).value = '';
    });
    document.getElementById('f-statut').value = 'interne';
    document.getElementById('f-utilisateur-id').value = '';
    document.getElementById('section-habs-modal').style.display = 'none';
    document.getElementById('section-documents').style.display = 'none';
    document.getElementById('modal-prev-file').value = '';
    document.getElementById('modal').style.display = 'flex';
}

function editer(id, nom, prenom, statut, entreprise, inrs, email, tel, habilitation, expiration, visite, formation, controle, note, hasPrev, prevNom, hasVisite, visiteNom, hasEval, evalNom, evalDate, visiteDate, hasAutorisation, autorisationNom, etat, utilisateurId) {
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
    document.getElementById('f-etat').value = etat || 'actif';
    document.getElementById('f-utilisateur-id').value = utilisateurId || '';

    document.getElementById('section-documents').style.display = 'block';
    document.getElementById('modal-prev-file').value = '';

    // Attestation prévention
    if (hasPrev === 'true') {
        document.getElementById('modal-prev-info').textContent = prevNom || 'attestation.pdf';
        document.getElementById('btn-suppr-prev').style.display = '';
    } else {
        document.getElementById('modal-prev-info').textContent = 'Aucune attestation';
        document.getElementById('btn-suppr-prev').style.display = 'none';
    }

    // Visite médicale
    document.getElementById('modal-visite-date').value = visiteDate || '';
    if (hasVisite === 'true') {
        document.getElementById('modal-visite-info').textContent = visiteNom || 'visite.pdf';
        document.getElementById('modal-visite-dl').href = `/api/upload/visite-medicale/${id}/download`;
        document.getElementById('modal-visite-dl').style.display = '';
        document.getElementById('btn-suppr-visite').style.display = '';
    } else {
        document.getElementById('modal-visite-info').textContent = 'Aucune visite';
        document.getElementById('modal-visite-dl').style.display = 'none';
        document.getElementById('btn-suppr-visite').style.display = 'none';
    }

    // Évaluation
    document.getElementById('modal-eval-date').value = evalDate || '';
    if (hasEval === 'true') {
        document.getElementById('modal-eval-info').textContent = evalNom || 'evaluation.pdf';
        document.getElementById('modal-eval-dl').href = `/api/upload/evaluation/${id}/download`;
        document.getElementById('modal-eval-dl').style.display = '';
        document.getElementById('btn-suppr-eval').style.display = '';
    } else {
        document.getElementById('modal-eval-info').textContent = 'Aucune évaluation';
        document.getElementById('modal-eval-dl').style.display = 'none';
        document.getElementById('btn-suppr-eval').style.display = 'none';
    }

    // Autorisation de conduite
    if (hasAutorisation === 'true') {
        document.getElementById('modal-autorisation-info').textContent = autorisationNom || 'autorisation.pdf';
        document.getElementById('modal-autorisation-dl').href = `/api/upload/autorisation-conduite/${id}/download`;
        document.getElementById('modal-autorisation-dl').style.display = '';
        document.getElementById('btn-suppr-autorisation').style.display = '';
    } else {
        document.getElementById('modal-autorisation-info').textContent = 'Aucune autorisation';
        document.getElementById('modal-autorisation-dl').style.display = 'none';
        document.getElementById('btn-suppr-autorisation').style.display = 'none';
    }

    // Habilitations CACES®
    document.getElementById('section-habs-modal').style.display = 'block';
    const habsList = document.getElementById('habs-modal-list');
    habsList.innerHTML = '';
    const habsContainer = document.getElementById('habs-' + id);
    const habsDivs = habsContainer ? habsContainer.querySelectorAll('[data-hab-id]') : [];
    if (habsDivs.length === 0) {
        habsList.innerHTML = '<span style="font-size:12px;color:#888;">Aucune habilitation</span>';
    } else {
        habsDivs.forEach(function(h) {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex; align-items:center; gap:8px; margin-bottom:4px;';
            row.innerHTML =
                '<span class="badge blue" style="font-size:12px;">' + h.dataset.habLabel + '</span>' +
                '<button class="btn btn-danger" style="padding:3px 8px;font-size:11px;"' +
                ' data-action="supprimer-hab" data-hab-id="' + h.dataset.habId + '" data-hab-label="' + h.dataset.habLabel + '">🗑️</button>';
            habsList.appendChild(row);
        });
    }

    // Cartes CACES®
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
        visite_medicale_date: document.getElementById('modal-visite-date').value || null,
        evaluation_date: document.getElementById('modal-eval-date').value || null,
        formation_continue: document.getElementById('f-formation').value || null,
        date_prochain_controle: document.getElementById('f-controle').value || null,
        note: document.getElementById('f-note').value || null,
        utilisateur_id: document.getElementById('f-utilisateur-id').value ? parseInt(document.getElementById('f-utilisateur-id').value) : null
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
    ouvrirPinAction(`Archiver "${nom}" ?`, async function(pin) {
        return fetch(`/api/testeurs/${idAArchiver}?pin=${pin}`, { method: 'DELETE' });
    });
}

function supprimerHab(habId, label) {
    idHabASupprimer = habId;
    ouvrirPinAction(`Supprimer l'habilitation "${label}" ?`, async function(pin) {
        return fetch(`/admin/habilitation/${idHabASupprimer}?pin=${pin}`, { method: 'DELETE' });
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
        if (!dateVal) { document.getElementById('prevention-error').style.display = 'block'; return; }
        const fd = new FormData();
        fd.append('file', file);
        const resp = await fetch(`/api/upload/attestation-prevention/${testeurId}?pin=${pin}&date_attestation=${dateVal}`, { method: 'POST', body: fd });
        if (resp.ok) { fermerPrevention(); input.value = ''; location.reload(); }
        else document.getElementById('prevention-error').style.display = 'block';
        this.removeEventListener('click', handler);
    });
}

function fermerPrevention() { document.getElementById('modal-prevention').style.display = 'none'; }

function fermerControle() { document.getElementById('modal-controle').style.display = 'none'; }

function changerEtatTesteur() {
    const id = document.getElementById('testeur-id').value;
    const etat = document.getElementById('f-etat').value;
    const labels = { actif: '✅ Actif', suspendu: '⚠️ Suspendu', sorti: '🚪 Sorti' };
    ouvrirPinAction(`Changer l'état en "${labels[etat]}" ?`, async function(pin) {
        return fetch(`/api/testeurs/${id}/etat?pin=${encodeURIComponent(pin)}&etat=${encodeURIComponent(etat)}`, {
            method: 'PUT'
        });
    });
}

function filtrer() {
    const q = document.getElementById('search').value.toLowerCase();
    const showInactifs = !!(document.getElementById('chk-inactifs') || {}).checked;
    const lbl = document.getElementById('lbl-inactifs');
    if (lbl) {
        lbl.style.background = showInactifs ? '#e3f2fd' : '#f0f2f7';
        lbl.style.borderColor = showInactifs ? '#1565c0' : '#c8d8f0';
    }
    document.querySelectorAll('.testeur-card').forEach(card => {
        if (card.dataset.inactif && !showInactifs) {
            card.style.display = 'none';
            return;
        }
        card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}
