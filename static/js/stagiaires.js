document.addEventListener('DOMContentLoaded', function () {

    // ── Recherche ──────────────────────────────────────────────────────────
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const q = this.value.toLowerCase();
            document.querySelectorAll('#tbody tr').forEach(function (tr) {
                tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
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
            const rows = Array.from(tbody.querySelectorAll('tr'));
            rows.sort(function (a, b) {
                const cell_a = a.cells[colIdx];
                const cell_b = b.cells[colIdx];
                const va = (cell_a.dataset.date || cell_a.textContent.trim()).toLowerCase();
                const vb = (cell_b.dataset.date || cell_b.textContent.trim()).toLowerCase();
                return sortAsc ? (va < vb ? -1 : va > vb ? 1 : 0) : (va < vb ? 1 : va > vb ? -1 : 0);
            });
            rows.forEach(function (row) { tbody.appendChild(row); });
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
});
