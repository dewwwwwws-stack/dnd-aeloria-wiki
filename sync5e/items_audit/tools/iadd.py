#!/usr/bin/env python3
"""Additive 5e.tools item import: keep every item the sheet has, add only new ones.

Usage: iadd.py NEW_PATCH NEW_NORM LIVE_DUMP OUT.json
  NEW_PATCH  items_patch.json from iparse+igen run on the NEW rows only (with an empty items_map)
  NEW_NORM   items_norm.json of that run
  LIVE_DUMP  keys/names/sources of every item list in the current sheet build (dump.py)
Rules (user, Nov 2026): existing items and house rules always win and never change; a new item whose name
is already used is skipped when it is the same book, a playtest, or a version of an item the sheet already
groups; a different item from another book is added as "Name (BOOK)".
"""
import json, re, sys, collections
NP, NN, LV, OUT = sys.argv[1:5]
B = json.load(open(NP)); N = json.load(open(NN))['entries']; L = json.load(open(LV))

def nk(n):
    n = (n or '').lower().replace('’', "'").replace('armour', 'armor')
    if ', ' in n and '(' not in n: n = ' '.join(reversed(n.split(', ', 1)))      # "Crossbow, Hand" = "Hand Crossbow"
    return re.sub(r'[^a-z0-9+]+', '', n)                                        # "Battle Axe" = "Battleaxe"
import difflib
def same_text(a, b):
    a, b = re.sub(r'\W+', ' ', (a or '').lower())[:1200], re.sub(r'\W+', ' ', (b or '').lower())[:1200]
    return bool(a and b) and difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() > 0.6
def slug(n): return re.sub(r'_+', '_', re.sub(r'[^a-z0-9+]+', '_', (n or '').lower().replace('+', ''))).strip('_')
def base(n): return re.sub(r' \([^()]*\)$', '', n)
PLAY = re.compile(r'^(X?UA|UA)')
ns = {(e['name'], e['source']) for e in N}
rep = collections.defaultdict(list)

live_names = collections.defaultdict(list)          # name -> [(list, key, source)]
for lst in ('magic', 'au', 'weapons', 'armour', 'gear', 'val', 'mnt'):
    for x in L[lst]: live_names[nk(x['name'])].append((lst, x['key'], x['source'], x.get('desc')))
used_keys = {lst: {x['key'] for x in L[lst]} for lst in L if isinstance(L[lst], list) and L[lst] and isinstance(L[lst][0], dict)}
item_keys = used_keys['magic'] | used_keys['au'] | set(L['aliases'])

def place(x, lst, keyset, kind):
    """Return the entry to add (maybe renamed) or None."""
    n, src = x['name'], x.get('source')
    hits = live_names.get(nk(n)) or live_names.get(nk(base(n))) or []
    if hits:
        if any(same_text(h[3], x.get('desc')) for h in hits): rep['same item as one you have (same text)'].append(f'{n} ({src})'); return None
        if any(h[2] == src for h in hits): rep['same book, already in the sheet'].append(f'{n} ({src})'); return None
        if src and PLAY.match(src): rep['playtest copy of an item you have'].append(f'{n} ({src})'); return None
        if not live_names.get(nk(n)) and base(n) != n: rep['new version of an item you have'].append(f'{n} ({src})'); return None
        if any(h[2] is None for h in hits) and lst != 'magic': rep['same name as a core item you have'].append(f'{n} ({src})'); return None
        renamed = f'{base(n) if base(n)!=n and base(n)!=n.rsplit(" (",1)[0] else n} ({src})'
        if any(h[2] == src or same_text(h[3], x.get('desc')) for h in live_names.get(nk(renamed), [])):    # added by an earlier run under its "(BOOK)" name
            rep['same book, already in the sheet'].append(f'{n} ({src})'); return None
        x = dict(x); x['name'] = renamed
        rep['added beside an item of the same name from another book'].append(x['name'])
    k = x['key'] if x['key'] not in keyset else slug(x['name'])
    while k in keyset: k += '_2'
    if k != x['key']: x = dict(x); x['key'] = k
    keyset.add(k); live_names[nk(x['name'])].append((lst, k, src, x.get('desc')))
    return x

out = {k: [] for k in ('magic', 'au', 'newWeapons', 'newArmour', 'gearAdd', 'valAdd', 'mntAdd')}
out['bases'] = {}; out['newAmmo'] = {}
for lst, src_list in (('magic', 'magic'), ('au', 'au')):
    for x in B[src_list]:
        if x.get('homebrew'): continue                       # the run's copies of the sheet's own items
        if (x['name'], x.get('source')) not in ns and (base(x['name']), x.get('source')) not in ns: continue
        y = place(x, 'magic', item_keys, 'magic')
        if y: out[lst].append(y)
# mundane lists: weapons/armour only when an added magic item uses them or they are new kit
for bk, lst in (('newWeapons', 'weapons'), ('newArmour', 'armour'), ('gearAdd', 'gear'), ('valAdd', 'val'), ('mntAdd', 'mnt')):
    for x in B[bk]:
        if x.get('source') and PLAY.match(x['source']): rep['playtest copy of an item you have'].append(f"{x['name']} ({x['source']})"); continue
        y = place(x, lst, used_keys[lst], lst)
        if y: out[bk].append(y)
# ammunition types and base names the added items need
for k, v in B['newAmmo'].items():
    if k not in L['ammo']: out['newAmmo'][k] = v
live_b = set(L['bases'])
need = {b for x in out['magic'] + out['au'] for b in (x.get('bases') or []) + [b for v in (x.get('versions') or []) for b in (v.get('bases') or [])]}
for b in sorted(need):
    if b in live_b: continue
    if b in B['bases']: out['bases'][b] = B['bases'][b]
    else: rep['MISSING base (fix by hand)'].append(b)
wk = used_keys['weapons'] | {w['key'] for w in out['newWeapons']}; ak = used_keys['armour'] | {a['key'] for a in out['newArmour']}
for b, v in out['bases'].items():
    if v.get('kind') == 'weapon' and v.get('key') not in wk: rep['MISSING base weapon (fix by hand)'].append(b)
    if v.get('kind') == 'armour' and v.get('key') not in ak: rep['MISSING base armour (fix by hand)'].append(b)
out['report'] = {k: sorted(set(v)) for k, v in rep.items()}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=0)
print({k: len(v) for k, v in out.items() if k != 'report'})
for k, v in out['report'].items(): print(f'{k}: {len(v)}', v[:12])
