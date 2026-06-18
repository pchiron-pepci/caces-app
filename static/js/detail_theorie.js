(function () {
    'use strict';
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-action="imprimer-detail"]');
        if (btn) window.print();
    });
}());
