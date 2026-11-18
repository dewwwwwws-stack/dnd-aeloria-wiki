// Short names for homebrew and playtest books, the same in every pack (bestiary, library): the books the sheet already
// uses (brew_files.json) keep theirs; the playtest books use 5e.tools' own; every other homebrew book (only with
// ALL_BREW) keeps its abbreviation unless another book already has it, then "~2", "~3"... Order is fixed (known
// books, playtest, then homebrew folders and files sorted), so a book's short name never depends on what a pack reads.
const fs = require('fs'), path = require('path');
// allow: short names of the homebrew books whose contents may be read (the DM's approvals); null = every book.
// Names are still given to every book (so they never change), and with `count` each book's entries are counted for
// the book list on the Sources page.
module.exports = function brewSources({ BREW, UA, known, J, all, allow, count }) {
  const counts = {};
  // a book made of dated parts (D&D Beyond Drops: one "book" per monthly drop, each entry's page = that drop's date):
  // every part becomes its own book, "BndD-2605" "D&D Beyond Drops: Horror Maps (Jun 2026)", inside the parent's group
  const parts = {}, parentOf = {};   // parts[json][date] = short name; parentOf[short name] = the parent's short name
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const srcOf = {}, names = {}, extra = new Set(), taken = new Map(), files = [];
  const abv = (s) => (J[s] ? (Array.isArray(J[s]) ? J[s][0] : J[s]) : s);
  for (const [j, v] of Object.entries(J)) taken.set(Array.isArray(v) ? v[0] : v, j);
  const read = (root, f) => { try { return JSON.parse(fs.readFileSync(path.join(root, f), 'utf8')); } catch (e) { return null; } };
  // the book an entry belongs to: its source's short name, or the dated part of it (D&D Beyond Drops)
  function bookFor(e) { if (!e) return null; const a = srcOf[e.source]; const P = parts[e.source]; return P && P[e.page] ? P[e.page] : a; }
  const book = (root, f, given, kind) => {
    const d = read(root, f); const m = d && d._meta; if (!m) return;
    const mine = [];
    for (const s of m.sources || []) {
      if (!s.json || srcOf[s.json]) continue;
      let a = given || s.abbreviation || s.json, n = 2;
      if (kind === 'ua' && J[s.json]) a = abv(s.json);
      else if (!given) while (taken.has(a) && taken.get(a) !== s.json) a = `${s.abbreviation || s.json}~${n++}`;
      taken.set(a, s.json); srcOf[s.json] = a;
      const stem = path.basename(f, '.json').split('; ').slice(1).join('; ');
      names[a] = [s.full && s.full !== a && s.full !== s.json ? s.full : (stem || s.full || s.json), (s.authors || []).join(', '), f, kind === 'ua' ? 'playtest' : 'homebrew'];
      if (kind === 'extra') extra.add(a);
    }
    for (const s of m.sources || []) if (s.json && srcOf[s.json]) mine.push(srcOf[s.json]);
    for (const b of d.book || []) {
      if (!b || !/^\d{4}-\d\d-\d\d$/.test(String(b.id || '')) || !srcOf[b.source]) continue;
      const parent = srcOf[b.source], y = b.id.slice(2, 4), mo = b.id.slice(5, 7), a = `${parent}-${y}${mo}`;
      (parts[b.source] = parts[b.source] || {})[b.id] = a; parentOf[a] = parent;
      const pn = names[parent] || [parent, '', f, 'homebrew'];
      names[a] = [`${pn[0]}: ${String(b.name || '').replace(/^.*?[—–-]\s*/, '')} (${MON[+mo - 1]} 20${y})`, pn[1], f, pn[3], b.id];
      if (extra.has(parent)) extra.add(a);
    }
    if (count) for (const [k, v] of Object.entries(d)) if (k !== '_meta' && Array.isArray(v)) for (const e of v) { const a = (e && bookFor(e)) || mine[0]; if (!a) continue; const c = counts[a] = counts[a] || {}; c[k] = (c[k] || 0) + 1; }
    // contents only for books the DM approved (playtest books always); a part of a book counts as its book too
    if (kind === 'ua' || !allow || mine.some((a) => allow.has(a)) || Object.values(parts).some((P) => Object.values(P).some((a) => mine.includes(parentOf[a]) && allow.has(a)))) files.push([root, f, kind]);
  };
  const knownFiles = new Set(Object.values(known).flat());
  for (const [a, fl] of Object.entries(known)) for (const f of fl) book(BREW, f, a, 'brew');
  const dirs = (root) => fs.readdirSync(root).filter((d) => !d.startsWith('.') && !d.startsWith('_') && fs.statSync(path.join(root, d)).isDirectory()).sort();
  if (UA && fs.existsSync(UA)) for (const d of dirs(UA)) for (const f of fs.readdirSync(path.join(UA, d)).sort()) if (f.endsWith('.json')) book(UA, `${d}/${f}`, null, 'ua');
  if (all) for (const d of dirs(BREW)) for (const f of fs.readdirSync(path.join(BREW, d)).sort()) if (f.endsWith('.json') && !knownFiles.has(`${d}/${f}`)) book(BREW, `${d}/${f}`, null, 'extra');
  const allowed = (a) => !allow || !names[a] || names[a][3] === 'playtest' || allow.has(a) || (parentOf[a] && allow.has(parentOf[a]));
  return { srcOf, names, extra, files, abv, counts, allowed, bookFor, parts, parentOf };
};
