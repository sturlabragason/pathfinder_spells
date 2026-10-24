// Index-card rendering shared by index.html (all spells) and caladrel_ecthelion/index.html.
(function () {
    'use strict';

    const ABBR = {
        abjuration: 'ABJ', conjuration: 'CON', divination: 'DIV', enchantment: 'ENC', evocation: 'EVO',
        illusion: 'ILL', necromancy: 'NEC', transmutation: 'TRS', universal: 'UNI'
    };
    const SCHOOLS = Object.keys(ABBR);
    const AON_SEARCH = 'https://aonprd.com/Search.aspx?Query=';
    const ALLOWED = new Set(['P', 'I', 'EM', 'B', 'STRONG', 'BR', 'UL', 'OL', 'LI', 'TABLE', 'THEAD', 'TBODY',
        'TR', 'TH', 'TD', 'SUP', 'SUB', 'H3', 'H4', 'H5', 'CAPTION']);

    const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
        c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    const abbr = school => ABBR[school] || (school ? school.slice(0, 3).toUpperCase() : '???');

    const ICON_CHEVRON = '<svg class="icon chevron" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">' +
        '<path d="M3.5 6l4.5 4.5L12.5 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    const ICON_SEARCH = '<svg class="icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">' +
        '<circle cx="7" cy="7" r="4.75" fill="none" stroke="currentColor" stroke-width="1.5"/>' +
        '<path d="M10.5 10.5l3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';

    // Rules text comes from a spreadsheet export and Foundry: keep the formatting tags, drop everything else.
    function sanitize(html) {
        const tpl = document.createElement('template');
        tpl.innerHTML = String(html || '').replace(/@\w+\[[^\]]*\](?:\{([^}]*)\})?/g, (m, label) => label || '');
        (function walk(node) {
            for (const child of Array.from(node.childNodes)) {
                if (child.nodeType === 1) {
                    walk(child);
                    if (!ALLOWED.has(child.tagName)) {
                        if (/^(SCRIPT|STYLE|IFRAME|OBJECT|EMBED|svg|math)$/i.test(child.tagName)) child.remove();
                        else child.replaceWith(...child.childNodes);
                    } else {
                        for (const a of Array.from(child.attributes)) {
                            if (!/^(colspan|rowspan)$/i.test(a.name)) child.removeAttribute(a.name);
                        }
                    }
                } else if (child.nodeType !== 3) {
                    child.remove();
                }
            }
        })(tpl.content);
        return tpl.content;
    }

    function typedRow(label, value) {
        if (!value) return '';
        return '<li><span class="k">' + esc(label) + '</span><span class="lead"></span><span class="v">' + esc(value) + '</span></li>';
    }

    // spell: {name, level, school, subschool, descriptor, casting_time, components, range, area, effect,
    //         targets, duration, save, sr, short, source, url, link_source, text}
    //         url is the d20pfsrd page when link_source is 'd20pfsrd', else the Archives of Nethys link.
    // opts:   {id, dc, stamps: [{text, cls}], teaser}
    function card(spell, opts) {
        opts = opts || {};
        const id = opts.id;
        const school = spell.school || '';
        const sub = [spell.subschool && '(' + spell.subschool + ')', spell.descriptor && '[' + spell.descriptor + ']']
            .filter(Boolean).join(' ');
        const short = spell.short || opts.teaser || '';
        const stamps = (opts.stamps || []).map(s => '<span class="stamp ' + (s.cls || '') + '">' + esc(s.text) + '</span>').join('');
        return '<article class="card spell" data-school="' + esc(school) + '" aria-labelledby="' + id + '-name">' +
            '<div class="card-head">' +
            '<span class="call">' + abbr(school) + '·' + (spell.level == null ? '?' : spell.level) + '</span>' +
            '<h3 id="' + id + '-name">' + esc(spell.name) + '</h3>' +
            (opts.dc ? '<span class="aside dc">DC <b>' + opts.dc + '</b></span>' : '<span class="aside"></span>') +
            '</div>' +
            '<div class="card-body">' +
            '<p class="marks ruled"><span class="school-mark">' + esc(school || 'no school') + '</span>' +
            (sub ? ' <span class="sch sub">' + esc(sub) + '</span>' : '') + '</p>' +
            (stamps ? '<p class="stamps">' + stamps + '</p>' : '') +
            '<ul class="typed">' +
            typedRow('Casting', spell.casting_time) +
            typedRow('Components', spell.components) +
            typedRow('Range', spell.range) +
            typedRow('Area', spell.area) +
            typedRow('Effect', spell.effect) +
            typedRow('Targets', spell.targets) +
            typedRow('Duration', spell.duration) +
            typedRow('Save', spell.save) +
            typedRow('SR', spell.sr) +
            '</ul>' +
            (short ? '<p class="short ruled">' + esc(short) + '</p>' : '') +
            '<button type="button" class="unfold" aria-expanded="false" aria-controls="' + id + '-rules">' +
            '<span class="when-closed">Rules text</span><span class="when-open">Fold away</span>' + ICON_CHEVRON + '</button>' +
            '<div class="fold" id="' + id + '-rules"><div class="fold-inner"></div></div>' +
            '</div></article>';
    }

    function fillRules(inner, spell) {
        inner.textContent = '';
        const rules = document.createElement('div');
        rules.className = 'rules ruled';
        rules.appendChild(sanitize(spell.text || ''));
        if (!rules.textContent.trim()) rules.innerHTML = '<p>No rules text on file for this card.</p>';
        inner.appendChild(rules);
        const foot = document.createElement('p');
        foot.className = 'rules-foot';
        const url = spell.url || AON_SEARCH + encodeURIComponent(spell.name);
        const label = spell.url && spell.link_source === 'd20pfsrd' ? 'd20pfsrd' : 'Archives of Nethys';
        foot.innerHTML = (spell.source ? '<span class="source">Source: ' + esc(spell.source) + '</span>' : '') +
            '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + label + ' →</a>';
        inner.appendChild(foot);
    }

    // Wires the unfold buttons inside container. getSpell(article) returns the spell for a card.
    function wire(container, getSpell) {
        container.addEventListener('click', ev => {
            const art = ev.target.closest('article.spell');
            if (!art || ev.target.closest('a, .fold')) return;
            if (!ev.target.closest('.unfold') && (window.getSelection() + '').length) return;
            const btn = art.querySelector('.unfold');
            const open = btn.getAttribute('aria-expanded') !== 'true';
            const inner = art.querySelector('.fold-inner');
            if (open && !inner.firstChild) fillRules(inner, getSpell(art));
            btn.setAttribute('aria-expanded', String(open));
            art.classList.toggle('open', open);
        });
    }

    function teaser(text, n) {
        const plain = String(text || '').replace(/<[^>]+>/g, ' ').replace(/@\w+\[[^\]]*\](?:\{([^}]*)\})?/g, '$1')
            .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
            .replace(/\s+/g, ' ').trim();
        return plain.length > n ? plain.slice(0, n).replace(/\s+\S*$/, '') + '…' : plain;
    }

    window.SpellCards = { SCHOOLS, ABBR, abbr, esc, card, wire, teaser, ICON_SEARCH, ICON_CHEVRON };
})();
