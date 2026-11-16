import csv,collections,re,json
csv.field_size_limit(10**9)
R=list(csv.DictReader(open('src/Items.csv',encoding='utf-8-sig',newline='')))
D=json.load(open('sheetdata/DMG_MAGIC_ITEMS.json')); A=json.load(open('sheetdata/AU_MAGIC_ITEMS.json')); G=json.load(open('sheetdata/PHB_GEAR.json'))
def k(n): 
    n=n.lower().replace('’',"'").replace('armour','armor')
    return re.sub(r'[^a-z0-9+]+',' ',n).strip()
PRE=re.compile(r"^The base item can be found in[^\n]*\n\n")
csvn=collections.defaultdict(list)
for r in R: csvn[k(r['Name'])].append(r)
C=collections.Counter
for label,X in (('DMG_MAGIC_ITEMS',D),('AU_MAGIC_ITEMS',A),('PHB_GEAR',G)):
    hit=[x for x in X if k(x['name']) in csvn]; miss=[x for x in X if k(x['name']) not in csvn]
    print(label,len(X),'found',len(hit),'not found',len(miss))
    print('  missing by source',C(x.get('source') for x in miss).most_common(25))
    print('  missing by type',C(x.get('type',x.get('category')) for x in miss).most_common(12))
    print('  samples',[x['name'] for x in miss][:40])
print('-----')
sn=collections.defaultdict(list)
for x in D+A+G: sn[k(x['name'])].append(x)
new=[r for r in R if k(r['Name']) not in sn]
print('CSV rows not on sheet',len(new))
print(' by rarity',C(r['Rarity'] for r in new).most_common())
print(' by source',C(r['Source'] for r in new).most_common(30))
exp=lambda r: bool(re.match(r'^[^,(]*\(',r['Type'])) and 'Generic Variant' not in r['Type']
print(' expansions among them',sum(exp(r) for r in new))
# field diffs for matched DMG
def rn(x): return (x or '').lower().strip()
rd=ad=td=0; ex=[]
def T(t): return re.sub(r'\s+',' ',re.sub(r'[*_#]','',t or '')).strip().lower()
for x in D+A:
    rs=csvn.get(k(x['name']))
    if not rs: continue
    src=[r for r in rs if r['Source']==x.get('source')] or rs
    r=src[0]
    if rn(x.get('rarity'))!=rn(r['Rarity']): rd+=1
    att=str(x.get('attunement')).lower() in ('true','1') or x.get('attunement') is True
    if att != r['Attunement'].startswith('Requires'): ad+=1
    if T(x.get('desc'))!=T(PRE.sub('',r['Text'])) : td+=1; ex.append((x['name'],x.get('desc','')[:150],r['Text'][:150]))
print('rarity diffs',rd,'attune diffs',ad,'text diffs',td)
for e in ex[:6]: print(e)
