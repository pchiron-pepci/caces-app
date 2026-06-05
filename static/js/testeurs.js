let idAArchiver = null;

function ouvrirFormulaire() {
    document.getElementById('modal-title').textContent = 'Nouveau testeur';
    document.getElementById('testeur-id').value = '';
    document.getElementById('f-nom').value = '';
    document.getElementById('f-prenom').value = '';
    document.getElementById('f-statut').value = 'interne';
    document.getElementById('f-entreprise').value = '';
    document.getElementById('f-email').value = '';
    document.getElementById('f-tel').value = '';
    document.getElementById('f-inrs').value = '';
    document.getElementById('f-habilitation').value = '';
    document.getElementById('f-expiration').value = '';
    document.getElementById('f-visite').value = '';
    document.getElementById('f-formation').value = '';
    document.getElementById('f-controle').value = '';
    document.getElementById('f-note').value = '';
    document.getElementById('modal').style.display = 'flex';
}

function editer(id, nom, prenom, statut, entreprise, inrs, email, tel, habilitation, expiration, visite, formation, controle, note) {
    document.getElementById('modal-title').textContent = 'Modifier testeur';
    document.getElementById('testeur-id').value = id;
    document.getElementById('f-nom').value = nom;
    document.getElementById('f-prenom').value = prenom;
    document.getElementById('f-statut').value = statut;
    document.getElementById('f-entreprise').value = entreprise;
    document.getElementById('f-inrs').value = inrs;
    document.getElementById('f-email').value = email;
    document.getElementById('f-tel').value = tel;
    document.getElementById('f-habilitation').value = habilitation;
    document.getElementById('f-expiration').value = expiration;
    document.getElementById('f-visite').value = visite;
    document.getElementById('f-formation').value = formation;
    document.getElementById('f-controle').value = controle;
    document.getElementById('f-note').value = note;
    document.getElementById('modal').style.display = 'flex';
}

function fermerModal() {
    document.getElementById('modal').style.display = 'none';
}

async function sauvegarder() {
    const id = document.getElementById('testeur-id').value;
    const data = {
        nom: document.getElementById('f-nom').value.toUpperCase(),
        prenom: document.getElementById('f-prenom').value,
        statut: document.getElementById('f-statut').value,
        entreprise: document.getElementById('f-entreprise').value || null,
        email: document.getElementById('f-email').value || null,
        telephone: document.getElementById('f-tel').value || null,
        numero_inrs: document.getElementById('f-inrs').value || null,
        date_habilitation: document.getElementById('f-habilitation').value || null,
        date_expiration_habilitation: document.getElementById('f-expiration').value || null,
        visite_medicale: document.getElementById('f-visite').value || null,
        formation_continue: document.getElementById('f-formation').value || null,
        date_prochain_controle: document.getElementById('f-controle').value || null,
        note: document.getElementById('f-note').value || null
    };
    if (!data.nom || !data.prenom) { alert('Nom et prénom sont obligatoires !'); return; }
    const url = id ? `/api/testeurs/${id}` : '/api/testeurs/';
    const method = id ? 'PUT' : 'POST';
    const resp = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) { fermerModal(); location.reload(); }
    else alert('Erreur lors de la sauvegarde !');
}

function archiver(id, nom) {
    idAArchiver = id;
    document.getElementById('pin-message').textContent = `Archiver "${nom}" ?`;
    document.getElementById('pin-input').value = '';
    document.getElementById('pin-error').style.display = 'none';
    document.getElementById('modal-pin').style.display = 'flex';
    document.getElementById('pin-confirm-btn').onclick = async () => {
        const pin = document.getElementById('pin-input').value;
        const resp = await fetch(`/api/testeurs/${idAArchiver}?pin=${pin}`, { method: 'DELETE' });
        if (resp.ok) { fermerPin(); location.reload(); }
        else document.getElementById('pin-error').style.display = 'block';
    };
}

function fermerPin() {
    document.getElementById('modal-pin').style.display = 'none';
}

function filtrer() {
    const q = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('#tbody tr').forEach(tr => {
        tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}