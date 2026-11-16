#!/usr/bin/env python3
"""Weekly 5e.tools sync for the Character Sheet: build the "pack" of everything 5e.tools has that the sheet does not.

  python3 sync5e/run.py --site DIR --brew DIR --ua DIR --img DIR --out DIR [--work DIR] [--reuse-export]

  --site  checkout of 5etools-mirror-3/5etools-src      --brew  checkout of TheGiddyLimit/homebrew
  --ua    checkout of TheGiddyLimit/unearthed-arcana    --img   checkout of 5etools-mirror-3/5etools-img (blobless is fine)
  --out   where _5etools_pack.json (+ parts) and _5etools_report.md are written

ADD ONLY. The pack holds entries whose key and name are not in baseline/live.json (the sheet as last built), so
nothing the sheet has is ever changed. Rules are those of the hand-run import (see new_rows.py and iadd.py).
Exit code 1 = something is wrong and NO pack was written (the old one stays in place); the report says what.
"""
import argparse, csv, datetime, json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
for a in ('site', 'brew', 'ua', 'img', 'out'): ap.add_argument('--' + a, required=True)
ap.add_argument('--work', default=os.path.join(HERE, '_work')); ap.add_argument('--reuse-export', action='store_true')
ap.add_argument('--baseline', default=os.path.join(HERE, 'baseline', 'live.json'))
A = ap.parse_args()
W = os.path.abspath(A.work); OUT = os.path.abspath(A.out); os.makedirs(W, exist_ok=True); os.makedirs(OUT, exist_ok=True)
FT = os.path.join(HERE, 'fivetools'); IA = os.path.join(HERE, 'items_audit')
errors, warns, notes = [], [], []

def run(cmd, **kw):
    print('+', ' '.join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode: raise RuntimeError(f"{os.path.basename(str(cmd[1]))} failed:\n{(r.stdout or '')[-1500:]}\n{(r.stderr or '')[-2500:]}")
    return r.stdout
def git_rev(d):
    try: return subprocess.run(['git', '-C', d, 'log', '-1', '--format=%h %cs'], capture_output=True, text=True).stdout.strip()
    except Exception: return '?'

def main():
    env = dict(os.environ, SITE=os.path.abspath(A.site), BREW=os.path.abspath(A.brew), UA=os.path.abspath(A.ua))
    new_csv = os.path.join(W, 'items_new.csv'); meta = os.path.join(W, 'items_new.meta.json')
    # 1. fresh export from the 5e.tools items page (all columns, the 26 homebrew books, playtest)
    if not (A.reuse_export and os.path.exists(new_csv)): run([sys.executable, os.path.join(FT, 'items_csv.py'), new_csv], env=env)
    n_rows = sum(1 for _ in csv.DictReader(open(new_csv, encoding='utf-8')))
    head = next(csv.reader(open(new_csv, encoding='utf-8')))
    if n_rows < 15000: errors.append(f'The 5e.tools export has only {n_rows:,} rows (expected about 18,800). The items page or a homebrew file has probably changed shape.')
    want = ['Name', 'Source', 'Page', 'Rarity', 'Type', 'Attunement', 'Damage', 'Properties', 'Mastery', 'Weight', 'Value', 'Text']
    if [h for h in want if h not in head]: errors.append('The export is missing columns: ' + ', '.join(h for h in want if h not in head))
    if errors: return None
    # 2. rows the sheet's own Items.csv does not have
    rows_csv = os.path.join(W, 'Items_new.csv')
    notes.append(run([sys.executable, os.path.join(FT, 'new_rows.py'), os.path.join(IA, 'src', 'Items.csv'), new_csv, meta, rows_csv]).strip().splitlines()[-1])
    # 3. the sheet's item pipeline on those rows alone (a private copy: the tools write next to themselves)
    ia = os.path.join(W, 'ia'); shutil.rmtree(ia, ignore_errors=True); shutil.copytree(IA, ia)
    for f in os.listdir(os.path.join(ia, 'tools')):
        if f.endswith('.py'):
            p = os.path.join(ia, 'tools', f); s = open(p, encoding='utf-8').read()
            s2 = s.replace('/home/claude/cs/tooling/items_audit', ia)
            if s2 != s: open(p, 'w', encoding='utf-8').write(s2)
    json.dump({'map': {}, 'unmatched': []}, open(os.path.join(ia, 'items_map.json'), 'w'))
    run([sys.executable, os.path.join(ia, 'tools', 'iparse.py'), rows_csv, os.path.join(ia, 'items_norm.json')], cwd=ia)
    run([sys.executable, os.path.join(ia, 'tools', 'igen.py')], cwd=ia)
    # 4. keep only what the sheet (as last built) does not have
    add_json = os.path.join(W, 'items_add.json')
    run([sys.executable, os.path.join(ia, 'tools', 'iadd.py'), os.path.join(ia, 'items_patch.json'), os.path.join(ia, 'items_norm.json'), A.baseline, add_json])
    ADD = json.load(open(add_json, encoding='utf-8')); rep = ADD.pop('report', {})
    bad = [k for k in rep if k.startswith('MISSING')]
    for k in bad: warns.append(f'{k}: ' + ', '.join(rep[k][:20]))
    if bad:   # an item whose weapon/armour type is unknown is held back rather than shipped broken
        miss = {b for k in bad for b in rep[k]}
        held = [x['name'] for x in ADD['magic'] if miss & set(x.get('bases') or [])]
        ADD['magic'] = [x for x in ADD['magic'] if not (miss & set(x.get('bases') or []))]
        if held: warns.append('Held back until fixed by hand: ' + ', '.join(held[:30]))
    # 5. pictures and book names for the new entries
    files = os.path.join(W, 'img_items.txt')
    open(files, 'w').write(subprocess.run(['git', '-C', A.img, 'ls-tree', '-r', '--name-only', 'HEAD', 'items'], capture_output=True, text=True).stdout)
    if os.path.getsize(files) < 1000: warns.append('Could not list the 5e.tools picture files; new items get no pictures this run.')
    img_json = os.path.join(W, 'item_images.json')
    run([sys.executable, os.path.join(FT, 'item_images.py'), meta, A.baseline, add_json, img_json, files])
    new_keys = {x['key'] for k in ('magic', 'au', 'newWeapons', 'newArmour', 'gearAdd', 'valAdd', 'mntAdd') for x in ADD.get(k, [])}
    PRE = [('~', 'https://raw.githubusercontent.com/TheGiddyLimit/homebrew-img/main/img/'), ('^', 'https://raw.githubusercontent.com/TheGiddyLimit/homebrew-img/refs/heads/main/img/'), ('`', 'https://raw.githubusercontent.com/TheGiddyLimit/homebrew/master/_img/')]
    img = {}
    for k, v in json.load(open(img_json, encoding='utf-8')).items():
        if k not in new_keys: continue
        for c, p in PRE:
            if v.startswith(p): v = c + v[len(p):]; break
        img[k] = v
    src_json = os.path.join(W, 'sources.json')
    try:
        run(['node', os.path.join(FT, 'sources.cjs'), A.site, A.brew, os.path.join(FT, 'brew_files.json'), src_json, A.ua])
        S = json.load(open(src_json, encoding='utf-8'))
    except Exception as e: S = {}; warns.append('Book names could not be read (' + str(e).splitlines()[0] + '); new books show as their short code.')
    used = {x.get('source') for k in ('magic', 'gearAdd', 'valAdd', 'mntAdd') for x in ADD.get(k, []) if x.get('source')}
    base = json.load(open(A.baseline, encoding='utf-8'))
    known = {x.get('source') for k in ('magic', 'au', 'gear', 'val', 'mnt') for x in base[k]}
    new_books = sorted(s for s in used if s not in known)
    # 6. checks
    keys = [x['key'] for x in ADD['magic']]; live = {x['key'] for x in base['magic'] + base['au']} | set(base['aliases'])
    if len(keys) != len(set(keys)): errors.append('Two new magic items share a key.')
    if set(keys) & live: errors.append('A new magic item reuses a key the sheet already has: ' + ', '.join(sorted(set(keys) & live)[:10]))
    for x in ADD['magic']:
        if not x.get('name') or not x.get('desc') and not x.get('versions'): warns.append(f"No text for {x.get('name') or x.get('key')}")
    wk = {w['key'] for w in base['weapons']} | {w['key'] for w in ADD['newWeapons']}
    notype = [x['name'] for x in ADD['magic'] if x.get('isWeapon') and not x.get('bases') and not (x.get('baseWeapon') or x.get('fixedBase') or x.get('weaponKey'))]
    if notype: warns.append('Weapons with no weapon type (they arrive without an attack line; tell Claude which weapon each counts as): ' + ', '.join(notype[:30]))
    if errors: return None
    built = max([git_rev(d).split(' ')[-1] for d in (A.site, A.brew, A.ua)] or ['?'])    # date of the newest source change: the same data gives the same pack
    pack = {'v': 1, 'built': built, 'from': {'5etools-src': git_rev(A.site), 'homebrew': git_rev(A.brew), 'unearthed-arcana': git_rev(A.ua)},
            'magic': ADD['magic'] + ADD.get('au', []), 'bases': ADD['bases'], 'newWeapons': ADD['newWeapons'], 'newArmour': ADD['newArmour'],
            'gearAdd': ADD['gearAdd'], 'valAdd': ADD['valAdd'], 'mntAdd': ADD['mntAdd'], 'img': img, 'src': {s: S[s] for s in used if s in S}}
    return pack, rep, new_books

def write(pack):
    for f in os.listdir(OUT):
        if re.match(r'^_5etools_pack_\d+\.json$', f): os.remove(os.path.join(OUT, f))
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    LIMIT = 650_000                                   # GitHub's file API stops at 1 MB (base64 adds a third)
    if len(dump(pack).encode()) <= LIMIT: parts = []
    else:
        items, pack['magic'], parts, cur = pack['magic'], [], [], []
        for it in items:
            cur.append(it)
            if len(dump(cur).encode()) > LIMIT: parts.append(cur[:-1]); cur = [it]
        if cur: parts.append(cur)
        pack['parts'] = [f'_5etools_pack_{i + 1}.json' for i in range(len(parts))]
        for n, p in zip(pack['parts'], parts): open(os.path.join(OUT, n), 'w', encoding='utf-8').write(dump({'magic': p}))
    open(os.path.join(OUT, '_5etools_pack.json'), 'w', encoding='utf-8').write(dump(pack))
    return len(parts)

res = None
try: res = main()
except Exception as e: errors.append(str(e))
L = [f'# 5e.tools sync — {datetime.date.today().isoformat()}', '']
if errors or not res:
    L += ['## FAILED — no pack written, the previous one stays in place', ''] + [f'- {e}' for e in errors] + ['']
else:
    pack, rep, new_books = res
    c = {k: len(pack[k]) for k in ('magic', 'gearAdd', 'valAdd', 'mntAdd', 'newWeapons', 'newArmour')}; all_magic = list(pack['magic']); nparts = write(pack)
    L += [f"**{c['magic']} magic items, {c['gearAdd']} gear, {c['valAdd']} valuables, {c['mntAdd']} mounts/vehicles, {c['newWeapons']} weapons, {c['newArmour']} armour** on top of the sheet as last built"
          + (f' (split over {nparts} extra files).' if nparts else '.'), '', 'From: ' + ', '.join(f'{k} {v}' for k, v in pack['from'].items()), '']
    if new_books: L += ['## New books (switched OFF for players until you turn them on in Vault > Sources)', '', ', '.join(new_books), '']
    if all_magic: L += ['## Magic items in the pack', '', ', '.join(f"{x['name']} ({x.get('source')})" for x in all_magic[:400]) + (' …' if len(all_magic) > 400 else ''), '']
    for k, v in rep.items():
        if not k.startswith('MISSING'): L += [f'<details><summary>Left out: {k} ({len(v)})</summary>', '', ', '.join(v[:300]), '', '</details>', '']
if warns: L += ['## Needs a look', ''] + [f'- {w}' for w in warns] + ['']
if notes: L += ['## Notes', ''] + [f'- {n}' for n in notes] + ['']
text = '\n'.join(L); open(os.path.join(OUT, '_5etools_report.md'), 'w', encoding='utf-8').write(text); print(text[:3000])
if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(text[:60000])
if os.environ.get('GITHUB_OUTPUT'): open(os.environ['GITHUB_OUTPUT'], 'a').write(f"status={'failed' if errors or not res else 'warn' if warns else 'ok'}\n")
sys.exit(1 if errors or not res else 0)
