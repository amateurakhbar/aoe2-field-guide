"""Build a single self-contained guide.html from the processed datasets.
Data AND chart images are embedded (no fetch, no assets folder) so the one file
works by double-click, offline."""
import json, base64

GOATCOUNTER = "https://maisarah.goatcounter.com/count"  # analytics endpoint

MODES = [("main", "AoE2: Definitive Edition", "data/aoe2_data.json"),
         ("chronicles", "Chronicles: Battle for Greece", "data/chronicles_data.json"),
         ("ror", "Return of Rome (AoE1)", "data/ror_data.json")]

def best_counters(unit, cs, by_name, cap=24):
    # effective counters: bonus that actually lands (minus target's armor in that class),
    # and flag counters the target outranges (they get kited). Addresses r/aoe2 feedback.
    tarmor = unit.get('armor_values', {})
    trange = unit.get('range') or 0
    agg = {}
    for cls in unit['armor_classes']:
        for t in cs.get(cls, {}).get('threats', []):
            if t['unit'] == unit['name']:
                continue
            eff = t['bonus'] - tarmor.get(cls, 0)          # armor negates bonus (e.g. Cataphract vs camel)
            if eff <= 0:
                continue
            cu = by_name.get(t['unit'], {})
            e = agg.get(t['unit'])
            if not e:
                e = agg[t['unit']] = {"unit": t['unit'], "bonus": 0, "vias": [],
                                      "outranged": trange > 0 and (cu.get('range') or 0) < trange}
            e["bonus"] += eff          # bonus from different armor classes STACKS (e.g. Halb vs Battle Elephant = cav + elephant)
            e["vias"].append(cls)
    return sorted(agg.values(), key=lambda x: (x['outranged'], -x['bonus']))[:cap]

UNIT_KEYS = ['name', 'cost', 'hp', 'attack', 'melee_armor', 'pierce_armor',
             'range', 'speed', 'armor_classes', 'bonus_damage_vs']
# base AoE2:DE villager gather rates (res/sec, no upgrades; food = farms)
GATHER = {'Food': 0.3166, 'Wood': 0.39, 'Gold': 0.38, 'Stone': 0.36}

def vils_per_building(cost, train_time):
    # villagers to continuously produce a unit from ONE building (idea: Survivalist's aoe2-de-tools)
    if not train_time or not cost:
        return None
    parts = {r: round((c / train_time) / GATHER[r], 1)
             for r, c in cost.items() if r in GATHER and c}
    return {"parts": parts, "total": round(sum(parts.values()), 1)} if parts else None

strategy = json.load(open('data/strategy.json'))
meta = json.load(open('data/meta.json'))['civs']
data = {"modes": {}, "build_orders": strategy['build_orders'],
        "build_catalog": json.load(open('data/build_orders.json'))}
for key, label, path in MODES:
    o = json.load(open(path))
    for civ in o['civilizations']:                       # attach community notes + meta by civ name
        civ['tactics'] = strategy['unit_notes'].get(civ['name'], [])
        civ['meta'] = meta.get(civ['name'])
    cs = o['counter_system']
    by_name = {u['name']: u for u in o['units_master'].values()}
    seen, units = set(), []
    for u in o['units_master'].values():
        if u['name'] in seen:
            continue                                  # collapse base/elite dupes by name
        seen.add(u['name'])
        row = {k: u[k] for k in UNIT_KEYS}
        row['best_counters'] = best_counters(u, cs, by_name)
        row['combat'] = bool((u.get('attack') or 0) > 0 or u['bonus_damage_vs'])
        row['vbld'] = vils_per_building(row['cost'], u.get('train_time'))
        units.append(row)
    units.sort(key=lambda x: x['name'])
    SHORT = {"main": "AoE2: DE", "chronicles": "Chronicles", "ror": "Return of Rome"}
    data['modes'][key] = {"label": label, "short": SHORT.get(key, label),
                          "civilizations": o['civilizations'],
                          "civ_units": o['civ_units'], "units": units}

blob = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')

HTML = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Age of Empires II — Field Guide</title>
<style>
:root{--bg:#1c1813;--panel:#262019;--panel2:#2f2820;--ink:#ece3d2;--mut:#a99c84;
--line:#473b2c;--gold:#d9a441;--red:#cf5b4e;--grn:#7fa650;--blu:#6f9fc4;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
h1,h2,h3{font-family:Georgia,'Times New Roman',serif;font-weight:600;margin:0}
a{color:var(--gold)}
header{padding:14px 18px;border-bottom:2px solid var(--line);background:linear-gradient(#2c2419,#221c14);
position:sticky;top:0;z-index:5}
header h1{font-size:20px;letter-spacing:.3px}
header .sub{color:var(--mut);font-size:12px;margin-top:2px}
.wrap{max-width:1100px;margin:0 auto;padding:0 16px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.modes{margin-top:10px;flex-wrap:nowrap;gap:6px}
.modes button,.tabs button{background:var(--panel);color:var(--ink);border:1px solid var(--line);
padding:7px 13px;border-radius:7px;cursor:pointer;font-size:13px}
.modes button{padding:5px 9px;font-size:12px;white-space:nowrap;flex:0 1 auto}
.modes button.on{background:var(--gold);color:#241c10;border-color:var(--gold);font-weight:600}
@media(max-width:420px){.modes button{padding:5px 7px;font-size:11px}}
.tabs{margin:14px 0;gap:6px}
.tabs button{font-size:14px;padding:9px 16px}
.tabs button.on{background:var(--panel2);border-color:var(--gold);color:var(--gold);font-weight:600}
input,select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
border-radius:7px;padding:9px 11px;font-size:14px;width:100%}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:14px}
.muted{color:var(--mut)}.small{font-size:12px}
.chip{display:inline-flex;align-items:center;gap:5px;background:var(--panel2);border:1px solid var(--line);
border-radius:999px;padding:4px 10px;font-size:13px;margin:3px 4px 3px 0}
.chip b{color:var(--gold)}
.chip.cnt b{color:var(--red)}.chip.str b{color:var(--grn)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid3{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px}
@media(max-width:720px){.grid2{grid-template-columns:1fr}}
.civcard{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px 12px;cursor:pointer}
.civcard:hover{border-color:var(--gold)}
.civcard .t{font-size:12px;color:var(--mut)}
.kv{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}
.stat{background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:5px 9px;font-size:12px}
.stat b{color:var(--gold);font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}
th{color:var(--mut);cursor:pointer;user-select:none;position:sticky;top:0;background:var(--panel)}
th:hover{color:var(--gold)}
tr.u:hover{background:var(--panel2)}tr.u{cursor:pointer}
tr.det td{background:#1f1a13;font-size:12.5px}
.tag{font-size:11px;color:var(--mut);border:1px solid var(--line);border-radius:4px;padding:1px 6px;margin-right:4px}
.uniq{color:var(--gold)}
.hint{color:var(--mut);font-size:13px}
.bigsearch{font-size:16px;padding:12px 14px}
.sec-h{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.6px;margin:0 0 6px}
ul.b{margin:6px 0;padding-left:18px}ul.b li{margin:3px 0}
</style></head><body>
<header><div class="wrap">
  <h1>⚔️ Age of Empires II Field Guide</h1>
  <div class="row modes" id="modes"></div>
</div></header>
<div class="wrap">
  <div class="row tabs" id="tabs"></div>
  <div id="view"></div>
  <p class="small muted" style="margin:24px 0 6px">Counters are derived from the in-game armor/attack class system
  (bonus damage). They show the objective matchup skeleton, not cost-efficiency or micro.</p>
  <p class="small muted" style="margin:0 0 24px">Data from aoe2techtree.net (units, civs, tech), AoE Companion (build orders),
  and the r/aoe2 community. Age of Empires II is a trademark of Microsoft. Fan project, not affiliated with Microsoft.</p>
</div>
<script>
const DATA = __DATA__;
const RES=['Food','Wood','Gold','Stone'];
let S={mode:'main',tab:'counters',civ:null,enemy:'',sort:'name',dir:1,uq:'',cq:''};
const $=s=>document.querySelector(s), elv=()=>$('#view');
const money=c=>RES.filter(r=>c[r]).map(r=>`${c[r]} ${r.toLowerCase()}`).join(', ')||'free';
const M=()=>DATA.modes[S.mode];
const esc=s=>(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));

function track(name){try{if(window.goatcounter&&window.goatcounter.count)window.goatcounter.count({path:name,title:name,event:true});}catch(e){}}
function modesBar(){
  $('#modes').innerHTML=Object.entries(DATA.modes).map(([k,m])=>
    `<button class="${k==S.mode?'on':''}" data-m="${k}" title="${m.label}">${m.short}</button>`).join('');
  $('#modes').querySelectorAll('button').forEach(b=>b.onclick=()=>{
    S.mode=b.dataset.m;S.civ=null;S.enemy='';track('mode/'+b.dataset.m);render();});
}
function tabsBar(){
  const T=[['counters','⚔️ Counter finder'],['civs','🏛️ Civilizations'],['units','🛡️ Units'],
    ['builds','📜 Build orders'],['ref','📖 Reference']];
  $('#tabs').innerHTML=T.map(([k,l])=>`<button class="${k==S.tab?'on':''}" data-t="${k}">${l}</button>`).join('');
  $('#tabs').querySelectorAll('button').forEach(b=>b.onclick=()=>{S.tab=b.dataset.t;track('tab/'+b.dataset.t);render();});
}

/* ---------- COUNTERS ---------- */
function tip(uo){
  const C=uo.armor_classes||[], has=x=>C.includes(x);
  if(has('Spearmen')) return 'Anti-cavalry: hold position and surround; don\'t chase faster units.';
  if(has('Skirmishers')) return 'Cheap anti-archer trash: mass them and keep them ahead of your gold units.';
  if(has('Camels')) return 'Fast anti-cavalry: raid and encircle; pull back from massed archers.';
  if(has('Monastery Units')) return 'Convert key targets and heal; keep behind your main army.';
  if(has('Mounted Archers')||has('All Archers')) return 'Kite: fire and retreat, focus-fire, micro vs skirmishers.';
  if(has('Mounted Units')) return 'Hit-and-run: dive siege/archers, retreat from spearmen.';
  if(has('Siege Units')) return 'Area damage vs clumps and buildings; screen it from raids.';
  if(has('Gunpowder Units')) return 'High burst damage: keep it back, micro, watch for skirmishers.';
  if(has('Infantry')) return 'Cheap and tanky: engage in numbers, strong vs buildings.';
  return 'Mass cost-effectively and engage on your terms.';
}
function ctrChip(c){return `<span class="chip cnt" title="effective bonus vs ${esc(c.vias.join(', '))}${c.outranged?', but the enemy outranges it':''}">${esc(c.unit)} <b>+${c.bonus}</b>${c.outranged?' ⚠':''}</span>`;}
function softCounters(u){
  const C=u.armor_classes||[], has=x=>C.includes(x), out=[];
  if(has('Mounted Units')) out.push(['Halberdier line','cheap, tanky anti-cavalry'],['Monks','convert and heal'],['Camels','faster anti-cavalry if your civ has them']);
  if(has('Camels')||has('Mamelukes')) out.push(['Archers / Crossbows','camels and mamelukes have low pierce armor'],['Monks','convert the expensive gold units']);
  if(has('Elephants')) out.push(['Halberdier line','huge bonus vs elephants'],['Monks','convert them, they cost a lot'],['Light cav / Hussar','surround and dodge the splash']);
  if(has('All Archers')) out.push(['Skirmisher line','cost-effective vs foot archers'],['Knights / cavalry','close the distance and run them down'],['Mangonel / Onager','area damage vs massed archers']);
  if(has('Mounted Archers')) out.push(['Skirmisher line','cheap; Imperial Skirmisher even outranges'],['Knights / light cav','chase them off']);
  if(has('Skirmishers')) out.push(['Knights / cavalry','skirmishers fold in melee'],['Mangonel / Scorpion','area damage']);
  if(has('Gunpowder Units')) out.push(['Skirmisher line','gunpowder units have low pierce armor'],['Knights / cavalry','close the gap fast']);
  if(has('Infantry')&&!has('Mounted Units')) out.push(['Archers / Crossbows','kite slow infantry'],['Scorpions / Mangonel','area damage vs clumps']);
  if(has('Siege Units')) out.push(['Knights / light cav','dive and snipe the siege'],['Spread your army','avoid Mangonel / Onager splash']);
  if(has('Monastery Units')) out.push(['Light cav / Scouts','kill monks before they convert']);
  const seen=new Set(); return out.filter(([n])=>!seen.has(n)&&seen.add(n));
}
function viewCounters(){
  const units=M().units, names=units.map(u=>u.name).sort();
  const civNames=M().civilizations.map(c=>c.name).sort();
  const umap=Object.fromEntries(units.map(u=>[u.name,u]));
  let h=`<div class="panel"><h2>What are you facing?</h2>
    <p class="hint">Enter the enemy unit; add your civ to filter to what you can build. Counters use <b>effective damage</b> (after the target's armor) and flag units the enemy <b>outranges</b> (⚠).</p>
    <div class="grid2">
      <div><div class="sec-h">Enemy unit</div>
        <input class="bigsearch" id="enemy" list="unames" autocomplete="off" placeholder="e.g. Knight, Mameluke, Cataphract…" value="${esc(S.enemy)}">
        <datalist id="unames">${names.map(n=>`<option value="${esc(n)}">`).join('')}</datalist>
        <div id="suggest" class="kv" style="margin-top:6px"></div></div>
      <div><div class="sec-h">Your civilization (optional)</div>
        <input class="bigsearch" id="myciv" list="cnames" autocomplete="off" placeholder="e.g. Franks — filters to your roster" value="${esc(S.myciv||'')}">
        <datalist id="cnames">${civNames.map(n=>`<option value="${esc(n)}">`).join('')}</datalist></div>
    </div></div>`;
  const u=units.find(x=>x.name.toLowerCase()===S.enemy.toLowerCase());
  if(u){
    const stats=[['Cost',money(u.cost)],['HP',u.hp],['Attack',u.attack],
      ['Melee armor',u.melee_armor],['Pierce armor',u.pierce_armor],['Range',u.range||'—'],['Speed',u.speed]];
    h+=`<div class="panel"><h2>${esc(u.name)}</h2>
      <div class="kv">${(u.armor_classes||[]).map(c=>`<span class="tag">${esc(c)}</span>`).join('')||'<span class="muted small">no combat classes</span>'}</div>
      <div class="kv">${stats.map(([k,v])=>`<span class="stat">${k} <b>${v}</b></span>`).join('')}</div></div>`;
    const allC=u.best_counters;
    const strongVs=`<div class="panel"><h3 style="color:var(--grn)">💪 ${esc(u.name)} is strong vs</h3>
        ${Object.keys(u.bonus_damage_vs).length?Object.entries(u.bonus_damage_vs).map(([k,v])=>`<span class="chip str">${esc(k)} <b>+${v}</b></span>`).join(''):'<p class="hint">No bonus damage — a generalist, not a counter unit.</p>'}</div>`;
    const civ=S.myciv&&M().civilizations.find(c=>c.name.toLowerCase()===S.myciv.toLowerCase());
    if(civ){
      const ru=M().civ_units[civ.name]||{}, roster=new Set(ru.all_units||[]), uq=new Set(ru.unique_units||[]);
      const avail=allC.filter(c=>roster.has(c.unit));
      h+=`<div class="panel" style="border:1px solid var(--gold)"><h3 style="color:var(--gold)">🛡️ ${esc(civ.name)} should counter it with</h3>
        ${avail.length?avail.map(c=>{const uo=umap[c.unit]||{};return `<div style="margin:8px 0;padding:9px 11px;background:var(--panel2);border:1px solid var(--line);border-radius:8px">
            <b>${uq.has(c.unit)?'<span class="uniq">'+esc(c.unit)+'</span>':esc(c.unit)}</b>
            <span class="chip cnt" style="margin-left:6px">+${c.bonus} vs ${esc(c.vias.join(', '))}</span>${c.outranged?' <span class="chip" style="border-color:var(--red);color:var(--red)">⚠ it outranges you</span>':''}
            <div class="small muted" style="margin-top:4px">${esc(tip(uo))}${uo.vbld?` · ~${uo.vbld.total} vils to mass-produce`:''}${c.outranged?' · it has more range, so mass up and use numbers or your own ranged units.':''}</div></div>`;}).join('')
          :`<p class="hint">${esc(civ.name)} has no hard counter to this in its roster — use your strongest gold unit, or win with eco / numbers.</p>`}
        </div>
        <details class="panel"><summary class="sec-h" style="cursor:pointer">Counters from any civilization (${allC.length})</summary>
          <div style="margin-top:8px">${allC.length?allC.map(ctrChip).join(''):'<p class="hint">No hard counters.</p>'}</div></details>
        ${strongVs}`;
    } else {
      h+=`<div class="grid2">
        <div class="panel"><h3 style="color:var(--red)">🗡️ Beat it with</h3>
          ${allC.length?allC.map(ctrChip).join(''):'<p class="hint">No hard counters — fight it cost-effectively or with raw numbers.</p>'}
          <p class="small muted" style="margin-top:8px">Effective bonus after armor. ⚠ = the enemy outranges this unit. Add your civ above to filter to your roster.</p></div>
        ${strongVs}</div>`;
    }
    const soft=softCounters(u);
    h+=`<div class="panel"><h3 style="color:var(--blu)">🧠 Practical / soft counters <span class="muted small">(rules of thumb)</span></h3>
      ${soft.length?soft.map(([n,why])=>`<div class="small" style="margin:5px 0"><b>${esc(n)}</b> <span class="muted">(${esc(why)})</span></div>`).join(''):'<p class="hint">Use cost-effective trash units, or your strongest gold unit.</p>'}
      <p class="small muted" style="margin-top:8px">The hard counters above are exact bonus damage from the game data. These are general rules of thumb (cost, armor, range, micro). For the community's full practical chart, open the <b>Reference</b> tab.</p></div>`;
  }
  elv().innerHTML=h;
  const sug=()=>{const box=$('#suggest');if(!box)return;const v=S.enemy.toLowerCase().trim();
    if(!v||units.some(x=>x.name.toLowerCase()===v)){box.innerHTML='';return;}
    box.innerHTML=names.filter(n=>n.toLowerCase().includes(v)).slice(0,8)
      .map(n=>`<span class="chip" style="cursor:pointer" data-pick="${esc(n)}">${esc(n)}</span>`).join('');
    box.querySelectorAll('[data-pick]').forEach(x=>x.onclick=()=>{S.enemy=x.dataset.pick;render();});};
  const inp=$('#enemy');
  inp.oninput=()=>{S.enemy=inp.value;if(units.find(x=>x.name.toLowerCase()===inp.value.toLowerCase()))render();else sug();};
  const mc=$('#myciv');
  mc.oninput=()=>{S.myciv=mc.value;if(!mc.value||civNames.some(c=>c.toLowerCase()===mc.value.toLowerCase()))render();};
  sug();   // no autofocus: focusing the datalist input pops its dropdown open on load
}

/* ---------- CIVILIZATIONS ---------- */
function viewCivs(){
  const civs=M().civilizations.filter(c=>c.name.toLowerCase().includes(S.cq.toLowerCase()));
  if(S.civ){
    const c=M().civilizations.find(x=>x.name===S.civ), r=M().civ_units[c.name];
    const uq=new Set(r?r.unique_units:[]);
    elv().innerHTML=`<div class="panel"><button class="chip" id="back">← all civilizations</button>
      <h2 style="margin-top:8px">${esc(c.name)}</h2>
      <div class="muted">${esc(c.civ_type||'')} · ${esc(c.expansion||'')}</div>
      ${c.meta?`<div style="margin-top:10px;padding:10px 12px;background:var(--panel2);border:1px solid var(--line);border-radius:8px">
        <div class="sec-h">How they play</div><div class="small">${esc(c.meta.playstyle)}</div>
        ${c.meta.watch_for?`<div class="small" style="margin-top:5px"><b class="uniq">Watch for:</b> ${esc(c.meta.watch_for)}</div>`:''}</div>`:''}
      <p class="sec-h" style="margin-top:14px">Civilization bonuses</p>
      <ul class="b">${c.civ_bonuses.map(b=>`<li>${esc(b.text)}</li>`).join('')}</ul>
      <p class="sec-h">Team bonus</p><p>${c.team_bonus?esc(c.team_bonus.text):'—'}</p>
      <p class="sec-h">Unique unit${c.unique_unit_text.length>1?'s':''}</p>
      <p class="uniq">${c.unique_unit_text.map(esc).join('<br>')||'—'}</p>
      <p class="sec-h">Unique techs</p>
      ${c.unique_techs.length?c.unique_techs.map(t=>`<div style="margin:6px 0"><b class="uniq">${esc(t.name)}</b>
        <span class="muted small">(${money(t.cost)}${t.research_time?`, ${t.research_time}s`:''})</span>
        ${t.effect?`<br><span class="small">${esc(t.effect)}</span>`:''}</div>`).join(''):'<p>—</p>'}
      ${c.tactics&&c.tactics.length?`<p class="sec-h">Unique unit tactics <span class="muted">(community)</span></p>
        ${c.tactics.map(t=>`<div style="margin:6px 0"><b class="uniq">${esc(t.unit)}</b>
          <span class="muted small">${esc(t.type)}${t.bonus?' · bonus vs '+esc(t.bonus):''}</span><br>
          <span class="small">${esc(t.notes)}</span></div>`).join('')}`:''}
      <p class="sec-h">Full roster <span class="muted">(${r?r.all_units.length:0} units · <span class="uniq">unique</span> highlighted)</span></p>
      <div>${(r?r.all_units:[]).map(n=>`<span class="chip ${uq.has(n)?'':''}" style="${uq.has(n)?'border-color:var(--gold)':''}">${uq.has(n)?'<span class="uniq">'+esc(n)+'</span>':esc(n)}</span>`).join('')}</div></div>`;
    $('#back').onclick=()=>{S.civ=null;render();};
    return;
  }
  elv().innerHTML=`<div class="panel"><input id="cq" placeholder="Search ${civs.length} civilizations…" value="${esc(S.cq)}"></div>
    <div class="grid3" id="clist">${civs.map(c=>`<div class="civcard" data-c="${esc(c.name)}">
      <div>${esc(c.name)}</div><div class="t">${esc(c.civ_type||'')}</div>
      <div class="t uniq">${esc((c.unique_unit_text[0]||'').split('(')[0].trim())}</div></div>`).join('')}</div>`;
  const q=$('#cq');q.oninput=()=>{S.cq=q.value;const p=q.selectionStart;viewCivs();$('#cq').focus();$('#cq').setSelectionRange(p,p);};
  elv().querySelectorAll('.civcard').forEach(d=>d.onclick=()=>{S.civ=d.dataset.c;render();});
}

/* ---------- UNITS ---------- */
function viewUnits(){
  let us=M().units.filter(u=>u.name.toLowerCase().includes(S.uq.toLowerCase()));
  const num=v=>typeof v==='number'?v:0;
  const key=u=>S.sort==='name'?u.name:S.sort==='cost'?
    num(u.cost.Food)+num(u.cost.Wood)+num(u.cost.Gold)+num(u.cost.Stone)
    :S.sort==='vbld'?(u.vbld?u.vbld.total:0):num(u[S.sort]);
  us=us.sort((a,b)=>{const ka=key(a),kb=key(b);return (ka>kb?1:ka<kb?-1:0)*S.dir;});
  const cols=[['name','Unit'],['cost','Cost'],['hp','HP'],['attack','Atk'],
    ['melee_armor','M.arm'],['pierce_armor','P.arm'],['range','Rng'],['speed','Spd'],['vbld','Vils/bld']];
  const vparts=u=>u.vbld?Object.entries(u.vbld.parts).map(([r,v])=>`${v} ${r.toLowerCase()}`).join(', '):'';
  elv().innerHTML=`<div class="panel"><h2>🛡️ Units</h2>
     <p class="hint"><b>Vils/bld</b> = villagers needed to continuously produce a unit from one production building (base gather rates, no eco upgrades or civ bonuses). Click a row for counters and the resource breakdown. Villager-production idea adapted from <a href="https://aoe2-de-tools.herokuapp.com/villagers-required/" target="_blank">Survivalist's aoe2-de-tools</a>.</p>
     <input id="uq" placeholder="Search ${M().units.length} units…" value="${esc(S.uq)}"></div>
   <div class="panel" style="overflow:auto"><table><thead><tr>
   ${cols.map(([k,l])=>`<th data-k="${k}">${l}${S.sort===k?(S.dir>0?' ▲':' ▼'):''}</th>`).join('')}
   <th>Bonus vs</th></tr></thead><tbody>
   ${us.map((u,i)=>`<tr class="u" data-i="${i}">
     <td>${esc(u.name)}</td><td class="small">${money(u.cost)}</td><td>${u.hp??'—'}</td><td>${u.attack??'—'}</td>
     <td>${u.melee_armor??'—'}</td><td>${u.pierce_armor??'—'}</td><td>${u.range||'—'}</td><td>${u.speed??'—'}</td>
     <td>${u.vbld?u.vbld.total:'—'}</td>
     <td class="small">${Object.entries(u.bonus_damage_vs).map(([k,v])=>`${esc(k)} +${v}`).join(', ')||'—'}</td></tr>
     <tr class="det" id="d${i}" style="display:none"><td colspan="10">
       <b style="color:var(--red)">Countered by:</b> ${u.best_counters.map(c=>esc(c.unit)+' +'+c.bonus).join(', ')||'—'}
       ${u.vbld?`<br><b style="color:var(--gold)">To mass-produce (1 building):</b> ~${u.vbld.total} villagers (${vparts(u)})`:''}
     </td></tr>`).join('')}
   </tbody></table></div>`;
  const q=$('#uq');q.oninput=()=>{S.uq=q.value;const p=q.selectionStart;viewUnits();$('#uq').focus();$('#uq').setSelectionRange(p,p);};
  elv().querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
    const k=th.dataset.k;if(S.sort===k)S.dir*=-1;else{S.sort=k;S.dir=1;}viewUnits();});
  elv().querySelectorAll('tr.u').forEach(tr=>tr.onclick=()=>{
    const d=$('#d'+tr.dataset.i);d.style.display=d.style.display==='none'?'':'none';});
}

/* ---------- BUILD ORDERS ---------- */
function fbtn(label,on,attr){return `<button ${attr} style="background:${on?'var(--gold)':'var(--panel2)'};color:${on?'#241c10':'var(--ink)'};border:1px solid var(--line);padding:5px 11px;border-radius:7px;cursor:pointer;font-size:12px;${on?'font-weight:600':''}">${esc(label)}</button>`;}
function viewBuilds(){
  const bc=DATA.build_catalog, cats=['All'].concat(bc.categories);
  const cat=S.bcat||'All';
  const phase=(t,a)=>a&&a.length?`<div style="margin-top:8px"><div class="sec-h">${t}</div><ul class="b">${a.map(s=>`<li>${esc(s)}</li>`).join('')}</ul></div>`:'';
  // Red Phosphorus fast castles -> dedicated sub-selector
  const rp=bc.builds.filter(b=>b.author==='Red Phosphorus');
  const sel=rp.find(b=>b.id===S.rpfc)||rp[0];
  const rpPanel=`<div class="panel" style="border:1px solid var(--gold)">
      <h2>⚔️ Red Phosphorus — Uncounterable Fast Castle</h2>
      <p class="hint">One fixed, optimized Fast Castle opening. "Uncounterable" means you reliably reach Castle Age <b>every game</b>, even under Feudal pressure (if denied, sell stone and wood at the Market to still click up). It is a fixed build, not a flexible one. The Castle-Age plans below are just normal play, chosen by your civ and the matchup. <a href="${esc(rp[0].source)}" target="_blank">source ↗</a></p>
      <div class="sec-h" style="margin-top:8px">Castle-Age plan (pick by matchup)</div>
      <div class="row" style="margin:6px 0 8px">${rp.map(b=>fbtn('→ '+b.followup,b.id===sel.id,`data-rp="${b.id}"`)).join('')}</div>
      <div style="border-top:1px solid var(--line);padding-top:8px">
        <h3>${esc(sel.name)} <span class="muted small">· ${esc(sel.level)} · ${esc(sel.vills)}</span></h3>
        ${sel.when?`<p class="small" style="margin:4px 0"><b class="uniq">When to use:</b> ${esc(sel.when)}</p>`:''}
        ${phase('Dark Age (shared opening)',sel.dark)}${phase('Feudal Age (shared opening)',sel.feudal)}${phase('Castle Age — '+sel.followup,sel.castle)}
        ${sel.notes&&sel.notes.length?`<div style="margin-top:8px"><div class="sec-h">Notes</div><ul class="b">${sel.notes.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></div>`:''}
      </div></div>`;
  // general catalog (excludes Red Phosphorus builds — they live in the panel above)
  let list=bc.builds.filter(b=>b.author!=='Red Phosphorus'&&(cat==='All'||b.category===cat));
  if(S.bq){const q=S.bq.toLowerCase();list=list.filter(b=>(b.name+' '+b.summary+' '+(b.civ||'')+' '+b.category+' '+b.level).toLowerCase().includes(q));}
  const nMain=bc.builds.filter(b=>b.author!=='Red Phosphorus').length;
  elv().innerHTML=`<div class="panel"><h2>📜 Build orders</h2>
      <p class="hint">${bc.builds.length} build orders from AoE Companion and community guides — including Red Phosphorus's Fast Castle set below. Click any build to expand the full step-by-step order.</p></div>
    ${rpPanel}
    <div class="panel"><div class="sec-h">All other build orders (${nMain})</div>
      <div class="row" style="margin:8px 0 6px">${cats.map(c=>fbtn(c,c===cat,`data-cat="${esc(c)}"`)).join('')}</div>
      <input id="bq" placeholder="Search builds — e.g. knights, drush, Franks, imperial…" value="${esc(S.bq||'')}"></div>
    ${list.map(b=>`<div class="panel" style="border-left:5px solid var(--gold)">
        <div class="bhead" data-id="${b.id}" style="cursor:pointer">
          <h3>${esc(b.name)} ${b.civ?`<span class="chip" style="border-color:var(--gold)"><span class="uniq">${esc(b.civ)}</span></span>`:''}</h3>
          <div class="muted small">${esc(b.category)} · ${esc(b.level)} · ${esc(b.vills)}</div>
          <div class="small" style="margin-top:4px">${esc(b.summary)}</div>
          ${S.bopen===b.id?'':'<div class="small muted" style="margin-top:4px">▼ expand build order</div>'}
        </div>
        ${S.bopen===b.id?`<div style="margin-top:8px;border-top:1px solid var(--line);padding-top:8px">
            ${phase('Dark Age',b.dark)}${phase('Feudal Age',b.feudal)}${phase('Castle Age',b.castle)}${phase('Imperial Age',b.imperial)}
            ${b.notes&&b.notes.length?`<div style="margin-top:8px"><div class="sec-h">Notes</div><ul class="b">${b.notes.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></div>`:''}
            <a class="small" href="${esc(b.source)}" target="_blank">source ↗</a></div>`:''}
      </div>`).join('')||'<div class="panel hint">No builds match.</div>'}
    <div class="panel"><div class="sec-h">Beginner: 5 builds in one flowchart (r/aoe2)</div>
      <a href="assets/buildorders.png" target="_blank"><img src="assets/buildorders.png" style="width:100%;border-radius:8px"></a></div>`;
  elv().querySelectorAll('[data-rp]').forEach(x=>x.onclick=()=>{S.rpfc=x.dataset.rp;viewBuilds();});
  elv().querySelectorAll('[data-cat]').forEach(x=>x.onclick=()=>{S.bcat=x.dataset.cat;viewBuilds();});
  const q=$('#bq');if(q)q.oninput=()=>{S.bq=q.value;const p=q.selectionStart;viewBuilds();$('#bq').focus();$('#bq').setSelectionRange(p,p);};
  elv().querySelectorAll('.bhead').forEach(hd=>hd.onclick=()=>{S.bopen=S.bopen===hd.dataset.id?null:hd.dataset.id;viewBuilds();});
}
/* ---------- REFERENCE CHARTS ---------- */
function viewRef(){
  const imgs=[['Unit response chart','assets/response_normal.jpg','Follow an arrow from the unit you face to the unit that beats it.'],
    ['Unit response chart — reversed','assets/response_reversed.jpg','Same matchups, arrows reversed: “to beat X, build Y.”'],
    ['Unique-units reference','assets/unique_units.jpg','Every civ’s unique unit with type, attack bonus and notes — also folded into the Civilizations tab.']];
  elv().innerHTML=`<div class="panel"><h2>📖 Reference charts</h2>
    <p class="hint">Community infographics from r/aoe2, preserved as-is. Click any chart to open it full size.</p></div>`+
    imgs.map(([t,src,cap])=>`<div class="panel"><p class="sec-h">${esc(t)}</p><p class="small muted">${esc(cap)}</p>
      <a href="${src}" target="_blank"><img src="${src}" style="width:100%;border-radius:8px" loading="lazy"></a></div>`).join('');
}
function render(){modesBar();tabsBar();
  ({counters:viewCounters,civs:viewCivs,units:viewUnits,builds:viewBuilds,ref:viewRef}[S.tab])();
  window.scrollTo(0,0);}   // reset scroll on every tab/civ/mode switch (search keystrokes call the view fn directly, so they don't jump)
render();
</script>
<script data-goatcounter="__GOATCOUNTER__" async src="//gc.zgo.at/count.js"></script>
</body></html>"""

html = HTML.replace('__DATA__', blob).replace('__GOATCOUNTER__', GOATCOUNTER)
# inline chart images as data URIs -> truly single-file, no assets/ folder
ASSETS = {'buildorders.png': 'image/png', 'response_normal.jpg': 'image/jpeg',
          'response_reversed.jpg': 'image/jpeg', 'unique_units.jpg': 'image/jpeg'}
for fn, mime in ASSETS.items():
    b64 = base64.b64encode(open('assets/' + fn, 'rb').read()).decode()
    html = html.replace('assets/' + fn, f'data:{mime};base64,{b64}')
html = html.replace('—', '-').replace('–', '-')   # strip em/en dashes from the whole UI (template + embedded data)
open('guide.html', 'w').write(html)
print(f"wrote self-contained guide.html ({len(html)//1024} KB, images inlined) — "
      f"{sum(len(m['units']) for m in data['modes'].values())} units, "
      f"{sum(len(m['civilizations']) for m in data['modes'].values())} civs")
