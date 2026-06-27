(function () {
  "use strict";

  var BODY = document.body;
  var SESSION_ID = BODY.dataset.sessionId;
  var JOUR_ID = BODY.dataset.jourTestId;
  var STAGIAIRE_ID = BODY.dataset.stagiaireId;
  var CATEGORIE = BODY.dataset.categorie;
  var BASE = "/api/sessions/" + SESSION_ID + "/pratique/saisie/";

  var state = {
    saisieId: null,
    mode: "binaire",
    statut: "en_cours",
    blocs: [],            // [{bloc_id, grille, notes{item_id:note}, elim:[crit_id]}]
    dirty: {},            // bloc_id -> true (modifs non synchronisees)
    online: navigator.onLine
  };

  function toast(msg) {
    var t = document.getElementById("sp-toast");
    t.textContent = msg; t.style.display = "block";
    clearTimeout(t._h); t._h = setTimeout(function () { t.style.display = "none"; }, 2000);
  }

  function api(method, url, body) {
    return fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || ("HTTP " + r.status)); });
      return r.json();
    });
  }

  // ─── Saisie adaptative : produit les controles selon mode + bareme ───
  function controlesItem(bloc, item) {
    if (item.descriptif_seul) {
      return '<div class="sp-item-desc">— ' + escapeHtml(item.libelle) + '</div>';
    }
    var bareme = item.bareme_max;
    var note = bloc.notes[item.id];
    var critHtml = item.critere_evaluation
      ? '<div class="sp-crit"><span class="sp-crit-ic">!</span> ' + escapeHtml(item.critere_evaluation) + '</div>'
      : '';
    var html = '<div class="sp-item"><div class="sp-item-lib">' + escapeHtml(item.libelle) + '</div>' + critHtml;
    html += '<div class="sp-item-saisie"><span class="sp-item-bareme">/' + fmt(bareme) + '</span>';

    if (state.mode === "binaire") {
      html += '<div style="display:flex;gap:4px;">'
        + btnBin(item.id, "ok", note === bareme)
        + btnBin(item.id, "ko", note === 0)
        + '</div>';
    } else {
      var pas = (state.mode === "partiel_demi") ? 0.5 : 1;
      // bareme <=3 -> paliers ; sinon stepper +/- pas
      if (bareme <= 3) {
        html += '<div class="sp-paliers" data-item="' + item.id + '">';
        for (var v = 0; v <= bareme + 1e-9; v += pas) {
          var on = (note === v) ? " on" : "";
          html += '<button class="sp-palier' + on + '" data-action="palier" data-item="' + item.id + '" data-val="' + v + '">' + fmt(v) + '</button>';
        }
        html += '</div>';
      } else {
        var cur = (note == null) ? 0 : note;
        html += '<div class="sp-step" data-item="' + item.id + '">'
          + '<button data-action="step" data-item="' + item.id + '" data-dir="-1" data-pas="' + pas + '">−</button>'
          + '<div class="sp-step-val" id="stepval-' + item.id + '">' + fmt(cur) + '</div>'
          + '<button data-action="step" data-item="' + item.id + '" data-dir="1" data-pas="' + pas + '" data-max="' + bareme + '">+</button>'
          + '<span class="sp-item-bareme">/ ' + fmt(bareme) + '</span></div>';
      }
    }
    html += '</div></div>';
    return html;
  }

  function btnBin(itemId, kind, on) {
    var cls = "sp-btn-bin" + (on ? (kind === "ok" ? " ok-on" : " ko-on") : "");
    var sym = kind === "ok" ? "✓" : "✗";
    return '<button class="' + cls + '" data-action="bin" data-item="' + itemId + '" data-kind="' + kind + '" aria-label="' + (kind === "ok" ? "Acquis" : "Non acquis") + '">' + sym + '</button>';
  }

  function renderBloc(bloc) {
    var g = bloc.grille;
    var html = "";
    if (g.type === "option") {
      html += '<div class="sp-bloc-titre"><div class="sp-bloc-line"></div>'
        + '<span class="sp-bloc-label">Option · ' + escapeHtml(g.libelle) + '</span>'
        + '<div class="sp-bloc-line"></div></div>';
    }
    g.themes.forEach(function (th, i) {
      var openCls = (i === 0 && g.type === "base") ? " open" : "";
      html += '<div class="sp-theme' + openCls + '" data-theme="' + th.id + '">';
      html += '<div class="sp-theme-head" data-action="toggle-theme">'
        + '<span class="sp-theme-titre"><span class="sp-chevron">▶</span>' + escapeHtml(th.libelle) + '</span>'
        + '<span class="sp-theme-score" id="score-' + bloc.bloc_id + '-' + th.id + '">—/' + fmt(th.bareme_theme) + ' · min ' + fmt(th.seuil) + '</span></div>';
      html += '<div class="sp-theme-body">';
      th.points.forEach(function (pe) {
        html += '<div class="sp-pe">';
        html += '<div class="sp-pe-head"><span class="sp-pe-badge" id="pebadge-' + bloc.bloc_id + '-' + pe.id + '">PE ' + pe.numero + '</span>';
        if (pe.libelle_chapeau) html += '<span class="sp-pe-chapeau">' + escapeHtml(pe.libelle_chapeau) + '</span>';
        html += '</div>';
        pe.items.forEach(function (item) { html += controlesItem(bloc, item); });
        html += '</div>';
      });
      html += '</div></div>';
    });
    // eliminatoires (une fois par bloc)
    if (g.eliminatoires && g.eliminatoires.length) {
      html += '<div class="sp-elim" data-bloc="' + bloc.bloc_id + '">'
        + '<div class="sp-elim-titre">⚠ Critères éliminatoires (échec direct)</div>';
      g.eliminatoires.forEach(function (c) {
        var checked = bloc.elim.indexOf(c.id) >= 0 ? " checked" : "";
        html += '<label><input type="checkbox" data-action="elim" data-bloc="' + bloc.bloc_id + '" data-crit="' + c.id + '"' + checked + '> ' + escapeHtml(c.libelle) + '</label>';
      });
      html += '</div>';
    }
    return html;
  }

  function renderAll() {
    var box = document.getElementById("sp-blocs");
    box.innerHTML = state.blocs.map(renderBloc).join("");
    document.getElementById("sp-mode-badge").textContent = modeLabel(state.mode);
    if (window.majProgression) window.majProgression();
    if (window.majScores) window.majScores();
  }

  function modeLabel(m) {
    if (m === "partiel_demi") return "Partiel ½ point";
    if (m === "partiel_entier") return "Partiel (entier)";
    return "Binaire";
  }

  function escapeHtml(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmt(n) {
    if (n == null) return "—";
    return (Math.round(n * 100) / 100).toString().replace(".", ",");
  }

  // expose pour les blocs suivants
  window._SP = { state: state, api: api, BASE: BASE, toast: toast, renderAll: renderAll, fmt: fmt };

  // ─── Chargement initial ───
  api("POST", BASE + JOUR_ID + "/" + STAGIAIRE_ID + "/" + CATEGORIE + "/ouvrir")
    .then(function (data) {
      state.saisieId = data.saisie_id;
      state.mode = data.mode;
      state.statut = data.statut;
      state.blocs = data.blocs.map(function (b) {
        return {
          bloc_id: b.bloc_id, grille: b.grille,
          notes: b.notes_saisies || {}, elim: b.eliminatoires_coches || []
        };
      });
      renderAll();
      if (data.reprise) toast("Saisie reprise");
      if (window._SP && typeof window._SP.runCalc === "function") { window._SP.runCalc(); }
    })
    .catch(function (e) {
      document.getElementById("sp-progress-txt").textContent = "Erreur : " + e.message;
    });

})();

(function () {
  "use strict";
  var SP = window._SP;
  var state = SP.state, api = SP.api, BASE = SP.BASE, toast = SP.toast, fmt = SP.fmt;

  function blocById(id) {
    for (var i = 0; i < state.blocs.length; i++) if (state.blocs[i].bloc_id == id) return state.blocs[i];
    return null;
  }
  function blocOfItem(itemId) {
    for (var i = 0; i < state.blocs.length; i++) {
      var b = state.blocs[i];
      var found = b.grille.themes.some(function (th) {
        return th.points.some(function (pe) {
          return pe.items.some(function (it) { return it.id == itemId; });
        });
      });
      if (found) return b;
    }
    return null;
  }
  function itemDef(itemId) {
    for (var i = 0; i < state.blocs.length; i++) {
      var th = state.blocs[i].grille.themes;
      for (var t = 0; t < th.length; t++)
        for (var p = 0; p < th[t].points.length; p++)
          for (var k = 0; k < th[t].points[p].items.length; k++)
            if (th[t].points[p].items[k].id == itemId) return th[t].points[p].items[k];
    }
    return null;
  }

  function setNote(itemId, val) {
    var b = blocOfItem(itemId);
    if (!b) return;
    b.notes[itemId] = val;
    state.dirty[b.bloc_id] = true;
    majProgression(); majScores();
    scheduleSync(b.bloc_id);
    debouncedCalc();
  }

  // ─── Sauvegarde fil de l'eau (auto si reseau, sinon au bouton) ───
  var syncTimers = {};
  function scheduleSync(blocId) {
    if (!navigator.onLine) return;
    clearTimeout(syncTimers[blocId]);
    syncTimers[blocId] = setTimeout(function () { syncBloc(blocId); }, 600);
  }
  function syncBloc(blocId) {
    var b = blocById(blocId);
    if (!b) return Promise.resolve();
    var notes = Object.keys(b.notes).map(function (iid) {
      return { item_id: parseInt(iid, 10), note: b.notes[iid] };
    });
    return api("POST", BASE + state.saisieId + "/enregistrer", {
      bloc_id: b.bloc_id, notes: notes, eliminatoires: b.elim
    }).then(function () {
      state.dirty[blocId] = false;
    }).catch(function () { /* garde dirty, retentera */ });
  }
  function syncAll() {
    return Promise.all(state.blocs.map(function (b) { return syncBloc(b.bloc_id); }));
  }

  // ─── Calcul / proposition live ───
  var calcTimer = null;
  function debouncedCalc() {
    clearTimeout(calcTimer);
    calcTimer = setTimeout(runCalc, 700);
  }
  function runCalc() {
    syncAll().then(function () {
      return api("GET", BASE + state.saisieId + "/calculer");
    }).then(renderPropo).catch(function () {});
  }
  if (window._SP) { window._SP.runCalc = runCalc; }

  function renderPropo(res) {
    var box = document.getElementById("sp-propo");
    box.style.display = "block";
    var html = "";
    function blocLine(d, acquis) {
      var ok = (acquis != null) ? acquis : d.reussi;
      var verdict = ok ? '<div class="sp-verdict ok">Réussi (proposé)</div>' : '<div class="sp-verdict ko">Échec (proposé)</div>';
      var raisons = "";
      if (!ok && d.raisons_echec && d.raisons_echec.length) {
        raisons = '<div class="sp-raisons">' + d.raisons_echec.map(function (r) { return "• " + r; }).join("<br>") + '</div>';
      }
      return '<div class="sp-propo-head"><span>' + d.libelle + '</span><span>' + fmt(d.note_globale) + ' / ' + fmt(d.note_max) + '</span></div>' + verdict + raisons;
    }
    if (res.base) html += blocLine(res.base, null);
    (res.options || []).forEach(function (o) {
      html += '<div style="margin-top:12px;"></div>' + blocLine(o, o.acquis);
    });
    box.innerHTML = html;
  }

  // ─── Progression + scores ───
  window.majProgression = function () {
    var totalItems = 0, faits = 0, ptsSaisis = 0, ptsMax = 0;
    state.blocs.forEach(function (b) {
      b.grille.themes.forEach(function (th) {
        th.points.forEach(function (pe) {
          pe.items.forEach(function (it) {
            if (it.descriptif_seul) return;
            totalItems++;
            ptsMax += it.bareme_max;
            if (b.notes[it.id] != null) { faits++; ptsSaisis += b.notes[it.id]; }
          });
        });
      });
    });
    var pct = totalItems ? Math.round(faits / totalItems * 100) : 0;
    document.getElementById("sp-progress-bar").style.width = pct + "%";
    document.getElementById("sp-progress-txt").textContent =
      faits + " / " + totalItems + " items · " + fmt(ptsSaisis) + " pts saisis";
  };

  window.majScores = function () {
    state.blocs.forEach(function (b) {
      b.grille.themes.forEach(function (th) {
        var noteTh = 0;
        th.points.forEach(function (pe) {
          var notePe = 0, baremePe = 0;
          pe.items.forEach(function (it) {
            if (it.bareme_max) { baremePe += it.bareme_max; notePe += (b.notes[it.id] || 0); }
          });
          noteTh += notePe;
          var badge = document.getElementById("pebadge-" + b.bloc_id + "-" + pe.id);
          if (badge) {
            var anyNote = pe.items.some(function (it) { return b.notes[it.id] != null; });
            if (anyNote && notePe < baremePe / 2) badge.classList.add("ko");
            else badge.classList.remove("ko");
          }
        });
        var sc = document.getElementById("score-" + b.bloc_id + "-" + th.id);
        if (sc) sc.textContent = fmt(noteTh) + "/" + fmt(th.bareme_theme) + " · min " + fmt(th.bareme_theme / 2);
      });
    });
  };

  // ─── Délégation des clics ───
  document.addEventListener("click", function (e) {
    var t;

    if ((t = e.target.closest('[data-action="toggle-theme"]'))) {
      t.closest(".sp-theme").classList.toggle("open"); return;
    }

    if ((t = e.target.closest('[data-action="toggle-criteres"]'))) {
      var on = document.body.classList.toggle("sp-show-crit");
      t.classList.toggle("on", on);
      var lbl = document.getElementById("sp-eye-label");
      if (lbl) lbl.textContent = on ? "Masquer les critères" : "Afficher les critères";
      return;
    }

    if ((t = e.target.closest('[data-action="bin"]'))) {
      var iid = parseInt(t.dataset.item, 10);
      var def = itemDef(iid);
      var val = (t.dataset.kind === "ok") ? def.bareme_max : 0;
      setNote(iid, val);
      // maj visuelle des 2 boutons
      var wrap = t.parentNode;
      wrap.querySelectorAll(".sp-btn-bin").forEach(function (btn) { btn.classList.remove("ok-on", "ko-on"); });
      t.classList.add(t.dataset.kind === "ok" ? "ok-on" : "ko-on");
      return;
    }

    if ((t = e.target.closest('[data-action="palier"]'))) {
      var iid2 = parseInt(t.dataset.item, 10);
      var v = parseFloat(t.dataset.val);
      setNote(iid2, v);
      var grp = t.closest(".sp-paliers");
      grp.querySelectorAll(".sp-palier").forEach(function (p) { p.classList.remove("on"); });
      t.classList.add("on");
      return;
    }

    if ((t = e.target.closest('[data-action="step"]'))) {
      var iid3 = parseInt(t.dataset.item, 10);
      var pas = parseFloat(t.dataset.pas);
      var dir = parseInt(t.dataset.dir, 10);
      var def3 = itemDef(iid3);
      var b3 = blocOfItem(iid3);
      var cur = (b3.notes[iid3] == null) ? 0 : b3.notes[iid3];
      cur = cur + dir * pas;
      if (cur < 0) cur = 0;
      if (cur > def3.bareme_max) cur = def3.bareme_max;
      setNote(iid3, cur);
      document.getElementById("stepval-" + iid3).textContent = fmt(cur);
      return;
    }
  });

  // eliminatoires
  document.addEventListener("change", function (e) {
    var cb = e.target.closest('[data-action="elim"]');
    if (!cb) return;
    var b = blocById(cb.dataset.bloc);
    var crit = parseInt(cb.dataset.crit, 10);
    var idx = b.elim.indexOf(crit);
    if (cb.checked && idx < 0) b.elim.push(crit);
    if (!cb.checked && idx >= 0) b.elim.splice(idx, 1);
    state.dirty[b.bloc_id] = true;
    scheduleSync(b.bloc_id);
    debouncedCalc();
  });

  // bouton Enregistrer
  document.addEventListener("click", function (e) {
    if (!e.target.closest('[data-action="enregistrer"]')) return;
    syncAll().then(function () { toast("Enregistré"); });
  });

  // reseau revenu -> resync
  window.addEventListener("online", function () { syncAll(); });

  // helpers exposes au bloc 3a
  window.majProgression = window.majProgression;
  window.majScores = window.majScores;
})();

(function () {
  "use strict";
  var SP = window._SP;
  var state = SP.state, api = SP.api, BASE = SP.BASE, toast = SP.toast, fmt = SP.fmt;

  document.addEventListener("click", function (e) {
    if (!e.target.closest('[data-action="valider"]')) return;

    // 1) tout synchroniser, 2) calculer, 3) demander decision + justif
    api("GET", BASE + state.saisieId + "/calculer").then(function (res) {
      ouvrirModalValidation(res);
    }).catch(function (err) { toast("Erreur calcul : " + err.message); });
  });

  function ouvrirModalValidation(res) {
    var baseReussi = res.base ? res.base.reussi : false;
    var echecGlobal = !baseReussi || (res.options || []).some(function (o) { return o.reussi === false; });

    var html = ''
      + '<div id="sp-modal-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px;">'
      + '<div style="background:#fff;border-radius:14px;padding:20px;max-width:440px;width:100%;max-height:90vh;overflow:auto;">'
      + '<h2 style="font-size:18px;margin-bottom:12px;color:#2d2d2d;">Valider le résultat</h2>';

    // recap base
    html += blocRecap("Catégorie — " + (res.base ? res.base.libelle : ""), res.base, "base", baseReussi);
    // recap options
    (res.options || []).forEach(function (o) {
      html += blocRecap("Option — " + o.libelle, o, "opt_" + o.code_option, o.acquis);
    });

    var obligLabel = echecGlobal
      ? '<span style="color:#cc0000;">(obligatoire en cas d\'échec)</span>'
      : '<span style="color:#888;font-weight:400;">(optionnel)</span>';
    html += '<div style="margin-top:14px;"><label style="font-size:13px;font-weight:700;color:#2d2d2d;">Justification ' + obligLabel + '</label>'
      + '<textarea id="sp-justif" rows="3" style="width:100%;margin-top:6px;border:1px solid #d0d4dc;border-radius:8px;padding:8px;font-size:13px;"></textarea></div>';

    html += '<div style="margin-top:8px;"><label style="font-size:13px;color:#555;">Observations (optionnel)</label>'
      + '<textarea id="sp-obs" rows="2" style="width:100%;margin-top:6px;border:1px solid #d0d4dc;border-radius:8px;padding:8px;font-size:13px;"></textarea></div>';

    html += '<div style="margin-top:8px;"><label style="font-size:13px;color:#555;">Nom du testeur</label>'
      + '<input id="sp-testeur" type="text" style="width:100%;margin-top:6px;border:1px solid #d0d4dc;border-radius:8px;padding:8px;font-size:13px;"></div>';

    html += '<div style="display:flex;gap:10px;margin-top:16px;">'
      + '<button data-action="annuler-valid" style="flex:1;height:44px;border:1px solid #b0b4bc;background:#fff;border-radius:8px;font-size:14px;cursor:pointer;">Annuler</button>'
      + '<button data-action="confirmer-valid" style="flex:1;height:44px;border:none;background:#1d9e75;color:#fff;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">Confirmer</button>'
      + '</div></div></div>';

    var div = document.createElement("div");
    div.innerHTML = html;
    document.body.appendChild(div.firstChild);

    // pre-cocher les decisions selon la proposition
    window._spDecisions = { base: baseReussi, options: {} };
    (res.options || []).forEach(function (o) { window._spDecisions.options[o.code_option] = !!o.acquis; });
  }

  function blocRecap(titre, d, key, propAcquis) {
    if (!d) return "";
    var ok = !!propAcquis;
    var color = ok ? "#0f6e56" : "#a32d2d";
    var label = ok ? "Réussi" : "Échec";
    var radios = ''
      + '<div style="display:flex;gap:8px;margin-top:6px;">'
      + '<label style="flex:1;text-align:center;padding:8px;border-radius:8px;border:1px solid #a5d6a7;background:#e8f5e9;font-size:13px;font-weight:700;cursor:pointer;">'
      + '<input type="radio" name="dec-' + key + '" value="1"' + (ok ? " checked" : "") + ' data-key="' + key + '"> Réussi</label>'
      + '<label style="flex:1;text-align:center;padding:8px;border-radius:8px;border:1px solid #ef9a9a;background:#ffebee;font-size:13px;font-weight:700;cursor:pointer;">'
      + '<input type="radio" name="dec-' + key + '" value="0"' + (!ok ? " checked" : "") + ' data-key="' + key + '"> Échec</label>'
      + '</div>';
    return '<div style="border:1px solid #e2e6ee;border-radius:10px;padding:10px;margin-bottom:8px;">'
      + '<div style="font-size:13px;font-weight:700;color:#2d2d2d;">' + escapeHtml(titre) + '</div>'
      + '<div style="font-size:12px;color:#555;margin-top:2px;">Proposition : <span style="color:' + color + ';font-weight:700;">' + label + '</span> (' + fmt(d.note_globale) + '/' + fmt(d.note_max) + ')</div>'
      + radios + '</div>';
  }

  // maj des decisions quand le testeur change un radio
  document.addEventListener("change", function (e) {
    var r = e.target.closest('input[type="radio"][data-key]');
    if (!r || !window._spDecisions) return;
    var key = r.dataset.key;
    var val = r.value === "1";
    if (key === "base") window._spDecisions.base = val;
    else if (key.indexOf("opt_") === 0) window._spDecisions.options[key.slice(4)] = val;
  });

  document.addEventListener("click", function (e) {
    if (e.target.closest('[data-action="annuler-valid"]')) {
      var ov = document.getElementById("sp-modal-overlay");
      if (ov) ov.remove();
      return;
    }
    if (e.target.closest('[data-action="confirmer-valid"]')) {
      var dec = window._spDecisions;
      var echec = !dec.base || Object.keys(dec.options).some(function (k) { return dec.options[k] === false; });
      var justif = (document.getElementById("sp-justif").value || "").trim();
      if (echec && !justif) { toast("Justification obligatoire en cas d'échec"); return; }

      api("POST", BASE + state.saisieId + "/valider", {
        testeur_nom: document.getElementById("sp-testeur").value || null,
        observations: document.getElementById("sp-obs").value || null,
        justification_ecart: justif || null,
        decision_base: dec.base,
        decisions_options: dec.options
      }).then(function () {
        var ov = document.getElementById("sp-modal-overlay");
        if (ov) ov.remove();
        toast("Résultat validé");
        setTimeout(function () { window.close(); }, 1200);
      }).catch(function (err) { toast("Erreur : " + err.message); });
    }
  });

  function escapeHtml(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
})();
