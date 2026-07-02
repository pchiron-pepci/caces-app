(function () {
  "use strict";

  var BODY = document.body;
  var SESSION_ID = BODY.dataset.sessionId;
  var JOUR_ID = BODY.dataset.jourTestId;
  var STAGIAIRE_ID = BODY.dataset.stagiaireId;
  var CATEGORIE = BODY.dataset.categorie;
  var FAMILLE = BODY.dataset.famille;
  var BASE = "/api/sessions/" + SESSION_ID + "/pratique/saisie/";

  var state = {
    saisieId: null,
    mode: "binaire",
    statut: "en_cours",
    blocs: [],            // [{bloc_id, grille, notes{item_id:note}, elim:[crit_id]}]
    dirty: {},            // bloc_id -> true (modifs non synchronisees)
    online: navigator.onLine,
    compteurs: null,
    chronos: {},
    horaires: {},        // groupKey -> {pp, mn, fp}  (duree AFFICHEE de chaque phase, mm:ss)
    jalons: {}           // groupKey -> {pp, mn, fp}  (INSTANT du clic = temps ecoule en s, ou null)
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

  // Libelles engins cat A (pour titrer les blocs base multi-engins)
  var ENGIN_LABELS = {
    "PH": "Pelle hydraulique compacte",
    "MB": "Motobasculeur compact",
    "CH": "Chargeuse compacte",
    "CP": "Compacteur compact"
  };

  // ─── LOT 1 : calcul des compteurs (1 UT = 60 min, proportionnel) ───
  var MINUTES_PAR_UT = 60;

  function calculerCompteurs(blocs) {
    var utBaseMax = 0, utInclus = 0, options = {};
    (blocs || []).forEach(function (b) {
      var g = b.grille || {};
      var ut = (typeof g.ut === "number") ? g.ut : (parseFloat(g.ut || 0) || 0);
      if (g.type === "base") {
        // Plusieurs machines base (ex. cat A : PH + N2) = UNE epreuve.
        // On prend le MAX, on n'additionne pas (sinon 1,5 + 1,5 = 3, faux).
        if (ut > utBaseMax) utBaseMax = ut;
      } else if (g.type === "option") {
        if (g.incluse) { utInclus += ut; }
        else if (g.code_option) {
          options[g.code_option] = { ut: ut, secondes: Math.round(ut * MINUTES_PAR_UT * 60), libelle: g.libelle || g.code_option };
        }
      }
    });
    var utCat = utBaseMax + utInclus;
    return {
      categorie: { ut: utCat, secondes: Math.round(utCat * MINUTES_PAR_UT * 60) },
      options: options
    };
  }

  function utLabel(ut) { return (ut === Math.floor(ut) ? ut : String(ut).replace(".", ",")) + " UT"; }

  function fmtDureeCourt(sec) {
    sec = Math.round(sec);
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
    if (h > 0) return h + "h" + (m > 0 ? (m < 10 ? "0" + m : m) : "");
    return m + " min";
  }

  // Recalcule les durees AFFICHEES de chaque phase a partir des jalons.
  function _recalcPhases(gkey) {
    var j = state.jalons[gkey] || { pp: null, mn: null, fp: null };
    var h = state.horaires[gkey] || { pp: "", mn: "", fp: "" };
    h.pp = (j.pp != null) ? _fmtEcoule(j.pp) : "";
    h.mn = (j.mn != null && j.pp != null) ? _fmtEcoule(Math.max(0, j.mn - j.pp)) : "";
    h.fp = (j.fp != null && j.mn != null) ? _fmtEcoule(Math.max(0, j.fp - j.mn)) : "";
    state.horaires[gkey] = h;
  }

  function _dureeEnSecondes(mmss) {
    var m = String(mmss).match(/^(?:(\d+):)?(\d{1,2}):(\d{1,2})$/);
    if (!m) return 0;
    var h = m[1] ? parseInt(m[1], 10) : 0;
    return h * 3600 + parseInt(m[2], 10) * 60 + parseInt(m[3], 10);
  }

  function _parseDuree(str) {
    // Accepte "mm:ss", "m:ss", "hh:mm:ss" ou un nombre de minutes seul.
    str = String(str).trim();
    if (/^\d+$/.test(str)) { return _fmtEcoule(parseInt(str, 10) * 60); }
    var m3 = str.match(/^(\d+):(\d{1,2}):(\d{1,2})$/);
    if (m3) {
      var sc3 = parseInt(m3[3], 10);
      if (sc3 > 59) return null;
      return _fmtEcoule(parseInt(m3[1], 10) * 3600 + parseInt(m3[2], 10) * 60 + sc3);
    }
    var m2 = str.match(/^(\d{1,2}):(\d{1,2})$/);
    if (m2) {
      var sc2 = parseInt(m2[2], 10);
      if (sc2 > 59) return null;
      return _fmtEcoule(parseInt(m2[1], 10) * 60 + sc2);
    }
    return null;
  }

  function _fmtEcoule(sec) {
    // Duree ecoulee positive, format mm:ss (ou h:mm:ss au-dela de 60 min).
    sec = Math.max(0, Math.round(sec));
    var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), x = sec % 60;
    var p = function (v) { return v < 10 ? "0" + v : v; };
    return (h > 0 ? (h + ":" + p(m)) : m) + ":" + p(x);
  }

  function fmtChrono(sec) {
    var neg = sec < 0, a = Math.abs(Math.round(sec));
    var h = Math.floor(a / 3600), m = Math.floor((a % 3600) / 60), x = a % 60;
    var p = function (v) { return v < 10 ? "0" + v : v; };
    return (neg ? "-" : "") + (h > 0 ? (h + ":" + p(m)) : m) + ":" + p(x);
  }

  function renderBloc(bloc) {
    var g = bloc.grille;
    var html = "";
    if (g.type === "option") {
      html += '<div class="sp-bloc-titre"><div class="sp-bloc-line"></div>'
        + '<span class="sp-bloc-label">Option · ' + escapeHtml(g.libelle) + '</span>'
        + '<div class="sp-bloc-line"></div></div>';
    } else if (g.type === "base") {
      // En-tete d'engin uniforme pour TOUTES les categories.
      //  - cat A multi-engins (g.variante) : badge "ENGIN N°1/N°2" + nom mappe + code.
      //  - categorie a un seul engin       : badge "ENGIN" + nom = g.libelle.
      var badge, nom;
      if (g.variante) {
        var rang = (g.variante === "PH") ? "N°1" : "N°2";
        badge = "ENGIN " + rang;
        nom = (ENGIN_LABELS[g.variante] || g.variante) + " (" + g.variante + ")";
      } else {
        badge = "ENGIN";
        nom = g.libelle || "";
      }
      html += '<div class="sp-engin-head" data-engin-badge="' + escapeHtml(badge) + '" data-engin-nom="' + escapeHtml(nom) + '" style="background:#2d2d2d;color:#fff;'
        + 'border-radius:8px;padding:10px 14px;margin:14px 0 8px;display:flex;'
        + 'align-items:center;gap:10px;border-left:5px solid #cc0000;">'
        + '<span style="background:#cc0000;color:#fff;font-weight:700;font-size:13px;'
        + 'padding:3px 9px;border-radius:5px;white-space:nowrap;">' + escapeHtml(badge) + '</span>'
        + '<span style="font-weight:700;font-size:15px;">' + escapeHtml(nom)
        + '</span></div>';
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

  // ─── LOT 2 : barre de compteurs figee ─────────────────────────
  function _groupes() {
    var c = state.compteurs || { categorie: { secondes: 0, ut: 0 }, options: {} };
    var out = [];
    if (c.categorie.secondes > 0) {
      out.push({ key: "CAT", label: "Categorie " + (CATEGORIE || ""), ref: c.categorie.secondes, ut: c.categorie.ut });
    }
    Object.keys(c.options).forEach(function (code) {
      var o = c.options[code];
      out.push({ key: "OPT:" + code, label: "Option " + code, ref: o.secondes, ut: o.ut });
    });
    return out;
  }

  function _ensureChrono(key, ref) {
    if (!state.chronos[key]) state.chronos[key] = { ref: ref, restant: ref, run: false, timer: null };
    else state.chronos[key].ref = ref;
    if (!state.horaires[key]) state.horaires[key] = { pp: "", mn: "", fp: "" };
    if (!state.jalons[key]) state.jalons[key] = { pp: null, mn: null, fp: null };
    return state.chronos[key];
  }

  function renderBarreCompteurs() {
    var host = document.getElementById("sp-compteurs");
    if (!host) {
      var content = document.getElementById("sp-content");
      if (!content) return;
      host = document.createElement("div");
      host.id = "sp-compteurs";
      host.style.cssText = "position:sticky;top:0;z-index:30;background:#fff;border-bottom:1px solid #d0d4d8;padding:8px;display:flex;gap:8px;flex-wrap:wrap;";
      content.insertBefore(host, content.firstChild);
    }
    var groupes = _groupes();
    if (!groupes.length) { host.style.display = "none"; return; }
    host.style.display = "block";
    // Ligne candidat compacte (reste visible avec les compteurs au scroll).
    var candEl = document.querySelector("#sp-header .sp-cand");
    var candNom = candEl ? candEl.textContent : "";
    var ligneCand = '<div style="font-size:13px;font-weight:700;color:#2d2d2d;padding:2px 2px 6px;">'
      + escapeHtml(candNom) + '</div>';
    var cartes = groupes.map(function (g) {
      var ch = _ensureChrono(g.key, g.ref);
      var hr = state.horaires[g.key];
      var depasse = ch.restant < 0;
      var seuil = Math.round(g.ref * 0.30);
      var alerte = ch.restant <= -seuil;
      var bordure = alerte ? "#cc0000" : (depasse ? "#e24b4a" : "#e0e3e6");
      var bg = alerte ? "#fcebeb" : "#fff";
      function rub(k, lib) {
        var val = hr[k];
        var set = !!val;
        var _titre = set ? "Cliquer pour corriger la duree de cette phase" : "Cliquer pour cloturer la phase precedente et demarrer celle-ci";
        return '<div class="sp-rub" data-clock="' + g.key + '|' + k + '" title="' + _titre + '" '
          + 'style="flex:1;border:1px solid ' + (set ? "#5dcaa5" : "#e0e3e6") + ';border-radius:5px;'
          + 'padding:3px 4px;cursor:pointer;text-align:center;background:' + (set ? "#e1f5ee" : "#f9fafb") + ';">'
          + '<div style="font-size:9px;color:#888;line-height:1.2;">' + lib + (set ? ' ✎' : '') + '</div>'
          + '<div style="font-size:12px;font-weight:700;font-family:monospace;color:' + (set ? "#0f6e56" : "#bbb") + ';">'
          + (val || "--:--") + '</div></div>';
      }
      return '<div class="sp-cmp" data-key="' + g.key + '" '
        + 'style="flex:1;min-width:200px;border:1px solid ' + bordure + ';border-radius:9px;padding:8px 9px;background:' + bg + ';">'
        + '<div style="display:flex;align-items:center;gap:8px;">'
        + '<span style="flex:1;font-size:10px;color:#888;">' + escapeHtml(g.label) + ' · ref ' + fmtDureeCourt(g.ref) + ' (' + utLabel(g.ut) + ')</span>'
        + '<span class="sp-cmp-t" style="font-family:monospace;font-size:19px;font-weight:700;font-variant-numeric:tabular-nums;color:' + (depasse ? "#cc0000" : "#2d2d2d") + ';">' + fmtChrono(ch.restant) + '</span>'
        + '</div>'
        + '<div style="display:flex;gap:3px;margin-top:4px;">'
        + '<button class="sp-cmp-btn" data-cmp="start" data-key="' + g.key + '" style="flex:1;height:24px;border:1px solid #d0d4d8;border-radius:5px;background:#fff;cursor:pointer;font-size:11px;">&#9654;</button>'
        + '<button class="sp-cmp-btn" data-cmp="stop" data-key="' + g.key + '" style="flex:1;height:24px;border:1px solid #d0d4d8;border-radius:5px;background:#fff;cursor:pointer;font-size:11px;">&#10073;&#10073;</button>'
        + '<button class="sp-cmp-btn" data-cmp="reset" data-key="' + g.key + '" style="flex:1;height:24px;border:1px solid #d0d4d8;border-radius:5px;background:#fff;cursor:pointer;font-size:11px;">&#8635;</button>'
        + '</div>'
        + '<div style="display:flex;gap:3px;margin-top:5px;">' + rub("pp", "Prise poste") + rub("mn", "Manoeuvre") + rub("fp", "Fin poste") + '</div>'
        + '</div>';
    }).join("");
    host.innerHTML = ligneCand + '<div style="display:flex;gap:8px;flex-wrap:wrap;">' + cartes + '</div>'
      + '<div id="sp-engin-courant" style="display:none;background:#cc0000;color:#fff;padding:5px 12px;margin:7px -8px -8px;font-size:13px;font-weight:700;align-items:center;gap:8px;"></div>';
    _installObserverEngin();
  }

  // Bandeau engin courant : suit l'en-tete d'engin le plus haut visible.
  var _engObserver = null;
  function _installObserverEngin() {
    var bandeau = document.getElementById("sp-engin-courant");
    if (!bandeau) return;
    var heads = Array.prototype.slice.call(document.querySelectorAll(".sp-engin-head"));
    if (heads.length < 2) { bandeau.style.display = "none"; return; }

    function maj() {
      var host = document.getElementById("sp-compteurs");
      var seuil = host ? (host.getBoundingClientRect().bottom) : 0;
      var courant = null;
      heads.forEach(function (h) {
        var top = h.getBoundingClientRect().top;
        if (top <= seuil + 4) courant = h;
      });
      if (!courant) courant = heads[0];
      var badge = courant.getAttribute("data-engin-badge") || "";
      var nom = courant.getAttribute("data-engin-nom") || "";
      bandeau.style.display = "flex";
      bandeau.innerHTML = '<span style="background:rgba(255,255,255,0.22);font-size:10px;padding:1px 7px;border-radius:4px;">'
        + badge + '</span><span>' + nom + '</span>';
    }

    window.removeEventListener("scroll", maj);
    window.addEventListener("scroll", maj, { passive: true });
    maj();
  }

  function _majAffichageCompteur(key) {
    var host = document.getElementById("sp-compteurs");
    if (!host) return;
    var el = null;
    var all = host.querySelectorAll(".sp-cmp");
    for (var i = 0; i < all.length; i++) { if (all[i].getAttribute("data-key") === key) { el = all[i]; break; } }
    if (!el) return;
    var ch = state.chronos[key]; if (!ch) return;
    var depasse = ch.restant < 0;
    var seuil = Math.round(ch.ref * 0.30);
    var alerte = ch.restant <= -seuil;
    var t = el.querySelector(".sp-cmp-t");
    t.textContent = fmtChrono(ch.restant);
    t.style.color = depasse ? "#cc0000" : "#2d2d2d";
    el.style.borderColor = alerte ? "#cc0000" : (depasse ? "#e24b4a" : "#e0e3e6");
    el.style.background = alerte ? "#fcebeb" : "#fff";
  }

  function _tick(key) {
    var ch = state.chronos[key]; if (!ch) return;
    ch.restant -= 1;
    _majAffichageCompteur(key);
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-cmp]");
    if (b) {
      var key = b.getAttribute("data-key");
      var act = b.getAttribute("data-cmp");
      var ch = state.chronos[key]; if (!ch) return;
      if (act === "start" && !ch.run) { ch.run = true; ch.timer = setInterval(function () { _tick(key); }, 1000); }
      else if (act === "stop") { ch.run = false; if (ch.timer) clearInterval(ch.timer); }
      else if (act === "reset") { ch.run = false; if (ch.timer) clearInterval(ch.timer); ch.restant = ch.ref; _majAffichageCompteur(key); }
      return;
    }
    var r = e.target.closest("[data-clock]");
    if (r) {
      var parts = r.getAttribute("data-clock").split("|");
      var gkey = parts[0], champ = parts[1];
      if (!state.jalons[gkey]) state.jalons[gkey] = { pp: null, mn: null, fp: null };
      if (!state.horaires[gkey]) state.horaires[gkey] = { pp: "", mn: "", fp: "" };
      var ch = state.chronos[gkey];
      var ecoule = ch ? (ch.ref - ch.restant) : 0;
      var dejaPose = state.jalons[gkey][champ] != null;
      var precede = { pp: null, mn: "pp", fp: "mn" };

      if (!dejaPose) {
        // 1er clic : exige que la phase precedente soit jalonnee (enchainement).
        var prev = precede[champ];
        if (prev && state.jalons[gkey][prev] == null) {
          alert("Cliquez d'abord la phase precedente (" +
            (prev === "pp" ? "Prise de poste" : "Manoeuvre") + ").");
          return;
        }
        state.jalons[gkey][champ] = ecoule;
      } else {
        // Reclic : edition manuelle de la DUREE de cette phase (jamais d'ecrasement auto).
        var libs = { pp: "Prise de poste", mn: "Manoeuvre", fp: "Fin de poste" };
        var actuel = state.horaires[gkey][champ] || "";
        var saisie = window.prompt(
          "Corriger la duree de la phase (" + (libs[champ] || champ) + ") au format mm:ss.",
          actuel
        );
        if (saisie === null) { return; }
        saisie = saisie.trim();
        if (saisie === "") { return; }
        var norm = _parseDuree(saisie);
        if (norm === null) { alert("Format invalide (attendu mm:ss, ex : 12:30)"); return; }
        // Reconstruire le jalon a partir de la duree corrigee + jalon precedent.
        var secs = _dureeEnSecondes(norm);
        var base = 0;
        if (champ === "mn") base = state.jalons[gkey].pp || 0;
        else if (champ === "fp") base = state.jalons[gkey].mn || 0;
        state.jalons[gkey][champ] = base + secs;
      }
      _recalcPhases(gkey);
      renderBarreCompteurs();
    }
  });

  function renderAll() {
    var box = document.getElementById("sp-blocs");
    state.compteurs = calculerCompteurs(state.blocs);
    renderBarreCompteurs();
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

  // ─── Testeurs habilites (famille + categorie + options du candidat) ───
  function chargerTesteurs(options, testeurIdPreselect) {
    var url = BASE + state.saisieId + "/testeurs-habilites?famille=" + encodeURIComponent(FAMILLE) +
              "&categorie=" + encodeURIComponent(CATEGORIE);
    if (options && options.length) {
      url += "&options=" + encodeURIComponent(options.join(","));
    }
    fetch(url).then(function (r) { return r.json(); }).then(function (list) {
      var sel = document.getElementById("sp-testeur-select");
      if (!sel) return;
      (list || []).forEach(function (t) {
        var o = document.createElement("option");
        o.value = t.id;
        o.textContent = t.nom + " " + t.prenom;
        sel.appendChild(o);
      });
      if (!list || list.length === 0) {
        var o = document.createElement("option");
        o.value = "";
        o.textContent = "Aucun testeur habilité " + FAMILLE + " " + CATEGORIE + (options && options.length ? " + " + options.join("/") : "");
        o.disabled = true;
        sel.appendChild(o);
      }
      if (testeurIdPreselect) {
        sel.value = String(testeurIdPreselect);
      }
      majBandeauTesteur();
    }).catch(function () {});
  }

  function majBandeauTesteur() {
    var sel = document.getElementById("sp-testeur-select");
    var band = document.getElementById("sp-testeur-band");
    var ic = document.getElementById("sp-testeur-ic");
    if (!sel || !band) return;
    if (sel.value) {
      band.classList.remove("non-selectionne");
      band.classList.add("selectionne");
      if (ic) ic.innerHTML = "&#10003;";
    } else {
      band.classList.remove("selectionne");
      band.classList.add("non-selectionne");
      if (ic) ic.innerHTML = "&#9888;";
    }
  }

  // ─── Chargement initial ───
  function traiterReponseSaisie(data) {
    state.saisieId = data.saisie_id;
    state.mode = data.mode;
    state.statut = data.statut;
    state.blocs = data.blocs.map(function (b) {
      return {
        bloc_id: b.bloc_id, grille: b.grille,
        notes: b.notes_saisies || {}, elim: b.eliminatoires_coches || []
      };
    });
    state.repriseTesteurId = data.testeur_id || null;
    state.repriseSignature = data.signature_testeur || null;
    state.repriseObservations = data.observations || null;
    state.repriseJustification = data.justification_ecart || null;
    renderAll();
    if (data.reprise) toast("Saisie reprise");
    if (window._SP && typeof window._SP.runCalc === "function") { window._SP.runCalc(); }
    var optionsCandidat = state.blocs
      .filter(function (b) { return b.grille && b.grille.type === "option" && b.grille.code_option; })
      .map(function (b) { return b.grille.code_option; });
    chargerTesteurs(optionsCandidat, state.repriseTesteurId);
  }

  function lancerOuverture(engin2, variante) {
    var url = BASE + JOUR_ID + "/" + STAGIAIRE_ID + "/" + CATEGORIE + "/ouvrir";
    var params = [];
    if (engin2) { params.push("engin2=" + encodeURIComponent(engin2)); }
    if (variante) { params.push("variante=" + encodeURIComponent(variante)); }
    if (params.length) { url += "?" + params.join("&"); }
    return api("POST", url)
      .then(traiterReponseSaisie)
      .catch(function (e) {
        document.getElementById("sp-progress-txt").textContent = "Erreur : " + e.message;
      });
  }

  function estCatA() {
    return (FAMILLE || "").toUpperCase().replace(/[^A-Z0-9]/g, "").indexOf("R482") === 0
      && (CATEGORIE || "").toUpperCase() === "A";
  }

  function afficherChoixEngin2() {
    var ENGINS = [
      { code: "MB", lib: "Motobasculeur compact" },
      { code: "CH", lib: "Chargeuse compacte" },
      { code: "CP", lib: "Compacteur compact" }
    ];
    var ov = document.createElement("div");
    ov.id = "sp-engin2-overlay";
    ov.style.cssText = "position:fixed;inset:0;background:rgba(45,45,45,0.92);z-index:200;"
      + "display:flex;align-items:center;justify-content:center;padding:20px;";
    var box = '<div style="background:#fff;border-radius:12px;max-width:440px;width:100%;'
      + 'padding:24px;box-shadow:0 10px 40px rgba(0,0,0,0.4);">'
      + '<div style="font-size:18px;font-weight:700;color:#2d2d2d;margin-bottom:4px;">Categorie A &mdash; Engins compacts</div>'
      + '<div style="font-size:13px;color:#666;margin-bottom:18px;line-height:1.5;">'
      + "L'epreuve se deroule sur <b>deux engins</b>. L'engin N1 est toujours la "
      + "<b>pelle hydraulique compacte (PH)</b>.<br>Choisissez l'engin N2 presente au candidat :</div>"
      + '<div id="sp-engin2-choices" style="display:flex;flex-direction:column;gap:10px;">';
    ENGINS.forEach(function (e) {
      box += '<button type="button" class="sp-engin2-btn" data-engin2="' + e.code + '" '
        + 'style="text-align:left;padding:14px 16px;border:2px solid #e2e6ee;border-radius:8px;'
        + 'background:#f9fafb;cursor:pointer;font-size:15px;color:#2d2d2d;transition:all .15s;">'
        + '<b>' + e.code + '</b> &mdash; ' + e.lib + '</button>';
    });
    box += '</div></div>';
    ov.innerHTML = box;
    document.body.appendChild(ov);

    ov.querySelectorAll(".sp-engin2-btn").forEach(function (btn) {
      btn.addEventListener("mouseover", function () {
        btn.style.borderColor = "#cc0000"; btn.style.background = "#fff5f5";
      });
      btn.addEventListener("mouseout", function () {
        btn.style.borderColor = "#e2e6ee"; btn.style.background = "#f9fafb";
      });
      btn.addEventListener("click", function () {
        var engin2 = btn.getAttribute("data-engin2");
        if (ov.parentNode) ov.parentNode.removeChild(ov);
        lancerOuverture(engin2);
      });
    });
  }

  function afficherChoixVariante(variantes) {
    var ov = document.createElement("div");
    ov.id = "sp-variante-overlay";
    ov.style.cssText = "position:fixed;inset:0;background:rgba(45,45,45,0.92);z-index:200;"
      + "display:flex;align-items:center;justify-content:center;padding:20px;";
    var box = '<div style="background:#fff;border-radius:12px;max-width:440px;width:100%;'
      + 'padding:24px;box-shadow:0 10px 40px rgba(0,0,0,0.4);">'
      + '<div style="font-size:18px;font-weight:700;color:#2d2d2d;margin-bottom:4px;">Categorie ' + CATEGORIE + ' &mdash; Choix de l\'engin</div>'
      + '<div style="font-size:13px;color:#666;margin-bottom:18px;line-height:1.5;">'
      + "Cette categorie se decline en plusieurs engins. Choisissez celui presente au candidat :</div>"
      + '<div id="sp-variante-choices" style="display:flex;flex-direction:column;gap:10px;">';
    variantes.forEach(function (v) {
      box += '<button type="button" class="sp-variante-btn" data-variante="' + v.variante + '" '
        + 'style="text-align:left;padding:14px 16px;border:2px solid #e2e6ee;border-radius:8px;'
        + 'background:#f9fafb;cursor:pointer;font-size:15px;color:#2d2d2d;transition:all .15s;">'
        + '<b>' + v.variante + '</b> &mdash; ' + (v.libelle || "") + '</button>';
    });
    box += '</div></div>';
    ov.innerHTML = box;
    document.body.appendChild(ov);

    ov.querySelectorAll(".sp-variante-btn").forEach(function (btn) {
      btn.addEventListener("mouseover", function () {
        btn.style.borderColor = "#cc0000"; btn.style.background = "#fff5f5";
      });
      btn.addEventListener("mouseout", function () {
        btn.style.borderColor = "#e2e6ee"; btn.style.background = "#f9fafb";
      });
      btn.addEventListener("click", function () {
        var variante = btn.getAttribute("data-variante");
        if (ov.parentNode) ov.parentNode.removeChild(ov);
        lancerOuverture(null, variante);
      });
    });
  }

  function ouvrirOuDemander() {
    var urlVar = BASE + JOUR_ID + "/" + STAGIAIRE_ID + "/" + CATEGORIE + "/variantes";
    api("GET", urlVar)
      .then(function (info) {
        if (info.mode === "cumul") {
          var url = BASE + JOUR_ID + "/" + STAGIAIRE_ID + "/" + CATEGORIE + "/ouvrir";
          api("POST", url).then(traiterReponseSaisie).catch(function () { afficherChoixEngin2(); });
        } else if (info.mode === "exclusif") {
          var url2 = BASE + JOUR_ID + "/" + STAGIAIRE_ID + "/" + CATEGORIE + "/ouvrir";
          api("POST", url2).then(traiterReponseSaisie).catch(function () {
            afficherChoixVariante(info.variantes || []);
          });
        } else if (info.mode === "cumul_total") {
          // G : les 2 engins CH+PC sont imposes, le back cree les 2 blocs, ouverture directe sans modale
          lancerOuverture(null);
        } else {
          lancerOuverture(null);
        }
      })
      .catch(function () {
        if (!estCatA()) { lancerOuverture(null); return; }
        var url = BASE + JOUR_ID + "/" + STAGIAIRE_ID + "/" + CATEGORIE + "/ouvrir";
        api("POST", url).then(traiterReponseSaisie).catch(function () { afficherChoixEngin2(); });
      });
  }

  document.addEventListener("change", function (e) {
    if (e.target && e.target.id === "sp-testeur-select") majBandeauTesteur();
  });

  ouvrirOuDemander();

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

    if (e.target.closest('[data-action="supprimer-saisie"]')) {
      var ov = document.getElementById("sp-pin-overlay");
      if (ov) { ov.style.display = "flex"; var pi = document.getElementById("sp-pin-input"); if (pi) { pi.value = ""; pi.focus(); } }
      return;
    }
    if (e.target.closest('[data-action="pin-annuler"]')) {
      var ov2 = document.getElementById("sp-pin-overlay");
      if (ov2) ov2.style.display = "none";
      return;
    }
    if (e.target.closest('[data-action="pin-confirmer"]')) {
      var pin = (document.getElementById("sp-pin-input").value || "").trim();
      if (!pin) { toast("Saisissez le PIN administrateur"); return; }
      if (!state.saisieId) { toast("Aucune saisie à supprimer"); return; }
      api("DELETE", BASE + state.saisieId, { pin: pin })
        .then(function () {
          var ov3 = document.getElementById("sp-pin-overlay");
          if (ov3) ov3.style.display = "none";
          toast("Saisie supprimée");
          setTimeout(function () { window.close(); }, 1000);
        })
        .catch(function (err) { toast("Erreur : " + err.message); });
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
  // ─── Canvas signature testeur ───
  var _sigState = { canvas: null, ctx: null, drawing: false, hasTrait: false };
  function initSignature() {
    var c = document.getElementById("sp-sig-canvas");
    if (!c) return;
    _sigState.canvas = c;
    var ctx = c.getContext("2d");
    var dpr = window.devicePixelRatio || 1;
    var rect = c.getBoundingClientRect();
    c.width = (rect.width || 300) * dpr;
    c.height = (rect.height || 140) * dpr;
    ctx.scale(dpr, dpr);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, rect.width || 300, rect.height || 140);
    ctx.strokeStyle = "#1a1a1a";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    _sigState.ctx = ctx;
    _sigState.hasTrait = false;

    function pos(e) {
      var r = c.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }
    function startDraw(e) { _sigState.drawing = true; ctx.beginPath(); var p = pos(e); ctx.moveTo(p.x, p.y); }
    function draw(e) {
      if (!_sigState.drawing) return;
      var p = pos(e);
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
      _sigState.hasTrait = true;
    }
    function stopDraw() { _sigState.drawing = false; }

    c.addEventListener("mousedown", startDraw);
    c.addEventListener("mousemove", draw);
    c.addEventListener("mouseup", stopDraw);
    c.addEventListener("mouseleave", stopDraw);
    c.addEventListener("touchstart", function (e) { e.preventDefault(); startDraw(e.touches[0]); }, { passive: false });
    c.addEventListener("touchmove", function (e) { e.preventDefault(); draw(e.touches[0]); }, { passive: false });
    c.addEventListener("touchend", stopDraw);
  }

  function clearSignature() {
    if (_sigState.ctx && _sigState.canvas) {
      _sigState.ctx.clearRect(0, 0, _sigState.canvas.width, _sigState.canvas.height);
      _sigState.hasTrait = false;
    }
  }
  function signatureData() {
    if (!_sigState.canvas || !_sigState.hasTrait) return null;
    return _sigState.canvas.toDataURL("image/png");
  }

  "use strict";
  var SP = window._SP;
  var state = SP.state, api = SP.api, BASE = SP.BASE, toast = SP.toast, fmt = SP.fmt;

  function _itemsSansNote() {
    // Compte UNIQUEMENT les items notables laisses vides (ni OK ni KO).
    // Les criteres eliminatoires (b.elim, cases a cocher) ne sont PAS dans cette boucle :
    // une case non cochee = pas de faute = reponse valide, jamais un oubli a signaler.
    var manquants = 0;
    state.blocs.forEach(function (b) {
      b.grille.themes.forEach(function (th) {
        th.points.forEach(function (pe) {
          pe.items.forEach(function (it) {
            if (it.descriptif_seul) return;
            if (b.notes[it.id] == null) manquants++;
          });
        });
      });
    });
    return manquants;
  }

  document.addEventListener("click", function (e) {
    if (!e.target.closest('[data-action="valider"]')) return;

    // Verification AMONT : le testeur habilite doit etre selectionne (en-tete)
    // AVANT d'ouvrir la fenetre de validation, pour ne pas remplir signature/commentaire
    // puis se faire bloquer a la derniere etape.
    var selTesteur = document.getElementById("sp-testeur-select");
    if (!selTesteur || !selTesteur.value) {
      toast("Selectionnez d'abord le testeur habilite (en-tete) avant de valider");
      if (selTesteur) {
        selTesteur.focus();
        selTesteur.style.outline = "2px solid #cc0000";
        setTimeout(function () { selTesteur.style.outline = ""; }, 2500);
      }
      return;
    }

    // Avertissement NON bloquant si des points n'ont pas ete evalues
    // (cas legitime : candidat arrete en cours d'epreuve, demotive).
    var manquants = _itemsSansNote();
    if (manquants > 0) {
      var msg = (manquants === 1
        ? "Il reste 1 point d'evaluation sans note."
        : "Il reste " + manquants + " points d'evaluation sans note.")
        + "\n\nUn candidat peut s'arreter en cours d'epreuve : vous pouvez valider malgre tout, ou revenir completer."
        + "\n\nValider quand meme ?";
      if (!window.confirm(msg)) return;
    }

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

    var selH = document.getElementById("sp-testeur-select");
    var nomTesteur = (selH && selH.value && selH.options[selH.selectedIndex]) ? selH.options[selH.selectedIndex].textContent : "";
    html += '<div style="margin-top:16px;border:1px solid #e0a93f;background:#faeeda;border-radius:8px;padding:10px;">'
      + '<div style="font-size:12px;color:#7a5a12;line-height:1.5;">Je soussigné(e) <strong>' + escapeHtml(nomTesteur || "—") + '</strong>, testeur habilité, certifie avoir vérifié l&#39;identité du candidat et atteste de la sincérité des résultats consignés.</div>'
      + '</div>';
    html += '<div style="margin-top:10px;"><label style="font-size:13px;font-weight:700;color:#2d2d2d;">Signature du testeur *</label>'
      + '<div style="border:1px solid #b0b4bc;border-radius:8px;margin-top:6px;background:#fff;position:relative;">'
      + '<canvas id="sp-sig-canvas" style="width:100%;height:140px;display:block;touch-action:none;"></canvas>'
      + '<button type="button" data-action="sig-clear" style="position:absolute;top:6px;right:6px;font-size:11px;padding:3px 8px;border:1px solid #ccc;background:#fff;border-radius:6px;cursor:pointer;">Effacer</button>'
      + '</div></div>';

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

    initSignature();

    // Reprise : pre-remplir observations / justification / signature deja saisies
    var obsEl = document.getElementById("sp-obs");
    if (obsEl && state.repriseObservations) obsEl.value = state.repriseObservations;
    var justifEl = document.getElementById("sp-justif");
    if (justifEl && state.repriseJustification) justifEl.value = state.repriseJustification;
    if (state.repriseSignature) {
      var cv = document.getElementById("sp-sig-canvas");
      if (cv && _sigState.ctx) {
        var img = new Image();
        img.onload = function () {
          var r = cv.getBoundingClientRect();
          _sigState.ctx.drawImage(img, 0, 0, r.width || 300, r.height || 140);
          _sigState.hasTrait = true;
        };
        var src = state.repriseSignature;
        if (src.indexOf("data:") !== 0) src = "data:image/png;base64," + src;
        img.src = src;
      }
    }
  }

  function blocRecap(titre, d, key, propAcquis) {
    if (!d) return "";
    var ok = !!propAcquis;
    var color = ok ? "#0f6e56" : "#a32d2d";
    var label = ok ? "Réussi" : "Échec";
    var echecMoteur = !ok;
    var reussiDisabled = echecMoteur ? " disabled" : "";
    var reussiStyle = echecMoteur
      ? "flex:1;text-align:center;padding:8px;border-radius:8px;border:1px solid #e0e0e0;background:#f3f3f3;color:#bbb;font-size:13px;font-weight:700;cursor:not-allowed;"
      : "flex:1;text-align:center;padding:8px;border-radius:8px;border:1px solid #a5d6a7;background:#e8f5e9;font-size:13px;font-weight:700;cursor:pointer;";
    var radios = ''
      + '<div style="display:flex;gap:8px;margin-top:6px;">'
      + '<label style="' + reussiStyle + '">'
      + '<input type="radio" name="dec-' + key + '" value="1"' + (ok ? " checked" : "") + reussiDisabled + ' data-key="' + key + '"> Réussi</label>'
      + '<label style="flex:1;text-align:center;padding:8px;border-radius:8px;border:1px solid #ef9a9a;background:#ffebee;font-size:13px;font-weight:700;cursor:pointer;">'
      + '<input type="radio" name="dec-' + key + '" value="0"' + (!ok ? " checked" : "") + ' data-key="' + key + '"> Échec</label>'
      + '</div>';
    var blocage = echecMoteur
      ? '<div style="font-size:11px;color:#a32d2d;margin-top:6px;line-height:1.4;"><strong>Échec au test :</strong> le résultat ne peut pas être transformé en réussite. Un commentaire est obligatoire.</div>'
      : '';
    return '<div style="border:1px solid #e2e6ee;border-radius:10px;padding:10px;margin-bottom:8px;">'
      + '<div style="font-size:13px;font-weight:700;color:#2d2d2d;">' + escapeHtml(titre) + '</div>'
      + '<div style="font-size:12px;color:#555;margin-top:2px;">Proposition : <span style="color:' + color + ';font-weight:700;">' + label + '</span> (' + fmt(d.note_globale) + '/' + fmt(d.note_max) + ')</div>'
      + radios + blocage + '</div>';
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
    if (e.target.closest('[data-action="sig-clear"]')) {
      clearSignature();
      return;
    }
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

      var selT = document.getElementById("sp-testeur-select");
      var testeurId = selT ? selT.value : "";
      if (!testeurId) { toast("Sélectionnez le testeur habilité (en-tête)"); return; }
      var testeurNom = selT.options[selT.selectedIndex] ? selT.options[selT.selectedIndex].textContent : "";

      var signature = signatureData();
      if (!signature) { toast("La signature du testeur est obligatoire"); return; }

      api("POST", BASE + state.saisieId + "/valider", {
        testeur_id: parseInt(testeurId, 10),
        testeur_nom: testeurNom || null,
        signature_testeur: signature,
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
