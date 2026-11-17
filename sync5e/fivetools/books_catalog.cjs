// The list of every homebrew and playtest book (name, authors, how many spells, creatures, items... each has) - no
// contents. The Sources page shows it so the DM can approve a book; the weekly sync then stores that book's contents.
// Usage: node books_catalog.cjs BREW UA brew_files.json json2abv.json OUT_FILE
const fs = require('fs');
const [BREW, UA, BF, J2A, OUT] = process.argv.slice(2);
const B = require('./brew_sources.cjs')({ BREW, UA, known: JSON.parse(fs.readFileSync(BF, 'utf8')), J: JSON.parse(fs.readFileSync(J2A, 'utf8')), all: true, allow: new Set(), count: true });
const KEEP = { monster: 'creatures', spell: 'spells', feat: 'feats', item: 'items', baseitem: 'items', magicvariant: 'items', race: 'species', subrace: 'species', background: 'backgrounds', class: 'classes', subclass: 'subclasses', optionalfeature: 'class options' };
const books = {};
for (const [a, n] of Object.entries(B.names)) {
  const c = {}; for (const [k, v] of Object.entries(B.counts[a] || {})) { const g = KEEP[k] || 'other'; c[g] = (c[g] || 0) + v; }
  if (!Object.keys(c).length) continue;
  books[a] = [n[0], n[1], n[3], c, B.extra.has(a) ? 1 : 0];   // name, authors, 'homebrew' | 'playtest', counts, 1 = from the full homebrew collection
}
fs.writeFileSync(OUT, JSON.stringify({ v: 1, books }));
console.log(JSON.stringify({ books: Object.keys(books).length, bytes: fs.statSync(OUT).size }));
