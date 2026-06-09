document.addEventListener('DOMContentLoaded', function () {

    chargerStagiaires();
    chargerEmises();

    // --- Sélect stagiaire → charger familles ---
    document.getElementById('sel-stagiaire').addEventListener('change', function () {
        const stagId = this.value;
        const selFamille = document.getElementById('sel-famille');
        selFamille.innerHTML = '<option value="">— —</option>';
        selFamille.disabled = true;
        selFamille.style.color = '#aaa';
        selFamille.style.borderColor = '#ddd';
        selFamille.style.background = '#f7f7f7';
        document.getElementById('section-caces').style.display = 'none';
        if (!stagId) return;
        fetch('/api/cartes-caces/familles/' + stagId)
            .then(r => r.json())
            .then(function (familles) {
                if (!familles.length) {
                    selFamille.innerHTML = '<option value="">Aucun CACES® validé</option>';
                    return;
                }
                selFamille.innerHTML = '<option value="">— Famille —</option>';
                familles.forEach(function (f) {
                    const opt = document.createElement('option');
                    opt.value = f; opt.textContent = f;
                    selFamille.appendChild(opt);
                });
                selFamille.disabled = false;
                selFamille.style.color = '#1a237e';
                selFamille.style.borderColor = '#c8d8f0';
                selFamille.style.background = '#fff';
            });
    });

    // --- PIN modal ---
    document.getElementById('btn-pin-carte-annuler').addEventListener('click', _fermerPin);
    document.getElementById('pin-carte-input').addEventListener('keydown', function (e) {
        if (e.key === 'Enter') document.getElementById('btn-pin-carte-confirmer').click();
    });
    document.getElementById('modal-pin-carte').addEventListener('click', function (e) {
        if (e.target === this) _fermerPin();
    });

    // --- Motif modal ---
    document.getElementById('btn-motif-carte-annuler').addEventListener('click', _fermerMotif);
    document.getElementById('modal-motif-carte').addEventListener('click', function (e) {
        if (e.target === this) _fermerMotif();
    });

    // --- Délégation clics ---
    document.addEventListener('click', function (e) {

        // Voir les CACES®
        const btnVoir = e.target.closest('[data-action="voir-caces"]');
        if (btnVoir) {
            const stagId = document.getElementById('sel-stagiaire').value;
            const famille = document.getElementById('sel-famille').value;
            if (!stagId || !famille) {
                alert('Choisissez un stagiaire et une famille.');
                return;
            }
            _chargerCacesValides(stagId, famille);
            return;
        }

        // Émettre (génère + imprime)
        const btnEmettre = e.target.closest('[data-action="emettre-carte"]');
        if (btnEmettre) {
            const stagId = btnEmettre.dataset.stagId;
            const famille = btnEmettre.dataset.famille;
            const nom = btnEmettre.dataset.nom || '';
            _ouvrirPin('Générer la carte ' + famille + ' pour ' + nom + ' ?', async function (pin) {
                const r = await fetch('/api/cartes-caces/emettre/' + stagId + '/' + encodeURIComponent(famille) + '?pin=' + encodeURIComponent(pin), { method: 'POST' });
                if (r.ok) {
                    const data = await r.json();
                    chargerEmises();
                    _ouvrirImpressionCarte(data);
                }
                return r;
            });
            return;
        }

        // Réimprimer
        const btnReimprimer = e.target.closest('[data-action="reimprimer-carte"]');
        if (btnReimprimer) {
            const id = btnReimprimer.dataset.id;
            fetch('/api/cartes-caces/reimprimer/' + id)
                .then(r => r.ok ? r.json() : Promise.reject(r))
                .then(function (data) { _ouvrirImpressionCarte(data); })
                .catch(function () { alert('Erreur lors de la récupération des données.'); });
            return;
        }

        // Annuler carte
        const btnAnnuler = e.target.closest('[data-action="annuler-carte"]');
        if (btnAnnuler) {
            const id = btnAnnuler.dataset.id;
            const num = btnAnnuler.dataset.num;
            _ouvrirMotif(function (motif) {
                _fermerMotif();
                _ouvrirPin('Annuler la carte ' + num + ' ?', async function (pin) {
                    const r = await fetch('/api/cartes-caces/annuler/' + id + '?pin=' + encodeURIComponent(pin), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motif: motif }),
                    });
                    if (r.ok) chargerEmises();
                    return r;
                });
            });
            return;
        }
    });
});

// ===== ÉTAT =====
let _pinCallback = null;
let _motifCallback = null;

// ===== PIN MODAL =====
function _ouvrirPin(titre, callback) {
    _pinCallback = callback;
    document.getElementById('pin-carte-titre').textContent = titre;
    document.getElementById('pin-carte-input').value = '';
    document.getElementById('pin-carte-erreur').textContent = '';
    document.getElementById('modal-pin-carte').style.display = 'flex';
    setTimeout(function () { document.getElementById('pin-carte-input').focus(); }, 50);

    document.getElementById('btn-pin-carte-confirmer').onclick = async function () {
        const pin = document.getElementById('pin-carte-input').value.trim();
        if (!pin) return;
        const btn = this;
        btn.disabled = true; btn.textContent = '…';
        try {
            const r = await _pinCallback(pin);
            if (r.ok) {
                _fermerPin();
            } else {
                const d = await r.json().catch(() => ({}));
                document.getElementById('pin-carte-erreur').textContent = d.detail || 'Erreur';
            }
        } finally {
            btn.disabled = false; btn.textContent = 'Confirmer';
        }
    };
}

function _fermerPin() {
    document.getElementById('modal-pin-carte').style.display = 'none';
    _pinCallback = null;
}

// ===== MOTIF MODAL =====
function _ouvrirMotif(onConfirme) {
    _motifCallback = onConfirme;
    document.getElementById('motif-carte-input').value = '';
    document.getElementById('motif-carte-erreur').textContent = '​';
    document.getElementById('modal-motif-carte').style.display = 'flex';
    setTimeout(function () { document.getElementById('motif-carte-input').focus(); }, 50);

    document.getElementById('btn-motif-carte-confirmer').onclick = function () {
        const motif = document.getElementById('motif-carte-input').value.trim();
        if (!motif) {
            document.getElementById('motif-carte-erreur').textContent = '⚠️ Le motif est obligatoire.';
            return;
        }
        if (_motifCallback) _motifCallback(motif);
    };
}

function _fermerMotif() {
    document.getElementById('modal-motif-carte').style.display = 'none';
    _motifCallback = null;
}

// ===== UTILITAIRES =====
function _fmtDate(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y;
}

function _fmtDateCourt(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.split('-');
    return d + '/' + m + '/' + y.slice(2);
}

function _noFormate(n) {
    return n ? String(n).padStart(4, '0') : '—';
}

// ===== CHARGEMENT STAGIAIRES =====
async function chargerStagiaires() {
    const sel = document.getElementById('sel-stagiaire');
    try {
        const r = await fetch('/api/cartes-caces/stagiaires');
        if (!r.ok) return;
        const data = await r.json();
        data.forEach(function (s) {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.nom + ' ' + s.prenom;
            sel.appendChild(opt);
        });
    } catch (_) {}
}

// ===== AFFICHAGE CACES VALIDES =====
async function _chargerCacesValides(stagId, famille) {
    const section = document.getElementById('section-caces');
    const infoEl = document.getElementById('info-stagiaire');
    const tableEl = document.getElementById('tableau-caces');
    const btnEmettre = document.getElementById('btn-emettre');

    infoEl.innerHTML = '<p style="color:#718096; padding:8px;">Chargement…</p>';
    tableEl.innerHTML = '';
    section.style.display = 'block';

    try {
        const r = await fetch('/api/cartes-caces/caces-valides/' + stagId + '/' + encodeURIComponent(famille));
        if (!r.ok) throw new Error();
        const data = await r.json();

        // Info stagiaire
        const photoBadge = data.photo_manquante
            ? '<span style="background:#ffebee; color:#c62828; border-radius:6px; padding:3px 10px; font-size:12px; font-weight:700;">📷 Photo manquante — impression bloquée</span>'
            : '<span style="background:#e8f5e9; color:#2e7d32; border-radius:6px; padding:3px 10px; font-size:12px; font-weight:700;">📷 Photo disponible</span>';
        infoEl.innerHTML = '<div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">'
            + '<span style="font-size:16px; font-weight:700; color:#1a237e;">' + data.stagiaire_nom + ' ' + data.stagiaire_prenom + '</span>'
            + '<span style="background:#1a237e; color:#fff; border-radius:6px; padding:2px 10px; font-size:14px; font-weight:800;">' + famille + '</span>'
            + photoBadge
            + '</div>';

        // Tableau CACES®
        if (!data.caces.length) {
            tableEl.innerHTML = '<p style="color:#718096; padding:12px;">Aucun CACES® validé pour cette famille.</p>';
            btnEmettre.style.display = 'none';
        } else {
            const rows = data.caces.map(function (co) {
                const opts = co.options_obtenues
                    ? co.options_obtenues.split(',').map(o => '<span style="background:#e8eaf6;color:#283593;border-radius:3px;padding:1px 5px;font-size:11px;font-weight:700;">' + o.trim() + '</span>').join(' ')
                    : '—';
                return '<tr>'
                    + '<td style="font-weight:700; color:#1a237e; padding:8px 10px;">' + co.categorie + '</td>'
                    + '<td style="font-family:monospace; font-size:13px; padding:8px 10px;"><span style="background:#e8eaf6; padding:2px 8px; border-radius:4px;">' + _noFormate(co.numero_ordre) + '</span></td>'
                    + '<td style="padding:8px 10px;">' + opts + '</td>'
                    + '<td style="font-size:13px; color:#444; padding:8px 10px;">' + _fmtDate(co.date_obtention) + '</td>'
                    + '<td style="font-size:13px; color:#2e7d32; font-weight:700; padding:8px 10px;">' + _fmtDate(co.date_echeance) + '</td>'
                    + '<td style="font-size:12px; color:#666; padding:8px 10px;">' + (co.testeur_nom || '—') + '</td>'
                    + '</tr>';
            }).join('');
            tableEl.innerHTML = '<table class="table">'
                + '<thead><tr>'
                + '<th>Cat.</th><th>N° CACES®</th><th>Options</th><th>Obtention</th><th>Échéance</th><th>Testeur</th>'
                + '</tr></thead><tbody>' + rows + '</tbody></table>';

            // Bouton émettre
            btnEmettre.dataset.stagId = stagId;
            btnEmettre.dataset.famille = famille;
            btnEmettre.dataset.nom = data.stagiaire_nom + ' ' + data.stagiaire_prenom;
            if (data.photo_manquante) {
                btnEmettre.disabled = true;
                btnEmettre.style.background = '#bdbdbd';
                btnEmettre.style.color = '#fff';
                btnEmettre.style.cursor = 'not-allowed';
                btnEmettre.style.boxShadow = 'none';
                btnEmettre.title = 'Photo manquante — ajoutez une photo au stagiaire avant d\'imprimer';
            } else {
                btnEmettre.disabled = false;
                btnEmettre.style.background = '#2e7d32';
                btnEmettre.style.color = '#fff';
                btnEmettre.style.cursor = 'pointer';
                btnEmettre.style.boxShadow = '0 3px 8px rgba(46,125,50,0.3)';
                btnEmettre.title = '';
            }
            btnEmettre.style.display = '';
        }
    } catch (_) {
        infoEl.innerHTML = '<p style="color:red; padding:8px;">Erreur de chargement</p>';
    }
}

// ===== CARTES ÉMISES =====
async function chargerEmises() {
    const el = document.getElementById('liste-emises');
    el.innerHTML = '<p style="color:#718096; text-align:center; padding:24px;">Chargement…</p>';
    try {
        const r = await fetch('/api/cartes-caces/emises');
        if (!r.ok) throw new Error();
        const data = await r.json();
        if (!data.length) {
            el.innerHTML = '<p style="color:#718096; padding:16px;">Aucune carte émise.</p>';
            return;
        }
        const rows = data.map(_renderEmise).join('');
        el.innerHTML = '<table class="table"><thead><tr>'
            + '<th>N° Carte</th><th>Stagiaire</th><th>Famille</th><th>Date</th><th>Statut</th><th></th>'
            + '</tr></thead><tbody>' + rows + '</tbody></table>';
    } catch (_) {
        el.innerHTML = '<p style="color:red; text-align:center; padding:24px;">Erreur de chargement</p>';
    }
}

function _renderEmise(carte) {
    const nomComplet = carte.stagiaire_nom + ' ' + carte.stagiaire_prenom;
    const emise = carte.statut === 'emise';
    const remplacee = carte.statut === 'remplacee';
    const annulee = carte.statut === 'annulee';

    const badgeHtml = emise
        ? '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">Émise</span>'
        : remplacee
        ? '<span class="badge" style="background:#f5f5f5;color:#888;">Remplacée</span>'
        : '<span class="badge" style="background:#ffebee;color:#c62828;">Annulée</span>';

    const motifHtml = (annulee || remplacee) && carte.motif_annulation
        ? '<div style="font-size:11px;color:#888;margin-top:2px;font-style:italic;">' + carte.motif_annulation + '</div>'
        : '';

    const actionsHtml = emise
        ? '<div style="display:flex;gap:6px;">'
            + '<button data-action="reimprimer-carte" data-id="' + carte.id + '" title="Réimprimer" '
            + 'style="background:none;border:1px solid #1a237e;color:#1a237e;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">🖨️</button>'
            + '<button data-action="annuler-carte" data-id="' + carte.id + '" data-num="' + carte.numero_carte + '" title="Annuler" '
            + 'style="background:none;border:1px solid #c62828;color:#c62828;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;">❌</button>'
            + '</div>'
        : '';

    const opacity = emise ? '' : 'opacity:0.5;';
    const strike = emise ? '' : 'text-decoration:line-through;';

    return '<tr style="' + opacity + '">'
        + '<td style="font-family:monospace;font-size:13px;font-weight:700;color:#1a237e;white-space:nowrap;' + strike + '">' + carte.numero_carte + '</td>'
        + '<td style="font-weight:600;font-size:13px;">' + nomComplet + motifHtml + '</td>'
        + '<td><span style="background:#1a237e;color:#fff;border-radius:5px;padding:2px 8px;font-size:12px;font-weight:800;">' + carte.famille + '</span></td>'
        + '<td style="font-size:12px;color:#666;white-space:nowrap;">' + _fmtDate(carte.date_generation) + '</td>'
        + '<td>' + badgeHtml + '</td>'
        + '<td>' + actionsHtml + '</td>'
        + '</tr>';
}

// ===== IMPRESSION =====
function _ouvrirImpressionCarte(data) {
    const nbCats = data.caces.length;
    const format = nbCats <= 4 ? 'cr80' : 'a5';
    const w = window.open('', '_blank');
    if (!w) {
        alert('Autorisez les popups pour imprimer.');
        return;
    }
    w.document.write(_buildCarteHtml(data, format));
    w.document.close();
    w.focus();
    setTimeout(function () { w.print(); }, 700);
}

function _buildCarteHtml(data, format) {
    const isCr80 = format === 'cr80';

    const logoHtml = data.config.logo_uri
        ? '<img src="' + data.config.logo_uri + '" style="height:' + (isCr80 ? '7mm' : '14mm') + ';width:auto;max-width:' + (isCr80 ? '14mm' : '28mm') + ';object-fit:contain;" />'
        : '';

    const photoHtml = data.photo_url
        ? '<img src="' + data.photo_url + '" style="width:' + (isCr80 ? '14mm' : '28mm') + ';height:' + (isCr80 ? '18mm' : '36mm') + ';object-fit:cover;border:0.5mm solid #ccc;border-radius:1mm;display:block;" />'
        : '<div style="width:' + (isCr80 ? '14mm' : '28mm') + ';height:' + (isCr80 ? '18mm' : '36mm') + ';background:#f0f0f0;border:0.5mm solid #ccc;border-radius:1mm;display:flex;align-items:center;justify-content:center;"><span style="font-size:' + (isCr80 ? '5pt' : '9pt') + ';color:#aaa;">Photo</span></div>';

    const caceRows = data.caces.map(function (co) {
        const no = co.numero_ordre ? String(co.numero_ordre).padStart(4, '0') : '—';
        const opts = co.options_obtenues ? co.options_obtenues : '';
        if (isCr80) {
            return '<tr>'
                + '<td style="font-weight:700;color:#1a237e;">' + co.categorie + '</td>'
                + '<td style="font-family:monospace;">' + no + '</td>'
                + (opts ? '<td>' + opts + '</td>' : '')
                + '<td>' + _fmtDateCourt(co.date_obtention) + '</td>'
                + '<td>' + _fmtDateCourt(co.date_echeance) + '</td>'
                + '</tr>';
        } else {
            return '<tr>'
                + '<td style="font-weight:700;color:#1a237e;">' + co.categorie + '</td>'
                + '<td style="font-family:monospace;">' + no + '</td>'
                + '<td>' + (opts || '—') + '</td>'
                + '<td>' + _fmtDate(co.date_obtention) + '</td>'
                + '<td>' + _fmtDate(co.date_echeance) + '</td>'
                + '<td style="color:#666;">' + (co.testeur_nom || '') + '</td>'
                + '</tr>';
        }
    }).join('');

    const hasOpts = data.caces.some(function (co) { return co.options_obtenues; });

    const tableHead = isCr80
        ? '<tr><th>Cat.</th><th>N° CACES®</th>' + (hasOpts ? '<th>Options</th>' : '') + '<th>Obtention</th><th>Échéance</th></tr>'
        : '<tr><th>Catégorie</th><th>N° CACES®</th><th>Options</th><th>Obtention</th><th>Échéance</th><th>Testeur</th></tr>';

    if (isCr80) {
        return '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>'
            + '* { margin:0; padding:0; box-sizing:border-box; }'
            + '@page { size: 85.6mm 54mm; margin: 0; }'
            + 'body { width:85.6mm; height:54mm; font-family:Arial,sans-serif; background:white; overflow:hidden; }'
            + '.carte { width:85.6mm; height:54mm; padding:2.5mm; display:flex; flex-direction:column; }'
            + '.header { display:flex; align-items:center; justify-content:space-between; margin-bottom:1.5mm; }'
            + '.org { font-size:5.5pt; font-weight:bold; color:#1a237e; flex:1; text-align:center; padding:0 1mm; }'
            + '.num-carte { font-size:5pt; font-family:monospace; color:#1a237e; font-weight:bold; white-space:nowrap; }'
            + '.divider { height:0.3mm; background:#1a237e; margin-bottom:1.5mm; }'
            + '.body { display:flex; gap:2mm; flex:1; min-height:0; }'
            + '.info { flex:1; min-width:0; }'
            + '.nom { font-size:7pt; font-weight:bold; color:#1a237e; }'
            + '.prenom { font-size:6pt; color:#555; margin-bottom:1mm; }'
            + '.famille-badge { display:inline-block; background:#1a237e; color:white; font-size:5pt; font-weight:bold; padding:0.3mm 1.5mm; border-radius:1mm; margin-bottom:1mm; }'
            + 'table { width:100%; border-collapse:collapse; }'
            + 'th { font-size:4pt; text-transform:uppercase; color:#666; text-align:left; padding:0.4mm 0.5mm; border-bottom:0.2mm solid #ccc; }'
            + 'td { font-size:5pt; padding:0.3mm 0.5mm; }'
            + '.footer { font-size:4pt; color:#aaa; text-align:center; margin-top:1mm; border-top:0.2mm solid #eee; padding-top:0.5mm; }'
            + '@media print { body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }'
            + '</style></head><body>'
            + '<div class="carte">'
            + '  <div class="header">'
            + '    ' + logoHtml
            + '    <span class="org">' + (data.config.nom_organisme || 'Certificat CACES®') + '</span>'
            + '    <span class="num-carte">' + data.numero_carte + '</span>'
            + '  </div>'
            + '  <div class="divider"></div>'
            + '  <div class="body">'
            + '    <div>' + photoHtml + '</div>'
            + '    <div class="info">'
            + '      <div class="nom">' + data.stagiaire_nom + '</div>'
            + '      <div class="prenom">' + data.stagiaire_prenom + '</div>'
            + '      <span class="famille-badge">' + data.famille + '</span>'
            + '      <table><thead>' + tableHead + '</thead><tbody>' + caceRows + '</tbody></table>'
            + '    </div>'
            + '  </div>'
            + (data.config.url_verification_caces ? '<div class="footer">Vérification : ' + data.config.url_verification_caces + '</div>' : '')
            + '</div>'
            + '</body></html>';
    } else {
        // Format A5 landscape
        return '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>'
            + '* { margin:0; padding:0; box-sizing:border-box; }'
            + '@page { size: A5 landscape; margin: 0; }'
            + 'body { width:210mm; height:148mm; font-family:Arial,sans-serif; background:white; overflow:hidden; }'
            + '.carte { width:210mm; height:148mm; padding:8mm; display:flex; flex-direction:column; }'
            + '.header { display:flex; align-items:center; justify-content:space-between; margin-bottom:4mm; }'
            + '.org { font-size:11pt; font-weight:bold; color:#1a237e; flex:1; text-align:center; padding:0 4mm; }'
            + '.num-carte { font-size:9pt; font-family:monospace; color:#1a237e; font-weight:bold; white-space:nowrap; }'
            + '.divider { height:0.5mm; background:#1a237e; margin-bottom:4mm; }'
            + '.body { display:flex; gap:6mm; flex:1; min-height:0; }'
            + '.info { flex:1; min-width:0; }'
            + '.nom { font-size:14pt; font-weight:bold; color:#1a237e; }'
            + '.prenom { font-size:11pt; color:#555; margin-bottom:3mm; }'
            + '.famille-badge { display:inline-block; background:#1a237e; color:white; font-size:10pt; font-weight:bold; padding:1mm 3mm; border-radius:2mm; margin-bottom:3mm; }'
            + 'table { width:100%; border-collapse:collapse; }'
            + 'th { font-size:8pt; text-transform:uppercase; color:#666; text-align:left; padding:2mm 2.5mm; border-bottom:0.4mm solid #ccc; background:#f5f5f5; }'
            + 'td { font-size:10pt; padding:2mm 2.5mm; border-bottom:0.2mm solid #f0f0f0; }'
            + '.footer { font-size:8pt; color:#aaa; text-align:center; margin-top:3mm; border-top:0.3mm solid #eee; padding-top:2mm; }'
            + '@media print { body { -webkit-print-color-adjust:exact; print-color-adjust:exact; } }'
            + '</style></head><body>'
            + '<div class="carte">'
            + '  <div class="header">'
            + '    ' + logoHtml
            + '    <span class="org">' + (data.config.nom_organisme || 'Certificat CACES®') + '</span>'
            + '    <span class="num-carte">' + data.numero_carte + '</span>'
            + '  </div>'
            + '  <div class="divider"></div>'
            + '  <div class="body">'
            + '    <div>' + photoHtml + '</div>'
            + '    <div class="info">'
            + '      <div class="nom">' + data.stagiaire_nom + '</div>'
            + '      <div class="prenom">' + data.stagiaire_prenom + '</div>'
            + '      <span class="famille-badge">' + data.famille + '</span>'
            + '      <table><thead>' + tableHead + '</thead><tbody>' + caceRows + '</tbody></table>'
            + '    </div>'
            + '  </div>'
            + (data.config.url_verification_caces ? '<div class="footer">Vérification : ' + data.config.url_verification_caces + '</div>' : '')
            + '</div>'
            + '</body></html>';
    }
}
