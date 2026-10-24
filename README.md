# Pathfinder Spells

A web-based tool tailored for Pathfinder spellcasters, designed to manage and filter spells for a single character. The project allows users to filter spells by level and whether they are included in the user's personalized list.

## Pages

Published on GitHub Pages: https://sturlabragason.github.io/pathfinder_spells/

- `index.html`: every sorcerer/wizard spell (1,897) as an index card. Search by name or rules text, filter by spell level (guide tabs 0-9, the `wiz` column), by school, and to the spells in Caladrel's book (stamped "IN BOOK"). Cards render 60 at a time as you scroll. Tap a card to unfold its rules text and the Archives of Nethys link.
- `caladrel_ecthelion/index.html`: "Caladrel's spell drawer", the spellbook of Caladrel Ecthëlion (elf Wizard 7, Conjurer with the Teleportation subschool, opposed schools Enchantment and Divination). It reads `caladrel_ecthelion/spellbook.json` and shows, per spell level 0-4, slots per day, save DC, conjuration DC (+2 from Spell Focus and Greater Spell Focus) and the number of known spells, then one card per spell with its save DC. Opposed-school spells are stamped "OPPOSED · 2 SLOTS"; Read Magic, prepared from memory, is stamped "FROM MEMORY". His character sheet is at https://caladrel.sturlabragason.online/ (source: [sturlabragason/pathfinder](https://github.com/sturlabragason/pathfinder)); it also fetches `spellbook.json`.

There are no frameworks and no build step. The look is the "card catalogue" design system shared with the character sheet:

- `catalog.css`: tokens and components (brass plate, guide tabs, index card, dot-leader rows, school inks, stamps). Copied from `sturlabragason/pathfinder` (`site/catalog.css`); change it there and copy it back, do not fork it here.
- `fonts/`: Courier Prime (SIL Open Font License, `fonts/OFL.txt`).
- `spells.css`: the layer for these two pages.
- `cards.js`: renders a spell as an index card (shared by both pages).
- `spells.js`: the all-spells page. `caladrel_ecthelion/drawer.js`: the spell drawer.

## Spell links

Each spell links to its page on [Archives of Nethys](https://aonprd.com/) (`https://aonprd.com/SpellDisplay.aspx?ItemName=<name>`). The link is stored in the `url` column of `spells.tsv` by `scripts/update_spells.py`, which matches every spell against the AoN wizard spell list. The pages do not guess URLs. A spell that has no match on AoN links to an AoN search for its name instead (8 spells at the moment, none of them in Caladrel's spellbook).

## Caladrel's spellbook: adding a spell

`caladrel_ecthelion/spellbook.txt` is the list of spells he knows: one spell name per line, spelled as in the `name` column of `spells.tsv` (case does not matter). Lines starting with `#` are comments.

When he learns a spell:

1. Add one line with its name to `caladrel_ecthelion/spellbook.txt`.
2. Run `python3 scripts/update_spells.py --no-foundry --no-aon` (offline, no PyYAML needed). It sets the `On my list` column of `spells.tsv` and rewrites `caladrel_ecthelion/spellbook.json` (via `scripts/build_spellbook_json.py`). It exits with status 1 and names any line it cannot find in `spells.tsv`.
3. Commit `spellbook.txt`, `spells.tsv` and `spellbook.json` and push to `main`. GitHub Pages republishes in a minute or two, and the drawer and the character sheet pick it up.

The slots per day, caster level and opposed schools are in `CHARACTER` at the top of `scripts/build_spellbook_json.py`; change them there when he levels up.

## Updating the spell data

```bash
pip install pyyaml
python3 scripts/update_spells.py                 # refresh spells.tsv and spellbook.json
python3 scripts/update_spells.py --check-links   # also fetch every spellbook link (about 1 request per second)
python3 scripts/update_spells.py --no-foundry --no-aon   # offline: only the spellbook marks and spellbook.json
```

The script keeps the existing rows of `spells.tsv`. It adds sorcerer/wizard spells that are missing, taken from the [Foundry VTT Pathfinder 1e system](https://gitlab.com/foundryvtt_pathfinder1e/foundryvtt-pathfinder1) spell pack, and regenerates those added rows (id `fvtt:...`) on every run. It then rewrites the `url` and `On my list` columns and writes `caladrel_ecthelion/spellbook.json`. It makes one download from gitlab.com and one request to aonprd.com (skip them with `--no-foundry` and `--no-aon`). Rows added from Foundry have the main columns filled in (school, level, casting time, components, range, duration, save, description); some of the sheet's per-descriptor and per-class columns stay empty, and the `source` column holds the Paizo product code (for example `PZO1110 p. 283`) instead of the book name.

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
- Spell links point to [Archives of Nethys](https://aonprd.com/).

## Open Game License

This project presents spell data and information under the Open Game License (OGL) as provided by Paizo Publishing for the Pathfinder Roleplaying Game. Users of this project should ensure they comply with the OGL when using and distributing content related to Pathfinder.

## Links

- Repository: [Pathfinder Spells on GitHub](https://github.com/sturlabragason/pathfinder_spells)
- Character sheet: [sturlabragason/pathfinder](https://github.com/sturlabragason/pathfinder)
- Site: https://sturlabragason.github.io/pathfinder_spells/

For any questions or issues, please open an issue on the GitHub repository.

