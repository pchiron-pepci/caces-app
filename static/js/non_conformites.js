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
        modal.style.display = 'block';
    }

    function fermerModal() {
        modal.style.display = 'none';
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
