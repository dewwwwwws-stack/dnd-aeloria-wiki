#!/usr/bin/env python3
"""Map the sheet's items to 5e.tools pictures.

Usage: item_images.py ITEMS_META.json LIVE_DUMP.json ITEMS_ADD.json OUT.json [IMG_FILE_LIST]
ITEMS_META is written by items_csv.py; LIVE_DUMP by dump.py (the current sheet's item lists); ITEMS_ADD by
items_audit/tools/iadd.py. OUT is {itemKey: picture}: "SRC/Name" means
https://raw.githubusercontent.com/5etools-mirror-3/5etools-img/main/items/SRC/Name.webp, anything else is a full
address (homebrew pictures). Pictures are fetched by the browser when an item is shown; nothing is stored in the vault.
Homebrew pictures that are book pages (a file not named after the item) are left out.
"""
import json, re, sys, collections
MT, LV, AD, OUT = sys.argv[1:5]
FILES = sys.argv[5] if len(sys.argv) > 5 else None   # optional: `git ls-tree -r --name-only HEAD items` of 5etools-img
M = json.load(open(MT)); L = json.load(open(LV)); A = json.load(open(AD))
def nk(n): return re.sub(r'[^a-z0-9+]+', '', (n or '').lower().replace('’', "'").replace('armour', 'armor'))
def strip_book(n): return re.sub(r" \([^()]*\)$", '', n or '')

def pic(m):
    i = m.get('img') or {}
    if i.get('path'):
        p = i['path']
        mm = re.match(r'^items/(.+)\.webp$', p)
        return mm.group(1) if mm else 'https://raw.githubusercontent.com/5etools-mirror-3/5etools-img/main/' + p
    u = i.get('url') or ''
    stem = re.sub(r'\.\w+$', '', u.rsplit('/', 1)[-1])
    if u and (nk(stem) in nk(m['name']) or nk(m['name']) in nk(stem)) and len(nk(stem)) >= 3: return u
    return None

by_ns, by_n = {}, collections.defaultdict(list)
for m in M:
    p = pic(m)
    if not p: continue
    by_ns[(nk(m['name']), m['abv'])] = p
    by_n[nk(m['name'])].append((not m.get('reprintedBy'), m['abv'].startswith(('UA', 'XUA')) is False, p))
    if m.get('variant'): by_n.setdefault('§' + nk(m['variant']), []).append((True, True, p))

by_file = collections.defaultdict(list)
if FILES:
    for l in open(FILES):
        mm = re.match(r'^items/([^/]+)/(.+)\.webp$', l.strip())
        if mm: by_file[nk(mm.group(2))].append((mm.group(1).startswith('X'), mm.group(1) + '/' + mm.group(2)))

def find(name, src):
    for n in (name, strip_book(name)):
        if (nk(n), src) in by_ns: return by_ns[(nk(n), src)]
    for n in (name, strip_book(name)):
        c = sorted(by_n.get(nk(n)) or [], reverse=True)
        if c: return c[0][2]
    c = by_n.get('§' + nk(strip_book(name)))
    if c: return c[0][2]
    c = sorted(by_file.get(nk(strip_book(name))) or [], reverse=True)    # a picture file named after the item
    return c[0][1] if c else None

out, miss = {}, collections.Counter()
lists = [(x, l) for l in ('magic', 'au', 'weapons', 'armour', 'gear', 'val', 'mnt') for x in L[l]]
lists += [(x, l) for l, k in (('magic', 'magic'), ('au', 'au'), ('weapons', 'newWeapons'), ('armour', 'newArmour'), ('gear', 'gearAdd'), ('val', 'valAdd'), ('mnt', 'mntAdd')) for x in A[k]]
for x, l in lists:
    p = find(x['name'], x.get('source'))
    if p: out[x['key']] = p
    else: miss[l] += 1
json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('pictures', len(out), 'of', len(lists), '| without:', dict(miss), '| homebrew addresses', sum(v.startswith('http') for v in out.values()))
