#!/usr/bin/env python3
"""Map every item the sheet has today onto the parsed CSV entries.

Usage: imap.py items_norm.json SHEETDATA_DIR OUT.json
Output: {'map': {oldKey: {key, entryId, version, base, how}}, 'unmatched': [...], 'report': ...}
"""
import json, re, sys, collections

NORM, SD, OUT = sys.argv[1:4]
N = json.load(open(NORM))
E = N['entries']
D = json.load(open(SD + '/DMG_MAGIC_ITEMS.json'))
A = json.load(open(SD + '/AU_MAGIC_ITEMS.json'))

def k(n):
    n = (n or '').lower().replace('’', "'").replace('armour', 'armor')
    n = re.sub(r"'s\b", 's', n)
    return re.sub(r'[^a-z0-9+]+', ' ', n).strip()

# row name -> (entry, version, base)
idx = collections.defaultdict(list)
for e in E:
    idx[k(e['name'])].append((e, None, None))
    for r in e['rows']: idx[k(r)].append((e, None, None))
    for b in e.get('bases') or []: idx[k(b['row'])].append((e, None, b['name']))
    for v in e.get('versions') or []:
        idx[k(v['name'])].append((e, v['id'], v.get('fixedBase')))
        for r in v.get('rows') or []: idx[k(r)].append((e, v['id'], v.get('fixedBase')))
        for b in v.get('bases') or []: idx[k(b['row'])].append((e, v['id'], b['name']))

def pick(cands, src):
    if not cands: return None
    # prefer most specific (with version/base), then same book
    seen = []
    for c in cands:
        if c not in seen: seen.append(c)
    same = [c for c in seen if c[0]['source'] == src] or seen
    same.sort(key=lambda c: (c[1] is None, c[2] is None))
    return same[0]

LEGACY = re.compile(r',?\s*\+1(?:,\s*\+2)?(?:,?\s*(?:or|,)\s*\+[23])+\s*$', re.I)   # "X, +1, +2, or +3"
def variants_of(name):
    out = [name]
    m = LEGACY.search(name)
    if m:
        stem = name[:m.start()].strip(' ,')
        out += ['+1/+2/+3 ' + stem, stem + ' +1/+2/+3', stem]
    m = re.match(r'^(.*?)\s*\+([123])$', name)          # "Elven Chain +1" -> "+1 Elven Chain"
    if m: out += ['+%s %s' % (m.group(2), m.group(1))]
    m = re.match(r'^\+([123])\s+(.*)$', name)
    if m: out += ['%s +%s' % (m.group(2), m.group(1))]
    m = re.match(r'^(.*?)\s*\((common|uncommon|rare|very rare|legendary)\)$', name, re.I)
    if m: out += [m.group(1)]
    out += [name.replace(' Of ', ' of ').replace("'S ", "'s ")]
    return out

# name templates: "Dancing {b}" -> entry, from every base row
TPL = collections.defaultdict(list)
BASENAMES = set()
for e in E:
    for v in [None] + list(e.get('versions') or []):
        for b in ((v or e).get('bases') or []):
            BASENAMES.add(b['name'])
            i0 = b['row'].lower().find(b['name'].lower())
            if i0 >= 0:
                TPL[k(b['row'][:i0] + ' QQB ' + b['row'][i0+len(b['name']):])].append((e, v['id'] if v else None, None))
W = json.load(open(SD + '/PHB_WEAPONS.json')); AR = json.load(open(SD + '/PHB_ARMOUR.json'))
BASENAMES |= {w['name'] for w in W} | {a['name'] for a in AR}
BASENAMES |= {'Acid Fighting Chain', '+1 Acid Fighting Chain', 'Fighting Chain, Two-Handed', 'Bellows Canister', 'Crossbow Bolts'}
BASES_LONGEST = sorted(BASENAMES, key=len, reverse=True)
def by_template(name, src):
    low = name.lower()
    for b in BASES_LONGEST:
        i0 = low.find(b.lower())
        if i0 < 0 or len(b) < 3: continue
        t = k(name[:i0] + ' QQB ' + name[i0+len(b):])
        c = pick(TPL.get(t), src)
        if c: return (c[0], c[1], b)
    return None

ALIAS = {   # old sheet key -> (CSV entry/row name, base)
  'elven_chain': ('Elven Chain', None), 'demon_armor': ('Demon Armor', None), 'efreeti_chain': ('Efreeti Chain', None),
  'piwafwi__cloak_of_elvenkind': ('Piwafwi (Cloak of Elvenkind)', None), 'bomb__renaissance': ('Bomb', None),
  'gambler_s_blade': ("Gambler's Blade", None), 'polymorph_blade': ('Polymorph Blade', None),
  'blade_of_the_medusa': ('Weapon of the Medusa', None), 'monster_tamer_s_knightly': ("Monster Tamer's Weapon", 'Knightly Sword'),
  'barrier_tattoo': ('Barrier Tattoo', None),
  'all_purpose_tool': ('+1/+2/+3 All-Purpose Tool', None), 'amulet_of_the_devout': ('+1/+2/+3 Amulet of the Devout', None),
  'arcane_grimoire': ('+1/+2/+3 Arcane Grimoire', None), 'bloodwell_vial': ('+1/+2/+3 Bloodwell Vial', None),
  'rhythm_maker_s_drum': ("+1/+2/+3 Rhythm-Maker's Drum", None),
  'delerium_crystal_chip': ('Chip', None), 'delerium_crystal_fragment': ('Fragment', None), 'delerium_crystal_shard': ('Shard (MoDk)', None),
  'delerium_crystal_crystal': ('Crystal (MoDk)', None), 'delerium_crystal_geode': ('Geode', None),
  'delerium_crystal_massive_cluster': ('Massive Cluster', None),
  # 27 Oct: old/UA copies that now exist under a newer name or book
  'white_dragonhide_cape': ('White Dragon Cape', None), 'radiance__wand': ('Radiance', None),
  'wraps_of_unarmed_prowess': ('Wraps of Unarmed Power', None), 'scroll_of_tarrasque_summoning': ('Scroll of Titan Summoning (Tarrasque)', None),
  'silver_dragon_shield__2': ('Shield of the Silver Dragon', None), 'red_dragon_s_thighbone': ('Dragon Thighbone Club', None),
  'plantslayer_longsword': ('Macuahuitl', None), 'plantslayer_battleaxe': ('Yester Hill Axe', None),
  'longsword_of_speaking_draconic': ('Draconic Longsword', None), 'powered_armor_llk': ('Powered Armor', None),
  'flame_tongue_shortsword_of_gem_detection': ('Flame Tongue Shortsword of Greed', None),
  'berserker_battleaxe__tamoachan': ("Tloques' Berserker Battleaxe", None), 'dragon_mask': ('Dragon Mask', None),
}
ENAME = {}
for e in E: ENAME.setdefault(e['name'], e)

res, unmatched = {}, []
for src_name, X in (('DMG', D), ('AU', A)):
    for x in X:
        c = None
        if x['key'] in ALIAS:
            an, ab = ALIAS[x['key']]
            e2 = ENAME.get(an)
            if e2 is None:
                cc = pick(idx.get(k(an)), None)
                if cc: e2 = cc[0]
            if e2 is not None: c = (e2, None, ab); how = 'manual'
        for nm in ([] if c else variants_of(x['name'])):
            c = pick(idx.get(k(nm)), x.get('source') or ('AU' if src_name == 'AU' else None))
            if c: how = 'name' if nm == x['name'] else 'renamed'; break
        if not c:
            c = by_template(x['name'], x.get('source'))
            if c: how = 'pattern'
        if not c:
            unmatched.append({'key': x['key'], 'name': x['name'], 'source': x.get('source'), 'type': x.get('type')}); continue
        e, ver, base = c
        res[x['key']] = {'entryId': e['id'], 'entry': e['name'], 'version': ver, 'base': base, 'how': how, 'oldName': x['name']}

stats = collections.Counter(v['how'] for v in res.values())
json.dump({'map': res, 'unmatched': unmatched}, open(OUT, 'w'), indent=0, ensure_ascii=False)
print('mapped', len(res), dict(stats), 'unmatched', len(unmatched))
print(collections.Counter(u['source'] for u in unmatched).most_common())
for u in unmatched: print('  ', u['key'], '|', u['name'], '|', u['source'], '|', u['type'])
