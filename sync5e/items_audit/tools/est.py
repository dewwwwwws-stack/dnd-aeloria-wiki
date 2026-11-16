import csv,collections,re,json
csv.field_size_limit(10**9)
R=list(csv.DictReader(open('src/Items.csv',encoding='utf-8-sig',newline='')))
PRE=re.compile(r'^The base item can be found in[^\n]*\n\n')
def norm(t): return re.sub(r'\s+',' ',t).strip()
byname=collections.defaultdict(list)
for r in R: byname[r['Name']].append(r)
def magic_text(r,base):
    t=PRE.sub('',r['Text'])
    for b in byname.get(base,[]):
        if b['Text'] and t.endswith(b['Text']): return t[:-len(b['Text'])].rstrip()
    for b in byname.get(base,[]):
        bt=b['Text'][:60]
        if bt and bt in t: return t[:t.index(bt)].rstrip()
    return t
def isexp(r): return bool(re.match(r'^[^,(]*\(',r['Type'])) and 'Generic Variant' not in r['Type']
def plusnorm(s): return re.sub(r'\+\s?[123]\b','+N',re.sub(r'\b(1|2|3)\b(?= bonus)','N',s))
groups=collections.defaultdict(list)
for r in R:
    if isexp(r):
        base=re.match(r'^[^,(]*\(([^)]*)\)',r['Type']).group(1)
        key=('E',r['Source'],plusnorm(norm(magic_text(r,base))))
    elif 'Generic Variant' in r['Type']:
        key=('E',r['Source'],plusnorm(norm(r['Text'].split('\n\nBase items')[0])))
    else:
        key=('S',r['Source'],plusnorm(r['Name']) if re.search(r'\+\s?[123]\b',r['Name']) else r['Name'])
    groups[key].append(r)
print('rows',len(R),'-> entries',len(groups))
C=collections.Counter
print('entries made of >1 rows',sum(1 for v in groups.values() if len(v)>1))
multi_rar=[v for v in groups.values() if len({r['Rarity'] for r in v})>1]
print('entries with >1 rarity (become var)',len(multi_rar))
print([sorted({r['Name'] for r in v})[:3] for v in multi_rar[:15]])
sing=[v for k,v in groups.items() if k[0]=='S' and len(v)>1]; print('plain +N groups',len(sing),[[r['Name'] for r in v] for v in sing[:10]])
json.dump([[list(k),[r['Name'] for r in v]] for k,v in groups.items()],open('/tmp/claude-0/-home-claude/566fe85c-bb76-535d-8370-dee49ad1e3ed/scratchpad/groups.json','w'))
