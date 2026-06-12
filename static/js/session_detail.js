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

    window._CANDIDATS_EPREUVES = {};

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-retirer-candidat-jour');
        if (btn) retirerCandidatJour(btn.dataset.jourId, btn.dataset.stagiaireId, btn.dataset.nom, btn.dataset.type);
    });
    document.addEventListener('focusout', function(e) {
        const inp = e.target.closest('[data-action="save-testeurs-sup"]');
        if (inp) saveTesteursSup(inp.dataset.jourId, inp.value);
    });
    document.addEventListener('change', function(e) {
        const cb = e.target;
        if (!cb.matches('[name^="jp-cat-"]') || cb.checked) return;
        const stagiaireId = parseInt(cb.name.replace('jp-cat-', ''));
        const cat = cb.value;
        const catsAvecResultat = (window._CANDIDATS_EPREUVES[stagiaireId] || window._CANDIDATS_EPREUVES[String(stagiaireId)] || []);
        if (catsAvecResultat.includes(cat)) {
            cb.checked = true;
            alert('Supprimez d\'abord le résultat de la catégorie ' + cat + ' avant de la retirer');
        }
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
        const checkedCats = new Set();
        document.querySelectorAll('[name="jp-cat-' + stagiaireId + '"]:checked').forEach(cb => {
            const ut = window.UT_PAR_CAT[cb.value] || 1.0;
            utCand += ut;
            total += ut;
            checkedCats.add(cb.value);
            document.querySelectorAll('[name="jp-opt-' + stagiaireId + '-' + cb.value + '"]:checked').forEach(optCb => {
                if (!optCb.dataset.incluse) {
                    utCand += 0.5;
                    total += 0.5;
                }
            });
        });
        // Option-seule : options cochées pour catégories NON cochées (base = 0, option = +0.5)
        document.querySelectorAll('[name^="jp-opt-' + stagiaireId + '-"]:checked').forEach(optCb => {
            const prefix = 'jp-opt-' + stagiaireId + '-';
            const cat = optCb.name.slice(prefix.length);
            if (!checkedCats.has(cat) && !optCb.dataset.incluse) {
                utCand += 0.5;
                total += 0.5;
            }
        });
        if (utCand > 0) {
            html += '<div style="display:flex; justify-content:space-between; padding:3px 0;">' +
                '<span><strong>' + nom + '</strong> : ' + Array.from(checkedCats).join(', ') + '</span>' +
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

async function saveTesteursSup(jourId, value) {
    await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/testeurs-sup', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ testeurs_sup: value || null })
    });
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
    if (resp.ok) { fermerModalJourTheorie(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
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

function ouvrirModifierJourPratique(jourId, testeurId, date, candidatsCategories, candidatsOptions, candidatsEpreuves) {
    window._CANDIDATS_EPREUVES = candidatsEpreuves || {};
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
        // Option-seule : options cochées pour catégories NON cochées
        document.querySelectorAll('[name^="jp-opt-' + stagiaireId + '-"]:checked').forEach(optCb => {
            const prefix = 'jp-opt-' + stagiaireId + '-';
            const cat = optCb.name.slice(prefix.length);
            if (!cats.includes(cat)) {
                if (!options[cat]) options[cat] = [];
                if (!options[cat].includes(optCb.value)) options[cat].push(optCb.value);
            }
        });
        if (cats.length > 0 || Object.keys(options).length > 0) candidats_pratique.push({ stagiaire_id: stagiaireId, categories: cats, options });
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
        if (resp.ok) { fermerModalJourPratique(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
    } else {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: window.SESSION_ID, date, type: 'pratique', testeur_id: parseInt(testeur_id), candidats_pratique })
        });
        if (resp.ok) { fermerModalJourPratique(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
    }
}

function supprimerJour(id) {
    demanderConfirmation('Supprimer ce jour de test ?', async () => {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + id, { method: 'DELETE' });
        if (resp.ok) location.reload(); else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
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
    if (resp.ok) { fermerModalCandidatJour(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

function saisirResultatPratique(stagiaireId, categorie, date, testeurId, identiteVerifiee, obtenue, noteTesteur, optionsPlanifiees, optionsObtenues, epreuveId) {
    document.getElementById('pratique-stagiaire-id').value = stagiaireId;
    document.getElementById('pratique-categorie').value = categorie;
    document.getElementById('pratique-epreuve-id').value = epreuveId || '';
    document.getElementById('pratique-annuler-zone').style.display = epreuveId ? 'block' : 'none';
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
        let html = '<label style="font-size:12px; font-weight:700; color:#555; display:block; margin-bottom:8px;">Options réussies</label><div style="display:flex; flex-wrap:wrap; gap:12px;">';
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

function annulerResultatPratique() {
    const epreuveId = document.getElementById('pratique-epreuve-id').value;
    if (!epreuveId) return;
    document.getElementById('pin-message').textContent = 'Supprimer définitivement ce résultat pratique ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/epreuves/' + epreuveId + '?pin=' + pin, { method: 'DELETE' });
        if (resp.ok) { fermerPin(); fermerModalPratique(); location.reload(); }
        else document.getElementById('pin-error').style.display = 'block';
    };
}

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
    if (resp.ok) { fermerModalPratique(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

function ouvrirAjoutCandidat() {
    document.getElementById('candidat-title').textContent = 'Ajouter un candidat';
    document.getElementById('sc-id').value = '';
    document.getElementById('sc-stagiaire').value = '';
    document.getElementById('sc-theorie').value = 'normal';
    document.getElementById('field-stagiaire').style.display = 'block';
    document.getElementById('modal-candidat').style.display = 'flex';
}

function editerCandidat(id, stagiaireId, theorie_dispensee) {
    document.getElementById('candidat-title').textContent = 'Modifier candidat';
    document.getElementById('sc-id').value = id;
    document.getElementById('sc-stagiaire').value = stagiaireId;
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
        theorie_dispensee: document.getElementById('sc-theorie').value === 'dispense'
    };
    if (!id && !data.stagiaire_id) { alert('Choisir un stagiaire !'); return; }
    const url = id ? '/api/sessions/' + window.SESSION_ID + '/candidats/' + id : '/api/sessions/' + window.SESSION_ID + '/candidats';
    const resp = await fetch(url, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) { fermerModalCandidat(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

function retirerCandidat(id, nom) {
    document.getElementById('pin-message').textContent = 'Supprimer ' + nom + ' de la session ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/candidats/' + id + '?pin=' + pin, { method: 'DELETE' });
        if (resp.ok) { fermerPin(); location.reload(); }
        else if (resp.status === 400) {
            const data = await resp.json();
            fermerPin();
            afficherErreur(data.detail || 'Erreur !');
        } else {
            document.getElementById('pin-error').style.display = 'block';
        }
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
    if (resp.ok) { fermerModalEquipement(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

function cloturerSession() {
    demanderConfirmation('Clôturer la session ? Les résultats seront verrouillés.', async () => {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/cloturer', { method: 'POST' });
        if (resp.ok) location.reload(); else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
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
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/reouvrir?pin=' + pin, { method: 'POST' });
        if (resp.ok) location.reload(); else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
    };
}

function fermerPin() { document.getElementById('modal-pin').style.display = 'none'; }

function demanderConfirmation(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('modal-confirm').style.display = 'flex';
    document.getElementById('confirm-ok-btn').onclick = () => { fermerConfirm(); callback(); };
}
function fermerConfirm() { document.getElementById('modal-confirm').style.display = 'none'; }

function afficherErreur(msg) {
    document.getElementById('alerte-message').textContent = msg;
    document.getElementById('modal-alerte').style.display = 'flex';
}
function fermerAlerte() { document.getElementById('modal-alerte').style.display = 'none'; }

function recalculerTotalLigne(tr) {
    var total = 0;
    tr.querySelectorAll('.planning-input').forEach(function(inp) {
        total += parseFloat(inp.value) || 0;
    });
    var cell = tr.querySelector('.planning-total-cell');
    if (!cell) return;
    var display = Number.isInteger(total) ? total + 'h' : total.toFixed(2).replace(/\.?0+$/, '') + 'h';
    cell.textContent = display;
    cell.style.color = total > 7 ? '#c62828' : '#333';
    cell.style.fontWeight = total > 7 ? 'bold' : '600';
}

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
    else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

async function retirerCandidatJour(jourId, stagiaireId, nom, typeJour) {
    if (typeJour === 'theorie') {
        const checkResp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats/' + stagiaireId + '/check-theorie');
        const checkData = await checkResp.json();
        if (checkData.has_resultat) {
            demanderConfirmation(
                'Ce candidat a déjà un résultat théorique enregistré. Êtes-vous sûr de vouloir le supprimer ?',
                () => _executerRetraitAvecPin(jourId, stagiaireId, nom)
            );
            return;
        }
    }
    _executerRetraitAvecPin(jourId, stagiaireId, nom);
}

function _executerRetraitAvecPin(jourId, stagiaireId, nom) {
    document.getElementById('pin-message').textContent = 'Retirer ' + nom + ' de ce jour ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('pin-error').textContent = 'Code PIN incorrect !';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats/' + stagiaireId + '?pin=' + encodeURIComponent(pin), { method: 'DELETE' });
        if (resp.ok) { fermerPin(); location.reload(); }
        else { const d = await resp.json(); document.getElementById('pin-error').textContent = d.detail || 'Code PIN incorrect !'; document.getElementById('pin-error').style.display = 'block'; }
    };
}

// ====== RGPD OVERLAY ======

var _rgpdStag = null;
var _rgpdVerifEnvoye = false;

function _rgpdMajChoix() {
    var sel = document.getElementById('rgpd-verificateur');
    var cb = document.getElementById('rgpd-identite-cb');
    var choix = document.getElementById('rgpd-choix');
    if (sel && cb && choix) {
        choix.style.display = (sel.value && cb.checked) ? 'block' : 'none';
    }
}

async function _envoyerVerification() {
    if (_rgpdVerifEnvoye || !_rgpdStag) return true;
    var sel = document.getElementById('rgpd-verificateur');
    var verificateur = sel ? sel.value : '';
    if (!verificateur) return false;
    try {
        var resp = await fetch(
            '/api/consentements/' + _rgpdStag.sessionId + '/' + _rgpdStag.stagiaireId + '/verification',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ verificateur_identite: verificateur })
            }
        );
        if (resp.ok) { _rgpdVerifEnvoye = true; return true; }
    } catch (e) { /* continue */ }
    return false;
}

document.addEventListener('DOMContentLoaded', function() {
    // Délégation clics RGPD
    document.addEventListener('click', function(e) {
        var btnOverlay = e.target.closest('[data-action="ouvrir-rgpd-overlay"]');
        if (btnOverlay) {
            ouvrirRGPDOverlay(
                btnOverlay.dataset.sessionId,
                btnOverlay.dataset.stagiaireId,
                btnOverlay.dataset.nom,
                btnOverlay.dataset.prenom,
                btnOverlay.dataset.ddn
            );
            return;
        }
        var btnRelire = e.target.closest('[data-action="ouvrir-rgpd-relire"]');
        if (btnRelire) {
            window.open('/consentement/' + btnRelire.dataset.sessionId + '/' + btnRelire.dataset.stagiaireId + '/relire', '_blank');
            return;
        }
        if (e.target.closest('[data-action="fermer-rgpd-overlay"]')) {
            document.getElementById('overlay-rgpd').style.display = 'none';
            return;
        }
    });

    var cbIdentite = document.getElementById('rgpd-identite-cb');
    if (cbIdentite) {
        cbIdentite.addEventListener('change', _rgpdMajChoix);
    }

    var selVerif = document.getElementById('rgpd-verificateur');
    if (selVerif) {
        selVerif.addEventListener('change', _rgpdMajChoix);
    }

    var btnQr = document.getElementById('btn-rgpd-qr');
    if (btnQr) {
        btnQr.addEventListener('click', async function() {
            var qrContainer = document.getElementById('rgpd-qr-container');
            var alreadyVisible = qrContainer.style.display !== 'none';
            // Envoyer la vérification au premier affichage du QR
            if (!alreadyVisible) {
                await _envoyerVerification();
                var url = window.location.origin + '/consentement/' + _rgpdStag.sessionId + '/' + _rgpdStag.stagiaireId;
                document.getElementById('rgpd-qr-code').innerHTML = '';
                new QRCode(document.getElementById('rgpd-qr-code'), {
                    text: url,
                    width: 200,
                    height: 200,
                    colorDark: '#cc0000',
                    colorLight: '#ffffff'
                });
            }
            qrContainer.style.display = alreadyVisible ? 'none' : 'block';
        });
    }

    var btnDirect = document.getElementById('btn-rgpd-direct');
    if (btnDirect) {
        btnDirect.addEventListener('click', async function() {
            if (!_rgpdStag) return;
            await _envoyerVerification();
            document.getElementById('overlay-rgpd').style.display = 'none';
            window.open('/consentement/' + _rgpdStag.sessionId + '/' + _rgpdStag.stagiaireId + '?direct=1', '_blank');
        });
    }
});

function ouvrirRGPDOverlay(sessionId, stagiaireId, nom, prenom, ddn) {
    _rgpdStag = { sessionId: sessionId, stagiaireId: stagiaireId };
    _rgpdVerifEnvoye = false;
    document.getElementById('rgpd-nom').textContent = nom + ' ' + prenom;
    document.getElementById('rgpd-ddn').textContent = ddn ? 'Né(e) le ' + ddn : '';
    document.getElementById('rgpd-verificateur').value = '';
    document.getElementById('rgpd-identite-cb').checked = false;
    document.getElementById('rgpd-choix').style.display = 'none';
    document.getElementById('rgpd-qr-container').style.display = 'none';
    document.getElementById('rgpd-qr-code').innerHTML = '';
    document.getElementById('overlay-rgpd').style.display = 'flex';
}

// ====== NEUTRALITÉ OVERLAY ======

var _neutraliteStag = null;
var _neutraliteVerifEnvoye = false;

function _neutraliteMajChoix() {
    var sel = document.getElementById('neutralite-verificateur');
    var cb = document.getElementById('neutralite-identite-cb');
    var choix = document.getElementById('neutralite-choix');
    if (sel && cb && choix) {
        choix.style.display = (sel.value && cb.checked) ? 'block' : 'none';
    }
}

document.getElementById('neutralite-identite-cb') && document.getElementById('neutralite-identite-cb').addEventListener('change', _neutraliteMajChoix);

async function _envoyerVerificationNeutralite() {
    if (_neutraliteVerifEnvoye || !_neutraliteStag) return true;
    var sel = document.getElementById('neutralite-verificateur');
    var verificateur = sel ? sel.value : '';
    if (!verificateur) return false;
    try {
        var resp = await fetch(
            '/api/neutralite/' + _neutraliteStag.jourId + '/' + _neutraliteStag.stagiaireId + '/verification',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ verificateur_identite: verificateur })
            }
        );
        if (resp.ok) { _neutraliteVerifEnvoye = true; return true; }
    } catch (e) { /* continue */ }
    return false;
}

document.addEventListener('DOMContentLoaded', function() {
    var cbN = document.getElementById('neutralite-identite-cb');
    if (cbN) cbN.addEventListener('change', _neutraliteMajChoix);

    var selN = document.getElementById('neutralite-verificateur');
    if (selN) selN.addEventListener('change', _neutraliteMajChoix);

    var btnNQr = document.getElementById('btn-neutralite-qr');
    if (btnNQr) {
        btnNQr.addEventListener('click', async function() {
            var qrContainer = document.getElementById('neutralite-qr-container');
            var alreadyVisible = qrContainer.style.display !== 'none';
            if (!alreadyVisible) {
                await _envoyerVerificationNeutralite();
                var url = window.location.origin + '/neutralite/' + _neutraliteStag.jourId + '/' + _neutraliteStag.stagiaireId;
                document.getElementById('neutralite-qr-code').innerHTML = '';
                new QRCode(document.getElementById('neutralite-qr-code'), {
                    text: url,
                    width: 200,
                    height: 200,
                    colorDark: '#cc0000',
                    colorLight: '#ffffff'
                });
            }
            qrContainer.style.display = alreadyVisible ? 'none' : 'block';
        });
    }

    var btnNDirect = document.getElementById('btn-neutralite-direct');
    if (btnNDirect) {
        btnNDirect.addEventListener('click', async function() {
            if (!_neutraliteStag) return;
            await _envoyerVerificationNeutralite();
            document.getElementById('overlay-neutralite').style.display = 'none';
            window.open('/neutralite/' + _neutraliteStag.jourId + '/' + _neutraliteStag.stagiaireId + '?direct=1', '_blank');
        });
    }

    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="ouvrir-neutralite-overlay"]')) {
            var btn = e.target.closest('[data-action="ouvrir-neutralite-overlay"]');
            ouvrirNeutraliteOverlay(
                btn.dataset.jourId,
                btn.dataset.stagiaireId,
                btn.dataset.nom,
                btn.dataset.prenom,
                btn.dataset.ddn,
                btn.dataset.testeur
            );
            return;
        }
        if (e.target.closest('[data-action="ouvrir-neutralite-relire"]')) {
            var btn = e.target.closest('[data-action="ouvrir-neutralite-relire"]');
            window.open('/neutralite/' + btn.dataset.jourId + '/' + btn.dataset.stagiaireId + '/relire', '_blank');
            return;
        }
        if (e.target.closest('[data-action="fermer-neutralite-overlay"]')) {
            document.getElementById('overlay-neutralite').style.display = 'none';
            return;
        }
    });
});

function ouvrirNeutraliteOverlay(jourId, stagiaireId, nom, prenom, ddn, testeur) {
    _neutraliteStag = { jourId: jourId, stagiaireId: stagiaireId };
    _neutraliteVerifEnvoye = false;
    document.getElementById('neutralite-nom').textContent = nom + ' ' + prenom;
    document.getElementById('neutralite-ddn').textContent = ddn ? 'Né(e) le ' + ddn : '';
    var sel = document.getElementById('neutralite-verificateur');
    sel.value = testeur || '';
    document.getElementById('neutralite-identite-cb').checked = false;
    document.getElementById('neutralite-choix').style.display = 'none';
    document.getElementById('neutralite-qr-container').style.display = 'none';
    document.getElementById('neutralite-qr-code').innerHTML = '';
    document.getElementById('overlay-neutralite').style.display = 'flex';
    _neutraliteMajChoix();
}

// ── Jours de formation ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="ouvrir-modal-jour-formation"]')) {
            document.getElementById('jf-date').value = '';
            document.getElementById('jf-intitule').value = '';
            document.getElementById('modal-jour-formation').style.display = 'flex';
            return;
        }
        if (e.target.closest('[data-action="fermer-modal-jour-formation"]')) {
            document.getElementById('modal-jour-formation').style.display = 'none';
            return;
        }
        if (e.target.closest('[data-action="sauvegarder-jour-formation"]')) {
            var date = document.getElementById('jf-date').value;
            var intitule = document.getElementById('jf-intitule').value.trim();
            if (!date) { alert('La date est obligatoire.'); return; }
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: date, intitule: intitule || null })
            }).then(function(r) {
                if (r.ok) {
                    document.getElementById('modal-jour-formation').style.display = 'none';
                    location.reload();
                } else {
                    r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de l\'ajout.'); });
                }
            });
            return;
        }
        var btnSupp = e.target.closest('[data-action="supprimer-jour-formation"]');
        if (btnSupp) {
            demanderConfirmation('Êtes-vous sûr de vouloir supprimer ce jour de formation ?', function() {
                fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + btnSupp.dataset.id,
                      { method: 'DELETE' })
                    .then(function(r) { if (r.ok) location.reload(); else r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de la suppression.'); }); });
            });
        }

        // ── LOT 2a : Affectation formateurs ───────────────────────────────────
        var btnAff = e.target.closest('[data-action="ouvrir-modal-affectation-formation"]');
        if (btnAff) {
            var jourId = btnAff.dataset.jourId;
            document.getElementById('af-jour-id').value = jourId;
            document.getElementById('af-jour-label').textContent = btnAff.dataset.jourLabel || '';
            // Reset complet
            document.querySelectorAll('.af-formateur-cb').forEach(function(cb) {
                cb.checked = false;
                var opts = document.getElementById('af-opts-' + cb.value);
                if (opts) { opts.style.display = 'none'; opts.querySelectorAll('input').forEach(function(i) { i.checked = false; }); }
            });
            // Pré-remplissage via GET
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + jourId + '/affectations')
                .then(function(r) { return r.json(); })
                .then(function(afs) {
                    afs.forEach(function(af) {
                        var cb = document.getElementById('af-cb-' + af.user_id);
                        if (!cb) return;
                        cb.checked = true;
                        var opts = document.getElementById('af-opts-' + af.user_id);
                        if (opts) {
                            opts.style.display = 'flex';
                            var theorieCb = opts.querySelector('.af-theorie');
                            var pratiqueCb = opts.querySelector('.af-pratique');
                            var principalR = opts.querySelector('.af-principal');
                            if (theorieCb) theorieCb.checked = af.theorie;
                            if (pratiqueCb) pratiqueCb.checked = af.pratique;
                            if (principalR && af.principal) principalR.checked = true;
                        }
                    });
                });
            document.getElementById('modal-affectation-formation').style.display = 'flex';
        }

        if (e.target.closest('[data-action="fermer-modal-affectation-formation"]')) {
            document.getElementById('modal-affectation-formation').style.display = 'none';
        }

        if (e.target.closest('[data-action="sauvegarder-affectation-formation"]')) {
            var jourIdSave = document.getElementById('af-jour-id').value;
            var affectations = [];
            document.querySelectorAll('.af-formateur-cb:checked').forEach(function(cb) {
                var userId = parseInt(cb.value);
                var opts = document.getElementById('af-opts-' + userId);
                affectations.push({
                    user_id: userId,
                    theorie: opts ? opts.querySelector('.af-theorie').checked : false,
                    pratique: opts ? opts.querySelector('.af-pratique').checked : false,
                    principal: opts ? opts.querySelector('.af-principal').checked : false,
                });
            });
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + jourIdSave + '/affectations', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(affectations),
            }).then(function(r) {
                if (r.ok) { document.getElementById('modal-affectation-formation').style.display = 'none'; location.reload(); }
                else r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de l\'enregistrement.'); });
            });
        }
    });

    // Toggle options formateur quand la case principale est cochée/décochée
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('af-formateur-cb')) {
            var opts = document.getElementById('af-opts-' + e.target.value);
            if (opts) {
                opts.style.display = e.target.checked ? 'flex' : 'none';
                if (!e.target.checked) opts.querySelectorAll('input').forEach(function(i) { i.checked = false; });
            }
        }
    });

    // ── LOT 2b : Planning apprenants ───────────────────────────────────────

    // Calcul total par ligne en temps réel
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('planning-input')) {
            var tr = e.target.closest('tr[data-stagiaire]');
            if (tr) recalculerTotalLigne(tr);
        }
    });

    // Initialiser les totaux au chargement
    document.querySelectorAll('tr[data-stagiaire]').forEach(function(tr) {
        recalculerTotalLigne(tr);
    });

    // Ouvrir modal ajout catégorie
    document.addEventListener('click', function(e) {
        var btnAcp = e.target.closest('[data-action="ouvrir-ajouter-cat-planning"]');
        if (btnAcp) {
            var jourId = btnAcp.dataset.jourId;
            document.getElementById('acp-jour-id').value = jourId;
            var table = document.getElementById('planning-' + jourId);
            var activeCats = new Set();
            if (table) {
                table.querySelectorAll('thead th[data-cat]').forEach(function(th) {
                    activeCats.add(th.dataset.cat);
                });
            }
            document.querySelectorAll('.acp-cat-cb').forEach(function(cb) {
                var active = activeCats.has(cb.value);
                cb.checked = active;
                cb.disabled = active;
                var lbl = document.getElementById('acp-label-' + cb.value);
                if (lbl) lbl.style.opacity = active ? '0.5' : '1';
            });
            document.getElementById('modal-ajouter-cat-planning').style.display = 'flex';
        }

        if (e.target.closest('[data-action="fermer-modal-ajouter-cat"]')) {
            document.getElementById('modal-ajouter-cat-planning').style.display = 'none';
        }

        // Confirmer ajout catégorie → injecter colonne dans le DOM
        if (e.target.closest('[data-action="confirmer-ajouter-cat-planning"]')) {
            var jourId = document.getElementById('acp-jour-id').value;
            var table = document.getElementById('planning-' + jourId);
            if (!table) { document.getElementById('modal-ajouter-cat-planning').style.display = 'none'; return; }
            document.querySelectorAll('.acp-cat-cb:checked:not(:disabled)').forEach(function(cb) {
                var cat = cb.value;
                // Entête
                var th = document.createElement('th');
                th.dataset.cat = cat;
                th.textContent = cat;
                th.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600;';
                var libreTh = table.querySelector('thead tr th.col-libre');
                if (libreTh) libreTh.parentNode.insertBefore(th, libreTh);
                // Cellule par ligne
                table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
                    var td = document.createElement('td');
                    td.style.cssText = 'padding:4px 6px; text-align:center;';
                    td.innerHTML = '<input type="number" class="h-cat planning-input" data-cat="' + cat + '" min="0" max="7" step="0.25" value="0" style="width:58px; text-align:center; border:1px solid #ddd; border-radius:4px; padding:2px 4px;">';
                    var libreTd = tr.querySelector('td.td-libre');
                    if (libreTd) tr.insertBefore(td, libreTd);
                });
            });
            document.getElementById('modal-ajouter-cat-planning').style.display = 'none';
            document.querySelectorAll('tr[data-stagiaire]').forEach(function(tr) { recalculerTotalLigne(tr); });
        }

        // Sauvegarder planning
        var btnSave = e.target.closest('[data-action="sauvegarder-planning"]');
        if (btnSave) {
            var jourId = btnSave.dataset.jourId;
            var table = document.getElementById('planning-' + jourId);
            if (!table) return;
            var libelleInput = table.querySelector('.libelle-libre');
            var libelleLibre = libelleInput ? libelleInput.value : '';
            var apprenants = [];
            table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
                var stagId = parseInt(tr.dataset.stagiaire);
                var theorie = parseFloat(tr.querySelector('.h-theorie').value) || 0;
                var libre = parseFloat(tr.querySelector('.h-libre').value) || 0;
                var hpc = {};
                tr.querySelectorAll('.h-cat').forEach(function(inp) {
                    var v = parseFloat(inp.value) || 0;
                    if (v > 0) hpc[inp.dataset.cat] = v;
                });
                apprenants.push({ stagiaire_id: stagId, heures_theorie: theorie, heures_par_cat: hpc, heures_libre: libre });
            });
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + jourId + '/planning', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ libelle_colonne_libre: libelleLibre, apprenants: apprenants }),
            }).then(function(r) {
                if (r.ok) location.reload();
                else r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de l\'enregistrement.'); });
            });
        }
    });
});