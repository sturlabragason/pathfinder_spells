#!/usr/bin/env python3
"""Write caladrel_ecthelion/spellbook.json from spells.tsv and spellbook.txt.

The JSON holds every spell in Caladrel's spellbook with the fields needed at the
table (level, school, casting, range, duration, save, rules text, AoN link). The
character sheet at caladrel.sturlabragason.online and caladrel_ecthelion/index.html
both read it. update_spells.py runs this at the end; run it alone after editing
spellbook.txt.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "spells.tsv"
SPELLBOOK = ROOT / "caladrel_ecthelion" / "spellbook.txt"
OUT = ROOT / "caladrel_ecthelion" / "spellbook.json"

CHARACTER = {
    "name": "Caladrel Ecthëlion",
    "class": "Wizard 7",
    "school": "conjuration",
    "subschool": "teleportation",
    "opposed": ["enchantment", "divination"],
    "caster_level": 7,
    "int_mod": 6,
    # wizard 7 base 4/4/3/2/1 + Int 22 bonus -/2/2/1/1 + school slot 1st-4th
    "slots": {"0": 4, "1": 7, "2": 6, "3": 4, "4": 3},
}

FIELDS = {
    "school": "school", "subschool": "subschool", "descriptor": "descriptor",
    "casting_time": "casting_time", "components": "components", "range": "range",
    "area": "area", "effect": "effect", "targets": "targets", "duration": "duration",
    "save": "saving_throw", "sr": "spell_resistence", "short": "short_description",
    "source": "source", "url": "url",
}
UNSAFE = re.compile(r"<\s*(script|style|iframe)[^>]*>.*?<\s*/\s*\1\s*>|\son\w+\s*=\s*\"[^\"]*\"", re.I | re.S)


def norm(name):
    return re.sub(r"\s*\(not in spellbook\)\s*$", "", name.lower().replace("\u2019", "'")).strip()


def read_spellbook():
    out = []
    for line in SPELLBOOK.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def clean(v):
    v = (v or "").strip()
    return "" if v in ("NULL", "-") else v


def main():
    csv.field_size_limit(sys.maxsize)
    with TSV.open(encoding="utf-8", newline="") as f:
        rows = {norm(r["name"]): r for r in csv.DictReader(f, delimiter="\t")}
    spells, missing = [], []
    for line in read_spellbook():
        r = rows.get(norm(line))
        if r is None:
            missing.append(line)
            continue
        level = clean(r.get("wiz")) or clean(r.get("sor"))
        s = {"name": re.sub(r"\s*\(Not in Spellbook\)\s*$", "", r["name"]).strip(),
             "level": int(level) if level.isdigit() else None}
        for k, col in FIELDS.items():
            s[k] = clean(r.get(col))
        s["school"] = s["school"].lower()
        text = clean(r.get("description_formated")) or "".join(
            f"<p>{p}</p>" for p in re.split(r"\s{2,}", clean(r.get("description"))) if p)
        s["text"] = UNSAFE.sub("", text)
        s["opposed"] = s["school"] in CHARACTER["opposed"]
        s["in_book"] = "not in spellbook" not in line.lower()
        spells.append(s)
    spells.sort(key=lambda s: (s["level"] if s["level"] is not None else 99, s["name"].lower()))
    data = {"character": CHARACTER, "count": len(spells), "spells": spells}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(spells)} spells")
    if missing:
        print("Not found in spells.tsv: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
