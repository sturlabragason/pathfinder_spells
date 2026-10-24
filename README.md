# Pathfinder Spells

A web-based tool tailored for Pathfinder spellcasters, designed to manage and filter spells for a single character. The project allows users to filter spells by level and whether they are included in the user's personalized list.

## Pages

Published on GitHub Pages: https://sturlabragason.github.io/pathfinder_spells/

- `index.html`: every sorcerer/wizard spell (1,897) as an index card. Search by name or rules text, filter by spell level (guide tabs 0-9, the `wiz` column), by school, and to the spells in Caladrel's book (stamped "IN BOOK"). Cards render 60 at a time as you scroll. Tap a card to unfold its rules text and its d20pfsrd link.
- `caladrel_ecthelion/index.html`: "Caladrel's spell drawer", the spellbook of Caladrel Ecthëlion (elf Wizard 7, Conjurer with the Teleportation subschool, opposed schools Enchantment and Divination). It reads `caladrel_ecthelion/spellbook.json` and shows, per spell level 0-4, slots per day, save DC, conjuration DC (+2 from Spell Focus and Greater Spell Focus) and the number of known spells, then one card per spell with its save DC. Opposed-school spells are stamped "OPPOSED · 2 SLOTS"; Read Magic, prepared from memory, is stamped "FROM MEMORY". His character sheet is at https://caladrel.sturlabragason.online/ (source: [sturlabragason/pathfinder](https://github.com/sturlabragason/pathfinder)); it also fetches `spellbook.json`.

There are no frameworks and no build step. The look is the "card catalogue" design system shared with the character sheet:

- `catalog.css`: tokens and components (brass plate, guide tabs, index card, dot-leader rows, school inks, stamps). Copied from `sturlabragason/pathfinder` (`site/catalog.css`); change it there and copy it back, do not fork it here.
- `fonts/`: Courier Prime (SIL Open Font License, `fonts/OFL.txt`).
- `spells.css`: the layer for these two pages.
- `cards.js`: renders a spell as an index card (shared by both pages).
- `spells.js`: the all-spells page. `caladrel_ecthelion/drawer.js`: the spell drawer.

## Spell links

Each spell links to its page on [d20pfsrd.com](https://www.d20pfsrd.com/). The link is stored in the `pfsrd` column of `spells.tsv` by `scripts/pfsrd_links.py` (run by `scripts/update_spells.py`). The pages do not guess URLs: every link is a page listed in the d20pfsrd sitemap (`https://www.d20pfsrd.com/sitemap.xml`), and any match that is not a plain slug match under `/magic/all-spells/` is fetched and accepted only on HTTP 200 with the spell name as the page's `<h1>` or as one of its headings. Variants that d20pfsrd keeps on the base spell's page (for example *Cure Light Wounds, Mass* or *Elemental Body II*) link to that heading (`.../cure-light-wounds/#cure_light_wounds_mass`). The downloaded sitemaps and checked pages are cached in `scripts/.cache/` (not committed).

A spell that d20pfsrd does not have (55 at the moment; in Caladrel's spellbook the Paizo blog cantrips *Breeze*, *Jolt*, *Penumbra* and *Root*, and *Scoop*) has an empty `pfsrd` cell and links to [Archives of Nethys](https://aonprd.com/) instead; the card then says "Archives of Nethys". The AoN link stays in the `url` column for every spell (`https://aonprd.com/SpellDisplay.aspx?ItemName=<name>`, or an AoN search for the 8 spells AoN's wizard list does not have).

`caladrel_ecthelion/spellbook.json` has `url` (the d20pfsrd link, or the AoN link when there is none), `aon` (the AoN link) and `link_source` (`d20pfsrd` or `aon`) for each spell.

## Caladrel's spellbook: adding a spell

`caladrel_ecthelion/spellbook.txt` is the list of spells he knows: one spell name per line, spelled as in the `name` column of `spells.tsv` (case does not matter). Lines starting with `#` are comments.

When he learns a spell:

1. Add one line with its name to `caladrel_ecthelion/spellbook.txt`.
2. Run `python3 scripts/update_spells.py --no-foundry --no-aon --no-pfsrd` (offline, no PyYAML needed). It sets the `On my list` column of `spells.tsv` and rewrites `caladrel_ecthelion/spellbook.json` (via `scripts/build_spellbook_json.py`). It exits with status 1 and names any line it cannot find in `spells.tsv`.
3. Commit `spellbook.txt`, `spells.tsv` and `spellbook.json` and push to `main`. GitHub Pages republishes in a minute or two, and the drawer and the character sheet pick it up.

The slots per day, caster level and opposed schools are in `CHARACTER` at the top of `scripts/build_spellbook_json.py`; change them there when he levels up.

## Updating the spell data

```bash
pip install pyyaml
python3 scripts/update_spells.py                 # refresh spells.tsv and spellbook.json
python3 scripts/update_spells.py --check-links   # also fetch every spellbook link (about 1 request per second)
python3 scripts/update_spells.py --no-foundry --no-aon --no-pfsrd   # offline: only the spellbook marks and spellbook.json
python3 scripts/pfsrd_links.py --check-all       # only the d20pfsrd links, fetching every page (cached)
```

The script keeps the existing rows of `spells.tsv`. It adds sorcerer/wizard spells that are missing, taken from the [Foundry VTT Pathfinder 1e system](https://gitlab.com/foundryvtt_pathfinder1e/foundryvtt-pathfinder1) spell pack, and regenerates those added rows (id `fvtt:...`) on every run. It then rewrites the `url`, `pfsrd` and `On my list` columns and writes `caladrel_ecthelion/spellbook.json`. It makes one download from gitlab.com and one request to aonprd.com (skip them with `--no-foundry` and `--no-aon`), and for d20pfsrd.com downloads the sitemap (once a month, otherwise cached) and fetches only the pages it has not checked before (skip with `--no-pfsrd`). Rows added from Foundry have the main columns filled in (school, level, casting time, components, range, duration, save, description); some of the sheet's per-descriptor and per-class columns stay empty, and the `source` column holds the Paizo product code (for example `PZO1110 p. 283`) instead of the book name.

`spells.txt` is an old copy of the original sheet export. The pages do not use it.

## Running locally

The pages load `spells.tsv` and `spellbook.json` over HTTP, so opening `index.html` from disk does not work. From the repository root:

```bash
python3 -m http.server 8000
```

Then browse to http://localhost:8000/ and http://localhost:8000/caladrel_ecthelion/.

## Usage with Docker

```bash
docker build -t pathfinder-spells . && docker run -d -p 8080:80 pathfinder-spells
```

Then browse to http://localhost:8080/.

## Caveats

- The site is built for one character. To use it for another, replace `caladrel_ecthelion/` (`spellbook.txt`) and `CHARACTER` in `scripts/build_spellbook_json.py`.
- The spell levels shown are the sorcerer/wizard levels (`wiz` column).
- A few rows of the original sheet have odd school values (`see text`, `transformation`); they show without a school ink and match no school filter.

## Data Source

- The original 1,648 spells come from a publicly available Google Spreadsheet maintained by Kyler Dixon: [Pathfinder Spell Database](https://docs.google.com/spreadsheets/d/197aOpt71IDoO6yCmOB1mtEhGE598jBVs5iZox8YMHAk/edit?usp=sharing). Its current export has the same 1,648 spells, so it has not been updated since.
- Spells added since then come from the [Foundry VTT Pathfinder 1e system](https://gitlab.com/foundryvtt_pathfinder1e/foundryvtt-pathfinder1) (`packs/spells`).
- Spell links point to [d20pfsrd.com](https://www.d20pfsrd.com/), or to [Archives of Nethys](https://aonprd.com/) for spells d20pfsrd does not have.

## Open Game License

This project presents spell data and information under the Open Game License (OGL) as provided by Paizo Publishing for the Pathfinder Roleplaying Game. Users of this project should ensure they comply with the OGL when using and distributing content related to Pathfinder.

## Links

- Repository: [Pathfinder Spells on GitHub](https://github.com/sturlabragason/pathfinder_spells)
- Character sheet: [sturlabragason/pathfinder](https://github.com/sturlabragason/pathfinder)
- Site: https://sturlabragason.github.io/pathfinder_spells/

For any questions or issues, please open an issue on the GitHub repository.

