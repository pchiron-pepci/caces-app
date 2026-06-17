(function () {
    'use strict';

    var dataEl = document.getElementById('projection-data');
    if (!dataEl) return;

    var questions = JSON.parse(dataEl.dataset.questions);
    var N = parseInt(dataEl.dataset.total, 10);
    if (!N || N === 0) return;

    var TOTAL_MS = 3600 * 1000;
    var DUR_MS   = TOTAL_MS / N;   // durée par question, recalculée sur N réel

    var currentIdx          = 0;
    var elapsedBeforePause  = 0;   // ms accumulées hors session courante
    var playStartTs         = null; // Date.now() au dernier play (null si pause)
    var interval            = null;
    var finished            = false;

    // ── Utilitaires temps ──────────────────────────────────────────
    function getElapsedMs() {
        return elapsedBeforePause + (playStartTs !== null ? Date.now() - playStartTs : 0);
    }

    function remainingMs() {
        return Math.max(0, TOTAL_MS - getElapsedMs());
    }

    // ── Affichage ─────────────────────────────────────────────────
    function pad2(n) { return n < 10 ? '0' + n : '' + n; }

    function renderTimer() {
        var rem  = Math.ceil(remainingMs() / 1000);
        var mm   = Math.floor(rem / 60);
        var ss   = rem % 60;
        var el   = document.getElementById('proj-timer');
        el.textContent = pad2(mm) + ':' + pad2(ss);
        if (rem <= 60) el.classList.add('urgent');
        else           el.classList.remove('urgent');
    }

    function renderQuestion(idx) {
        var q = questions[idx];
        document.getElementById('proj-q-num').textContent =
            'Question ' + (idx + 1) + ' / ' + N;
        document.getElementById('proj-theme-label').textContent =
            'Thème ' + q.theme;
        document.getElementById('proj-q-numero').textContent =
            'Q ' + q.seq;
        document.getElementById('proj-q-texte').textContent = q.texte || '';

        var imgZone = document.getElementById('proj-img-zone');
        var img     = document.getElementById('proj-img');
        if (q.image) {
            img.src = q.image;
            imgZone.classList.add('visible');
        } else {
            img.src = '';
            imgZone.classList.remove('visible');
        }
    }

    function renderEtat(playing) {
        var btn = document.getElementById('btn-playpause');
        var lbl = document.getElementById('proj-etat');
        if (playing) {
            btn.textContent = '⏸ Pause';
            lbl.textContent = 'Lecture';
        } else {
            btn.textContent = '▶ Lecture';
            lbl.textContent = 'En pause';
        }
    }

    // ── Tick (interval 250 ms pour un affichage chrono fluide) ────
    function tick() {
        renderTimer();

        if (remainingMs() <= 0 && !finished) {
            finished = true;
            pause(true);
            document.getElementById('proj-overlay-fin').style.display = 'flex';
            return;
        }

        var expectedIdx = Math.min(
            Math.floor(getElapsedMs() / DUR_MS),
            N - 1
        );
        if (expectedIdx !== currentIdx) {
            currentIdx = expectedIdx;
            renderQuestion(currentIdx);
        }
    }

    // ── Contrôles ─────────────────────────────────────────────────
    function play() {
        if (finished) return;
        playStartTs = Date.now();
        renderEtat(true);
        interval = setInterval(tick, 250);
    }

    function pause(silent) {
        if (playStartTs !== null) {
            elapsedBeforePause += Date.now() - playStartTs;
            playStartTs = null;
        }
        if (interval) { clearInterval(interval); interval = null; }
        if (!silent) renderEtat(false);
    }

    function reset() {
        pause(true);
        finished              = false;
        elapsedBeforePause    = 0;
        playStartTs           = null;
        currentIdx            = 0;
        renderQuestion(0);
        renderTimer();
        renderEtat(false);
        document.getElementById('proj-overlay-fin').style.display = 'none';
    }

    // ── Listeners ─────────────────────────────────────────────────
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-action]');
        if (!btn) return;
        switch (btn.dataset.action) {
            case 'playpause':
                if (playStartTs !== null) pause(false); else play();
                break;
            case 'prev':
                if (currentIdx > 0) { currentIdx--; renderQuestion(currentIdx); }
                break;
            case 'next':
                if (currentIdx < N - 1) { currentIdx++; renderQuestion(currentIdx); }
                break;
            case 'reset':
                reset();
                break;
        }
    });

    // ── Init ──────────────────────────────────────────────────────
    renderQuestion(0);
    renderTimer();
    renderEtat(false);

}());
