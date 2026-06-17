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
    var lastAutoStep        = 0;   // dernier palier d'auto-avance franchi
    var elapsedBeforePause  = 0;   // ms accumulées hors session courante
    var playStartTs         = null; // Date.now() au dernier play (null si pause)
    var interval            = null;
    var finished            = false;

    // ── Synthèse vocale — config identique à test_theorie.html ────
    // lang fr-FR, rate 0.9, pas de voix sélectionnée, pas de pitch.
    // Contournement bug Chrome : cancel() suivi immédiatement de speak()
    // peut avaler la lecture. On différe speak() de 100 ms via setTimeout
    // (fonction, pas string — CSP-safe). Le timeout précédent est toujours
    // annulé pour éviter tout chevauchement lors des auto-avances rapides.
    var _speakTimer = null;

    function speak(text) {
        if (!window.speechSynthesis || !text) return;
        if (_speakTimer) { clearTimeout(_speakTimer); _speakTimer = null; }
        window.speechSynthesis.cancel();
        _speakTimer = setTimeout(function () {
            _speakTimer = null;
            var u = new SpeechSynthesisUtterance(text);
            u.lang = 'fr-FR';
            u.rate = 0.9;
            window.speechSynthesis.speak(u);
        }, 100);
    }

    function cancelSpeech() {
        if (_speakTimer) { clearTimeout(_speakTimer); _speakTimer = null; }
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }

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
            'Question ' + (idx + 1) + ' / ' + N;
        document.getElementById('proj-theme-label').textContent =
            'Thème ' + q.theme;
        document.getElementById('proj-q-numero').textContent =
            'Q ' + q.seq;
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

        // Chrono monotone — auto-avance par crans depuis la position courante.
        // lastAutoStep est le dernier palier franchi ; on avance d'autant de crans
        // que de paliers nouveaux, borné à N-1. Un saut manuel ne modifie JAMAIS
        // elapsed ni lastAutoStep : la prochaine auto-avance fera +1 depuis la
        // position manuelle courante, au franchissement du palier suivant.
        var palier = Math.floor(getElapsedMs() / DUR_MS);
        if (palier > lastAutoStep) {
            var crans = Math.min(palier - lastAutoStep, N - 1 - currentIdx);
            lastAutoStep = palier;
            if (crans > 0) {
                currentIdx += crans;
                renderQuestion(currentIdx);
                speak(questions[currentIdx].texte);
            }
        }
    }

    // ── Contrôles ─────────────────────────────────────────────────
    function play() {
        if (finished) return;
        playStartTs = Date.now();
        renderEtat(true);
        interval = setInterval(tick, 250);
        speak(questions[currentIdx].texte); // lecture de la question courante au démarrage
    }

    function pause(silent) {
        if (playStartTs !== null) {
            elapsedBeforePause += Date.now() - playStartTs;
            playStartTs = null;
        }
        if (interval) { clearInterval(interval); interval = null; }
        cancelSpeech();                // coupe la voix dans tous les cas
        if (!silent) renderEtat(false);
    }

    function reset() {
        pause(true);
        finished           = false;
        elapsedBeforePause = 0;
        playStartTs        = null;
        currentIdx         = 0;
        lastAutoStep       = 0;
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
                if (currentIdx > 0) {
                    cancelSpeech();
                    currentIdx--;
                    renderQuestion(currentIdx);
                    if (playStartTs !== null) speak(questions[currentIdx].texte);
                }
                break;
            case 'next':
                if (currentIdx < N - 1) {
                    cancelSpeech();
                    currentIdx++;
                    renderQuestion(currentIdx);
                    if (playStartTs !== null) speak(questions[currentIdx].texte);
                }
                break;
            case 'reset':
                reset();
                break;
            case 'relire':
                speak(questions[currentIdx].texte); // relit la question affichée
                break;
        }
    });

    // ── Init — affiche Q1 sans parler (interaction utilisateur requise) ──
    renderQuestion(0);
    renderTimer();
    renderEtat(false);

}());
