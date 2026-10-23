# Pathfinder Spells

A web-based tool tailored for Pathfinder spellcasters, designed to manage and filter spells for a single character. The project allows users to filter spells by level and whether they are included in the user's personalized list.

## Pages

- `index.html`: every sorcerer/wizard spell (1,897), with a level filter (0-9) and a checkbox to show only spells in Caladrel's spellbook.
- `caladrel_ecthelion/index.html`: the character page for Caladrel Ecthëlion (elf Wizard 7, Conjurer with the Teleportation subschool). It shows his portrait, spells per day and save DCs for spell levels 0-4, how many spells of each level are in his spellbook, and the spell table filtered to his spellbook by default (level filter 0-4). Spells from his opposed schools (Enchantment, Divination) are shaded and tagged "opposed". His full character sheet lives in [sturlabragason/pathfinder](https://github.com/sturlabragason/pathfinder).

Both pages use Tailwind CSS 2 and DataTables 1.11 from public CDNs, so they need internet access, and `styles.css` for the parchment look. There is no build step.

## Spell links

Each spell name links to its page on [Archives of Nethys](https://aonprd.com/) (`https://aonprd.com/SpellDisplay.aspx?ItemName=<name>`). The link is stored in the `url` column of `spells.tsv` by `scripts/update_spells.py`, which matches every spell against the AoN wizard spell list. The page does not guess URLs. A spell that has no match on AoN links to an AoN search for its name instead (8 spells at the moment, none of them in Caladrel's spellbook).

## Caladrel's spellbook

`caladrel_ecthelion/spellbook.txt` is the list of spells he knows: one spell name per line, spelled as in the `name` column of `spells.tsv` (case does not matter). Lines starting with `#` are comments. When he learns a spell, add one line. Both pages read this file directly, so the change shows up on the next page load.

`scripts/update_spells.py` also copies the list into the `On my list` column of `spells.tsv` and reports any name it cannot find. The pages only fall back to that column if `spellbook.txt` cannot be loaded.

## Updating the spell data

```bash
pip install pyyaml
python3 scripts/update_spells.py                 # refresh spells.tsv
python3 scripts/update_spells.py --check-links   # also fetch every spellbook link (about 1 request per second)
```

The script keeps the existing rows of `spells.tsv`. It adds sorcerer/wizard spells that are missing, taken from the [Foundry VTT Pathfinder 1e system](https://gitlab.com/foundryvtt_pathfinder1e/foundryvtt-pathfinder1) spell pack, and regenerates those added rows (id `fvtt:...`) on every run. It then rewrites the `url` and `On my list` columns. It makes one download from gitlab.com and one request to aonprd.com. Rows added from Foundry have the main columns filled in (school, level, casting time, components, range, duration, save, description); some of the sheet's per-descriptor and per-class columns stay empty, and the `source` column holds the Paizo product code (for example `PZO1110 p. 283`) instead of the book name.

`spells.txt` is an old copy of the original sheet export. The pages do not use it.

## Running locally

The pages load `spells.tsv` and `spellbook.txt` over HTTP, so opening `index.html` from disk does not work. From the repository root:

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

- The site is built for one character. To use it for another, replace `caladrel_ecthelion/` (page and `spellbook.txt`) and the `data-*` attributes on the page's `<body>`.
- The spell levels shown are the sorcerer/wizard levels (`wiz` column).

## Data Source

- The original 1,648 spells come from a publicly available Google Spreadsheet maintained by Kyler Dixon: [Pathfinder Spell Database](https://docs.google.com/spreadsheets/d/197aOpt71IDoO6yCmOB1mtEhGE598jBVs5iZox8YMHAk/edit?usp=sharing). Its current export has the same 1,648 spells, so it has not been updated since.
- Spells added since then come from the [Foundry VTT Pathfinder 1e system](https://gitlab.com/foundryvtt_pathfinder1e/foundryvtt-pathfinder1) (`packs/spells`).
- Spell links point to [Archives of Nethys](https://aonprd.com/).

## Open Game License

This project presents spell data and information under the Open Game License (OGL) as provided by Paizo Publishing for the Pathfinder Roleplaying Game. Users of this project should ensure they comply with the OGL when using and distributing content related to Pathfinder.

## Links

- Repository: [Pathfinder Spells on GitHub](https://github.com/sturlabragason/pathfinder_spells)
- Character sheet: [sturlabragason/pathfinder](https://github.com/sturlabragason/pathfinder)
- The site is not published on GitHub Pages at the moment.

For any questions or issues, please open an issue on the GitHub repository.

