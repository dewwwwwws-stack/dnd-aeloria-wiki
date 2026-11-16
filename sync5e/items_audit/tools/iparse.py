#!/usr/bin/env python3
"""Parse Items.csv into merged item entries.

Usage: iparse.py Items.csv OUT.json

One entry per magic item. Merges:
  * per-base copies ("Flame Tongue Longsword", "Flame Tongue Greatsword" ...) -> one entry with `bases`
  * +1/+2/+3 sets (same book, same text apart from the number) -> one entry with numeric `versions`
  * item groups ("Multiple variations of this item exist ...") whose members differ in rarity,
    or are magic -> one entry with named `versions`
Rarity becomes 'var' when the versions differ in rarity.
Duplicate names across books: identical text keeps the newest book; different items keep both,
named "Name (BOOK)".
"""
import csv, collections, re, json, sys

csv.field_size_limit(10**9)
SRC, OUT = sys.argv[1], sys.argv[2]
ROWS = list(csv.DictReader(open(SRC, encoding='utf-8-sig', newline='')))
for i, r in enumerate(ROWS): r['_i'] = i

PRE = re.compile(r'^The base item can be found in[^\n]*\n\n')
GROUP = re.compile(r'Multiple variations of this item exist, as listed below:\s*(.*?)(?:\n\n|$)', re.S)
BASELIST = re.compile(r'\s*Base items\. This item variant can be applied to the following base items:.*$', re.S)

def norm(t): return re.sub(r'\s+', ' ', t or '').strip()

def split_type(t):
    """'Weapon (Hand Crossbow (Wooden Bolts)), Martial Weapon' -> ('Weapon', 'Hand Crossbow (Wooden Bolts)', ['Martial Weapon'])"""
    t = t.strip()
    m = re.match(r'^([^,(]*)\(', t)
    if not m:
        parts = [p.strip() for p in t.split(',')]
        return parts[0], None, parts[1:]
    depth = 0
    for j in range(m.end() - 1, len(t)):
        if t[j] == '(': depth += 1
        elif t[j] == ')':
            depth -= 1
            if depth == 0: break
    inner = t[m.end():j]
    rest = [p.strip() for p in t[j+1:].split(',') if p.strip()]
    return m.group(1).strip(), inner, rest

BYNAME = collections.defaultdict(list)
for r in ROWS: BYNAME[r['Name']].append(r)
NAMES_LONGEST = sorted(BYNAME, key=len, reverse=True)
NAMES_CI = {n.lower(): n for n in BYNAME}

def is_gv(r): return 'Generic Variant' in r['Type']
def is_group(r): return bool(GROUP.search(r['Text']))
def base_of(r):
    if is_gv(r): return None
    c, b, rest = split_type(r['Type'])
    return b

def magic_text(r, base):
    """The item's own text, with the 'base item can be found' line and the base item's own text removed."""
    t = PRE.sub('', r['Text'])
    cands = [b for b in BYNAME.get(base, []) if b['Text']]
    for b in cands:
        if t.endswith(b['Text']): return t[:-len(b['Text'])].rstrip()
    for b in cands:
        bt = PRE.sub('', b['Text'])
        if bt and t.endswith(bt): return t[:-len(bt)].rstrip()
    # base text not present as its own row: the base's text is identical across the family, cut later
    return t

PLUS = re.compile(r'\+([123])\b')
def plus_key(s): return PLUS.sub('+N', re.sub(r'\b([123])\b(?=\s+bonus)', 'N', s))

# ---------------------------------------------------------------- per-base families
def cat_of(r):
    c, b, rest = split_type(r['Type'])
    if c in ('Weapon', 'Melee Weapon', 'Ranged Weapon'): return 'Weapon'
    if c in ('Light Armor', 'Medium Armor', 'Heavy Armor', 'Armor'): return 'Armor'
    return c

def common_prefix_paras(texts):
    ps = [t.split('\n\n') for t in texts]
    out = []
    for i in range(min(len(p) for p in ps)):
        if len({p[i] for p in ps}) == 1: out.append(ps[0][i])
        else: break
    return '\n\n'.join(out)

fam = collections.OrderedDict()
for r in ROWS:
    if is_gv(r) or is_group(r): continue
    b = base_of(r)
    if not b: continue
    r['_base'] = b
    r['_mt'] = magic_text(r, b)
    if r['Rarity'] == 'none':          # plain items (art objects, barding ...) stay one entry each
        fam[('M', r['_i'])] = [r]; continue
    i0 = r['Name'].lower().find(b.lower())
    tpl = (r['Name'][:i0] + '{base}' + r['Name'][i0+len(b):]) if i0 >= 0 else None
    if tpl and tpl.strip() != '{base}':
        key = ('T', r['Source'], cat_of(r), tpl)
    else:
        key = ('X', r['Source'], norm(r['_mt']))
    fam.setdefault(key, []).append(r)

# a family's own text: the paragraphs every member shares (each member ends with its base item's text)
for k, rs in fam.items():
    if len(rs) > 1:
        cp = common_prefix_paras([PRE.sub('', r['Text']) for r in rs])
        for r in rs: r['_mt'] = cp or r['_mt']

GV_BY_TEXT = collections.defaultdict(list)
GV_BY_NAME = collections.defaultdict(list)
for r in ROWS:
    if is_gv(r):
        GV_BY_TEXT[(r['Source'], norm(BASELIST.sub('', PRE.sub('', r['Text']))))].append(r)
        GV_BY_NAME[(r['Source'], r['Name'].lower())].append(r)

PLAIN_BY_NAME = collections.defaultdict(list)
for r in ROWS:
    if not is_gv(r) and not is_group(r) and not base_of(r):
        PLAIN_BY_NAME[(r['Source'], r['Name'].lower())].append(r)

def find_gv(key, rs):
    src = rs[0]['Source']
    if key[0] == 'T':
        tpl = key[3]
        cat = key[2]
        words = {'Weapon': ('Weapon', ''), 'Armor': ('Armor', ''), 'Ammunition': ('Ammunition', '')}.get(cat, (cat, ''))
        cands = [re.sub(r'\s+', ' ', tpl.replace('{base}', w)).strip(' ,') for w in words]
        for c in cands:
            g = GV_BY_NAME.get((src, c.lower()))
            if g: return g[0]
        for c in cands:
            g = PLAIN_BY_NAME.get((src, c.lower()))
            if g: return g[0]
    t = norm(rs[0]['_mt'])
    g = GV_BY_TEXT.get((src, t))
    if g: return g[0]
    # generic variant text may be a prefix of the member text (members add the base's text)
    for (s2, gt), gs in GV_BY_TEXT.items():
        if s2 == src and gt and len(gt) > 40 and t.startswith(gt): return gs[0]
    return None

entries = []          # final list
row_owner = {}        # row index -> entry id
def new_entry(**kw):
    e = dict(kw); e['id'] = len(entries); entries.append(e); return e

def fields(r):
    return dict(source=r['Source'], page=r['Page'], rarity=r['Rarity'], csvType=r['Type'],
                attunement=r['Attunement'], damage=r['Damage'], properties=r['Properties'],
                mastery=r['Mastery'], weight=r['Weight'], value=r['Value'])

def name_tpl(rs):
    """Find a template like '{base} of Retribution' that produces every member's name."""
    tpls = set()
    for r in rs:
        b = r['_base']; i0 = r['Name'].lower().find(b.lower())
        if i0 >= 0: tpls.add(r['Name'][:i0] + '{base}' + r['Name'][i0+len(b):])
        else: return None
    return tpls.pop() if len(tpls) == 1 else None

used_gv = {}
def base_rec(r):
    return {'name': r['_base'], 'row': r['Name'], 'rarity': r['Rarity'], 'attunement': r['Attunement'],
            'damage': r['Damage'], 'properties': r['Properties'], 'mastery': r['Mastery'], 'weight': r['Weight'],
            'csvType': r['Type']}
for fkey, rs in fam.items():
    gv = find_gv(fkey, rs)
    if gv is not None and gv['_i'] in used_gv:
        # another family (e.g. the ammunition half of "Adamantine Weapon") already made this entry: pool the bases
        e = entries[used_gv[gv['_i']]]
        e['bases'] += [base_rec(r) for r in rs]; e['rows'] += [r['Name'] for r in rs]
        if len({b['rarity'] for b in e['bases']}) > 1: e['rarityByBase'] = True
        for r in rs: row_owner[r['_i']] = e['id']
        continue
    if len(rs) == 1 and not gv:
        r = rs[0]
        e = new_entry(name=r['Name'], desc=PRE.sub('', r['Text']), rows=[r['Name']], fixedBase=r['_base'], **fields(r))
        row_owner[r['_i']] = e['id']; continue
    tpl = name_tpl(rs)
    cat, _, _ = split_type(rs[0]['Type'])
    if gv: name = gv['Name']
    elif tpl and tpl.endswith(' {base}') and re.search(r"(Blade|Sword|Axe|Bow|Hammer|Spear|Staff|Mace|Club)$", tpl[:-7]):
        name = tpl[:-7].strip()
    elif tpl and tpl.startswith('{base} ') and re.match(r"[A-Z]", tpl[7:]) : name = tpl[7:].strip()
    elif tpl: name = tpl.replace('{base}', {'Weapon': 'Weapon', 'Ammunition': 'Ammunition'}.get(cat, cat)).strip()
    else: name = rs[0]['Name']
    base0 = gv or rs[0]
    rar = collections.Counter(r['Rarity'] for r in rs)
    att = collections.Counter(r['Attunement'] for r in rs)
    e = new_entry(name=name, desc=(BASELIST.sub('', PRE.sub('', gv['Text'])) if gv else rs[0]['_mt']),
                  rows=[r['Name'] for r in rs] + ([gv['Name']] if gv else []),
                  bases=[base_rec(r) for r in rs],
                  nameTpl=tpl, baseCat=cat, **fields(base0))
    e['rarity'] = rar.most_common(1)[0][0] if not gv else gv['Rarity']
    if len(rar) > 1: e['rarityByBase'] = True
    e['attunement'] = (gv or rs[0])['Attunement']
    for r in rs: row_owner[r['_i']] = e['id']
    if gv: row_owner[gv['_i']] = e['id']; used_gv[gv['_i']] = e['id']

# remaining generic variants (no expansions found) and plain rows
for r in ROWS:
    if r['_i'] in row_owner or is_group(r): continue
    desc = BASELIST.sub('', PRE.sub('', r['Text'])) if is_gv(r) else PRE.sub('', r['Text'])
    e = new_entry(name=r['Name'], desc=desc, rows=[r['Name']], **fields(r))
    b = base_of(r)
    if b: e['fixedBase'] = b
    row_owner[r['_i']] = e['id']

# ---------------------------------------------------------------- +1/+2/+3 sets
alive = {e['id']: e for e in entries}
def plus_of(e):
    m = PLUS.search(e['name'])
    return int(m.group(1)) if m else None
sets = collections.defaultdict(list)
for e in entries:
    p = plus_of(e)
    if p is None: continue
    sets[(e['source'], plus_key(e['name']), (e['csvType'] or '').split(',')[0].split('(')[0].strip())].append(e)
for k, es in sets.items():
    ps = sorted({plus_of(e) for e in es})
    if len(es) < 2 or len(ps) != len(es): continue
    es.sort(key=plus_of)
    first = es[0]
    m = dict(first)
    m['id'] = len(entries)
    m['name'] = PLUS.sub(lambda mm: '+' + '/+'.join(str(p) for p in ps), first['name'], count=1)
    m['versions'] = [{'id': str(plus_of(e)), 'bonus': plus_of(e), 'label': '+%d' % plus_of(e), 'name': e['name'],
                      'rarity': e['rarity'], 'attunement': e['attunement'], 'desc': e['desc'],
                      'bases': e.get('bases'), 'rows': e['rows']} for e in es]
    m['rows'] = [n for e in es for n in e['rows']]
    rars = {v['rarity'] for v in m['versions']}
    m['rarity'] = 'var' if len(rars) > 1 else rars.pop()
    m['desc'] = first['desc']
    entries.append(m)
    for e in es: e['_mergedInto'] = m['id']

# ---------------------------------------------------------------- item groups
def entry_of_name(n):
    rs = BYNAME.get(n)
    if not rs: return None
    e = entries[row_owner[rs[0]['_i']]] if rs[0]['_i'] in row_owner else None
    while e is not None and '_mergedInto' in e: e = entries[e['_mergedInto']]
    return e

def split_members(s):
    out, i = [], 0
    while i < len(s):
        if s[i] in ' \n': i += 1; continue
        for n in NAMES_LONGEST:
            if s.startswith(n, i) or s[i:i+len(n)].lower() == n.lower():
                out.append(NAMES_CI[s[i:i+len(n)].lower()] if s[i:i+len(n)].lower() in NAMES_CI else n); i += len(n); break
        else:
            return out, s[i:]
    return out, ''

BOOK_YEAR = {"DMG'24": 2024, "PHB'24": 2024, "GH:CG'24": 2024, "GH:MG'24": 2024.1, "TGS1'24": 2024, 'TGS2': 2023,
             'TGS3': 2023, 'WttHC': 2022, 'XGE': 2017, 'CoA': 2024, 'MoDk': 2023, 'FRHoF': 2025, 'AI': 2019,
             'CoS': 2016, 'EET': 2015, 'AU': 2024.5, 'EGW': 2020, 'TDCSR': 2022, 'WDH': 2018}
group_report = []
for r in sorted(ROWS, key=lambda r: -BOOK_YEAR.get(r['Source'], 2000)):
    if not is_group(r): continue
    m = GROUP.search(r['Text'])
    members, rest = split_members(m.group(1).strip())
    own = r['Text'][:m.start()].strip()
    tail = r['Text'][m.end():].strip()
    mem_entries = []
    for n in members:
        e = entry_of_name(n)
        if e is not None and e not in mem_entries: mem_entries.append(e)
    rars = {e['rarity'] for e in mem_entries}
    magic = any(e['rarity'] not in ('none',) for e in mem_entries)
    info = {'group': r['Name'], 'source': r['Source'], 'members': members, 'unparsed': rest[:80]}
    if (not mem_entries) or (not magic):
        e = new_entry(name=r['Name'], desc=PRE.sub('', r['Text']), rows=[r['Name']], **fields(r))
        row_owner[r['_i']] = e['id']; info['action'] = 'kept as its own entry (members are mundane / not found)'
        group_report.append(info); continue
    if len(mem_entries) == 1 and mem_entries[0].get('versions'):
        # e.g. "Rod of the Pact Keeper" -> already the +1/+2/+3 set: give the set the group's name
        tgt = mem_entries[0]
        if tgt.get('groupName'):
            tgt['rows'].append(r['Name']); tgt.setdefault('alsoIn', []).append(r['Source'])
            row_owner[r['_i']] = tgt['id']; info['action'] = 'same group as %s (%s): kept as another name for it' % (tgt['name'], tgt['source'])
            group_report.append(info); continue
        tgt['groupName'] = r['Name']; tgt['name'] = r['Name']; tgt['rows'].append(r['Name'])
        tgt['source'] = r['Source']; tgt['page'] = r['Page']
        if own: tgt['groupDesc'] = own
        row_owner[r['_i']] = tgt['id']; info['action'] = 'named the +N set'
        group_report.append(info); continue
    g = fields(r)
    ge = new_entry(name=r['Name'], desc=own, groupTail=tail, rows=[r['Name']], **g)
    vers = []
    for e in mem_entries:
        if e.get('versions'):
            for v in e['versions']:
                vers.append(dict(v, id=v['name']))
        else:
            vers.append({'id': e['name'], 'label': e['name'], 'name': e['name'], 'rarity': e['rarity'],
                         'attunement': e['attunement'], 'desc': e['desc'], 'bases': e.get('bases'),
                         'fixedBase': e.get('fixedBase'), 'rows': e['rows'], 'csvType': e['csvType'],
                         'weight': e['weight'], 'value': e['value'], 'source': e['source']})
        e['_mergedInto'] = ge['id']
        ge['rows'] += e['rows']
    ge['versions'] = vers
    ge['groupName'] = r['Name']
    rr = {v['rarity'] for v in vers}
    ge['rarity'] = 'var' if len(rr) > 1 else rr.pop()
    if not own: ge['desc'] = ''
    # type/attunement from the members when the group row has none
    if ge['csvType'] in ('', 'Generic Variant'): ge['csvType'] = mem_entries[0]['csvType']
    row_owner[r['_i']] = ge['id']; info['action'] = 'merged into one entry'
    group_report.append(info)

# ---------------------------------------------------------------- "Name (Small)/(Large)" sets with different rarities
paren_report = []
pset = collections.defaultdict(list)
for e in entries:
    if '_mergedInto' in e or e.get('versions'): continue
    m = re.match(r'^(.*\S)\s+\(([^()]+)\)$', e['name'])
    if m: pset[(e['source'], m.group(1))].append(e)
for (src, stem), es in pset.items():
    if len(es) < 2 or len({e['rarity'] for e in es}) < 2: continue
    tgts = [x for x in entries if x['name'] == stem and x['source'] == src and '_mergedInto' not in x]
    if tgts and tgts[0].get('versions'): continue
    if tgts:
        ge = tgts[0]
    else: ge = new_entry(name=stem, desc='', rows=[], **{k2: es[0][k2] for k2 in ('source','page','rarity','csvType','attunement','damage','properties','mastery','weight','value')})
    ge['versions'] = [{'id': e['name'], 'label': re.match(r'^.*\((.*)\)$', e['name']).group(1), 'name': e['name'], 'rarity': e['rarity'],
                       'attunement': e['attunement'], 'desc': e['desc'], 'bases': e.get('bases'), 'fixedBase': e.get('fixedBase'),
                       'rows': e['rows'], 'csvType': e['csvType'], 'weight': e['weight'], 'value': e['value']} for e in es]
    ge['rows'] = ge.get('rows', []) + [n for e in es for n in e['rows']]
    ge['rarity'] = 'var'; ge['parenSet'] = True
    for e in es: e['_mergedInto'] = ge['id']
    paren_report.append({'name': stem, 'source': src, 'versions': [e['name'] for e in es]})

# ---------------------------------------------------------------- hand-made sets (user decisions)
MANUAL_SETS = [('Dragon Mask', 'RoTOS', ['Black Dragon Mask', 'Blue Dragon Mask', 'Green Dragon Mask', 'Red Dragon Mask', 'White Dragon Mask'])]
for gname, gsrc, members in MANUAL_SETS:
    es = [e for e in entries if '_mergedInto' not in e and e['name'] in members and not e.get('versions')]
    if len(es) < 2: continue
    ge = new_entry(name=gname, desc='', rows=[], **{k2: es[0][k2] for k2 in ('page','rarity','csvType','attunement','damage','properties','mastery','weight','value')}, source=gsrc)
    ge['versions'] = [{'id': e['name'], 'label': e['name'].replace(' Dragon Mask', ''), 'name': e['name'], 'rarity': e['rarity'],
                       'attunement': e['attunement'], 'desc': e['desc'], 'rows': e['rows'], 'csvType': e['csvType'], 'source': e['source']} for e in sorted(es, key=lambda e: e['name'])]
    ge['rows'] = [n for e in es for n in e['rows']]
    rr = {e['rarity'] for e in es}; ge['rarity'] = 'var' if len(rr) > 1 else rr.pop()
    for e in es: e['_mergedInto'] = ge['id']

final = [e for e in entries if '_mergedInto' not in e]

# ---------------------------------------------------------------- duplicates
dup_report = []
byn = collections.defaultdict(list)
for e in final: byn[e['name']].append(e)
drop = set()
for n, es in byn.items():
    if len(es) < 2: continue
    if len({e['source'] for e in es}) < len(es):
        print('WARNING same name twice in one book:', n, [e['source'] for e in es])
    texts = {norm(e['desc']) + '|' + e['rarity'] for e in es}
    if len(texts) == 1:
        es2 = sorted(es, key=lambda e: BOOK_YEAR.get(e['source'], 2000), reverse=True)
        keep = es2[0]
        for e in es2[1:]:
            drop.add(e['id']); keep.setdefault('alsoIn', []).append(e['source']); keep['rows'] += e['rows']
        dup_report.append({'name': n, 'kept': keep['source'], 'dropped': [e['source'] for e in es2[1:]], 'why': 'same text'})
    else:
        for e in es: e['name'] = '%s (%s)' % (n, e['source'])
        dup_report.append({'name': n, 'kept': [e['source'] for e in es], 'why': 'different items, both kept'})
final = [e for e in final if e['id'] not in drop]

# ---------------------------------------------------------------- kinds
def kind(e):
    c = (e['csvType'] or '').split(',')[0].strip()
    c0 = re.sub(r'\s*\(.*', '', c)
    if e['rarity'] != 'none': return 'magic'
    if c0 in ('Weapon', 'Melee Weapon', 'Ranged Weapon'): return 'weapon'
    if c0 in ('Light Armor', 'Medium Armor', 'Heavy Armor', 'Shield', 'Armor'): return 'armour'
    if c0 == 'Treasure' or c0 == 'Trade Good' or c0 == 'Trade Bar': return 'valuable'
    if c0 in ('Vehicle', 'Mount'): return 'mount'
    return 'gear'
for e in final:
    e['kind'] = kind(e)
    e.pop('_mergedInto', None)

out = {'entries': final, 'groups': group_report, 'parenSets': paren_report, 'duplicates': dup_report,
       'stats': {'rows': len(ROWS), 'entries': len(final),
                 'by_kind': collections.Counter(e['kind'] for e in final),
                 'var': sum(1 for e in final if e['rarity'] == 'var'),
                 'with_versions': sum(1 for e in final if e.get('versions')),
                 'with_bases': sum(1 for e in final if e.get('bases')),
                 'rows_covered': len({n for e in final for n in e['rows']})}}
json.dump(out, open(OUT, 'w'), indent=0, ensure_ascii=False)
print(json.dumps(out['stats'], indent=1))
