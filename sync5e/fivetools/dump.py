import json, sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+sys.argv[1]); pg.wait_for_timeout(4000)
    r=pg.evaluate("""()=>{const f=a=>(a||[]).map(x=>({key:x.key,name:x.name,source:x.source||null,desc:(x.desc||"").slice(0,1500)}));
      return {magic:f(typeof DMG_MAGIC_ITEMS!=='undefined'?DMG_MAGIC_ITEMS:window.DMG_MAGIC_ITEMS), au:f(typeof AU_MAGIC_ITEMS!=='undefined'?AU_MAGIC_ITEMS:null),
      weapons:f(PHB_WEAPONS), armour:f(PHB_ARMOUR), gear:f(PHB_GEAR), val:f(VALUABLES_CATALOG), mnt:f(MOUNTS_VEHICLES_CATALOG),
      aliases:Object.keys(typeof ITEM_KEY_ALIASES!=='undefined'?ITEM_KEY_ALIASES:{}), bases:Object.keys(typeof ITEM_BASES!=='undefined'?ITEM_BASES:{}), ammo:Object.keys(AMMO_TYPES),
      rep:{src:(()=>{const lc=x=>String(x||'').toLowerCase().replace(/\s+/g,' ').trim(), vs=(l,k,x)=>typeof vaultSrc==='function'?vaultSrc(l,k,x):(x||null), sub={};
        Object.entries(PHB_SUBCLASSES).forEach(([k,x])=>{const b=vs('subclasses',k,x.source); sub[k]=b; sub[k.split('/')[0]+'/'+lc(x.name)]=b;});
        return {spell:Object.fromEntries(PHB_SPELL_LIST.map(x=>[lc(x.name),vs('spells',x.key,x.source)])), feat:Object.fromEntries(Object.entries(PHB_FEATS).map(([k,x])=>[lc(x.name),vs('feats',k,x.source)])),
          race:Object.fromEntries(Object.entries(PHB_RACES).map(([k,x])=>[lc(String(x.name).replace(/\s*\([^)]*\)\s*/g,' ')),vs('species',k,x.source)])), background:Object.fromEntries(Object.entries(PHB_BACKGROUNDS).map(([k,x])=>[lc(x.name),vs('backgrounds',k,x.source)])),
          class:Object.fromEntries(Object.keys(PHB_CLASSES).map(k=>[lc(PHB_CLASSES[k].name),typeof vaultClassSrc==='function'?vaultClassSrc(k):null])), subclass:sub};})(),
        // a short sample of each entry's own text: a newer printing is only offered when the sheet's text matches the older one
        txt:(()=>{const lc=x=>String(x||'').toLowerCase().replace(/\s+/g,' ').trim(), T=x=>lc([x.desc,x.intro,x.trait,...(x.features||[]).map(f=>f&&(f.name+' '+f.desc)),...(Array.isArray(x.traits)?x.traits:Object.values(x.traits||{})).map(f=>typeof f==='string'?f:((f&&f.name)||'')+' '+((f&&f.desc)||''))].filter(Boolean).join(' ').replace(/<[^>]+>/g,' ')).slice(0,700), o={spell:{},feat:{},race:{},background:{},subclass:{}};
          PHB_SPELL_LIST.forEach(x=>o.spell[lc(x.name)]=T(x)); Object.values(PHB_FEATS).forEach(x=>o.feat[lc(x.name)]=T(x)); Object.values(PHB_BACKGROUNDS).forEach(x=>o.background[lc(x.name)]=T(x));
          Object.values(PHB_RACES).forEach(x=>{const n=lc(String(x.name).replace(/\s*\([^)]*\)\s*/g,' ')); o.race[n]=((o.race[n]||'')+' '+T(x)).trim().slice(0,1400);});
          Object.entries(PHB_SUBCLASSES).forEach(([k,x])=>{o.subclass[k]=T(x); o.subclass[k.split('/')[0]+'/'+lc(x.name)]=o.subclass[k];}); return o;})(), spells:PHB_SPELL_LIST.map(x=>[x.key,x.name]), feats:Object.entries(PHB_FEATS).map(([k,x])=>[k,x.name]), races:Object.entries(PHB_RACES).map(([k,x])=>[k,x.name,Object.values(x.subraces||{}).map(r=>r&&r.name).filter(Boolean)]),
        bgs:Object.entries(PHB_BACKGROUNDS).map(([k,x])=>[k,x.name]), classes:Object.entries(PHB_CLASSES).map(([k,x])=>[k,x.name]), subclasses:Object.entries(PHB_SUBCLASSES).map(([k,x])=>[k,x.name]),
        invocations:PHB_INVOCATIONS.map(x=>[x.clean||x.name,x.name]), maneuvers:PHB_MANEUVERS.map(x=>[x.name,x.name]), metamagic:PHB_METAMAGIC.map(x=>[x.name,x.name]), arcaneshots:Object.keys(ARCANE_SHOT_DESCS).map(n=>[n,n]), glossary:Object.keys(RULES_GLOSSARY).map(k=>[k,RULES_GLOSSARY[k].name]), conditions:Object.keys(CONDITION_INFO).map(k=>[k,k]), aliases:Object.keys(GLOSSARY_ALIASES).map(k=>[k,k])}}}""")
    json.dump(r, open(sys.argv[2],'w')); print({k:len(v) for k,v in r.items()}, {k:len(v) for k,v in r['rep'].items()})
