'use strict';

document.addEventListener('DOMContentLoaded', function () {

    // ---- Accordéons ----
    document.querySelectorAll('.aide-section-header').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var section = btn.closest('.aide-section');
            var isOpen = section.classList.contains('open');
            // Tout fermer
            document.querySelectorAll('.aide-section').forEach(function (s) {
                s.classList.remove('open', 'highlight');
            });
            document.querySelectorAll('.aide-card').forEach(function (c) {
                c.classList.remove('active');
            });
            if (!isOpen) {
                section.classList.add('open');
            }
        });
    });

    // ---- Clic sur une carte → scroll + déplie section ----
    document.querySelectorAll('.aide-card').forEach(function (card) {
        card.addEventListener('click', function () {
            var target = card.dataset.target;
            if (!target) return;
            var section = document.getElementById(target);
            if (!section) return;
            // Activer la carte
            document.querySelectorAll('.aide-card').forEach(function (c) { c.classList.remove('active'); });
            card.classList.add('active');
            // Ouvrir et highlight la section
            document.querySelectorAll('.aide-section').forEach(function (s) { s.classList.remove('open', 'highlight'); });
            section.classList.add('open', 'highlight');
            // Scroll
            setTimeout(function () {
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 50);
        });
        card.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.click();
            }
        });
    });

    // ---- Recherche client ----
    var searchInput = document.getElementById('aide-search');
    var noResult = document.getElementById('aide-no-result');

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            var q = searchInput.value.trim().toLowerCase();
            var anyVisible = false;

            document.querySelectorAll('.aide-section').forEach(function (section) {
                if (!q) {
                    section.style.display = '';
                    anyVisible = true;
                    return;
                }
                var text = section.textContent.toLowerCase();
                if (text.includes(q)) {
                    section.style.display = '';
                    section.classList.add('open');
                    anyVisible = true;
                } else {
                    section.style.display = 'none';
                    section.classList.remove('open', 'highlight');
                }
            });

            // Grille : masquer cartes sans résultat de section
            document.querySelectorAll('.aide-card').forEach(function (card) {
                if (!q) {
                    card.style.display = '';
                    return;
                }
                var target = card.dataset.target;
                var section = target ? document.getElementById(target) : null;
                card.style.display = (section && section.style.display !== 'none') ? '' : 'none';
            });

            if (noResult) {
                noResult.style.display = anyVisible ? 'none' : '';
            }
        });
    }
});
