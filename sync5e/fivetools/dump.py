import json, sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto('file://'+sys.argv[1]); pg.wait_for_timeout(4000)
    r=pg.evaluate("""()=>{const f=a=>(a||[]).map(x=>({key:x.key,name:x.name,source:x.source||null,desc:(x.desc||"").slice(0,1500)}));
      return {magic:f(typeof DMG_MAGIC_ITEMS!=='undefined'?DMG_MAGIC_ITEMS:window.DMG_MAGIC_ITEMS), au:f(typeof AU_MAGIC_ITEMS!=='undefined'?AU_MAGIC_ITEMS:null),
      weapons:f(PHB_WEAPONS), armour:f(PHB_ARMOUR), gear:f(PHB_GEAR), val:f(VALUABLES_CATALOG), mnt:f(MOUNTS_VEHICLES_CATALOG),
      aliases:Object.keys(typeof ITEM_KEY_ALIASES!=='undefined'?ITEM_KEY_ALIASES:{}), bases:Object.keys(typeof ITEM_BASES!=='undefined'?ITEM_BASES:{}), ammo:Object.keys(AMMO_TYPES)}}""")
    json.dump(r, open(sys.argv[2],'w')); print({k:len(v) for k,v in r.items()})
