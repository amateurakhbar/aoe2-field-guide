# Age of Empires II — Field Guide

A single, self-contained **`guide.html`** — open it in any browser (offline, no install, no server). It bundles:

- **⚔️ Counter finder** — enter the enemy unit (and optionally *your civilization*) to see exactly what beats it, ranked by bonus damage, with how-to-use tips filtered to your roster.
- **🏛️ Civilizations** — all 76 civs across 3 game modes: bonuses, team bonus, unique units, unique techs (cost + effect), full roster, and community tactical notes.
- **🛡️ Units** — searchable, sortable stats table for every unit (cost, HP, attack, armor, range, speed, bonus-vs, counters).
- **📜 Build orders** — 19 build orders incl. a dedicated **Red Phosphorus Fast Castle** sub-selector (6 follow-ups), plus scouts, archers, MAA, drush, fast imperial and civ-specific builds.
- **📖 Reference** — the community charts (unit response chart + reversed, unique-units table).

## Use it

Just open [`guide.html`](guide.html). Everything (data + chart images) is embedded.

## Coverage

53 AoE2:DE civs · 6 Chronicles: Battle for Greece · 17 Return of Rome (AoE1) = **76 civs**, **376 unit types**.

## Rebuild

```sh
python3 build.py        # process raw game data -> data/*.json (+ readable .md)
python3 make_guide.py   # build self-contained guide.html (inlines data + images)
python3 check.py        # integrity checks
```

## Data sources & credits

- **Unit / civ / tech data + counters:** [aoe2techtree.net](https://aoe2techtree.net) ([SiegeEngineers/aoe2techtree](https://github.com/SiegeEngineers/aoe2techtree)), extracted from the AoE2:DE game files.
- **Build orders:** [AoE Companion](https://aoecompanion.com/build-guides) and its community guides, incl. Red Phosphorus's [Uncounterable Fast Castle](https://aoecompanion.com/b/kxnt2j50mm).
- **Charts:** community infographics from [r/aoe2](https://www.reddit.com/r/aoe2/) (unit response chart, build-order flowchart, unique-units table) by their respective authors.

*Age of Empires II © Microsoft Corporation. This is a non-commercial fan project made under Microsoft's [Game Content Usage Rules](https://www.xbox.com/en-us/developers/rules); not endorsed by or affiliated with Microsoft. All community charts and build orders belong to their original authors.*
