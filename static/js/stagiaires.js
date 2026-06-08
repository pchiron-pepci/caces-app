document.addEventListener('DOMContentLoaded', function () {

    // ── Recherche ──────────────────────────────────────────────────────────
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const q = this.value.toLowerCase();
            document.querySelectorAll('#tbody tr:not(.hist-row)').forEach(function (tr) {
                const sid = tr.dataset.stagiaireId;
                const visible = tr.textContent.toLowerCase().includes(q);
                tr.style.display = visible ? '' : 'none';
                // hide hist row when stagiaire row is hidden
                if (sid) {
                    const histRow = document.getElementById('hist-' + sid);
                    if (histRow && !visible) histRow.style.display = 'none';
                }
            });
        });
    }

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
        document.getElementById('pin-message').textContent = 'Archiver "' + nom + '" ?';
        document.getElementById('pin-input').value = '';
        document.getElementById('pin-error').style.display = 'none';
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
            document.getElementById('pin-error').style.display = 'block';
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
            const resp = await fetch('/stagiaires/' + id + '/historique');
            if (!resp.ok) throw new Error();
            const data = await resp.json();
            body.innerHTML = renderHistorique(data);
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

        let html = '<div style="display:flex; flex-direction:column; gap:8px; padding:4px 0;">';
        data.forEach(function (s) {
            const badgeStyle = STATUT_BADGE[s.statut] || 'background:#f5f5f5; color:#666;';
            const badgeLabel = STATUT_LABEL[s.statut] || s.statut;

            let dates = [];
            if (s.date_theorie) dates.push('Th. ' + formatDate(s.date_theorie));
            if (s.date_pratique_debut) {
                let prat = 'Pr. ' + formatDate(s.date_pratique_debut);
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

            html += '<div style="border:1px solid #e0e0e0; border-radius:8px; padding:10px 14px; background:white;">';
            html += '<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">';
            html += '<a href="/sessions/' + s.session_id + '" style="font-family:\'Barlow Condensed\',sans-serif; font-size:15px; font-weight:700; text-decoration:none; color:#1a3a8f;">' + s.reference + '</a>';
            html += '<span style="font-size:13px; color:#555; font-weight:600;">' + s.famille + '</span>';
            html += '<span style="' + badgeStyle + ' padding:2px 8px; border-radius:8px; font-size:11px; font-weight:600;">' + badgeLabel + '</span>';
            if (dates.length) html += '<span style="font-size:11px; color:#888; margin-left:auto;">' + dates.join(' · ') + '</span>';
            html += '</div>';
            html += '<div style="font-size:13px; display:flex; flex-direction:column; gap:3px;">';
            html += '<div><span style="color:#666; display:inline-block; width:68px;">Théorie :</span>' + theorieHtml + '</div>';
            html += '<div><span style="color:#666; display:inline-block; width:68px;">Pratique :</span>' + pratiqueHtml + '</div>';
            html += '</div></div>';
        });
        html += '</div>';
        return html;
    }

    function formatDate(iso) {
        if (!iso) return '';
        const parts = iso.split('-');
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    }
});
