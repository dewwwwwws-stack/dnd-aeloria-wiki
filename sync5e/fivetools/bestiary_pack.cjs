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
// what else can bring a creature out: spells and magic items whose text links the creature ({@creature ...}) and talks
// about summoning, conjuring, animating or turning into it. 5e.tools' own summonedBySpell field misses Animate Dead,
// Find Steed and every item (Figurine of Wondrous Power, Bag of Tricks...). Name-matched; the sheet shows a creature to
// a player only when their character knows/prepares the spell or owns the item.
const SUM_BY = { spell: new Map(), item: new Map() };
{
  const walk = (x, acc) => { if (typeof x === 'string') acc.push(x); else if (Array.isArray(x)) x.forEach((y) => walk(y, acc)); else if (x && typeof x === 'object') for (const [k, v] of Object.entries(x)) if (k !== 'name' && k !== 'source') walk(v, acc); };
  const scan = (kind, e, rx) => { const acc = []; walk(e.entries || [], acc); walk(e.entriesHigherLevel || [], acc); const t = acc.join(' '); if (!rx.test(t)) return;
    for (const m of t.matchAll(/\{@creature ([^}|]+)/g)) { const n = F.norm(m[1].trim()); const M = SUM_BY[kind]; if (!M.has(n)) M.set(n, new Set()); M.get(n).add(e.name); } };
  const SPELL_RX = /\b(summon|conjur|animate|raise|creates? an?|calls? forth|appears? in an unoccupied|becomes? (your|a)|you create)/i;
  const ITEM_RX = /\b(summon|conjur|becomes? a|turns? into|transforms? into|animate|appears? in an unoccupied|comes to life|living creature|pull(s|ed)? (an?|the) .{0,30}out|takes the form|assumes the form|calls? forth|springs? forth)/i;
  const NOT_SPELLS = new Set(['Wish', 'Major Image']);   // they name a creature only as an example
  // spells: the newest printing only (the 2024 Find Steed brings the Otherworldly Steed, not a warhorse)
  try { const si = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'spells', 'index.json'), 'utf8')); for (const f of Object.values(si)) for (const sp of JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'spells', f), 'utf8')).spell || []) if (!NOT_SPELLS.has(sp.name) && !(sp.reprintedAs && sp.reprintedAs.length)) scan('spell', sp, SPELL_RX); } catch (e) { fails.push('summoning spells: ' + e.message); }
  try { for (const it of JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'items.json'), 'utf8')).item || []) scan('item', it, ITEM_RX); } catch (e) { fails.push('summoning items: ' + e.message); }
}
const out = {}; for (const x of res.failed) fails.push(`${x.name} (${x.source}): ${x.why}`);
for (const m of res.ok) {
  let sb; try { sb = conv.convert(m); } catch (e) { fails.push(`${m.name} (${m.source}): ${e.message}`); continue; }
  delete sb.image;
  const a = bookFor(m) || brewSrc[m.source] || abv(m.source);
  const tk = m.tokenUrl || (m.token && m.token.name ? `bestiary/tokens/${m.token.source || m.source}/${m.token.name}.webp` : m.hasToken ? `bestiary/tokens/${m.source}/${m.name.replace(/"/g, '')}.webp` : null);
  const rp = (m.reprintedAs || [])[0]; const rpk = rp ? (typeof rp === 'string' ? rp : rp.uid || '') : '';
  const e = { k: keyOf(m), n: m.name, s: m.source, a, cr: typeof m.cr === 'object' ? (m.cr && m.cr.cr) : m.cr, t: sb.type, sz: sb.size, env: m.environment || undefined, al: sb.alignment,
    fam: m.familiar ? 1 : undefined, sum: m.summonedBySpell ? String(m.summonedBySpell).split('|')[0] : undefined, suml: m.summonedBySpellLevel || undefined,
    ss: (() => { const S = SUM_BY.spell.get(F.norm(m.name)); return S ? [...S].sort() : undefined; })(), si: (() => { const S = SUM_BY.item.get(F.norm(m.name)); return S ? [...S].sort() : undefined; })(),
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
