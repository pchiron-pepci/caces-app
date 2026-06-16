document.addEventListener('DOMContentLoaded', function () {

    const NC_DATA = JSON.parse(document.getElementById('nc-data').textContent);

    // ── Recherche ──────────────────────────────────────────────────────────
    const searchInput = document.getElementById('nc-search');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const q = this.value.toLowerCase();
            document.querySelectorAll('.nc-card').forEach(function (card) {
                const hay = (card.dataset.search || '').toLowerCase();
                card.style.display = hay.includes(q) ? '' : 'none';
            });
        });
    }

    // ── Tri colonnes ──────────────────────────────────────────────────────────
    let sortCol = null;
    let sortDir = 1;
    const attrMap = {
        reference: 'ref', date: 'date', titre: 'titre',
        origine: 'origine', type_nc: 'type', nature: 'nature', statut: 'statut'
    };

    document.addEventListener('click', function (e) {
        const col = e.target.closest('.nc-sort-col');
        if (!col) return;
        const key = col.dataset.col;
        if (sortCol === key) { sortDir *= -1; } else { sortCol = key; sortDir = 1; }
        document.querySelectorAll('.sort-arrow').forEach(function (el) { el.textContent = ''; });
        const arrowEl = document.getElementById('arrow-' + key);
        if (arrowEl) arrowEl.textContent = sortDir === 1 ? ' ↑' : ' ↓';
        const container = document.getElementById('nc-list');
        if (!container) return;
        const attr = 'data-' + (attrMap[key] || key);
        const cards = Array.from(container.querySelectorAll('.nc-card'));
        cards.sort(function (a, b) {
            const va = (a.getAttribute(attr) || '').toLowerCase();
            const vb = (b.getAttribute(attr) || '').toLowerCase();
            return va < vb ? -sortDir : va > vb ? sortDir : 0;
        });
        cards.forEach(function (card) { container.appendChild(card); });
    });

    // ── Toggle expand/collapse ─────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const header = e.target.closest('.nc-toggle-header');
        if (!header) return;
        const id = header.dataset.id;
        const body = document.getElementById('nc-body-' + id);
        const arrow = header.querySelector('.nc-arrow');
        if (!body) return;
        const open = body.style.display !== 'none';
        body.style.display = open ? 'none' : 'block';
        if (arrow) arrow.style.transform = open ? '' : 'rotate(90deg)';
    });

    // ── Clôturer ───────────────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.nc-cloturer-btn');
        if (!btn) return;
        const id = btn.dataset.id;
        const pin = prompt('Code PIN administrateur requis pour clôturer :');
        if (pin === null) return;
        fetch('/api/non-conformites/' + id + '/cloturer?pin=' + encodeURIComponent(pin), { method: 'PATCH' })
            .then(r => r.json())
            .then(data => {
                if (data.detail) { alert('Erreur : ' + data.detail); return; }
                location.reload();
            });
    });

    // ── Rouvrir ────────────────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.nc-rouvrir-btn');
        if (!btn) return;
        const id = btn.dataset.id;
        const pin = prompt('Code PIN administrateur requis pour rouvrir :');
        if (pin === null) return;
        fetch('/api/non-conformites/' + id + '/rouvrir?pin=' + encodeURIComponent(pin), { method: 'PATCH' })
            .then(r => r.json())
            .then(data => {
                if (data.detail) { alert('Erreur : ' + data.detail); return; }
                location.reload();
            });
    });

    // ── Sans objet ─────────────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.nc-sans-objet-btn');
        if (!btn) return;
        const id = btn.dataset.id;
        const pin = prompt('Code PIN administrateur requis pour classer sans objet :');
        if (pin === null) return;
        fetch('/api/non-conformites/' + id + '/sans-objet?pin=' + encodeURIComponent(pin), { method: 'PATCH' })
            .then(r => r.json())
            .then(data => {
                if (data.detail) { alert('Erreur : ' + data.detail); return; }
                location.reload();
            });
    });

    // ── Modal helpers ──────────────────────────────────────────────────────
    const modal = document.getElementById('modal-nc');
    const today = new Date().toISOString().slice(0, 10);

    // Session search
    const sessionSearch = document.getElementById('nc-session-search');
    const sessionListe = document.getElementById('nc-session-liste');
    const sessionIdEl = document.getElementById('nc-session-id');
    const clearSessionBtn = document.getElementById('btn-clear-session');
    let _sessionDebounce = null;

    function resetSessionFields() {
        if (sessionIdEl) sessionIdEl.value = '';
        if (sessionSearch) sessionSearch.value = '';
        if (clearSessionBtn) clearSessionBtn.style.display = 'none';
        if (sessionListe) sessionListe.style.display = 'none';
    }

    if (sessionSearch) {
        sessionSearch.addEventListener('input', function () {
            clearTimeout(_sessionDebounce);
            const q = this.value.trim();
            if (!q) {
                sessionIdEl.value = '';
                sessionListe.style.display = 'none';
                clearSessionBtn.style.display = 'none';
                return;
            }
            _sessionDebounce = setTimeout(function () {
                fetch('/api/sessions/search?q=' + encodeURIComponent(q))
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        sessionListe.innerHTML = '';
                        if (!data.length) { sessionListe.style.display = 'none'; return; }
                        data.forEach(function (s) {
                            const li = document.createElement('li');
                            li.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:13px;border-bottom:1px solid #f0f0f0;';
                            li.textContent = s.reference + ' — ' + s.famille + ' (' + s.statut + ')';
                            li.addEventListener('mouseenter', function () { this.style.background = '#f0f4ff'; });
                            li.addEventListener('mouseleave', function () { this.style.background = ''; });
                            li.addEventListener('mousedown', function (e) {
                                e.preventDefault();
                                sessionIdEl.value = s.id;
                                sessionSearch.value = s.reference;
                                sessionListe.style.display = 'none';
                                clearSessionBtn.style.display = 'inline';
                            });
                            sessionListe.appendChild(li);
                        });
                        sessionListe.style.display = 'block';
                    });
            }, 300);
        });

        sessionSearch.addEventListener('blur', function () {
            setTimeout(function () { if (sessionListe) sessionListe.style.display = 'none'; }, 200);
        });
    }

    if (clearSessionBtn) {
        clearSessionBtn.addEventListener('click', function () {
            resetSessionFields();
        });
    }

    function ouvrirModal(nc) {
        document.getElementById('nc-id').value = nc ? nc.id : '';
        document.getElementById('modal-nc-titre').textContent = nc ? 'Modifier la non-conformité' : 'Nouvelle non-conformité';
        document.getElementById('nc-date').value = nc ? nc.date : today;
        document.getElementById('nc-statut').value = nc ? nc.statut : 'ouvert';
        document.getElementById('nc-declarant').value = nc && nc.declarant_id ? String(nc.declarant_id) : '';
        document.getElementById('nc-origine').value = nc ? nc.origine : 'interne';
        document.getElementById('nc-type').value = nc ? nc.type_nc : 'non-conformite';
        document.getElementById('nc-nature').value = nc && nc.nature ? nc.nature : '';
        document.getElementById('nc-titre-input').value = nc ? nc.titre : '';
        document.getElementById('nc-description').value = nc ? nc.description : '';
        document.getElementById('nc-action-preventive').value = nc ? nc.action_preventive : '';
        document.getElementById('nc-action-corrective').value = nc ? nc.action_corrective : '';
        document.getElementById('nc-justificatif-file').value = '';
        const actuelDiv = document.getElementById('nc-justificatif-actuel');
        actuelDiv.textContent = nc && nc.justificatif_nom ? nc.justificatif_nom : '';
        if (nc && nc.session_id) {
            sessionIdEl.value = nc.session_id;
            sessionSearch.value = nc.session_ref || '';
            clearSessionBtn.style.display = 'inline';
        } else {
            resetSessionFields();
        }
        modal.style.display = 'block';
    }

    function fermerModal() {
        modal.style.display = 'none';
        resetSessionFields();
    }

    document.getElementById('btn-nouvelle-nc').addEventListener('click', function () {
        ouvrirModal(null);
    });

    document.getElementById('btn-fermer-nc').addEventListener('click', fermerModal);
    document.getElementById('btn-annuler-nc').addEventListener('click', fermerModal);
    modal.addEventListener('click', function (e) {
        if (e.target === modal) fermerModal();
    });

    // ── Bouton choisir fichier PDF ─────────────────────────────────────────
    document.getElementById('btn-choisir-pdf').addEventListener('click', function () {
        document.getElementById('nc-justificatif-file').click();
    });
    document.getElementById('nc-justificatif-file').addEventListener('change', function () {
        const actuelDiv = document.getElementById('nc-justificatif-actuel');
        actuelDiv.textContent = this.files.length > 0 ? this.files[0].name : '';
    });

    // ── Bouton Modifier ────────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.nc-edit-btn');
        if (!btn) return;
        const id = parseInt(btn.dataset.id);
        const nc = NC_DATA.find(function (x) { return x.id === id; });
        if (nc) ouvrirModal(nc);
    });

    // ── Sauvegarder (créer ou modifier) ───────────────────────────────────
    document.getElementById('btn-sauvegarder-nc').addEventListener('click', function () {
        const id = document.getElementById('nc-id').value;
        const titre = document.getElementById('nc-titre-input').value.trim();
        const dateVal = document.getElementById('nc-date').value;
        if (!titre) { alert('Le titre est obligatoire.'); return; }
        if (!dateVal) { alert('La date est obligatoire.'); return; }

        const fileInput = document.getElementById('nc-justificatif-file');

        function envoyer(pdfB64, pdfNom) {
            const declarantVal = document.getElementById('nc-declarant').value;
            const payload = {
                date: dateVal,
                declarant_id: declarantVal ? parseInt(declarantVal) : null,
                origine: document.getElementById('nc-origine').value,
                type_nc: document.getElementById('nc-type').value,
                nature: document.getElementById('nc-nature').value || null,
                titre: titre,
                statut: document.getElementById('nc-statut').value,
                description: document.getElementById('nc-description').value || null,
                action_preventive: document.getElementById('nc-action-preventive').value || null,
                action_corrective: document.getElementById('nc-action-corrective').value || null,
                justificatif_pdf: pdfB64 || null,
                justificatif_nom: pdfNom || null,
                session_id: sessionSearch.value.trim() ? (parseInt(sessionIdEl.value) || null) : null,
            };
            const url = id ? '/api/non-conformites/' + id : '/api/non-conformites';
            const method = id ? 'PUT' : 'POST';
            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
                .then(r => r.json())
                .then(data => {
                    if (data.detail) { alert('Erreur : ' + data.detail); return; }
                    location.reload();
                });
        }

        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            const reader = new FileReader();
            reader.onload = function (ev) {
                const b64 = ev.target.result.split(',')[1];
                envoyer(b64, file.name);
            };
            reader.readAsDataURL(file);
        } else {
            const nc = NC_DATA.find(function (x) { return x.id === parseInt(id); });
            envoyer(null, nc ? nc.justificatif_nom : null);
        }
    });
});
