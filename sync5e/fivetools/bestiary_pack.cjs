// Bestiary pack: every 5e.tools creature (official + the loaded homebrew books), _copy-resolved and converted to the
// Fantasy Statblocks shape the user's notes use. One file per book (split under 650 KB) + an index.
// Usage: node bestiary_pack.cjs SITE BREW brew_files.json json2abv.json OUT_DIR [UA_DIR]
// Consumers (sheet Vault, Character Sheet Sync) filter by the books the DM approved and prefer the newest printing.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const [SITE, BREW, BF, J2A, OUT, UA_DIR] = process.argv.slice(2);
const src = fs.readFileSync(path.join(__dirname, 'vendor.js'), 'utf8') + '\n' + fs.readFileSync(path.join(__dirname, 'core.js'), 'utf8') + '\nmodule.exports = { FiveTools };';
const mod = new module.constructor(); mod._compile(src, 'fivetools.js'); const F = mod.exports.FiveTools;
const J = JSON.parse(fs.readFileSync(J2A, 'utf8'));
const abv = s => (J[s] ? (Array.isArray(J[s]) ? J[s][0] : J[s]) : s);
const D = path.join(SITE, 'data', 'bestiary'), idx = JSON.parse(fs.readFileSync(path.join(D, 'index.json'), 'utf8'));
let all = []; for (const f of Object.values(idx)) all = all.concat(JSON.parse(fs.readFileSync(path.join(D, f), 'utf8')).monster || []);
const templates = JSON.parse(fs.readFileSync(path.join(D, 'template.json'), 'utf8')).monsterTemplate || [];
// homebrew: short names shared with the library pack (brew_sources.cjs); with ALL_BREW=1 every homebrew book is read
const fails = [];
const allow = process.env.BREW_ALLOW ? new Set(JSON.parse(fs.readFileSync(process.env.BREW_ALLOW, 'utf8'))) : null;   // only approved homebrew books
const { srcOf: brewSrc, names, extra, files: bookFiles, allowed, bookFor } = require('./brew_sources.cjs')({ BREW, UA: UA_DIR, known: JSON.parse(fs.readFileSync(BF, 'utf8')), J, all: !!process.env.ALL_BREW, allow });
for (const [root, f] of bookFiles) {
  let d; try { d = JSON.parse(fs.readFileSync(path.join(root, f), 'utf8')); } catch (e) { fails.push(`${f}: not readable (${e.message})`); continue; }
  for (const m of d.monster || []) { if (!brewSrc[m.source]) brewSrc[m.source] = m.source; if (allowed(bookFor(m) || brewSrc[m.source])) all.push(m); }
}
// spell links in the user's own form: [[Tools/Spells/Gust Of Wind|Gust of Wind]] (the plugin may re-point the folder)
const titleCase = n => String(n).replace(/\b([a-z])/g, (m, c) => c.toUpperCase());
const res = F.resolveCopies(all, templates); const conv = F.converter({ spellNote: (k, name) => 'Tools/Spells/' + titleCase(name) });
const keyOf = m => F.norm(m.name) + '|' + String(m.source).toLowerCase();
const out = {}; for (const x of res.failed) fails.push(`${x.name} (${x.source}): ${x.why}`);
for (const m of res.ok) {
  let sb; try { sb = conv.convert(m); } catch (e) { fails.push(`${m.name} (${m.source}): ${e.message}`); continue; }
  delete sb.image;
  const a = bookFor(m) || brewSrc[m.source] || abv(m.source);
  const tk = m.tokenUrl || (m.token && m.token.name ? `bestiary/tokens/${m.token.source || m.source}/${m.token.name}.webp` : m.hasToken ? `bestiary/tokens/${m.source}/${m.name.replace(/"/g, '')}.webp` : null);
  const rp = (m.reprintedAs || [])[0]; const rpk = rp ? (typeof rp === 'string' ? rp : rp.uid || '') : '';
  const e = { k: keyOf(m), n: m.name, s: m.source, a, cr: typeof m.cr === 'object' ? (m.cr && m.cr.cr) : m.cr, t: sb.type, sz: sb.size, env: m.environment || undefined, al: sb.alignment,
    fam: m.familiar ? 1 : undefined, sum: m.summonedBySpell ? String(m.summonedBySpell).split('|')[0] : undefined, suml: m.summonedBySpellLevel || undefined,
    npc: m.isNpc ? 1 : undefined, tk: tk || undefined, rp: rpk ? F.norm(rpk.split('|')[0]) + '|' + String(rpk.split('|')[1] || '').toLowerCase() : undefined, sb };
  (out[a] = out[a] || []).push(e);
}
fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) if (/^b_.*\.json$|^index\.json$/.test(f)) fs.unlinkSync(path.join(OUT, f));
const index = { v: 1, files: {}, counts: {}, total: 0, names: Object.fromEntries(Object.entries(names).filter(([a]) => out[a])), extra: [...extra].filter(a => out[a]).sort(), nfails: fails.length, fails: fails.slice(0, 200) };
const LIMIT = 650000, usedBase = new Set();
const safe = a => { let b = a.replace(/[^A-Za-z0-9]+/g, '_'); if (usedBase.has(b.toLowerCase())) b += '_' + crypto.createHash('sha1').update(a).digest('hex').slice(0, 6); usedBase.add(b.toLowerCase()); return b; };
for (const [a, L] of Object.entries(out)) {
  const base = safe(a);
  L.sort((x, y) => x.n.localeCompare(y.n)); const parts = [[]]; let size = 0;
  for (const e of L) { const z = JSON.stringify(e).length; if (size + z > LIMIT && parts[parts.length - 1].length) { parts.push([]); size = 0; } parts[parts.length - 1].push(e); size += z; }
  index.files[a] = parts.map((p, i) => { const name = `b_${base}${parts.length > 1 ? '_' + (i + 1) : ''}.json`; const txt = JSON.stringify(p);
    fs.writeFileSync(path.join(OUT, name), txt); return { f: name, h: crypto.createHash('sha1').update(txt).digest('hex').slice(0, 12), n: p.length }; });
  index.counts[a] = L.length; index.total += L.length;
}
fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index));
console.log(JSON.stringify({ total: index.total, books: Object.keys(out).length, files: Object.values(index.files).flat().length, fails: fails.length, firstFails: fails.slice(0, 3) }));
