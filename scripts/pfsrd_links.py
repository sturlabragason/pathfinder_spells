#!/usr/bin/env python3
"""Set the "pfsrd" column of spells.tsv: a verified d20pfsrd.com link per spell.

No URL is built from a spell name. Every link is either a page listed in the
d20pfsrd WordPress sitemap (https://www.d20pfsrd.com/sitemap.xml) or a page
from it that was fetched and confirmed:

1. The sitemap is downloaded (index plus wp-sitemap-posts-page-N.xml) and
   cached in scripts/.cache/d20pfsrd/ (refreshed after --max-age days).
   Spell pages are the ones under /magic/all-spells/; Paizo mythic spells
   (/alternative-rule-systems/.../mythic-spells/) come next, and pages under
   /magic/3rd-party-spells/ are used only when neither has the spell.
2. A spell whose normalised name (case, accents, apostrophes, punctuation,
   "X, Mass" -> "Mass X" / "X Mass", trailing roman numeral -> digit,
   trailing "(...)") equals the normalised slug of exactly one core page
   gets that page.
3. Otherwise candidate pages are fetched and the spell is accepted only when
   the page answers HTTP 200 and its <h1> has the same words as the spell
   name, or (for variants such as "Cure Light Wounds, Mass" or "Summon
   Monster III", which d20pfsrd keeps on the base spell's page) a heading on
   the page does. When that heading has an id, the link points at it
   (#cure_light_wounds_mass).
4. Spells with no confirmed page get an empty "pfsrd" cell; the pages then
   fall back to the Archives of Nethys link in the "url" column.

Fetched pages are cached in scripts/.cache/d20pfsrd/pages.json, so reruns
only fetch what is new. Requests are sequential with a delay.

    python3 scripts/pfsrd_links.py                 # update spells.tsv
    python3 scripts/pfsrd_links.py --check-book    # also fetch every link in Caladrel's spellbook
    python3 scripts/pfsrd_links.py --check-all     # fetch every link (slow, ~1 request/s, cached)

update_spells.py calls this unless it is given --no-pfsrd.
"""
import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "spells.tsv"
SPELLBOOK = ROOT / "caladrel_ecthelion" / "spellbook.txt"
CACHE = Path(__file__).resolve().parent / ".cache" / "d20pfsrd"
PAGES = CACHE / "pages.json"
SITE = "https://www.d20pfsrd.com/"
SITEMAP_INDEX = SITE + "sitemap.xml"
CORE = SITE + "magic/all-spells/"
THIRD = SITE + "magic/3rd-party-spells/"
MYTHIC = SITE + "alternative-rule-systems/paizo-rules-systems/mythic/mythic-magic/mythic-spells/"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"
DELAY = 1.0

ALIASES = {
    "adjuring step": "abjuring step",
    "liberating comand": "liberating command",
    "suppres charms and compulsions": "suppress charms and compulsions",
    # d20pfsrd drops the Golarion name; checked by hand that the page is the same spell
    "serren's swift girding": "swift girding",
    "serren's armor lock": "armor lock",
}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
MODIFIERS = {"mass", "greater", "lesser", "communal", "major", "minor", "supreme", "improved", "giant"}

_last_request = [0.0]


def _get(url):
    """GET url politely. Returns (status, final_url, body)."""
    wait = DELAY - (time.monotonic() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, final, body = r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        status, final, body = e.code, e.geturl() or url, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        status, final, body = 0, url, str(e).encode()
    _last_request[0] = time.monotonic()
    return status, final, body


# ---------------------------------------------------------------- sitemap

def sitemap_locs(max_age_days=30, refresh=False):
    """All <loc> URLs of the d20pfsrd page sitemaps (cached)."""
    CACHE.mkdir(parents=True, exist_ok=True)

    def cached(name, url):
        path = CACHE / name
        fresh = path.exists() and time.time() - path.stat().st_mtime < max_age_days * 86400
        if refresh or not fresh:
            # d20pfsrd answers some sitemap files with status 404 but a complete urlset body.
            _, _, body = _get(url)
            if b"<urlset" not in body and b"<sitemapindex" not in body:
                if path.exists():
                    print(f"pfsrd: {url} did not return a sitemap, keeping the cached copy", file=sys.stderr)
                    return path.read_text(encoding="utf-8")
                raise RuntimeError(f"{url} did not return a sitemap")
            path.write_bytes(body)
        return path.read_text(encoding="utf-8")

    index = cached("sitemap.xml", SITEMAP_INDEX)
    locs = []
    for sm in re.findall(r"<loc>([^<]+)</loc>", index):
        sm = html.unescape(sm)
        if "/wp-sitemap-posts-page-" in sm:
            locs += [html.unescape(l) for l in re.findall(r"<loc>([^<]+)</loc>", cached(sm.rsplit("/", 1)[1], sm))]
    return locs


# ---------------------------------------------------------------- names

def fold(s):
    s = unicodedata.normalize("NFKD", s.replace("\u2019", "'").replace("\u2018", "'"))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def words(s):
    """Words of a name: folded, apostrophes dropped, trailing roman numeral as a digit."""
    w = re.findall(r"[a-z0-9]+", fold(s).replace("'", ""))
    if len(w) > 1 and w[-1] in ROMAN:
        w[-1] = ROMAN[w[-1]]
    return w


def key(s):
    return "".join(words(s))


def bag(s):
    return " ".join(sorted(words(s)))


def slug_words(url):
    return url.rstrip("/").rsplit("/", 1)[1].split("-")


def name_forms(*names):
    """Spellings to try for a spell: as given, without trailing (...), comma parts reordered."""
    forms = []
    for n in names:
        if not n or n == "NULL":
            continue
        n = fold(n).replace("<", ",")
        n = ALIASES.get(re.sub(r"\s+", " ", n).strip(), n)
        for f in (n, re.sub(r"\s*\([^)]*\)\s*$", "", n)):
            forms.append(f)
            if "," in f:
                head, tail = f.split(",", 1)
                forms += [f"{tail} {head}", f"{head} {tail}"]
    return list(dict.fromkeys(forms))


# ---------------------------------------------------------------- pages

def load_pages():
    return json.loads(PAGES.read_text(encoding="utf-8")) if PAGES.exists() else {}


def save_pages(pages):
    CACHE.mkdir(parents=True, exist_ok=True)
    PAGES.write_text(json.dumps(pages, indent=0, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def page_info(url, pages, refetch=False):
    """Status, title, h1 and content headings (text + id) of a d20pfsrd page, cached."""
    if url in pages and not refetch:
        return pages[url]
    status, final, body = _get(url)
    page = body.decode("utf-8", "replace")
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    heads = []
    for m in re.finditer(r"<h([2-6])(?![^>]*widget-title)[^>]*>(.*?)</h\1>", page, re.S):
        ident = re.search(r'\sid="([^"]+)"', m.group(2))
        heads.append([text_of(m.group(2)), ident.group(1) if ident else ""])
    info = {"status": status, "final": final, "title": text_of(title.group(1)) if title else "",
            "h1": text_of(h1.group(1)) if h1 else "", "heads": heads, "checked": time.strftime("%Y-%m-%d")}
    pages[url] = info
    return info


def ok(info, url):
    return info["status"] == 200 and info["final"].rstrip("/") == url.rstrip("/")


def confirm(url, forms, pages):
    """The link for one of forms on page url, or None. Checks the <h1>, then the headings."""
    info = page_info(url, pages)
    if not ok(info, url):
        return None
    bags = {bag(f) for f in forms}
    h1 = info["h1"]
    # "Carve Passage (Kobold)": d20pfsrd adds the race of race-specific spells to the title
    if bag(h1) in bags or bag(re.sub(r"\s*\([^)]*\)\s*$", "", h1)) in bags:
        return url
    for text, ident in info["heads"]:
        if bag(text) in bags:
            return url + "#" + ident if ident else url
    return None


# ---------------------------------------------------------------- matching

class Tier:
    """Spell pages under one path of the sitemap, by slug (key) and by slug words in any order (bag)."""
    def __init__(self, prefix, trusted):
        self.prefix, self.trusted = prefix, trusted
        self.by_key, self.by_bag, self.by_first = {}, {}, {}

    def add(self, u):
        name = " ".join(slug_words(u))
        self.by_key.setdefault(key(name), []).append(u)
        self.by_bag.setdefault(bag(name), []).append(u)
        self.by_first.setdefault(key(name)[:3], []).append(u)

    def starting_with(self, name, limit=4):
        """Pages whose slug starts with the words of name (whole words), shortest first."""
        k = key(name)
        out = []
        for u in self.by_first.get(k[:3], []):
            acc = ""
            for x in slug_words(u):
                acc += key(x)
                if acc == k:
                    out.append(u)
                if len(acc) >= len(k):
                    break
        return sorted(out, key=len)[:limit]


class Index:
    def __init__(self, locs):
        # Paizo spells first; the sitemap alone vouches only for a unique slug match under /magic/all-spells/.
        self.tiers = [Tier(CORE, True), Tier(MYTHIC, False), Tier(THIRD, False)]
        self.urls = set()
        for u in locs:
            tier = next((t for t in self.tiers if u.startswith(t.prefix)), None)
            if tier is None or u == tier.prefix:
                continue
            if re.fullmatch(r"[a-z]|spells-[a-z]-[a-z]", "-".join(slug_words(u))):
                continue  # index pages such as /magic/all-spells/a/
            self.urls.add(u)
            tier.add(u)


def base_forms(forms):
    """Forms with a variant word (mass, greater, ..., trailing number) removed: the base spell's name."""
    out = []
    for f in forms:
        w = words(f)
        if w and w[-1].isdigit():
            out.append(" ".join(w[:-1]))
        stripped = [x for x in w if x not in MODIFIERS]
        if stripped and stripped != w:
            out.append(" ".join(stripped))
    return [f for f in dict.fromkeys(out) if f]


def find(forms, idx, pages):
    """(verified d20pfsrd link, how) for a spell, or ("", "no page")."""
    for t in idx.tiers:
        # 1. slug equals the name. A single core page with that slug is taken from the sitemap as is;
        #    several pages, or a page elsewhere, must be confirmed by fetching it.
        hits = list(dict.fromkeys(u for f in forms for u in t.by_key.get(key(f), [])))
        if t.trusted and len(hits) == 1:
            return hits[0], "slug"
        for u in hits:
            link = confirm(u, forms, pages)
            if link:
                return link, "slug+h1"
        # 2. same words in another order: confirm by h1
        for u in dict.fromkeys(u for f in forms for u in t.by_bag.get(bag(f), [])):
            link = confirm(u, forms, pages)
            if link:
                return link, "words+h1"
        # 2b. slug is the name plus a suffix (carve-passage-kobold): confirm by h1
        for f in forms:
            for u in t.starting_with(f):
                if u in hits:
                    continue
                link = confirm(u, [f], pages)
                if link == u:
                    return link, "prefix+h1"
        # 3. a variant (Mass X, X II, Lesser X) kept on the page of the base spell or of its first
        #    version: confirm by a heading on that page. Version 1 is the page's own h1 ("Elemental Body").
        for b in base_forms(forms):
            cands = list(dict.fromkeys(t.by_key.get(key(b), []) + t.by_key.get(key(b + " 1"), []) +
                                       t.starting_with(b)))
            first = [f for f in forms if words(f)[-1:] == ["1"]]
            for u in cands:
                link = confirm(u, forms, pages)
                if link:
                    return link, "base+heading"
                if first and confirm(u, [b], pages) == u and not any(
                        bag(h) == bag(b + " 1") for h, _ in pages[u]["heads"]):
                    return u, "base+h1 (version 1)"
    return "", "no page"


def read_book():
    names = set()
    for line in SPELLBOOK.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(re.sub(r"\s*\(not in spellbook\)\s*$", "", fold(line)).strip())
    return names


def aon_name(url):
    m = re.search(r"ItemName=([^&]+)", url or "")
    return urllib.parse.unquote(m.group(1)) if m else ""


def apply(header, rows, max_age_days=30, refresh=False, check="none", quiet=False):
    """Fill the "pfsrd" column of rows in place. check: none | book | all (fetch every emitted link)."""
    if "pfsrd" not in header:
        header.append("pfsrd")
        for r in rows:
            r.append("")
    I = {h: i for i, h in enumerate(header)}
    idx = Index(sitemap_locs(max_age_days, refresh))
    pages = load_pages()
    book = read_book()
    stats, missing = {}, []
    try:
        for r in rows:
            name = r[I["name"]]
            forms = name_forms(re.sub(r"\s*\(not in spellbook\)\s*$", "", name, flags=re.I),
                               r[I["linktext"]] if "linktext" in I else "",
                               aon_name(r[I["url"]]) if "url" in I else "")
            link, how = find(forms, idx, pages)
            in_book = re.sub(r"\s*\(not in spellbook\)\s*$", "", fold(name)).strip() in book
            if link and (check == "all" or (check == "book" and in_book)):
                # fetch the page (again, if the cached copy is older than max_age_days) and
                # require HTTP 200 plus the spell name as its h1 or as the linked heading
                base = link.split("#", 1)[0]
                checked = pages.get(base, {}).get("checked", "")
                stale = checked < time.strftime("%Y-%m-%d", time.localtime(time.time() - max_age_days * 86400))
                page_info(base, pages, refetch=stale)
                if how == "base+h1 (version 1)":
                    good = ok(pages[base], base)
                else:
                    good = confirm(base, forms, pages) == link
                if not good:
                    link, how = "", "page check failed"
            assert not link or link.split("#", 1)[0] in idx.urls, link
            r[I["pfsrd"]] = link
            stats[how] = stats.get(how, 0) + 1
            if not link:
                missing.append(name)
    finally:
        save_pages(pages)
    linked = sum(1 for r in rows if r[I["pfsrd"]])
    if not quiet:
        print(f"d20pfsrd: {linked}/{len(rows)} spells linked "
              f"({', '.join(f'{k} {v}' for k, v in sorted(stats.items()))})")
        print("d20pfsrd: no verified page (pages use the AoN link): " + (", ".join(missing) or "-"))
    return missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="download the sitemaps again even if cached")
    ap.add_argument("--max-age", type=float, default=30, help="days before cached sitemaps are refreshed (default 30)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check-book", action="store_true", help="fetch the link of every spellbook spell (cached)")
    g.add_argument("--check-all", action="store_true", help="fetch every link (cached; ~1 request/s when not)")
    args = ap.parse_args()

    text = TSV.read_text(encoding="utf-8")
    lines = text.split("\n")
    header = lines[0].rstrip("\r").split("\t")
    rows = [l.rstrip("\r").split("\t") for l in lines[1:] if l.strip()]
    apply(header, rows, args.max_age, args.refresh,
          "all" if args.check_all else "book" if args.check_book else "none")
    TSV.write_text("\r\n".join("\t".join(r) for r in [header] + rows), encoding="utf-8", newline="")
    print(f"Wrote {len(rows)} spells to {TSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
