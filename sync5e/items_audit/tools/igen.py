#!/usr/bin/env python3
"""Build items_patch.json for step 42 from the parsed CSV (items_norm.json), the mapping of the
sheet's old items (items_map.json) and the sheet's current data (sheetdata/).

Usage: igen.py   (paths fixed below)
"""
import json, re, collections, sys

B = '/home/claude/cs/tooling/items_audit/'
N = json.load(open(B + 'items_norm.json'))
M = json.load(open(B + 'items_map.json'))
SD = B + 'sheetdata/'
OLD = json.load(open(SD + 'DMG_MAGIC_ITEMS.json'))
OLD_AU = json.load(open(SD + 'AU_MAGIC_ITEMS.json'))
W = json.load(open(SD + 'PHB_WEAPONS.json'))
AR = json.load(open(SD + 'PHB_ARMOUR.json'))
G = json.load(open(SD + 'PHB_GEAR.json'))
VAL = json.load(open(SD + 'VALUABLES_CATALOG.json'))
MNT = json.load(open(SD + 'MOUNTS_VEHICLES_CATALOG.json'))
E = N['entries']
# 3 Nov (user: "correct Long Sword to Longsword"): the CSV's "Long Sword" is the Longsword. A generic item's
# "Long Sword" form is dropped where the item also offers "Longsword", renamed where it doesn't; a fixed
# "Long Sword" base becomes "Longsword". Old copies made with "Long Sword" are moved over (aliases below, and
# module 47 on load).
# (same for the CSV's "Battle Axe", which is the Battleaxe)
_FOLD = {'Long Sword': 'Longsword', 'Battle Axe': 'Battleaxe'}
for _e in E:
    for _v in [_e] + list(_e.get('versions') or []):
        _bs = _v.get('bases')
        if _bs:
            _names = {b['name'] for b in _bs}; _nb = []
            for b in _bs:
                if b['name'] in _FOLD:
                    _to = _FOLD[b['name']]
                    if _to in _names: continue
                    b = dict(b, name=_to, row=str(b.get('row') or '').replace(b['name'], _to))
                _nb.append(b)
            _v['bases'] = _nb
        if _v.get('fixedBase') in _FOLD: _v['fixedBase'] = _FOLD[_v['fixedBase']]
# the CSV's "(*)" rows repeat an item of the same name and book: fold them into it
_names = {(e['name'], e['source']): e for e in E}
STAR_DROPPED = []
for e in list(E):
    if e['name'].endswith(' (*)'):
        stem = _names.get((e['name'][:-4], e['source']))
        if stem is not None:
            stem['rows'] += e['rows']; E.remove(e); STAR_DROPPED.append((e['id'], stem['id'], e['name']))
EBYID = {e['id']: e for e in E}
REPORT = collections.defaultdict(list)

def k(n):
    n = (n or '').lower().replace('’', "'").replace('‘', "'").replace('armour', 'armor')
    n = re.sub(r"'s\b", 's', n)
    return re.sub(r'[^a-z0-9+]+', ' ', n).strip()
def slug(n):
    n = (n or '').lower().replace('’', "'").replace('+', '')
    return re.sub(r'[^a-z0-9]+', '_', n).strip('_')
def clean(t): return (t or '').replace('‑', '-').replace('\xa0', ' ')
def wt(w):
    w = clean(w).strip()
    return re.sub(r'\.$', '', w) if w else None

# ════════════════════════════════════════════════════════ bases
WK = {k(w['name']): w['key'] for w in W}
WK.update({'staff': 'quarterstaff', 'hoopak': 'hoopak_melee', 'double bladed scimitar': [w['key'] for w in W if k(w['name']) == 'double bladed scimitar'][0],
           'long sword': None})
AK = {}
for a in AR:
    if a['key'] == 'mage_armor': continue
    AK[k(a['name'])] = a['key']; AK[k(a['name'] + ' armor')] = a['key']
AMMO = {'arrow': 'arrows', 'arrows': 'arrows', 'bolt': 'bolts', 'crossbow bolt': 'bolts', 'bolts': 'bolts',
        'sling bullet': 'bullets', 'needle': 'needles', 'blowgun needle': 'needles', 'firearm bullet': 'firearm_rounds',
        'energy cell': 'energy_cell'}
NEW_AMMO = {}
def ammo_key(name):
    n = k(re.sub(r',\s*(silver|wooden)$', '', name, flags=re.I))
    if n in AMMO: return AMMO[n]
    key = slug(n)
    NEW_AMMO.setdefault(key, name.split(',')[0].strip() + 's' if not name.endswith('s') else name)
    return key

PROPMAP = {'ammunition': 'ammunition', 'finesse': 'finesse', 'heavy': 'heavy', 'light': 'light', 'loading': 'loading',
           'reach': 'reach', 'thrown': 'thrown', 'two-handed': 'two_handed', 'versatile': 'versatile', 'special': 'special',
           'burst fire': 'burst_fire'}
def split_props(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(': depth += 1
        if ch == ')': depth -= 1
        if ch == ',' and depth == 0: out.append(cur.strip()); cur = ''
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

def make_weapon(name, row, mundane=False):
    props_txt = clean(row.get('properties', ''))
    ctype = clean(row.get('csvType', ''))
    dmg = clean(row.get('damage', ''))
    m = re.match(r'^(\d+)(?:d(\d+))?\s*(\w+)?', dmg)
    if m: damage = {'count': int(m.group(1)), 'die': int(m.group(2) or 1) if m.group(2) else 1, 'type': (m.group(3) or '').lower()}
    else: damage = {'count': 0, 'die': 0, 'type': ''}
    if m and not m.group(2): damage = {'count': int(m.group(1)), 'die': 1, 'type': (m.group(3) or '').lower()}
    props, extra = [], []
    vers = None; rng = None; thrown = None; ammo = None
    for p in split_props(props_txt):
        pl = p.lower()
        base = re.sub(r'\s*\(.*', '', pl).strip()
        arg = re.search(r'\((.*)\)', p)
        arg = arg.group(1) if arg else ''
        if base.startswith('range '):
            rng = re.sub(r'^range\s*', '', p, flags=re.I).replace(' ft.', ' ft').strip(); continue
        if base in PROPMAP:
            props.append(PROPMAP[base])
            if base == 'versatile':
                mm = re.search(r'1?d(\d+)', arg); vers = int(mm.group(1)) if mm else None
            if base == 'thrown':
                mm = re.search(r'(\d+/\d+)', arg); thrown = (mm.group(1) + ' ft') if mm else None
            if base == 'ammunition':
                mm = re.search(r'(\d+(?:/\d+)?)\s*ft', arg); rng = (mm.group(1) + ' ft') if mm else rng
                mm = re.search(r';\s*([^)]+)$', arg)
                if mm: ammo = ammo_key(mm.group(1).strip())
            if base == 'two-handed' and arg: extra.append(p)
        else:
            extra.append(p)
    comps = [c.strip() for c in ctype.split(',')]
    is_fire = any(c == 'Firearm' for c in comps)
    is_rng = any(c == 'Ranged Weapon' for c in comps)
    lst = 'firearm' if is_fire else ('ranged' if is_rng else 'melee')
    typ = 'Simple' if 'Simple Weapon' in comps else 'Martial'
    mast = clean(row.get('mastery', ''))
    mast = re.sub(r'^Mastery:\s*', '', mast).split(',')[0].strip()
    mast = re.sub(r'\s*\(.*', '', mast).lower().replace(' ', '_').replace('-', '_') or None
    if ammo is None and lst != 'melee' and 'ammunition' in props:
        ammo = 'firearm_rounds' if lst == 'firearm' else None
    w = {'key': slug(name), 'name': name, 'type': typ, 'list': lst, 'ability': 'dex' if lst != 'melee' else 'str',
         'damage': damage, 'versatile_die': vers, 'range': rng if lst != 'melee' else 'Melee',
         'thrown_range': thrown, 'properties': props, 'mastery': mast, 'mastery_desc': '', 'ammo': ammo,
         'monk': False, 'weight': wt(row.get('weight')), 'value': row.get('value') or None}
    if 'Advanced Weapon' in comps: w['category'] = 'Advanced'
    if is_fire: w['category'] = w.get('category') or 'Firearm'
    if extra: w['extraProps'] = extra
    if not mundane: w['baseOnly'] = True
    return w

def armour_type(ctype):
    c = clean(ctype).split(',')[0]
    for t in ('Light', 'Medium', 'Heavy'):
        if c.startswith(t): return t.lower()
    return 'medium'
def make_armour(name, row, desc='', mundane=False):
    dm = clean(row.get('damage', ''))
    m = re.search(r'AC\s*(\d+)', dm)
    a = {'key': slug(name), 'name': name, 'ac': int(m.group(1)) if m else 10, 'type': armour_type(row.get('csvType', '')),
         'stealthDisadv': 'Disadvantage on Dexterity (Stealth)' in (desc or ''), 'strReq': 0,
         'weight': wt(row.get('weight')), 'value': row.get('value') or None}
    mm = re.search(r'Strength score lower than (\d+)', desc or '')
    if mm: a['strReq'] = int(mm.group(1))
    mm = re.search(r'max (\d+)', dm)
    if 'Dex' not in dm and a['type'] != 'heavy': a['noDex'] = True
    if not mundane: a['baseOnly'] = True
    return a

# collect every base name with a sample row
BASE_ROWS = collections.OrderedDict()
def note_base(name, rec):
    if name and name not in BASE_ROWS: BASE_ROWS[name] = rec
for e in E:
    for v in [e] + list(e.get('versions') or []):
        for b in v.get('bases') or []: note_base(b['name'], b)
        if v.get('fixedBase'): note_base(v['fixedBase'], {'name': v['fixedBase'], 'csvType': v.get('csvType', ''), 'damage': v.get('damage', ''),
                                                           'properties': v.get('properties', ''), 'mastery': v.get('mastery', ''), 'weight': v.get('weight', '')})
MUNDANE_BY_NAME = {e['name']: e for e in E if e['kind'] in ('weapon', 'armour')}
NEW_WEAPONS, NEW_ARMOUR = [], []
BASES = {}   # base name -> {kind, key}
def base_kind(rec):
    c = clean(rec.get('csvType', '')).split(',')[0].strip()
    c0 = re.sub(r'\s*\(.*', '', c)
    if c0 in ('Weapon', 'Melee Weapon', 'Ranged Weapon', 'Staff') or 'Weapon' in c: return 'weapon'
    if c0 in ('Light Armor', 'Medium Armor', 'Heavy Armor', 'Armor'): return 'armour'
    if c0 == 'Shield': return 'shield'
    if c0 == 'Ammunition': return 'ammo'
    return 'other'
used_keys = {w['key'] for w in W} | {a['key'] for a in AR}
for name, rec in BASE_ROWS.items():
    kind = base_kind(rec)
    if kind == 'weapon':
        key = WK.get(k(name))
        if key is None:
            mrow = MUNDANE_BY_NAME.get(name)
            src = {'damage': mrow['damage'], 'properties': mrow['properties'], 'mastery': mrow['mastery'], 'weight': mrow['weight'],
                   'csvType': mrow['csvType'], 'value': mrow['value']} if mrow else rec
            w = make_weapon(name, src, mundane=bool(mrow))
            while w['key'] in used_keys: w['key'] += '_b'
            used_keys.add(w['key']); NEW_WEAPONS.append(w); WK[k(name)] = w['key']; key = w['key']
        BASES[name] = {'kind': 'weapon', 'key': key}
    elif kind == 'armour':
        key = AK.get(k(name)) or AK.get(k(re.sub(r'\s+armor$', '', name, flags=re.I)))
        if key is None:
            a = make_armour(name, rec)
            while a['key'] in used_keys: a['key'] += '_b'
            used_keys.add(a['key']); NEW_ARMOUR.append(a); AK[k(name)] = a['key']; key = a['key']
        BASES[name] = {'kind': 'armour', 'key': key}
    elif kind == 'shield':
        BASES[name] = {'kind': 'shield', 'key': 'shield'}
    elif kind == 'ammo':
        BASES[name] = {'kind': 'ammo', 'key': ammo_key(name)}
    else:
        BASES[name] = {'kind': 'other'}
# plain CSV weapons/armour the sheet lacks (Blowgun, Yklwa, Wooden Staff, Powered Armor)
for e in E:
    if e['kind'] == 'weapon' and k(e['name']) not in WK and e['name'] not in ('Hoopak',):
        w = make_weapon(e['name'], e, mundane=True)
        while w['key'] in used_keys: w['key'] += '_b'
        used_keys.add(w['key']); NEW_WEAPONS.append(w); WK[k(e['name'])] = w['key']
        REPORT['mundane_weapons_added'].append(e['name'])
    if e['kind'] == 'armour' and k(e['name']) not in AK and re.search(r'AC\s*\d', e['damage'] or ''):
        a = make_armour(e['name'], e, e['desc'], mundane=True)
        while a['key'] in used_keys: a['key'] += '_b'
        used_keys.add(a['key']); NEW_ARMOUR.append(a); AK[k(e['name'])] = a['key']
        REPORT['mundane_armour_added'].append(e['name'])
for w in NEW_WEAPONS:
    if w.get('ammo') and w['ammo'] not in ('arrows', 'bolts', 'bullets', 'darts', 'needles', 'firearm_rounds', 'energy_cell'):
        NEW_AMMO.setdefault(w['ammo'], w['ammo'].replace('_', ' ').title())

# updates to the sheet's existing weapons/armour from the CSV's plain rows (the CSV wins)
WEAPON_SET, ARMOUR_SET = {}, {}
for e in E:
    if e['kind'] == 'weapon' and k(e['name']) in {k(w['name']) for w in W}:
        old = [w for w in W if k(w['name']) == k(e['name'])][0]
        nw = make_weapon(old['name'], e, mundane=True)
        ch = {}
        for f in ('damage', 'versatile_die', 'weight', 'value', 'mastery'):
            ov, nv = old.get(f), nw.get(f)
            if f == 'weight' and ov and nv and ov.replace('.', '').strip() == nv.replace('.', '').strip(): continue
            if f == 'range' and old.get('list') == 'melee': continue
            if f == 'damage' and ov and nv and (ov.get('count'), ov.get('die'), ov.get('type')) == (nv['count'], nv['die'], nv['type']): continue
            if nv not in (None, '') and ov != nv: ch[f] = nv
        if False:
            ch['properties'] = sorted(set(nw['properties']) | (set(old.get('properties') or []) - set(PROPMAP.values())), key=nw['properties'].index if False else str)
            ch['properties'] = nw['properties'] + [p for p in (old.get('properties') or []) if p not in nw['properties'] and p not in PROPMAP.values()]
        if ch: WEAPON_SET[old['key']] = ch; REPORT['weapon_changes'].append({old['name']: ch})
    if e['kind'] == 'armour':
        key = AK.get(k(e['name']))
        old = next((a for a in AR if a['key'] == key), None)
        if not old or old['key'] == 'shield': continue
        na = make_armour(e['name'], e, e['desc'], mundane=True)
        ch = {}
        if old['name'] != e['name']: ch['name'] = e['name']
        for f in ('ac', 'weight', 'value', 'stealthDisadv', 'strReq'):
            ov, nv = old.get(f), na.get(f)
            if f == 'weight' and ov and nv and ov.replace('.', '') == nv.replace('.', ''): continue
            if nv not in (None, '') and ov != nv: ch[f] = nv
        if ch: ARMOUR_SET[old['key']] = ch; REPORT['armour_changes'].append({old['name']: ch})

# ════════════════════════════════════════════════════════ magic entries
OLDBYKEY = {x['key']: x for x in OLD}
OLDAUBYKEY = {x['key']: x for x in OLD_AU}
ALL_OLD_KEYS = set(OLDBYKEY) | set(OLDAUBYKEY)
by_entry = collections.defaultdict(list)            # entry id -> [(oldKey, version, base)]
_star = {a: b for a, b, _ in STAR_DROPPED}
for ok, v in M['map'].items(): by_entry[_star.get(v['entryId'], v['entryId'])].append((ok, v['version'], v['base']))

WIRE = ('effects', 'charges', 'grantedSpells', 'dmgres', 'resistanceOptions', 'container', 'grantedResources',
        'polymorphForm', 'attunementNoSlot', 'maxBonus', 'resistanceIsDragonColor', 'resistanceVulnBackfire', 'shortDesc', 'tiers')

def sheet_type(csvType, fixedBase=None, baseCat=None):
    c = clean(csvType).split(',')[0].strip()
    c0 = re.sub(r'\s*\(.*', '', c).strip()
    comps = [x.strip() for x in clean(csvType).split(',')]
    if c0 == 'Generic Variant':
        c0 = next((re.sub(r'\s*\(.*', '', x) for x in comps if x != 'Generic Variant'), baseCat or 'Wondrous Item')
        if c0 == 'Generic Variant': c0 = baseCat or 'Wondrous Item'
    t = {'Melee Weapon': 'weapon', 'Ranged Weapon': 'weapon', 'Weapon': 'weapon', 'Light Armor': 'armor', 'Medium Armor': 'armor',
         'Heavy Armor': 'armor', 'Armor': 'armor', 'Delerium': 'crystal'}.get(c0, c0.lower())
    if fixedBase and t in ('weapon', 'armor'): t = '%s (%s)' % (t, fixedBase.lower())
    if t == 'weapon' and baseCat and not fixedBase: t = 'weapon (any)'
    return t

def flags(csvType, baseCat=None):
    t = clean(csvType)
    comps = [x.strip() for x in t.split(',')]
    c0 = re.sub(r'\s*\(.*', '', comps[0])
    if c0 == 'Generic Variant' and baseCat: c0 = baseCat
    isAmmo = c0 == 'Ammunition' or baseCat == 'Ammunition'
    isWeapon = isAmmo or 'Weapon' in c0 or any(re.match(r'^(Weapon|Melee Weapon|Ranged Weapon)\b', x) for x in comps) or baseCat == 'Weapon'
    isArmour = c0 in ('Light Armor', 'Medium Armor', 'Heavy Armor', 'Armor', 'Shield') or baseCat in ('Armor', 'Shield')
    return isWeapon, isArmour, isAmmo

def attune(s):
    s = s or ''
    if s.startswith('Requires Attunement'):
        note = s[len('Requires Attunement'):].strip()
        return True, (note or None)
    if s == 'Attunement Optional': return False, 'Optional'
    return False, None

def rar(r):
    r = (r or '').lower()
    return {'unknown (magic)': 'unknown', 'varies': 'var'}.get(r, r)

key_taken = set()
def choose_key(e, olds):
    gen = [ok for ok, ver, base in olds if ver is None and base is None and ok not in key_taken]
    pref = [ok for ok in gen if M['map'][ok]['how'] in ('name', 'manual', 'renamed')]
    for ok in pref + gen:
        key_taken.add(ok); return ok, True
    base = slug(e['name']) or 'item'
    if e['source'] == 'AU' and not base.startswith('au_'): base = 'au_' + base
    kk = base; i = 2
    while kk in key_taken or kk in ALL_OLD_KEYS: kk = '%s_%d' % (base, i); i += 1
    key_taken.add(kk); return kk, False

def vbonus(v):
    return v.get('bonus') if isinstance(v.get('bonus'), int) else None

out_magic, out_au = [], []
aliases = {}
for e in E:
    if e['kind'] != 'magic': continue
    olds = by_entry.get(e['id'], [])
    key, reused = choose_key(e, olds)
    vers = e.get('versions') or []
    base_cat = e.get('baseCat') or next((v.get('baseCat') for v in vers if v.get('baseCat')), None)
    if not base_cat:
        bl = e.get('bases') or next((v.get('bases') for v in vers if v.get('bases')), None) or []
        if bl: base_cat = {'weapon': 'Weapon', 'armour': 'Armor', 'shield': 'Shield', 'ammo': 'Ammunition'}.get(BASES.get(bl[0]['name'], {}).get('kind'))
    fixed = e.get('fixedBase')
    if not fixed and vers and all(v.get('fixedBase') for v in vers) and len({v['fixedBase'] for v in vers}) == 1: fixed = vers[0]['fixedBase']
    ctype = e['csvType'] if e['csvType'] not in ('', 'Generic Variant') else (vers[0].get('csvType') if vers and vers[0].get('csvType') else e['csvType'])
    isW, isA, isAm = flags(ctype, base_cat)
    att, note = attune(e['attunement'] if not vers else (vers[0].get('attunement') or e['attunement']))
    d = {'key': key, 'name': e['name'], 'rarity': rar(e['rarity']), 'type': sheet_type(ctype, fixed, base_cat),
         'desc': e['desc'] if not vers else (e['desc'] or vers[0].get('desc') or ''),
         'attunement': att, 'attunementNote': note, 'isWeapon': isW, 'isArmour': isA, 'isAmmo': isAm,
         'source': e['source'], 'page': e['page'] if e['page'] not in ('', 'undefined', '0') else None,
         'weight': wt(e['weight']), 'value': e['value'] or None, 'csvType': clean(e['csvType'])}
    if e.get('alsoIn'): d['alsoIn'] = e['alsoIn']
    if e.get('groupTail'): d['descTail'] = e['groupTail']
    if fixed: d['fixedBase'] = fixed
    # versions
    if vers:
        vs = []
        for v in vers:
            va, vn = attune(v.get('attunement') or '')
            o = {'id': v['id'], 'label': v.get('label') or v['name'], 'name': v['name'], 'rarity': rar(v['rarity'])}
            if vbonus(v) is not None: o['bonus'] = v['bonus']
            if va != att or vn != note: o['attunement'] = va; o['attunementNote'] = vn
            if v.get('desc') and v['desc'] != d['desc']: o['desc'] = v['desc']
            if v.get('fixedBase') and v['fixedBase'] != fixed: o['fixedBase'] = v['fixedBase']
            vs.append(o)
        d['versions'] = vs
        rs = {o['rarity'] for o in vs}
        d['rarity'] = 'var' if len(rs) > 1 else rs.pop()
    # bases: union over versions, with the CSV's own name for each (version, base)
    rows = {}; brar = {}; batt = {}; bnames = []
    for v in [None] + list(vers):
        src = (v or e).get('bases') or []
        vid = v['id'] if v else ''
        for b in src:
            if b['name'] not in bnames: bnames.append(b['name'])
            rows[vid + '|' + b['name']] = b['row']
            vr = rar(b['rarity']); want = rar(v['rarity']) if v else d['rarity']
            if vr != want: brar[vid + '|' + b['name']] = vr
            ba, bn = attune(b['attunement'])
            wa = att if not v else attune(v.get('attunement') or '')[0]
            if ba != wa: batt[vid + '|' + b['name']] = [ba, bn]
    if vers and not e.get('bases'):
        rows = {kk: vv for kk, vv in rows.items() if not kk.startswith('|')}
    if bnames:
        d['bases'] = bnames
        d['baseRows'] = rows
        if brar: d['baseRarity'] = brar
        if batt: d['baseAttune'] = batt
        if len({rar(x) for x in brar.values()} | {d['rarity']}) > 1 and d['rarity'] != 'var' and not vers:
            d['rarity'] = 'var'
    # wiring carried over from the old entries
    oldobjs = [(OLDBYKEY.get(ok) or OLDAUBYKEY.get(ok), ver, base) for ok, ver, base in olds]
    oldobjs = [x for x in oldobjs if x[0]]
    rep = next((o for o, ver, base in oldobjs if ver is None and base is None), None) or (oldobjs[0][0] if oldobjs else None)
    if rep:
        for f in WIRE:
            if rep.get(f) not in (None, [], {}): d[f] = rep[f]
        if rep.get('dmOnly') is not None or True:
            d['dmOnly'] = all(bool(o.get('dmOnly')) for o, _, _ in oldobjs)
        if not rep.get('dmOnly') and rep.get('source') in ('Homebrew',): pass
    else:
        d['dmOnly'] = True
    if d.get('dmOnly') is False: d.pop('dmOnly')
    # numeric versions: effects become 'variable' (driven by the chosen +N)
    if vers and any('bonus' in o for o in d['versions']):
        fx = dict(d.get('effects') or {})
        fxv = [o.get('effects') for o, ver, base in oldobjs if ver is not None and o.get('effects')]
        for f in ('weaponBonus', 'acBonus', 'spellAtkBonus', 'spellDCBonus', 'otherBonus'):
            if any(isinstance(x, dict) and f in x for x in fxv) or f in fx: fx[f] = 'variable'
        if not fx and (isW or isA): fx['weaponBonus'] = 'variable'
        if isA and 'acBonus' in fx: fx['weaponBonus'] = 'variable'; fx.pop('acBonus')   # +N armour/shields keep their bonus in weaponBonus (acBonus 'variable' was added as text)
        d['effects'] = fx or None
        d['rarityByBonus'] = {str(o['bonus']): o['rarity'] for o in d['versions'] if 'bonus' in o}
        d.pop('tiers', None)
    # named versions: per-version effects from old tiers / old per-version entries
    if vers and not any('bonus' in o for o in d['versions']):
        tiers = (rep or {}).get('tiers') or {}
        for o in d['versions']:
            t = next((t for t in tiers.values() if k(t.get('name')) == k(o['name'])), None)
            if t and t.get('effects'): o['effects'] = t['effects']
            src = next((ob for ob, ver, base in oldobjs if ver == o['id'] and ob.get('effects')), None)
            if src and 'effects' not in o and src['effects'] != d.get('effects'): o['effects'] = src['effects']
            src = next((ob for ob, ver, base in oldobjs if ver == o['id']), None)
            if src:
                for f in ('charges', 'grantedSpells', 'grantedResources', 'dmgres', 'resistanceOptions'):
                    if src.get(f) not in (None, [], {}) and src.get(f) != d.get(f): o[f] = src[f]
        d.pop('tiers', None)
    if d.get('effects') is None: d['effects'] = None
    # Spell Scroll keeps the sheet's own spell/level picker, and its per-level entries (the
    # spell-scroll feature reads each level's save DC / attack bonus from them)
    if e['name'] == 'Spell Scroll' and d.get('versions'):
        lv_entries = []
        for v in d.pop('versions'):
            m = re.match(r'^Spell Scroll \((Cantrip|Level (\d))\)$', v['name'])
            if not m: continue
            vk = 'spell_scroll_cantrip' if m.group(1) == 'Cantrip' else 'spell_scroll_level_' + m.group(2)
            ve = {kk: vv for kk, vv in d.items() if kk not in ('key', 'name', 'rarity', 'desc', 'rarityByBonus')}
            ve.update({'key': vk, 'name': v['name'], 'rarity': v['rarity'], 'desc': v.get('desc') or d['desc']})
            old_lv = OLDBYKEY.get(vk)
            if old_lv is not None:
                for f in WIRE:
                    if old_lv.get(f) not in (None, [], {}): ve[f] = old_lv[f]
                if not old_lv.get('dmOnly'): ve.pop('dmOnly', None)
                else: ve['dmOnly'] = True
            key_taken.add(vk); lv_entries.append(ve)
        out_magic.extend(lv_entries)
        olds = [o for o in olds if o[0] not in {x['key'] for x in lv_entries}]
        d['rarity'] = 'var'
    # aliases for old keys that now point here
    for ok, ver, base in olds:
        if ok == key and ver is None and base is None: continue
        aliases[ok] = [key, ver, base]
    (out_au if e['source'] == 'AU' else out_magic).append(d)
    REPORT['kept_key' if reused else 'new_key'].append(key)

# delerium crystals: the CSV names them just "Chip", "Shard" ... - keep the sheet's names
for d in out_magic:
    pass
DELERIUM = {'Chip': 'Delerium Crystal (Chip)', 'Fragment': 'Delerium Crystal (Fragment)', 'Shard (MoDk)': 'Delerium Crystal (Shard)',
            'Crystal (MoDk)': 'Delerium Crystal (Crystal)', 'Geode': 'Delerium Crystal (Geode)', 'Massive Cluster': 'Delerium Crystal (Massive Cluster)'}

# mundane entries that the sheet held as magic items (delerium crystals) stay in the magic catalogue
for e in E:
    if e['kind'] == 'magic': continue
    olds = by_entry.get(e['id'], [])
    if not olds: continue
    ok = olds[0][0]; ob = OLDBYKEY.get(ok)
    if not ob: continue
    d = dict(ob)
    d['name'] = DELERIUM.get(e['name'], e['name']); d['source'] = e['source']
    d['desc'] = e['desc']
    d['weight'] = wt(e['weight']) or ob.get('weight'); d['value'] = e['value'] or None; d['rarity'] = 'common' if ob.get('rarity') else 'none'
    d['rarity'] = ob.get('rarity') or 'none'
    d['csvType'] = clean(e['csvType'])
    key_taken.add(ok)
    out_magic.append(d)
    for ok2, ver, base in olds[1:]: aliases[ok2] = [ok, ver, base]
    REPORT['mundane_kept_as_magic'].append(d['name'])

# homebrew: old items with no CSV match stay, flagged - except those the user removed (27 Oct)
REMOVED = {'transmuter_s_stone', 'potent_transmuter_s_stone', 'arcane_propulsion_armor', 'armor_of_magical_strength',
           'enhanced_arcane_focus___1_or__2', 'radiant_weapon', 'lost_sword', 'galder_s_bubble_pipe', 'heward_s_hireling_armor',
           'leather_golem_armor', 'spellcasting_bolts', 'ancient_relic_boulder', 'ring_of_hardened_magma'}
for x in OLD + OLD_AU:
    if x['key'] in M['map']: continue
    if x['key'] in REMOVED: REPORT['removed'].append(x['name']); continue
    if x['key'] in key_taken: continue
    d = dict(x)
    if x['key'] != 'genies_vessel':
        d['homebrew'] = True
        d['oldSource'] = x.get('source')
        d['source'] = 'Homebrew'
        REPORT['homebrew'].append('%s (%s)' % (x['name'], x.get('source')))
    key_taken.add(x['key'])
    (out_au if x in OLD_AU else out_magic).append(d)

# AU: keep dmOnly from the old AU list (the user's own flags)
for d in out_au:
    o = OLDAUBYKEY.get(d['key'])
    if o is not None:
        if o.get('dmOnly'): d['dmOnly'] = True
        else: d.pop('dmOnly', None)

# ════════════════════════════════════════════════════════ mundane gear / valuables / mounts
gear_names = {k(g['name']): g for g in G}
val_names = {k(v['name']): v for v in VAL}
mnt_names = {k(v['name']): v for v in MNT}
GEAR_ADD, GEAR_SET, VAL_ADD, VAL_SET, MNT_ADD, MNT_SET = [], {}, [], {}, [], {}
def gear_cat(ctype):
    c = re.sub(r'\s*\(.*', '', clean(ctype).split(',')[0]).strip()
    return {'Trade Bar': 'Trade Good'}.get(c, c) or 'Other'
for e in E:
    if e['kind'] in ('magic', 'weapon', 'armour'): continue
    if by_entry.get(e['id']) and any(OLDBYKEY.get(ok) for ok, _, _ in by_entry[e['id']]): continue   # held as magic item
    nm = k(e['name'])
    cat = gear_cat(e['csvType'])
    if e['kind'] == 'gear':
        g = gear_names.get(nm)
        if g:
            ch = {}
            if e['desc'] and e['desc'] != g.get('desc'): ch['desc'] = e['desc']
            if e['value'] and e['value'] != g.get('value'): ch['value'] = e['value']
            if wt(e['weight']) and (g.get('weight') or '').rstrip('.') != wt(e['weight']): ch['weight'] = e['weight']
            if ch: GEAR_SET[g['key']] = ch
        elif 'Multiple variations of this item exist' in (e['desc'] or ''):
            REPORT['group_headings_not_gear'].append(e['name'])   # e.g. "Musical Instrument": a heading, not an item
        elif cat == 'Ammunition':
            REPORT['ammo_not_gear'].append(e['name'])      # the sheet tracks ammunition in its ammo tracker
        else:
            GEAR_ADD.append({'key': slug(e['name']) if slug(e['name']) not in {x['key'] for x in G} else slug(e['name'] + ' ' + e['source']),
                             'name': e['name'], 'category': cat, 'weight': e['weight'] or None, 'value': e['value'] or None,
                             'desc': e['desc'], 'source': e['source']})
    elif e['kind'] == 'valuable':
        v = val_names.get(nm)
        if v:
            ch = {}
            if e['desc'] and e['desc'] != v.get('desc') and not e['desc'].startswith('Treasure ('): ch['desc'] = e['desc']
            if e['value'] and e['value'] != v.get('value'): ch['value'] = e['value']
            if ch: VAL_SET[v['key']] = ch
        else:
            c2 = re.search(r'\((.*?)\)', e['csvType']); c2 = c2.group(1) if c2 else cat
            VAL_ADD.append({'key': slug(e['name']), 'name': e['name'], 'category': c2 if c2 in ('Gemstone', 'Art Object') else 'Trade Good',
                            'value': e['value'] or None, 'weight': e['weight'] or None, 'desc': e['desc'], 'source': e['source']})
    elif e['kind'] == 'mount':
        v = mnt_names.get(nm)
        if v:
            ch = {}
            if e['desc'] and e['desc'] != v.get('desc'): ch['desc'] = e['desc']
            if e['value'] and e['value'] != v.get('value'): ch['value'] = e['value']
            if ch: MNT_SET[v['key']] = ch
        else:
            c2 = e['csvType'].split(',')[0].strip()
            MNT_ADD.append({'key': slug(e['name']), 'name': e['name'], 'category': c2 if c2.startswith('Vehicle') or c2 == 'Mount' else 'Mount',
                            'value': e['value'] or None, 'weight': e['weight'] or None, 'desc': e['desc'], 'source': e['source']})
# squashed tables in gear text (28 Oct), same rebuild as the magic items
import tables as _gtables
for g in G:
    t = (GEAR_SET.get(g['key']) or {}).get('desc') or g.get('desc') or ''
    new, n = _gtables.rebuild_text(g['key'], t)
    if n: GEAR_SET.setdefault(g['key'], {})['desc'] = new
for g in GEAR_ADD:
    new, n = _gtables.rebuild_text(g['key'], g.get('desc') or '')
    if n: g['desc'] = new
# unique keys
for L, old in ((GEAR_ADD, G), (VAL_ADD, VAL), (MNT_ADD, MNT)):
    seen = {x['key'] for x in old}
    for x in L:
        b = x['key']; i = 2
        while x['key'] in seen: x['key'] = '%s_%d' % (b, i); i += 1
        seen.add(x['key'])

REPORT['star_rows_folded'] = [n for _, _, n in STAR_DROPPED]
# layout repairs for lists/tables the CSV squashed together (words unchanged)
sys.path.insert(0, B + 'tools'); from ifix import fix_text
_inv = collections.defaultdict(list)
for ok, v in aliases.items(): _inv[v[0]].append(ok)
FIXN = collections.Counter()
for d in out_magic + out_au:
    if d.get('homebrew') and d['key'] != 'x': continue
    olds = [OLDBYKEY.get(k2) or OLDAUBYKEY.get(k2) for k2 in [d['key']] + _inv.get(d['key'], [])]
    old_t = next((o.get('desc') for o in olds if o and '|' in (o.get('desc') or '')), None)
    d['desc'], notes = fix_text(d.get('desc', ''), old_t)
    for n_ in notes: FIXN[n_] += 1
    for v in d.get('versions') or []:
        if v.get('desc'):
            v['desc'], notes = fix_text(v['desc'], old_t)
            for n_ in notes: FIXN[n_] += 1
    if any('left as in' in n_ for n_ in notes): REPORT['tables_left'].append(d['name'])
REPORT['text_fixes'] = dict(FIXN)
# ════════════════════════════════════════════════════════ item effects (stage 2)
sys.path.insert(0, B + 'tools'); import ifx as IFX
_SP = json.load(open(SD + 'PHB_SPELL_LIST.json'))
SPELL_NAMES = {x['name'].lower(): x['name'] for x in _SP}
# older books name some spells without their wizard ("black tentacles", "acid arrow", "tiny hut")
for _nm in list(SPELL_NAMES.values()):
    _m = re.match(r"([A-Z][\w-]+)'s (.+)$", _nm)
    if _m and _m.group(1) not in ('Hunter', 'Dragon', 'Crusader', 'Fortune') and len(_m.group(2).split()) >= 2 and _m.group(2).lower() not in SPELL_NAMES:
        SPELL_NAMES[_m.group(2).lower()] = _nm
def _dedupe(fx, d):
    E = d.get('effects') or {}
    drop = {'ac': 'acBonus', 'saveBonus': 'saveBonus', 'scores': 'scoresOverride', 'wBonus': 'weaponBonus', 'armourBonus': 'weaponBonus',
            'spellAtk': 'spellAtkBonus', 'spellDC': 'spellDCBonus', 'advSaves': 'advSaves', 'advChecks': 'advChecks'}
    for f, ef in drop.items():
        if f in fx and E.get(ef) not in (None, 0, [], ''): fx.pop(f)
    if 'armourBonus' in fx and E.get('acBonus'): fx.pop('armourBonus')
    if 'acIf' in fx and (E.get('acBonus') not in (None, 0, '') or (d.get('isArmour') and E.get('weaponBonus') not in (None, 0, ''))): fx.pop('acIf')
    if 'ac' in fx and d.get('isArmour') and E.get('weaponBonus') not in (None, 0, ''): fx.pop('ac')
    if 'allAtk' in fx and E.get('weaponBonus') not in (None, 0, ''): fx.pop('allAtk')
    if 'skillAdv' in fx and E.get('skillAdvantage'):
        fx['skillAdv'] = [x for x in fx['skillAdv'] if x != str(E['skillAdvantage']).lower()] or None
        if not fx['skillAdv']: fx.pop('skillAdv')
    if 'resist' in fx and (d.get('dmgres') or d.get('resistanceOptions')): fx.pop('resist')
    return fx
def _fx_of(r, d, passive_only=False):
    out = {}
    pp = _dedupe(dict(r['p']), d)
    if pp: out['p'] = pp
    if r['u'] and not passive_only: out['u'] = r['u']
    if r['notes']: out['notes'] = r['notes']
    return out
FXSTAT = collections.Counter(); PROBE = {}
for d in out_magic + out_au:
    r = IFX.extract(d.get('desc', ''), d, SPELL_NAMES)
    fx = _fx_of(r, d)
    labels = list(r['found'])
    for v in d.get('versions') or []:
        if not v.get('desc'): continue
        rv = IFX.extract(v['desc'], d, SPELL_NAMES)
        fv = _fx_of(rv, d)
        if fv: v['fx'] = fv; labels += ['[%s] %s' % (v.get('label') or v['name'], x) for x in rv['found']]
        if rv['charges'] and not v.get('charges') and not d.get('charges'):
            v['charges'] = {'max': rv['charges']['max'], 'recovery': rv['charges'].get('recovery', 'dawn'), **({'recoveryNote': '; '.join(x for x in (('regains ' + rv['charges']['regain']) if rv['charges'].get('regain') else '', rv['charges'].get('note', '')) if x)} if rv['charges'].get('regain') or rv['charges'].get('note') else {})}
        for sp in rv['spells']:
            gs = v.setdefault('grantedSpells', list(d.get('grantedSpells') or []))
            if not any((g.get('spellName') or '').lower() == sp['spellName'].lower() for g in gs): gs.append(sp)
    if fx: d['fx'] = fx
    if r['charges'] and not d.get('charges'):
        c = r['charges']; d['charges'] = {'max': c['max'], 'recovery': c.get('recovery', 'dawn'), **({'recoveryNote': '; '.join(x for x in (('regains ' + c['regain']) if c.get('regain') else '', c.get('note', '')) if x)} if c.get('regain') or c.get('note') else {})}
        FXSTAT['charges added'] += 1
    for sp in r['spells']:
        gs = d.setdefault('grantedSpells', [])
        if not any((g.get('spellName') or '').lower() == sp['spellName'].lower() for g in gs): gs.append(sp); FXSTAT['spells added'] += 1
    if not d.get('grantedSpells'): d.pop('grantedSpells', None)
    if r['req']: d['attuneReq'] = r['req']
    existing = [k2 for k2 in ('effects', 'charges', 'grantedSpells', 'dmgres', 'resistanceOptions', 'grantedResources') if d.get(k2)]
    PROBE[d['key']] = {'name': d['name'], 'found': labels + (['spells: ' + ', '.join(g['spellName'] for g in d.get('grantedSpells') or [])] if d.get('grantedSpells') else []),
                       'existing': existing, 'notes': r['notes'], 'req': (r['req'] or {}).get('text')}
    for x in labels: FXSTAT[x.split(' ')[0]] += 1
REPORT['fx_stats'] = dict(FXSTAT.most_common(40))
json.dump(PROBE, open(B + 'fx_probe.json', 'w'), indent=0, ensure_ascii=False)
# Sweep 2: weapons with no weapon type never reached the Attacks list (staffs became weapons in stage 1; one-off
# magic weapons). Staffs (CSV: 1d6 bludgeoning, versatile) are quarterstaffs; one-offs take the standard weapon
# with the same damage dice; the few with no match are left to the player's weapon pick.
WEAPON_FOR = {'au_blade_of_the_guardian': 'Greatsword', 'darts_of_the_macaw': 'Dart', 'hooked_shortspear': 'Dagger', 'iron_ball': 'Light Hammer',
              'light_repeating_crossbow': 'Light Crossbow', 'mind_lash': 'Whip', 'poison_soaked_kukri': 'Dagger', 'raven_s_feather': 'Greatsword',
              'silver_sword': 'Greatsword', 'saint_markovia_s_thighbone': 'Mace', 'skysail': 'Quarterstaff',
              'sussur_dagger': 'Dagger', 'the_lucky_marksman': 'Revolver'}
# Homebrew items (the user's own, not DM-edited), reviewed 27 Oct against their own text
for d in out_magic + out_au:
    if d['key'] == 'the_lucky_marksman':   # 2d8 radiant only on a "Heads" ricochet that costs a charge - not every hit
        d['fx'] = {'p': {'wNotes': ['+2d8 Radiant (Ricochet, Heads: expend 1 charge)']}}
    elif d['key'] == 'sussur_dagger':
        d['fx'] = {'p': {'wNotes': ['on a hit: Constitution save (your save DC) or Silenced until the end of its next turn']}}
    elif d['key'] == 'unstable_feywild_crystal' and not d.get('grantedResources'):
        d['grantedResources'] = [{'name': 'Feywild Chance', 'desc': 'Gain Advantage on one d20 Test. Regained early by rolling on the Wild Magic Surge table right after casting a spell with a spell slot (1 + Proficiency Bonus times per Long Rest).', 'usesMax': 1, 'recovery': 'long'}]
# Squashed tables (28 Oct): Items.csv lost every table's cell breaks; rebuilt as markdown tables, word for word
import tables as _tables
for d in out_magic + out_au:
    for o in [d] + list(d.get('versions') or []):
        if o.get('desc'):
            o['desc'], _n = _tables.rebuild_text(d['key'], o['desc'])
            if _n: FXSTAT['tables rebuilt'] += _n
# Book items whose DM edits the user retired on 28 Oct: the book entry carries the wiring those edits had
for d in out_magic + out_au:
    k = d['key']
    if k == 'candle_of_invocation':
        d['fx'] = {'p': {}, 'u': {'advSaves': ['all'], 'advChecks': ['str', 'dex', 'con', 'int', 'wis', 'cha']}, 'notes': ["Use while you are in the lit candle's light: Advantage on D20 Tests; a Cleric or Druid in the light can cast level 1 spells they have prepared without expending spell slots"]}
        d['grantedSpells'] = [{'spellName': 'Gate', 'grantType': 'limited', 'usesMax': 1, 'recovery': 'none', 'note': 'when first lit; destroys the candle'}]
    elif k == 'amulet_of_the_planes':
        d['grantedSpells'] = [{'spellName': 'Plane Shift', 'grantType': 'atWill', 'note': 'after a DC 15 Intelligence (Arcana) check'}]
    elif k == 'bloodwell_vial':
        d['grantedResources'] = [{'name': 'Bloodwell: regain 5 Sorcery Points', 'desc': 'When you roll any Hit Dice to recover Hit Points while carrying the vial, you can regain 5 Sorcery Points.', 'usesMax': 1, 'recovery': 'dawn'}]
    elif k == 'trollblood_potion':
        d['fx'] = {'notes': ['When drunk: regain 5 Hit Points at the start of each of your turns for 1 minute (ends early if you take Fire or Acid damage)']}
    elif k == 'au_thayan_sword':
        d['charges'] = {'max': 4, 'recovery': 'dawn', 'recoveryNote': 'regains 1d4'}
        d['grantedSpells'] = [{'spellName': n, 'grantType': 'itemCharges', 'chargeCost': 1, 'fixedDC': 15} for n in ('Searing Smite', 'Thunderous Smite', 'Wrathful Smite')]
        d['grantedResources'] = [{'name': 'Resurgent Warrior', 'desc': "If you're reduced to 0 Hit Points but not killed outright while holding this sword, you can drop to 1 Hit Point instead.", 'usesMax': 1, 'recovery': 'dawn'}]
        d['desc'] = d['desc'].replace('Searing SmiteThunderous SmiteWrathful Smite Resurgent Warrior.', '- Searing Smite\n- Thunderous Smite\n- Wrathful Smite\n\nResurgent Warrior.')
# Gi of Shifting Seasons (28 Oct): the wearer picks the season; each season's benefits only while it's that season
GI_MODES = {'label': 'Season', 'list': [
    {'id': 'winter', 'name': 'Winter', 'p': {'flurryNote': 'Gi (Winter): each creature you hit loses 5 ft of Speed (to a minimum of 15 ft) until the start of your next turn'}, 'notes': ['Winter: you are immune to the effects of extreme cold', "Winter: when you hit a creature with an attack from Flurry of Blows, its speed is reduced by 5 feet (to a minimum of 15 feet) until the start of your next turn"]},
    {'id': 'spring', 'name': 'Spring', 'p': {}, 'enter': {'tempHP': '1d4+4'}, 'notes': ['Spring: when the gi changes to Spring, you gain 1d4 + 4 Temporary Hit Points (added when you pick it here)', 'Spring: when you use Step of the Wind, your jump distance is tripled instead of doubled, and you ignore difficult terrain until the end of your turn']},
    {'id': 'summer', 'name': 'Summer', 'p': {'unarmedDmg': '2 Fire', 'unarmedNotes': ['Gi (Summer): 3 Fire instead of 2 when you are outside during the day']}, 'notes': ['Summer: you are immune to the effects of extreme heat', 'Summer: your unarmed strikes deal an extra 2 Fire damage on a hit (3 instead if you are outside during the day)']},
    {'id': 'autumn', 'name': 'Autumn', 'p': {'advSaves': ['con']}, 'notes': ['Autumn: when you use Patient Defense, creatures provoke an Opportunity Attack from you when they move within 5 feet of you until the start of your next turn']},
]}
for d in out_magic + out_au:
    if d['key'] == 'gi_of_shifting_seasons':
        d['fx'] = {'modes': GI_MODES, 'notes': ["Change season: 1 minute of silent meditation, or move one season on (Winter > Spring > Summer > Autumn) whenever you spend ki with an action, bonus action or reaction"]}
# fx notes cut short by the reader: use the whole sentence from the item's own text
def _whole(note, text):
    pre = re.match(r'^((?:conditional [a-z ]+|permanent increase when used):\s*)', note, re.I)
    body = note[pre.end():] if pre else note
    if not body or not text: return note
    flat = re.sub(r'\s+', ' ', text)
    i = flat.find(body.strip()[:60])
    if i < 0: return note
    j = flat.find('. ', i + len(body.strip()) - 1)
    end = len(flat) if j < 0 else j + 1
    return (pre.group(1) if pre else '') + flat[i:end].strip()
for d in out_magic + out_au:
    for o in [d] + list(d.get('versions') or []):
        fx = o.get('fx') or {}
        if fx.get('notes'): fx['notes'] = [_whole(n, o.get('desc') or d.get('desc') or '') for n in fx['notes']]
# Dragon Mask (28 Oct): the colour is the version, so no separate colour pick; its wiring lives in module 43
for d in out_magic + out_au:
    if d['key'] == 'dragon_mask':
        for k in ('resistanceOptions', 'resistanceIsDragonColor'): d.pop(k, None)
        d.pop('fx', None)
        for v in d.get('versions') or []: v.pop('fx', None)
# Potion of Polymorphine (28 Oct): one item, rarity Varies, the grade is the version (old keys still find it)
_PM = [d for d in out_magic if d['key'].startswith('potion_of_polymorphine_')]
if _PM:
    _order = ['crude', 'refined', 'volatile', 'unstable', 'chaotic']
    _PM.sort(key=lambda d: _order.index(d['key'].rsplit('_', 1)[1]) if d['key'].rsplit('_', 1)[1] in _order else 99)
    g = {k: v for k, v in _PM[0].items() if k not in ('key', 'name', 'rarity', 'desc')}
    g.update({'key': 'potion_of_polymorphine', 'name': 'Potion of Polymorphine', 'rarity': 'var', 'desc': _PM[0]['desc'], 'versions': []})
    for i, d in enumerate(_PM):
        lab = re.search(r'\(([^)]+)\)', d['name']).group(1)
        v = {'id': lab, 'label': lab, 'name': d['name'], 'rarity': d['rarity']}
        if i: v['desc'] = d['desc']
        g['versions'].append(v)
        aliases[d['key']] = ['potion_of_polymorphine', lab, None]
    i0 = out_magic.index(_PM[0])
    out_magic = [d for d in out_magic if d not in _PM]
    out_magic.insert(min(i0, len(out_magic)), g)
# 28 Oct: every catalogue item is shown to players (the DM can still hide one from the DM panel)
_shown = 0
for d in out_magic + out_au:
    for o in [d] + list(d.get('versions') or []):
        if o.pop('dmOnly', None): _shown += 1
FXSTAT['made visible to players'] = _shown
# Aboleth Brain (homebrew): Devouring Urge on organic weapons
for d in out_magic + out_au:
    if d['key'] == 'aboleth_brain':
        fx = d.setdefault('fx', {}); fx.setdefault('p', {})
        fx['p']['organicNote'] = 'Devouring Urge (once per turn, on a hit): +1d6 Necrotic or Psychic; you can spend a Hit Die to regain its roll + Con modifier HP (min 1); the DM gives you a mutation for 1 minute'
NOBASE = []
for d in out_magic + out_au:
    if not d.get('isWeapon') or d.get('isAmmo') or d.get('bases') or d.get('fixedBase') or any(v.get('fixedBase') for v in d.get('versions') or []): continue
    w = WEAPON_FOR.get(d['key'])
    if not w and (str(d.get('type', '')).lower() == 'staff' or re.search(r'\bstaff\b', d['name'], re.I)): w = 'Quarterstaff'
    if w: d['fixedBase'] = w; FXSTAT['weapon type set'] += 1
    else: NOBASE.append(d['key'])
REPORT['weapons_without_type'] = NOBASE
# DM edits the user retired (27 Oct): these follow the CSV; they were visible to players, so they stay visible
RETIRED_DM_EDITS = ['1_shield', 'badge_of_the_savant_abjuration', 'dusk_dagger_rare', '1_rod_of_the_pact_keeper',
                    '2_rod_of_the_pact_keeper', '3_rod_of_the_pact_keeper', '3_arcane_grimoire', 'rod_of_the_pact_keeper___1___2__or__3']
for d in out_magic + out_au:
    if d['key'] in ('shield___1___2__or__3', 'rod_of_the_pact_keeper___1___2__or__3', 'arcane_grimoire', 'dusk_dagger', 'badge_of_the_savant'):
        d.pop('dmOnly', None)
# "Long Sword" -> "Longsword" (see the top): old keys and old copies' base point at the Longsword
for _k, _a in aliases.items():
    if _a and len(_a) > 2 and _a[2] in _FOLD: _a[2] = _FOLD[_a[2]]
for _f, _t in _FOLD.items():
    if _t in BASES: BASES[_f] = dict(BASES[_t])
patch = {'retiredDmEdits': RETIRED_DM_EDITS, 'magic': out_magic, 'au': out_au, 'aliases': aliases, 'bases': BASES,
         'newWeapons': NEW_WEAPONS, 'newArmour': NEW_ARMOUR, 'newAmmo': NEW_AMMO,
         'weaponSet': WEAPON_SET, 'armourSet': ARMOUR_SET,
         'gearAdd': GEAR_ADD, 'gearSet': GEAR_SET, 'valAdd': VAL_ADD, 'valSet': VAL_SET, 'mntAdd': MNT_ADD, 'mntSet': MNT_SET}
json.dump(patch, open(B + 'items_patch.json', 'w'), ensure_ascii=False)
REPORT_S = {kk: (len(v) if isinstance(v, list) else v) for kk, v in REPORT.items()}
json.dump(REPORT, open(B + 'igen_report.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps({'magic': len(out_magic), 'au': len(out_au), 'aliases': len(aliases), 'bases': len(BASES),
                  'newWeapons': len(NEW_WEAPONS), 'newArmour': len(NEW_ARMOUR), 'newAmmo': NEW_AMMO,
                  'weaponSet': len(WEAPON_SET), 'armourSet': len(ARMOUR_SET), 'gearAdd': len(GEAR_ADD), 'gearSet': len(GEAR_SET),
                  'valAdd': len(VAL_ADD), 'valSet': len(VAL_SET), 'mntAdd': len(MNT_ADD), 'mntSet': len(MNT_SET), **REPORT_S}, indent=1))
