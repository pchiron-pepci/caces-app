document.addEventListener('DOMContentLoaded', function () {

    // ── Recherche + filtre inactifs ────────────────────────────────────────
    function filtrer() {
        var q = ((document.getElementById('search') || {}).value || '').toLowerCase();
        var showInactifs = !!(document.getElementById('chk-inactifs') || {}).checked;
        var lbl = document.getElementById('lbl-inactifs');
        if (lbl) {
            lbl.style.background = showInactifs ? '#e3f2fd' : '#f0f2f7';
            lbl.style.borderColor = showInactifs ? '#1565c0' : '#c8d8f0';
        }
        document.querySelectorAll('#tbody tr:not(.hist-row)').forEach(function (tr) {
            var sid = tr.dataset.stagiaireId;
            if (tr.dataset.inactif && !showInactifs) {
                tr.style.display = 'none';
                if (sid) { var h = document.getElementById('hist-' + sid); if (h) h.style.display = 'none'; }
                return;
            }
            var visible = tr.textContent.toLowerCase().includes(q);
            tr.style.display = visible ? '' : 'none';
            if (sid) { var h = document.getElementById('hist-' + sid); if (h && !visible) h.style.display = 'none'; }
        });
    }

    var searchInput = document.getElementById('search');
    if (searchInput) searchInput.addEventListener('input', filtrer);
    var chkInactifs = document.getElementById('chk-inactifs');
    if (chkInactifs) chkInactifs.addEventListener('change', filtrer);
    filtrer();

    // ── Tri colonnes ──────────────────────────────────────────────────────
    let sortColIdx = null;
    let sortAsc = true;

    document.querySelectorAll('th[data-sort-col]').forEach(function (th) {
        th.addEventListener('click', function () {
            const colIdx = parseInt(this.dataset.sortCol);
            if (sortColIdx === colIdx) { sortAsc = !sortAsc; } else { sortColIdx = colIdx; sortAsc = true; }
            document.querySelectorAll('.sort-arrow-col').forEach(function (el) { el.textContent = ''; });
            const arrowEl = document.getElementById('arrow-col-' + colIdx);
            if (arrowEl) arrowEl.textContent = sortAsc ? ' ↑' : ' ↓';
            const tbody = document.getElementById('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr:not(.hist-row)'));
            rows.sort(function (a, b) {
                const cell_a = a.cells[colIdx];
                const cell_b = b.cells[colIdx];
                const va = (cell_a.dataset.date || cell_a.textContent.trim()).toLowerCase();
                const vb = (cell_b.dataset.date || cell_b.textContent.trim()).toLowerCase();
                return sortAsc ? (va < vb ? -1 : va > vb ? 1 : 0) : (va < vb ? 1 : va > vb ? -1 : 0);
            });
            rows.forEach(function (row) {
                tbody.appendChild(row);
                const sid = row.dataset.stagiaireId;
                if (sid) {
                    const histRow = document.getElementById('hist-' + sid);
                    if (histRow) tbody.appendChild(histRow);
                }
            });
        });
    });

    // ── Preview photo ──────────────────────────────────────────────────────
    const photoInput = document.getElementById('f-photo');
    if (photoInput) {
        photoInput.addEventListener('change', function () {
            const file = this.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function (e) {
                const preview = document.getElementById('f-photo-preview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    // ── Event delegation ──────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        if (action === 'nouveau-stagiaire') ouvrirFormulaire();
        else if (action === 'editer') ouvrirEdition(btn);
        else if (action === 'archiver') archiver(btn.dataset.id, btn.dataset.nom);
        else if (action === 'historique') toggleHistorique(btn.dataset.id, btn);
        else if (action === 'sauvegarder') sauvegarder();
        else if (action === 'fermer-modal') fermerModal();
        else if (action === 'confirmer-archivage') confirmerArchivage();
        else if (action === 'fermer-pin') fermerPin();
        else if (action === 'toggle-session') {
            if (e.target.closest('a')) return;
            const sid = btn.dataset.id;
            const detail = document.getElementById('session-detail-' + sid);
            const arrow  = document.getElementById('session-arrow-' + sid);
            if (!detail) return;
            const open = detail.style.display !== 'none';
            detail.style.display = open ? 'none' : 'block';
            if (arrow) arrow.textContent = open ? '▶' : '▼';
        }
        else if (action === 'ajouter-reprise') { ouvrirModalReprise(btn.dataset.id); return; }
        else if (action === 'ajouter-caces-externe') { ouvrirModalCacesExterne(btn.dataset.id); return; }
        else if (action === 'modifier-caces-externe') {
            try { var _e = JSON.parse(btn.getAttribute('data-ext')); ouvrirModalModifExterne(btn.dataset.stag, _e); } catch (e) {}
            return;
        }
        else if (action === 'fermer-modal-caces-externe') { document.getElementById('modal-caces-externe').style.display = 'none'; return; }
        else if (action === 'confirmer-caces-externe') { confirmerCacesExterne(); return; }
        else if (action === 'suppr-caces-externe') { supprimerCacesExterne(btn.dataset.id, btn.dataset.stag); return; }
        else if (action === 'fermer-modal-reprise') { document.getElementById('modal-reprise').style.display = 'none'; return; }
        else if (action === 'confirmer-ajout-reprise') { confirmerAjoutReprise(); return; }
        else if (action === 'joindre-justif-reprise') {
            joindreJustifReprise(btn.dataset.stag, btn.dataset.id, btn.dataset.aFichier === '1', btn.dataset.nomFichier || '');
            return;
        }
        else if (action === 'fermer-justif-reprise') { document.getElementById('modal-justif-reprise').style.display = 'none'; return; }
        else if (action === 'justif-reprise-envoyer') { _justifReprEnvoyer(); return; }
        else if (action === 'justif-reprise-supprimer') { _justifReprSupprimer(); return; }
        else if (action === 'modifier-reprise-caces') {
            try { var _r = JSON.parse(btn.getAttribute('data-reprise')); ouvrirModalModifReprise(btn.dataset.stag, _r); } catch (e) {}
            return;
        }
        else if (action === 'ajouter-orpheline') { ouvrirModalOrpheline(btn.dataset.id); return; }
        else if (action === 'fermer-modal-orpheline') { document.getElementById('modal-orpheline').style.display = 'none'; return; }
        else if (action === 'orph-type-theorie') { orphChoisirType('theorie'); return; }
        else if (action === 'orph-type-pratique') { orphChoisirType('pratique'); return; }
        else if (action === 'orph-retour') { orphRetourChoix(); return; }
        else if (action === 'confirmer-ajout-orpheline') { confirmerAjoutOrpheline(); return; }
        else if (action === 'toggle-historique-reprise') {
            var rid = btn.dataset.id;
            var rbody = document.getElementById('hist-reprise-body-' + rid);
            var rarrow = document.getElementById('hist-reprise-arrow-' + rid);
            if (rbody) {
                var open = rbody.style.display !== 'none';
                rbody.style.display = open ? 'none' : 'block';
                if (rarrow) rarrow.textContent = open ? '▶' : '▼';
            }
            return;
        }
        else if (action === 'toggle-caces-carte') {
            const carteId = btn.dataset.carteId;
            const detail = document.getElementById('stag-caces-detail-' + carteId);
            if (!detail) return;
            const isOpen = detail.style.display !== 'none';
            if (isOpen) {
                detail.style.display = 'none';
                btn.textContent = '▶';
            } else {
                detail.style.display = 'block';
                btn.textContent = '▼';
                if (btn.dataset.loaded === '0') {
                    btn.dataset.loaded = '1';
                    chargerCacesCarteStag(carteId, detail);
                }
            }
        }
        else if (action === 'ouvrir-suppr-reprise') {
            window._supprReprise = { type: btn.dataset.type, id: btn.dataset.id, stag: btn.dataset.stag };
            document.getElementById('suppr-reprise-pin').value = '';
            var errDiv = document.getElementById('suppr-reprise-error');
            if (errDiv) { errDiv.style.display = 'none'; errDiv.textContent = ''; }
            document.getElementById('modal-suppr-reprise').style.display = 'flex';
            return;
        }
        else if (action === 'suppr-reprise-annuler') {
            document.getElementById('modal-suppr-reprise').style.display = 'none';
            return;
        }
        else if (action === 'suppr-reprise-confirmer') {
            var sr = window._supprReprise;
            if (!sr) return;
            var pin = document.getElementById('suppr-reprise-pin').value;
            var errDiv2 = document.getElementById('suppr-reprise-error');
            fetch('/stagiaires/' + sr.stag + '/reprises/' + sr.type + '/' + sr.id + '/supprimer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pin: pin })
            }).then(function(resp) {
                if (resp.ok) {
                    document.getElementById('modal-suppr-reprise').style.display = 'none';
                    location.reload();
                } else {
                    resp.json().then(function(d) {
                        if (errDiv2) { errDiv2.textContent = d.detail || 'Erreur'; errDiv2.style.display = 'block'; }
                    }).catch(function() {
                        if (errDiv2) { errDiv2.textContent = 'Erreur inconnue'; errDiv2.style.display = 'block'; }
                    });
                }
            });
            return;
        }
    });

    // ── Modals ────────────────────────────────────────────────────────────
    function resetForm() {
        document.getElementById('stagiaire-id').value = '';
        document.getElementById('f-nom').value = '';
        document.getElementById('f-prenom').value = '';
        document.getElementById('f-ddn').value = '';
        document.getElementById('f-employeur').value = '';
        document.getElementById('f-email').value = '';
        document.getElementById('f-tel').value = '';
        document.getElementById('f-note').value = '';
        document.getElementById('f-photo').value = '';
        document.getElementById('f-photo-preview').style.display = 'none';
    }

    function ouvrirFormulaire() {
        document.getElementById('modal-title').textContent = 'Nouveau stagiaire';
        resetForm();
        document.getElementById('modal').style.display = 'flex';
    }

    function ouvrirEdition(btn) {
        document.getElementById('modal-title').textContent = 'Modifier stagiaire';
        resetForm();
        document.getElementById('stagiaire-id').value = btn.dataset.id;
        document.getElementById('f-nom').value = btn.dataset.nom;
        document.getElementById('f-prenom').value = btn.dataset.prenom;
        document.getElementById('f-ddn').value = btn.dataset.ddn;
        document.getElementById('f-email').value = btn.dataset.email;
        document.getElementById('f-tel').value = btn.dataset.tel;
        document.getElementById('f-employeur').value = btn.dataset.employeur;
        document.getElementById('f-note').value = btn.dataset.note;
        document.getElementById('modal').style.display = 'flex';
    }

    function fermerModal() {
        document.getElementById('modal').style.display = 'none';
    }

    async function sauvegarder() {
        const id = document.getElementById('stagiaire-id').value;
        const data = {
            nom: document.getElementById('f-nom').value.toUpperCase(),
            prenom: document.getElementById('f-prenom').value,
            date_naissance: document.getElementById('f-ddn').value,
            email: document.getElementById('f-email').value || null,
            telephone: document.getElementById('f-tel').value || null,
            employeur: document.getElementById('f-employeur').value || null,
            note: document.getElementById('f-note').value || null
        };
        if (!data.nom || !data.prenom || !data.date_naissance) {
            alert('Nom, prénom et date de naissance sont obligatoires !');
            return;
        }
        const url = id ? '/stagiaires/' + id : '/stagiaires/';
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (resp.ok) {
            const stagiaire = await resp.json();
            const photoFile = document.getElementById('f-photo').files[0];
            if (photoFile) {
                const formData = new FormData();
                formData.append('file', photoFile);
                await fetch('/stagiaires/photo/' + stagiaire.id, { method: 'POST', body: formData });
            }
            fermerModal();
            location.reload();
        } else {
            alert('Erreur lors de la sauvegarde !');
        }
    }

    // ── Archivage ─────────────────────────────────────────────────────────
    let idAArchiver = null;

    function archiver(id, nom) {
        idAArchiver = id;
        document.getElementById('pin-message').textContent = 'Supprimer définitivement "' + nom + '" ?';
        document.getElementById('pin-input').value = '';
        const errEl = document.getElementById('pin-error');
        errEl.textContent = '';
        errEl.style.display = 'none';
        document.getElementById('modal-pin').style.display = 'flex';
    }

    function fermerPin() {
        document.getElementById('modal-pin').style.display = 'none';
        idAArchiver = null;
    }

    async function confirmerArchivage() {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch('/stagiaires/' + idAArchiver + '?pin=' + encodeURIComponent(pin), { method: 'DELETE' });
        if (resp.ok) {
            fermerPin();
            location.reload();
        } else {
            const errEl = document.getElementById('pin-error');
            try {
                const d = await resp.json();
                errEl.textContent = '❌ ' + (d.detail || 'Erreur inconnue');
            } catch (_) {
                errEl.textContent = resp.status === 403 ? '❌ Code PIN incorrect !' : '❌ Erreur lors de la suppression.';
            }
            errEl.style.display = 'block';
        }
    }

    // ── Historique stagiaire ───────────────────────────────────────────────
    async function toggleHistorique(id, btn) {
        const row = document.getElementById('hist-' + id);
        const body = document.getElementById('hist-body-' + id);

        if (row.style.display !== 'none') {
            row.style.display = 'none';
            if (btn) btn.textContent = '▶';
            return;
        }

        row.style.display = '';
        if (btn) btn.textContent = '▼';

        if (body.dataset.loaded) return;

        body.innerHTML = '<em style="color:#888;">Chargement...</em>';
        try {
            const [rHisto, rCaces, rCartes, rReprises, rOrph] = await Promise.all([
                fetch('/stagiaires/' + id + '/historique'),
                fetch('/stagiaires/' + id + '/caces-valides'),
                fetch('/stagiaires/' + id + '/cartes-emises'),
                fetch('/stagiaires/' + id + '/reprises'),
                fetch('/stagiaires/' + id + '/reprises/orphelines'),
            ]);
            if (!rHisto.ok || !rCaces.ok || !rCartes.ok || !rReprises.ok || !rOrph.ok) throw new Error();
            const [sessions, caces, cartes, reprises, orphelines] = await Promise.all([rHisto.json(), rCaces.json(), rCartes.json(), rReprises.json(), rOrph.json()]);
            body.innerHTML = renderHistorique(sessions) + renderCacesValides(caces) + renderCartesEmises(cartes) + renderHistoriqueDeReprise(reprises, orphelines, id);
            body.dataset.loaded = '1';
        } catch (_) {
            body.innerHTML = '<em style="color:red;">Erreur de chargement.</em>';
        }
    }

    function renderHistorique(data) {
        if (!data.length) return '<p style="color:#888; margin:8px 0;">Aucune session enregistrée.</p>';

        const STATUT_BADGE = {
            planifiee: 'background:#e3f2fd; color:#1565c0;',
            en_cours: 'background:#fff3e0; color:#e65100;',
            terminee: 'background:#e8f5e9; color:#2e7d32;',
            annulee: 'background:#fce4ec; color:#c62828;'
        };
        const STATUT_LABEL = { planifiee: 'Planifiée', en_cours: 'En cours', terminee: 'Terminée', annulee: 'Annulée' };

        let html = '<div style="display:flex; flex-direction:column; gap:6px; padding:4px 0;">';
        data.forEach(function (s) {
            const badgeStyle = STATUT_BADGE[s.statut] || 'background:#f5f5f5; color:#666;';
            const badgeLabel = STATUT_LABEL[s.statut] || s.statut;

            let dates = [];
            if (s.date_theorie) dates.push(formatDate(s.date_theorie));
            if (s.date_pratique_debut) {
                let prat = formatDate(s.date_pratique_debut);
                if (s.date_pratique_fin && s.date_pratique_fin !== s.date_pratique_debut) {
                    prat += ' → ' + formatDate(s.date_pratique_fin);
                }
                dates.push(prat);
            }

            let theorieHtml = '<span style="color:#bbb;">—</span>';
            if (s.theorie) {
                if (s.theorie.statut === 'obtenu') {
                    const note = s.theorie.note !== null ? ' (' + s.theorie.note + '%)' : '';
                    theorieHtml = '<span style="color:#2e7d32; font-weight:700;">✅ Obtenu' + note + '</span>';
                } else if (s.theorie.statut === 'non_obtenu') {
                    const note = s.theorie.note !== null ? ' (' + s.theorie.note + '%)' : '';
                    theorieHtml = '<span style="color:#c62828; font-weight:700;">❌ Non obtenu' + note + '</span>';
                } else {
                    theorieHtml = '<span style="color:#888; font-style:italic;">Planifié</span>';
                }
            }

            let pratiqueHtml = '<span style="color:#bbb;">—</span>';
            if (s.pratique.length) {
                pratiqueHtml = s.pratique.map(function (p) {
                    let bg, icon, extra = '';
                    if (p.statut === 'obtenu') {
                        bg = 'background:#e8f5e9; color:#2e7d32;';
                        icon = '✅ ';
                        if (p.options) extra = ' <span style="color:#2e7d32; font-weight:700; font-size:10px;">' + p.options + '</span>';
                    } else if (p.statut === 'non_obtenu') {
                        bg = 'background:#fce4ec; color:#c62828;';
                        icon = '❌ ';
                    } else {
                        bg = 'background:#f5f5f5; color:#888;';
                        icon = '';
                        extra = ' <em style="font-size:10px;">planifié</em>';
                    }
                    return '<span style="' + bg + ' display:inline-flex; align-items:center; gap:3px; padding:2px 7px; border-radius:6px; font-size:12px; margin:2px;">' + icon + p.categorie + extra + '</span>';
                }).join('');
            }

            // En-tête cliquable (repliée par défaut)
            html += '<div style="border:1px solid #e0e0e0; border-radius:8px; overflow:hidden; background:white;">';
            html += '<div data-action="toggle-session" data-id="' + s.session_id + '" '
                + 'style="display:flex; align-items:center; gap:8px; padding:9px 14px; cursor:pointer; flex-wrap:wrap; user-select:none;">';
            html += '<span id="session-arrow-' + s.session_id + '" style="font-size:10px; color:#999; flex-shrink:0;">▶</span>';
            html += '<a href="/sessions/' + s.session_id + '" style="font-family:\'Barlow Condensed\',sans-serif; font-size:15px; font-weight:700; text-decoration:none; color:#1a3a8f;">' + s.reference + '</a>';
            html += '<span style="font-size:13px; color:#555; font-weight:600;">' + s.famille + '</span>';
            html += '<span style="' + badgeStyle + ' padding:2px 8px; border-radius:8px; font-size:11px; font-weight:600;">' + badgeLabel + '</span>';
            if (dates.length) html += '<span class="sess-dates" style="font-size:11px; color:#888; margin-left:auto;">' + dates.join(' · ') + '</span>';
            html += '</div>';

            // Corps repliable (caché par défaut)
            html += '<div id="session-detail-' + s.session_id + '" style="display:none; border-top:1px solid #f0f0f0; padding:8px 14px 10px; font-size:13px; display:none; flex-direction:column; gap:3px;">';
            html += '<div><span style="color:#666; display:inline-block; width:68px;">Théorie :</span>' + theorieHtml + '</div>';
            html += '<div><span style="color:#666; display:inline-block; width:68px;">Pratique :</span>' + pratiqueHtml + '</div>';
            html += '</div>';

            html += '</div>';
        });
        html += '</div>';
        return html;
    }

    function renderCacesValides(caces) {
        let html = '<div style="margin-top:16px;">';
        html += '<div style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px;">🏆 CACES® de l\'apprenant</div>';

        if (!caces || !caces.length) {
            html += '<p style="color:#bbb;font-size:13px;font-style:italic;margin:0;">Aucun CACES®.</p></div>';
            return html;
        }

        var otc = caces.filter(function (c) { return !c.organisme_externe; });
        var st  = caces.filter(function (c) { return c.organisme_externe && c.sous_traitance; });
        var ext = caces.filter(function (c) { return c.organisme_externe && !c.sous_traitance; });

        html += _sectionCaces('CACES de l\'organisme', otc, false);
        html += _sectionCaces('CACES externes — sous-traitance', st, true);
        html += _sectionCaces('CACES externes', ext, true);

        html += '</div>';
        return html;
    }

    // colExterne = true -> derniere colonne = organisme emetteur (au lieu du testeur)
    function _sectionCaces(titre, liste, colExterne) {
        if (!liste || !liste.length) return '';
        var derColLabel = colExterne ? 'Organisme' : 'Testeur';
        var html = '<div style="margin-top:14px;">';
        html += '<div style="font-size:11px;font-weight:700;color:#5566aa;letter-spacing:0.4px;margin-bottom:6px;padding-top:8px;border-top:2px solid #e6e8ef;">' + titre + '</div>';
        html += '<div class="co-hscroll"><div style="border:1px solid #c8d8f0;border-radius:10px;overflow:hidden;">';
        html += '<div class="csec-head-row" style="display:flex;align-items:center;background:#f0f2f7;border-bottom:1px solid #dde3f0;padding:7px 12px;">';
        html += '<div style="width:60px;min-width:60px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">N°</div>';
        html += '<div style="width:70px;min-width:70px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Fam.</div>';
        html += '<div style="width:52px;min-width:52px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Cat.</div>';
        html += '<div style="width:80px;min-width:80px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Options</div>';
        html += '<div style="width:160px;min-width:160px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">' + derColLabel + '</div>';
        html += '<div style="width:84px;min-width:84px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Obtention</div>';
        html += '<div style="width:84px;min-width:84px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Échéance</div>';
        html += '<div style="flex:1;"></div>';
        html += '</div>';

        liste.forEach(function (co, i) {
            var bg = i % 2 === 0 ? '#fff' : '#f5f7ff';
            var noFormate;
            if (colExterne) {
                noFormate = co.sous_traitance ? 'S/T' : 'EXT';
            } else {
                noFormate = co.ancien_numero ? co.ancien_numero : (co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—');
            }
            var noBg = colExterne ? (co.sous_traitance ? '#0f6e56' : '#5f5e5a') : '#1a237e';
            var options = co.options_obtenues
                ? co.options_obtenues.split(',').map(function (o) {
                    return '<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:0 4px;font-size:10px;font-weight:700;">' + o.trim() + '</span>';
                  }).join(' ')
                : '<span style="color:#ccc;font-size:11px;">—</span>';
            var derCol = colExterne
                ? '<span style="color:#00695c;font-weight:700;">' + (co.organisme_externe || '—') + '</span>'
                : (co.testeur_nom || '<span style="color:#ccc;">—</span>');

            html += '<div class="csec-row" style="display:flex;align-items:center;padding:8px 12px;background:' + bg + ';border-bottom:1px solid #eef0f6;">';
            html += '<div class="csec-no" style="width:60px;min-width:60px;"><span style="background:' + noBg + ';color:#fff;border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700;font-family:monospace;">' + noFormate + '</span></div>';
            html += '<div class="csec-fam" style="width:70px;min-width:70px;font-size:12px;font-weight:700;color:#555;">' + co.famille + '</div>';
            html += '<div class="csec-cat" style="width:52px;min-width:52px;"><span style="background:#1a237e;color:#fff;border-radius:4px;padding:0 6px;font-size:11px;font-weight:800;">' + co.categorie + '</span></div>';
            html += '<div class="csec-opt" style="width:80px;min-width:80px;display:flex;flex-wrap:wrap;gap:2px;align-items:center;">' + options + '</div>';
            html += '<div class="csec-der" data-label="' + derColLabel + '" style="width:160px;min-width:160px;font-size:12px;color:#555;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:6px;">' + derCol + '</div>';
            html += '<div class="csec-obt" data-label="Obtention" style="width:84px;min-width:84px;font-size:12px;font-weight:700;color:#1a237e;">' + formatDate(co.date_obtention) + '</div>';
            html += '<div class="csec-ech" data-label="Échéance" style="width:84px;min-width:84px;font-size:12px;font-weight:700;color:#2e7d32;">' + formatDate(co.date_echeance) + '</div>';
            html += '<div style="flex:1;"></div>';
            html += '</div>';
        });

        html += '</div></div></div>';
        return html;
    }

    function renderHistoriqueDeReprise(reprises, orphelines, stagiaireId) {
        var contenu = renderReprisesHistorique(reprises, stagiaireId) + renderCacesExternes(reprises, stagiaireId) + renderOrphelinesReprises(orphelines, stagiaireId);
        return '<div style="margin-top:16px;border-top:2px solid #e0e0e0;padding-top:10px;">'
            + '<div data-action="toggle-historique-reprise" data-id="' + stagiaireId + '" style="display:flex;align-items:center;gap:8px;cursor:pointer;user-select:none;">'
            + '<span id="hist-reprise-arrow-' + stagiaireId + '" style="color:#2d2d2d;font-size:12px;">▶</span>'
            + '<strong style="color:#2d2d2d;font-size:14px;">🗂️ Historique de reprise</strong>'
            + '</div>'
            + '<div id="hist-reprise-body-' + stagiaireId + '" style="display:none;padding-left:4px;">'
            + contenu
            + '</div>'
            + '</div>';
    }

    var _justifRepr = { stag: null, co: null, aFichier: false };

    function joindreJustifReprise(stagiaireId, coId, aFichier, nomFichier) {
        _justifRepr = { stag: stagiaireId, co: coId, aFichier: !!aFichier };
        document.getElementById('justif-reprise-fichier').value = '';
        document.getElementById('justif-reprise-pin').value = '';
        var err = document.getElementById('justif-reprise-error');
        err.style.display = 'none'; err.textContent = '';
        var actuel = document.getElementById('justif-reprise-actuel');
        var btnSuppr = document.getElementById('justif-reprise-btn-suppr');
        if (aFichier) {
            actuel.innerHTML = 'Fichier actuel : <strong>' + (nomFichier || 'justificatif') + '</strong>. Choisissez un nouveau fichier pour le remplacer, ou supprimez-le.';
            btnSuppr.style.display = 'inline-block';
        } else {
            actuel.textContent = "Aucun justificatif joint pour l'instant.";
            btnSuppr.style.display = 'none';
        }
        document.getElementById('modal-justif-reprise').style.display = 'flex';
    }

    function _justifReprEnvoyer() {
        var err = document.getElementById('justif-reprise-error');
        var f = document.getElementById('justif-reprise-fichier').files[0];
        var pin = document.getElementById('justif-reprise-pin').value;
        if (!f) { err.textContent = 'Choisissez un fichier.'; err.style.display = 'block'; return; }
        if (!pin) { err.textContent = 'Code PIN requis.'; err.style.display = 'block'; return; }
        var fd = new FormData();
        fd.append('fichier', f); fd.append('pin', pin);
        fetch('/stagiaires/' + _justifRepr.stag + '/reprises/caces/' + _justifRepr.co + '/justificatif', {
            method: 'POST', credentials: 'same-origin', body: fd
        }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
              if (!res.ok) { err.textContent = res.data.detail || 'Erreur'; err.style.display = 'block'; return; }
              document.getElementById('modal-justif-reprise').style.display = 'none';
              _rechargerHistoStag(_justifRepr.stag);
          }).catch(function () { err.textContent = 'Erreur reseau'; err.style.display = 'block'; });
    }

    function _justifReprSupprimer() {
        var err = document.getElementById('justif-reprise-error');
        var pin = document.getElementById('justif-reprise-pin').value;
        if (!pin) { err.textContent = 'Code PIN requis pour supprimer.'; err.style.display = 'block'; return; }
        fetch('/stagiaires/' + _justifRepr.stag + '/reprises/caces/' + _justifRepr.co + '/justificatif', {
            method: 'DELETE', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: pin })
        }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
              if (!res.ok) { err.textContent = res.data.detail || 'Erreur'; err.style.display = 'block'; return; }
              document.getElementById('modal-justif-reprise').style.display = 'none';
              _rechargerHistoStag(_justifRepr.stag);
          }).catch(function () { err.textContent = 'Erreur reseau'; err.style.display = 'block'; });
    }

    function _rechargerHistoStag(sid) {
        var body = document.getElementById('hist-body-' + sid);
        if (body) { delete body.dataset.loaded; }
        var b = document.querySelector('[data-action="historique"][data-id="' + sid + '"]');
        var row = document.getElementById('hist-' + sid);
        if (row) { row.style.display = 'none'; if (b) b.textContent = '▶'; }
        if (b) toggleHistorique(String(sid), b);
    }

    function _frReprToAttr(r) {
        return JSON.stringify({
            id: r.id, famille: r.famille, categorie: r.categorie,
            options_obtenues: r.options_obtenues || "", date_obtention: r.date_obtention,
            date_echeance: r.date_echeance, ancien_numero: r.ancien_numero || "",
            testeur_id: r.testeur_id || ""
        }).replace(/"/g, "&quot;");
    }

    function ouvrirModalModifReprise(stagiaireId, r) {
        ouvrirModalReprise(stagiaireId);
        _repriseEditId = r.id;
        var titre = document.querySelector('#modal-reprise h3');
        if (titre) titre.textContent = 'Modifier un CACES repris';
        var sFam = document.getElementById('rep-famille');
        sFam.value = r.famille;
        // Declenche le chargement des categories pour la famille, puis pre-selectionne.
        var evt = new Event('change', { bubbles: true });
        sFam.dispatchEvent(evt);
        setTimeout(function () {
            var sCat = document.getElementById('rep-categorie');
            if (sCat) { sCat.disabled = false; sCat.value = r.categorie; }
            document.getElementById('rep-options').value = r.options_obtenues || '';
            document.getElementById('rep-date-obtention').value = r.date_obtention || '';
            document.getElementById('rep-date-echeance').value = r.date_echeance || '';
            document.getElementById('rep-ancien-numero').value = r.ancien_numero || '';
            if (r.testeur_id) {
                var sTest = document.getElementById('rep-testeur');
                var _try = 0;
                var _pre = setInterval(function () {
                    _try++;
                    if (sTest.querySelector('option[value="' + r.testeur_id + '"]')) {
                        sTest.value = String(r.testeur_id);
                        clearInterval(_pre);
                    } else if (_try > 20) {
                        clearInterval(_pre);
                    }
                }, 100);
            }
        }, 350);
    }

    function renderReprisesHistorique(reprises, stagiaireId) {
        var lignes = '';
        var reprisesLocales = (reprises || []).filter(function(r) { return !r.organisme_externe; });
        if (reprisesLocales.length === 0) {
            lignes = '<div style="color:#888;font-size:13px;padding:6px 0;">Aucun CACES repris.</div>';
        } else {
            lignes = reprisesLocales.map(function(r) {
                var opts = r.options_obtenues
                    ? r.options_obtenues.split(',').map(function(o){ return '<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:1px 4px;font-size:10px;font-weight:700;">' + o.trim() + '</span>'; }).join(' ')
                    : '<span style="color:#ccc;font-size:11px;">—</span>';
                return '<div class="repr-row" style="display:flex;align-items:center;gap:10px;padding:7px 10px;border-bottom:1px solid #eef0f6;font-size:12px;flex-wrap:wrap;">'
                    + '<span class="repr-ident" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
                        + '<span style="font-family:monospace;font-weight:700;color:#7b1fa2;white-space:nowrap;" title="Ancien numero (repris)">' + (r.ancien_numero || '—') + '</span>'
                        + '<span style="font-weight:700;color:#555;">' + r.famille + '</span>'
                        + '<span style="background:#1a237e;color:#fff;border-radius:4px;padding:0 5px;font-weight:800;">' + r.categorie + '</span>'
                        + '<span style="display:flex;gap:2px;">' + opts + '</span>'
                        + '<span class="repr-ident-btns" style="display:none;align-items:center;gap:6px;margin-left:auto;">'
                            + '<button type="button" data-action="modifier-reprise-caces" data-reprise="' + _frReprToAttr(r) + '" data-stag="' + stagiaireId + '" style="background:#ede7f6;color:#5e35b1;border:1px solid #d1c4e9;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Modifier">✏️</button>'
                            + '<button type="button" data-action="ouvrir-suppr-reprise" data-type="caces" data-id="' + r.id + '" data-stag="' + stagiaireId + '" style="background:#fce4e4;color:#c62828;border:1px solid #f8bbd0;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Supprimer">🗑️</button>'
                        + '</span>'
                    + '</span>'
                    + '<span class="repr-dates" style="display:flex;align-items:center;gap:8px;">'
                        + '<span style="color:#1a237e;font-weight:700;">' + _fmtDateRep(r.date_obtention) + '</span>'
                        + '<span style="color:#2e7d32;font-weight:700;">→ ' + _fmtDateRep(r.date_echeance) + '</span>'
                        + (r.testeur_nom ? '<span style="color:#888;font-size:11px;margin-left:8px;">' + r.testeur_nom + '</span>' : '')
                    + '</span>'
                    + '<span class="repr-actions" style="display:flex;align-items:center;gap:8px;margin-left:auto;flex-wrap:wrap;">'
                        + (r.a_justificatif
                            ? '<a href="/stagiaires/' + stagiaireId + '/caces-externe/' + r.id + '/justificatif" target="_blank" style="color:#00695c;font-size:11px;text-decoration:underline;" title="Voir le justificatif">📎 ' + (r.justificatif_nom || 'Justificatif') + '</a>'
                            : '<span style="color:#e65100;font-size:11px;" title="Aucun justificatif joint">⚠️ Sans justificatif</span>')
                        + '<button type="button" data-action="joindre-justif-reprise" data-id="' + r.id + '" data-stag="' + stagiaireId + '" data-a-fichier="' + (r.a_justificatif ? '1' : '0') + '" data-nom-fichier="' + (r.justificatif_nom || '') + '" style="background:#e0f2f1;color:#00695c;border:1px solid #b2dfdb;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="' + (r.a_justificatif ? 'Gerer le justificatif' : 'Joindre un justificatif') + '">📤</button>'
                        + '<span class="repr-actions-btns" style="display:flex;align-items:center;gap:8px;">'
                            + '<button type="button" data-action="modifier-reprise-caces" data-reprise="' + _frReprToAttr(r) + '" data-stag="' + stagiaireId + '" style="background:#ede7f6;color:#5e35b1;border:1px solid #d1c4e9;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Modifier">✏️</button>'
                            + '<button type="button" data-action="ouvrir-suppr-reprise" data-type="caces" data-id="' + r.id + '" data-stag="' + stagiaireId + '" style="background:#fce4e4;color:#c62828;border:1px solid #f8bbd0;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Supprimer">🗑️</button>'
                        + '</span>'
                    + '</span>'
                    + '</div>';
            }).join('');
        }
        return '<div style="margin-top:10px;">'
            + '<div style="display:flex;align-items:center;justify-content:flex-start;gap:12px;margin-bottom:6px;">'
            + '<strong style="color:#7b1fa2;font-size:13px;">🪪 Historique CACES internes</strong>'
            + '<button data-action="ajouter-reprise" data-id="' + stagiaireId + '" style="background:none;border:none;padding:2px 4px;font-size:18px;line-height:1;cursor:pointer;" title="Nouveau">🆕</button>'
            + '</div>'
            + lignes
            + '</div>';
    }

    function _fmtDateRep(iso) {
        if (!iso) return '—';
        var p = iso.split('-');
        return p[2] + '/' + p[1] + '/' + p[0];
    }

    function renderCacesExternes(reprises, stagiaireId) {
        var externes = (reprises || []).filter(function(r) { return r.organisme_externe; });
        var lignes = '';
        if (externes.length === 0) {
            lignes = '<div style="color:#888;font-size:13px;padding:6px 0;">Aucun CACES externe enregistré.</div>';
        } else {
            lignes = externes.map(function(r) {
                var justif = r.a_justificatif
                    ? '<a href="/stagiaires/' + stagiaireId + '/caces-externe/' + r.id + '/justificatif" target="_blank" style="color:#00695c;font-size:11px;text-decoration:underline;" title="Voir le justificatif">📎 ' + (r.justificatif_nom || 'Justificatif') + '</a>'
                    : '<span style="color:#e65100;font-size:11px;" title="Aucun justificatif joint">⚠️ Sans justificatif</span>';
                return '<div class="cext-row" style="display:flex;align-items:center;gap:10px;padding:7px 10px;border-bottom:1px solid #eef0f6;font-size:12px;flex-wrap:wrap;">'
                    + '<span class="cext-ident" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
                        + '<span style="font-weight:700;color:#555;">' + r.famille + '</span>'
                        + '<span style="background:#00695c;color:#fff;border-radius:4px;padding:0 5px;font-weight:800;">' + r.categorie + '</span>'
                        + (r.options_obtenues ? '<span style="display:flex;gap:2px;">' + r.options_obtenues.split(',').map(function(o){ return '<span style="background:#e0f2f1;color:#00695c;border-radius:3px;padding:1px 4px;font-size:10px;font-weight:700;">' + o.trim() + '</span>'; }).join(' ') + '</span>' : '')
                        + (r.sous_traitance ? '<span style="background:#e6f1fb;color:#0c447c;border-radius:3px;padding:1px 6px;font-size:10px;font-weight:700;" title="Passe en sous-traitance via l\'organisme habilite">S/T</span>' : '')
                        + '<span class="cext-ident-btns" style="display:none;align-items:center;gap:6px;margin-left:auto;">'
                            + '<button type="button" data-action="modifier-caces-externe" data-ext="' + _cextToAttr(r) + '" data-stag="' + stagiaireId + '" style="background:#ede7f6;color:#5e35b1;border:1px solid #d1c4e9;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Modifier">✏️</button>'
                            + '<button type="button" data-action="suppr-caces-externe" data-id="' + r.id + '" data-stag="' + stagiaireId + '" style="background:#fce4e4;color:#c62828;border:1px solid #f8bbd0;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Supprimer">🗑️</button>'
                        + '</span>'
                    + '</span>'
                    + '<span class="cext-dates" style="display:flex;align-items:center;gap:8px;">'
                        + '<span style="color:#1a237e;font-weight:700;">' + _fmtDateRep(r.date_obtention) + '</span>'
                        + '<span style="color:#2e7d32;font-weight:700;">→ ' + _fmtDateRep(r.date_echeance) + '</span>'
                        + '<span style="color:#00695c;font-weight:700;margin-left:8px;">🌐 ' + r.organisme_externe + '</span>'
                    + '</span>'
                    + '<span class="cext-actions" style="display:flex;align-items:center;gap:8px;margin-left:auto;flex-wrap:wrap;">'
                        + justif
                        + '<button type="button" data-action="joindre-justif-reprise" data-id="' + r.id + '" data-stag="' + stagiaireId + '" data-a-fichier="' + (r.a_justificatif ? '1' : '0') + '" data-nom-fichier="' + (r.justificatif_nom || '') + '" style="background:#e0f2f1;color:#00695c;border:1px solid #b2dfdb;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="' + (r.a_justificatif ? 'Gerer le justificatif' : 'Joindre un justificatif') + '">📤</button>'
                        + '<span class="cext-actions-btns" style="display:flex;align-items:center;gap:8px;">'
                            + '<button type="button" data-action="modifier-caces-externe" data-ext="' + _cextToAttr(r) + '" data-stag="' + stagiaireId + '" style="background:#ede7f6;color:#5e35b1;border:1px solid #d1c4e9;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Modifier">✏️</button>'
                            + '<button type="button" data-action="suppr-caces-externe" data-id="' + r.id + '" data-stag="' + stagiaireId + '" style="background:#fce4e4;color:#c62828;border:1px solid #f8bbd0;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Supprimer">🗑️</button>'
                        + '</span>'
                    + '</span>'
                    + '</div>';
            }).join('');
        }
        return '<div style="margin-top:10px;">'
            + '<div style="display:flex;align-items:center;justify-content:flex-start;gap:12px;margin-bottom:6px;">'
            + '<strong style="color:#00695c;font-size:13px;">🌐 CACES externes</strong>'
            + '<button data-action="ajouter-caces-externe" data-id="' + stagiaireId + '" style="background:none;border:none;padding:2px 4px;font-size:18px;line-height:1;cursor:pointer;" title="Nouveau">🆕</button>'
            + '</div>'
            + lignes
            + '</div>';
    }

    function renderOrphelinesReprises(data, stagiaireId) {
        var theories = (data && data.theories) ? data.theories : [];
        var pratiques = (data && data.pratiques) ? data.pratiques : [];

        // sous-bloc theories
        var blocTheo = '';
        if (theories.length > 0) {
            blocTheo = '<div style="font-size:12px;font-weight:700;color:#b26a00;margin:6px 0 2px;">🎓 Théories orphelines</div>'
                + theories.map(function(t) {
                    return '<div style="display:flex;align-items:center;gap:10px;padding:6px 10px;border-bottom:1px solid #fdf0e0;font-size:12px;flex-wrap:wrap;">'
                        + '<span style="font-weight:700;color:#555;">' + t.famille + '</span>'
                        + '<span style="color:#b26a00;font-weight:700;">' + _fmtDateRep(t.date_obtention) + '</span>'
                        + (t.testeur_nom ? '<span style="color:#888;font-size:11px;">' + t.testeur_nom + '</span>' : '')
                        + '<span style="color:#b26a00;font-size:10px;font-style:italic;">en attente d\'une pratique</span>'
                        + '<button type="button" data-action="ouvrir-suppr-reprise" data-type="theorie" data-id="' + t.id + '" data-stag="' + stagiaireId + '" style="margin-left:auto;background:#fce4e4;color:#c62828;border:1px solid #f8bbd0;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Supprimer">🗑️</button>'
                        + '</div>';
                }).join('');
        }

        // sous-bloc pratiques
        var blocPrat = '';
        if (pratiques.length > 0) {
            blocPrat = '<div style="font-size:12px;font-weight:700;color:#b26a00;margin:8px 0 2px;">🔧 Pratiques orphelines</div>'
                + pratiques.map(function(p) {
                    var opts = p.options_obtenues
                        ? p.options_obtenues.split(',').map(function(o){ return '<span style="background:#fff3e0;color:#b26a00;border-radius:3px;padding:1px 4px;font-size:10px;font-weight:700;">' + o.trim() + '</span>'; }).join(' ')
                        : '';
                    return '<div style="display:flex;align-items:center;gap:10px;padding:6px 10px;border-bottom:1px solid #fdf0e0;font-size:12px;flex-wrap:wrap;">'
                        + '<span style="font-weight:700;color:#555;">' + p.famille + '</span>'
                        + '<span style="background:#e65100;color:#fff;border-radius:4px;padding:0 5px;font-weight:800;">' + p.categorie + '</span>'
                        + '<span style="display:flex;gap:2px;">' + opts + '</span>'
                        + '<span style="color:#b26a00;font-weight:700;">' + _fmtDateRep(p.date_obtention) + '</span>'
                        + (p.testeur_nom ? '<span style="color:#888;font-size:11px;">' + p.testeur_nom + '</span>' : '')
                        + '<span style="color:#b26a00;font-size:10px;font-style:italic;">en attente d\'une théorie</span>'
                        + '<button type="button" data-action="ouvrir-suppr-reprise" data-type="pratique" data-id="' + p.id + '" data-stag="' + stagiaireId + '" style="margin-left:auto;background:#fce4e4;color:#c62828;border:1px solid #f8bbd0;border-radius:4px;padding:2px 7px;font-size:14px;cursor:pointer;" title="Supprimer">🗑️</button>'
                        + '</div>';
                }).join('');
        }

        var corps = (blocTheo + blocPrat) || '<div style="color:#888;font-size:13px;padding:6px 0;">Aucune orpheline.</div>';

        return '<div style="margin-top:14px;border-top:1px solid #ffe0b2;padding-top:10px;">'
            + '<div style="display:flex;align-items:center;justify-content:flex-start;gap:12px;margin-bottom:6px;">'
            + '<strong style="color:#e65100;font-size:13px;">🧩 Orphelines reprises</strong>'
            + '<button data-action="ajouter-orpheline" data-id="' + stagiaireId + '" style="background:none;border:none;padding:2px 4px;font-size:18px;line-height:1;cursor:pointer;" title="Nouveau">🆕</button>'
            + '</div>'
            + corps
            + '</div>';
    }

    function renderCartesEmises(cartes) {
        let html = '<div style="margin-top:16px;">';
        html += '<div style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px;">🪪 Cartes émises</div>';

        if (!cartes.length) {
            html += '<p style="color:#bbb;font-size:13px;font-style:italic;margin:0;">Aucune carte émise.</p>';
            html += '</div>';
            return html;
        }

        html += '<div class="co-hscroll"><div style="border:1px solid #c8d8f0;border-radius:10px;overflow:hidden;">';
        html += '<div class="carte-head-row" style="display:flex;align-items:center;background:#f0f2f7;border-bottom:1px solid #dde3f0;padding:7px 12px;gap:0;">';
        html += '<div style="width:28px;min-width:28px;"></div>';
        html += '<div style="flex:1;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">N° Carte</div>';
        html += '<div style="width:70px;min-width:70px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Famille</div>';
        html += '<div style="width:90px;min-width:90px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Émission</div>';
        html += '<div style="width:76px;min-width:76px;font-size:10px;color:#888;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Statut</div>';
        html += '</div>';

        cartes.forEach(function (c, i) {
            const bg = i % 2 === 0 ? '#fff' : '#f5f7ff';
            const emise = c.statut === 'emise';
            const badgeHtml = emise
                ? '<span style="background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:1px 7px;font-size:10px;font-weight:700;">Émise</span>'
                : '<span style="background:#f5f5f5;color:#888;border-radius:4px;padding:1px 7px;font-size:10px;font-weight:700;">Remplacée</span>';
            const opacity = emise ? '' : 'opacity:0.65;';

            html += '<div style="border-bottom:1px solid #eef0f6;' + opacity + '">';
            html += '<div class="carte-row" style="display:flex;align-items:center;padding:8px 12px;background:' + bg + ';gap:0;">';
            html += '<div class="carte-toggle" style="width:28px;min-width:28px;text-align:center;">'
                + '<button data-action="toggle-caces-carte" data-carte-id="' + c.id + '" data-loaded="0" '
                + 'style="background:none;border:none;cursor:pointer;font-size:11px;color:#2d2d2d;padding:1px 4px;line-height:1;" '
                + 'title="Voir les CACES® de cette carte">▶</button></div>';
            html += '<div class="carte-num" style="flex:1;"><span style="font-family:monospace;font-size:12px;font-weight:700;color:#1a237e;">' + c.numero_carte + '</span></div>';
            html += '<div class="carte-fam" data-label="Famille" style="width:70px;min-width:70px;font-size:12px;font-weight:700;color:#555;">' + c.famille + '</div>';
            html += '<div class="carte-em" data-label="Émission" style="width:90px;min-width:90px;font-size:12px;color:#666;">' + formatDate(c.date_generation) + '</div>';
            html += '<div class="carte-sta" style="width:76px;min-width:76px;">' + badgeHtml + '</div>';
            html += '</div>';
            html += '<div id="stag-caces-detail-' + c.id + '" style="display:none;padding:10px 12px 14px 40px;background:#f7f8fc;border-top:1px solid #e8eef8;">'
                + '<span style="color:#888;font-size:12px;">Chargement…</span></div>';
            html += '</div>';
        });

        html += '</div></div></div>';
        return html;
    }

    async function chargerCacesCarteStag(carteId, el) {
        try {
            const r = await fetch('/api/cartes-caces/' + carteId + '/caces');
            if (!r.ok) throw new Error();
            const caces = await r.json();
            if (!caces.length) {
                el.innerHTML = '<span style="color:#888;font-size:12px;font-style:italic;">Aucun CACES® valide actuel pour cette famille.</span>';
                return;
            }
            const header = '<div class="cdet-head-row" style="display:flex;align-items:center;gap:0;padding:4px 8px;border-bottom:1px solid #dde3f0;background:#eef0f8;">'
                + '<div style="width:50px;min-width:50px;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">Cat.</div>'
                + '<div style="flex:1;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">Libellé</div>'
                + '<div style="width:52px;min-width:52px;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">Options</div>'
                + '<div style="width:54px;min-width:54px;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">N°</div>'
                + '<div style="width:80px;min-width:80px;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">Obtention</div>'
                + '<div style="width:80px;min-width:80px;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">Échéance</div>'
                + '<div style="flex:1;font-size:9px;color:#888;font-weight:700;text-transform:uppercase;">Testeur</div>'
                + '</div>';
            const rows = caces.map(function (co) {
                const opts = co.options_obtenues
                    ? co.options_obtenues.split(',').map(function (o) {
                        return '<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:0 4px;font-size:10px;font-weight:700;">' + o.trim() + '</span>';
                      }).join(' ')
                    : '<span style="color:#ccc;">—</span>';
                const noFormate = co.ancien_numero ? co.ancien_numero : (co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—');
                return '<div class="cdet-row" style="display:flex;align-items:center;gap:0;padding:5px 8px;border-bottom:1px solid #e8eef0;">'
                    + '<div class="cdet-cat" style="width:50px;min-width:50px;"><span style="background:#1a237e;color:#fff;border-radius:4px;padding:0 6px;font-size:11px;font-weight:800;">' + co.categorie + '</span></div>'
                    + '<div class="cdet-lib" style="flex:1;font-size:11px;color:#444;">' + (co.categorie_libelle || '—') + '</div>'
                    + '<div class="cdet-opt" style="width:52px;min-width:52px;display:flex;flex-wrap:wrap;gap:2px;">' + opts + '</div>'
                    + '<div class="cdet-no" style="width:54px;min-width:54px;"><span style="background:#e8eaf6;font-family:monospace;font-size:11px;padding:1px 5px;border-radius:3px;">' + noFormate + '</span></div>'
                    + '<div class="cdet-obt" data-label="Obtention" style="width:80px;min-width:80px;font-size:11px;color:#444;">' + formatDate(co.date_obtention) + '</div>'
                    + '<div class="cdet-ech" data-label="Échéance" style="width:80px;min-width:80px;font-size:11px;font-weight:700;color:#2e7d32;">' + formatDate(co.date_echeance) + '</div>'
                    + '<div class="cdet-test" data-label="Testeur" style="flex:1;font-size:10px;color:#666;">' + (co.testeur_nom || '—') + '</div>'
                    + '</div>';
            }).join('');
            el.innerHTML = '<div class="co-hscroll"><div style="border:1px solid #dde3f0;border-radius:6px;overflow:hidden;">' + header + rows + '</div></div>';
        } catch (_) {
            el.innerHTML = '<span style="color:#c62828;font-size:12px;">Erreur de chargement.</span>';
        }
    }

    function formatDate(iso) {
        if (!iso) return '';
        const parts = iso.split('-');
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    }

    // ── Reprise d'historique ───────────────────────────────────────────────
    var _repriseStagiaireId = null;

    var _repriseEditId = null;

    function ouvrirModalReprise(stagiaireId) {
        _repriseStagiaireId = stagiaireId;
        _repriseEditId = null;
        var _repTitre = document.querySelector('#modal-reprise h3');
        if (_repTitre) _repTitre.textContent = '🪪 Ajouter un CACES repris';
        document.getElementById('rep-categorie').innerHTML = '<option value="">— Choisir une famille d\'abord —</option>';
        document.getElementById('rep-categorie').disabled = true;
        document.getElementById('rep-options').value = '';
        document.getElementById('rep-date-obtention').value = '';
        document.getElementById('rep-date-echeance').value = '';
        document.getElementById('rep-ancien-numero').value = '';
        document.getElementById('rep-pin').value = '';
        var err = document.getElementById('rep-error');
        err.style.display = 'none'; err.textContent = '';
        var sFam = document.getElementById('rep-famille');
        sFam.innerHTML = '<option value="">— Choisir —</option>';
        try {
            var familles = JSON.parse(document.getElementById('reprise-data').dataset.familles || '[]');
            familles.forEach(function(f) {
                var o = document.createElement('option');
                o.value = f.code; o.textContent = f.code + ' — ' + f.libelle;
                sFam.appendChild(o);
            });
        } catch (e) {}
        sFam.value = '';
        var sTest = document.getElementById('rep-testeur');
        sTest.innerHTML = '<option value="">— Chargement… —</option>';
        fetch('/api/testeurs/', { credentials: 'same-origin' })
            .then(function(r){ return r.json(); })
            .then(function(testeurs){
                sTest.innerHTML = '<option value="">— Choisir —</option>';
                (testeurs || []).forEach(function(t){
                    var o = document.createElement('option');
                    o.value = t.id; o.textContent = t.nom + ' ' + t.prenom;
                    sTest.appendChild(o);
                });
            })
            .catch(function(){ sTest.innerHTML = '<option value="">— Erreur chargement —</option>'; });
        document.getElementById('modal-reprise').style.display = 'flex';
    }

    var _orphStagiaireId = null;
    var _orphType = null;  // 'theorie' | 'pratique'

    function ouvrirModalOrpheline(stagiaireId) {
        _orphStagiaireId = stagiaireId;
        _orphType = null;
        document.getElementById('orph-choix').style.display = 'flex';
        document.getElementById('orph-form').style.display = 'none';
        document.getElementById('modal-orpheline').style.display = 'flex';
    }

    function orphRetourChoix() {
        _orphType = null;
        document.getElementById('orph-choix').style.display = 'flex';
        document.getElementById('orph-form').style.display = 'none';
    }

    function orphChoisirType(type) {
        _orphType = type;
        document.getElementById('orph-choix').style.display = 'none';
        document.getElementById('orph-form').style.display = 'flex';

        var titre = document.getElementById('orph-form-titre');
        var catWrap = document.getElementById('orph-categorie-wrap');
        var optWrap = document.getElementById('orph-options-wrap');
        if (type === 'theorie') {
            titre.textContent = '🎓 Théorie orpheline';
            catWrap.style.display = 'none';
            optWrap.style.display = 'none';
        } else {
            titre.textContent = '🔧 Pratique orpheline';
            catWrap.style.display = 'block';
            optWrap.style.display = 'block';
        }

        document.getElementById('orph-categorie').innerHTML = '<option value="">— Choisir une famille d\'abord —</option>';
        document.getElementById('orph-categorie').disabled = true;
        document.getElementById('orph-options').value = '';
        document.getElementById('orph-date').value = '';
        document.getElementById('orph-pin').value = '';
        var err = document.getElementById('orph-error');
        err.style.display = 'none'; err.textContent = '';

        var sFam = document.getElementById('orph-famille');
        sFam.innerHTML = '<option value="">— Choisir —</option>';
        try {
            var familles = JSON.parse(document.getElementById('reprise-data').dataset.familles || '[]');
            familles.forEach(function(f) {
                var o = document.createElement('option');
                o.value = f.code; o.textContent = f.code + ' — ' + f.libelle;
                sFam.appendChild(o);
            });
        } catch (e) {}
        sFam.value = '';

        var sTest = document.getElementById('orph-testeur');
        sTest.innerHTML = '<option value="">— Chargement… —</option>';
        fetch('/api/testeurs/', { credentials: 'same-origin' })
            .then(function(r){ return r.json(); })
            .then(function(testeurs){
                sTest.innerHTML = '<option value="">— Choisir —</option>';
                (testeurs || []).forEach(function(t){
                    var o = document.createElement('option');
                    o.value = t.id; o.textContent = t.nom + ' ' + t.prenom;
                    sTest.appendChild(o);
                });
            })
            .catch(function(){ sTest.innerHTML = '<option value="">— Erreur chargement —</option>'; });
    }

    function confirmerAjoutOrpheline() {
        var err = document.getElementById('orph-error');
        err.style.display = 'none'; err.textContent = '';

        var famille = document.getElementById('orph-famille').value;
        var dateObt = document.getElementById('orph-date').value;
        var testeurId = parseInt(document.getElementById('orph-testeur').value, 10);
        var pin = document.getElementById('orph-pin').value;

        if (!famille || !dateObt || !testeurId || !pin) {
            err.textContent = 'Famille, date, testeur et PIN sont obligatoires.'; err.style.display = 'block'; return;
        }

        var url, payload;
        if (_orphType === 'theorie') {
            url = '/stagiaires/' + _orphStagiaireId + '/reprises/theorie';
            payload = { famille: famille, date_obtention: dateObt, testeur_id: testeurId, pin: pin };
        } else {
            var categorie = document.getElementById('orph-categorie').value;
            if (!categorie) { err.textContent = 'La categorie est obligatoire pour une pratique.'; err.style.display = 'block'; return; }
            url = '/stagiaires/' + _orphStagiaireId + '/reprises/pratique';
            payload = {
                famille: famille,
                categorie: categorie,
                options_obtenues: document.getElementById('orph-options').value.trim() || null,
                date_obtention: dateObt,
                testeur_id: testeurId,
                pin: pin,
            };
        }

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload),
        })
        .then(function(r){
            if (r.ok) return r.json().then(function(){
                document.getElementById('modal-orpheline').style.display = 'none';
                var sid = _orphStagiaireId;
                var bodyEl = document.getElementById('hist-body-' + sid);
                var btn = document.querySelector('[data-action="historique"][data-id="' + sid + '"]');
                if (bodyEl) { delete bodyEl.dataset.loaded; }
                var row = document.getElementById('hist-' + sid);
                if (row) { row.style.display = 'none'; if (btn) btn.textContent = '▶'; }
                if (btn) toggleHistorique(String(sid), btn);
            });
            return r.json().then(function(d){
                err.textContent = '❌ ' + (d.detail || 'Erreur'); err.style.display = 'block';
            });
        })
        .catch(function(){ err.textContent = '❌ Erreur reseau.'; err.style.display = 'block'; });
    }

    document.addEventListener('change', function(e){
        if (e.target && e.target.id === 'rep-famille') {
            var fam = e.target.value;
            var sCat = document.getElementById('rep-categorie');
            if (!fam) { sCat.innerHTML = '<option value="">— Choisir une famille d\'abord —</option>'; sCat.disabled = true; return; }
            sCat.innerHTML = '<option value="">— Chargement… —</option>'; sCat.disabled = true;
            fetch('/admin/categories/' + encodeURIComponent(fam), { credentials: 'same-origin' })
                .then(function(r){ return r.json(); })
                .then(function(cats){
                    sCat.innerHTML = '<option value="">— Choisir —</option>';
                    (cats || []).forEach(function(c){
                        var o = document.createElement('option');
                        o.value = c.code; o.textContent = c.code + ' — ' + c.libelle;
                        sCat.appendChild(o);
                    });
                    sCat.disabled = false;
                })
                .catch(function(){ sCat.innerHTML = '<option value="">— Erreur —</option>'; sCat.disabled = true; });
        }
        if (e.target && e.target.id === 'cext-famille') {
            var fam = e.target.value;
            var sCat = document.getElementById('cext-categorie');
            if (!fam) { sCat.innerHTML = '<option value="">— Choisir une famille d\'abord —</option>'; sCat.disabled = true; return; }
            sCat.innerHTML = '<option value="">— Chargement… —</option>'; sCat.disabled = true;
            fetch('/admin/categories/' + encodeURIComponent(fam), { credentials: 'same-origin' })
                .then(function(r){ return r.json(); })
                .then(function(cats){
                    sCat.innerHTML = '<option value="">— Choisir —</option>';
                    (cats || []).forEach(function(c){
                        var o = document.createElement('option');
                        o.value = c.code; o.textContent = c.code + ' — ' + c.libelle;
                        sCat.appendChild(o);
                    });
                    sCat.disabled = false;
                })
                .catch(function(){ sCat.innerHTML = '<option value="">— Erreur —</option>'; sCat.disabled = true; });
        }
        if (e.target && e.target.id === 'orph-famille') {
            var fam = e.target.value;
            var sCat = document.getElementById('orph-categorie');
            if (!fam) { sCat.innerHTML = '<option value="">— Choisir une famille d\'abord —</option>'; sCat.disabled = true; return; }
            sCat.innerHTML = '<option value="">— Chargement… —</option>'; sCat.disabled = true;
            fetch('/admin/categories/' + encodeURIComponent(fam), { credentials: 'same-origin' })
                .then(function(r){ return r.json(); })
                .then(function(cats){
                    sCat.innerHTML = '<option value="">— Choisir —</option>';
                    (cats || []).forEach(function(c){
                        var o = document.createElement('option');
                        o.value = c.code; o.textContent = c.code + ' — ' + c.libelle;
                        sCat.appendChild(o);
                    });
                    sCat.disabled = false;
                })
                .catch(function(){ sCat.innerHTML = '<option value="">— Erreur —</option>'; sCat.disabled = true; });
        }
    });

    var _cextEditId = null;

    function _cextToAttr(r) {
        return JSON.stringify({
            id: r.id, organisme: r.organisme_externe || "", famille: r.famille,
            categorie: r.categorie, date_echeance: r.date_echeance,
            options_obtenues: r.options_obtenues || "",
            sous_traitance: !!r.sous_traitance
        }).replace(/"/g, "&quot;");
    }

    function ouvrirModalModifExterne(stagiaireId, r) {
        ouvrirModalCacesExterne(stagiaireId);
        _cextEditId = r.id;
        var titre = document.querySelector('#modal-caces-externe h3');
        if (titre) titre.textContent = 'Modifier un CACES externe';
        document.getElementById('cext-organisme').value = r.organisme || '';
        var sFam = document.getElementById('cext-famille');
        sFam.value = r.famille;
        sFam.dispatchEvent(new Event('change', { bubbles: true }));
        setTimeout(function () {
            var sCat = document.getElementById('cext-categorie');
            if (sCat) { sCat.disabled = false; sCat.value = r.categorie; }
            document.getElementById('cext-echeance').value = r.date_echeance || '';
            document.getElementById('cext-options').value = r.options_obtenues || '';
            document.getElementById('cext-soustraitance').checked = !!r.sous_traitance;
        }, 350);
    }

    function ouvrirModalCacesExterne(stagiaireId) {
        _cextEditId = null;
        window._cextStagiaireId = stagiaireId;
        document.getElementById('cext-organisme').value = '';
        document.getElementById('cext-categorie').innerHTML = '<option value="">— Choisir une famille d\'abord —</option>';
        document.getElementById('cext-categorie').disabled = true;
        document.getElementById('cext-echeance').value = '';
        document.getElementById('cext-options').value = '';
        document.getElementById('cext-soustraitance').checked = false;
        document.getElementById('cext-fichier').value = '';
        document.getElementById('cext-pin').value = '';
        document.getElementById('cext-error').style.display = 'none';
        document.getElementById('cext-warn').style.display = 'none';
        var sFam = document.getElementById('cext-famille');
        sFam.innerHTML = '<option value="">— Choisir —</option>';
        try {
            var familles = JSON.parse(document.getElementById('reprise-data').dataset.familles || '[]');
            familles.forEach(function(f) {
                var o = document.createElement('option');
                o.value = f.code; o.textContent = f.code + ' — ' + f.libelle;
                sFam.appendChild(o);
            });
        } catch (e) {}
        sFam.value = '';
        document.getElementById('modal-caces-externe').style.display = 'flex';
    }

    function confirmerCacesExterne() {
        var stagiaireId = window._cextStagiaireId;
        var fd = new FormData();
        fd.append('famille', document.getElementById('cext-famille').value);
        fd.append('categorie', document.getElementById('cext-categorie').value);
        fd.append('date_echeance', document.getElementById('cext-echeance').value);
        fd.append('organisme', document.getElementById('cext-organisme').value);
        fd.append('options', document.getElementById('cext-options').value.trim());
        fd.append('sous_traitance', document.getElementById('cext-soustraitance').checked ? 'true' : 'false');
        fd.append('pin', document.getElementById('cext-pin').value);
        var fichierInput = document.getElementById('cext-fichier');
        if (fichierInput.files && fichierInput.files[0]) { fd.append('fichier', fichierInput.files[0]); }
        var errDiv = document.getElementById('cext-error');
        var warnDiv = document.getElementById('cext-warn');
        errDiv.style.display = 'none';
        warnDiv.style.display = 'none';
        var _url = '/stagiaires/' + stagiaireId + '/caces-externe';
        var _method = 'POST';
        if (_cextEditId) { _url = _url + '/' + _cextEditId; _method = 'PUT'; }
        fetch(_url, {
            method: _method,
            credentials: 'same-origin',
            body: fd
        }).then(function(r) {
            return r.json().then(function(d) { return { ok: r.ok, data: d }; });
        }).then(function(res) {
            if (!res.ok) {
                errDiv.textContent = res.data.detail || 'Erreur';
                errDiv.style.display = 'block';
            } else {
                if (res.data.exploitable === false) {
                    warnDiv.textContent = 'CACES ajouté mais non exploitable (base théorique > 12 mois).';
                    warnDiv.style.display = 'block';
                    setTimeout(function() {
                        document.getElementById('modal-caces-externe').style.display = 'none';
                        rechargerHistoriqueReprise(stagiaireId);
                    }, 2000);
                } else {
                    document.getElementById('modal-caces-externe').style.display = 'none';
                    rechargerHistoriqueReprise(stagiaireId);
                }
            }
        }).catch(function() {
            errDiv.textContent = 'Erreur réseau';
            errDiv.style.display = 'block';
        });
    }

    function supprimerCacesExterne(cacesId, stagiaireId) {
        var pin = prompt('PIN admin pour supprimer ce CACES externe :');
        if (!pin) return;
        fetch('/stagiaires/' + stagiaireId + '/caces-externe/' + cacesId + '?pin=' + encodeURIComponent(pin), {
            method: 'DELETE',
            credentials: 'same-origin'
        }).then(function(r) {
            if (r.ok) {
                rechargerHistoriqueReprise(stagiaireId);
            } else {
                r.json().then(function(d) { alert(d.detail || 'Erreur'); });
            }
        }).catch(function() { alert('Erreur réseau'); });
    }

    function rechargerHistoriqueReprise(stagiaireId) {
        var sid = String(stagiaireId);
        var body = document.getElementById('hist-body-' + sid);
        var btn = document.querySelector('[data-action="historique"][data-id="' + sid + '"]');
        if (body) { delete body.dataset.loaded; }
        var row = document.getElementById('hist-' + sid);
        if (row) { row.style.display = 'none'; if (btn) btn.textContent = '▶'; }
        if (btn) toggleHistorique(sid, btn);
    }

    function confirmerAjoutReprise() {
        var err = document.getElementById('rep-error');
        err.style.display = 'none'; err.textContent = '';
        var payload = {
            famille: document.getElementById('rep-famille').value,
            categorie: document.getElementById('rep-categorie').value,
            options_obtenues: document.getElementById('rep-options').value.trim() || null,
            date_obtention: document.getElementById('rep-date-obtention').value,
            date_echeance: document.getElementById('rep-date-echeance').value,
            ancien_numero: document.getElementById('rep-ancien-numero').value.trim(),
            testeur_id: parseInt(document.getElementById('rep-testeur').value, 10),
            pin: document.getElementById('rep-pin').value,
        };
        if (!payload.famille || !payload.categorie || !payload.date_obtention || !payload.date_echeance || !payload.ancien_numero || !payload.testeur_id || !payload.pin) {
            err.textContent = 'Tous les champs (sauf options) sont obligatoires.'; err.style.display = 'block'; return;
        }
        var _url = '/stagiaires/' + _repriseStagiaireId + '/reprises';
        var _method = 'POST';
        if (_repriseEditId) { _url = '/stagiaires/' + _repriseStagiaireId + '/reprises/caces/' + _repriseEditId; _method = 'PUT'; }
        fetch(_url, {
            method: _method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload),
        })
        .then(function(r){
            if (r.ok) return r.json().then(function(){
                document.getElementById('modal-reprise').style.display = 'none';
                var sid = _repriseStagiaireId;
                var body = document.getElementById('hist-body-' + sid);
                var btn = document.querySelector('[data-action="historique"][data-id="' + sid + '"]');
                if (body) { delete body.dataset.loaded; }
                var row = document.getElementById('hist-' + sid);
                if (row) { row.style.display = 'none'; if (btn) btn.textContent = '▶'; }
                if (btn) toggleHistorique(String(sid), btn);
            });
            return r.json().then(function(d){
                err.textContent = '❌ ' + (d.detail || 'Erreur'); err.style.display = 'block';
            });
        })
        .catch(function(){ err.textContent = '❌ Erreur réseau.'; err.style.display = 'block'; });
    }

});
