#!/usr/bin/env python3
"""Refresh spells.tsv.

What it does, in order:

1. Reads the existing spells.tsv (originally an export of Kyler Dixon's
   "Spells DB" Google Sheet, which has not changed since this repo was made).
2. Adds sorcerer/wizard spells that are missing from it, taken from the
   Foundry VTT Pathfinder 1e system
   (https://gitlab.com/foundryvtt_pathfinder1e/foundryvtt-pathfinder1, packs/spells).
   Rows added this way get an id of "fvtt:<foundry id>" and are regenerated on
   every run, so later fixes upstream are picked up. Rows from the original
   sheet are never changed, apart from the two columns below.
3. Sets the "url" column for every spell: a direct Archives of Nethys
   (aonprd.com) SpellDisplay link when the name is on AoN's wizard spell list,
   otherwise an AoN search link.
4. Sets the "pfsrd" column: a d20pfsrd.com link verified against the
   d20pfsrd sitemap and, where needed, the page itself (scripts/pfsrd_links.py,
   which caches what it downloads in scripts/.cache/). Spells without a
   verified d20pfsrd page keep an empty cell and the pages use "url" instead.
5. Sets the "On my list" column from caladrel_ecthelion/spellbook.txt
   (one spell name per line, case-insensitive).
6. Writes caladrel_ecthelion/spellbook.json (scripts/build_spellbook_json.py),
   which the spell drawer page and the character sheet read.

Network: one download from gitlab.com and one page from aonprd.com, unless
local copies are passed with --foundry-archive / --aon-html, or skipped with
--no-foundry / --no-aon. The d20pfsrd step reads the cached sitemap (refreshed
monthly) and fetches only pages it has not checked before; skip it with
--no-pfsrd. With --no-foundry --no-aon --no-pfsrd it runs offline and only
steps 5-6 change anything.
--check-links also fetches the AoN and d20pfsrd link of every spellbook spell
(about one request per second); failed AoN links fall back to the search
link, failed d20pfsrd links are dropped.

Needs PyYAML (pip install pyyaml) unless --no-foundry is used. From the repo root:

    python3 scripts/update_spells.py [--check-links]
    python3 scripts/update_spells.py --no-foundry --no-aon --no-pfsrd   # offline: marks + JSON only
"""
import argparse
import html
import io
import re
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "spells.tsv"
SPELLBOOK = ROOT / "caladrel_ecthelion" / "spellbook.txt"
FOUNDRY_URL = ("https://gitlab.com/api/v4/projects/foundryvtt_pathfinder1e%2Ffoundryvtt-pathfinder1"
               "/repository/archive.tar.gz?path=packs/spells&sha=master")
AON_LIST_URL = "https://aonprd.com/Spells.aspx?Class=Wizard"
AON_SPELL = "https://aonprd.com/SpellDisplay.aspx?ItemName="
AON_SEARCH = "https://aonprd.com/Search.aspx?Query="
UA = "Mozilla/5.0 (pathfinder_spells update script; +https://github.com/sturlabragason/pathfinder_spells)"

# Misspellings in the original sheet, mapped to the published name.
ALIASES = {
    "adjuring step": "abjuring step",
    "liberating comand": "liberating command",
    "suppres charms and compulsions": "suppress charms and compulsions",
}

SCHOOLS = {"abj": "abjuration", "con": "conjuration", "div": "divination", "enc": "enchantment",
           "evo": "evocation", "ill": "illusion", "nec": "necromancy", "trs": "transmutation",
           "uni": "universal"}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
RANGES = {"close": "close (25 ft. + 5 ft./2 levels)", "medium": "medium (100 ft. + 10 ft./level)",
          "long": "long (400 ft. + 40 ft./level)", "touch": "touch", "personal": "personal",
          "unlimited": "unlimited", "seeText": "see text", "melee": "melee", "reach": "reach"}
ACTIVATION = {"standard": "standard action", "move": "move action", "swift": "swift action",
              "immediate": "immediate action", "full": "full-round action", "free": "free action",
              "round": "round", "minute": "minute", "hour": "hour"}
DURATIONS = {"inst": "instantaneous", "perm": "permanent", "seeText": "see text"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def key(name):
    """Name normalised for matching: case, apostrophes, spacing, trailing (...), sheet typos, roman numerals."""
    n = name.replace("\u2019", "'").replace("<", ",").lower()
    n = re.sub(r"\s*\([^)]*\)\s*$", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    n = ALIASES.get(n, n)
    return re.sub(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix)$", lambda m: ROMAN[m.group(1)], n)


def plain(name):
    """Search form of a name: trailing (...) removed."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name.replace("<", ",")).strip()


def read_tsv():
    lines = TSV.read_text(encoding="utf-8").split("\n")
    header = lines[0].rstrip("\r").split("\t")
    rows = [l.rstrip("\r").split("\t") for l in lines[1:] if l.strip()]
    if "url" not in header:
        header.append("url")
        for r in rows:
            r.append("")
    return header, rows


def aon_names(html_bytes):
    page = html_bytes.decode("utf-8", "replace")
    names = {urllib.parse.unquote(html.unescape(n))
             for n in re.findall(r'SpellDisplay\.aspx\?ItemName=([^"&]+)', page)}
    by_key = {}
    for n in sorted(names):
        by_key.setdefault(key(n), []).append(n)
    return by_key


def aon_url(row, I, by_key):
    name = row[I["name"]]
    for candidate in (name, row[I["linktext"]]):
        if not candidate or candidate == "NULL":
            continue
        matches = by_key.get(key(candidate), [])
        exact = [m for m in matches if m.lower() == candidate.lower()]
        if exact or len(matches) == 1:
            return AON_SPELL + urllib.parse.quote((exact or matches)[0], safe="")
    return AON_SEARCH + urllib.parse.quote(plain(name), safe="")


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def foundry_row(y, header):
    s = y["system"]
    action = next(iter((s.get("actions") or {}).values()), {})
    learned = (s.get("learnedAt") or {}).get("class") or {}
    row = dict.fromkeys(header, "")

    levels = {}
    for cls, lv in learned.items():
        levels["sorcerer/wizard" if cls in ("sorcerer", "wizard") else cls] = lv

    act = action.get("activation") or {}
    cost = act.get("cost") or 1
    unit = ACTIVATION.get(act.get("type"), act.get("type") or "")
    plural = "s" if cost != 1 and unit in ("round", "minute", "hour") else ""
    casting = f"{cost} {unit}{plural}".strip()

    rng = action.get("range") or {}
    units = rng.get("units")
    if units in ("ft", "mi"):
        rng_text = f"{rng.get('value')} {units}."
    elif units == "spec":
        rng_text = rng.get("value") or ""
    else:
        rng_text = RANGES.get(units, "")

    dur = action.get("duration") or {}
    du = dur.get("units")
    if du == "spec":
        dur_text = dur.get("value") or ""
    elif du in DURATIONS:
        dur_text = DURATIONS[du]
    elif du:
        value = str(dur.get("value") or "1").strip()
        dur_text = f"1 {du}/level" if value.startswith("@cl") else f"{value} {du}{'s' if value != '1' else ''}"
    else:
        dur_text = ""
    if dur.get("dismiss"):
        dur_text += " (D)"

    comp = s.get("components") or {}
    mat = (s.get("materials") or {}).get("value")
    parts = [p for p, on in (("V", comp.get("verbal")), ("S", comp.get("somatic"))) if on]
    if comp.get("material"):
        parts.append(f"M ({mat})" if mat else "M")
    if comp.get("focus"):
        parts.append("F")
    if comp.get("divineFocus"):
        parts.append("DF")

    src = (s.get("sources") or [{}])[0]
    desc = (s.get("description") or {}).get("value", "") or ""
    target = action.get("target")
    wiz = learned.get("wizard", learned.get("sorcerer", ""))
    row.update({
        "name": y["name"],
        "school": SCHOOLS.get(s.get("school"), s.get("school") or ""),
        "subschool": ", ".join(s.get("subschool") or []),
        "descriptor": ", ".join(s.get("descriptors") or []),
        "spell_level": ", ".join(f"{c} {lv}" for c, lv in sorted(levels.items())),
        "casting_time": casting,
        "components": ", ".join(parts),
        "range": rng_text,
        "area": action.get("area") or "",
        "effect": action.get("effect") or "",
        "targets": target.get("value", "") if isinstance(target, dict) else "",
        "duration": dur_text,
        "saving_throw": (action.get("save") or {}).get("description", "") or "",
        "spell_resistence": "yes" if s.get("sr") else "no",
        "wiz": str(wiz),
        "sor": str(learned.get("sorcerer", wiz)),
        "description": strip_html(desc),
        "linktext": y["name"],
        "description_formated": desc,
        "source": f"{src.get('id', '')} p. {src.get('pages', '')}" if src.get("pages") else src.get("id", ""),
        "short_description": (s.get("description") or {}).get("summary", "") or "",
        "id": f"fvtt:{y['_id']}",
    })
    return [re.sub(r"[\t\r\n]+", " ", str(row[h])) for h in header]


def foundry_spells(archive_bytes):
    import yaml  # PyYAML
    spells = []
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.name.endswith(".yaml"):
                continue
            y = yaml.safe_load(tar.extractfile(m))
            if not isinstance(y, dict) or y.get("type") != "spell":
                continue
            learned = (y["system"].get("learnedAt") or {}).get("class") or {}
            if "wizard" in learned or "sorcerer" in learned:
                spells.append(y)
    return spells


def read_spellbook():
    names = []
    for line in SPELLBOOK.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.append(line)
    return names


def check_link(url):
    try:
        body = fetch(url).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as e:
        return False, str(e)
    return "- Spells - Archives of Nethys" in body, "ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--foundry-archive", help="local copy of the Foundry packs/spells .tar.gz")
    ap.add_argument("--aon-html", help="local copy of " + AON_LIST_URL)
    ap.add_argument("--no-foundry", action="store_true", help="do not add spells from Foundry")
    ap.add_argument("--no-aon", action="store_true", help="keep the existing url column (no request to aonprd.com)")
    ap.add_argument("--no-pfsrd", action="store_true",
                    help="keep the existing pfsrd column (no requests to d20pfsrd.com)")
    ap.add_argument("--check-links", action="store_true",
                    help="fetch every spellbook spell link (~1 req/s); failures fall back to search links")
    args = ap.parse_args()

    header, rows = read_tsv()
    I = {h: i for i, h in enumerate(header)}

    if not args.no_foundry:
        archive = Path(args.foundry_archive).read_bytes() if args.foundry_archive else fetch(FOUNDRY_URL)
        rows = [r for r in rows if not r[I["id"]].startswith("fvtt:")]
        known = set()
        for r in rows:
            known.add(key(r[I["name"]]))
            if r[I["linktext"]] not in ("", "NULL"):
                known.add(key(r[I["linktext"]]))
        added = []
        for y in sorted(foundry_spells(archive), key=lambda y: y["name"].lower()):
            if key(y["name"]) not in known:
                known.add(key(y["name"]))
                rows.append(foundry_row(y, header))
                added.append(y["name"])
        print(f"Added {len(added)} spells from Foundry PF1: {', '.join(added) or '-'}")
        rows.sort(key=lambda r: r[I["name"]].lower())

    if not args.no_aon:
        by_key = aon_names(Path(args.aon_html).read_bytes() if args.aon_html else fetch(AON_LIST_URL))
        for r in rows:
            r[I["url"]] = aon_url(r, I, by_key)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if not args.no_pfsrd:
        import pfsrd_links
        pfsrd_links.apply(header, rows, check="book" if args.check_links else "none")
    elif "pfsrd" not in header:
        header.append("pfsrd")
        for r in rows:
            r.append("")

    book = read_spellbook()
    wanted = {n.lower().replace("\u2019", "'"): n for n in book}
    matched = set()
    for r in rows:
        names = {r[I["name"]].lower().replace("\u2019", "'")}
        hit = names & wanted.keys()
        r[I["On my list"]] = "1" if hit else ""
        matched |= hit
    missing = [wanted[k] for k in wanted.keys() - matched]
    marked = sum(r[I["On my list"]] == "1" for r in rows)
    print(f"Spellbook: {len(book)} lines, {marked} rows marked")
    if missing:
        print("Spellbook names not found in spells.tsv: " + ", ".join(sorted(missing)), file=sys.stderr)

    if args.check_links:
        failed = []
        for r in rows:
            if r[I["On my list"]] != "1" or not r[I["url"]].startswith(AON_SPELL):
                continue
            ok, _ = check_link(r[I["url"]])
            if not ok:
                failed.append(r[I["name"]])
                r[I["url"]] = AON_SEARCH + urllib.parse.quote(plain(r[I["name"]]), safe="")
            time.sleep(1)
        search = [r[I["name"]] for r in rows if r[I["On my list"]] == "1" and r[I["url"]].startswith(AON_SEARCH)]
        print(f"Link check: {len(failed)} direct links failed and now use search: {', '.join(failed) or '-'}")
        print(f"Spellbook spells linking to AoN search: {', '.join(search) or '-'}")

    TSV.write_text("\r\n".join("\t".join(r) for r in [header] + rows), encoding="utf-8", newline="")
    print(f"Wrote {len(rows)} spells to {TSV.relative_to(ROOT)}")

    import build_spellbook_json
    json_status = build_spellbook_json.main()
    return 1 if missing or json_status else 0


if __name__ == "__main__":
    sys.exit(main())
