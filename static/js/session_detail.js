var STAGIAIRES_DATA = [];

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
        try { window.UTILISATEURS_TESTEURS = JSON.parse(_d.dataset.testeurs || '[]'); } catch(e) { window.UTILISATEURS_TESTEURS = []; }
    }

    window._CANDIDATS_EPREUVES = {};

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-retirer-candidat-jour');
        if (btn) retirerCandidatJour(btn.dataset.jourId, btn.dataset.stagiaireId, btn.dataset.nom, btn.dataset.type);
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="show-tab"]');
        if (btn) showTab(btn.dataset.tab, btn);
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="cloturer-session"]')) cloturerSession();
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="declencher-tirage"]');
        if (!btn) return;
        var sessionId = btn.dataset.sessionId;
        demanderConfirmation(
            '⚠️ Attention — opération irréversible.\n\nLe tirage sera figé définitivement pour cette session. Continuer ?',
            function() {
                document.getElementById('pin-message').textContent = 'Saisir le code PIN administrateur pour déclencher le tirage.';
                document.getElementById('pin-input').value = '';
                document.getElementById('pin-error').style.display = 'none';
                document.getElementById('modal-pin').style.display = 'flex';
                document.getElementById('pin-confirm-btn').onclick = async function() {
                    var pin = document.getElementById('pin-input').value;
                    var r = await fetch('/api/sessions/' + sessionId + '/declencher-tirage', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pin: pin })
                    });
                    if (r.ok) { fermerPin(); location.reload(); }
                    else {
                        var d = await r.json();
                        if (d.detail && d.detail.toLowerCase().includes('pin')) {
                            document.getElementById('pin-error').style.display = 'block';
                        } else {
                            fermerPin();
                            afficherErreur(d.detail || 'Erreur lors du déclenchement du tirage.');
                        }
                    }
                };
            }
        );
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="supprimer-jour"]');
        if (btn) supprimerJour(parseInt(btn.dataset.jourId));
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="ouvrir-ajout-candidat-jour"]');
        if (!btn) return;
        var dejaIds;
        try { dejaIds = JSON.parse(btn.dataset.candidats || '[]'); } catch(_) { dejaIds = []; }
        ouvrirAjoutCandidatJour(btn.dataset.jourId, dejaIds);
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="retirer-candidat"]');
        if (btn) retirerCandidat(parseInt(btn.dataset.scId), btn.dataset.nom);
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="editer-equipement"]');
        if (!btn) return;
        editerEquipement(
            parseInt(btn.dataset.eqId),
            parseInt(btn.dataset.numero),
            btn.dataset.designation  || '',
            btn.dataset.marque       || '',
            btn.dataset.type         || '',
            btn.dataset.serie        || '',
            btn.dataset.dateVerif    || '',
            btn.dataset.organisme    || '',
            btn.dataset.proprietaire || ''
        );
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="reouvrir-session"]')) reouvrirsession();
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="modifier-jour-pratique"]');
        if (!btn) return;
        var cats, opts, epreuves, note;
        try { cats     = JSON.parse(btn.dataset.categories || '{}'); } catch(_) { cats = {}; }
        try { opts     = JSON.parse(btn.dataset.options    || '{}'); } catch(_) { opts = {}; }
        try { epreuves = JSON.parse(btn.dataset.epreuves   || '{}'); } catch(_) { epreuves = {}; }
        try { note     = JSON.parse(btn.dataset.note);               } catch(_) { note = null; }
        ouvrirModifierJourPratique(parseInt(btn.dataset.jourId), btn.dataset.date, cats, opts, epreuves, note);
    });
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action="gerer-testeurs"]');
        if (btn) gererTesteurs(btn.dataset.jourId, btn.dataset.jourType);
    });
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-action="editer-candidat"]');
        if (btn) editerCandidat(parseInt(btn.dataset.scId), parseInt(btn.dataset.stagId), btn.dataset.dispense === 'true', btn.dataset.note);
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="ouvrir-ajout-jour-theorie"]')) ouvrirAjoutJourTheorie();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="ouvrir-ajout-jour-pratique"]')) ouvrirAjoutJourPratique();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="ouvrir-ajout-candidat"]')) ouvrirAjoutCandidat();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="ouvrir-ajout-equipement"]')) ouvrirAjoutEquipement();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-jour-theorie"]')) sauvegarderJourTheorie();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-jour-theorie"]')) fermerModalJourTheorie();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-jour-pratique"]')) sauvegarderJourPratique();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-jour-pratique"]')) fermerModalJourPratique();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-candidat-jour"]')) sauvegarderCandidatJour();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-candidat-jour"]')) fermerModalCandidatJour();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-modifier-jour-theorie"]')) sauvegarderModifierJourTheorie();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-modifier-jour-theorie"]')) document.getElementById('modal-modifier-jour-theorie').style.display = 'none';
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-pratique"]')) sauvegarderPratique();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-pratique"]')) fermerModalPratique();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="annuler-resultat-pratique"]')) annulerResultatPratique();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-candidat"]')) sauvegarderCandidat();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-candidat"]')) fermerModalCandidat();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="supprimer-equipement"]')) supprimerEquipement();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-equipement"]')) sauvegarderEquipement();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-equipement"]')) fermerModalEquipement();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="sauvegarder-affectations-test"]')) sauvegarderAffectationsTest();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-modal-testeurs"]')) document.getElementById('modal-testeurs').style.display = 'none';
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-pin"]')) fermerPin();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-confirm"]')) fermerConfirm();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-alerte"]')) fermerAlerte();
    });
    const scTheorie = document.getElementById('sc-theorie');
    if (scTheorie) scTheorie.addEventListener('change', _syncDispenseNote);
    document.addEventListener('change', function(e) {
        const cb = e.target;
        if (!cb.matches('[name^="jp-cat-"]')) return;
        const stagiaireId = parseInt(cb.name.replace('jp-cat-', ''));
        const cat = cb.value;
        if (!cb.checked) {
            const catsAvecResultat = (window._CANDIDATS_EPREUVES[stagiaireId] || window._CANDIDATS_EPREUVES[String(stagiaireId)] || []);
            if (catsAvecResultat.includes(cat)) {
                cb.checked = true;
                alert('Supprimez d\'abord le résultat de la catégorie ' + cat + ' avant de la retirer');
            }
        }
        // Sync included options to follow their category
        document.querySelectorAll('[name="jp-opt-' + stagiaireId + '-' + cat + '"][data-incluse="1"]').forEach(function(ob) {
            ob.checked = cb.checked;
            ob.disabled = true;
        });
    });

    // ── Sélecteur stagiaire : init données ──
    var _stagEl = document.getElementById('stagiaires-data');
    if (_stagEl) try { STAGIAIRES_DATA = JSON.parse(_stagEl.dataset.stagiaires || '[]'); } catch(_) {}

    // ── Sélecteur stagiaire : input → recherche (debounce 150 ms) ──
    var _stagTimer = null;
    document.addEventListener('input', function(e) {
        if (e.target.id !== 'sc-stagiaire-search') return;
        document.getElementById('sc-stagiaire').value = '';
        clearTimeout(_stagTimer);
        var texte = e.target.value.trim();
        if (!texte) { var l = document.getElementById('sc-stagiaire-liste'); if (l) l.style.display = 'none'; return; }
        _stagTimer = setTimeout(function() { _afficherResultatsCandidats(rechercherCandidats(texte)); }, 150);
    });

    // ── Sélecteur stagiaire : clic item + clic hors dropdown ──
    document.addEventListener('click', function(e) {
        var item = e.target.closest('.stag-result-item');
        if (item) { _selectionnerCandidatStagiaire(item.dataset.id, item.dataset.label); return; }
        var wrap = document.getElementById('sc-stagiaire-wrap');
        var liste = document.getElementById('sc-stagiaire-liste');
        if (liste && liste.style.display !== 'none' && wrap && !wrap.contains(e.target)) liste.style.display = 'none';
    });
});

// ── Source des résultats candidats — remplacer le CORPS de cette fonction
//    pour passer en mode serveur (fetch /api/stagiaires?q=) sans rien changer d'autre ──
function rechercherCandidats(texte) {
    if (!texte || texte.length < 2) return [];
    var q = texte.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return STAGIAIRES_DATA.filter(function(s) {
        var t = ((s.nom || '') + ' ' + (s.prenom || '')).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        return t.includes(q);
    }).slice(0, 30);
}

function _afficherResultatsCandidats(resultats) {
    var liste = document.getElementById('sc-stagiaire-liste');
    if (!liste) return;
    if (!resultats.length) { liste.style.display = 'none'; return; }
    var html = resultats.map(function(s) {
        var label = (s.nom || '') + ' ' + (s.prenom || '');
        return '<div class="stag-result-item" data-id="' + s.id
            + '" data-label="' + label.replace(/&/g, '&amp;').replace(/"/g, '&quot;') + '"'
            + ' style="padding:9px 14px; cursor:pointer; font-size:14px; border-bottom:1px solid #f0f2f7;">'
            + label + '</div>';
    }).join('');
    if (resultats.length === 30) {
        html += '<div style="padding:7px 14px; font-size:12px; color:#888; font-style:italic; background:#fafafa;">Affinez votre recherche…</div>';
    }
    liste.innerHTML = html;
    liste.style.display = 'block';
}

function _selectionnerCandidatStagiaire(id, label) {
    document.getElementById('sc-stagiaire').value = id;
    var inp = document.getElementById('sc-stagiaire-search');
    if (inp) inp.value = label;
    var liste = document.getElementById('sc-stagiaire-liste');
    if (liste) liste.style.display = 'none';
}

function _resetStagiaireSearch() {
    document.getElementById('sc-stagiaire').value = '';
    var inp = document.getElementById('sc-stagiaire-search');
    if (inp) { inp.value = ''; inp.disabled = false; }
    var liste = document.getElementById('sc-stagiaire-liste');
    if (liste) liste.style.display = 'none';
}

function showTab(name, btn) {
    ['sequencage','candidats','testeurs','equipements'].forEach(t => {
        document.getElementById('tab-' + t).style.display = 'none';
    });
    document.getElementById('tab-' + name).style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active-tab'));
    btn.classList.add('active-tab');
}

function _syncIncludesForStag(stagiaireId) {
    document.querySelectorAll('[name="jp-cat-' + stagiaireId + '"]').forEach(function(catCb) {
        document.querySelectorAll('[name="jp-opt-' + stagiaireId + '-' + catCb.value + '"][data-incluse="1"]').forEach(function(ob) {
            ob.checked = catCb.checked;
            ob.disabled = true;
        });
    });
}

function toggleCandidatPratique(stagiaireId) {
    const checked = document.getElementById('jp-cand-' + stagiaireId).checked;
    const cats = document.getElementById('cats-' + stagiaireId);
    cats.style.opacity = checked ? '1' : '0.3';
    cats.querySelectorAll('input').forEach(cb => cb.disabled = !checked);
    _syncIncludesForStag(stagiaireId);
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

async function toggleIdentite(jourId, stagiaireId, btn) {
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats/' + stagiaireId + '/identite', { method: 'PUT' });
    if (resp.ok) { const data = await resp.json(); btn.textContent = data.identite_verifiee ? '✅' : '⬜'; }
}

function ouvrirAjoutJourTheorie() {
    document.getElementById('jt-date').value = '';
    document.querySelectorAll('[name="jt-candidat"]').forEach(cb => { cb.checked = !cb.dataset.already; });
    var jtNote = document.getElementById('jt-note'); if (jtNote) jtNote.value = '';
    document.getElementById('modal-jour-theorie').style.display = 'flex';
}

function fermerModalJourTheorie() { document.getElementById('modal-jour-theorie').style.display = 'none'; }

async function sauvegarderJourTheorie() {
    const date = document.getElementById('jt-date').value;
    if (!date) { alert('La date est obligatoire !'); return; }
    if (window.DATE_DEBUT_SESSION && date < window.DATE_DEBUT_SESSION) { alert('⚠️ Date antérieure au début de la session !'); return; }
    if (window.DATE_FIN_SESSION && date > window.DATE_FIN_SESSION) { alert('⚠️ Date postérieure à la fin de la session !'); return; }
    const candidats = [];
    document.querySelectorAll('[name="jt-candidat"]:checked').forEach(cb => candidats.push(parseInt(cb.value)));
    if (candidats.length === 0) { alert('Selectionnez au moins un candidat !'); return; }
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: window.SESSION_ID, date, type: 'theorie', candidats, note: (document.getElementById('jt-note') || {value: ''}).value.trim() || null })
    });
    if (resp.ok) { fermerModalJourTheorie(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

function ouvrirAjoutJourPratique() {
    document.getElementById('jp-titre').textContent = 'Planifier jour de test pratique';
    document.getElementById('jp-jour-id').value = '';
    document.getElementById('jp-date').value = '';
    document.querySelectorAll('[name="jp-candidat"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('[name^="jp-cat-"], [name^="jp-opt-"]').forEach(cb => { cb.checked = false; cb.disabled = true; });
    document.querySelectorAll('[id^="cats-"]').forEach(div => div.style.opacity = '0.3');
    var jpNote = document.getElementById('jp-note'); if (jpNote) jpNote.value = '';
    document.getElementById('modal-jour-pratique').style.display = 'flex';
    calculerRecapUT();
}

function ouvrirModifierJourPratique(jourId, date, candidatsCategories, candidatsOptions, candidatsEpreuves, note) {
    window._CANDIDATS_EPREUVES = candidatsEpreuves || {};
    document.getElementById('jp-titre').textContent = 'Modifier jour de test pratique';
    document.getElementById('jp-jour-id').value = jourId;
    document.getElementById('jp-date').value = date;
    var jpNote = document.getElementById('jp-note'); if (jpNote) jpNote.value = note || '';
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
            _syncIncludesForStag(stagiaireId);
        });
    }
    document.getElementById('modal-jour-pratique').style.display = 'flex';
    calculerRecapUT();
}

function fermerModalJourPratique() { document.getElementById('modal-jour-pratique').style.display = 'none'; }

async function sauvegarderJourPratique() {
    const date = document.getElementById('jp-date').value;
    const jourId = document.getElementById('jp-jour-id').value;
    const noteEl = document.getElementById('jp-note');
    const noteVal = noteEl ? noteEl.value.trim() || null : null;
    if (!date) { alert('La date est obligatoire !'); return; }
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
            body: JSON.stringify({ date, note: noteVal })
        });
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidats_pratique })
        });
        if (resp.ok) { fermerModalJourPratique(); location.reload(); } else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
    } else {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: window.SESSION_ID, date, type: 'pratique', candidats_pratique, note: noteVal })
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

function ouvrirAjoutCandidatJour(jourId, dejaIds) {
    document.getElementById('acj-jour-id').value = jourId;
    document.querySelectorAll('[name="acj-candidat"]').forEach(function(cb) {
        var already = dejaIds && dejaIds.includes(parseInt(cb.value));
        cb.checked = false;
        cb.disabled = already;
        var label = cb.closest('label');
        if (label) {
            label.style.opacity = already ? '0.45' : '1';
            label.style.cursor = already ? 'not-allowed' : 'pointer';
            var tag = label.querySelector('.acj-deja-tag');
            if (tag) tag.style.display = already ? '' : 'none';
        }
    });
    document.getElementById('modal-candidat-jour').style.display = 'flex';
}

function fermerModalCandidatJour() { document.getElementById('modal-candidat-jour').style.display = 'none'; }

async function sauvegarderCandidatJour() {
    const jourId = document.getElementById('acj-jour-id').value;
    const candidats = [];
    document.querySelectorAll('[name="acj-candidat"]:checked:not(:disabled)').forEach(cb => candidats.push(parseInt(cb.value)));
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

function _syncDispenseNote() {
    const isDispense = document.getElementById('sc-theorie').value === 'dispense';
    const field = document.getElementById('field-dispense-note');
    field.style.display = isDispense ? 'block' : 'none';
    if (!isDispense) document.getElementById('sc-dispense-note').value = '';
}

function ouvrirAjoutCandidat() {
    document.getElementById('candidat-title').textContent = 'Ajouter un candidat';
    document.getElementById('sc-id').value = '';
    _resetStagiaireSearch();
    document.getElementById('sc-theorie').value = 'normal';
    document.getElementById('sc-dispense-note').value = '';
    document.getElementById('field-dispense-note').style.display = 'none';
    document.getElementById('field-stagiaire').style.display = 'block';
    document.getElementById('modal-candidat').style.display = 'flex';
}

function editerCandidat(id, stagiaireId, theorie_dispensee, dispenseNote) {
    document.getElementById('candidat-title').textContent = 'Modifier candidat';
    document.getElementById('sc-id').value = id;
    document.getElementById('sc-stagiaire').value = stagiaireId;
    document.getElementById('sc-theorie').value = theorie_dispensee ? 'dispense' : 'normal';
    document.getElementById('sc-dispense-note').value = dispenseNote || '';
    document.getElementById('field-dispense-note').style.display = theorie_dispensee ? 'block' : 'none';
    document.getElementById('field-stagiaire').style.display = 'none';
    document.getElementById('modal-candidat').style.display = 'flex';
}

function fermerModalCandidat() { document.getElementById('modal-candidat').style.display = 'none'; }

async function sauvegarderCandidat() {
    const id = document.getElementById('sc-id').value;
    const isDispense = document.getElementById('sc-theorie').value === 'dispense';
    const data = {
        session_id: window.SESSION_ID,
        stagiaire_id: parseInt(document.getElementById('sc-stagiaire').value),
        theorie_dispensee: isDispense,
        dispense_note: isDispense ? (document.getElementById('sc-dispense-note').value.trim() || null) : null
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
    var btnSupp = document.getElementById('btn-supprimer-equipement');
    if (btnSupp) btnSupp.style.display = 'none';
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
    var btnSupp = document.getElementById('btn-supprimer-equipement');
    if (btnSupp) btnSupp.style.display = 'inline-block';
    document.getElementById('modal-equipement').style.display = 'flex';
}

async function supprimerEquipement() {
    const id = document.getElementById('equip-id').value;
    if (!id) return;
    demanderConfirmation('Supprimer définitivement cet équipement ? Cette action est irréversible.', async () => {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/equipements/' + id, { method: 'DELETE' });
        if (resp.ok) { fermerModalEquipement(); location.reload(); }
        else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
    });
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
    document.getElementById('pin-message').textContent = 'Rouvrir la session ?';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/reouvrir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin })
        });
        if (resp.ok) { fermerPin(); location.reload(); }
        else { document.getElementById('pin-error').style.display = 'block'; }
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

function afficherSuccesToast(msg) {
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;top:20px;right:24px;background:#2e7d32;color:white;padding:12px 20px;border-radius:8px;font-size:14px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.25);transition:opacity .4s;';
    document.body.appendChild(t);
    setTimeout(function() {
        t.style.opacity = '0';
        setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 400);
    }, 1600);
}

function formatH(v) {
    if (!v) return '—';
    var r = Math.round(v * 100) / 100;
    return Number.isInteger(r) ? r + 'h' : r.toFixed(2).replace(/\.?0+$/, '') + 'h';
}

function recalculerTotalLigne(tr) {
    var total = 0;
    tr.querySelectorAll('.planning-input').forEach(function(inp) {
        total += parseFloat(inp.value) || 0;
    });
    var cell = tr.querySelector('.planning-total-cell');
    if (!cell) return;
    cell.textContent = formatH(total) === '—' ? '0h' : formatH(total);
    cell.style.color = total > 7 ? '#c62828' : '#333';
    cell.style.fontWeight = total > 7 ? 'bold' : '600';
}

function recalculerTotauxColonnes(table) {
    if (!table) return;
    var tfoot = table.querySelector('tfoot');
    if (!tfoot) return;

    var maxTheorie = 0;
    table.querySelectorAll('tbody .h-theorie').forEach(function(i) { maxTheorie = Math.max(maxTheorie, parseFloat(i.value) || 0); });
    var tc = tfoot.querySelector('.tcol-theorie');
    if (tc) tc.textContent = formatH(maxTheorie);

    var catTotals = {};
    table.querySelectorAll('tbody .h-cat').forEach(function(i) {
        var c = i.dataset.cat;
        catTotals[c] = (catTotals[c] || 0) + (parseFloat(i.value) || 0);
    });
    tfoot.querySelectorAll('.tcol-cat').forEach(function(td) {
        td.textContent = formatH(catTotals[td.dataset.cat] || 0);
    });

    var totalLibre = 0;
    table.querySelectorAll('tbody .h-libre').forEach(function(i) { totalLibre += parseFloat(i.value) || 0; });
    var tl = tfoot.querySelector('.tcol-libre');
    if (tl) tl.textContent = formatH(totalLibre);

    var catSum = 0;
    Object.keys(catTotals).forEach(function(k) { catSum += catTotals[k]; });
    var grandTotal = maxTheorie + catSum + totalLibre;
    var tg = tfoot.querySelector('.tcol-grand');
    if (tg) tg.textContent = formatH(grandTotal);
}

function ouvrirModifierJourTheorie(jourId, date) {
    document.getElementById('mjt-jour-id').value = jourId;
    document.getElementById('mjt-date').value = date;
    document.getElementById('modal-modifier-jour-theorie').style.display = 'flex';
}

async function sauvegarderModifierJourTheorie() {
    const jourId = document.getElementById('mjt-jour-id').value;
    const date = document.getElementById('mjt-date').value;
    if (!date) { alert('La date est obligatoire !'); return; }
    if (window.DATE_DEBUT_SESSION && date < window.DATE_DEBUT_SESSION) { alert('⚠️ Date antérieure au début de la session !'); return; }
    if (window.DATE_FIN_SESSION && date > window.DATE_FIN_SESSION) { alert('⚠️ Date postérieure à la fin de la session !'); return; }
    const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/modifier', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date })
    });
    if (resp.ok) { document.getElementById('modal-modifier-jour-theorie').style.display = 'none'; location.reload(); }
    else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
}

function retirerCandidatJour(jourId, stagiaireId, nom, typeJour) {
    demanderConfirmation('Retirer ' + nom + ' de ce jour ?', async () => {
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/candidats/' + stagiaireId, { method: 'DELETE' });
        if (resp.ok) location.reload();
        else { const d = await resp.json(); afficherErreur(d.detail || 'Erreur !'); }
    });
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

// ── AFFECTATION TESTEURS ──────────────────────────────────────────────────────

function gererTesteurs(jourId, jourType) {
    document.getElementById('at-jour-id').value = jourId;
    document.getElementById('at-jour-type').value = jourType;
    var liste = document.getElementById('at-liste');
    liste.innerHTML = '<p style="color:#888; font-size:13px;">Chargement…</p>';
    document.getElementById('modal-testeurs').style.display = 'flex';
    fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/affectations-test')
        .then(function(r) { return r.json(); })
        .then(function(ats) {
            var byUser = {};
            ats.forEach(function(at) { byUser[at.user_id] = at; });
            var utList = window.UTILISATEURS_TESTEURS || [];
            if (utList.length === 0) {
                liste.innerHTML = '<p style="color:#888; font-size:13px;">Aucun testeur disponible. Liez un compte utilisateur à une fiche testeur.</p>';
                return;
            }
            var html = '';
            utList.forEach(function(ut) {
                var at = byUser[ut.user_id] || {};
                var checked = at.user_id !== undefined ? 'checked' : '';
                var principal = at.principal ? 'checked' : '';
                var habsLabel = (ut.habs && ut.habs.length > 0) ? ' <span style="color:#666; font-size:12px;">(' + ut.habs.join(', ') + ')</span>' : '';
                html +=
                    '<label style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:#f5f5f5; border-radius:8px; cursor:pointer;">' +
                    '<input type="checkbox" name="at-user" value="' + ut.user_id + '" ' + checked + ' onchange="_atToggle(this)">' +
                    '<span style="flex:1;">' + (ut.prenom ? ut.prenom + ' ' : '') + ut.nom + habsLabel + '</span>' +
                    '<span style="display:flex; align-items:center; gap:4px; font-size:12px; color:#555;">' +
                    '<input type="radio" name="at-principal" value="' + ut.user_id + '" ' + principal + '> ★ Principal' +
                    '</span>' +
                    '</label>';
            });
            liste.innerHTML = html;
        })
        .catch(function() {
            liste.innerHTML = '<p style="color:#c62828; font-size:13px;">Erreur lors du chargement.</p>';
        });
}

function _atToggle(checkbox) {
    if (!checkbox.checked) {
        document.querySelectorAll('[name="at-principal"]').forEach(function(r) {
            if (r.value === checkbox.value) r.checked = false;
        });
    }
}

async function sauvegarderAffectationsTest() {
    var jourId = document.getElementById('at-jour-id').value;
    var data = [];
    document.querySelectorAll('[name="at-user"]:checked').forEach(function(cb) {
        var userId = parseInt(cb.value);
        var principalEl = document.querySelector('[name="at-principal"][value="' + userId + '"]');
        data.push({ user_id: userId, principal: principalEl ? principalEl.checked : false });
    });
    var resp = await fetch('/api/sessions/' + window.SESSION_ID + '/jours/' + jourId + '/affectations-test', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (resp.ok) {
        document.getElementById('modal-testeurs').style.display = 'none';
        location.reload();
    } else {
        var d = await resp.json();
        afficherErreur(d.detail || 'Erreur lors de l\'enregistrement.');
    }
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
            var jfNote = document.getElementById('jf-note'); if (jfNote) jfNote.value = '';
            document.querySelectorAll('#jf-candidats .jf-candidat-cb').forEach(function(cb) { cb.checked = false; });
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
            var stagIds = [];
            document.querySelectorAll('#jf-candidats .jf-candidat-cb:checked').forEach(function(cb) { stagIds.push(parseInt(cb.value)); });
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: date, intitule: intitule || null, note: (document.getElementById('jf-note') || {value: ''}).value.trim() || null, stagiaire_ids: stagIds })
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
            demanderConfirmation('Supprimer définitivement ce jour de formation ? Cette action est irréversible.', function() {
                fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + btnSupp.dataset.id,
                      { method: 'DELETE' })
                    .then(function(r) { if (r.ok) location.reload(); else r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de la suppression.'); }); });
            });
        }

        var btnEdit = e.target.closest('[data-action="modifier-jour-formation"]');
        if (btnEdit) {
            document.getElementById('jf-edit-id').value = btnEdit.dataset.id;
            document.getElementById('jf-edit-date').value = btnEdit.dataset.date;
            document.getElementById('jf-edit-intitule').value = btnEdit.dataset.intitule || '';
            var jfEditNote = document.getElementById('jf-edit-note'); if (jfEditNote) jfEditNote.value = btnEdit.dataset.note || '';
            var candidats; try { candidats = JSON.parse(btnEdit.dataset.candidats); } catch(_) { candidats = null; }
            var avecHeures; try { avecHeures = JSON.parse(btnEdit.dataset.avecHeures || '[]'); } catch(_) { avecHeures = []; }
            document.querySelectorAll('#jf-edit-candidats .jf-edit-candidat-cb').forEach(function(cb) {
                cb.checked = candidats === null || candidats.includes(parseInt(cb.value));
                var lbl = cb.closest('label');
                if (avecHeures.includes(parseInt(cb.value))) {
                    cb.disabled = true;
                    if (lbl) { lbl.title = 'Remettez d\'abord ses heures à zéro pour pouvoir le retirer'; lbl.style.opacity = '0.55'; }
                } else {
                    cb.disabled = false;
                    if (lbl) { lbl.title = ''; lbl.style.opacity = '1'; }
                }
            });
            document.getElementById('modal-modifier-jour-formation').style.display = 'flex';
            return;
        }
        if (e.target.closest('[data-action="fermer-modal-modifier-jour-formation"]')) {
            document.getElementById('modal-modifier-jour-formation').style.display = 'none';
            return;
        }
        if (e.target.closest('[data-action="sauvegarder-modifier-jour-formation"]')) {
            var id = document.getElementById('jf-edit-id').value;
            var date = document.getElementById('jf-edit-date').value;
            var intitule = document.getElementById('jf-edit-intitule').value.trim();
            if (!date) { alert('La date est obligatoire.'); return; }
            var editStagIds = [];
            document.querySelectorAll('#jf-edit-candidats .jf-edit-candidat-cb:checked').forEach(function(cb) { editStagIds.push(parseInt(cb.value)); });
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + id, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date_str: date, intitule: intitule || null, note: (document.getElementById('jf-edit-note') || {value: ''}).value.trim() || null, stagiaire_ids: editStagIds })
            }).then(function(r) {
                if (r.ok) {
                    document.getElementById('modal-modifier-jour-formation').style.display = 'none';
                    afficherSuccesToast('Jour modifié ✓');
                    setTimeout(function() { location.reload(); }, 800);
                } else {
                    r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de la modification.'); });
                }
            });
            return;
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

        var btnVoirNote = e.target.closest('[data-action="voir-note-jour"]');
        if (btnVoirNote) {
            document.getElementById('modal-note-jour-texte').textContent = btnVoirNote.dataset.note || '';
            document.getElementById('modal-note-jour').style.display = 'flex';
        }
        if (e.target.closest('[data-action="fermer-modal-note-jour"]')) {
            document.getElementById('modal-note-jour').style.display = 'none';
        }

        // ── Note privée ──────────────────────────────────────────────────────
        var btnNotePrivee = e.target.closest('[data-action="ouvrir-note-privee"]');
        if (btnNotePrivee) {
            window._MNP_JOUR_ID   = btnNotePrivee.dataset.jourId;
            window._MNP_JOUR_TYPE = btnNotePrivee.dataset.jourType;
            var peutModifier     = btnNotePrivee.dataset.peutModifier === '1';
            var sessModifiable   = btnNotePrivee.dataset.sessionModifiable === '1';
            var note             = btnNotePrivee.dataset.note || '';
            var zLecture  = document.getElementById('mnp-zone-lecture');
            var zEdition  = document.getElementById('mnp-zone-edition');
            var zPin      = document.getElementById('mnp-zone-pin');
            var btnSave   = document.getElementById('mnp-btn-save');
            var btnDel    = document.getElementById('mnp-btn-delete');
            var ta        = document.getElementById('mnp-textarea');
            document.getElementById('mnp-pin').value = '';
            document.getElementById('mnp-pin-error').style.display = 'none';
            ta.readOnly = false;
            if (peutModifier) {
                // Principal : mode édition, pas de PIN
                zEdition.style.display = 'block'; zLecture.style.display = 'none'; zPin.style.display = 'none';
                ta.value = note;
                if (sessModifiable) {
                    btnSave.style.display = ''; btnDel.style.display = note ? '' : 'none';
                } else {
                    ta.readOnly = true; btnSave.style.display = 'none'; btnDel.style.display = 'none';
                }
            } else {
                // Admin : édition + PIN requis pour enregistrer ou supprimer
                zEdition.style.display = 'block'; zLecture.style.display = 'none';
                ta.value = note;
                if (sessModifiable) {
                    btnSave.style.display = ''; btnDel.style.display = note ? '' : 'none';
                    zPin.style.display = 'block';
                } else {
                    btnSave.style.display = 'none'; btnDel.style.display = 'none';
                    zPin.style.display = 'none';
                }
            }
            document.getElementById('modal-note-privee').style.display = 'flex';
        }

        if (e.target.closest('[data-action="fermer-note-privee"]')) {
            document.getElementById('modal-note-privee').style.display = 'none';
        }

        if (e.target.closest('[data-action="sauvegarder-note-privee"]')) {
            var noteVal = document.getElementById('mnp-textarea').value;
            var pinVal  = document.getElementById('mnp-pin').value.trim();
            var errEl   = document.getElementById('mnp-pin-error');
            errEl.style.display = 'none';
            var jType   = window._MNP_JOUR_TYPE;
            var jId     = window._MNP_JOUR_ID;
            var url     = jType === 'formation'
                ? '/api/sessions/' + window.SESSION_ID + '/jours-formation/' + jId + '/note-privee'
                : '/api/sessions/' + window.SESSION_ID + '/jours/' + jId + '/note-privee';
            fetch(url, { method: 'PUT', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ note: noteVal, pin: pinVal || null }) })
            .then(function(r) {
                if (r.ok) { document.getElementById('modal-note-privee').style.display = 'none'; location.reload(); }
                else r.json().then(function(d) {
                    if (d.detail && d.detail.toLowerCase().includes('pin')) { errEl.style.display = 'block'; }
                    else { afficherErreur(d.detail || 'Erreur'); }
                });
            });
        }

        if (e.target.closest('[data-action="supprimer-note-privee"]')) {
            var pin2   = document.getElementById('mnp-pin').value.trim();
            var errEl2 = document.getElementById('mnp-pin-error');
            errEl2.style.display = 'none';
            var jType2 = window._MNP_JOUR_TYPE;
            var jId2   = window._MNP_JOUR_ID;
            var url2   = jType2 === 'formation'
                ? '/api/sessions/' + window.SESSION_ID + '/jours-formation/' + jId2 + '/note-privee'
                : '/api/sessions/' + window.SESSION_ID + '/jours/' + jId2 + '/note-privee';
            demanderConfirmation('Supprimer définitivement cette note confidentielle ?', function() {
                fetch(url2, { method: 'DELETE', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ pin: pin2 || null }) })
                .then(function(r) {
                    if (r.ok) { document.getElementById('modal-note-privee').style.display = 'none'; location.reload(); }
                    else r.json().then(function(d) {
                        if (d.detail && d.detail.toLowerCase().includes('pin')) { errEl2.style.display = 'block'; }
                        else { afficherErreur(d.detail || 'Erreur'); }
                    });
                });
            });
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

    // Calcul total par ligne + totaux colonnes en temps réel
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('planning-input')) {
            var tr = e.target.closest('tr[data-stagiaire]');
            if (tr) {
                recalculerTotalLigne(tr);
                recalculerTotauxColonnes(tr.closest('table'));
            }
        }
    });

    // Initialiser les totaux au chargement
    document.querySelectorAll('tr[data-stagiaire]').forEach(function(tr) {
        recalculerTotalLigne(tr);
    });
    document.querySelectorAll('table[id^="planning-"]').forEach(function(table) {
        recalculerTotauxColonnes(table);
    });

    // Helpers : ajouter / retirer une colonne planning dans le DOM
    function _colHasHours(table, val) {
        var sel = val === '__theorie__' ? '.h-theorie' : val === '__libre__' ? '.h-libre' : '.h-cat[data-cat="' + val + '"]';
        return Array.prototype.some.call(table.querySelectorAll('tbody ' + sel), function(i) {
            return (parseFloat(i.value) || 0) > 0;
        });
    }
    function _addPlanningCol(table, val) {
        var tfootRow = table.querySelector('tfoot tr');
        if (val === '__theorie__') {
            var th = document.createElement('th');
            th.className = 'col-theorie';
            th.textContent = 'TH';
            th.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600;';
            var appTh = table.querySelector('thead tr th.col-apprenant');
            if (appTh) appTh.parentNode.insertBefore(th, appTh.nextSibling);
            table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
                var td = document.createElement('td'); td.style.cssText = 'padding:4px 6px; text-align:center;'; td.dataset.label = 'TH';
                td.innerHTML = '<input type="number" class="h-theorie planning-input" min="0" max="7" step="0.25" value="0" style="width:58px; text-align:center; border:1px solid #ddd; border-radius:4px; padding:2px 4px;">';
                var appTd = tr.querySelector('td:first-child'); if (appTd) tr.insertBefore(td, appTd.nextSibling);
            });
            if (tfootRow) { var ftd = document.createElement('td'); ftd.className = 'tcol-theorie'; ftd.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600;'; ftd.textContent = '—'; var fApp = tfootRow.querySelector('td:first-child'); if (fApp) tfootRow.insertBefore(ftd, fApp.nextSibling); }
        } else if (val === '__libre__') {
            var th = document.createElement('th'); th.className = 'col-libre'; th.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600; background:#f0f2f7;';
            th.innerHTML = '<input type="text" class="libelle-libre" placeholder="Libre" style="width:64px; border:none; background:transparent; font-weight:600; color:#1565c0; text-align:center; font-size:13px; font-family:inherit;">';
            var spacerTh = table.querySelector('thead tr th.col-spacer'); if (spacerTh) spacerTh.parentNode.insertBefore(th, spacerTh);
            table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
                var td = document.createElement('td'); td.className = 'td-libre'; td.style.cssText = 'padding:4px 6px; text-align:center; background:#fafafa;'; td.dataset.label = 'Libre';
                td.innerHTML = '<input type="number" class="h-libre planning-input" min="0" max="7" step="0.25" value="0" style="width:58px; text-align:center; border:1px solid #ddd; border-radius:4px; padding:2px 4px;">';
                var spacerTd = tr.querySelector('td.td-spacer'); if (spacerTd) tr.insertBefore(td, spacerTd);
            });
            if (tfootRow) { var ftd = document.createElement('td'); ftd.className = 'tcol-libre'; ftd.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600; background:#e8eaf0;'; ftd.textContent = '—'; var fSpacer = tfootRow.querySelector('.tcol-spacer'); if (fSpacer) tfootRow.insertBefore(ftd, fSpacer); }
        } else {
            var th = document.createElement('th'); th.dataset.cat = val; th.textContent = val; th.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600;';
            var anchorTh = table.querySelector('thead tr th.col-libre') || table.querySelector('thead tr th.col-spacer'); if (anchorTh) anchorTh.parentNode.insertBefore(th, anchorTh);
            table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
                var td = document.createElement('td'); td.style.cssText = 'padding:4px 6px; text-align:center;'; td.dataset.label = val;
                td.innerHTML = '<input type="number" class="h-cat planning-input" data-cat="' + val + '" min="0" max="7" step="0.25" value="0" style="width:58px; text-align:center; border:1px solid #ddd; border-radius:4px; padding:2px 4px;">';
                var anchorTd = tr.querySelector('td.td-libre') || tr.querySelector('td.td-spacer'); if (anchorTd) tr.insertBefore(td, anchorTd);
            });
            if (tfootRow) { var ftd = document.createElement('td'); ftd.className = 'tcol-cat'; ftd.dataset.cat = val; ftd.style.cssText = 'padding:6px 8px; text-align:center; font-weight:600;'; ftd.textContent = '—'; var fAnchor = tfootRow.querySelector('.tcol-libre') || tfootRow.querySelector('.tcol-spacer'); if (fAnchor) tfootRow.insertBefore(ftd, fAnchor); }
        }
    }
    function _removePlanningCol(table, val) {
        if (val === '__theorie__') {
            var el = table.querySelector('thead th.col-theorie'); if (el) el.remove();
            table.querySelectorAll('tbody .h-theorie').forEach(function(i) { i.closest('td').remove(); });
            var el2 = table.querySelector('tfoot .tcol-theorie'); if (el2) el2.remove();
        } else if (val === '__libre__') {
            var el = table.querySelector('thead th.col-libre'); if (el) el.remove();
            table.querySelectorAll('tbody .h-libre').forEach(function(i) { i.closest('td').remove(); });
            var el2 = table.querySelector('tfoot .tcol-libre'); if (el2) el2.remove();
        } else {
            var el = table.querySelector('thead th[data-cat="' + val + '"]'); if (el) el.remove();
            table.querySelectorAll('tbody .h-cat[data-cat="' + val + '"]').forEach(function(i) { i.closest('td').remove(); });
            var el2 = table.querySelector('tfoot .tcol-cat[data-cat="' + val + '"]'); if (el2) el2.remove();
        }
    }

    function _sortPlanningCols(table) {
        var theadRow = table.querySelector('thead tr');
        var tfoot = table.querySelector('tfoot tr');
        var catThs = Array.from(theadRow.querySelectorAll('th[data-cat]'));
        if (catThs.length <= 1) return;
        catThs.sort(function(a, b) { return a.dataset.cat.localeCompare(b.dataset.cat, undefined, {numeric: true}); });
        var anchorTh = theadRow.querySelector('th.col-libre') || theadRow.querySelector('th.col-spacer');
        catThs.forEach(function(th) { theadRow.insertBefore(th, anchorTh); });
        table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
            var anchorTd = tr.querySelector('td.td-libre') || tr.querySelector('td.td-spacer');
            catThs.forEach(function(th) {
                var inp = tr.querySelector('.h-cat[data-cat="' + th.dataset.cat + '"]');
                if (inp) tr.insertBefore(inp.closest('td'), anchorTd);
            });
        });
        if (tfoot) {
            var fAnchor = tfoot.querySelector('.tcol-libre') || tfoot.querySelector('.tcol-spacer');
            catThs.forEach(function(th) {
                var ftd = tfoot.querySelector('.tcol-cat[data-cat="' + th.dataset.cat + '"]');
                if (ftd) tfoot.insertBefore(ftd, fAnchor);
            });
        }
    }

    // Case "Colonne libre" → afficher/masquer le champ titre
    document.addEventListener('change', function(e) {
        if (e.target.matches('.acp-cat-cb') && e.target.value === '__libre__') {
            document.getElementById('acp-libre-titre-wrap').style.display = e.target.checked ? 'block' : 'none';
        }
    });

    // Ouvrir modal ajout/retrait colonne
    document.addEventListener('click', function(e) {
        var btnAcp = e.target.closest('[data-action="ouvrir-ajouter-cat-planning"]');
        if (btnAcp) {
            var jourId = btnAcp.dataset.jourId;
            document.getElementById('acp-jour-id').value = jourId;
            var table = document.getElementById('planning-' + jourId);
            var activeCats = new Set();
            var hasTheorieCol = false, hasLibreCol = false;
            if (table) {
                table.querySelectorAll('thead th[data-cat]').forEach(function(th) { activeCats.add(th.dataset.cat); });
                hasTheorieCol = !!table.querySelector('thead th.col-theorie');
                hasLibreCol   = !!table.querySelector('thead th.col-libre');
            }
            document.querySelectorAll('.acp-cat-cb').forEach(function(cb) {
                var val = cb.value;
                var isActive = (val === '__theorie__') ? hasTheorieCol : (val === '__libre__') ? hasLibreCol : activeCats.has(val);
                var hasHours = isActive && table && _colHasHours(table, val);
                cb.checked = isActive;
                cb.disabled = hasHours;
                cb.dataset.wasActive = isActive ? 'true' : 'false';
                var lbl = document.getElementById('acp-label-' + val);
                if (lbl) {
                    lbl.style.opacity = hasHours ? '0.5' : '1';
                    lbl.title = hasHours ? 'Contient des heures — remettez à 0 pour retirer' : '';
                }
            });
            // Pré-remplir titre colonne libre + afficher/masquer le champ
            var titrePre = hasLibreCol && table ? (table.querySelector('.libelle-libre') || {value: ''}).value : '';
            document.getElementById('acp-libre-titre').value = titrePre;
            document.getElementById('acp-libre-titre-wrap').style.display = hasLibreCol ? 'block' : 'none';
            document.getElementById('modal-ajouter-cat-planning').style.display = 'flex';
        }

        if (e.target.closest('[data-action="fermer-modal-ajouter-cat"]')) {
            document.getElementById('modal-ajouter-cat-planning').style.display = 'none';
        }

        // Confirmer : ajouter les nouvelles colonnes cochées, retirer les décochées vides
        if (e.target.closest('[data-action="confirmer-ajouter-cat-planning"]')) {
            var jourId = document.getElementById('acp-jour-id').value;
            var table = document.getElementById('planning-' + jourId);
            if (!table) { document.getElementById('modal-ajouter-cat-planning').style.display = 'none'; return; }
            document.querySelectorAll('.acp-cat-cb').forEach(function(cb) {
                if (cb.disabled) return; // a des heures → intouchable
                var val = cb.value;
                var wasActive = cb.dataset.wasActive === 'true';
                if (cb.checked && !wasActive) _addPlanningCol(table, val);
                else if (!cb.checked && wasActive) _removePlanningCol(table, val);
            });
            // Injecter le titre saisi dans l'input inline du <th> + data-label des <td>
            var titreSaisi = document.getElementById('acp-libre-titre').value.trim();
            var inlineInput = table.querySelector('.libelle-libre');
            if (inlineInput) {
                inlineInput.value = titreSaisi;
                var labelVal = titreSaisi || 'Libre';
                table.querySelectorAll('.td-libre').forEach(function(td) { td.dataset.label = labelVal; });
            }
            _sortPlanningCols(table);
            document.getElementById('modal-ajouter-cat-planning').style.display = 'none';
            document.querySelectorAll('tr[data-stagiaire]').forEach(function(tr) { recalculerTotalLigne(tr); });
            recalculerTotauxColonnes(table);
        }

        // Sauvegarder planning
        var btnSave = e.target.closest('[data-action="sauvegarder-planning"]');
        if (btnSave) {
            var jourId = btnSave.dataset.jourId;
            var table = document.getElementById('planning-' + jourId);
            if (!table) return;
            var libelleInput = table.querySelector('.libelle-libre');
            var libelleLibre = libelleInput ? libelleInput.value : '';
            var hasTheorieCol = table.querySelector('tbody tr[data-stagiaire] .h-theorie') !== null;
            var hasLibreCol = table.querySelector('tbody tr[data-stagiaire] .h-libre') !== null;
            var apprenants = [];
            table.querySelectorAll('tbody tr[data-stagiaire]').forEach(function(tr) {
                var stagId = parseInt(tr.dataset.stagiaire);
                var tInp = tr.querySelector('.h-theorie');
                var lInp = tr.querySelector('.h-libre');
                var theorie = tInp ? (parseFloat(tInp.value) || 0) : 0;
                var libre = lInp ? (parseFloat(lInp.value) || 0) : 0;
                var hpc = {};
                tr.querySelectorAll('.h-cat').forEach(function(inp) {
                    var v = parseFloat(inp.value) || 0;
                    hpc[inp.dataset.cat] = v;
                });
                apprenants.push({ stagiaire_id: stagId, heures_theorie: theorie, heures_par_cat: hpc, heures_libre: libre });
            });
            fetch('/api/sessions/' + window.SESSION_ID + '/jours-formation/' + jourId + '/planning', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ libelle_colonne_libre: libelleLibre, has_theorie_col: hasTheorieCol, has_libre_col: hasLibreCol, apprenants: apprenants }),
            }).then(function(r) {
                if (r.ok) afficherSuccesToast('Données enregistrées ✓');
                else r.json().then(function(d) { afficherErreur(d.detail || 'Erreur lors de l\'enregistrement.'); });
            });
        }
    });

    // Badge résultat pratique cliquable → modifier un résultat existant
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="modifier-epreuve-pratique"]');
        if (!btn) return;
        var optsPlanif; try { optsPlanif = JSON.parse(btn.dataset.optsPlanif || '[]'); } catch(e) { optsPlanif = []; }
        saisirResultatPratique(
            parseInt(btn.dataset.stagiaireId),
            btn.dataset.cat,
            btn.dataset.date,
            btn.dataset.testeurId,
            btn.dataset.identite === 'true',
            btn.dataset.obtenue === 'true',
            btn.dataset.noteTesteur,
            optsPlanif,
            btn.dataset.optsObtenues,
            parseInt(btn.dataset.epreuveId)
        );
    });

    // Bouton "+" nouveau résultat pratique (CSP-safe : data-action au lieu de onclick)
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="nouveau-resultat-pratique"]');
        if (!btn) return;
        var optsPlanifNew; try { optsPlanifNew = JSON.parse(btn.dataset.optsPlanif || '[]'); } catch(e) { optsPlanifNew = []; }
        saisirResultatPratique(
            parseInt(btn.dataset.stagiaireId),
            btn.dataset.cat,
            btn.dataset.date,
            '',
            btn.dataset.identite === 'true',
            null,
            '',
            optsPlanifNew,
            '',
            null
        );
    });
});