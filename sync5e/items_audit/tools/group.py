import csv,collections,re,json,sys
csv.field_size_limit(10**9)
R=list(csv.DictReader(open('src/Items.csv',encoding='utf-8-sig',newline='')))
def norm(t): return re.sub(r'\s+',' ',t).strip()
base_rows=collections.defaultdict(list)
for r in R:
    base_rows[r['Name']].append(r)
PRE=re.compile(r'^The base item can be found in[^\n]*\n\n')
def magic_text(r,base):
    t=PRE.sub('',r['Text'])
    for b in base_rows.get(base,[]):
        bt=b['Text']
        if bt and t.endswith(bt): return t[:-len(bt)].rstrip()
    # fallback: strip after base-text start if base has text and it appears
    for b in base_rows.get(base,[]):
        bt=b['Text'][:60]
        if bt and bt in t: return t[:t.index(bt)].rstrip()
    return t
gv={}
for r in R:
    if 'Generic Variant' in r['Type']:
        gv.setdefault(norm(r['Text'].split('\n\nBase items')[0]),[]).append(r)
fam=collections.defaultdict(list); out=[]
for i,r in enumerate(R):
    m=re.match(r'^[^,(]*\(([^)]*)\)',r['Type'])
    if not m or 'Generic Variant' in r['Type']: continue
    base=m.group(1)
    mt=norm(magic_text(r,base))
    fam[(mt,r['Source'])].append((r['Name'],base,r['Rarity']))
print('expansion rows',sum(len(v) for v in fam.values()),'families',len(fam))
withgv=sum(1 for k in fam if k[0] in gv); print('families with a generic variant row',withgv)
sizes=collections.Counter(min(len(v),50)//10*10 for v in fam.values()); print(sorted(sizes.items()))
nogv=[(k,v) for k,v in fam.items() if k[0] not in gv]
print('no gv families',len(nogv), 'rows',sum(len(v) for k,v in nogv))
for k,v in sorted(nogv,key=lambda x:-len(x[1]))[:30]: print(len(v),k[1],v[:3],'|',k[0][:70])
json.dump({'fam':[[k[0],k[1],v] for k,v in fam.items()]},open('/tmp/claude-0/-home-claude/566fe85c-bb76-535d-8370-dee49ad1e3ed/scratchpad/fam.json','w'))
