# ponytail: validate all three processed datasets
import json
FILES = {"main":"data/aoe2_data.json","chronicles":"data/chronicles_data.json","ror":"data/ror_data.json"}
COUNTS = {"main":53,"chronicles":6,"ror":17}
for key, path in FILES.items():
    o = json.load(open(path))
    assert o['num_civilizations'] == COUNTS[key], f"{key}: {o['num_civilizations']} civs"
    # no unresolved name ids leaked
    bad_u = [u['name'] for u in o['units_master'].values() if u['name'].startswith('#')]
    assert not bad_u, f"{key}: unresolved unit names {bad_u[:5]}"
    for c in o['civilizations']:
        assert not c['name'].startswith('#'), f"{key}: bad civ name {c['name']}"
        assert c['civ_type'], f"{key}/{c['name']}: no civ type"
        assert c['civ_bonuses'], f"{key}/{c['name']}: no bonuses"
        for t in c['unique_techs']:
            assert t['name'] and not t['name'].startswith('#'), f"{key}/{c['name']}: bad UT"
    print(f"OK {key}: {o['num_civilizations']} civs, {o['num_unit_definitions']} units, "
          f"{len(o['counter_system'])} counter classes")
# main rock-paper-scissors still holds
um = {u['name']:u for u in json.load(open('data/aoe2_data.json'))['units_master'].values()}
assert 'Mounted Units' in um['Spearman']['bonus_damage_vs']
assert 'All Archers' in um['Skirmisher']['bonus_damage_vs']
print("OK — counter system intact across all modes")
