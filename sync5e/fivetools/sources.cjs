// Source names and groups, the way 5e.tools sorts them. Usage: node sources.cjs SITE BREW brew_files.json OUT.json [UA_REPO]
// OUT: { ABV: [full name, group] }, group = core | adventure | partnered | other | playtest | homebrew
const fs = require('fs'), vm = require('vm'), path = require('path');
const [SITE, BREW, BF, OUT, UA] = process.argv.slice(2);
const ctx = vm.createContext({ console, globalThis: null }); ctx.globalThis = ctx; ctx.window = ctx;
const src = fs.readFileSync(path.join(SITE, 'js/parser.js'), 'utf8').replace(/^\s*(import|export) .*$/gm, '').replace(/^"use strict";/, '');
try { vm.runInContext(src + '\n;globalThis.__P = Parser;', ctx, { filename: 'parser.js' }); } catch (e) { if (!ctx.__P) { try { vm.runInContext('globalThis.__P = Parser;', ctx); } catch (e2) { throw e; } } }
const P = ctx.__P, out = {};
for (const j of Object.keys(P.SOURCE_JSON_TO_FULL)) {
  const abv = P.SOURCE_JSON_TO_ABV[j] || j;
  const g = /^(X?UA|UA)/.test(j) || (P.SOURCE_PREFIX_TO_SHORT && /^(UA|XUA)/.test(j)) ? 'playtest'
    : P.SOURCES_PARTNERED_WOTC.has(j) ? 'partnered' : P.SOURCES_NON_STANDARD_WOTC.has(j) ? 'other'
    : P.SOURCES_ADVENTURES.has(j) ? 'adventure' : 'core';
  out[abv] = [P.SOURCE_JSON_TO_FULL[j], g];
}
const B = JSON.parse(fs.readFileSync(BF, 'utf8'));
for (const [abv, files] of Object.entries(B)) for (const f of files) {
  const m = JSON.parse(fs.readFileSync(path.join(BREW, f), 'utf8'))._meta.sources.find(s => s.abbreviation === abv);
  if (m) out[abv] = [m.full, m.partnered ? 'partnered' : 'homebrew'];
}
if (UA) { const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => e.name.startsWith('.') || e.name.startsWith('_') ? [] : e.isDirectory() ? walk(path.join(d, e.name)) : e.name.endsWith('.json') ? [path.join(d, e.name)] : []);
  for (const f of walk(UA)) { try { for (const m of JSON.parse(fs.readFileSync(f, 'utf8'))._meta.sources || []) if (m.abbreviation && !out[m.abbreviation]) out[m.abbreviation] = [m.full, 'playtest']; } catch (e) {} } }
// the sheet's own codes
Object.assign(out, { Homebrew: ['Homebrew (your own items)', 'homebrew'], Unknown: ['No source given', 'homebrew'] });
if (out.TCE && !out.TCoE) out.TCoE = [out.TCE[0] + ' (old code)', out.TCE[1]]; if (out.ERLW && !out.WGE) out.WGE = ["Wayfinder's Guide to Eberron", 'core'];
for (const k of ['WoW', 'ICC']) if (out[k]) out[k][1] = 'universes';
out.UA = ['Unearthed Arcana (playtest, packet not recorded)', 'playtest']; out.Legacy = ['2014 rules (book not recorded)', 'core']; out['Core rules'] = ["Player's Handbook (2024)", 'core'];
if (!out.WoW) out.WoW = ['D&D: World of Warcraft', 'universes'];
fs.writeFileSync(OUT, JSON.stringify(out));
fs.writeFileSync(OUT.replace(/\.json$/, '') + '.json2abv.json', JSON.stringify(Object.fromEntries(Object.keys(P.SOURCE_JSON_TO_FULL).map(j => [j, [P.SOURCE_JSON_TO_ABV[j] || j, (P.SOURCE_JSON_TO_DATE || {})[j] || null]]))));
const c = {}; Object.values(out).forEach(v => c[v[1]] = (c[v[1]] || 0) + 1); console.log(Object.keys(out).length, c);
