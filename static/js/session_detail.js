var STAGIAIRES_DATA = [];

function reduireImage(file) {
  return new Promise(function(resolve) {
    if (!file || !file.type || file.type.indexOf('image/') !== 0) { resolve(file); return; }
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function() {
      try {
        var MAX = 1600;
        var w = img.naturalWidth, h = img.naturalHeight;
        if (!w || !h) { URL.revokeObjectURL(url); resolve(file); return; }
        var scale = Math.min(1, MAX / Math.max(w, h));
        var nw = Math.round(w * scale), nh = Math.round(h * scale);
        var canvas = document.createElement('canvas');
        canvas.width = nw; canvas.height = nh;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, nw, nh);
        URL.revokeObjectURL(url);
        canvas.toBlob(function(blob) {
          if (!blob) { resolve(file); return; }
          if (blob.size >= file.size) { resolve(file); return; }
          var nomBase = (file.name || 'photo').replace(/\.[^.]+$/, '');
          var nouveau = new File([blob], nomBase + '.jpg', { type: 'image/jpeg' });
          resolve(nouveau);
        }, 'image/jpeg', 0.8);
      } catch (e) { URL.revokeObjectURL(url); resolve(file); }
    };
    img.onerror = function() { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

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
        window.TERRAIN_GELE = _d.dataset.terrainGele === 'true';
        window.SESSION_SANS_RESULTAT = _d.dataset.sansResultat === 'true';
        window.USER_ROLE = _d.dataset.userRole || '';
    }

    if (window.TERRAIN_GELE && window.USER_ROLE === 'terrain') {
        const TERRAIN_OK = new Set([
            'show-tab', 'fermer-pin', 'fermer-confirm', 'fermer-alerte',
            'fermer-modal-jour-theorie', 'fermer-modal-jour-pratique',
            'fermer-modal-candidat-jour', 'fermer-modal-modifier-jour-theorie',
            'fermer-modal-pratique', 'fermer-modal-candidat', 'fermer-modal-equipement',
            'fermer-modal-testeurs', 'fermer-neutralite-overlay'
        ]);
        var _content = document.querySelector('.content') || document;
        _content.querySelectorAll('[data-action]').forEach(function(el) {
            if (!TERRAIN_OK.has(el.dataset.action)) el.style.display = 'none';
        });
        var banner = document.createElement('div');
        banner.style.cssText = 'background:#fff3e0;border:1px solid #ef6c00;color:#bf360c;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:13px;font-weight:600;';
        banner.textContent = '🔐 Session clôturée côté terrain — modifications désactivées. Contactez le back-office pour réouvrir.';
        var mainContent = document.querySelector('.content');
        if (mainContent) mainContent.insertBefore(banner, mainContent.firstChild);
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
        var btn = e.target.closest('[data-action="pdf-sujet-theorie"]');
        if (btn) {
            var sid = btn.dataset.sessionId;
            window.open('/api/sessions/' + sid + '/theorie/pdf/sujet', '_blank');
        }
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="projection-theorie"]');
        if (btn) {
            window.open('/sessions/' + btn.dataset.sessionId + '/projection/' + btn.dataset.jourId, '_blank');
        }
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="pdf-corrige-theorie"]');
        if (btn) {
            var sid = btn.dataset.sessionId;
            window.open('/api/sessions/' + sid + '/theorie/pdf/corrige', '_blank');
        }
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="export-zip"]');
        if (!btn) return;
        var sid = btn.dataset.sessionId;
        document.getElementById('pin-message').textContent = 'Saisir le code PIN administrateur pour télécharger le dossier ZIP.';
        document.getElementById('pin-input').value = '';
        document.getElementById('pin-error').style.display = 'none';
        document.getElementById('modal-pin').style.display = 'flex';
        document.getElementById('pin-confirm-btn').onclick = async function() {
            var pin = document.getElementById('pin-input').value;
            fermerPin();
            afficherSuccesToast('Téléchargement en cours…');
            try {
                var resp = await fetch(
                    '/sessions/' + sid + '/export-zip?pin=' + encodeURIComponent(pin),
                    { credentials: 'same-origin' }
                );
                if (resp.ok) {
                    var filename = 'export-session.zip';
                    var cd = resp.headers.get('Content-Disposition');
                    if (cd) {
                        var m = cd.match(/filename[^;=\n]*=([^;\n]*)/);
                        if (m && m[1]) filename = m[1].trim().replace(/['"]/g, '');
                    }
                    var blob = await resp.blob();
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(function() { URL.revokeObjectURL(url); }, 100);
                } else {
                    var errData = await resp.json().catch(function() { return {}; });
                    afficherErreur(errData.detail || 'Erreur ' + resp.status + ' lors du téléchargement ZIP.');
                }
            } catch (err) {
                console.error('[export-zip]', err);
                afficherErreur('Erreur réseau lors du téléchargement ZIP.');
            }
        };
    });
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="declencher-tirage"]');
        if (!btn) return;
        var sessionId = btn.dataset.sessionId;
        demanderConfirmation(
            '⚠️ Attention.\n\nLe tirage sera figé définitivement pour cette session. Continuer ?',
            function() {
                document.getElementById('pin-message').textContent = 'Saisir le code PIN administrateur pour déclencher le tirage.';
                document.getElementById('pin-input').value = '';
                document.getElementById('pin-error').style.display = 'none';
                document.getElementById('modal-pin').style.display = 'flex';
                document.getElementById('pin-confirm-btn').onclick = async function() {
                    var pin = document.getElementById('pin-input').value;
                    var r = await fetch('/api/sessions/' + sessionId + '/declencher-tirage?pin=' + encodeURIComponent(pin), {
                        method: 'POST'
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
        var btn = e.target.closest('[data-action="choix-doc-candidat"]');
        if (!btn) return;
        window._choixDocStagId = btn.getAttribute('data-stag-id');
        document.getElementById('modal-choix-doc').style.display = 'flex';
    });
    document.addEventListener('click', function(e) {
        if (!e.target.closest('[data-action="fermer-choix-doc"]')) return;
        document.getElementById('modal-choix-doc').style.display = 'none';
    });
    document.addEventListener('click', function(e) {
        if (!e.target.closest('[data-action="choix-doc-bilan"]')) return;
        var stagId = window._choixDocStagId;
        document.getElementById('modal-choix-doc').style.display = 'none';
        if (!stagId) { afficherErreur('Candidat introuvable'); return; }
        window.open('/api/sessions/' + SESSION_ID + '/attestation-reussite/' + stagId, '_blank');
    });
    document.addEventListener('click', function(e) {
        if (!e.target.closest('[data-action="choix-doc-reco"]')) return;
        var stagId = window._choixDocStagId;
        document.getElementById('modal-choix-doc').style.display = 'none';
        if (!stagId) { afficherErreur('Candidat introuvable'); return; }
        window._frStagiaireId = stagId;
        ouvrirFicheReco();
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
        if (e.target.closest('[data-action="cloturer-terrain"]')) cloturerTerrain();
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="rouvrir-terrain"]')) rouvrirTerrain();
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
        if (btn) editerCandidat(parseInt(btn.dataset.scId), parseInt(btn.dataset.stagId), btn.dataset.dispense === 'true', btn.dataset.note, btn.dataset.fichierNom, btn.dataset.dispenseDate, btn.dataset.dispenseOrigine || '', btn.dataset.dispenseEcheance || '');
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
        if (e.target.closest('[data-action="ouvrir-fiche-reco"]')) ouvrirFicheReco();
        if (e.target.closest('[data-action="fermer-fiche-reco"]')) { document.getElementById('modal-fiche-reco').style.display = 'none'; }
        if (e.target.closest('[data-action="enregistrer-fiche-reco"]')) enregistrerFicheReco();
        if (e.target.closest('[data-action="generer-pdf-fiche-reco"]')) genererPdfFicheReco();
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
        if (e.target.closest('[data-action="confirmer-avert-cloture"]')) {
            document.getElementById('modal-avert-cloture').style.display = 'none';
            _executerCloture();
        }
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-avert-cloture"]'))
            document.getElementById('modal-avert-cloture').style.display = 'none';
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="fermer-alerte"]')) fermerAlerte();
    });
    const scTheorie = document.getElementById('sc-theorie');
    if (scTheorie) scTheorie.addEventListener('change', _syncDispenseNote);
    document.addEventListener('change', function(e) {
        const cb = e.target;
        // --- Cocher une option facultative force sa catégorie support à se cocher ---
        if (cb.matches('[name^="jp-opt-"]') && cb.checked && !cb.dataset.incluse) {
            const m = cb.name.match(/^jp-opt-(\d+)-(.+)$/);
            if (m) {
                const sid = m[1];
                const catOpt = m[2];
                const catCb = document.querySelector('[name="jp-cat-' + sid + '"][value="' + catOpt + '"]');
                if (catCb && !catCb.checked) {
                    catCb.checked = true;
                    catCb.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }
        if (!cb.matches('[name^="jp-cat-"]')) return;
        const stagiaireId = parseInt(cb.name.replace('jp-cat-', ''));
        const cat = cb.value;
        if (!cb.checked) {
            const catsAvecResultat = (window._CANDIDATS_EPREUVES[stagiaireId] || window._CANDIDATS_EPREUVES[String(stagiaireId)] || []);
            if (catsAvecResultat.includes(cat)) {
                cb.checked = true;
                alert('Supprimez d\'abord le résultat de la catégorie ' + cat + ' avant de la retirer');
            }
            // Décocher la catégorie décoche aussi ses options facultatives
            document.querySelectorAll('[name="jp-opt-' + stagiaireId + '-' + cat + '"]').forEach(function(ob) {
                if (!ob.dataset.incluse) ob.checked = false;
            });
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
    try {
        var _savedTab = sessionStorage.getItem('sessionDetailTab');
        if (_savedTab) {
            var _btn = document.querySelector('.tab-btn[data-tab="' + _savedTab + '"]');
            if (_btn) showTab(_savedTab, _btn);
        }
    } catch(e) {}
    document.addEventListener('change', function(e) {
        if (e.target && e.target.id === 'sc-theorie') { _syncDispenseNote(); }
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

function _dateFr(iso) {
    if (!iso) return '';
    var p = String(iso).split('-');
    if (p.length !== 3) return iso;
    return p[2] + '/' + p[1] + '/' + p[0];
}

function _dateMoinsUnJour(y, m, d) {
    var dt;
    try {
        dt = new Date(y, m - 1, d);
        if (dt.getMonth() !== (m - 1)) { dt = new Date(y, 2, 1); }
    } catch (e) { dt = new Date(y, 2, 1); }
    dt.setDate(dt.getDate() - 1);
    return dt;
}
function _bornesEcheance(dateBaseIso) {
    var N = (window.SESSION_FAMILLE === 'R482') ? 10 : 5;
    var parts = dateBaseIso.split('-');
    var y = parseInt(parts[0], 10), m = parseInt(parts[1], 10), d = parseInt(parts[2], 10);
    return {
        haute: _dateMoinsUnJour(y + N, m, d),
        basse: _dateMoinsUnJour(y + (N - 1), m, d),
    };
}

function _selectionnerCandidatStagiaire(id, label) {
    document.getElementById('sc-stagiaire').value = id;
    window._scStagiaireId = id;
    var inp = document.getElementById('sc-stagiaire-search');
    if (inp) inp.value = label;
    var liste = document.getElementById('sc-stagiaire-liste');
    if (liste) liste.style.display = 'none';
    _detecterDispense();
}

function _resetStagiaireSearch() {
    document.getElementById('sc-stagiaire').value = '';
    var inp = document.getElementById('sc-stagiaire-search');
    if (inp) { inp.value = ''; inp.disabled = false; }
    var liste = document.getElementById('sc-stagiaire-liste');
    if (liste) liste.style.display = 'none';
}

function showTab(name, btn) {
    ['sequencage','candidats','testeurs','equipements','documents'].forEach(t => {
        document.getElementById('tab-' + t).style.display = 'none';
    });
    document.getElementById('tab-' + name).style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active-tab'));
    btn.classList.add('active-tab');
    try { sessionStorage.setItem('sessionDetailTab', name); } catch(e) {}
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
        // (cas "option-seule" supprimé : une option ne peut exister sans sa catégorie support)
        if (cats.length > 0) candidats_pratique.push({ stagiaire_id: stagiaireId, categories: cats, options });
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
            if (opt.incluse) {
                html += '<label style="display:flex;align-items:center;gap:6px;font-size:14px;color:#888;cursor:default;">'
                     + '<input type="checkbox" name="pratique-option" value="' + opt.code + '" data-incluse="1" disabled> '
                     + opt.code + ' — ' + opt.libelle + ' <span style="font-size:11px;color:#aaa;">(incluse)</span></label>';
            } else {
                const checked = obtained.includes(opt.code) ? 'checked' : '';
                html += '<label style="display:flex;align-items:center;gap:6px;font-size:14px;cursor:pointer;">'
                     + '<input type="checkbox" name="pratique-option" value="' + opt.code + '" ' + checked + '> '
                     + opt.code + ' — ' + opt.libelle + '</label>';
            }
        });
        html += '</div>';
        container.innerHTML = html;
        container.style.display = 'block';
    } else {
        container.innerHTML = '';
        container.style.display = 'none';
    }
    synchroniserOptionsIncluses();
    document.getElementById('modal-pratique').style.display = 'flex';
}

function fermerModalPratique() { document.getElementById('modal-pratique').style.display = 'none'; }

function synchroniserOptionsIncluses() {
    var reussi = document.querySelector('[name="pratique-resultat"]:checked');
    var estReussi = reussi && reussi.value === 'true';
    document.querySelectorAll('[name="pratique-option"][data-incluse="1"]').forEach(function(cb) {
        cb.checked = !!estReussi;
    });
}

document.addEventListener('change', function(e) {
    if (e.target && e.target.name === 'pratique-resultat') {
        synchroniserOptionsIncluses();
    }
});

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
    var selT = document.getElementById('sc-theorie');
    var isDispense = selT && selT.value === 'dispense';
    var field = document.getElementById('field-dispense-note');
    if (field) field.style.display = isDispense ? 'block' : 'none';
    var note = document.getElementById('sc-dispense-note');
    if (!isDispense && note) note.value = '';
    _detecterDispense();
}

function _detecterDispense() {
    var box = document.getElementById('dispense-proposition');
    if (!box) return;
    var selT = document.getElementById('sc-theorie');
    var isDispense = selT && selT.value === 'dispense';
    var stagId = window._scStagiaireId;
    var famille = window.SESSION_FAMILLE;
    var sessionId = window.SESSION_ID;
    if (!isDispense || !stagId || !famille) {
        box.style.display = 'none';
        box.innerHTML = '';
        return;
    }
    box.style.display = 'block';
    box.innerHTML = '🔎 Recherche d\'une base de dispense…';
    var url = '/stagiaires/' + stagId + '/base-theorique?famille=' + encodeURIComponent(famille) + (sessionId ? '&session_id=' + sessionId : '');
    fetch(url, { credentials: 'same-origin' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data || !data.possible) {
                box.innerHTML = 'ℹ️ Aucune base de dispense détectée pour cette famille. Si le candidat détient un CACES d\'un autre organisme, enregistrez-le dans sa fiche (onglet reprise → CACES externes).';
                box.style.background = '#fff7e6';
                box.style.borderColor = '#e0c080';
                return;
            }
            var typeLib = data.type === 'caces' ? 'CACES' : 'Théorie';
            var origineLib = (data.origine === 'externe')
                ? ('externe' + (data.organisme ? ' (' + data.organisme + ')' : ''))
                : 'interne';
            var lienHtml = data.lien ? ' · <a href="' + data.lien + '" target="_blank">Vérifier ↗</a>' : '';
            box.style.background = '#eef2f5';
            box.style.borderColor = '#cbd5dc';
            box.innerHTML =
                '<strong>ℹ️ Dispense possible (à valider par vous)</strong><br>' +
                'Base : ' + typeLib + ' — ' + (data.reference || '') + '<br>' +
                'Origine : ' + origineLib + '<br>' +
                'Date d\'origine : ' + _dateFr(data.date_origine) + ' · Dispense valable jusqu\'au ' + _dateFr(data.date_limite_dispense) +
                lienHtml;
        })
        .catch(function() {
            box.innerHTML = '⚠️ Erreur lors de la recherche de base de dispense.';
            box.style.background = '#fdecea';
            box.style.borderColor = '#e0a0a0';
        });
}

function _appliquerVisibiliteOrigine() { /* obsolete : origine geree par le moteur */ }

function _verifierQ2() { return; }
function _verifierQ2_obsolete() {
    var warn = document.getElementById('dispense-q2-warning');
    var radioExt = document.getElementById('dispense-origine-externe');
    if (!warn || !radioExt) return;
    var dateExtVal = document.getElementById('sc-dispense-date').value;
    if (radioExt.checked && window._dispenseDateInterne && dateExtVal && dateExtVal < window._dispenseDateInterne) {
        warn.style.display = 'block';
        warn.innerHTML = '⚠️ La date externe saisie (' + _dateFr(dateExtVal) + ') est ANTERIEURE a la base interne detectee (' + _dateFr(window._dispenseDateInterne) + '). La base la plus recente devrait primer — verifiez votre saisie.';
    } else {
        warn.style.display = 'none';
        warn.innerHTML = '';
    }
}

function _verifierEcheance() { return; }
function _verifierEcheance_obsolete() {
    var warn = document.getElementById('dispense-echeance-warning');
    var radioExt = document.getElementById('dispense-origine-externe');
    if (!warn || !radioExt) return;
    var baseVal = document.getElementById('sc-dispense-date').value;
    var echVal = document.getElementById('sc-dispense-echeance').value;
    if (!radioExt.checked || !baseVal || !echVal) { warn.style.display = 'none'; return; }
    var ech = new Date(echVal + 'T00:00:00');
    var base = new Date(baseVal + 'T00:00:00');
    var b = _bornesEcheance(baseVal);
    if (ech <= base) {
        warn.style.display = 'block';
        warn.style.background = '#fde8e8'; warn.style.border = '1px solid #e0a0a0'; warn.style.color = '#a33';
        warn.innerHTML = '⛔ L\'echeance (' + _dateFr(echVal) + ') doit etre posterieure a la date de base (' + _dateFr(baseVal) + '). Le serveur refusera l\'enregistrement.';
    } else if (ech > b.haute) {
        warn.style.display = 'block';
        warn.style.background = '#fde8e8'; warn.style.border = '1px solid #e0a0a0'; warn.style.color = '#a33';
        warn.innerHTML = '⛔ L\'echeance (' + _dateFr(echVal) + ') depasse la duree maximale du CACES (jusqu\'au ' + _dateFr(_isoFromDate(b.haute)) + ' max). Le serveur refusera l\'enregistrement.';
    } else if (ech < b.basse) {
        warn.style.display = 'block';
        warn.style.background = '#fff7e6'; warn.style.border = '1px solid #e0c080'; warn.style.color = '#8a6d3b';
        warn.innerHTML = '⚠️ L\'echeance (' + _dateFr(echVal) + ') est plus courte que prevu (attendu apres le ' + _dateFr(_isoFromDate(b.basse)) + '). Verifiez le justificatif externe — non bloquant.';
    } else {
        warn.style.display = 'none';
    }
}

function _isoFromDate(dt) {
    var mm = String(dt.getMonth() + 1).padStart(2, '0');
    var dd = String(dt.getDate()).padStart(2, '0');
    return dt.getFullYear() + '-' + mm + '-' + dd;
}

function _appliquerRoleModaleCandidat() {
    var estTerrain = window.USER_ROLE === 'terrain';
    var ids = ['sc-stagiaire-search', 'sc-theorie', 'dispense-origine-interne', 'dispense-origine-externe', 'sc-dispense-date', 'sc-dispense-echeance', 'sc-dispense-note'];
    ids.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.disabled = estTerrain;
    });
    var btnSave = document.querySelector('[data-action="sauvegarder-candidat"]');
    if (btnSave) btnSave.style.display = estTerrain ? 'none' : '';
    var btnAnnuler = document.querySelector('[data-action="fermer-modal-candidat"]');
    if (btnAnnuler && estTerrain) btnAnnuler.textContent = 'Fermer';
}

function ouvrirAjoutCandidat() {
    document.getElementById('candidat-title').textContent = 'Ajouter un candidat';
    document.getElementById('sc-id').value = '';
    _majAffichageJustif('');
    _resetStagiaireSearch();
    document.getElementById('sc-theorie').value = 'normal';
    var _note = document.getElementById('sc-dispense-note');
    if (_note) _note.value = '';
    var _fn = document.getElementById('field-dispense-note');
    if (_fn) _fn.style.display = 'none';
    var _box = document.getElementById('dispense-proposition');
    if (_box) { _box.style.display = 'none'; _box.innerHTML = ''; }
    document.getElementById('field-stagiaire').style.display = 'block';
    if (window.USER_ROLE === 'terrain') {
        afficherErreur('L\'inscription d\'un candidat est reservee au back-office.');
        return;
    }
    document.getElementById('modal-candidat').style.display = 'flex';
}

function editerCandidat(id, stagiaireId, theorie_dispensee, dispenseNote, fichierNom, dispenseDate, origine, dispenseEcheance) {
    window._scStagiaireId = stagiaireId;
    document.getElementById('candidat-title').textContent = 'Modifier candidat';
    document.getElementById('sc-id').value = id;
    document.getElementById('sc-stagiaire').value = stagiaireId;
    document.getElementById('sc-theorie').value = theorie_dispensee ? 'dispense' : 'normal';
    var _en = document.getElementById('sc-dispense-note');
    if (_en) _en.value = dispenseNote || '';
    var _efn = document.getElementById('field-dispense-note');
    if (_efn) _efn.style.display = theorie_dispensee ? 'block' : 'none';
    document.getElementById('field-stagiaire').style.display = 'none';
    _syncDispenseNote();
    document.getElementById('modal-candidat').style.display = 'flex';
    _detecterDispense();
    _appliquerRoleModaleCandidat();

}

function fermerModalCandidat() { document.getElementById('modal-candidat').style.display = 'none'; }

function ouvrirFicheReco() {
    var stagiaireId = window._frStagiaireId;
    var sessionId = window.SESSION_ID;
    if (!stagiaireId || !sessionId) { afficherErreur('Candidat introuvable'); return; }
    var modal = document.getElementById('modal-fiche-reco');
    var contenu = document.getElementById('fr-contenu');
    var actions = document.getElementById('fr-actions');
    contenu.innerHTML = '<div style="text-align:center; color:#888; padding:40px;">Chargement…</div>';
    actions.style.display = 'none';
    modal.style.display = 'flex';
    fetch('/api/fiches-reco/' + sessionId + '/' + stagiaireId)
        .then(function (r) { return r.json(); })
        .then(function (data) { construireFormFicheReco(data); })
        .catch(function () { contenu.innerHTML = '<div style="color:#cc0000; padding:20px;">Erreur de chargement de la fiche.</div>'; });
}

function _frEsc(s) {
    if (s == null) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _frRecalcTotal() {
    document.querySelectorAll('[data-fr-soustotal]').forEach(function (el) {
        var cat = el.getAttribute('data-fr-soustotal');
        var st = 0;
        document.querySelectorAll('[data-fr-cat="' + cat + '"]').forEach(function (inp) {
            var v = parseFloat(inp.value);
            if (!isNaN(v)) st += v;
        });
        var txt = (st === Math.floor(st)) ? String(st) : String(st).replace('.', ',');
        el.textContent = txt + ' h';
    });
    var total = 0;
    document.querySelectorAll('[data-fr-duree="1"]').forEach(function (inp) {
        var v = parseFloat(inp.value);
        if (!isNaN(v)) total += v;
    });
    var el = document.getElementById('fr-total-heures');
    if (el) {
        var txt = (total === Math.floor(total)) ? String(total) : String(total).replace('.', ',');
        el.textContent = txt + ' h';
    }
}

function _frInputDuree(id, cat, valeurDefaut) {
    var v = (valeurDefaut != null) ? valeurDefaut : '';
    return '<input type="number" id="' + id + '" value="' + v + '" min="0" step="0.5" style="width:72px; padding:5px 7px; border:1.5px solid #c8d8f0; border-radius:6px; font-size:13px;" data-fr-duree="1" data-fr-cat="' + _frEsc(cat) + '"> <span style="font-size:12px; color:#666;">h</span>';
}

function _frSommeCat(cat) {
    var st = 0;
    document.querySelectorAll('[data-fr-cat="' + cat + '"]').forEach(function (inp) {
        var v = parseFloat(inp.value);
        if (!isNaN(v)) st += v;
    });
    return st;
}

function _frCollectSaisies(calcul) {
    var saisies = { pratiques: {} };
    var selTh = document.getElementById('fr-duree-theorie');
    if (selTh) saisies.theorie = parseFloat(selTh.value) || 0;
    (calcul.pratiques_echec || []).forEach(function (p) {
        saisies.pratiques[p.categorie] = { duree_heures: _frSommeCat(p.categorie) };
    });
    var totalEl = document.getElementById('fr-total-heures');
    if (totalEl) saisies.total_label = totalEl.textContent;
    return saisies;
}

function construireFormFicheReco(data) {
    var contenu = document.getElementById('fr-contenu');
    var actions = document.getElementById('fr-actions');
    var calcul = data.calcul || {};
    var fiche = data.fiche || {};
    window._frData = data;
    if (!calcul.a_des_echecs) {
        contenu.innerHTML = '<div style="text-align:center; padding:40px; color:#1b5e20; background:#e8f5e9; border-radius:10px;"><div style="font-size:40px;">✓</div><div style="font-size:16px; font-weight:600; margin-top:8px;">Aucune recommandation nécessaire</div><div style="font-size:13px; color:#555; margin-top:6px;">Ce candidat n\'a échoué à aucune épreuve dans cette session.</div></div>';
        actions.style.display = 'none';
        return;
    }
    var c = calcul.candidat || {};
    var html = '';
    html += '<div style="background:#f6f7f9; border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:13px;"><strong>' + _frEsc(c.nom) + ' ' + _frEsc(c.prenom) + '</strong>' + (c.date_naissance ? ' <span style="color:#888;">né(e) le ' + _frEsc(c.date_naissance) + '</span>' : '') + '</div>';

    if (calcul.theorie_echec) {
        var th = calcul.theorie_echec;
        var themesT = (th.themes_echoues || []).map(function (t) { return '<li>' + _frEsc(t.libelle) + '</li>'; }).join('');
        html += '<div style="border:1px solid #e57373; border-radius:8px; margin-bottom:12px;"><div style="background:#fcebeb; color:#a32d2d; padding:7px 12px; font-weight:600; font-size:13px; border-radius:8px 8px 0 0;">✗ Épreuve théorique — échouée (' + _frEsc(th.note_totale) + '/100)</div><div style="padding:10px 12px;"><div style="font-size:12px; color:#666; margin-bottom:4px;">Thèmes à retravailler :</div><ul style="margin:0 0 10px 18px; font-size:13px; color:#333;">' + (themesT || '<li style="color:#888;">—</li>') + '</ul><label style="font-size:12px; color:#666; display:block; margin-bottom:4px;">Durée de formation recommandée</label>' + _frInputDuree('fr-duree-theorie', 'THEO', th.duree_heures) + '</div></div>';
    }
    (calcul.pratiques_echec || []).forEach(function (p) {
        var cat = p.categorie;
        var ti = 0;
        var blocsHtml = (p.themes_blocs || []).map(function (tb) {
            var inner = '';
            if (tb.moyenne_insuffisante) {
                inner += '<div style="font-size:11px; color:#555; margin:2px 0;">Moyenne du thème insuffisante</div>';
            }
            (tb.pe_zero || []).forEach(function (pe) {
                inner += '<li style="color:#a32d2d;">' + _frEsc(pe.libelle) + ' — <strong>0/' + _frEsc(pe.bareme) + '</strong> (note éliminatoire)</li>';
            });
            (tb.pe_sous_moyenne || []).forEach(function (pe) {
                inner += '<li style="color:#7a5a12;">' + _frEsc(pe.libelle) + ' — ' + _frEsc(pe.note) + '/' + _frEsc(pe.bareme) + ' (sous la moyenne)</li>';
            });
            var champThemeId = 'fr-th-' + cat + '-' + ti; ti++;
            var champ = _frInputDuree(champThemeId, cat, 1.5);
            return '<div style="margin-bottom:10px; border-bottom:1px dashed #eee; padding-bottom:8px;"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="font-size:13px; font-weight:600; color:#2d2d2d;">' + _frEsc(tb.theme) + '</div><div>' + champ + '</div></div><ul style="margin:4px 0 0 18px; font-size:12px;">' + (inner || '<li style="color:#888;">—</li>') + '</ul></div>';
        }).join('');
        var optHtml = '';
        if (p.options_a_repasser && p.options_a_repasser.length && p.base_reussie) {
            optHtml = '<div style="font-size:12px; color:#7a5a12; background:#faeeda; border-radius:6px; padding:6px 9px; margin-top:8px;">Catégorie obtenue, mais option(s) à repasser : ' + p.options_a_repasser.map(function (o) { return _frEsc(o.libelle); }).join(', ') + '</div>';
        }
        html += '<div style="border:1px solid #e57373; border-radius:8px; margin-bottom:12px;"><div style="background:#fcebeb; color:#a32d2d; padding:7px 12px; font-weight:600; font-size:13px; border-radius:8px 8px 0 0;">✗ Pratique catégorie ' + _frEsc(cat) + ' — échouée</div><div style="padding:10px 12px;">';
        if (p.categorie_echouee) {
            html += '<div style="font-size:12px; color:#666; margin-bottom:6px;">Thèmes à retravailler (' + (p.nb_themes || 0) + ') — durée ajustable par thème :</div>' + (blocsHtml || '<div style="color:#888; font-size:12px;">—</div>');
            if (p.fautes_eliminatoires && p.fautes_eliminatoires.length) {
                html += '<div style="margin-top:8px; background:#fcebeb; border:1px solid #e57373; border-radius:6px; padding:6px 9px;"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="font-size:12px; font-weight:600; color:#a32d2d;">Faute(s) éliminatoire(s) :</div><div>' + _frInputDuree('fr-elim-' + cat, cat, 1) + '</div></div><ul style="margin:3px 0 0 18px; font-size:12px; color:#a32d2d;">' + p.fautes_eliminatoires.map(function (f) { return '<li>' + _frEsc(f) + '</li>'; }).join('') + '</ul></div>';
            }
            if (p.temps_blocs && p.temps_blocs.length) {
                var tiT = 0;
                var tHtml = p.temps_blocs.map(function (tb) {
                    var elim = (tb.niveau === 'eliminatoire');
                    var pctBg = elim ? '#a32d2d' : '#e0a94a';
                    var pctFg = elim ? '#ffffff' : '#5a3a00';
                    var etiq = elim
                        ? '<span style="color:#a32d2d; font-weight:600;">temps éliminatoire (&gt; 130%)</span>'
                        : '<span style="color:#b26a00; font-weight:600;">à améliorer (100–130%)</span>';
                    var champTid = 'fr-temps-' + cat + '-' + tiT; tiT++;
                    return '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                        + '<div style="display:flex; align-items:center; gap:8px; font-size:12px; color:#333;">'
                        + '<span style="display:inline-block; min-width:40px; text-align:center; padding:2px 0; border-radius:4px; font-weight:700; background:' + pctBg + '; color:' + pctFg + ';">' + _frEsc(tb.pct) + '%</span>'
                        + '<span><strong>' + _frEsc(tb.libelle) + '</strong> — ' + etiq + '</span></div>'
                        + '<div>' + _frInputDuree(champTid, cat, tb.duree_heures) + '</div></div>';
                }).join('');
                html += '<div style="margin-top:8px; background:#fdf6ea; border-left:4px solid #b26a00; padding:8px 12px;"><div style="font-size:12px; font-weight:600; color:#b26a00; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Maîtrise du temps</div>' + tHtml + '</div>';
            }
            html += '<div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center; background:#f6f7f9; border-radius:6px; padding:7px 12px;"><span style="font-size:12px; font-weight:600; color:#2d2d2d;">Sous-total catégorie ' + _frEsc(cat) + '</span><span style="font-weight:700; font-size:14px; color:#2d2d2d;" data-fr-soustotal="' + _frEsc(cat) + '">—</span></div>';
        }
        html += optHtml + '</div></div>';
    });
    html += '<div style="background:#2d2d2d; color:#fff; border-radius:8px; padding:10px 14px; margin:8px 0 16px; display:flex; justify-content:space-between; align-items:center; font-size:14px;"><span style="font-weight:600;">Durée totale de formation recommandée</span><span id="fr-total-heures" style="font-weight:700; font-size:16px;">' + _frEsc(calcul.duree_totale_label || '0 h') + '</span></div>';
    html += '<div style="margin-top:8px; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888; margin-bottom:8px;">Précisions du testeur</div><div style="display:flex; flex-direction:column; gap:7px;"><label style="font-size:13px; display:flex; align-items:center; gap:8px; font-weight:normal;"><input type="checkbox" id="fr-fraude"' + (fiche.fraude_theorie ? ' checked' : '') + '> Fraude ou tentative de fraude pendant l\'épreuve théorique</label><label style="font-size:13px; display:flex; align-items:center; gap:8px; font-weight:normal;"><input type="checkbox" id="fr-langue"' + (fiche.difficultes_langue ? ' checked' : '') + '> Importantes difficultés de compréhension de la langue française</label><label style="font-size:13px; display:flex; align-items:center; gap:8px; font-weight:normal;"><input type="checkbox" id="fr-comportement"' + (fiche.comportement_dangereux ? ' checked' : '') + '> Comportement dangereux incompatible avec la conduite en sécurité</label></div><div style="margin-top:10px;"><label style="font-size:12px; color:#666;">Autres précisions</label><textarea id="fr-autres" rows="2" style="width:100%; margin-top:4px; border:1.5px solid #c8d8f0; border-radius:8px; padding:8px; font-size:13px; box-sizing:border-box;">' + _frEsc(calcul.observations_testeur || '') + '</textarea></div>';
    contenu.innerHTML = html;
    actions.style.display = 'flex';
    contenu.querySelectorAll('[data-fr-duree="1"]').forEach(function (inp) { inp.addEventListener('input', _frRecalcTotal); });
    _frRecalcTotal();
}

function enregistrerFicheReco() {
    var data = window._frData;
    if (!data) return;
    var calcul = data.calcul || {};
    var stagiaireId = window._frStagiaireId;
    var sessionId = window.SESSION_ID;
    var saisies = _frCollectSaisies(calcul);
    var payload = {
        fraude_theorie: !!(document.getElementById('fr-fraude') && document.getElementById('fr-fraude').checked),
        difficultes_langue: !!(document.getElementById('fr-langue') && document.getElementById('fr-langue').checked),
        comportement_dangereux: !!(document.getElementById('fr-comportement') && document.getElementById('fr-comportement').checked),
        autres_precisions: (document.getElementById('fr-autres') || {}).value || null,
        saisies: saisies
    };
    var btn = document.getElementById('fr-btn-enregistrer');
    if (btn) { btn.disabled = true; btn.textContent = 'Enregistrement…'; }
    fetch('/api/fiches-reco/' + sessionId + '/' + stagiaireId, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        .then(function (r) { return r.json(); })
        .then(function (res) {
            if (btn) { btn.disabled = false; btn.textContent = 'Enregistrer'; }
            if (res && res.ok) { if (typeof toast === 'function') toast('Fiche enregistrée'); else if (typeof afficherSucces === 'function') afficherSucces('Fiche enregistrée'); }
            else { if (typeof afficherErreur === 'function') afficherErreur('Erreur lors de l\'enregistrement'); }
        })
        .catch(function () { if (btn) { btn.disabled = false; btn.textContent = 'Enregistrer'; } if (typeof afficherErreur === 'function') afficherErreur('Erreur réseau'); });
}

function genererPdfFicheReco() {
    var stagiaireId = window._frStagiaireId;
    var sessionId = window.SESSION_ID;
    if (!stagiaireId || !sessionId) return;
    var btn = document.getElementById('fr-btn-pdf');
    if (btn) { btn.disabled = true; btn.textContent = 'Génération…'; }
    var data = window._frData || {};
    var calcul = data.calcul || {};
    var saisies = _frCollectSaisies(calcul);
    var payload = {
        fraude_theorie: !!(document.getElementById('fr-fraude') && document.getElementById('fr-fraude').checked),
        difficultes_langue: !!(document.getElementById('fr-langue') && document.getElementById('fr-langue').checked),
        comportement_dangereux: !!(document.getElementById('fr-comportement') && document.getElementById('fr-comportement').checked),
        autres_precisions: (document.getElementById('fr-autres') || {}).value || null,
        saisies: saisies
    };
    fetch('/api/fiches-reco/' + sessionId + '/' + stagiaireId, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        .then(function () {
            window.open('/api/fiches-reco/' + sessionId + '/' + stagiaireId + '/pdf', '_blank');
            if (btn) { btn.disabled = false; btn.textContent = '📄 Générer le PDF'; }
        })
        .catch(function () {
            if (btn) { btn.disabled = false; btn.textContent = '📄 Générer le PDF'; }
            if (typeof afficherErreur === 'function') afficherErreur('Erreur lors de la génération');
        });
}

async function sauvegarderCandidat() {
    const id = document.getElementById('sc-id').value;
    const isDispense = document.getElementById('sc-theorie').value === 'dispense';
    const data = {
        session_id: window.SESSION_ID,
        stagiaire_id: parseInt(document.getElementById('sc-stagiaire').value),
        theorie_dispensee: isDispense,
        dispense_note: isDispense ? ((document.getElementById('sc-dispense-note') || {}).value || '').trim() || null : null
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

function _executerCloture() {
    fetch('/api/sessions/' + window.SESSION_ID + '/cloturer', { method: 'POST' })
        .then(function(resp) {
            if (resp.ok) { location.reload(); }
            else { resp.json().then(function(d) { afficherErreur(d.detail || 'Erreur !'); }); }
        });
}

function cloturerSession() {
    if (window.SESSION_SANS_RESULTAT) {
        document.getElementById('modal-avert-cloture').style.display = 'flex';
    } else {
        demanderConfirmation('Clôturer la session ? Les résultats seront verrouillés.', _executerCloture);
    }
}

function cloturerTerrain() {
    document.getElementById('pin-message').textContent = 'Clôturer la session côté terrain ? Saisir le PIN formateur.';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/cloturer-terrain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin })
        });
        if (resp.ok) { fermerPin(); location.reload(); }
        else {
            const data = await resp.json().catch(() => ({}));
            document.getElementById('pin-error').textContent = data.detail || 'Erreur';
            document.getElementById('pin-error').style.display = 'block';
        }
    };
}

function rouvrirTerrain() {
    document.getElementById('pin-message').textContent = 'Réouvrir la session côté terrain ? Saisir le PIN administrateur.';
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/api/sessions/' + window.SESSION_ID + '/rouvrir-terrain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin })
        });
        if (resp.ok) { fermerPin(); location.reload(); }
        else {
            const data = await resp.json().catch(() => ({}));
            document.getElementById('pin-error').textContent = data.detail || 'Erreur';
            document.getElementById('pin-error').style.display = 'block';
        }
    };
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
        // Stocke le contexte et ouvre la modale de CHOIX (en ligne vs manuel)
        window._pratiqueCtx = {
            stagiaireId: parseInt(btn.dataset.stagiaireId),
            jourTestId: btn.dataset.jourTestId,
            cat: btn.dataset.cat,
            date: btn.dataset.date,
            testeurId: btn.dataset.testeurId,
            identite: btn.dataset.identite === 'true',
            obtenue: btn.dataset.obtenue === 'true',
            noteTesteur: btn.dataset.noteTesteur,
            optsPlanif: optsPlanif,
            optsObtenues: btn.dataset.optsObtenues,
            epreuveId: parseInt(btn.dataset.epreuveId),
            estNumerique: btn.dataset.estNumerique === '1',
            justifNom: btn.dataset.justifNom || ''
        };
        var zonePdf = document.getElementById('choix-pratique-pdf-zone');
        if (zonePdf) zonePdf.style.display = 'block';
        var mc = document.getElementById('modal-choix-pratique');
        if (mc) mc.style.display = 'flex';
    });

    // Fermer la modale de choix
    document.addEventListener('click', function (e) {
        if (e.target.closest('[data-action="fermer-choix-pratique"]')) {
            document.getElementById('modal-choix-pratique').style.display = 'none';
        }
    });

    // Choix : enregistrement manuel -> modale existante (comportement d'origine)
    document.addEventListener('click', function (e) {
        if (!e.target.closest('[data-action="choix-pratique-manuel"]')) return;
        document.getElementById('modal-choix-pratique').style.display = 'none';
        var c = window._pratiqueCtx; if (!c) return;
        saisirResultatPratique(
            c.stagiaireId, c.cat, c.date, c.testeurId, c.identite,
            c.obtenue, c.noteTesteur, c.optsPlanif, c.optsObtenues, c.epreuveId
        );
    });

    // Choix : "Résultats" -> selon la voie de saisie.
    //  - numerique : PDF genere a la volee (en-tete, notes, signature)
    //  - manuel    : fichier justificatif depose (grille jointe)
    document.addEventListener('click', function (e) {
        if (!e.target.closest('[data-action="choix-pratique-pdf"]')) return;
        var c = window._pratiqueCtx; if (!c) return;
        var sidp = (typeof SESSION_ID !== 'undefined') ? SESSION_ID : (document.body.dataset.sessionId || window.location.pathname.split('/')[2]);
        document.getElementById('modal-choix-pratique').style.display = 'none';
        if (c.estNumerique) {
            window.open('/api/sessions/' + sidp + '/pratique/resultat/' + c.jourTestId + '/' + c.stagiaireId + '/' + encodeURIComponent(c.cat) + '/pdf', '_blank');
        } else if (c.justifNom) {
            window.open('/api/sessions/' + sidp + '/pratique/justificatif/' + c.epreuveId, '_blank');
        } else {
            afficherErreur("Aucun document disponible : joignez la grille d’évaluation via l’icône sous la catégorie.");
        }
    });

    // Choix : saisie en ligne -> ecran plein ecran (nouvel onglet)
    document.addEventListener('click', function (e) {
        if (!e.target.closest('[data-action="choix-pratique-enligne"]')) return;
        document.getElementById('modal-choix-pratique').style.display = 'none';
        var c = window._pratiqueCtx; if (!c) return;
        var sid = (typeof SESSION_ID !== 'undefined') ? SESSION_ID : (document.body.dataset.sessionId || window.location.pathname.split('/')[2]);
        window.open('/sessions/' + sid + '/pratique/saisie-en-ligne/' + c.jourTestId + '/' + c.stagiaireId + '/' + c.cat, '_blank');
    });

    // Bouton "+" nouveau résultat pratique -> modale de CHOIX (en ligne vs manuel)
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-action="nouveau-resultat-pratique"]');
        if (!btn) return;
        var optsPlanifNew; try { optsPlanifNew = JSON.parse(btn.dataset.optsPlanif || '[]'); } catch(e) { optsPlanifNew = []; }
        window._pratiqueCtx = {
            stagiaireId: parseInt(btn.dataset.stagiaireId),
            cat: btn.dataset.cat,
            date: btn.dataset.date,
            testeurId: '',
            identite: btn.dataset.identite === 'true',
            obtenue: null,
            noteTesteur: '',
            optsPlanif: optsPlanifNew,
            optsObtenues: '',
            epreuveId: null,
            jourTestId: parseInt(btn.dataset.jourTestId)
        };
        var zonePdfN = document.getElementById('choix-pratique-pdf-zone');
        if (zonePdfN) zonePdfN.style.display = 'none';
        var mc = document.getElementById('modal-choix-pratique');
        if (mc) mc.style.display = 'flex';
    });
});

// ── Modal choix test théorique (numérique vs dégradé) ───────────────────────
document.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-action="choix-test"]');
    if (btn) {
        var modal = document.getElementById('modal-choix-test');
        modal.dataset.sessionId = btn.dataset.sessionId;
        modal.dataset.jourId    = btn.dataset.jourId;
        modal.style.display = 'flex';
        return;
    }
    if (e.target.closest('[data-action="fermer-choix-test"]')) {
        document.getElementById('modal-choix-test').style.display = 'none';
        return;
    }
    if (e.target.closest('[data-action="choix-test-numerique"]')) {
        var modal = document.getElementById('modal-choix-test');
        var sid = modal.dataset.sessionId;
        var jid = modal.dataset.jourId;
        modal.style.display = 'none';
        window.open('/test/theorie/' + sid + '/' + jid, '_blank');
        return;
    }
    if (e.target.closest('[data-action="choix-test-degrade"]')) {
        var modal = document.getElementById('modal-choix-test');
        var sid = modal.dataset.sessionId;
        var jid = modal.dataset.jourId;
        modal.style.display = 'none';
        window.open('/sessions/' + sid + '/theorie/saisie-degrade/' + jid, '_blank');
        return;
    }
});

// ── Loupe résultat théorique (numérique uniquement) ──────────────────────────
document.addEventListener('click', function(e) {

    // ── Ouvrir le menu loupe ──────────────────────────────────────────────────
    var btnLoupe = e.target.closest('[data-action="loupe-theorie"]');
    if (btnLoupe) {
        var modal = document.getElementById('modal-loupe-theorie');
        modal.dataset.sessionId   = btnLoupe.dataset.sessionId;
        modal.dataset.stagiaireId = btnLoupe.dataset.stagiaireId;
        modal.dataset.jourId      = btnLoupe.dataset.jourId;
        modal.dataset.cloture     = btnLoupe.dataset.cloture;

        var btnModifier  = document.getElementById('btn-loupe-modifier');
        var btnSupprimer = document.getElementById('btn-loupe-supprimer');
        if (btnModifier)  btnModifier.style.display  = (btnLoupe.dataset.cloture === '1') ? 'none' : '';
        if (btnSupprimer) btnSupprimer.style.display = '';   // Tous rôles — PIN formateur requis côté serveur

        modal.style.display = 'flex';
        return;
    }

    // ── Fermer le menu loupe ──────────────────────────────────────────────────
    if (e.target.closest('[data-action="fermer-loupe-theorie"]')) {
        document.getElementById('modal-loupe-theorie').style.display = 'none';
        return;
    }

    // ── Visualiser — ouvre la page Détail ────────────────────────────────────
    if (e.target.closest('[data-action="loupe-visualiser"]')) {
        var modal = document.getElementById('modal-loupe-theorie');
        var sid   = modal.dataset.sessionId;
        var stag  = modal.dataset.stagiaireId;
        var jid   = modal.dataset.jourId;
        modal.style.display = 'none';
        window.open('/sessions/' + sid + '/theorie/' + stag + '/detail?jour_id=' + jid, '_blank');
        return;
    }

    // ── Modifier — PIN → reouvrir → localStorage → /start (atterrit sur récap) ─
    if (e.target.closest('[data-action="loupe-modifier"]')) {
        var modal = document.getElementById('modal-loupe-theorie');
        var sid   = modal.dataset.sessionId;
        var stag  = modal.dataset.stagiaireId;
        var jid   = modal.dataset.jourId;
        modal.style.display = 'none';

        document.getElementById('pin-message').textContent = 'Code PIN formateur — corriger le résultat.';
        document.getElementById('pin-input').value = '';
        document.getElementById('pin-error').style.display = 'none';
        document.getElementById('pin-error').textContent = '';
        document.getElementById('modal-pin').style.display = 'flex';

        document.getElementById('pin-confirm-btn').onclick = async function() {
            var pin = document.getElementById('pin-input').value;
            var tok = localStorage.getItem('token');
            var h   = { 'Content-Type': 'application/json' };
            if (tok) h['Authorization'] = 'Bearer ' + tok;
            var resp;
            try {
                resp = await fetch(
                    '/api/sessions/' + sid + '/theorie/reouvrir/' + stag + '/' + jid,
                    { method: 'POST', headers: h, credentials: 'same-origin', body: JSON.stringify({ pin: pin }) }
                );
            } catch (err) {
                document.getElementById('pin-error').textContent = 'Erreur réseau.';
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            if (resp.status === 403) {
                document.getElementById('pin-error').textContent = 'Code PIN incorrect.';
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            if (!resp.ok) {
                var errData = await resp.json().catch(function() { return {}; });
                document.getElementById('pin-error').textContent = errData.detail || 'Erreur ' + resp.status;
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            var data = await resp.json();
            var cle = 'corriger_rt_' + sid + '_' + jid + '_' + stag;
            localStorage.setItem(cle, JSON.stringify(data.reponses || {}));
            localStorage.setItem('testeur_corr_' + sid + '_' + jid + '_' + stag, data.testeur_id != null ? String(data.testeur_id) : '');
            fermerPin();
            // Route : /test/theorie/{jour_test_id}/{stagiaire_id}/start (sans session_id)
            // La clé localStorage corriger_rt_{sid}_{jid}_{stag} garde bien sid — c'est le SESSION_ID
            // passé par le template page_test_theorie_start (jour.session_id).
            window.open('/test/theorie/' + jid + '/' + stag + '/start', '_blank');
        };
        return;
    }

    // ── Supprimer — PIN → DELETE → reload ────────────────────────────────────
    if (e.target.closest('[data-action="loupe-supprimer"]')) {
        var modal = document.getElementById('modal-loupe-theorie');
        var sid   = modal.dataset.sessionId;
        var stag  = modal.dataset.stagiaireId;
        var jid   = modal.dataset.jourId;
        modal.style.display = 'none';

        document.getElementById('pin-message').textContent = 'Code PIN formateur — supprimer définitivement ce résultat théorique ?';
        document.getElementById('pin-input').value = '';
        document.getElementById('pin-error').style.display = 'none';
        document.getElementById('pin-error').textContent = '';
        document.getElementById('modal-pin').style.display = 'flex';

        document.getElementById('pin-confirm-btn').onclick = async function() {
            var pin = document.getElementById('pin-input').value;
            var tok = localStorage.getItem('token');
            var h   = { 'Content-Type': 'application/json' };
            if (tok) h['Authorization'] = 'Bearer ' + tok;
            var resp;
            try {
                resp = await fetch(
                    '/api/sessions/' + sid + '/theorie/reponses/' + stag + '/' + jid,
                    { method: 'DELETE', headers: h, credentials: 'same-origin', body: JSON.stringify({ pin: pin }) }
                );
            } catch (err) {
                document.getElementById('pin-error').textContent = 'Erreur réseau.';
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            if (resp.status === 403) {
                document.getElementById('pin-error').textContent = 'Code PIN incorrect.';
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            if (!resp.ok) {
                var errData = await resp.json().catch(function() { return {}; });
                document.getElementById('pin-error').textContent = errData.detail || 'Erreur ' + resp.status;
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            fermerPin();
            location.reload();
        };
        return;
    }
});

// ── Justificatif PDF (résultat dégradé) ──────────────────────────────────────
var _justifCtx = null;   // { sessionId, stagId, jourId, fichier_base64, fichier_nom }

document.getElementById('justif-file-input').addEventListener('change', function() {
    var file = this.files[0];
    this.value = '';   // reset pour permettre re-sélection
    if (!file || !_justifCtx) return;

    var reader = new FileReader();
    reader.onload = function(ev) {
        // ev.target.result = "data:application/pdf;base64,XXXXX"
        _justifCtx.fichier_base64 = ev.target.result.split(',')[1];
        _justifCtx.fichier_nom    = file.name;

        document.getElementById('pin-message').textContent = 'Code PIN formateur — ajouter le justificatif PDF.';
        document.getElementById('pin-input').value = '';
        document.getElementById('pin-error').style.display = 'none';
        document.getElementById('pin-error').textContent = '';
        document.getElementById('modal-pin').style.display = 'flex';

        document.getElementById('pin-confirm-btn').onclick = async function() {
            var pin = document.getElementById('pin-input').value;
            var tok = localStorage.getItem('token');
            var h   = { 'Content-Type': 'application/json' };
            if (tok) h['Authorization'] = 'Bearer ' + tok;
            var ctx = _justifCtx;
            var resp;
            try {
                resp = await fetch(
                    '/api/sessions/' + ctx.sessionId + '/theorie/justificatif/' + ctx.stagId + '/' + ctx.jourId,
                    { method: 'POST', headers: h, credentials: 'same-origin',
                      body: JSON.stringify({ pin: pin, fichier_base64: ctx.fichier_base64, fichier_nom: ctx.fichier_nom }) }
                );
            } catch (err) {
                document.getElementById('pin-error').textContent = 'Erreur réseau.';
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            if (resp.status === 403) {
                document.getElementById('pin-error').textContent = 'Code PIN incorrect.';
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            if (!resp.ok) {
                var errData = await resp.json().catch(function() { return {}; });
                document.getElementById('pin-error').textContent = errData.detail || 'Erreur ' + resp.status;
                document.getElementById('pin-error').style.display = 'block';
                return;
            }
            fermerPin();
            location.reload();
        };
    };
    reader.readAsDataURL(file);
});

// ── Justificatif grille pratique (multi-format, 1 fichier, R2) ──
var _justifPratiqueCtx = null;
(function() {
    var inp = document.getElementById('justif-pratique-file-input');
    if (!inp) {
        inp = document.createElement('input');
        inp.type = 'file';
        inp.id = 'justif-pratique-file-input';
        inp.accept = '.pdf,.xlsx,.xls,.docx,.doc,.jpg,.jpeg,.png,.heic,.webp';
        inp.style.display = 'none';
        document.body.appendChild(inp);
    }
    inp.addEventListener('change', function() {
        var file = this.files && this.files[0];
        this.value = '';
        if (!file || !_justifPratiqueCtx) return;
        if (file.size > 10 * 1024 * 1024) {
            alert('Fichier trop volumineux (10 Mo maximum).');
            return;
        }
        var reader = new FileReader();
        reader.onload = function(ev) {
            _justifPratiqueCtx.fichier_base64 = ev.target.result.split(',')[1];
            _justifPratiqueCtx.fichier_nom = file.name;
            document.getElementById('pin-message').textContent = "Code PIN formateur — joindre la grille d'évaluation.";
            document.getElementById('pin-input').value = '';
            document.getElementById('pin-error').style.display = 'none';
            document.getElementById('pin-error').textContent = '';
            document.getElementById('modal-pin').style.display = 'flex';
            document.getElementById('pin-confirm-btn').onclick = async function() {
                var pin = document.getElementById('pin-input').value;
                var tok = localStorage.getItem('token');
                var h = { 'Content-Type': 'application/json' };
                if (tok) h['Authorization'] = 'Bearer ' + tok;
                var ctx = _justifPratiqueCtx;
                var resp;
                try {
                    resp = await fetch(
                        '/api/sessions/' + ctx.sessionId + '/pratique/justificatif/' + ctx.epreuveId,
                        { method: 'POST', headers: h, credentials: 'same-origin',
                          body: JSON.stringify({ pin: pin, fichier_base64: ctx.fichier_base64, fichier_nom: ctx.fichier_nom }) }
                    );
                } catch (err) {
                    document.getElementById('pin-error').textContent = 'Erreur réseau.';
                    document.getElementById('pin-error').style.display = 'block';
                    return;
                }
                if (resp.status === 403) {
                    document.getElementById('pin-error').textContent = 'Code PIN incorrect.';
                    document.getElementById('pin-error').style.display = 'block';
                    return;
                }
                if (!resp.ok) {
                    var errData = await resp.json().catch(function() { return {}; });
                    document.getElementById('pin-error').textContent = errData.detail || 'Erreur ' + resp.status;
                    document.getElementById('pin-error').style.display = 'block';
                    return;
                }
                fermerPin();
                location.reload();
            };
        };
        reader.readAsDataURL(file);
    });
})();

document.addEventListener('click', function(e) {
    if (e.target.closest('[data-action="justif-pratique-voir"]')) {
        var btn = e.target.closest('[data-action="justif-pratique-voir"]');
        window.open('/api/sessions/' + btn.dataset.sessionId + '/pratique/justificatif/' + btn.dataset.epreuveId, '_blank');
        return;
    }
    if (e.target.closest('[data-action="justif-pratique-upload"]')) {
        var btn = e.target.closest('[data-action="justif-pratique-upload"]');
        _justifPratiqueCtx = { sessionId: btn.dataset.sessionId, epreuveId: btn.dataset.epreuveId };
        document.getElementById('justif-pratique-file-input').click();
        return;
    }
});

document.addEventListener('click', function(e) {
    if (e.target.closest('[data-action="justif-voir"]')) {
        var btn = e.target.closest('[data-action="justif-voir"]');
        window.open(
            '/api/sessions/' + btn.dataset.sessionId + '/theorie/justificatif/' + btn.dataset.stagiaireId + '/' + btn.dataset.jourId,
            '_blank'
        );
        return;
    }
    if (e.target.closest('[data-action="justif-upload"]')) {
        var btn = e.target.closest('[data-action="justif-upload"]');
        _justifCtx = { sessionId: btn.dataset.sessionId, stagId: btn.dataset.stagiaireId, jourId: btn.dataset.jourId };
        document.getElementById('justif-file-input').click();
        return;
    }
});

(function() {
    var POLL_MS = 30000;
    var _refSignature = null;
    var _pollStarted = false;

    var MODAL_IDS = ['modal-pin', 'modal-jour-theorie', 'modal-jour-pratique',
        'modal-candidat-jour', 'modal-modifier-jour-theorie', 'modal-pratique',
        'modal-candidat', 'modal-equipement', 'modal-testeurs', 'modal-avert-cloture',
        'modal-choix-test', 'modal-loupe-theorie'];

    function uneModaleOuverte() {
        return MODAL_IDS.some(function(id) {
            var el = document.getElementById(id);
            return el && el.style.display === 'flex';
        });
    }

    function signatureEtat(data) {
        if (!data || !data.candidats) return '';
        return data.candidats.map(function(c) {
            return c.stagiaire_id + ':' + c.theorie + ':' + c.pratique + ':' + c.neutralite;
        }).join('|');
    }

    function verifierEtatLive() {
        if (document.hidden) return;
        if (typeof window.SESSION_ID === 'undefined' || !window.SESSION_ID) return;

        fetch('/api/sessions/' + window.SESSION_ID + '/etat-live', { credentials: 'same-origin' })
            .then(function(r) { if (!r.ok) throw new Error('etat-live ' + r.status); return r.json(); })
            .then(function(data) {
                var sig = signatureEtat(data);

                if (_refSignature === null) {
                    _refSignature = sig;
                    return;
                }

                if (sig === _refSignature) return;

                if (uneModaleOuverte()) {
                    return;
                }

                location.reload();
            })
            .catch(function(e) { console.warn('Suivi live indisponible:', e.message); });
    }

    function demarrerPolling() {
        if (_pollStarted) return;
        _pollStarted = true;
        verifierEtatLive();
        setInterval(verifierEtatLive, POLL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', demarrerPolling);
    } else {
        demarrerPolling();
    }
})();

// ===== Justificatif de dispense (R2) — CSP-safe =====

function _majAffichageJustif(nom) {
    var span = document.getElementById('sc-justif-nom');
    var btnVoir = document.getElementById('sc-justif-btn-voir');
    var btnRetirer = document.getElementById('sc-justif-btn-retirer');
    var msg = document.getElementById('sc-justif-msg');
    if (msg) { msg.textContent = ''; msg.style.color = ''; }
    if (nom) {
        if (span) span.textContent = '📄 ' + nom;
        if (btnVoir) btnVoir.style.display = 'inline-block';
        if (btnRetirer) btnRetirer.style.display = 'inline-block';
    } else {
        if (span) span.textContent = 'Aucun justificatif joint';
        if (btnVoir) btnVoir.style.display = 'none';
        if (btnRetirer) btnRetirer.style.display = 'none';
    }
}

function _justifMsg(texte, couleur) {
    var msg = document.getElementById('sc-justif-msg');
    if (msg) { msg.textContent = texte; msg.style.color = couleur || '#4a5568'; }
}

async function _assurerCandidatEnregistre() {
    var idExistant = document.getElementById('sc-id').value;
    if (idExistant) return idExistant;

    var stagId = parseInt(document.getElementById('sc-stagiaire').value);
    if (!stagId) { _justifMsg('Choisissez d\'abord un stagiaire.', '#cc0000'); return null; }

    var isDispense = document.getElementById('sc-theorie').value === 'dispense';
    var noteEl = document.getElementById('sc-dispense-note');
    var data = {
        session_id: window.SESSION_ID,
        stagiaire_id: stagId,
        theorie_dispensee: isDispense,
        dispense_note: isDispense ? ((noteEl.value || '').trim() || null) : null
    };
    var resp = await fetch('/api/sessions/' + window.SESSION_ID + '/candidats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(data)
    });
    if (!resp.ok) {
        var e = await resp.json().catch(function() { return {}; });
        _justifMsg(e.detail || 'Erreur lors de l\'enregistrement du candidat.', '#cc0000');
        return null;
    }
    var j = await resp.json();
    if (j.id) {
        document.getElementById('sc-id').value = j.id;
        return j.id;
    }
    return null;
}

async function _uploaderJustif(fichier) {
    var scId = await _assurerCandidatEnregistre();
    if (!scId) return;

    var fd = new FormData();
    fichier = await reduireImage(fichier);
    fd.append('fichier', fichier);
    _justifMsg('Envoi en cours…', '#4a5568');
    try {
        var resp = await fetch('/api/sessions/' + window.SESSION_ID + '/candidats/' + scId + '/dispense-fichier', {
            method: 'POST',
            credentials: 'same-origin',
            body: fd
        });
        if (!resp.ok) {
            var e = await resp.json().catch(function() { return {}; });
            _justifMsg(e.detail || 'Erreur lors de l\'envoi.', '#cc0000');
            return;
        }
        var j = await resp.json();
        _majAffichageJustif(j.fichier_nom || fichier.name);
        _justifMsg('Justificatif enregistré.', '#2e7d32');
    } catch (err) {
        _justifMsg('Erreur réseau.', '#cc0000');
    }
}

document.addEventListener('click', function(e) {
    var joindre = e.target.closest('[data-action="sc-justif-joindre"]');
    if (joindre) { document.getElementById('sc-justif-input').click(); return; }

    var voir = e.target.closest('[data-action="sc-justif-voir"]');
    if (voir) {
        var scId = document.getElementById('sc-id').value;
        if (scId) window.open('/api/sessions/' + window.SESSION_ID + '/candidats/' + scId + '/dispense-fichier', '_blank');
        return;
    }

    var retirer = e.target.closest('[data-action="sc-justif-retirer"]');
    if (retirer) {
        var scId2 = document.getElementById('sc-id').value;
        if (!scId2) return;
        fetch('/api/sessions/' + window.SESSION_ID + '/candidats/' + scId2 + '/dispense-fichier', {
            method: 'DELETE',
            credentials: 'same-origin'
        }).then(function(r) {
            if (r.ok) { _majAffichageJustif(''); _justifMsg('Justificatif retiré.', '#2e7d32'); }
            else { _justifMsg('Erreur lors du retrait.', '#cc0000'); }
        }).catch(function() { _justifMsg('Erreur réseau.', '#cc0000'); });
        return;
    }
});

document.addEventListener('change', function(e) {
    if (e.target && e.target.id === 'sc-justif-input') {
        var f = e.target.files && e.target.files[0];
        if (f) _uploaderJustif(f);
        e.target.value = '';
    }
});

function afficherInfoToast(msg) {
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;top:20px;right:24px;background:#4a5568;color:white;padding:12px 20px;border-radius:8px;font-size:14px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.25);transition:opacity .4s;';
    document.body.appendChild(t);
    setTimeout(function() {
        t.style.opacity = '0';
        setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 400);
    }, 1800);
}


// ===== Justificatifs de formation — menu multi-fichiers (chantier table Justificatif) =====
(function() {
  // Recupere le role pour savoir si on affiche le bouton Supprimer (back-office uniquement)
  function _estBackOffice() {
    var el = document.getElementById('session-data');
    if (!el) return false;
    var role = el.getAttribute('data-user-role') || '';
    return role === 'admin' || role === 'utilisateur';
  }

  function _fermerMenuFormation() {
    var ex = document.getElementById('overlay-justif-formation');
    if (ex) ex.remove();
  }

  async function _chargerListeFormation(scId, container) {
    container.innerHTML = '<div style="padding:12px; color:#888;">Chargement…</div>';
    try {
      var resp = await fetch('/api/sessions/' + SESSION_ID + '/justificatifs?type=formation&session_candidat_id=' + scId,
                             { credentials: 'same-origin' });
      if (!resp.ok) { container.innerHTML = '<div style="padding:12px; color:#cc0000;">Erreur de chargement</div>'; return; }
      var liste = await resp.json();
      if (!liste.length) {
        container.innerHTML = '<div style="padding:12px; color:#d98800;">⚠️ Aucun justificatif de formation pour ce candidat.</div>';
        return;
      }
      var html = '';
      var back = _estBackOffice();
      var _peutSuppr = function(j) { return _estBackOffice() || (j.uploade_par_role === 'terrain'); };
      liste.forEach(function(j) {
        var d = j.date_upload ? new Date(j.date_upload).toLocaleDateString('fr-FR') : '';
        html += '<div style="display:flex; align-items:center; gap:8px; padding:8px 12px; border-bottom:1px solid #eee;">'
              + '<span style="flex:1; font-size:13px;">📄 ' + (j.fichier_nom || 'fichier')
              + '<span style="color:#999; font-size:11px;"> · ' + d + (j.uploade_par ? ' · ' + j.uploade_par : '') + '</span></span>'
              + '<button class="btn btn-secondary" style="font-size:11px; padding:2px 8px;" data-action="justif-formation-voir" data-id="' + j.id + '">Voir</button>'
              + (_peutSuppr(j) ? '<button class="btn-suppr-justif" style="border:none; background:transparent; color:#888; cursor:pointer; font-size:14px; padding:2px 6px;" data-action="justif-formation-supprimer" data-id="' + j.id + '" title="Supprimer ce justificatif">🗑️</button>' : '')
              + '</div>';
      });
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = '<div style="padding:12px; color:#cc0000;">Erreur reseau</div>';
    }
  }

  function _ouvrirMenuFormation(scId) {
    _fermerMenuFormation();
    var overlay = document.createElement('div');
    overlay.id = 'overlay-justif-formation';
    overlay.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.4); z-index:9999; display:flex; align-items:center; justify-content:center;';
    overlay.setAttribute('data-sc-id', scId);

    var box = document.createElement('div');
    box.style.cssText = 'background:#fff; border-radius:10px; width:90%; max-width:480px; max-height:80vh; overflow:auto; box-shadow:0 8px 30px rgba(0,0,0,0.3);';
    box.innerHTML =
        '<div style="background:#2d2d2d; color:#fff; padding:12px 16px; border-radius:10px 10px 0 0; display:flex; align-items:center; justify-content:between;">'
      + '<strong style="flex:1;">📋 Justificatifs de formation</strong>'
      + '<span data-action="justif-formation-fermer" title="Fermer" style="cursor:pointer; font-size:22px; line-height:1; padding:0 4px;">&times;</span>'
      + '</div>'
      + '<div id="liste-justif-formation"></div>'
      + '<div style="padding:12px 16px; border-top:1px solid #eee;">'
      + '<button class="btn" style="background:#2d2d2d; color:#fff;" data-action="justif-formation-ajouter">+ Ajouter un fichier</button>'
      + '</div>';
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    _chargerListeFormation(scId, document.getElementById('liste-justif-formation'));
  }

  async function _uploaderFormation(scId, fichier) {
    var fd = new FormData();
    fd.append('type', 'formation');
    fd.append('session_candidat_id', scId);
    fichier = await reduireImage(fichier);
    fd.append('fichier', fichier);
    afficherInfoToast('Envoi en cours…');
    fetch('/api/sessions/' + SESSION_ID + '/justificatifs', { method: 'POST', credentials: 'same-origin', body: fd })
      .then(function(resp) {
        if (!resp.ok) { return resp.json().then(function(d) { throw new Error(d.detail || 'Erreur'); }); }
        return resp.json();
      })
      .then(function() {
        afficherSuccesToast('Justificatif ajoute');
        // recharger la liste de la modale ouverte
        var cont = document.getElementById('liste-justif-formation');
        if (cont) _chargerListeFormation(scId, cont);
        // mettre a jour la pastille FORM. sans recharger la page
        _majPastilleFormation(scId);
      })
      .catch(function(err) { afficherErreur(err.message || 'Erreur upload'); });
  }

  async function _majPastilleFormation(scId) {
    try {
      var resp = await fetch('/api/sessions/' + SESSION_ID + '/justificatifs?type=formation&session_candidat_id=' + scId,
                             { credentials: 'same-origin' });
      if (!resp.ok) return;
      var liste = await resp.json();
      var n = liste.length;
      var pastille = document.querySelector('[data-action="justif-formation-menu"][data-sc-id="' + scId + '"]');
      if (!pastille) return;
      pastille.setAttribute('data-nb', n);
      if (n > 0) {
        pastille.style.background = '#4a5568';
        pastille.style.color = '#fff';
        pastille.textContent = '📋 ' + n;
        pastille.title = n + ' justificatif(s) de formation — cliquer pour voir / ajouter';
      } else {
        pastille.style.background = '#d98800';
        pastille.style.color = '#fff';
        pastille.textContent = '⚠️ Formation';
        pastille.title = 'Aucun justificatif de formation — cliquer pour en ajouter';
      }
    } catch (e) { /* silencieux */ }
  }

  // Listener delegue unique
  document.addEventListener('click', function(e) {
    var open = e.target.closest('[data-action="justif-formation-menu"]');
    if (open) { _ouvrirMenuFormation(open.dataset.scId); return; }

    var fermer = e.target.closest('[data-action="justif-formation-fermer"]');
    if (fermer) { _fermerMenuFormation(); return; }

    // clic sur l'overlay (hors box) ferme
    if (e.target.id === 'overlay-justif-formation') { _fermerMenuFormation(); return; }

    var voir = e.target.closest('[data-action="justif-formation-voir"]');
    if (voir) {
      window.open('/api/sessions/' + SESSION_ID + '/justificatifs/' + voir.dataset.id, '_blank');
      return;
    }

    var ajouter = e.target.closest('[data-action="justif-formation-ajouter"]');
    if (ajouter) {
      var overlay = document.getElementById('overlay-justif-formation');
      var scId = overlay ? overlay.getAttribute('data-sc-id') : null;
      if (!scId) return;
      var input = document.createElement('input');
      input.type = 'file';
      input.accept = '.pdf,.doc,.docx,.xls,.xlsx';
      input.style.display = 'none';
      document.body.appendChild(input);
      input.addEventListener('change', function() {
        if (input.files && input.files[0]) _uploaderFormation(scId, input.files[0]);
        input.remove();
      });
      input.click();
      return;
    }

    var suppr = e.target.closest('[data-action="justif-formation-supprimer"]');
    if (suppr) {
      var overlay2 = document.getElementById('overlay-justif-formation');
      var scId2 = overlay2 ? overlay2.getAttribute('data-sc-id') : null;
      if (!confirm('Supprimer ce justificatif de formation ?')) return;
      fetch('/api/sessions/' + SESSION_ID + '/justificatifs/' + suppr.dataset.id, { method: 'DELETE', credentials: 'same-origin' })
        .then(function(resp) {
          if (!resp.ok) { return resp.json().then(function(d) { throw new Error(d.detail || 'Erreur'); }); }
          afficherSuccesToast('Justificatif supprime');
          if (scId2) { var c = document.getElementById('liste-justif-formation'); if (c) _chargerListeFormation(scId2, c); }
          if (scId2) _majPastilleFormation(scId2);
        })
        .catch(function(err) { afficherErreur(err.message || 'Erreur suppression'); });
      return;
    }
  });
})();

// ===== Onglet Documents de session (type=document_session) =====
(function() {
  function _docEstBackOffice() {
    var el = document.getElementById('session-data');
    if (!el) return false;
    var role = el.getAttribute('data-user-role') || '';
    return role === 'admin' || role === 'utilisateur';
  }

  async function _docChargerListe() {
    var cont = document.getElementById('doc-session-liste');
    if (!cont) return;
    cont.innerHTML = '<div style="color:#888; padding:8px;">Chargement…</div>';
    try {
      var resp = await fetch('/api/sessions/' + SESSION_ID + '/justificatifs?type=document_session',
                             { credentials: 'same-origin' });
      if (!resp.ok) { cont.innerHTML = '<div style="color:#cc0000; padding:8px;">Erreur de chargement</div>'; return; }
      var liste = await resp.json();
      if (!liste.length) {
        cont.innerHTML = '<div style="color:#999; padding:8px; font-style:italic;">Aucun document pour cette session.</div>';
        return;
      }
      var back = _docEstBackOffice();
      var _docPeutSuppr = function(j) { return _docEstBackOffice() || (j.uploade_par_role === 'terrain'); };
      var html = '';
      liste.forEach(function(j) {
        var d = j.date_upload ? new Date(j.date_upload).toLocaleDateString('fr-FR') : '';
        html += '<div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:10px 8px; border-bottom:1px solid #eee;">'
              + '<div style="flex:1 1 200px; min-width:0;">'
              + '<span style="display:inline-block; background:#4a5568; color:#fff; font-size:11px; padding:1px 8px; border-radius:10px; margin-right:6px;">' + (j.libelle ? _docEsc(j.libelle) : 'Document') + '</span>'
              + '<span title="' + _docEsc(j.fichier_nom || 'fichier') + '" style="display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%;">📄 ' + _docEsc(j.fichier_nom || 'fichier') + '</span>'
              + '<div style="color:#999; font-size:11px; margin-top:2px;">' + d + (j.uploade_par ? ' · ' + _docEsc(j.uploade_par) : '') + '</div>'
              + '</div>'
              + '<div style="flex:0 0 auto; display:flex; align-items:center; gap:6px; margin-left:auto;">'
              + '<button class="btn btn-secondary" style="font-size:11px; padding:2px 8px;" data-action="doc-session-voir" data-id="' + j.id + '">Voir</button>'
              + (_docPeutSuppr(j) ? '<button style="border:none; background:transparent; color:#888; cursor:pointer; font-size:14px; padding:2px 6px;" data-action="doc-session-supprimer" data-id="' + j.id + '" title="Supprimer">🗑️</button>' : '')
              + '</div>'
              + '</div>';
      });
      cont.innerHTML = html;
    } catch (e) {
      cont.innerHTML = '<div style="color:#cc0000; padding:8px;">Erreur réseau</div>';
    }
  }

  function _docEsc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  async function _docAjouter() {
    var fileInput = document.getElementById('doc-session-file');
    var libelleInput = document.getElementById('doc-session-libelle');
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
      alert('Sélectionnez un fichier.'); return;
    }
    var libelle = libelleInput ? libelleInput.value.trim() : '';
    var fd = new FormData();
    fd.append('type', 'document_session');
    var fichierDoc = await reduireImage(fileInput.files[0]);
    fd.append('fichier', fichierDoc);
    if (libelle) fd.append('libelle', libelle);
    try {
      var resp = await fetch('/api/sessions/' + SESSION_ID + '/justificatifs', {
        method: 'POST', body: fd, credentials: 'same-origin'
      });
      var data = await resp.json();
      if (!resp.ok) { alert(data.detail || 'Erreur upload'); return; }
      fileInput.value = '';
      if (libelleInput) libelleInput.value = '';
      _docChargerListe();
    } catch (e) {
      alert('Erreur réseau');
    }
  }

  async function _docSupprimer(id) {
    if (!confirm('Supprimer ce document ?')) return;
    try {
      var resp = await fetch('/api/sessions/' + SESSION_ID + '/justificatifs/' + id, {
        method: 'DELETE', credentials: 'same-origin'
      });
      if (!resp.ok) { alert('Erreur suppression'); return; }
      _docChargerListe();
    } catch (e) {
      alert('Erreur réseau');
    }
  }

  document.addEventListener('click', function(e) {
    var tabBtn = e.target.closest('[data-action="show-tab"][data-tab="documents"]');
    if (tabBtn) { _docChargerListe(); return; }

    var puce = e.target.closest('[data-action="doc-nature-puce"]');
    if (puce) {
      var inp = document.getElementById('doc-session-libelle');
      if (inp) { inp.value = puce.dataset.val; inp.focus(); }
      return;
    }

    var act = e.target.closest('[data-action]');
    if (!act) return;
    var action = act.getAttribute('data-action');

    if (action === 'doc-session-ajouter') { _docAjouter(); return; }
    if (action === 'doc-session-voir') {
      window.open('/api/sessions/' + SESSION_ID + '/justificatifs/' + act.getAttribute('data-id'), '_blank');
      return;
    }
    if (action === 'doc-session-supprimer') { _docSupprimer(act.getAttribute('data-id')); return; }
  });
})();

// -- VISIBILITE TERRAIN (oeil de la fiche session) --
(function () {
    function _modal() { return document.getElementById('modal-visibilite'); }
    function ouvrirVisibilite(sessionId) {
        document.getElementById('vis-session-id').value = sessionId;
        var liste = document.getElementById('vis-liste');
        liste.innerHTML = '<p style="color:#888; font-size:13px;">Chargement...</p>';
        _modal().style.display = 'flex';
        fetch('/api/sessions/' + sessionId + '/visibilite')
            .then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.json(); })
            .then(function (personnes) {
                if (!personnes.length) {
                    liste.innerHTML = '<p style="color:#888; font-size:13px;">Aucune personne affectee a cette session.</p>';
                    return;
                }
                liste.innerHTML = '';
                personnes.forEach(function (p) {
                    var row = document.createElement('div');
                    row.style.cssText = 'background:#f5f5f5; border-radius:8px; padding:8px 12px;';
                    var label = document.createElement('label');
                    label.style.cssText = 'display:flex; align-items:center; gap:10px; cursor:pointer; font-size:14px;';
                    var cb = document.createElement('input');
                    cb.type = 'checkbox'; cb.className = 'vis-cb'; cb.value = p.user_id;
                    if (p.visible) cb.checked = true;
                    var span = document.createElement('span');
                    span.style.flex = '1';
                    span.textContent = (p.nom || '') + ' ' + (p.prenom || '');
                    label.appendChild(cb); label.appendChild(span);
                    row.appendChild(label); liste.appendChild(row);
                });
            })
            .catch(function () {
                liste.innerHTML = '<p style="color:#c62828; font-size:13px;">Erreur de chargement.</p>';
            });
    }
    function fermerVisibilite() { _modal().style.display = 'none'; }
    function toutCocher(val) {
        document.querySelectorAll('#vis-liste .vis-cb').forEach(function (cb) { cb.checked = val; });
    }
    function sauvegarderVisibilite() {
        var sessionId = document.getElementById('vis-session-id').value;
        var ids = [];
        document.querySelectorAll('#vis-liste .vis-cb:checked').forEach(function (cb) {
            ids.push(parseInt(cb.value, 10));
        });
        fetch('/api/sessions/' + sessionId + '/visibilite', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_ids: ids })
        })
            .then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.json(); })
            .then(function () { fermerVisibilite(); })
            .catch(function () { alert('Erreur lors de l enregistrement de la visibilite.'); });
    }
    document.addEventListener('click', function (e) {
        var open = e.target.closest('[data-action="ouvrir-visibilite"]');
        if (open) { ouvrirVisibilite(open.dataset.sessionId); return; }
        if (e.target.closest('[data-action="fermer-visibilite"]')) { fermerVisibilite(); return; }
        if (e.target.closest('[data-action="vis-tout-cocher"]')) { toutCocher(true); return; }
        if (e.target.closest('[data-action="vis-tout-decocher"]')) { toutCocher(false); return; }
        if (e.target.closest('[data-action="sauvegarder-visibilite"]')) { sauvegarderVisibilite(); return; }
    });
})();