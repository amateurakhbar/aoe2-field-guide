import json, re
from collections import Counter, defaultdict

def load(p): return json.load(open(p))
MAIN_STR = load('data/strings_en.json')

def clean(t): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()
def norm(t):  return re.sub(r'[^a-z0-9]', '', t.lower())

def effect_fields(text):
    vals = [v for v in re.findall(r'[+\-]?\d+(?:/\d+)?%?', text) if any(ch.isdigit() for ch in v)]
    ages = []
    for a in re.findall(r'([A-Z][a-z]+) Age', text):   # generic: Dark/Feudal/Castle/Imperial/Civic/Classical...
        if a not in ages: ages.append(a)
    return {"text": text, "values": vals, "ages": ages}

CLASS = {0:'Wonders',1:'Infantry',2:'Heavy Warships',3:'Base Pierce',4:'Base Melee',
 5:'Elephants',8:'Mounted Units',11:'All Buildings',13:'Stone Defense & Harbors',
 14:'Predator Animals',15:'All Archers',16:'Ships',17:'High-Pierce-Armor Siege',18:'Trees',
 19:'Unique Units',20:'Siege Units',21:'Standard Buildings',22:'Walls & Gates',
 23:'Gunpowder Units',24:'Aggressive Huntables',25:'Monastery Units',26:'Castles & Kreposts',
 27:'Spearmen',28:'Mounted Archers',29:'Shock Infantry',30:'Camels',31:'Unblockable Melee',
 32:'Condottieri',34:'Fishing Ships',35:'Mamelukes',36:'Heroes & Kings',37:'Heavy Siege',
 38:'Skirmishers',39:'Cavalry Resistance',40:'Houses',41:'Fire Ships',60:'Long-Range Warships'}
BASE = {3, 4, 31}

def resolve(S, lid, offs):
    for off in offs:
        v = S.get(str(lid + off))
        if v: return v
    return None
def name_of(S, lid, offs): return clean(resolve(S, lid, offs) or f"#{lid}")

HEADERS = {"unique unit":"unit","unique units":"unit","unique tech":"tech",
           "unique techs":"tech","team bonus":"team"}
def parse_help(raw):
    civ_type, sec = None, "bonus"
    out = {"bonus":[], "unit":[], "tech":[], "team":[]}
    for part in (raw or "").split('<br>'):
        t = clean(part)
        if not t: continue
        key = t.lower().rstrip(':')
        if key in HEADERS: sec = HEADERS[key]; continue
        if civ_type is None: civ_type = t; continue
        out[sec].append(t.lstrip('•').strip())
    return civ_type, out

# ---------- normalize the two on-disk schemas into one intermediate form ----------
def main_schema(path, extra=None):
    d = load(path)
    S = {**MAIN_STR, **(extra or {})}
    civs = {k: {"unit_ids":c['Unit'], "tech_ids":c['Tech'],
                "name_id":c['name_string_id'], "help_id":c['help_string_id']}
            for k, c in d['civs'].items()}
    return dict(civs=civs, units=d['data']['Unit'], techs=d['data']['Tech'], S=S,
                off=dict(unit=(9000,0), tech=(10000,9000,0), name=(0,9000), help=(0,9000)))

def ror_schema(path):
    d = load(path)
    S = {**MAIN_STR, **load('data/ror_strings_en.json')}
    civs = {k: {"unit_ids":[n['id'] for n in c['units']], "tech_ids":[n['id'] for n in c['techs']],
                "name_id":int(d['civ_names'][k]), "help_id":int(d['civ_helptexts'][k])}
            for k, c in d['techtrees'].items()}
    return dict(civs=civs, units=d['data']['units'], techs=d['data']['techs'], S=S,
                off=dict(unit=(0,9000), tech=(0,10000,9000), name=(0,), help=(0,)))

# ---------- the single pipeline ----------
def process(ds, edition, expansion_of):
    S, off = ds['S'], ds['off']
    units_raw, techs_raw, civs_raw = ds['units'], ds['techs'], ds['civs']
    uname = lambda l: name_of(S, l, off['unit'])
    tname = lambda l: name_of(S, l, off['tech'])

    # units + counter graph
    units_master, info = {}, {}
    for uid, u in units_raw.items():
        name = uname(u['LanguageNameId'])
        if name.startswith('#'):  # rare: no name string -> fall back to internal name
            name = re.sub(r'\s*-\s*\w+( Age)?$', '', u.get('internal_name', '')).strip() or name
        classes = sorted({a['Class'] for a in u.get('Armours', []) if a['Class'] not in BASE})
        bonus = {}
        for atk in u.get('Attacks', []):
            if atk['Amount'] > 0 and atk['Class'] not in BASE:
                bonus[atk['Class']] = max(bonus.get(atk['Class'], 0), atk['Amount'])
        units_master[uid] = {"id":int(uid), "name":name, "internal_name":u.get('internal_name'),
            "cost":u.get('Cost', {}), "hp":u.get('HP'), "attack":u.get('Attack'),
            "melee_armor":u.get('MeleeArmor'), "pierce_armor":u.get('PierceArmor'),
            "range":u.get('Range'), "speed":u.get('Speed'), "line_of_sight":u.get('LineOfSight'),
            "train_time":u.get('TrainTime'),
            "armor_classes":[CLASS.get(c, f"class_{c}") for c in classes],
            "bonus_damage_vs":{CLASS.get(c, f"class_{c}"):a for c, a in sorted(bonus.items())}}
        info[uid] = {"name":name, "classes":classes, "bonus":bonus}

    members, dealers = defaultdict(set), defaultdict(dict)
    for i in info.values():
        for c in i['classes']: members[c].add(i['name'])
        for c, a in i['bonus'].items(): dealers[c][i['name']] = max(dealers[c].get(i['name'], 0), a)
    for uid, i in info.items():
        cb = set().union(*[set(dealers.get(c, {})) for c in i['classes']]) if i['classes'] else set()
        cn = set().union(*[members.get(c, set()) for c in i['bonus']]) if i['bonus'] else set()
        units_master[uid]["countered_by"] = sorted(cb - {i['name']})
        units_master[uid]["counters"]     = sorted(cn - {i['name']})
    counter_system = {CLASS.get(c, f"class_{c}"): {"class_id":c,
        "members":sorted(members.get(c, set())),
        "threats":[{"unit":n, "bonus":a} for n, a in sorted(dealers.get(c, {}).items(), key=lambda x:-x[1])]}
        for c in sorted(set(members) | set(dealers))}

    # techs: uniqueness + global name map
    tech_civ_count = Counter(t for c in civs_raw.values() for t in c['tech_ids'])
    TECH_BY_NAME = {}
    for tid, t in techs_raw.items():
        TECH_BY_NAME.setdefault(norm(tname(t.get('LanguageNameId', 0))), (int(tid), t))
    unit_civ_count = Counter(u for c in civs_raw.values() for u in c['unit_ids'])

    civilizations, civ_units = [], {}
    for key in sorted(civs_raw):
        c = civs_raw[key]
        name = name_of(S, c['name_id'], off['name'])
        civ_type, parsed = parse_help(resolve(S, c['help_id'], off['help']) or "")

        cand = {}
        for tid in [t for t in c['tech_ids'] if tech_civ_count[t] == 1]:
            t = techs_raw.get(str(tid), {})
            cand[norm(tname(t.get('LanguageNameId', 0)))] = (tid, t)
        ut = []
        for line in parsed["tech"]:
            nm = re.split(r'\s*\(', line, maxsplit=1)[0].strip()
            m = re.search(r'\((.*)\)\s*$', line)
            hit = cand.get(norm(nm)) or next(((i, t) for cn, (i, t) in cand.items() if cn in norm(line)), None) \
                  or TECH_BY_NAME.get(norm(nm))
            tid, t = hit if hit else (None, {})
            eff = m.group(1) if m else None
            f = effect_fields(eff or "")
            ut.append({"id":tid, "name":nm, "effect":eff, "values":f["values"], "ages":f["ages"],
                       "cost":t.get('Cost', {}), "research_time":t.get('ResearchTime')})

        all_units = sorted({units_master[str(u)]['name'] for u in c['unit_ids'] if str(u) in units_master})
        unique_units = sorted({units_master[str(u)]['name'] for u in c['unit_ids']
                               if str(u) in units_master and unit_civ_count[u] == 1})
        civ_units[name] = {"all_units":all_units, "unique_units":unique_units}
        civilizations.append({"key":key, "name":name, "expansion":expansion_of(key),
            "civ_type":civ_type,
            "civ_bonuses":[effect_fields(b) for b in parsed["bonus"]],
            "team_bonus":effect_fields(" ".join(parsed["team"])) if parsed["team"] else None,
            "unique_unit_text":parsed["unit"], "unique_units":unique_units,
            "unique_techs":ut, "num_units":len(all_units)})

    return {"edition":edition, "num_civilizations":len(civilizations),
            "num_unit_definitions":len(units_master), "civilizations":civilizations,
            "units_master":units_master, "civ_units":civ_units, "counter_system":counter_system,
            "class_labels":{str(k):v for k, v in CLASS.items()}}

# ---------- expansion attribution (main only) ----------
EXP = {}
for grp, names in {
 "The Age of Kings (1999)":["Britons","Byzantines","Celts","Chinese","Franks","Goths","Japanese","Mongols","Persians","Saracens","Teutons","Turks","Vikings"],
 "The Conquerors (2000)":["Aztecs","Huns","Koreans","Mayans","Spanish"],
 "The Forgotten (2013)":["Incas","Italians","Magyars","Slavs"],
 "The African Kingdoms (2015)":["Berbers","Ethiopians","Malians","Portuguese"],
 "Rise of the Rajas (2016)":["Burmese","Khmer","Malay","Vietnamese"],
 "DE / The Last Khans (2019)":["Bulgarians","Cumans","Lithuanians","Tatars"],
 "Lords of the West (2021)":["Burgundians","Sicilians"],
 "Dawn of the Dukes (2021)":["Bohemians","Poles"],
 "Dynasties of India (2022)":["Bengalis","Dravidians","Gurjaras","Hindustanis"],
 "Return of Rome (2023)":["Romans"],
 "The Mountain Royals (2023)":["Armenians","Georgians"],
 "Three Kingdoms (2025)":["Jurchens","Khitans","Shu","Wei","Wu"],
 "American civs (recent)":["Mapuche","Muisca","Tupi"]}.items():
    for n in names: EXP[n] = grp

DATASETS = [
 ("main", "AoE2:DE main game", "data/aoe2_data.json",
  process(main_schema('data/aoe2techtree.json'), "AoE2:DE main game", lambda k: EXP.get(k, "?"))),
 ("chronicles", "Chronicles: Battle for Greece", "data/chronicles_data.json",
  process(main_schema('study/chronicles_data_data.json', load('data/chronicles_strings_en.json')),
          "Chronicles: Battle for Greece", lambda k: "Chronicles: Battle for Greece")),
 ("ror", "Return of Rome (AoE1)", "data/ror_data.json",
  process(ror_schema('study/ror_data_data.json'), "Return of Rome (AoE1)",
          lambda k: "Return of Rome (AoE1)")),
]
for _, _, path, out in DATASETS:
    json.dump(out, open(path, 'w'), indent=2)
    print(f"{out['edition']:32s} civs {out['num_civilizations']:3d} | units {out['num_unit_definitions']:3d} "
          f"| counter classes {len(out['counter_system'])}")

# ================= COMBINED READABLE MARKDOWN (all 3 modes) =================
def money(c): return " ".join(f"{v}{k[0]}" for k, v in c.items()) or "free"
RELEASE = ["The Age of Kings (1999)","The Conquerors (2000)","The Forgotten (2013)",
 "The African Kingdoms (2015)","Rise of the Rajas (2016)","DE / The Last Khans (2019)",
 "Lords of the West (2021)","Dawn of the Dukes (2021)","Dynasties of India (2022)",
 "Return of Rome (2023)","The Mountain Royals (2023)","Three Kingdoms (2025)","American civs (recent)"]

civA = ["# Age of Empires II — All Civilizations (3 game modes)\n"]
bonA = ["# Age of Empires II — Civ Bonuses, Team Bonuses & Unique Techs (all modes)\n"]
cntA = ["# Age of Empires II — Counter Universe (all modes)\n",
        "Derived from the armor/attack class system; base melee/pierce excluded.\n"]
rosA = ["# Age of Empires II — Unit Rosters by Civ (all modes). **Bold** = civ-unique.\n"]

for label, edition, _, out in DATASETS:
    civs = out['civilizations']
    civA.append(f"\n# {edition}  ({len(civs)} civs)\n")
    groups = RELEASE if label == "main" else [edition]
    byexp = defaultdict(list)
    for c in civs: byexp[c['expansion']].append(c)
    for g in groups:
        rows = sorted(byexp.get(g, []), key=lambda x: x['name'])
        if not rows: continue
        civA.append(f"\n## {g}\n\n| Civ | Type | Unique unit | Unique techs |\n|---|---|---|---|")
        for c in rows:
            uu = ", ".join(c['unique_unit_text']) or "—"
            uts = ", ".join(t['name'] for t in c['unique_techs']) or "—"
            civA.append(f"| {c['name']} | {c.get('civ_type') or ''} | {uu} | {uts} |")

    bonA.append(f"\n# {edition}\n")
    for c in sorted(civs, key=lambda x: x['name']):
        bonA.append(f"\n## {c['name']} — *{c.get('civ_type') or ''}*\n")
        bonA.append("**Civ bonuses:**")
        bonA += [f"- {b['text']}" for b in c['civ_bonuses']] or ["- (none)"]
        bonA.append(f"\n**Unique unit:** {', '.join(c['unique_unit_text']) or '—'}")
        if c['unique_techs']:
            bonA.append("\n**Unique techs:**")
            for t in c['unique_techs']:
                eff = f" — {t['effect']}" if t['effect'] else ""
                bonA.append(f"- **{t['name']}** ({money(t['cost'])}, {t['research_time']}s){eff}")
        bonA.append(f"\n**Team bonus:** {c['team_bonus']['text'] if c['team_bonus'] else '—'}")

    cntA.append(f"\n# {edition}\n")
    for cn, blk in sorted(out['counter_system'].items(), key=lambda x: x[1]['class_id']):
        if not blk['threats']: continue
        cntA.append(f"\n## vs {cn}  *(class {blk['class_id']})*\n")
        cntA.append("**Countered by:** " + ", ".join(f"{t['unit']} (+{t['bonus']})" for t in blk['threats']))
        if blk['members']:
            cntA.append(f"\n**Members ({len(blk['members'])}):** " + ", ".join(blk['members']))

    rosA.append(f"\n# {edition}\n")
    for c in sorted(civs, key=lambda x: x['name']):
        uniq = set(out['civ_units'][c['name']]['unique_units'])
        items = [f"**{u}**" if u in uniq else u for u in out['civ_units'][c['name']]['all_units']]
        rosA.append(f"\n## {c['name']}\n")
        rosA.append(", ".join(items))

open('ALL_CIVILIZATIONS.md','w').write("\n".join(civA) + "\n")
open('CIV_BONUSES.md','w').write("\n".join(bonA) + "\n")
open('COUNTERS.md','w').write("\n".join(cntA) + "\n")
open('UNITS_BY_CIV.md','w').write("\n".join(rosA) + "\n")
total = sum(o['num_civilizations'] for *_, o in DATASETS)
print(f"TOTAL {total} civs across {len(DATASETS)} modes")
print("wrote ALL_CIVILIZATIONS.md, CIV_BONUSES.md, COUNTERS.md, UNITS_BY_CIV.md + 3 json files")
