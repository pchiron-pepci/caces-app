(function () {
    'use strict';

    // ── Accordéon cartes (Cartographie, Testeurs, Organisation, Documents) ───
    var CARTES = ['cartographie', 'organisation', 'testeurs', 'documents'];

    // ── Accordéon sous-sections de "À traiter" ───────────────────────────────
    var SECTIONS = ['sessions', 'caces', 'nc', 'alertes', 'photos'];

    function clefCarte(nom)   { return 'dash_replie_' + nom; }
    function clefSection(nom) { return 'dash_section_replie_' + nom; }

    function appliquerEtat() {
        CARTES.forEach(function (nom) {
            var head = document.querySelector('[data-action="toggle-dash-carte"][data-carte="' + nom + '"]');
            if (!head) return;
            var card  = head.closest('.card');
            if (!card) return;
            var body  = card.querySelector('.dash-card-body');
            var arrow = head.querySelector('.dash-arrow');
            // default = replié (clé absente ou 'true') ; 'false' = déplié
            var ouvert = localStorage.getItem(clefCarte(nom)) === 'false';
            if (body)  body.style.display = ouvert ? '' : 'none';
            if (arrow) arrow.textContent  = ouvert ? '▼' : '▶';
        });

        SECTIONS.forEach(function (nom) {
            var head = document.querySelector('[data-action="toggle-dash-section"][data-section="' + nom + '"]');
            if (!head) return;
            var body  = head.nextElementSibling;
            var arrow = head.querySelector('.dash-arrow');
            // Onglet « À traiter » : TOUJOURS replié au démarrage (pas de restauration localStorage)
            var ouvert = false;
            if (body)  body.style.display = ouvert ? '' : 'none';
            if (arrow) arrow.textContent  = ouvert ? '▼' : '▶';
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        appliquerEtat();

        document.addEventListener('click', function (e) {
            // Ne pas intercepter les clics sur liens/boutons (ex: "Voir tout")
            if (e.target.closest('a, button')) return;

            // Toggle cartes
            var headCarte = e.target.closest('[data-action="toggle-dash-carte"]');
            if (headCarte) {
                var nom   = headCarte.dataset.carte;
                var card  = headCarte.closest('.card');
                if (!card) return;
                var body  = card.querySelector('.dash-card-body');
                var arrow = headCarte.querySelector('.dash-arrow');
                if (!body) return;
                var ouvert = body.style.display !== 'none';
                body.style.display = ouvert ? 'none' : '';
                if (arrow) arrow.textContent = ouvert ? '▶' : '▼';
                localStorage.setItem(clefCarte(nom), ouvert ? 'true' : 'false');
                return;
            }

            // Toggle sous-sections
            var headSection = e.target.closest('[data-action="toggle-dash-section"]');
            if (headSection) {
                var nom   = headSection.dataset.section;
                var body  = headSection.nextElementSibling;
                var arrow = headSection.querySelector('.dash-arrow');
                if (!body) return;
                var ouvert = body.style.display !== 'none';
                body.style.display = ouvert ? 'none' : '';
                if (arrow) arrow.textContent = ouvert ? '▶' : '▼';
                localStorage.setItem(clefSection(nom), ouvert ? 'true' : 'false');
            }
        });
    });
}());
