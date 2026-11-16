#!/usr/bin/env python3
"""Pick the rows of a fresh 5e.tools Items.csv that the sheet's Items.csv does not have.

Usage: new_rows.py OLD_Items.csv NEW_Items.csv NEW.meta.json OUT_Items_new.csv
Rules (user, Nov 2026): newest printing wins (rows reprinted by a newer book are left out); playtest (UA/XUA)
rows are left out when a printed book has an item of that name, and only the latest playtest packet of a name
is kept; a specific version of a generic item the sheet already has ("+1 X" of "X") is left out, because
existing items never change.
"""
import csv, json, sys, io, re, collections
OLD, NEW, META, OUT = sys.argv[1:5]
old = list(csv.DictReader(open(OLD, encoding='utf-8')))
new = list(csv.DictReader(open(NEW, encoding='utf-8')))
meta = {(m['name'], m['abv']): m for m in json.load(open(META))}
have = {(r['Name'], r['Source']) for r in old}; old_names = {r['Name'] for r in old}
play = lambda s: s.startswith(('UA', 'XUA'))
printed = {r['Name'].lower() for r in old + new if not play(r['Source'])}
def packet(s):                       # later packets sort higher: XUA24A > XUA23P8 > ... > UA20SMT
    m = re.match(r'^X?UA(\d\d)?(.*)$', s); return (s.startswith('XUA'), m.group(1) or '', m.group(2))
latest = {}
for r in new:
    if play(r['Source']): latest[r['Name'].lower()] = max(latest.get(r['Name'].lower(), r['Source']), r['Source'], key=packet)
rows, why = [], collections.Counter()
for r in new:
    k = (r['Name'], r['Source']); m = meta.get(k) or {}
    if k in have: continue
    if m.get('reprintedBy'): why['older printing'] += 1; continue
    if play(r['Source']):
        if r['Name'].lower() in printed: why['playtest of a printed item'] += 1; continue
        if latest[r['Name'].lower()] != r['Source']: why['older playtest packet'] += 1; continue
    if m.get('variant') and m['variant'] in old_names: why['version of an item you have'] += 1; continue
    rows.append(r)
buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=list(old[0].keys()), quoting=csv.QUOTE_ALL, lineterminator='\n')
w.writeheader(); [w.writerow({f: r.get(f, '') for f in old[0].keys()}) for r in rows]
open(OUT, 'w', encoding='utf-8', newline='').write(buf.getvalue())
print('new rows', len(rows), dict(why))
