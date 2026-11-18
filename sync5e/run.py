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
ap.add_argument('--prev', default=None, help='folder holding the previous _5etools_pack.json (+ parts) and _5etools_changes.json, to report what changed')
ap.add_argument('--baseline', default=os.path.join(HERE, 'baseline', 'live.json'))
ap.add_argument('--approvals', default=None, help="the DM's chars/_dm_sources.json: homebrew contents are stored only for books approved there")
ap.add_argument('--chars', default=None, help='folder of character files: books their kept 5e.tools entries came from are stored too')
ap.add_argument('--all-brew', action='store_true', help='store every homebrew book (testing only)')
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

KINDS = (('magic', 'Magic items'), ('gearAdd', 'Gear'), ('valAdd', 'Valuables'), ('mntAdd', 'Mounts & vehicles'), ('newWeapons', 'Weapons'), ('newArmour', 'Armour'))
def _load_pack(d):
    try:
        P = json.load(open(os.path.join(d, '_5etools_pack.json'), encoding='utf-8'))
        for n in P.get('parts', []): P['magic'] = P.get('magic', []) + json.load(open(os.path.join(d, n), encoding='utf-8')).get('magic', [])
        return P
    except Exception: return None
def _entries(P): return {f"{k}:{x['key']}": {'kind': lbl, 'name': x.get('name'), 'source': x.get('source')} for k, lbl in KINDS for x in (P or {}).get(k, []) if x.get('key')}
def diff_with_prev(pack, more=None):
    prev = _load_pack(A.prev) if A.prev else None
    now, was = _entries(pack), _entries(prev)
    new = [now[k] for k in now if k not in was]; gone = [was[k] for k in was if k not in now]
    hist = []
    try: hist = json.load(open(os.path.join(A.prev, '_5etools_changes.json'), encoding='utf-8')).get('runs', []) if A.prev else []
    except Exception: hist = []
    run = {'date': datetime.date.today().isoformat(), 'built': pack.get('built'), 'first': prev is None, 'new': new, 'gone': gone, 'total': len(now)}
    # every part of the run, not just items (the sheet's "What changed" and status line read these)
    if more: run.update(more)
    hist = [run] + hist   # every run is recorded, also one that changed nothing
    json.dump({'runs': hist[:20]}, open(os.path.join(OUT, '_5etools_changes.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    return run
def _bybook(L): 
    by = {}
    for x in L: by.setdefault(f"{x['kind']}", []).append(f"{x['name']} ({x['source']})")
    return [f"- **{k}** ({len(v)}): " + ', '.join(sorted(v)[:300]) + (' …' if len(v) > 300 else '') for k, v in by.items()]
res = None; change = None
try: res = main()
except Exception as e: errors.append(str(e))
L = [f'# 5e.tools sync — {datetime.date.today().isoformat()}', '']
if errors or not res:
    L += ['## FAILED — no pack written, the previous one stays in place', ''] + [f'- {e}' for e in errors] + ['']
else:
    pack, rep, new_books = res
    # homebrew: contents are stored only for books the DM approved (either list on Vault > Sources), plus books that
    # characters still use entries from; every other homebrew book only gets a line in the book list
    allow, kept_books, approvals_ok = set(), set(), False
    if A.approvals and os.path.exists(A.approvals):
        try:
            ap_ = json.load(open(A.approvals, encoding='utf-8')); approvals_ok = True
            allow |= {k for k, v in (ap_.get('approved') or {}).items() if v} | {k for k, v in (ap_.get('sync') or {}).items() if v}
        except Exception as e: warns.append('Could not read the approvals (_dm_sources.json): ' + str(e)[:200])
    if A.chars and os.path.isdir(A.chars):
        for fn in os.listdir(A.chars):
            if not fn.endswith('.json') or fn.startswith('_'): continue
            try: kept_books |= set((json.load(open(os.path.join(A.chars, fn), encoding='utf-8')).get('imports_5e') or {}).values())
            except Exception: pass
    allow |= kept_books
    allow_file = os.path.join(W, 'brew_allow.json'); json.dump(sorted(allow), open(allow_file, 'w'))
    BREW_ENV = dict(os.environ, ALL_BREW='1')
    if not A.all_brew: BREW_ENV['BREW_ALLOW'] = allow_file
    books = None
    try:
        r = json.loads(run(['node', '--max-old-space-size=8000', os.path.join(FT, 'books_catalog.cjs'), A.brew, A.ua, os.path.join(FT, 'brew_files.json'), os.path.join(W, 'sources.json2abv.json'), os.path.join(OUT, '_5etools_books.json')]).strip().splitlines()[-1])
        cat = json.load(open(os.path.join(OUT, '_5etools_books.json'), encoding='utf-8'))['books']
        brew = [a for a, b in cat.items() if b[2] == 'homebrew']
        books = {'listed': len(cat), 'brew': len(brew), 'stored': sorted(a for a in brew if A.all_brew or a in allow), 'kept': sorted(kept_books - {k for k in allow if k not in kept_books}), 'approvals': approvals_ok}
    except Exception as e:
        warns.append('Book list not built this run: ' + str(e).splitlines()[0][:300])
    # bestiary pack (independent of the items: a problem here is reported, never blocks the items)
    best = None
    try:
        bo = os.path.join(OUT, '_bestiary'); j2a = os.path.join(W, 'sources.json2abv.json')
        r = json.loads(run(['node', '--max-old-space-size=6000', os.path.join(FT, 'bestiary_pack.cjs'), A.site, A.brew, os.path.join(FT, 'brew_files.json'), j2a, bo, A.ua], env=BREW_ENV).strip().splitlines()[-1])   # every homebrew book with creatures
        I = json.load(open(os.path.join(bo, 'index.json'), encoding='utf-8')); prevI = None
        try: prevI = json.load(open(os.path.join(A.prev, '_bestiary_index.json'), encoding='utf-8')) if A.prev else None
        except Exception: prevI = None
        newX = set(a for a in I.get('extra', []) if prevI is not None and a not in prevI.get('counts', {}))   # reported on their own line
        changed = sorted(a for a in I['counts'] if a not in newX and (not prevI or [x['h'] for x in I['files'][a]] != [x['h'] for x in prevI.get('files', {}).get(a, [])]))
        best = {'total': I['total'], 'books': len(I['counts']), 'fails': r.get('fails', 0), 'changed': changed, 'first': prevI is None,
                'added': {a: I['counts'][a] - ((prevI or {}).get('counts', {}).get(a, 0)) for a in changed},
                'extra': len(I.get('extra', [])), 'extraN': sum(I['counts'].get(a, 0) for a in I.get('extra', [])),
                'newExtra': [f"{I['names'][a][0]} ({a}, {I['counts'][a]})" for a in I.get('extra', []) if prevI is not None and a not in prevI.get('counts', {})]}
        if r.get('fails'): warns.append(f"Bestiary: {r['fails']} creatures could not be built (usually a homebrew book that copies from one that isn't loaded), e.g. " + '; '.join(I.get('fails', [])[:3]))
    except Exception as e:
        warns.append('Bestiary pack not built this run: ' + str(e).splitlines()[0][:300])
    # raw 5e.tools library (DM's Vault > 5e.tools): every other category, shown as 5e.tools has it; never touches the sheet's lists
    raw = None
    try:
        ro = os.path.join(OUT, '_5etools_raw'); j2a = os.path.join(W, 'sources.json2abv.json')
        r = json.loads(run(['node', '--max-old-space-size=8000', os.path.join(FT, 'raw_pack.cjs'), A.site, A.brew, A.ua, os.path.join(FT, 'brew_files.json'), j2a, ro], env=BREW_ENV).strip().splitlines()[-1])
        RI = json.load(open(os.path.join(ro, 'index.json'), encoding='utf-8')); prevR = None
        try: prevR = json.load(open(os.path.join(A.prev, '_5etools_raw_index.json'), encoding='utf-8')) if A.prev else None
        except Exception: prevR = None
        grew = {c: v['n'] - ((prevR or {}).get('cats', {}).get(c, {}).get('n', 0)) for c, v in RI['cats'].items()}
        raw = {'total': RI['total'], 'cats': {c: v['n'] for c, v in RI['cats'].items()}, 'labels': {c: v['label'] for c, v in RI['cats'].items()}, 'first': prevR is None,
               'grew': {c: n for c, n in grew.items() if n and prevR is not None}, 'fails': r.get('fails', 0)}
        if r.get('fails', 0) > 300: warns.append(f"5e.tools library: {r['fails']} entries could not be built, e.g. " + '; '.join(RI.get('fails', [])[:3]))
    except Exception as e:
        warns.append('5e.tools library not built this run: ' + str(e).splitlines()[0][:300])
    # new for the sheet: spells, feats, species, backgrounds, classes, subclasses, class options it does not have yet
    sheet = None
    try:
        so = os.path.join(OUT, '_5etools_sheet'); j2a = os.path.join(W, 'sources.json2abv.json')
        r = json.loads(run(['node', '--max-old-space-size=8000', os.path.join(FT, 'sheet_pack.cjs'), A.site, A.brew, A.ua, os.path.join(FT, 'brew_files.json'), j2a, A.baseline, so], env=BREW_ENV).strip().splitlines()[-1])
        SI = json.load(open(os.path.join(so, 'index.json'), encoding='utf-8')); prevS = None
        try: prevS = json.load(open(os.path.join(A.prev, '_5etools_sheet_index.json'), encoding='utf-8')) if A.prev else None
        except Exception: prevS = None
        off = set(SI.get('official', []))
        sheet = {'total': SI['total'], 'kinds': {k: v['n'] for k, v in SI['kinds'].items()}, 'official': {k: sum(n for a, n in v['counts'].items() if a in off) for k, v in SI['kinds'].items()}, 'first': prevS is None,
                 'newBooks': sorted(a for a in off if prevS is not None and a not in set(prevS.get('official', []))), 'fails': r.get('fails', 0)}
    except Exception as e:
        warns.append('New-for-the-sheet pack not built this run: ' + str(e).splitlines()[0][:300])
    # what this run changed, part by part, for the change log
    prevStored = None
    try: prevStored = next((r.get('stored') for r in json.load(open(os.path.join(A.prev, '_5etools_changes.json'), encoding='utf-8')).get('runs', []) if r.get('stored') is not None), None) if A.prev else None
    except Exception: prevStored = None
    more = {}
    if books: more['stored'] = books['stored']; more['brewAdded'] = sorted(set(books['stored']) - set(prevStored or [])) if prevStored is not None else []; more['brewRemoved'] = sorted(set(prevStored or []) - set(books['stored']))
    if best: more['creatures'] = {'total': best['total'], 'added': {a: n for a, n in best['added'].items() if n} if not best['first'] else {}, 'changed': best['changed'][:60] if not best['first'] else []}
    if sheet:
        prevSK = {}
        try: prevSK = {k: v['n'] for k, v in json.load(open(os.path.join(A.prev, '_5etools_sheet_index.json'), encoding='utf-8'))['kinds'].items()} if A.prev else {}
        except Exception: prevSK = {}
        more['sheet'] = {'total': sheet['total'], 'grew': {k: n - prevSK.get(k, 0) for k, n in sheet['kinds'].items() if n != prevSK.get(k, 0)} if prevSK else {}}
    if raw: more['library'] = {'total': raw['total'], 'grew': raw['grew']}
    change = diff_with_prev(pack, more)
    c = {k: len(pack[k]) for k in ('magic', 'gearAdd', 'valAdd', 'mntAdd', 'newWeapons', 'newArmour')}; all_magic = list(pack['magic']); nparts = write(pack)
    L += [f"**{c['magic']} magic items, {c['gearAdd']} gear, {c['valAdd']} valuables, {c['mntAdd']} mounts/vehicles, {c['newWeapons']} weapons, {c['newArmour']} armour** on top of the sheet as last built"
          + (f' (split over {nparts} extra files).' if nparts else '.'), '', 'From: ' + ', '.join(f'{k} {v}' for k, v in pack['from'].items()), '']
    if change['first']: L += ['## What changed', '', 'First sync: everything in the pack is new to the sheet.', '']
    elif not change['new'] and not change['gone']: L += ['## What changed', '', 'Nothing new since the last sync.', '']
    else:
        L += [f"## New since the last sync ({len(change['new'])})", ''] + (_bybook(change['new']) or ['None.']) + ['']
        if change['gone']: L += [f"## No longer in the pack ({len(change['gone'])})", '', 'Usually because the sheet was rebuilt with them built in; otherwise 5e.tools removed or renamed them.', ''] + _bybook(change['gone']) + ['']
    if best:
        L += ['## Bestiary', '', f"{best['total']:,} creatures from {best['books']} books." + (' First bestiary pack.' if best['first'] else (f" Changed books: {', '.join(best['changed'][:40])}" + (' …' if len(best['changed']) > 40 else '') if best['changed'] else ' Nothing changed since the last sync.')), '']
        if best['extra']: L += [f"Of these, {best['extraN']:,} come from {best['extra']} homebrew books in the full 5e.tools homebrew collection. Each stays off until you turn it on in Vault > Sources.", '']
        if best['newExtra']: L += ['New homebrew books with creatures: ' + ', '.join(best['newExtra'][:60]) + (' …' if len(best['newExtra']) > 60 else ''), '']
        more = {a: n for a, n in best['added'].items() if n > 0 and not best['first']}
        if more: L += ['New creatures by book: ' + ', '.join(f'{a} +{n}' for a, n in sorted(more.items())), '']
    if books:
        L += ['## Homebrew', '', f"{books['brew']:,} homebrew books are listed on Vault > Sources (names and what each has, no contents). Contents are stored for the {len(books['stored'])} you approved" + (f" or that characters still use ({', '.join(books['kept'][:20])})" if books['kept'] else '') + ': ' + (', '.join(books['stored'][:80]) or 'none') + '.', '']
        if not books['approvals']: L += ['No approvals were found (chars/_dm_sources.json), so no homebrew contents were stored.', '']
    if sheet:
        K = {'spell': 'spells', 'feat': 'feats', 'background': 'backgrounds', 'race': 'species', 'class': 'classes', 'subclass': 'subclasses', 'invocation': 'invocations', 'maneuver': 'maneuvers', 'metamagic': 'metamagic options', 'arcaneshot': 'Arcane Shots', 'rune': 'runes'}
        L += ['## New for the sheet', '', 'Added to the sheet\'s own lists from official books: ' + (', '.join(f"{n} {K.get(k, k)}" for k, n in sheet['official'].items() if n) or 'nothing') + '. Playtest and homebrew books add theirs once you tick them "Add to the sheet" in Vault > Sources (available: ' + ', '.join(f"{n:,} {K.get(k, k)}" for k, n in sheet['kinds'].items()) + ').', '',
              'Check them in Vault > New from 5e.tools: each shows what was wired automatically and what is still text only.', '']
        if sheet['newBooks']: L += ['New official books with new content: ' + ', '.join(sheet['newBooks']), '']
    if raw:
        L += ['## 5e.tools library (DM only)', '', f"{raw['total']:,} entries: " + ', '.join(f"{raw['labels'][c]} {n:,}" for c, n in raw['cats'].items()) + '.' + (' First library pack.' if raw['first'] else ''), '']
        if raw['grew']: L += ['Change since last sync: ' + ', '.join(f"{raw['labels'][c]} {'+' if n > 0 else ''}{n}" for c, n in raw['grew'].items()), '']
        if raw['fails']: L += [f"{raw['fails']} entries could not be built (mostly homebrew that copies from a book that is not loaded).", '']
    if new_books: L += ['## New books (switched OFF for players until you turn them on in Vault > Sources)', '', ', '.join(new_books), '']
    if all_magic: L += ['## Magic items in the pack', '', ', '.join(f"{x['name']} ({x.get('source')})" for x in all_magic[:400]) + (' …' if len(all_magic) > 400 else ''), '']
    for k, v in rep.items():
        if not k.startswith('MISSING'): L += [f'<details><summary>Left out: {k} ({len(v)})</summary>', '', ', '.join(v[:300]), '', '</details>', '']
if warns: L += ['## Needs a look', ''] + [f'- {w}' for w in warns] + ['']
if notes: L += ['## Notes', ''] + [f'- {n}' for n in notes] + ['']
text = '\n'.join(L); open(os.path.join(OUT, '_5etools_report.md'), 'w', encoding='utf-8').write(text); print(text[:3000])
if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(text[:60000])
if os.environ.get('GITHUB_OUTPUT'): open(os.environ['GITHUB_OUTPUT'], 'a').write(f"status={'failed' if errors or not res else 'warn' if warns else 'ok'}\nnew_count={len(change['new']) if change and not change['first'] else 0}\n")
sys.exit(1 if errors or not res else 0)
