// Spell table for index.html and caladrel_ecthelion/index.html.
// Page settings come from data-* attributes on <body>:
//   data-tsv        path to spells.tsv                 (default "spells.tsv")
//   data-spellbook  path to the spellbook name list    (default "caladrel_ecthelion/spellbook.txt")
//   data-opposed    comma-separated opposed schools    (default "enchantment,divination")
$(function () {
    const body = document.body.dataset;
    const tsvUrl = body.tsv || 'spells.tsv';
    const spellbookUrl = body.spellbook || 'caladrel_ecthelion/spellbook.txt';
    const opposed = (body.opposed || 'enchantment,divination').toLowerCase().split(',').map(s => s.trim());
    const AON_SEARCH = 'https://aonprd.com/Search.aspx?Query=';

    const $level = $('#spellLevelFilter');
    const $mine = $('#myListFilter');
    let table = null;

    const normalise = name => name.replace(/\u2019/g, "'").trim().toLowerCase();
    const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    function parseSpellbook(text) {
        return new Set(text.split(/\r?\n/)
            .map(line => line.replace(/#.*/, ''))
            .filter(line => line.trim())
            .map(normalise));
    }

    function parseTsv(text, spellbook) {
        const lines = text.split(/\r?\n/).filter(line => line.trim());
        const headers = lines[0].split('\t');
        const col = name => headers.indexOf(name);
        const c = {
            mine: col('On my list'), name: col('name'), school: col('school'), wiz: col('wiz'),
            casting: col('casting_time'), range: col('range'), url: col('url')
        };
        return lines.slice(1).map(line => {
            const cells = line.split('\t');
            const name = cells[c.name];
            const school = (cells[c.school] || '').toLowerCase();
            const url = c.url >= 0 && cells[c.url] ? cells[c.url] : AON_SEARCH + encodeURIComponent(name);
            return {
                name: name,
                school: school,
                level: parseInt(cells[c.wiz], 10),
                casting_time: cells[c.casting] || '',
                range: cells[c.range] || '',
                url: url,
                mine: spellbook ? spellbook.has(normalise(name)) : cells[c.mine] === '1',
                opposed: opposed.includes(school)
            };
        });
    }

    $.fn.dataTable.ext.search.push(function (settings, data, dataIndex, row) {
        if (settings.nTable.id !== 'spellsTable') {
            return true;
        }
        const level = $level.val();
        if (level && level !== 'All' && row.level !== parseInt(level, 10)) {
            return false;
        }
        return !$mine.prop('checked') || row.mine;
    });

    function showKnownCounts(rows) {
        $('[data-known-level]').each(function () {
            const level = parseInt(this.dataset.knownLevel, 10);
            this.textContent = rows.filter(r => r.mine && r.level === level).length;
        });
    }

    function build(rows) {
        showKnownCounts(rows);
        table = $('#spellsTable').DataTable({
            data: rows,
            pageLength: 100,
            order: [[2, 'asc'], [0, 'asc']],
            createdRow: function (tr, row) {
                if (row.opposed) {
                    tr.classList.add('opposed');
                }
                if (row.mine) {
                    tr.classList.add('mine');
                }
            },
            columns: [
                {
                    title: 'Name', data: 'name',
                    render: (name, type, row) => type === 'display'
                        ? '<a href="' + escapeHtml(row.url) + '" target="_blank" rel="noopener">' + escapeHtml(name) + '</a>'
                        : name
                },
                {
                    title: 'School', data: 'school',
                    render: (school, type, row) => type === 'display' && row.opposed
                        ? escapeHtml(school) + ' <span class="opposed-badge" title="Opposed school: costs two slots to prepare">opposed</span>'
                        : (type === 'display' ? escapeHtml(school) : school)
                },
                { title: 'Level', data: 'level', render: (level, type) => (isNaN(level) ? '' : level) },
                { title: 'Casting Time', data: 'casting_time', render: $.fn.dataTable.render.text() },
                { title: 'Range', data: 'range', render: $.fn.dataTable.render.text() }
            ]
        });
        $level.add($mine).on('change', () => table.draw());
    }

    $.when(
        $.ajax({ url: tsvUrl, dataType: 'text' }),
        $.ajax({ url: spellbookUrl, dataType: 'text' }).then(text => parseSpellbook(text), () => $.Deferred().resolve(null))
    ).done(function (tsv, spellbook) {
        if (!spellbook) {
            console.warn('Spellbook list not found at ' + spellbookUrl + '; using the "On my list" column of spells.tsv.');
        }
        build(parseTsv(tsv[0], spellbook));
    }).fail(function () {
        $('#loadError').removeClass('hidden').text('Could not load ' + tsvUrl + '. Serve this folder over HTTP (see README).');
    });
});
