#!/usr/bin/env python3
"""Work out which book each sheet entry comes from, for entries whose own source code 5e.tools does not know
("2014", "PHB", "-", "UA7", "Arcana Unleashed" ...). Nothing in the sheet's data is changed: the result is a
lookup the Vault and the players' pickers read.

Usage: source_map.py SHEET.html SITE sources.json OUT.json [UA_REPO]
OUT: { list: { key: ABV } } for lists spells, feats, subclasses, species, backgrounds, gear, weapons, armour, val, mnt.
Rule: a known code is kept; an alias is translated (EFotA -> EFA ...); "2014" = the oldest printing of that name,
"-"/"PHB"/"2024" = the newest; playtest codes -> "UA"; anything not found -> "Legacy" (2014) or PHB'24.
"""
import json, re, sys, glob, collections
from playwright.sync_api import sync_playwright
SHEET, SITE, SRC, OUT = sys.argv[1:5]; UA = sys.argv[5] if len(sys.argv) > 5 else None
# books made of dated parts (D&D Beyond Drops): entry name -> part, from sources.cjs
try: PARTS = json.load(open(SRC.replace('.json', '') + '.parts.json'))
except Exception: PARTS = {}
PART_OF = {n: pa for P in PARTS.values() for n, pa in P.items()}
S = json.load(open(SRC)); J = json.load(open(SRC.replace('.json', '') + '.json2abv.json'))
ALIAS = {'EFotA': 'EFA', 'RtHW': 'RHW', 'ABoH': 'ABH', 'Arcana Unleashed': 'AU', 'DMG24': "DMG'24", 'MotM': 'MPMM', "PHB'24 (House Rule)": "PHB'24", 'TCoE': 'TCE', 'BoH': 'ABH'}
OLD, NEW = {'2014'}, {'-', 'PHB', '2024', '', None}
nk = lambda n: re.sub(r'[^a-z0-9]+', '', (n or '').lower().replace('’', "'"))
def load(pat, prop):
    out = []
    for f in sorted(glob.glob(SITE + '/data/' + pat)):
        out += json.load(open(f)).get(prop, [])
    return out
def index(entries, name=lambda e: [e['name']] if e.get('name') else []):
    ix = collections.defaultdict(list)
    for e in entries:
        if e.get('source') not in J: continue
        for n in name(e): ix[nk(n)].append((J[e['source']][1] or '9999', J[e['source']][0]))
    return {k: sorted(set(v)) for k, v in ix.items()}
IX = {
  'feats': index(load('feats.json', 'feat') + load('optionalfeatures.json', 'optionalfeature')),
  'subclasses': index(load('class/class-*.json', 'subclass'), lambda e: [e['className'] + '/' + e['name'], e['className'] + '/' + e.get('shortName', e['name'])]),
  'species': index(load('races.json', 'race') + load('races.json', 'subrace')),
  'backgrounds': index(load('backgrounds.json', 'background')),
  'items': index(load('items-base.json', 'baseitem') + load('items.json', 'item')),
  'spells': index(load('spells/spells-*.json', 'spell')),
}
# playtest: every packet in the unearthed-arcana collection, by entry name (codes the sheet made up: UA7, UA2026, UA25P...)
UAIX, UAABV, UADATE = collections.defaultdict(list), {}, {}
if UA:
    PROPS = {'spells': ['spell'], 'feats': ['feat', 'optionalfeature'], 'subclasses': ['subclass'], 'species': ['race', 'subrace'], 'backgrounds': ['background'], 'items': ['item', 'baseitem']}
    for f in glob.glob(UA + '/*/*.json'):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        mm = d.get('_meta') or {}
        for m_ in mm.get('sources', []): UAABV[m_['json']] = m_.get('abbreviation') or m_['json']; UADATE[m_['json']] = mm.get('dateReleased') or m_.get('dateReleased') or ''
        for lst, props in PROPS.items():
            for pr in props:
                for e in d.get(pr, []) or []:
                    if not isinstance(e, dict) or not e.get('source'): continue
                    for n in ([e['className'] + '/' + e['name'], e['className'] + '/' + e.get('shortName', e['name'])] if pr == 'subclass' and e.get('className') else [e.get('name')]):
                        if n: UAIX[(lst, nk(n))].append(e['source'])
def ua_packet(lst, name, code):
    # the packet with this entry: the one whose code matches the sheet's (UA25P -> XUA25P), else the newest
    def w(n):
        n = n or ''; cls, _, nm = n.rpartition('/'); pre = cls + '/' if cls else ''
        bare = re.sub(r'^(?:path|college|circle|oath|way|school|order|domain|warrior) of (?:the )?', '', nm, flags=re.I)
        bare2 = re.sub(r'\s+(patron|domain|sorcery)$', '', re.sub(r'^the\s+', '', bare, flags=re.I), flags=re.I)
        return [n, pre + bare, pre + bare2, pre + bare2 + ' Patron']
    cand = []
    for n in w(name): cand += UAIX.get((lst if lst in ('spells', 'feats', 'subclasses', 'species', 'backgrounds') else 'items', nk(n)), [])
    abvs = sorted(set(UAABV.get(j, j) for j in cand), key=lambda a: max([UADATE.get(j, '') for j, v in UAABV.items() if v == a] or ['']))
    for a in abvs:
        if code and (a == code or a == 'X' + code): return a
    if len(abvs) > 1: return abvs           # decided after the others with this code are known
    if abvs: return abvs[0]
    if code and ('X' + code) in S: return 'X' + code
    return None
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto('file://' + SHEET); pg.wait_for_timeout(3000)
    L = pg.evaluate("""()=>{ const a=(X,f)=>(Array.isArray(X)?X.map(x=>[x.key,x]):Object.entries(X)).map(([k,x])=>({key:k,name:f?f(k,x):x.name,source:x.source||null}));
      const g=n=>{try{return eval(n)}catch(e){return null}};
      return {spells:a(PHB_SPELL_LIST), feats:a(PHB_FEATS), subclasses:a(PHB_SUBCLASSES,(k,x)=>(PHB_CLASSES[k.split('/')[0]]||{name:k.split('/')[0]}).name+'/'+x.name), species:a(g('PHB_RACES')||{}), backgrounds:a(g('PHB_BACKGROUNDS')||{}),
        gear:a(PHB_GEAR), weapons:a(PHB_WEAPONS), armour:a(PHB_ARMOUR), val:a(VALUABLES_CATALOG), mnt:a(MOUNTS_VEHICLES_CATALOG)} }""")
def pick(c, core, old):
    a = [x[1] for x in c]
    if core in a: return core
    if not old: return ("DMG'24" if "DMG'24" in a else a[-1])
    b = [x for x in a if x != "DMG'14"] or a
    return b[0]
out, stat = {}, collections.Counter()
LATER, VOTES = [], collections.defaultdict(collections.Counter)   # several packets fit: prefer the one(s) other entries with the same code are in
for lst, rows in L.items():
    ix = IX.get(lst) or IX['items']; m = out[lst] = {}
    for r in rows:
        s = r['source']
        if s in PARTS and (r['name'] or '').rpartition('/')[2].lower() in PARTS[s]: m[r['key']] = PARTS[s][(r['name'] or '').rpartition('/')[2].lower()]; stat['part of a book'] += 1; continue
        if s in S and s != 'UA': stat['known'] += 1; continue
        if s in ALIAS: m[r['key']] = ALIAS[s]; stat['alias'] += 1; continue
        if s and re.match(r'^(X?UA|UV)', s):
            a = ua_packet(lst, r['name'], s) if UA else None
            if isinstance(a, list): LATER.append((m, r['key'], s, a)); continue
            bare = (r['name'] or '').rpartition('/')[2].lower()   # subclasses come as "Class/Name"
            if not a and bare in PART_OF: a = PART_OF[bare]   # not playtest after all (e.g. a D&D Beyond Drop)
            if a: VOTES[s][a] += 1
            m[r['key']] = a or 'UA'; stat['playtest packet' if a else 'playtest (packet not found)'] += 1; continue
        if s and '(' in s:                                  # "Tabaxi (MPMM)", "Dhampir (BoH)": the book in brackets
            inner = s[s.index('(') + 1:].rstrip(')'); inner = ALIAS.get(inner, inner)
            if inner in S: m[r['key']] = inner; stat['bracket'] += 1; continue
        if lst == 'species' and r['key'].startswith('multiverse_'): m[r['key']] = 'MPMM'; stat['key hint'] += 1; continue
        if lst == 'species' and r['key'].endswith('_mtof'): m[r['key']] = 'MTF'; stat['key hint'] += 1; continue
        w = (r['name'] or '').split(' ')
        c = ix.get(nk(r['name'])) or (ix.get(nk(f'{w[1]} ({w[0]})')) if len(w) == 2 else None) or ix.get(nk(re.sub(r'\s*\(.*\)$', '', r['name'] or ''))) or []
        if s in OLD:
            m[r['key']] = pick(c, "PHB'14", True) if c else 'Legacy'; stat['2014 by name' if c else '2014 not found'] += 1
        else:
            m[r['key']] = pick(c, "PHB'24", False) if c else "PHB'24"; stat['newest by name' if c else 'core not found'] += 1
for m, k, code, abvs in LATER:
    pref = [a for a in abvs if VOTES[code][a]] or [a for a in abvs if any(a.startswith(v[:6]) for v in VOTES[code])]
    m[k] = (sorted(pref, key=lambda a: -VOTES[code][a])[0] if pref else abvs[-1]); stat['playtest packet'] += 1
json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(dict(stat)); print({k: collections.Counter(v.values()).most_common(8) for k, v in out.items()})
