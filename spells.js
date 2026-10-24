// All sorcerer/wizard spells (index.html): reads spells.tsv and renders spell entries in pages of 60.
(function () {
    'use strict';
    const C = window.SpellCards;
    const PAGE = 60;
    const LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
    const TAB_COLOURS = ['--guide-buff', '--guide-salmon', '--guide-sage', '--guide-cadet', '--guide-lilac', '--guide-ochre'];
    const COLS = {
        name: 'name', school: 'school', subschool: 'subschool', descriptor: 'descriptor', casting_time: 'casting_time',
        components: 'components', range: 'range', area: 'area', effect: 'effect', targets: 'targets', duration: 'duration',
        save: 'saving_throw', sr: 'spell_resistence', short: 'short_description', source: 'source', aon: 'url', pfsrd: 'pfsrd'
    };

    const $ = id => document.getElementById(id);
    const state = { tab: 'all', q: '', school: '', mine: false };
    let rows = [];
    let matches = [];
    let rendered = 0;

    $('searchIcon').outerHTML = C.ICON_SEARCH;

    const clean = v => { v = (v || '').trim(); return v === 'NULL' || v === '-' ? '' : v; };

    function parseTsv(text) {
        const lines = text.split('\n');
        const header = lines[0].replace(/\r$/, '').split('\t');
        const at = {};
        header.forEach((h, i) => { at[h] = i; });
        for (const need of ['name', 'school', 'wiz']) {
            if (!(need in at)) throw new Error('spells.tsv has no "' + need + '" column.');
        }
        const out = [];
        for (let n = 1; n < lines.length; n++) {
            const line = lines[n].replace(/\r$/, '');
            if (!line.trim()) continue;
            const cells = line.split('\t');
            const get = col => (col in at ? clean(cells[at[col]]) : '');
            const s = {};
            for (const k in COLS) s[k] = get(COLS[k]);
            s.name = s.name.replace(/\s*\(Not in Spellbook\)\s*$/i, '');
            s.school = s.school.toLowerCase();
            s.url = s.pfsrd || s.aon;
            s.link_source = s.pfsrd ? 'd20pfsrd' : 'aon';
            const lv = parseInt(get('wiz') || get('sor'), 10);
            s.level = isNaN(lv) ? null : lv;
            s.text = get('description_formated') || get('description');
            s.mine = get('On my list') === '1';
            s.lname = s.name.toLowerCase();
            out.push(s);
        }
        return out.sort((a, b) => (a.level ?? 99) - (b.level ?? 99) || a.lname.localeCompare(b.lname));
    }

    function hay(s) {
        if (s.hay == null) {
            s.hay = (s.short + ' ' + s.text.replace(/<[^>]+>/g, ' ')).toLowerCase().replace(/\s+/g, ' ');
        }
        return s.hay;
    }

    function buildTabs() {
        const counts = {};
        rows.forEach(s => { counts[s.level] = (counts[s.level] || 0) + 1; });
        const tabs = [{ key: 'all', label: 'All', n: rows.length }].concat(LEVELS.map(l => ({ key: String(l), label: String(l), n: counts[l] || 0 })));
        $('tabs').innerHTML = tabs.map((t, i) =>
            '<button type="button" class="guide" role="tab" id="tab-' + t.key + '" data-tab="' + t.key + '" aria-controls="results"' +
            ' style="--tab: var(' + TAB_COLOURS[i % TAB_COLOURS.length] + ')"' +
            (t.key === 'all' ? '' : ' aria-label="Level ' + t.key + ', ' + t.n + ' spells"') + '>' +
            t.label + (t.key === 'all' ? '' : '<span class="n">' + t.n + '</span>') + '</button>').join('');
        $('tabs').addEventListener('click', ev => {
            const b = ev.target.closest('.guide');
            if (b) selectTab(b.dataset.tab);
        });
        $('tabs').addEventListener('keydown', ev => {
            if (!/^(ArrowLeft|ArrowRight|Home|End)$/.test(ev.key)) return;
            const all = Array.from($('tabs').querySelectorAll('.guide'));
            let i = all.findIndex(b => b.dataset.tab === state.tab);
            i = ev.key === 'Home' ? 0 : ev.key === 'End' ? all.length - 1 : (i + (ev.key === 'ArrowRight' ? 1 : -1) + all.length) % all.length;
            selectTab(all[i].dataset.tab);
            all[i].focus();
            ev.preventDefault();
        });
    }

    function selectTab(key) {
        state.tab = key;
        $('tabs').querySelectorAll('.guide').forEach(b => {
            const on = b.dataset.tab === key;
            b.setAttribute('aria-selected', String(on));
            b.tabIndex = on ? 0 : -1;
            if (on) {
                $('tabRule').style.setProperty('--tab-active', b.style.getPropertyValue('--tab'));
                b.scrollIntoView({ block: 'nearest', inline: 'nearest' });
            }
        });
        $('results').setAttribute('aria-labelledby', 'tab-' + key);
        apply();
    }

    function buildSchools() {
        const chips = [{ s: '', abbr: 'All', full: 'All schools' }].concat(C.SCHOOLS.map(s => ({ s, abbr: C.abbr(s), full: s })));
        $('schools').insertAdjacentHTML('beforeend', chips.map(c =>
            '<button type="button" class="chip" data-school="' + c.s + '" aria-pressed="' + (c.s === '') + '"' +
            (c.s ? ' aria-label="' + c.full + '"' : '') + '><span class="abbr">' + c.abbr + '</span><span class="full">' + c.full + '</span></button>').join(''));
        $('schools').addEventListener('click', ev => {
            const b = ev.target.closest('.chip');
            if (!b) return;
            state.school = state.school === b.dataset.school ? '' : b.dataset.school;
            $('schools').querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', String(c.dataset.school === state.school)));
            apply();
        });
    }

    function apply() {
        const q = state.q;
        const level = state.tab === 'all' ? null : +state.tab;
        const base = rows.filter(s => (level === null || s.level === level) &&
            (!state.school || s.school === state.school) && (!state.mine || s.mine));
        if (q) {
            const byName = base.filter(s => s.lname.includes(q));
            const named = new Set(byName);
            matches = byName.concat(base.filter(s => !named.has(s) && hay(s).includes(q)));
        } else {
            matches = base;
        }
        rendered = 0;
        $('results').textContent = '';
        if (!matches.length) {
            $('results').innerHTML = '<div class="card notice"><div class="card-head"><span class="call">NIL</span>' +
                '<h2>No spells match</h2><span class="aside"></span></div><p>Try fewer letters, another level or school.</p></div>';
        }
        more();
    }

    function more() {
        const next = matches.slice(rendered, rendered + PAGE);
        $('results').insertAdjacentHTML('beforeend', next.map(s => {
            const i = s.idx;
            return C.card(s, {
                id: 'r' + i,
                stamps: s.mine ? [{ text: 'In book' }] : [],
                teaser: s.short ? '' : C.teaser(s.text, 160)
            }).replace('<article ', '<article data-i="' + i + '" ');
        }).join(''));
        rendered += next.length;
        $('foot').hidden = rendered >= matches.length;
        $('more').textContent = 'Show more spells (' + (matches.length - rendered) + ' left)';
        $('tally').innerHTML = 'Showing <b>' + rendered + '</b> of ' + matches.length.toLocaleString('en') + ' spells';
    }

    function wireControls() {
        let t = 0;
        $('q').addEventListener('input', () => {
            clearTimeout(t);
            t = setTimeout(() => { state.q = $('q').value.trim().toLowerCase(); apply(); }, 120);
        });
        $('mine').addEventListener('click', () => {
            state.mine = !state.mine;
            $('mine').setAttribute('aria-pressed', String(state.mine));
            apply();
        });
        $('more').addEventListener('click', more);
        if ('IntersectionObserver' in window) {
            new IntersectionObserver(entries => {
                if (entries.some(e => e.isIntersecting) && rendered < matches.length) more();
            }, { rootMargin: '800px 0px' }).observe($('sentinel'));
        }
        C.wire($('results'), art => rows[+art.dataset.i]);
    }

    async function load() {
        const res = await fetch('spells.tsv');
        if (!res.ok) throw new Error('spells.tsv answered HTTP ' + res.status + ' ' + res.statusText + '.');
        const size = +res.headers.get('content-length');
        if (!res.body || !size || !window.TextDecoder) return res.text();
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let text = '', got = 0, last = 0;
        for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            got += value.length;
            text += decoder.decode(value, { stream: true });
            if (got - last > 400000) {
                last = got;
                $('progress').textContent = 'Read ' + (got / 1e6).toFixed(1) + ' of ' + (size / 1e6).toFixed(1) + ' MB of spells.tsv.';
            }
        }
        return text + decoder.decode();
    }

    load()
        .then(text => {
            rows = parseTsv(text);
            rows.forEach((s, i) => { s.idx = i; });
            if (!rows.length) throw new Error('spells.tsv has no spell rows.');
            $('total').textContent = rows.length.toLocaleString('en') + ' spells';
            buildTabs();
            buildSchools();
            wireControls();
            selectTab('all');
        })
        .catch(err => {
            $('results').innerHTML = '<div class="card notice error" role="alert"><div class="card-head"><span class="call">ERR</span>' +
                '<h2>The spell list did not load</h2><span class="aside"></span></div><p>' + C.esc(location.protocol === 'file:'
                    ? 'Opened from disk, so the browser will not read spells.tsv. Serve the folder over HTTP (python3 -m http.server).'
                    : 'Could not load the spell list: ' + err.message) + '</p></div>';
        });
})();
