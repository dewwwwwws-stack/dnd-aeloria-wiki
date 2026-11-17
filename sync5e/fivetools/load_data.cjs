// Every 5e.tools entry of the given categories, from the official data, the playtest collection and homebrew, with
// copies resolved within each category. Shared by raw_pack.cjs (DM's 5e.tools page) and sheet_pack.cjs (the sheet's lists).
const fs = require('fs'), path = require('path');
module.exports = function loadData({ SITE, BREW, UA, BF, J2A, all, cats }) {
  const vsrc = fs.readFileSync(path.join(__dirname, 'vendor.js'), 'utf8') + '\nmodule.exports = FiveToolsVendor;';
  const vmod = new module.constructor(); vmod._compile(vsrc, 'vendor.js'); const V = vmod.exports;
  const CAT = new Set(cats);
  const FEATURES = ['classFeature', 'subclassFeature'];
// ── sources: official short names, the playtest and homebrew books ──
const J = JSON.parse(fs.readFileSync(J2A, 'utf8'));
const known = JSON.parse(fs.readFileSync(BF, 'utf8'));
// BREW_ALLOW: a JSON file listing the homebrew books the DM approved (+ books characters still use); only those are read
const allow = process.env.BREW_ALLOW ? new Set(JSON.parse(fs.readFileSync(process.env.BREW_ALLOW, 'utf8'))) : null;
const { srcOf, names, extra, files: bookFiles, abv, allowed } = require('./brew_sources.cjs')({ BREW, UA, known, J, all, allow });
const data = Object.fromEntries([...CAT, ...FEATURES].map((c) => [c, []]));
const fails = [];
const take = (d, origin) => { for (const c of Object.keys(data)) for (const e of d[c] || []) if (e && typeof e === 'object' && e.name) { e.__o = origin; data[c].push(e); } };
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { fails.push(`${f}: not readable (${e.message})`); return null; } };

// official
const D = path.join(SITE, 'data');
for (const f of fs.readdirSync(D)) if (f.endsWith('.json') && !/^(fluff|foundry|makebrew|renderdemo|changelog|converter|names|life|loot|encounter|msbcr|adventures|books|makecards|monsterfeatures|generated)/.test(f)) { const d = readJson(path.join(D, f)); if (d) take(d, 'official'); }
for (const sub of ['spells', 'class']) for (const f of fs.readdirSync(path.join(D, sub))) if (/^(spells|class)-.*\.json$/.test(f)) { const d = readJson(path.join(D, sub, f)); if (d) take(d, 'official'); }
// playtest and homebrew books
for (const [root, f, kind] of bookFiles) { const d = readJson(path.join(root, f)); if (d) take(d, kind); }
const srcField = (e) => e.source || (e.inherits && e.inherits.source) || '';
const bookOf = (e) => srcOf[srcField(e)] || abv(srcField(e) || 'Unknown');

// ── copies ("as X, but...") within a category ──
const norm = (s) => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
const NONE = { _MERGE_REQUIRES_PRESERVE: {} };
for (const c of Object.keys(data)) {
  const L = data[c]; if (!L.some((e) => e._copy)) continue;
  const by = new Map(); for (const e of L) { const k = norm(e.name) + '|' + norm(e.source) + (c === 'subclass' ? '|' + norm(e.className) : c === 'subrace' ? '|' + norm(e.raceName) : ''); if (!by.has(k)) by.set(k, e); }
  const busy = new Set(), bad = new Set();
  const resolve = (e) => {
    if (!e._copy) return true; if (bad.has(e)) return false; if (busy.has(e)) { bad.add(e); return false; }
    const p = e._copy, k = norm(p.name) + '|' + norm(p.source) + (c === 'subclass' ? '|' + norm(p.className) : c === 'subrace' ? '|' + norm(p.raceName) : '');
    const parent = by.get(k);
    if (!parent) { bad.add(e); fails.push(`${e.name} (${e.source}, ${c}): copies ${p.name} (${p.source}), which is not loaded`); return false; }
    busy.add(e);
    try { if (!resolve(parent)) { bad.add(e); return false; } const o = e.__o; V.copyApplier.getCopy(NONE, V.MiscUtil.copyFast(parent), e, null, {}); e.__o = o; delete e._copy; return true; }
    catch (err) { bad.add(e); fails.push(`${e.name} (${e.source}, ${c}): ${String(err && err.message || err).slice(0, 120)}`); return false; } finally { busy.delete(e); }
  };
  data[c] = L.filter((e) => resolve(e) || true);
}

  // a file can hold several books: entries of books that are not approved are dropped too
  if (allow) for (const c of Object.keys(data)) data[c] = data[c].filter((e) => e.__o === 'official' || allowed(bookOf(e)));
  return { data, srcOf, names, extra, abv, fails, bookOf, srcField, norm, V, allowed };
};
