(function () {
    'use strict';

    var dataEl = document.getElementById('projection-data');
    if (!dataEl) return;

    var questions = JSON.parse(dataEl.dataset.questions);
    var N = parseInt(dataEl.dataset.total, 10);
    if (!N || N === 0) return;

    var TOTAL_MS = 3600 * 1000;
    var DUR_MS   = TOTAL_MS / N;   // créneau par question (ms)

    var currentIdx    = 0;
    var chronoStartTs = null;  // 1er Lecture — monotone, plafond 1h absolu
    var slotStartTs   = null;  // début du créneau courant (play-time seulement)
    var pauseBeganAt  = null;  // quand la pause a commencé (null = pas en pause)
    var playing       = false;
    var interval      = null;
    var finished      = false;

    // ── Synthèse vocale ───────────────────────────────────────────
    // lang fr-FR, rate 0.8 ; contournement bug Chrome cancel→speak :
    // setTimeout 100 ms CSP-safe + clearTimeout anti-chevauchement.
    var _speakTimer = null;

    function speak(text) {
        if (!window.speechSynthesis || !text) return;
        if (_speakTimer) { clearTimeout(_speakTimer); _speakTimer = null; }
        window.speechSynthesis.cancel();
        _speakTimer = setTimeout(function () {
            _speakTimer = null;
            var u = new SpeechSynthesisUtterance(text);
            u.lang = 'fr-FR';
            u.rate = 0.8;
            window.speechSynthesis.speak(u);
        }, 100);
    }

    function cancelSpeech() {
        if (_speakTimer) { clearTimeout(_speakTimer); _speakTimer = null; }
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }

    // ── Chrono global (monotone, inaltérable) ─────────────────────
    function getElapsedMs() {
        return chronoStartTs !== null ? Date.now() - chronoStartTs : 0;
    }

    function remainingMs() {
        return Math.max(0, TOTAL_MS - getElapsedMs());
    }

    // ── Créneau par question (pause-aware) ────────────────────────
    // slotElapsedMs() retourne le temps de LECTURE écoulé sur la
    // question courante — la pause n'est pas comptée.
    function slotElapsedMs() {
        if (slotStartTs === null) return 0;
        if (!playing && pauseBeganAt !== null) {
            // En pause : geler à l'instant où la pause a commencé
            return Math.max(0, pauseBeganAt - slotStartTs);
        }
        return Math.max(0, Date.now() - slotStartTs);
    }

    // Repart le créneau à zéro pour la question courante.
    // Si on est en pause, le créneau part de 0 mais reste gelé.
    function resetSlot() {
        slotStartTs  = Date.now();
        pauseBeganAt = playing ? null : Date.now();
    }

    // ── Affichage ─────────────────────────────────────────────────
    function pad2(n) { return n < 10 ? '0' + n : '' + n; }

    function renderTimer() {
        var rem = Math.ceil(remainingMs() / 1000);
        var el  = document.getElementById('proj-timer');
        el.textContent = pad2(Math.floor(rem / 60)) + ':' + pad2(rem % 60);
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

    function renderEtat(isPlaying) {
        var btn = document.getElementById('btn-playpause');
        var lbl = document.getElementById('proj-etat');
        if (isPlaying) {
            btn.textContent = '⏸ Pause';
            lbl.textContent = 'Lecture';
        } else {
            btn.textContent = '▶ Lecture';
            lbl.textContent = 'En pause';
        }
    }

    // ── Tick (250 ms, tourne sans interruption) ───────────────────
    function tick() {
        renderTimer();

        // Chrono global PRIME : fin à 0:00, quoi qu'il arrive
        if (remainingMs() <= 0 && !finished) {
            finished = true;
            playing  = false;
            if (interval) { clearInterval(interval); interval = null; }
            cancelSpeech();
            document.getElementById('proj-overlay-fin').style.display = 'flex';
            return;
        }

        if (!playing) return;

        // Auto-avance : créneau PAR QUESTION — ne dépend plus du chrono global
        if (slotElapsedMs() >= DUR_MS && currentIdx < N - 1) {
            currentIdx++;
            resetSlot();
            renderQuestion(currentIdx);
            speak(questions[currentIdx].texte);
        }
    }

    // ── Contrôles ─────────────────────────────────────────────────
    function play() {
        if (finished) return;
        if (chronoStartTs === null) {
            // 1er Lecture : démarre le chrono global ET le premier créneau
            chronoStartTs = Date.now();
            interval = setInterval(tick, 250);
            resetSlot();
        } else if (pauseBeganAt !== null) {
            // Reprise après pause : décaler slotStartTs pour ne pas compter la pause
            slotStartTs += Date.now() - pauseBeganAt;
            pauseBeganAt = null;
        }
        playing = true;
        renderEtat(true);
        speak(questions[currentIdx].texte);
    }

    function pause(silent) {
        if (!playing) return;
        playing      = false;
        pauseBeganAt = Date.now();
        cancelSpeech();
        if (!silent) renderEtat(false);
    }

    function reset() {
        playing      = false;
        pauseBeganAt = null;
        if (interval) { clearInterval(interval); interval = null; }
        cancelSpeech();
        finished      = false;
        chronoStartTs = null;
        slotStartTs   = null;
        currentIdx    = 0;
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
                if (playing) pause(false); else play();
                break;
            case 'prev':
                if (!finished && currentIdx > 0) {
                    cancelSpeech();
                    currentIdx--;
                    resetSlot();        // repart un créneau plein pour cette question
                    renderQuestion(currentIdx);
                    if (playing) speak(questions[currentIdx].texte);
                }
                break;
            case 'next':
                if (!finished && currentIdx < N - 1) {
                    cancelSpeech();
                    currentIdx++;
                    resetSlot();        // repart un créneau plein pour cette question
                    renderQuestion(currentIdx);
                    if (playing) speak(questions[currentIdx].texte);
                }
                break;
            case 'reset':
                reset();
                break;
            case 'relire':
                speak(questions[currentIdx].texte);
                break;
        }
    });

    // ── Init ──────────────────────────────────────────────────────
    renderQuestion(0);
    renderTimer();
    renderEtat(false);

}());
