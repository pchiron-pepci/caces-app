// Photo modal — Cropper.js 35:45, stockage base64 PostgreSQL
// Utilisé dans session_detail.html et stagiaires.html

var _photoCropper = null;
var _photoStagiaireId = null;

function ouvrirPhotoModal(stagiaireId, nom, existingPhotoSrc) {
    _photoStagiaireId = stagiaireId;

    document.getElementById('photo-modal-nom').textContent = nom;

    var previewSection = document.getElementById('photo-modal-preview-section');
    if (existingPhotoSrc) {
        document.getElementById('photo-modal-preview').src = existingPhotoSrc;
        previewSection.style.display = 'block';
    } else {
        previewSection.style.display = 'none';
    }

    document.getElementById('photo-modal-cropper-section').style.display = 'none';
    var btnValider = document.getElementById('photo-modal-valider');
    btnValider.style.display = 'none';
    btnValider.disabled = false;
    btnValider.textContent = 'Valider ✓';

    document.getElementById('photo-input-camera').value = '';
    document.getElementById('photo-input-import').value = '';

    if (_photoCropper) { _photoCropper.destroy(); _photoCropper = null; }

    document.getElementById('modal-photo').style.display = 'flex';
}

function fermerPhotoModal() {
    document.getElementById('modal-photo').style.display = 'none';
    if (_photoCropper) { _photoCropper.destroy(); _photoCropper = null; }
}

function _chargerFichierPhoto(file) {
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        var img = document.getElementById('photo-cropper-img');
        img.src = e.target.result;

        document.getElementById('photo-modal-preview-section').style.display = 'none';
        document.getElementById('photo-modal-cropper-section').style.display = 'block';
        document.getElementById('photo-modal-valider').style.display = 'block';
        document.getElementById('photo-modal-valider').disabled = false;
        document.getElementById('photo-modal-valider').textContent = 'Valider ✓';

        if (_photoCropper) { _photoCropper.destroy(); }
        _photoCropper = new Cropper(img, {
            aspectRatio: 35 / 45,
            viewMode: 1,
            dragMode: 'move',
            autoCropArea: 0.9,
            restore: false,
            guides: true,
            center: true,
            highlight: false,
            cropBoxResizable: true,
            toggleDragModeOnDblclick: false,
            zoomOnTouch: true,
            zoomOnWheel: true,
        });
    };
    reader.readAsDataURL(file);
}

function _clearPhotoCells(stagiaireId) {
    document.querySelectorAll('.photo-cell[data-stag-id="' + stagiaireId + '"]').forEach(function(cell) {
        var img = cell.querySelector('img.photo-img');
        if (img) img.remove();
        var ov = cell.querySelector('.photo-overlay');
        if (ov) ov.remove();
        if (!cell.querySelector('.photo-placeholder')) {
            var ph = document.createElement('div');
            ph.className = 'photo-placeholder';
            ph.style.fontSize = '20px';
            ph.textContent = '👤';
            cell.appendChild(ph);
        }
    });
}

function _updatePhotoCells(stagiaireId, base64DataUri) {
    document.querySelectorAll('.photo-cell[data-stag-id="' + stagiaireId + '"]').forEach(function(cell) {
        var ph = cell.querySelector('.photo-placeholder');
        if (ph) ph.remove();
        var img = cell.querySelector('img.photo-img');
        if (!img) {
            img = document.createElement('img');
            img.className = 'photo-img';
            cell.insertBefore(img, cell.firstChild);
        }
        img.src = base64DataUri;
        if (!cell.querySelector('.photo-overlay')) {
            var ov = document.createElement('div');
            ov.className = 'photo-overlay';
            ov.textContent = '✎';
            cell.appendChild(ov);
        }
    });
}

async function supprimerPhoto() {
    if (!_photoStagiaireId) return;
    if (!confirm('Supprimer la photo ?')) return;
    try {
        var resp = await fetch('/stagiaires/' + _photoStagiaireId + '/photo', { method: 'DELETE' });
        if (resp.ok) {
            _clearPhotoCells(_photoStagiaireId);
            fermerPhotoModal();
        } else {
            var err = await resp.json().catch(function() { return {}; });
            alert('Erreur : ' + (err.detail || 'Échec de la suppression'));
        }
    } catch(e) {
        alert('Erreur réseau.');
    }
}

async function validerPhoto() {
    if (!_photoCropper || !_photoStagiaireId) return;
    var btn = document.getElementById('photo-modal-valider');
    btn.disabled = true;
    btn.textContent = 'Enregistrement…';

    var canvas = _photoCropper.getCroppedCanvas({ maxWidth: 467, maxHeight: 600 });
    var base64DataUri = canvas.toDataURL('image/jpeg', 0.8);

    try {
        var resp = await fetch('/stagiaires/' + _photoStagiaireId + '/photo-upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ photo_base64: base64DataUri })
        });
        if (resp.ok) {
            _updatePhotoCells(_photoStagiaireId, base64DataUri);
            fermerPhotoModal();
        } else {
            var err = await resp.json().catch(function() { return {}; });
            alert('Erreur : ' + (err.detail || 'Échec de l\'enregistrement'));
            btn.disabled = false;
            btn.textContent = 'Valider ✓';
        }
    } catch(e) {
        alert('Erreur réseau.');
        btn.disabled = false;
        btn.textContent = 'Valider ✓';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('photo-input-camera').addEventListener('change', function() {
        _chargerFichierPhoto(this.files[0]);
    });
    document.getElementById('photo-input-import').addEventListener('change', function() {
        _chargerFichierPhoto(this.files[0]);
    });

    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-action="supprimer-photo"]')) {
            supprimerPhoto();
            return;
        }
        var cell = e.target.closest('.photo-cell[data-stag-id]');
        if (!cell) return;
        var img = cell.querySelector('img.photo-img');
        var existingSrc = img ? img.src : null;
        ouvrirPhotoModal(cell.dataset.stagId, cell.dataset.stagNom, existingSrc);
    });

    var modalPhoto = document.getElementById('modal-photo');
    if (modalPhoto) {
        modalPhoto.addEventListener('click', function(e) {
            if (e.target === modalPhoto) fermerPhotoModal();
        });
    }
});
