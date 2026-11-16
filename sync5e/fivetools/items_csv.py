#!/usr/bin/env python3
"""Items.csv from 5e.tools itself: the repo's own items page, run headless, with the homebrew and playtest
books loaded, writes the same "Table View → Download CSV" file the user downloaded from 5e.tools by hand.

Usage: python3 items_csv.py OUT.csv
Needs: SITE  a checkout of 5etools-mirror-3/5etools-src (without data/adventure, data/book is fine)
       BREW  a checkout of TheGiddyLimit/homebrew (the files in brew_files.json)
       UA    a checkout of TheGiddyLimit/unearthed-arcana (its files with items)
"""
import json, os, re, shutil, subprocess, sys, time, socket, urllib.parse
SITE = os.environ.get('SITE', '/tmp/claude-0/5e/src')
BREW = os.environ.get('BREW', '/tmp/claude-0/hb/r')
UA = os.environ.get('UA', '/tmp/claude-0/ua')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]

def stage(src_root, files, dest):
    """Copies the files into the site's homebrew/ or prerelease/ folder, listed for loading on start."""
    d = os.path.join(SITE, dest)
    for f in os.listdir(d):
        if f != 'index.json': os.remove(os.path.join(d, f))
    names = []
    for f in files:
        name = os.path.basename(f)
        shutil.copy(os.path.join(src_root, f), os.path.join(d, name))
        names.append(name)
    idx = json.load(open(os.path.join(d, 'index.json')))
    idx['toImport'] = names
    json.dump(idx, open(os.path.join(d, 'index.json'), 'w'), indent='\t')
    return names

brew = json.load(open(os.path.join(HERE, 'brew_files.json')))
brew_files = sorted({f for v in brew.values() for f in v})
ua_props = json.load(open(os.path.join(UA, '_generated/index-props.json')))
ua_files = sorted(ua_props['item'])
print('homebrew', len(stage(BREW, brew_files, 'homebrew')), '| playtest', len(stage(UA, ua_files, 'prerelease')))

s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'], cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    from playwright.sync_api import sync_playwright
    time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        # the page fetches the homebrew and playtest repos' files (indexes, books a book depends on) from GitHub:
        # answered from the local checkouts (git fetches a file the checkout lacks); fonts and art are not needed
        repos = {'homebrew': BREW, 'unearthed-arcana': UA}
        RAW = re.compile(r'^https://(?:raw\.githubusercontent\.com|raw\.githack\.com)/TheGiddyLimit/([\w-]+)/(?:master|main)/(.+)$|^https://cdn\.jsdelivr\.net/gh/TheGiddyLimit/([\w-]+)@(?:master|main)/(.+)$')
        served = {'ok': 0, 'missing': []}
        def route(r):
            url = r.request.url
            if url.startswith(f'http://127.0.0.1:{port}/'): return r.continue_()
            m = RAW.match(url.split('?')[0])
            if m:
                repo, path = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
                root = repos.get(repo); path = urllib.parse.unquote(path)
                if root and path.endswith('.json'):
                    f = os.path.join(root, path)
                    data = open(f, 'rb').read() if os.path.exists(f) else subprocess.run(['git', '-C', root, 'cat-file', 'blob', f'HEAD:{path}'], capture_output=True).stdout
                    if data:
                        served['ok'] += 1
                        return r.fulfill(status=200, body=data, headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})
                    served['missing'].append(path)
            return r.fulfill(status=404, body='')
        pg.route('**/*', route)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(f'http://127.0.0.1:{port}/items.html', timeout=120000)
        # the list is ready once every item (official, homebrew, playtest) is in
        pg.wait_for_function("() => typeof dbg_page !== 'undefined' && dbg_page._dataList && dbg_page._dataList.length > 1000", timeout=300000)
        pg.wait_for_timeout(8000)
        n0 = -1
        for _ in range(30):
            n = pg.evaluate('dbg_page._dataList.length')
            if n == n0: break
            n0 = n; pg.wait_for_timeout(3000)
        info = pg.evaluate("""() => {
          const opts = dbg_page._tableViewOptions || dbg_page.__tableViewOptions || dbg_page._listPageOptions?.tableViewOptions;
          return { n: dbg_page._dataList.length, hasOpts: !!opts, keys: Object.keys(dbg_page).filter(k => /table/i.test(k)) };
        }""")
        print('items loaded', info, '| repo files served', served['ok'], 'missing', served['missing'][:5])
        csv = pg.evaluate("""() => {
          const opts = dbg_page._tableViewOptions;
          const colTransforms = opts.colTransforms;
          const rdState = new UtilsTableview._RenderState();
          rdState.comp = { _state: Object.fromEntries(Object.keys(colTransforms).map((k) => [k, true])) };
          UtilsTableview._getTableHtml({ rdState, entities: dbg_page._dataList, colTransforms, additionalData: opts.additionalData, sorter: opts.sorter });
          return UtilsTableview._getAsCsv({ colTransforms, rdState });
        }""")
        open(OUT, 'w', encoding='utf-8').write(csv)
        # beside it: each item's reprint (newest wins) and picture, as the page knows them
        side = pg.evaluate("""async () => {
          const uid = (n, s) => `${String(n).toLowerCase()}|${String(s).toLowerCase()}`;
          const have = new Set(dbg_page._dataList.map((it) => uid(it.name, it.source)));
          const out = [];
          for (const it of dbg_page._dataList) {
            const rep = (it.reprintedAs || []).map((r) => (typeof r === 'string' ? r : r.uid || '')).filter(Boolean);
            const by = rep.find((r) => { const [n, s] = r.split('|'); return have.has(uid(n, s || it.source)); }) || null;
            let img = null;
            if (it.hasFluffImages || it.fluff || it._variantName) {
              try {
                const fl = await dbg_page._pFnGetFluff(it);
                const im = (fl && fl.images || []).find((x) => x && x.href);
                if (im) img = im.href.type === 'internal' ? { repo: 'img', path: im.href.path } : { url: im.href.url };
              } catch (e) { /* none */ }
            }
            out.push({ name: it.name, source: it.source, abv: Parser.sourceJsonToAbv(it.source), reprintedBy: by, img, variant: it._variantName || null, base: it._baseName || null });
          }
          return out;
        }""")
        json.dump(side, open(OUT.replace('.csv', '') + '.meta.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print('meta: reprinted', sum(1 for x in side if x['reprintedBy']), '| with a picture', sum(1 for x in side if x['img']))
        print('wrote', OUT, len(csv), 'chars;', 'page errors:', errs[:3])
        b.close()
finally:
    srv.terminate()
