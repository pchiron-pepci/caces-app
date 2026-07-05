(function () {
  'use strict';
  var SEUIL = 6;
  var LIGNES = [];
  var SORT = { key: 'date_echeance', asc: true };

  var NAT = { otc: 'OTC', st: 'S/T', ext: 'Externe' };
  var STA = {
    exp: { lib: 'Expiré', c: '#a32d2d' },
    ren: { lib: 'À renouveler', c: '#854f0b' },
    val: { lib: 'Valide', c: '#3b6d11' }
  };

  function frDate(iso) {
    if (!iso) return '—';
    var p = iso.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function charger() {
    fetch('/api/registre-caces?seuil=' + SEUIL)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        LIGNES = data.lignes || [];
        peuplerSelect('rc-f-soc', data.societes || []);
        peuplerSelect('rc-f-fam', data.familles || []);
        render();
      })
      .catch(function () {
        document.getElementById('rc-tbody').innerHTML =
          '<tr><td colspan="7" class="rc-empty">Erreur de chargement.</td></tr>';
      });
  }

  function peuplerSelect(id, valeurs) {
    var sel = document.getElementById(id);
    var courant = sel.value;
    sel.innerHTML = '<option value="">' + (id === 'rc-f-soc' ? 'Toutes' : 'Toutes') + '</option>';
    valeurs.forEach(function (v) {
      var o = document.createElement('option');
      o.value = v; o.textContent = v;
      sel.appendChild(o);
    });
    sel.value = courant;
  }

  function trier(rows) {
    var k = SORT.key, asc = SORT.asc ? 1 : -1;
    return rows.slice().sort(function (a, b) {
      var va, vb;
      if (k === 'cat') { va = a.famille + a.categorie; vb = b.famille + b.categorie; }
      else if (k === 'nom') { va = a.nom + a.prenom; vb = b.nom + b.prenom; }
      else { va = a[k] || ''; vb = b[k] || ''; }
      if (va < vb) return -1 * asc;
      if (va > vb) return 1 * asc;
      return 0;
    });
  }

  function render() {
    var soc = document.getElementById('rc-f-soc').value;
    var fam = document.getElementById('rc-f-fam').value;
    var nat = document.getElementById('rc-f-nat').value;
    var txt = document.getElementById('rc-f-txt').value.toLowerCase();
    var sExp = document.getElementById('rc-c-exp').checked;
    var sRen = document.getElementById('rc-c-ren').checked;
    var sVal = document.getElementById('rc-c-val').checked;

    var rows = LIGNES.filter(function (l) {
      if (soc && l.societe !== soc) return false;
      if (fam && l.famille !== fam) return false;
      if (nat && l.nature !== nat) return false;
      if (txt && (l.nom + ' ' + l.prenom + ' ' + l.societe).toLowerCase().indexOf(txt) < 0) return false;
      var st = l.statut_echeance;
      if (st === 'exp' && !sExp) return false;
      if (st === 'ren' && !sRen) return false;
      if (st === 'val' && !sVal) return false;
      return true;
    });

    rows = trier(rows);
    var tbody = document.getElementById('rc-tbody');

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="rc-empty">Aucun CACES® ne correspond aux filtres.</td></tr>';
    } else {
      tbody.innerHTML = rows.map(function (l) {
        var sa = STA[l.statut_echeance] || STA.val;
        var natCls = 'rc-nat rc-nat-' + l.nature;
        return '<tr>'
          + '<td>' + esc(l.prenom) + ' ' + esc(l.nom) + '</td>'
          + '<td style="color:#6b6a65;">' + (esc(l.societe) || '—') + '</td>'
          + '<td><b>' + esc(l.famille) + '</b> ' + esc(l.categorie) + '</td>'
          + '<td><span class="' + natCls + '">' + (NAT[l.nature] || '?') + '</span></td>'
          + '<td style="color:#6b6a65;">' + frDate(l.date_obtention) + '</td>'
          + '<td>' + frDate(l.date_echeance) + '</td>'
          + '<td><span class="rc-sta" style="color:' + sa.c + ';"><span class="rc-dot" style="background:' + sa.c + ';"></span>' + sa.lib + '</span></td>'
          + '</tr>';
      }).join('');
    }
    document.getElementById('rc-count').textContent =
      rows.length + ' CACES® affiché' + (rows.length > 1 ? 's' : '');
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function setSeuil(m) {
    SEUIL = m;
    document.getElementById('rc-seuil-lbl').textContent = m;
    document.querySelectorAll('.rc-seuil').forEach(function (b) {
      b.classList.toggle('actif', parseInt(b.dataset.m, 10) === m);
    });
    charger();
  }

  function exporter() {
    var params = new URLSearchParams({
      seuil: SEUIL,
      soc: document.getElementById('rc-f-soc').value,
      fam: document.getElementById('rc-f-fam').value,
      nat: document.getElementById('rc-f-nat').value,
      txt: document.getElementById('rc-f-txt').value,
      exp: document.getElementById('rc-c-exp').checked ? '1' : '0',
      ren: document.getElementById('rc-c-ren').checked ? '1' : '0',
      val: document.getElementById('rc-c-val').checked ? '1' : '0'
    });
    window.location = '/api/registre-caces/export?' + params.toString();
  }

  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-action]');
    if (!el) return;
    var a = el.dataset.action;
    if (a === 'rc-seuil') { setSeuil(parseInt(el.dataset.m, 10)); }
    else if (a === 'rc-sort') {
      var k = el.dataset.key;
      if (SORT.key === k) { SORT.asc = !SORT.asc; } else { SORT.key = k; SORT.asc = true; }
      render();
    }
    else if (a === 'rc-export') { exporter(); }
  });

  document.addEventListener('change', function (e) {
    if (e.target.closest('#rc-f-soc, #rc-f-fam, #rc-f-nat') || e.target.type === 'checkbox') render();
  });

  var champTxt = document.getElementById('rc-f-txt');
  if (champTxt) champTxt.addEventListener('input', render);

  charger();
})();
