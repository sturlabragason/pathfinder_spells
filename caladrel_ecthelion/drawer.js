// Caladrel's spell drawer: renders ./spellbook.json (written by scripts/build_spellbook_json.py).
(function () {
    'use strict';
    const C = window.SpellCards;
    const LEVELS = [0, 1, 2, 3, 4];
    const TAB_COLOURS = ['--guide-buff', '--guide-salmon', '--guide-sage', '--guide-cadet', '--guide-lilac', '--guide-ochre'];
    const ORD = ['0', '1st', '2nd', '3rd', '4th'];

    const $ = id => document.getElementById(id);
    const state = { tab: 'all', q: '', school: '' };
    let spells = [];
    let character = null;

    document.getElementById('searchIcon').outerHTML = C.ICON_SEARCH;

    function dcFor(spell) {
        const save = (spell.save || '').trim();
        if (!save || /^none\b/i.test(save) || spell.level == null) return null;
        return 10 + spell.level + character.int_mod + (spell.school === character.school ? 2 : 0);
    }

    function buildTabs(counts) {
        const tabs = [{ key: 'all', label: 'All', n: spells.length }].concat(
            LEVELS.map(l => ({ key: String(l), label: ORD[l], n: counts[l] || 0 })));
        $('tabs').innerHTML = tabs.map((t, i) =>
            '<button type="button" class="guide" role="tab" id="tab-' + t.key + '" data-tab="' + t.key + '"' +
            ' aria-controls="levels" style="--tab: var(' + TAB_COLOURS[i] + ')">' +
            C.esc(t.label) + '<span class="n">' + t.n + '</span></button>').join('');
        $('tabs').addEventListener('click', ev => {
            const b = ev.target.closest('.guide');
            if (b) selectTab(b.dataset.tab, true);
        });
        $('tabs').addEventListener('keydown', ev => {
            if (!/^(ArrowLeft|ArrowRight|Home|End)$/.test(ev.key)) return;
            const all = Array.from($('tabs').querySelectorAll('.guide'));
            let i = all.findIndex(b => b.dataset.tab === state.tab);
            i = ev.key === 'Home' ? 0 : ev.key === 'End' ? all.length - 1 : (i + (ev.key === 'ArrowRight' ? 1 : -1) + all.length) % all.length;
            selectTab(all[i].dataset.tab, true);
            all[i].focus();
            ev.preventDefault();
        });
    }

    function selectTab(key, fromUser) {
        state.tab = key;
        $('tabs').querySelectorAll('.guide').forEach(b => {
            const on = b.dataset.tab === key;
            b.setAttribute('aria-selected', String(on));
            b.tabIndex = on ? 0 : -1;
            if (on) $('tabRule').style.setProperty('--tab-active', b.style.getPropertyValue('--tab'));
        });
        $('levels').setAttribute('aria-labelledby', 'tab-' + key);
        if (fromUser) history.replaceState(null, '', key === 'all' ? location.pathname : '#level-' + key);
        apply();
    }

    function buildSchools() {
        const present = C.SCHOOLS.filter(s => spells.some(x => x.school === s));
        const chips = [{ s: '', abbr: 'All', full: 'All schools' }].concat(present.map(s => ({ s, abbr: C.abbr(s), full: s })));
        $('schools').insertAdjacentHTML('beforeend', chips.map(c =>
            '<button type="button" class="chip" data-school="' + c.s + '" aria-pressed="' + (c.s === '' ) + '"' +
            (c.s ? ' aria-label="' + c.full + '"' : '') + '>' +
            '<span class="abbr">' + c.abbr + '</span><span class="full">' + c.full + '</span></button>').join(''));
        $('schools').addEventListener('click', ev => {
            const b = ev.target.closest('.chip');
            if (!b) return;
            state.school = state.school === b.dataset.school ? '' : b.dataset.school;
            $('schools').querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', String(c.dataset.school === state.school)));
            apply();
        });
    }

    function summary(level, known) {
        const slots = character.slots[String(level)];
        const dc = 10 + level + character.int_mod;
        const title = level === 0 ? 'Cantrips' : ORD[level] + ' level';
        return '<section class="card summary" aria-labelledby="sum-' + level + '">' +
            '<div class="card-head"><span class="call">LVL·' + level + '</span>' +
            '<h2 id="sum-' + level + '">' + title + '</h2>' +
            '<span class="aside">' + known + ' known</span></div>' +
            '<ul class="typed">' +
            '<li><span class="k">Slots per day</span><span class="lead"></span><span class="v">' + slots +
            (level > 0 ? ' (1 conjuration)' : '') + '</span></li>' +
            '<li><span class="k">Save DC</span><span class="lead"></span><span class="v">' + dc + '</span></li>' +
            '<li data-school="conjuration"><span class="k">Conjuration DC</span><span class="lead"></span><span class="v sch">' + (dc + 2) + '</span></li>' +
            '<li><span class="k">Spells known</span><span class="lead"></span><span class="v" data-known="' + level + '">' + known + '</span></li>' +
            '</ul>' +
            (known ? '' : '<p class="empty"><span class="stamp">No cards filed</span></p>') +
            '<p class="short ruled nomatch" hidden>No cards in this drawer match the search.</p>' +
            '</section>';
    }

    function render(data) {
        character = data.character;
        spells = data.spells;
        const counts = {};
        spells.forEach(s => { counts[s.level] = (counts[s.level] || 0) + 1; });
        $('total').textContent = spells.length + ' cards';

        $('levels').innerHTML = LEVELS.map(level => {
            const cards = spells.map((s, i) => [s, i]).filter(([s]) => s.level === level).map(([s, i]) => {
                const stamps = [];
                if (s.opposed) stamps.push({ text: 'Opposed · 2 slots' });
                if (s.in_book === false) stamps.push({ text: 'From memory' });
                return C.card(s, { id: 's' + i, dc: dcFor(s), stamps }).replace('<article ', '<article data-i="' + i + '" ');
            }).join('');
            return '<div class="level" data-level="' + level + '" id="level-' + level + '">' + summary(level, counts[level] || 0) + cards + '</div>';
        }).join('');

        buildTabs(counts);
        buildSchools();
        C.wire($('levels'), art => spells[+art.dataset.i]);

        let t = 0;
        $('q').addEventListener('input', () => {
            clearTimeout(t);
            t = setTimeout(() => { state.q = $('q').value.trim().toLowerCase(); apply(); }, 60);
        });
        const m = /^#level-([0-4])$/.exec(location.hash);
        selectTab(m ? m[1] : 'all', false);
    }

    function apply() {
        const q = state.q;
        let shown = 0;
        $('levels').querySelectorAll('.level').forEach(sec => {
            const visible = state.tab === 'all' || sec.dataset.level === state.tab;
            sec.hidden = !visible;
            let inLevel = 0;
            sec.querySelectorAll('article.spell').forEach(art => {
                const s = spells[+art.dataset.i];
                const ok = (!state.school || s.school === state.school) &&
                    (!q || s.name.toLowerCase().includes(q) || (s.short || '').toLowerCase().includes(q));
                art.hidden = !ok;
                if (ok) inLevel++;
            });
            const total = sec.querySelectorAll('article.spell').length;
            sec.querySelector('.nomatch').hidden = !(total && !inLevel);
            if (visible) shown += inLevel;
        });
        const scope = state.tab === 'all' ? spells.length : spells.filter(s => String(s.level) === state.tab).length;
        $('tally').innerHTML = 'Showing <b>' + shown + '</b> of ' + scope + ' cards' +
            (state.tab === 'all' ? '' : ' at ' + (state.tab === '0' ? 'level 0' : ORD[+state.tab] + ' level'));
    }

    function fail(msg) {
        $('levels').innerHTML = '<div class="card notice error" role="alert"><div class="card-head"><span class="call">ERR</span>' +
            '<h2>The drawer is stuck</h2><span class="aside"></span></div><p>' + C.esc(msg) + '</p></div>';
        $('tally').textContent = '';
    }

    fetch('spellbook.json', { cache: 'no-cache' })
        .then(r => {
            if (!r.ok) throw new Error('spellbook.json answered HTTP ' + r.status + ' ' + r.statusText + '.');
            return r.json().catch(() => { throw new Error('spellbook.json is not valid JSON.'); });
        })
        .then(render)
        .catch(err => fail(location.protocol === 'file:'
            ? 'Opened from disk, so the browser will not read spellbook.json. Serve the folder over HTTP (python3 -m http.server).'
            : 'Could not load the spellbook: ' + err.message));
})();
