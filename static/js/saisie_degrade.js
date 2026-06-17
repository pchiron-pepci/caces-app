(function () {
    'use strict';

    var dataEl = document.getElementById('sd-data');
    var SESSION_ID = parseInt(dataEl.dataset.sessionId, 10);
    var JOUR_ID    = parseInt(dataEl.dataset.jourId, 10);

    // Candidat en attente de confirmation PIN
    var _pending = null;  // { stagiaireId, nom, notes }

    // ── Utilitaire auth ───────────────────────────────────────────
    // Renvoie les headers pour fetch : Bearer depuis localStorage (comme
    // l'intercepteur de base.html) + Content-Type. Le cookie access_token
    // (httponly) est envoyé en plus via credentials:'same-origin'.
    function authHeaders() {
        var h = { 'Content-Type': 'application/json' };
        var tok = localStorage.getItem('token');
        if (tok) h['Authorization'] = 'Bearer ' + tok;
        return h;
    }

    // ── Modal PIN ─────────────────────────────────────────────────
    function ouvrirPin(stagiaireId, nom, notes) {
        _pending = { stagiaireId: stagiaireId, nom: nom, notes: notes, action: 'enregistrer' };
        document.getElementById('pin-message').innerHTML = 'Confirmez la saisie pour <strong>' + nom + '</strong>';
        document.getElementById('pin-input').value      = '';
        document.getElementById('pin-error').style.display = 'none';
        document.getElementById('pin-error').textContent   = '';
        document.getElementById('modal-pin').style.display = 'flex';
        setTimeout(function () { document.getElementById('pin-input').focus(); }, 50);
    }

    function ouvrirPinSupprimer(stagiaireId, nom) {
        _pending = { stagiaireId: stagiaireId, nom: nom, action: 'supprimer' };
        document.getElementById('pin-message').innerHTML = 'Supprimer définitivement le résultat de <strong>' + nom + '</strong>&nbsp;?';
        document.getElementById('pin-input').value      = '';
        document.getElementById('pin-error').style.display = 'none';
        document.getElementById('pin-error').textContent   = '';
        document.getElementById('modal-pin').style.display = 'flex';
        setTimeout(function () { document.getElementById('pin-input').focus(); }, 50);
    }

    function fermerPin() {
        document.getElementById('modal-pin').style.display = 'none';
        _pending = null;
    }

    function afficherErreurPin(msg) {
        var el = document.getElementById('pin-error');
        el.textContent   = msg;
        el.style.display = '';
    }

    // ── Collecte + validation des saisies ─────────────────────────
    function collecterNotes(stagiaireId) {
        var inputs = document.querySelectorAll('#form-' + stagiaireId + ' .theme-input');
        var notes  = {};
        var ok     = true;
        inputs.forEach(function (inp) {
            // id : "t{num}-{stagiaireId}"
            var tNum = inp.id.split('-')[0].slice(1);
            var val  = inp.value.trim();
            // Rejeter UNIQUEMENT les champs vides ou non numériques.
            // 0 est une valeur valide (thème entièrement raté) : tester val===''
            // et Number.isNaN, jamais !val ni !note (0 est falsy en JS).
            if (val === '' || Number.isNaN(parseInt(val, 10))) {
                inp.style.borderColor = '#c62828';
                ok = false;
            } else {
                inp.style.borderColor = '';
                notes[tNum] = parseInt(val, 10);
            }
        });
        return ok ? notes : null;
    }

    // ── Rendu résultat après enregistrement ───────────────────────
    // Lit uniquement les champs du résultat API — zéro navigation DOM fragile.
    function afficherResultat(stagiaireId, resultat) {
        var zone = document.getElementById('result-zone-' + stagiaireId);
        if (!zone) return;

        var html   = '';
        var themes = Object.keys(resultat.notes_themes).sort();
        themes.forEach(function (tStr) {
            var noteTheme = resultat.notes_themes[tStr];
            var maxTheme  = resultat.max_themes[tStr];
            var themeOk   = resultat.themes_ok[tStr];
            html += '<div class="result-row">'
                + '<span class="badge ' + (themeOk ? 'badge-green' : 'badge-red') + '">T' + tStr + '</span>'
                + '<span style="font-size:13px; color:#333; margin-left:4px;">Thème ' + tStr + '</span>'
                + '<span style="margin-left:auto; font-weight:700;">'
                + Math.round(noteTheme) + '/' + Math.round(maxTheme)
                + '</span>'
                + '</div>';
        });
        var obtenue = resultat.obtenue;
        var total   = Math.round(resultat.note_totale);
        html += '<div class="result-row" style="margin-top:6px; border-top:1px solid #eee; padding-top:8px;">'
            + '<span class="result-total">Total : ' + total + '/100</span>'
            + '<span style="margin-left:8px;">'
            + '<span class="badge ' + (obtenue ? 'badge-green' : 'badge-red') + '">'
            + (obtenue ? 'RÉUSSI' : 'ÉCHEC') + '</span>'
            + '</span></div>';

        zone.innerHTML = html;
        zone.style.display = '';

        // Mise à jour du badge statut dans l'en-tête de la carte
        var statusEl = document.querySelector('#cand-' + stagiaireId + ' .cand-head div:last-child');
        if (statusEl) {
            statusEl.innerHTML = '<span class="badge badge-orange">Saisie papier</span> '
                + '<span class="badge ' + (obtenue ? 'badge-green' : 'badge-red') + '">'
                + (obtenue ? 'RÉUSSI' : 'ÉCHEC') + '</span>';
        }
    }

    // ── Suppression d'un résultat dégradé (back-office uniquement) ───────────
    async function supprimerDegrade(pin) {
        if (!_pending) return;
        var stagId = _pending.stagiaireId;
        var resp;
        try {
            resp = await fetch(
                '/api/sessions/' + SESSION_ID + '/theorie/reponses/' + stagId + '/' + JOUR_ID,
                {
                    method:      'DELETE',
                    headers:     authHeaders(),
                    body:        JSON.stringify({ pin: pin }),
                    credentials: 'same-origin',
                }
            );
        } catch (err) {
            afficherErreurPin('Erreur réseau — vérifiez votre connexion.');
            return;
        }
        if (resp.status === 403) {
            var err403 = await resp.json().catch(function () { return {}; });
            afficherErreurPin(err403.detail || 'Code PIN incorrect.');
            return;
        }
        if (!resp.ok) {
            var errData = await resp.json().catch(function () { return {}; });
            afficherErreurPin('Erreur ' + resp.status + ' : ' + (errData.detail || 'Erreur serveur.'));
            return;
        }
        fermerPin();
        location.reload();
    }

    // ── Appel API ─────────────────────────────────────────────────
    async function soumettre(pin) {
        if (!_pending) return;
        var body = {
            jour_test_id:    JOUR_ID,
            stagiaire_id:    _pending.stagiaireId,
            pin:             pin,
            notes_par_theme: _pending.notes,
        };
        var resp;
        try {
            resp = await fetch(
                '/api/sessions/' + SESSION_ID + '/theorie/reponses-degrade',
                {
                    method:      'POST',
                    headers:     authHeaders(),
                    body:        JSON.stringify(body),
                    credentials: 'same-origin',
                }
            );
        } catch (err) {
            afficherErreurPin('Erreur réseau — vérifiez votre connexion.');
            return;
        }

        if (resp.status === 403) {
            // PIN incorrect ou session clôturée — la modal reste ouverte
            var err403 = await resp.json().catch(function () { return {}; });
            afficherErreurPin(err403.detail || 'Code PIN incorrect.');
            return;
        }

        if (!resp.ok) {
            var errData = await resp.json().catch(function () { return {}; });
            afficherErreurPin('Erreur ' + resp.status + ' : ' + (errData.detail || 'Erreur serveur.'));
            return;
        }

        var data   = await resp.json();
        var stagId = _pending.stagiaireId;
        fermerPin();
        afficherResultat(stagId, data.resultat);
    }

    // ── Listeners ─────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-action="enregistrer-degrade"]');
        if (btn) {
            var stagId = parseInt(btn.dataset.stagiaireId, 10);
            var nom    = btn.dataset.nom;
            var notes  = collecterNotes(stagId);
            if (!notes) return;
            ouvrirPin(stagId, nom, notes);
            return;
        }
        var btnSupp = e.target.closest('[data-action="supprimer-degrade"]');
        if (btnSupp) {
            var stagId = parseInt(btnSupp.dataset.stagiaireId, 10);
            var nom    = btnSupp.dataset.nom;
            ouvrirPinSupprimer(stagId, nom);
            return;
        }
        if (e.target.closest('[data-action="pin-confirmer"]')) {
            var pin = document.getElementById('pin-input').value;
            if (_pending && _pending.action === 'supprimer') {
                supprimerDegrade(pin);
            } else {
                soumettre(pin);
            }
            return;
        }
        if (e.target.closest('[data-action="pin-annuler"]')) {
            fermerPin();
            return;
        }
    });

    document.getElementById('pin-input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            var pin = this.value;
            if (_pending && _pending.action === 'supprimer') {
                supprimerDegrade(pin);
            } else {
                soumettre(pin);
            }
        }
    });

}());
