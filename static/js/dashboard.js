(function () {
    'use strict';

    var CARTES = ['cartographie', 'organisation', 'testeurs', 'documents'];

    function clef(nom) { return 'dash_replie_' + nom; }

    function appliquerEtat() {
        CARTES.forEach(function (nom) {
            var head = document.querySelector('[data-action="toggle-dash-carte"][data-carte="' + nom + '"]');
            if (!head) return;
            var card  = head.closest('.card');
            if (!card) return;
            var body  = card.querySelector('.dash-card-body');
            var arrow = head.querySelector('.dash-arrow');
            // default = replié (clé absente ou 'true') ; 'false' = déplié
            var ouvert = localStorage.getItem(clef(nom)) === 'false';
            if (body)  body.style.display = ouvert ? '' : 'none';
            if (arrow) arrow.textContent  = ouvert ? '▼' : '▶';
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        appliquerEtat();

        document.addEventListener('click', function (e) {
            // Ne pas intercepter les clics sur liens/boutons dans l'en-tête (ex: "Voir tout")
            if (e.target.closest('a, button')) return;
            var head = e.target.closest('[data-action="toggle-dash-carte"]');
            if (!head) return;
            var nom  = head.dataset.carte;
            var card = head.closest('.card');
            if (!card) return;
            var body  = card.querySelector('.dash-card-body');
            var arrow = head.querySelector('.dash-arrow');
            if (!body) return;
            var ouvert = body.style.display !== 'none';
            body.style.display = ouvert ? 'none' : '';
            if (arrow) arrow.textContent = ouvert ? '▶' : '▼';
            localStorage.setItem(clef(nom), ouvert ? 'true' : 'false');
        });
    });
}());
