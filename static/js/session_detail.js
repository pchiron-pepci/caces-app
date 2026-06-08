document.addEventListener('DOMContentLoaded', function() {
    const _d = document.getElementById('session-data');
    if (_d) {
        window.SESSION_ID = parseInt(_d.dataset.sessionId);
        window.SESSION_FAMILLE = _d.dataset.famille;
        window.DATE_DEBUT_SESSION = _d.dataset.debut;
        window.DATE_FIN_SESSION = _d.dataset.fin;
        window.NB_EQUIPEMENTS = parseInt(_d.dataset.nbEquipements);
        try { window.UT_PAR_CAT = JSON.parse(_d.dataset.utParCat); } catch(e) { console.error('UT_PAR_CAT parse error:', e, _d.dataset.utParCat); window.UT_PAR_CAT = {}; }
        try { window.OPTIONS_PAR_CAT = JSON.parse(_d.dataset.optionsParCat || '{}'); } catch(e) { console.error('OPTIONS_PAR_CAT parse error:', e, _d.dataset.optionsParCat); window.OPTIONS_PAR_CAT = {}; }
    }

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-retirer-candidat-jour');
        if (btn) retirerCandidatJour(btn.dataset.jourId, btn.dataset.stagiaireId, btn.dataset.nom);
    });
});

function showTab(name, btn) {
    ['sequencage','candidats','testeurs','equipements'].forEach(t => {
        document.getElementById('tab-' + t).style.display = 'none';
    });
    document.getElementById('tab-' + name).style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active-tab'));
    btn.classList.add('active-tab');
}

function toggleCandidatPratique(stagiaireId) {
    const checked = document.getElementById('jp-cand-' + stagiaireId).checked;
    const cats = document.getElementById('cats-' + stagiaireId);
    cats.style.opacity = checked ? '1' : '0.3';
    cats.querySelectorAll('input').forEach(cb => cb.disabled = !checked);
}

function calculerRecapUT() {
    let html = '';
    let total = 0;
    document.querySelectorAll('[id^="jp-cand-"]:checked').forEach(candCb => {
        const stagiaireId = candCb.value;
        const labelEl = candCb.closest('div') ? candCb.closest('div').querySelector('label') : null;
        const nom = labelEl ? labelEl.textContent.trim() : stagiaireId;
        let utCand = 0;
        const cats = [];
        document.querySelectorAll('[name="jp-cat-' + stagiaireId + '"]:checked').forEach(cb => {
            const ut = window.UT_PAR_CAT[cb.value] || 1.0;
            utCand += ut;
            total += ut;
            cats.push(cb.value);
        });
        if (utCand > 0) {
            html += '<div style="display:flex; justify-content:space-between; padding:3px 0;">' +
                '<span><strong>' + nom + '</strong> : ' + cats.join(', ') + '</span>' +
                '<span><strong>' + utCand.toFixed(1) + ' UT</strong></span></div>';
        }
    });
    const nbTesteurs = total > 0 ? Math.ceil(total / 6) : 0;
    const utLibres = (nbTesteurs * 6) - total;
    document.getElementById('recap-ut-detail').innerHTML = html || '<span style="color:#888;">Aucun candidat selectionne</span>';
    const couleurTotal = total > 6 ? '#e65100' : '#1a237e';
    const couleurLibres = utLibres > 0 ? '#2e7d32' : '#888';
    document.getElementById('recap-ut-total').innerHTML =
        '<div style="display:flex; gap:32px;">' +
        '<span>Total : <strong style="color:' + couleurTotal + '">' + total.toFixed(1) + ' UT</strong></span>' +
        '<span>Testeurs necessaires : <strong style="color:#1a237e;">' + nbTesteurs + '</strong></span>' +
        '<span>UT libres : <strong style="color:' + couleurLibres + '">' + utLibres.toFixed(1) + '</strong></span></div>';
}

async function toggleIdentite(jourId, stagiaireId, btn) {
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats/' + stagiaireId + '/identite', { method: 'PUT' });
    if (resp.ok) { const data = await resp.json(); btn.textContent = data.identite_verifiee ? '✅' : '⬜'; }
}

function ouvrirAjoutJourTheorie() {
    document.getElementById('jt-date').value = '';
    document.getElementById('jt-testeur').value = '';
    document.querySelectorAll('[name="jt-candidat"]').forEach(cb => cb.checked = true);
    document.getElementById('modal-jour-theorie').style.display = 'flex';
}

function fermerModalJourTheorie() { document.getElementById('modal-jour-theorie').style.display = 'none'; }

async function sauvegarderJourTheorie() {
    const date = document.getElementById('jt-date').value;
    const testeur_id = document.getElementById('jt-testeur').value;
    if (!date) { alert('La date est obligatoire !'); return; }
    if (!testeur_id) { alert('Le testeur est obligatoire !'); return; }
    if (window.DATE_DEBUT_SESSION && date < window.DATE_DEBUT_SESSION) { alert('⚠️ Date antérieure au début de la session !'); return; }
    if (window.DATE_FIN_SESSION && date > window.DATE_FIN_SESSION) { alert('⚠️ Date postérieure à la fin de la session !'); return; }
    const candidats = [];
    document.querySelectorAll('[name="jt-candidat"]:checked').forEach(cb => candidats.push(parseInt(cb.value)));
    if (candidats.length === 0) { alert('Selectionnez au moins un candidat !'); return; }
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: window.SESSION_ID, date, type: 'theorie', testeur_id: parseInt(testeur_id), candidats })
    });
    if (resp.ok) { fermerModalJourTheorie(); location.reload(); } else alert('Erreur !');
}

function ouvrirAjoutJourPratique() {
    document.getElementById('jp-titre').textContent = 'Planifier jour de test pratique';
    document.getElementById('jp-jour-id').value = '';
    document.getElementById('jp-date').value = '';
    document.getElementById('jp-testeur').value = '';
    document.querySelectorAll('[name="jp-candidat"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('[name^="jp-cat-"], [name^="jp-opt-"]').forEach(cb => { cb.checked = false; cb.disabled = true; });
    document.querySelectorAll('[id^="cats-"]').forEach(div => div.style.opacity = '0.3');
    document.getElementById('modal-jour-pratique').style.display = 'flex';
    calculerRecapUT();
}

function ouvrirModifierJourPratique(jourId, testeurId, date, candidatsCategories, candidatsOptions) {
    document.getElementById('jp-titre').textContent = 'Modifier jour de test pratique';
    document.getElementById('jp-jour-id').value = jourId;
    document.getElementById('jp-date').value = date;
    document.getElementById('jp-testeur').value = testeurId;
    document.querySelectorAll('[name="jp-candidat"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('[name^="jp-cat-"], [name^="jp-opt-"]').forEach(cb => { cb.checked = false; cb.disabled = true; });
    document.querySelectorAll('[id^="cats-"]').forEach(div => div.style.opacity = '0.3');
    if (candidatsCategories) {
        Object.keys(candidatsCategories).forEach(function(stagiaireId) {
            var candCb = document.getElementById('jp-cand-' + stagiaireId);
            if (!candCb) return;
            candCb.checked = true;
            var catsDiv = document.getElementById('cats-' + stagiaireId);
            if (catsDiv) {
                catsDiv.style.opacity = '1';
                catsDiv.querySelectorAll('input').forEach(function(cb) { cb.disabled = false; });
            }
            var plannedCats = candidatsCategories[stagiaireId] || [];
            document.querySelectorAll('[name="jp-cat-' + stagiaireId + '"]').forEach(function(cb) {
                cb.checked = plannedCats.includes(cb.value);
            });
            if (candidatsOptions && candidatsOptions[stagiaireId]) {
                var opts = candidatsOptions[stagiaireId];
                Object.keys(opts).forEach(function(cat) {
                    var plannedOpts = opts[cat] || [];
                    document.querySelectorAll('[name="jp-opt-' + stagiaireId + '-' + cat + '"]').forEach(function(ob) {
                        ob.checked = plannedOpts.includes(ob.value);
                    });
                });
            }
        });
    }
    document.getElementById('modal-jour-pratique').style.display = 'flex';
    calculerRecapUT();
}

function fermerModalJourPratique() { document.getElementById('modal-jour-pratique').style.display = 'none'; }

async function sauvegarderJourPratique() {
    const date = document.getElementById('jp-date').value;
    const testeur_id = document.getElementById('jp-testeur').value;
    const jourId = document.getElementById('jp-jour-id').value;
    if (!date) { alert('La date est obligatoire !'); return; }
    if (!testeur_id) { alert('Le testeur est obligatoire !'); return; }
    if (window.DATE_DEBUT_SESSION && date < window.DATE_DEBUT_SESSION) { alert('⚠️ Date antérieure au début de la session !'); return; }
    if (window.DATE_FIN_SESSION && date > window.DATE_FIN_SESSION) { alert('⚠️ Date postérieure à la fin de la session !'); return; }
    const candidats_pratique = [];
    document.querySelectorAll('[id^="jp-cand-"]:checked').forEach(candCb => {
        const stagiaireId = parseInt(candCb.value);
        const cats = [];
        const options = {};
        document.querySelectorAll('[name="jp-cat-' + stagiaireId + '"]:checked').forEach(cb => {
            const cat = cb.value;
            cats.push(cat);
            const optCbs = document.querySelectorAll('[name="jp-opt-' + stagiaireId + '-' + cat + '"]:checked');
            if (optCbs.length > 0) options[cat] = Array.from(optCbs).map(o => o.value);
        });
        if (cats.length > 0) candidats_pratique.push({ stagiaire_id: stagiaireId, categories: cats, options });
    });
    if (candidats_pratique.length === 0) { alert('Selectionnez au moins un candidat !'); return; }
    if (jourId) {
        await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/modifier', {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, testeur_id: parseInt(testeur_id) })
        });
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidats_pratique })
        });
        if (resp.ok) { fermerModalJourPratique(); location.reload(); } else alert('Erreur !');
    } else {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: window.SESSION_ID, date, type: 'pratique', testeur_id: parseInt(testeur_id), candidats_pratique })
        });
        if (resp.ok) { fermerModalJourPratique(); location.reload(); } else alert('Erreur !');
    }
}

function supprimerJour(id) {
    demanderConfirmation('Supprimer ce jour de test ?', async () => {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + id, { method: 'DELETE' });
        if (resp.ok) location.reload(); else alert('Erreur !');
    });
}

function ouvrirAjoutCandidatJour(jourId) {
    document.getElementById('acj-jour-id').value = jourId;
    document.querySelectorAll('[name="acj-candidat"]').forEach(cb => cb.checked = false);
    document.getElementById('modal-candidat-jour').style.display = 'flex';
}

function fermerModalCandidatJour() { document.getElementById('modal-candidat-jour').style.display = 'none'; }

async function sauvegarderCandidatJour() {
    const jourId = document.getElementById('acj-jour-id').value;
    const candidats = [];
    document.querySelectorAll('[name="acj-candidat"]:checked').forEach(cb => candidats.push(parseInt(cb.value)));
    if (candidats.length === 0) { alert('Selectionnez au moins un candidat !'); return; }
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidats })
    });
    if (resp.ok) { fermerModalCandidatJour(); location.reload(); } else alert('Erreur !');
}

function saisirResultatPratique(stagiaireId, categorie, date, testeurId, identiteVerifiee, obtenue, noteTesteur, optionsPlanifiees, optionsObtenues) {
    document.getElementById('pratique-stagiaire-id').value = stagiaireId;
    document.getElementById('pratique-categorie').value = categorie;
    document.getElementById('pratique-info').textContent = 'Categorie : ' + categorie;
    document.getElementById('pratique-testeur').value = testeurId || '';
    document.getElementById('pratique-date').value = date || '';
    document.getElementById('pratique-note').value = noteTesteur || '';
    document.querySelectorAll('[name="pratique-resultat"]').forEach(r => r.checked = false);
    if (obtenue === true || obtenue === 'true') {
        document.querySelector('[name="pratique-resultat"][value="true"]').checked = true;
    } else if (obtenue === false || obtenue === 'false') {
        document.querySelector('[name="pratique-resultat"][value="false"]').checked = true;
    }
    const container = document.getElementById('pratique-options-container');
    const planified = Array.isArray(optionsPlanifiees) ? optionsPlanifiees : [];
    const obtained = (optionsObtenues || '').split(',').filter(Boolean);
    const allOpts = window.OPTIONS_PAR_CAT[categorie] || [];
    const displayOpts = planified.length > 0
        ? allOpts.filter(o => planified.includes(o.code))
        : allOpts.filter(o => obtained.includes(o.code));
    if (displayOpts.length > 0) {
        let html = '<label style="font-size:12px; font-weight:700; color:#555; display:block; margin-bottom:8px;">Options évaluées</label><div style="display:flex; flex-wrap:wrap; gap:12px;">';
        displayOpts.forEach(function(opt) {
            const checked = obtained.includes(opt.code) ? 'checked' : '';
            html += '<label style="display:flex; align-items:center; gap:6px; font-size:14px; cursor:pointer;"><input type="checkbox" name="pratique-option" value="' + opt.code + '" ' + checked + '> ' + opt.code + ' — ' + opt.libelle + '</label>';
        });
        html += '</div>';
        container.innerHTML = html;
        container.style.display = 'block';
    } else {
        container.innerHTML = '';
        container.style.display = 'none';
    }
    document.getElementById('modal-pratique').style.display = 'flex';
}

function fermerModalPratique() { document.getElementById('modal-pratique').style.display = 'none'; }

async function sauvegarderPratique() {
    const stagiaireId = document.getElementById('pratique-stagiaire-id').value;
    const categorie = document.getElementById('pratique-categorie').value;
    const testeurId = document.getElementById('pratique-testeur').value;
    const date = document.getElementById('pratique-date').value;
    const resultatEl = document.querySelector('[name="pratique-resultat"]:checked');
    if (!testeurId) { alert('Le testeur est obligatoire !'); return; }
    if (!resultatEl) { alert('Le resultat est obligatoire !'); return; }
    const optsCbs = document.querySelectorAll('[name="pratique-option"]:checked');
    const optionsObtenues = optsCbs.length > 0 ? Array.from(optsCbs).map(cb => cb.value).join(',') : null;
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/epreuves', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: window.SESSION_ID, stagiaire_id: parseInt(stagiaireId),
            testeur_id: parseInt(testeurId), date,
            famille: window.SESSION_FAMILLE, categorie,
            obtenue: resultatEl.value === 'true',
            note_testeur: document.getElementById('pratique-note').value || null,
            options_obtenues: optionsObtenues
        })
    });
    if (resp.ok) { fermerModalPratique(); location.reload(); } else alert('Erreur !');
}

function ouvrirAjoutCandidat() {
    document.getElementById('candidat-title').textContent = 'Ajouter un candidat';
    document.getElementById('sc-id').value = '';
    document.getElementById('sc-stagiaire').value = '';
    document.getElementById('sc-rgpd').value = 'true';
    document.getElementById('sc-photo').value = 'true';
    document.getElementById('sc-theorie').value = 'normal';
    document.getElementById('field-stagiaire').style.display = 'block';
    document.getElementById('modal-candidat').style.display = 'flex';
}

function editerCandidat(id, stagiaireId, theorie_dispensee, rgpd, photo) {
    document.getElementById('candidat-title').textContent = 'Modifier candidat';
    document.getElementById('sc-id').value = id;
    document.getElementById('sc-stagiaire').value = stagiaireId;
    document.getElementById('sc-rgpd').value = rgpd ? 'true' : 'false';
    document.getElementById('sc-photo').value = photo ? 'true' : 'false';
    document.getElementById('sc-theorie').value = theorie_dispensee ? 'dispense' : 'normal';
    document.getElementById('field-stagiaire').style.display = 'none';
    document.getElementById('modal-candidat').style.display = 'flex';
}

function fermerModalCandidat() { document.getElementById('modal-candidat').style.display = 'none'; }

async function sauvegarderCandidat() {
    const id = document.getElementById('sc-id').value;
    const data = {
        session_id: window.SESSION_ID,
        stagiaire_id: parseInt(document.getElementById('sc-stagiaire').value),
        rgpd_accepte: document.getElementById('sc-rgpd').value === 'true',
        photo_accepte: document.getElementById('sc-photo').value === 'true',
        theorie_dispensee: document.getElementById('sc-theorie').value === 'dispense'
    };
    if (!id && !data.stagiaire_id) { alert('Choisir un stagiaire !'); return; }
    const url = id ? '/api/sessions/' + window.SESSION_ID + '/candidats/' + id : '/api/sessions/' + window.SESSION_ID + '/candidats';
    const resp = await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) { fermerModalCandidat(); location.reload(); } else alert('Erreur !');
}

function retirerCandidat(id, nom) {
    document.getElementById('pin-message').textContent = 'Retirer ' + nom + ' de la session ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        if (pin !== '1505') { document.getElementById('pin-error').style.display = 'block'; return; }
        fermerPin();
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/candidats/' + id, { method: 'DELETE' });
        if (resp.ok) location.reload();
    };
}

function ouvrirAjoutEquipement() {
    document.getElementById('equip-title').textContent = 'Ajouter un equipement';
    document.getElementById('equip-id').value = '';
    document.getElementById('equip-numero').value = window.NB_EQUIPEMENTS + 1;
    ['designation','marque','type','serie','organisme','proprietaire'].forEach(f => document.getElementById('equip-' + f).value = '');
    document.getElementById('equip-date-verif').value = '';
    document.getElementById('modal-equipement').style.display = 'flex';
}

function editerEquipement(id, numero, designation, marque, type, serie, dateVerif, organisme, proprietaire) {
    document.getElementById('equip-title').textContent = 'Modifier equipement';
    document.getElementById('equip-id').value = id;
    document.getElementById('equip-numero').value = numero;
    document.getElementById('equip-designation').value = designation;
    document.getElementById('equip-marque').value = marque;
    document.getElementById('equip-type').value = type;
    document.getElementById('equip-serie').value = serie;
    document.getElementById('equip-date-verif').value = dateVerif;
    document.getElementById('equip-organisme').value = organisme;
    document.getElementById('equip-proprietaire').value = proprietaire;
    document.getElementById('modal-equipement').style.display = 'flex';
}

function fermerModalEquipement() { document.getElementById('modal-equipement').style.display = 'none'; }

async function sauvegarderEquipement() {
    const id = document.getElementById('equip-id').value;
    const data = {
        session_id: window.SESSION_ID,
        numero: parseInt(document.getElementById('equip-numero').value),
        designation: document.getElementById('equip-designation').value || null,
        marque: document.getElementById('equip-marque').value || null,
        type_modele: document.getElementById('equip-type').value || null,
        numero_serie: document.getElementById('equip-serie').value || null,
        date_verification: document.getElementById('equip-date-verif').value || null,
        organisme_verification: document.getElementById('equip-organisme').value || null,
        proprietaire: document.getElementById('equip-proprietaire').value || null
    };
    const url = id ? '/api/sessions/' + window.SESSION_ID + '/equipements/' + id : '/api/sessions/' + window.SESSION_ID + '/equipements';
    const resp = await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) { fermerModalEquipement(); location.reload(); } else alert('Erreur !');
}

function cloturerSession() {
    demanderConfirmation('Clôturer la session ? Les résultats seront verrouillés.', async () => {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/cloturer', { method: 'POST' });
        if (resp.ok) location.reload(); else alert('Erreur !');
    });
}

function reouvrirsession() {
    document.getElementById('pin-message').textContent = 'Réouvrir la session ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        if (pin !== '1505') { document.getElementById('pin-error').style.display = 'block'; return; }
        fermerPin();
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/reouvrir', { method: 'POST' });
        if (resp.ok) location.reload(); else alert('Erreur !');
    };
}

function fermerPin() { document.getElementById('modal-pin').style.display = 'none'; }

function demanderConfirmation(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('modal-confirm').style.display = 'flex';
    document.getElementById('confirm-ok-btn').onclick = () => { fermerConfirm(); callback(); };
}
function fermerConfirm() { document.getElementById('modal-confirm').style.display = 'none'; }

function ouvrirModifierJourTheorie(jourId, date, testeurId) {
    document.getElementById('mjt-jour-id').value = jourId;
    document.getElementById('mjt-date').value = date;
    document.getElementById('mjt-testeur').value = testeurId || '';
    document.getElementById('modal-modifier-jour-theorie').style.display = 'flex';
}

async function sauvegarderModifierJourTheorie() {
    const jourId = document.getElementById('mjt-jour-id').value;
    const date = document.getElementById('mjt-date').value;
    const testeurId = document.getElementById('mjt-testeur').value;
    if (!date) { alert('La date est obligatoire !'); return; }
    if (window.DATE_DEBUT_SESSION && date < window.DATE_DEBUT_SESSION) { alert('⚠️ Date antérieure au début de la session !'); return; }
    if (window.DATE_FIN_SESSION && date > window.DATE_FIN_SESSION) { alert('⚠️ Date postérieure à la fin de la session !'); return; }
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/modifier', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, testeur_id: parseInt(testeurId) })
    });
    if (resp.ok) { document.getElementById('modal-modifier-jour-theorie').style.display = 'none'; location.reload(); }
    else alert('Erreur !');
}

function retirerCandidatJour(jourId, stagiaireId, nom) {
    document.getElementById('pin-message').textContent = 'Retirer ' + nom + ' de ce jour ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        if (pin !== '1505') { document.getElementById('pin-error').style.display = 'block'; return; }
        fermerPin();
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats/' + stagiaireId, { method: 'DELETE' });
        if (resp.ok) location.reload(); else alert('Erreur !');
    };
}