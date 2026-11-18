// New for the sheet: 5e.tools spells, feats, backgrounds, species, classes, subclasses and class options (invocations,
// maneuvers, metamagic) that the sheet does not have yet, converted into the sheet's own shapes so they work in its
// pickers. Add-only: anything the sheet already has (by name) is left out, so its own versions and house rules win.
// Each entry carries `_w`: what was wired automatically and what still needs doing (the DM's "New from 5e.tools" list).
// Usage: node sheet_pack.cjs SITE BREW UA brew_files.json json2abv.json live.json OUT_DIR   (ALL_BREW=1: all homebrew)
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const [SITE, BREW, UA, BF, J2A, LIVE, OUT] = process.argv.slice(2);
const KINDS = ['spell', 'feat', 'background', 'race', 'subrace', 'class', 'subclass', 'optionalfeature', 'variantrule', 'action', 'sense', 'skill', 'status', 'condition', 'disease'];
const L = require('./load_data.cjs')({ SITE, BREW, UA, BF, J2A, all: !!process.env.ALL_BREW, cats: KINDS });
const { data, names, extra, bookOf, srcField, fails, norm } = L;
// rules text as the sheet's glossary shows it: plain safe HTML, links to other entries dropped (the glossary links its own terms)
let FEAT_MAP_R = null;
const RH = require('./render_html.cjs')({ get FEAT_MAP() { return FEAT_MAP_R; }, featLookup: () => null, norm });
const J = JSON.parse(fs.readFileSync(J2A, 'utf8'));
const OFFICIAL = new Set(Object.values(J).map((v) => (Array.isArray(v) ? v[0] : v)));
const live = JSON.parse(fs.readFileSync(LIVE, 'utf8')).rep || {};

// ── helpers ──
const csrc = fs.readFileSync(path.join(__dirname, 'vendor.js'), 'utf8') + '\n' + fs.readFileSync(path.join(__dirname, 'core.js'), 'utf8') + '\nmodule.exports = { FiveTools };';
const cmod = new module.constructor(); cmod._compile(csrc, 'core.js'); const conv = cmod.exports.FiveTools.converter({});
const tags = (s) => conv.tags(s).replace(/\[\[[^|\]]*\|([^\]]*)\]\]/g, '$1').replace(/\[\[([^\]]*)\]\]/g, '$1');
const slug = (s) => String(s || '').toLowerCase().replace(/['’]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
const lc = (s) => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
const bare = (s) => lc(String(s).replace(/\s*\([^)]*\)\s*/g, ' '));
// a subclass's core name: "Path of the Berserker" / "Berserker", "Archfey Patron" / "The Archfey" → "berserker", "archfey"
const core = (s) => lc(s).replace(/\s*\([^)]*\)/g, '').replace(/^(path|college|circle|oath|way|school|order|domain|tradition|archetype|conclave|discipline) of (the )?/, '').replace(/^the /, '').replace(/ (domain|patron|sorcery|bloodline|origin|college|circle|path|oath|tradition|order|school)$/, '').trim();
const cap = (s) => String(s || '').replace(/\b[a-z]/g, (c) => c.toUpperCase());
const ABIL = { str: 'Strength', dex: 'Dexterity', con: 'Constitution', int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma' };
const SCHOOL = { A: 'Abjuration', C: 'Conjuration', D: 'Divination', E: 'Enchantment', V: 'Evocation', I: 'Illusion', N: 'Necromancy', T: 'Transmutation', P: 'Psionic' };

// entries → plain paragraphs (the sheet's text style: "Name. text")
let FEAT_MAP = null, featLookup = null;
function paras(e) {
  if (e == null) return [];
  if (typeof e === 'string' || typeof e === 'number') return [tags(e)].filter(Boolean);
  if (Array.isArray(e)) return e.flatMap(paras);
  switch (e.type) {
    case 'list': return (e.items || []).flatMap((i) => { const p = typeof i === 'string' ? [tags(i)] : i && (i.type === 'item' || i.type === 'itemSub') ? [`${tags(i.name || '')} ${paras(i.entries || i.entry || '').join(' ')}`.trim()] : paras(i); return p.map((x) => '• ' + x); });
    case 'item': case 'itemSub': case 'itemSpell': return [`${tags(e.name || '')} ${paras(e.entries || e.entry || '').join(' ')}`.trim()];
    case 'table': return [[tags(e.caption || ''), ...(e.rows || []).map((r) => (r && !Array.isArray(r) ? r.row || [] : r || []).map((c) => (c && typeof c === 'object' ? (c.type === 'cell' ? (c.roll ? ('exact' in c.roll ? c.roll.exact : `${c.roll.min}–${c.roll.max}`) : paras(c.entry).join(' ')) : paras(c).join(' ')) : tags(c))).join(': '))].filter(Boolean).join('; ')];
    case 'image': case 'gallery': case 'hr': return [];
    case 'abilityDc': return [`${tags(e.name)} save DC = 8 + your Proficiency Bonus + your ${(e.attributes || []).map((a) => ABIL[a] || a).join(' or ')} modifier`];
    case 'abilityAttackMod': return [`${tags(e.name)} attack modifier = your Proficiency Bonus + your ${(e.attributes || []).map((a) => ABIL[a] || a).join(' or ')} modifier`];
    case 'refClassFeature': case 'refSubclassFeature': { const f = featLookup && featLookup(e.type === 'refClassFeature' ? 'class' : 'subclass', String(e.classFeature || e.subclassFeature || '').split('|')); return f ? named(f.name, f.entries) : []; }
    case 'refOptionalfeature': return [tags(String(e.optionalfeature || '').split('|')[0])];
  }
  return e.name ? named(e.name, e.entries || e.entry || e.items) : paras(e.entries || e.entry || e.items || []);
}
function named(name, body) { const p = paras(body); const n = tags(name); const lab = /[.:!?]$/.test(n) ? n : n + '.'; return p.length ? [`${lab} ${p[0]}`, ...p.slice(1)] : [lab]; }
const pipe = (e) => paras(e).join(' | ');
// "once per Long Rest", "a number of times equal to your Proficiency Bonus" → the sheet's usages / recovery
function usage(text) {
  const t = String(text);
  const rec = /Short or Long Rest/i.test(t) ? 'short rest' : /Long Rest/i.test(t) ? 'long rest' : /Short Rest/i.test(t) ? 'short rest' : null;
  if (!rec) return null;
  if (/number of times equal to your Proficiency Bonus/i.test(t)) return { usages: 'prof_bonus', recovery: rec };
  const m = /number of times equal to your (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) modifier/i.exec(t);
  if (m) return { usages: 'mod_' + m[1].slice(0, 3).toLowerCase(), recovery: rec };
  if (/(Once you use this|you can't (use|do) (it|so|this) again until you finish)/i.test(t)) return { usages: /twice/i.test(t) ? 2 : 1, recovery: rec };
  return null;
}

// ── what the sheet already has (by name), and the spell keys it knows ──
const have = {
  spell: new Set((live.spells || []).map(([, n]) => lc(n))), feat: new Set((live.feats || []).map(([, n]) => lc(n))),
  race: new Set((live.races || []).flatMap(([k, n, subs]) => [bare(n), lc(n), lc(k), ...(subs || []).flatMap((x) => [lc(x), lc(x) + ' ' + bare(n), bare(n) + ' (' + lc(x) + ')'])])), background: new Set((live.bgs || []).map(([, n]) => lc(n))),
  class: new Set((live.classes || []).flatMap(([k, n]) => [lc(n), lc(k)])), subclass: new Set((live.subclasses || []).flatMap(([k, n]) => [lc(k), k.split('/')[0] + '/' + lc(n), k.split('/')[0] + '/' + core(k.split('/')[1]), k.split('/')[0] + '/' + core(n)])),
  invocation: new Set((live.invocations || []).map(([c]) => lc(c))), maneuver: new Set((live.maneuvers || []).map(([n]) => lc(n))), metamagic: new Set((live.metamagic || []).map(([n]) => lc(n))),
  arcaneshot: new Set((live.arcaneshots || []).map(([n]) => lc(n))),
  rule: new Set([...(live.glossary || []).flatMap(([k, n]) => [lc(k), lc(n)]), ...(live.conditions || []).map(([k]) => lc(k)), ...(live.aliases || []).map(([k]) => lc(k))]), rune: new Set(['cloud rune', 'fire rune', 'frost rune', 'hill rune', 'stone rune', 'storm rune']),   // the Rune Knight's own six (fighter step)
};
const spellKeyOf = new Map((live.spells || []).map(([k, n]) => [lc(n), k]));
const usedKeys = { spell: new Set((live.spells || []).map(([k]) => k)), feat: new Set((live.feats || []).map(([k]) => k)), race: new Set((live.races || []).map(([k]) => k)), background: new Set((live.bgs || []).map(([k]) => k)) };
const keyFor = (kind, name, book) => { let k = slug(name); if (usedKeys[kind].has(k)) k = slug(name + ' ' + book); let n = 2; const b = k; while (usedKeys[kind].has(k)) k = b + '_' + n++; usedKeys[kind].add(k); return k; };
const classKey = (n) => slug(n);

// class features (for classes and subclasses)
FEAT_MAP = new Map();
for (const x of data.classFeature) FEAT_MAP.set(lc([x.name, x.className, x.classSource, x.level, x.source].join('|')), x);
for (const x of data.subclassFeature) FEAT_MAP.set(lc([x.name, x.className, x.classSource, x.subclassShortName, x.subclassSource, x.level, x.source].join('|')), x);
featLookup = (cls, p) => {
  if (cls === 'class') { const [n, cn, cs0, lv, fs0] = p; const cs = cs0 || 'PHB'; return FEAT_MAP.get(lc([n, cn, cs, lv, fs0 || cs].join('|'))); }
  const [n, cn, cs0, sn, ss0, lv, fs0] = p; const cs = cs0 || 'PHB', ss = ss0 || 'PHB'; return FEAT_MAP.get(lc([n, cn, cs, sn, ss, lv, fs0 || ss].join('|')));
};
const refId = (r) => String(typeof r === 'object' ? r.classFeature || r.subclassFeature || '' : r).split('|');

// spell lists: official from 5e.tools' lookup, homebrew from the spell itself
let LOOK = {}; try { LOOK = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'generated', 'gendata-spell-source-lookup.json'), 'utf8')); } catch (e) {}
function spellClasses(sp) {
  const out = new Set();
  const l = (LOOK[lc(sp.source)] || {})[lc(sp.name)];
  if (l && l.class) for (const by of Object.values(l.class)) for (const c of Object.keys(by)) out.add(classKey(c));
  for (const c of (sp.classes && sp.classes.fromClassList) || []) out.add(classKey(c.name));
  return [...out];
}

// ── spells ──
const TIME = (t) => (t || []).map((x) => { const n = x.number || 1; return x.unit === 'action' ? `${n} a` : x.unit === 'bonus' ? `${n} bns` : x.unit === 'reaction' ? `${n} rea` : x.unit === 'minute' ? `${n} min` : x.unit === 'hour' ? `${n} h` : `${n} ${x.unit}`; }).join(' or ') || '1 a';
const RANGE = (r) => {
  if (!r) return '';
  if (r.type === 'special') return 'Special';
  const d = r.distance || {}; const ft = (a) => d.type === 'miles' ? `${a} mile${a > 1 ? 's' : ''}` : `${a} ft`;
  if (r.type === 'point') return d.type === 'self' ? 'Self' : d.type === 'touch' ? 'Touch' : d.type === 'sight' ? 'Sight' : d.type === 'unlimited' ? 'Unlimited' : ft(d.amount);
  const shape = { radius: 'rad', sphere: 'sphere', cone: 'cone', line: 'line', cube: 'cube', hemisphere: 'hemisphere', emanation: 'emanation', cylinder: 'cylinder' }[r.type] || r.type;
  return `S:${d.amount}-ft ${shape}`;
};
const DUR = (ds) => (ds || []).map((x) => x.type === 'instant' ? 'Instantaneous' : x.type === 'permanent' ? 'Till dispelled' : x.type === 'special' ? 'Special' : x.duration ? `${x.concentration ? 'Conc, ' : ''}${x.duration.amount} ${{ minute: 'min', hour: 'h', round: x.duration.amount > 1 ? 'rounds' : 'round', day: 'days', turn: 'turn', week: 'weeks', year: 'years' }[x.duration.type] || x.duration.type}` : '').filter(Boolean).join(' or ');
function makeSpell(sp, book) {
  const w = { auto: ['Level, school, casting time, range, components, duration and text'], todo: [] };
  const c = sp.components || {};
  const full = paras(sp.entries).join('\n\n') + (sp.entriesHigherLevel ? '\n\n' + paras(sp.entriesHigherLevel).join('\n\n') : '');
  const first = (paras(sp.entries)[0] || '').split(/(?<=\.)\s/)[0];
  const classes = spellClasses(sp);
  if (classes.length) w.auto.push('Class spell lists: ' + classes.join(', ')); else w.todo.push('Which classes can learn it (5e.tools lists none)');
  w.info = ['No Spell Effect (the Activate button), like other spells without one'];
  const o = { key: keyFor('spell', sp.name, book), name: sp.name, level: sp.level, school: SCHOOL[sp.school] || sp.school || '', time: TIME(sp.time), range: RANGE(sp.range), duration: DUR(sp.duration) || 'Instantaneous',
    components: [c.v && 'V', c.s && 'S', c.m && 'M'].filter(Boolean).join(','), conc: (sp.duration || []).some((d) => d.concentration), classes,
    desc: first.length > 160 ? first.slice(0, 157) + '…' : first, tags: [/^S:/.test(RANGE(sp.range)) || (sp.areaTags || []).length ? 'aoe' : null, (sp.spellAttack || []).length ? 'atk' : null].filter(Boolean), descFull: full, source: book };
  if (c.m) o.material = typeof c.m === 'string' ? c.m : c.m.text || '';
  if (sp.meta && sp.meta.ritual) o.ritual = true;
  spellKeyOf.set(lc(sp.name), spellKeyOf.get(lc(sp.name)) || o.key);
  return [o, w];
}

// ── additional spells (feats, species, subclasses, invocations) ──
const spellRef = (s) => { const n = String(s).split('#')[0].split('|')[0]; return { name: n, key: spellKeyOf.get(lc(n)) || null, cantrip: /#c$/.test(String(s)) }; };
function engineSpells(add, w) {
  // the sheet's feat engine: { spells: [{k, how, lv}], picks: [{kind:'spell', filter, how, count}|{kind:'ability', pool}] }
  const d = { spells: [], picks: [] };
  if (!Array.isArray(add) || !add.length) return null;
  if (add.length > 1) { w.todo.push('A choice between sets of spells (' + add.map((a) => a.name || '?').join(' / ') + ')'); }
  const a = add[0];
  if (a.ability && a.ability.choose) d.picks.push({ id: 'ab', kind: 'ability', label: 'Spellcasting ability', pool: a.ability.choose.slice(), count: 1 });
  else if (typeof a.ability === 'string') d.sab = a.ability;
  const ab = d.picks.length ? 'pick:ab' : undefined;
  const take = (list, how, lv) => {
    for (const s of [].concat(list || [])) {
      if (typeof s === 'string') { const r = spellRef(s); if (r.key) d.spells.push({ k: r.key, how: r.cantrip ? 'cantrip' : how, lv, ab }); else w.todo.push('Spell not in the sheet: ' + r.name); }
      else if (s && s.choose) {
        const f = {}; String(s.choose).split('|').forEach((p) => { const [k, v] = p.split('='); if (k === 'level') f.level = v.split(';').map(Number); if (k === 'class') f.classes = v.split(';').map(classKey); if (k === 'school') f.schools = v.split(';').map((x) => SCHOOL[x] || x); });
        d.picks.push({ id: 'sp' + d.picks.length, kind: 'spell', label: 'Spell', filter: f, how: f.level && f.level.every((x) => x === 0) ? 'cantrip' : how, count: s.count || 1, ab });
      } else if (s && typeof s === 'object') w.todo.push('Spell grant of a kind the sheet does not read');
    }
  };
  for (const [lvl, v] of Object.entries(a.known || {})) { const lv = lvl === '_' ? 1 : +lvl; if (Array.isArray(v)) take(v, 'prep', lv); else if (v && v._) take(v._, 'prep', lv); }
  for (const [lvl, v] of Object.entries(a.prepared || {})) { const lv = lvl === '_' ? 1 : +lvl; take(Array.isArray(v) ? v : v && v._, 'prep', lv); }
  for (const [lvl, v] of Object.entries(a.innate || {})) {
    const lv = lvl === '_' ? 1 : +lvl;
    if (Array.isArray(v)) take(v, 'atwill', lv);
    else if (v) { if (v.will) take(v.will, 'atwill', lv); if (v.ritual) take(v.ritual, 'ritual', lv); for (const [, per] of Object.entries(v.daily || {})) take(per, 'lr', lv); for (const [, per] of Object.entries(v.rest || {})) take(per, 'sr', lv); if (v._) take(v._, 'atwill', lv); }
  }
  if (a.expanded) w.todo.push('Expanded spell list (extra spells the class may choose)');
  if (!d.spells.length) delete d.spells; if (!d.picks.length) delete d.picks;
  return d;
}

// ── feats ──
const FEATCAT = { O: 'origin', G: 'general', FS: 'style', 'FS:P': 'style', 'FS:R': 'style', EB: 'epic', D: 'dragonmark' };
const prereqText = (p) => (p || []).map((o) => Object.entries(o).map(([k, v]) => k === 'level' ? `Level ${typeof v === 'object' ? v.level : v}${v && v.class ? ' ' + v.class.name : ''}` : k === 'ability' ? v.map((a) => Object.entries(a).map(([s, n]) => `${ABIL[s] || s} ${n}+`).join(' or ')).join('; ') : k === 'spellcasting' || k === 'spellcasting2020' || k === 'spellcastingFeature' ? 'Spellcasting or Pact Magic feature' : k === 'race' || k === 'species' ? v.map((r) => cap(r.name) + (r.subrace ? ` (${r.subrace})` : '')).join(' or ') : k === 'feat' ? v.map((f) => cap(String(f).split('|')[0])).join(' or ') : k === 'other' || k === 'otherSummary' ? (typeof v === 'string' ? v : v.entry || '') : k === 'proficiency' ? v.map((x) => Object.entries(x).map(([a, b]) => `${cap(b)} ${a}`).join(', ')).join(' or ') : k === 'background' ? v.map((b) => b.name).join(' or ') : k === 'campaign' ? v.join(' or ') + ' campaign' : '').filter(Boolean).join(', ')).filter(Boolean).join('; or ');
const minLevel = (p) => { for (const o of p || []) if (o.level) return typeof o.level === 'object' ? o.level.level : o.level; return null; };
function makeFeat(f, book) {
  const w = { auto: ['Text, type and prerequisite'], todo: [] };
  const desc = pipe(f.entries);
  const o = { name: f.name, type: FEATCAT[f.category] || 'general', prereq: prereqText(f.prerequisite), minLevel: minLevel(f.prerequisite), desc, asi: {}, skills: [], source: book };
  let pool = null;
  for (const a of f.ability || []) {
    if (a.choose && a.choose.from) { pool = a.choose.from.slice(); if ((a.choose.amount || 1) !== 1 || (a.choose.count || 1) !== 1) w.todo.push('Ability score increase of more than +1 in one score'); }
    else for (const [k, v] of Object.entries(a)) if (ABIL[k]) o.asi[k] = v;
  }
  if (pool) w.auto.push('Ability score increase (choose from ' + pool.map((x) => x.toUpperCase()).join(', ') + ')'); else if (Object.keys(o.asi).length) w.auto.push('Ability score increase');
  for (const sp of f.skillProficiencies || []) { const fixed = Object.keys(sp).filter((k) => sp[k] === true); if (fixed.length) { o.skills.push(...fixed); w.auto.push('Skill proficiency: ' + fixed.map(cap).join(', ')); } if (sp.choose || sp.any) w.todo.push('A choice of skill proficiency'); }
  const u = usage(desc); if (u) { o.usages = u.usages; o.recovery = u.recovery; w.auto.push(`Uses: ${u.usages === 'prof_bonus' ? 'Proficiency Bonus' : u.usages} per ${u.recovery}`); }
  const eng = engineSpells(f.additionalSpells, w);
  if (eng && (eng.spells || eng.picks)) w.auto.push('Spells it grants');
  for (const [k, lab] of [['toolProficiencies', 'Tool proficiency'], ['languageProficiencies', 'Languages'], ['expertise', 'Expertise'], ['resist', 'Damage resistance'], ['immune', 'Damage immunity'], ['conditionImmune', 'Condition immunity'], ['senses', 'Senses'], ['armorProficiencies', 'Armour training'], ['weaponProficiencies', 'Weapon proficiency'], ['savingThrowProficiencies', 'Saving throw proficiency'], ['optionalfeatureProgression', 'Class options it grants'], ['bonusSenses', 'Senses']])
    if (f[k]) w.todo.push(lab);
  return [{ key: lc(f.name), name: f.name, feat: o, engine: eng ? Object.assign({ name: f.name }, eng) : null, asiPool: pool }, w];
}

// ── backgrounds ──
const itemName = (x) => cap(String(x).split('|')[0]);
function makeBackground(b, book) {
  const w = { auto: ['Text'], todo: [] };
  const o = { name: b.name, source: book, page: String(b.page || ''), abilityScores: [], scoresTxt: '', skills: [], skillKeys: [], tools: [], languages: [], langExtra: 0, originFeat: '', equipmentA: [], goldA: 0, goldB: 0, trait: '' };
  const ab = (b.ability || [])[0];
  if (ab && ab.choose) { const from = (ab.choose.weighted && ab.choose.weighted.from) || ab.choose.from || []; o.abilityScores = from.map((x) => ABIL[x]); o.scoresTxt = `+2 and +1 -or- +1 to each from ${o.abilityScores.join(', ').replace(/, ([^,]*)$/, ', and $1')}`; w.auto.push('Ability scores'); }
  else w.todo.push(ab ? 'Ability scores (fixed, not a choice)' : 'Older (2014) background: no ability scores');
  const sk = (b.skillProficiencies || [])[0] || {};
  o.skillKeys = Object.keys(sk).filter((k) => sk[k] === true).map((k) => k.replace(/ /g, '_')); o.skills = Object.keys(sk).filter((k) => sk[k] === true).map(cap);
  if (o.skills.length) w.auto.push('Skills'); if (sk.choose || sk.any) w.todo.push('A choice of skills');
  const tl = (b.toolProficiencies || [])[0] || {}; o.tools = Object.keys(tl).filter((k) => tl[k] === true).map(cap); if (o.tools.length) w.auto.push('Tools'); if (tl.choose || tl.any || Object.keys(tl).some((k) => k.startsWith('any'))) w.todo.push('A choice of tools');
  const lg = (b.languageProficiencies || [])[0] || {}; o.languages = Object.keys(lg).filter((k) => lg[k] === true && !k.startsWith('any')).map(cap); o.langExtra = lg.anyStandard || lg.any || 0;
  const ft = (b.feats || [])[0]; if (ft) { o.originFeat = cap(Object.keys(ft)[0].split('|')[0]); w.auto.push('Origin feat: ' + o.originFeat); } else w.todo.push('No origin feat');
  const eq = (b.startingEquipment || [])[0] || {};
  for (const x of eq.A || eq._ || []) { if (typeof x === 'string') o.equipmentA.push({ name: itemName(x), qty: 1 }); else if (x.item) o.equipmentA.push({ name: x.displayName || itemName(x.item), qty: x.quantity || 1 }); else if (x.special) o.equipmentA.push({ name: cap(x.special), qty: x.quantity || 1 }); else if (x.value) o.goldA = x.value / 100; else if (x.containsValue) o.goldA = x.containsValue / 100; }
  for (const x of eq.B || []) if (x && x.value) o.goldB = x.value / 100;
  if (o.equipmentA.length || o.goldB) w.auto.push('Starting equipment');
  const p = paras(b.entries).filter((x) => !/^(Ability Scores|Feat|Skill Proficiencies|Tool Proficiency|Equipment|Languages|Tool Proficiencies)\b/i.test(x.replace(/^•\s*/, '')));
  o.trait = p.join(' | ');
  return [o, w];
}

// ── species ──
const SIZE = { T: 'Tiny', S: 'Small', M: 'Medium', L: 'Large', H: 'Huge', G: 'Gargantuan', V: 'Varies' };
function makeRace(r, book, name, extraEntries) {
  const w = { auto: ['Text and traits'], todo: [] };
  const sp = typeof r.speed === 'number' ? { walk: r.speed } : r.speed || { walk: 30 };
  const sizes = (r.size || ['M']).map((s) => SIZE[s] || s);
  const feats = [];
  for (const e of [...(r.entries || []), ...(extraEntries || [])]) {
    if (!e || typeof e !== 'object' || !e.name) continue;
    if (/^(age|alignment|size|speed|languages?|creature type|ability score increases?)$/i.test(String(e.name).trim())) continue;   // already in the species' own fields
    const desc = pipe(e.entries || e.entry || []); const lv = (/(?:character )?level (\d+)/i.exec(desc) || [])[1];
    const u = usage(desc);
    feats.push({ name: tags(e.name), level: lv && /when you reach|starting at|once you reach/i.test(desc) ? +lv : 1, desc, usages: u ? u.usages : null, recovery: u ? u.recovery : null });
  }
  if (feats.some((f) => f.usages)) w.auto.push('Uses per rest (from the text)');
  const o = { name, speed: typeof sp.walk === 'number' ? sp.walk : 30, size: sizes.join(' or '), sizeOptions: sizes, darkvision: r.darkvision || 0, features: feats, subraces: {}, type: cap((r.creatureTypes || ['humanoid'])[0]),
    sizeText: sizes.join(' or '), speedText: `${sp.walk || 30} feet`, intro: '', hidden: false, source: book, langFixed: [], langNote: '' };
  if (typeof sp.fly === 'number') o.flySpeed = sp.fly; else if (sp.fly === true) o.flyEqualsSpeed = true;
  if (typeof sp.swim === 'number') o.swimSpeed = sp.swim; else if (sp.swim === true) o.swimEqualsSpeed = true;
  if (typeof sp.climb === 'number') o.climbSpeed = sp.climb; else if (sp.climb === true) o.climbEqualsSpeed = true;
  const res = (r.resist || []).filter((x) => typeof x === 'string'); if (res.length) { o.dmgres = res.map(cap); w.auto.push('Damage resistance'); } if ((r.resist || []).some((x) => typeof x !== 'string')) w.todo.push('A choice of damage resistance');
  const ci = (r.conditionImmune || []).filter((x) => typeof x === 'string'); if (ci.length) o.condImm = ci.map(cap);
  if (r.darkvision) w.auto.push('Darkvision');
  const lg = (r.languageProficiencies || [])[0] || {}; const fixed = Object.keys(lg).filter((k) => lg[k] === true && !k.startsWith('any')).map(cap); const n = lg.anyStandard || lg.any || 0;
  o.languages = [...fixed, n ? `${n} of your choice` : ''].filter(Boolean).join(' + ') || 'Common + 2 of your choice'; o.langFixed = fixed;
  if (r.ability && r.ability.length) w.todo.push('Older (2014) ability score increase');
  if (r.additionalSpells) w.todo.push('Species spells (e.g. a cantrip it knows)');
  for (const [k, lab] of [['skillProficiencies', 'Skill proficiency'], ['toolProficiencies', 'Tool proficiency'], ['weaponProficiencies', 'Weapon proficiency'], ['armorProficiencies', 'Armour training'], ['feats', 'A feat it grants'], ['senses', 'Other senses'], ['immune', 'Damage immunity']]) if (r[k]) w.todo.push(lab);
  if (feats.length) w.todo.push('Trait effects beyond the above are text only');
  return [o, w];
}

// ── classes and subclasses ──
const CASTER = { full: 'full', '1/2': 'half', '1/3': 'third', pact: 'pact', artificer: 'half' };
function featureList(refs, kind, skipFirstNamed) {
  const out = [];
  for (const r of refs || []) {
    const p = refId(r); const f = featLookup(kind, p);
    if (!f) continue;
    // a subclass's first feature often just holds the others (refSubclassFeature): each becomes its own feature
    const refs2 = (f.entries || []).filter((x) => x && typeof x === 'object' && x.type === 'refSubclassFeature');
    if (refs2.length && kind === 'subclass') {
      const own = (f.entries || []).filter((x) => !(x && typeof x === 'object' && x.type === 'refSubclassFeature'));
      const intro = pipe(own);
      if (intro && !(skipFirstNamed && lc(f.name) === lc(skipFirstNamed))) out.push(feature(f.name, f.level, intro));
      else if (intro) out._intro = intro;
      for (const x of refs2) { const g = featLookup('subclass', String(x.subclassFeature).split('|')); if (g) out.push(feature(g.name, g.level, pipe(g.entries))); }
      continue;
    }
    out.push(feature(f.name, f.level, pipe(f.entries)));
  }
  return out;
}
const feature = (name, level, desc) => { const u = usage(desc); return { name: tags(name), level: +level || 1, desc, usages: u ? u.usages : null, recovery: u ? u.recovery : null }; };
function makeClass(c, book) {
  const w = { auto: ['Hit die, saving throws, features by level'], todo: ['New class: hit points, level-up choices, resources and the class table need checking in play'] };
  const sk = (c.startingProficiencies && c.startingProficiencies.skills || [])[0];
  const skillsText = sk && sk.choose ? `Choose ${sk.choose.count || 2}: ${(sk.choose.from || []).map(cap).join(', ')}` : '';
  const o = { name: c.name, die: (c.hd && c.hd.faces) || 8, saves: c.proficiency || [], primaryAbility: (c.primaryAbility || []).flatMap((x) => Object.keys(x)), skillsText,
    spellcasting: c.casterProgression ? { type: CASTER[c.casterProgression] || 'full', ability: c.spellcastingAbility } : { type: 'none' }, features: featureList(c.classFeatures, 'class'), subclasses: [], source: book };
  if (c.cantripProgression) o.spellcasting.cantrips = c.cantripProgression.slice(0, 20);
  if (c.preparedSpellsProgression) o.spellcasting.prepared = c.preparedSpellsProgression.slice(0, 20);
  if (c.casterProgression) { w.auto.push('Spellcasting (' + o.spellcasting.type + ')'); if (o.spellcasting.type === 'third') w.todo.push('One-third caster spell slots'); }
  if (o.features.some((f) => f.usages)) w.auto.push('Uses per rest (from the text)');
  return [o, w];
}
function makeSubclass(s, book, cls) {
  const w = { auto: ['Features by level'], todo: [] };
  const features = featureList(s.subclassFeatures, 'subclass', s.name);
  const o = { name: s.name, source: book, tagline: '', intro: features._intro || '', features: features.slice(), bonusSpells: [], cls, sub: lc(s.shortName || s.name) };
  if (o.features.some((f) => f.usages)) w.auto.push('Uses per rest (from the text)');
  const add = (s.additionalSpells || [])[0];
  if (add) {
    const lists = [add.prepared, add.known].filter(Boolean);
    for (const L of lists) for (const lv of Object.keys(L).sort((a, b) => (+a || 0) - (+b || 0))) for (const x of [].concat(Array.isArray(L[lv]) ? L[lv] : (L[lv] && L[lv]._) || [])) {
      if (typeof x !== 'string') { w.todo.push('A choice of bonus spells'); continue; }
      const r = spellRef(x); if (r.key) o.bonusSpells.push(r.key); else w.todo.push('Bonus spell not in the sheet: ' + r.name);
    }
    if (o.bonusSpells.length) w.auto.push('Bonus spells (always prepared)');
    if (add.expanded) w.todo.push('Expanded spell list (extra spells it may choose)');
    if (add.innate) w.todo.push('Spells cast without a slot');
  }
  if (features.some((f) => /\bchoose (one|two|an?)\b/i.test(f.desc))) w.todo.push('Choices in its features (e.g. pick an option)');
  if (s.optionalfeatureProgression) w.todo.push('Class options it grants (e.g. maneuvers, runes)');
  w.todo.push('Feature effects are text only, apart from the above');
  return [o, w];
}

// ── class options ──
function makeOption(f, book) {
  const t = f.featureType || [];
  const w = { auto: ['Text'], todo: [] };
  const desc = pipe(f.entries);
  if (t.includes('EI')) {
    const pre = f.prerequisite || []; let minLv = 1, pact = null, cantripReq = null;
    for (const o of pre) { if (o.level) minLv = typeof o.level === 'object' ? o.level.level : o.level; if (o.pact) pact = lc(o.pact); for (const s of o.spell || []) if (/eldritch blast/i.test(String(s))) cantripReq = 'eldritch_blast'; }
    const o = { name: f.name, clean: f.name, minLevel: minLv, pact, cantripReq, desc, effects: [], source: book };
    const inn = f.additionalSpells && f.additionalSpells[0] && f.additionalSpells[0].innate && f.additionalSpells[0].innate._;
    if (inn) { const will = inn.will && inn.will[0], daily = inn.daily && Object.values(inn.daily)[0] && Object.values(inn.daily)[0][0]; const s = spellRef(will || daily || ''); if (s.key) { o.grantedSpell = s.key; o.grantType = will ? 'atWill' : 'onceLR'; w.auto.push('Spell it grants'); } else w.todo.push('Spell it grants is not in the sheet'); }
    if (minLv > 1 || pact || cantripReq) w.auto.push('Prerequisites');
    for (const q of pre) for (const k of Object.keys(q)) if (!['level', 'pact', 'spell'].includes(k)) w.todo.push(k === 'patron' ? `Prerequisite not checked by the picker: ${q.patron} patron` : k === 'optionalfeature' ? `Prerequisite not checked by the picker: ${[].concat(q.optionalfeature).map((x) => String(x).split('|')[0]).join(' or ')}` : `Prerequisite not checked by the picker (${k})`);
    if (!o.grantedSpell) w.todo.push('Effect is text only');
    return ['invocation', o, w];
  }
  if (t.some((x) => /^MV/.test(x))) { w.todo.push('Effect is text only'); return ['maneuver', { name: f.name, desc, source: book }, w]; }
  // Arcane Archer shots and Rune Knight runes (artificer infusions are 2014 only: the sheet's 2024 artificer has Replicate Magic Item instead)
  if (t.some((x) => /^AS(:|$)/.test(x))) { w.todo.push('Effect is text only'); return ['arcaneshot', { name: f.name, desc, source: book }, w]; }
  if (t.includes('RN')) { let lv = 3; for (const o of f.prerequisite || []) if (o.level) lv = typeof o.level === 'object' ? o.level.level : o.level; w.auto.push('Level it becomes available (' + lv + ')'); w.todo.push('Effect is text only'); return ['rune', { name: f.name, lv, desc: `${f.name}. ${desc}`, source: book }, w]; }
  if (t.includes('MM')) { const cost = (f.consumes && f.consumes.amount) || (/(\d+) Sorcery Points?/i.exec(desc) || [])[1] || 1; w.auto.push('Sorcery Point cost'); w.todo.push('Effect is text only'); return ['metamagic', { name: f.name, cost: +cost, desc, source: book }, w]; }
  return null;
}

// ── build ──
const out = {};   // kind -> book -> [entry]
const seen = new Set();   // one per kind + book + name (5e.tools lists some subclasses under both the 2014 and 2024 class)
const push = (kind, book, e) => { const id = kind + '|' + book + '|' + lc(e.key && kind === 'subclass' ? e.key : e.name); if (seen.has(id)) return; seen.add(id); ((out[kind] = out[kind] || {})[book] = out[kind][book] || []).push(e); };
const rpKey = (e, kind) => { const rp = (e.reprintedAs || [])[0]; const s = rp ? String(typeof rp === 'string' ? rp : rp.uid || '') : ''; return s ? kind + '|' + lc(s.split('|')[0]) + '|' + lc(s.split('|')[1] || '') : undefined; };
const meta = (kind, e, book, w) => ({ _k: kind + '|' + lc(e.name) + '|' + lc(srcField(e)) + (kind === 'subclass' ? '|' + lc(e.className) : ''), _b: book, _rp: rpKey(e, kind), _w: w, _x: extra.has(book) ? 1 : undefined, _o: OFFICIAL.has(book) && !names[book] ? 1 : undefined });
let skipped = 0;
// reprinted under a name the sheet already has (e.g. Feeblemind → Befuddlement): the sheet's newer one wins
const reprintHave = (e, kind) => (e.reprintedAs || []).some((rp) => {
  const p = String(typeof rp === 'string' ? rp : rp.uid || '').split('|'); const n = lc(p[0]);
  if (kind === 'subclass') { const ck = classKey(p[1] || e.className); return have.subclass.has(ck + '/' + n) || have.subclass.has(ck + '/' + core(n)); }
  const h = have[kind]; return h && (h.has(n) || h.has(bare(n)));
});
const tryAdd = (fn) => { try { fn(); } catch (err) { fails.push(String(err && err.stack || err).split('\n').slice(0, 2).join(' ').slice(0, 200)); } };
// spells first, so feats and subclasses can point at new spells too
for (const sp of data.spell) tryAdd(() => { if (have.spell.has(lc(sp.name)) || reprintHave(sp, 'spell')) { skipped++; return; } const b = bookOf(sp); const [o, w] = makeSpell(sp, b); push('spell', b, Object.assign(o, meta('spell', sp, b, w))); });
for (const f of data.feat) tryAdd(() => { if (lc(f.name) === 'ability score improvement') return; if (have.feat.has(lc(f.name)) || reprintHave(f, 'feat')) { skipped++; return; } const b = bookOf(f); const [o, w] = makeFeat(f, b); push('feat', b, Object.assign(o, meta('feat', f, b, w))); });
let old2014 = 0;
for (const x of data.background) tryAdd(() => { if (!x.ability || !x.ability.length) { old2014++; return; }   // 2014-style background (ability scores on the species, no origin feat): not for this 2024 sheet
  if (have.background.has(lc(x.name)) || reprintHave(x, 'background')) { skipped++; return; } const b = bookOf(x); const [o, w] = makeBackground(x, b); o.key = keyFor('background', x.name, b); push('background', b, Object.assign(o, meta('background', x, b, w))); });
const raceBy = new Map(data.race.map((r) => [lc(r.name) + '|' + lc(r.source), r]));
for (const r of data.race) tryAdd(() => { if (have.race.has(bare(r.name)) || have.race.has(lc(r.name)) || reprintHave(r, 'race')) { skipped++; return; } const b = bookOf(r); const [o, w] = makeRace(r, b, r.name); o.key = keyFor('race', r.name, b); push('race', b, Object.assign(o, meta('race', r, b, w))); });
for (const s of data.subrace) tryAdd(() => {
  if (!s.name) return; const nm = `${s.raceName} (${s.name})`;
  if (have.race.has(lc(nm)) || have.race.has(lc(`${s.name} ${s.raceName}`))) { skipped++; return; }
  const base = raceBy.get(lc(s.raceName) + '|' + lc(s.raceSource)); if (!base) return;
  const b = bookOf(s); const merged = Object.assign({}, base, Object.fromEntries(Object.entries(s).filter(([k]) => !['name', 'source', 'entries', 'page'].includes(k))));
  const [o, w] = makeRace(merged, b, nm, s.entries); o.key = keyFor('race', nm, b); const m = meta('race', Object.assign({}, s, { name: nm }), b, w); push('race', b, Object.assign(o, m));
});
const sheetClasses = new Set((live.classes || []).map(([k]) => k));
const newClasses = new Set();
for (const c of data.class) tryAdd(() => { if (have.class.has(lc(c.name)) || reprintHave(c, 'class')) { skipped++; return; } const b = bookOf(c); const [o, w] = makeClass(c, b); o.key = classKey(c.name); newClasses.add(o.key); push('class', b, Object.assign(o, meta('class', c, b, w))); });
data.subclass.sort((a, b) => (b.classSource === 'XPHB') - (a.classSource === 'XPHB'));
for (const s of data.subclass) tryAdd(() => {
  const ck = classKey(s.className); if (!sheetClasses.has(ck) && !newClasses.has(ck)) return;
  const sk = ck + '/' + lc(s.shortName || s.name);
  if (reprintHave(s, 'subclass') || have.subclass.has(sk) || have.subclass.has(ck + '/' + lc(s.name)) || have.subclass.has(ck + '/' + core(s.name)) || have.subclass.has(ck + '/' + core(s.shortName || ''))) { skipped++; return; }
  const b = bookOf(s); const [o, w] = makeSubclass(s, b, ck); o.key = ck + '/' + lc(s.name); push('subclass', b, Object.assign(o, meta('subclass', s, b, w)));
});
for (const f of data.optionalfeature) tryAdd(() => {
  const r = makeOption(f, bookOf(f)); if (!r) return; const [kind, o, w] = r;
  if (have[kind].has(lc(f.name)) || reprintHave(f, kind)) { skipped++; return; }
  const b = bookOf(f); push(kind, b, Object.assign(o, meta(kind, f, b, w)));
});

// ── newer printings of what the sheet already has ──
// The sheet's own entries always win, so a later reprint (a Xanathar's spell redone in Arcana Unleashed, say) is never
// put in over them. Instead it is listed for the DM ("Newer printing available") when 5e.tools links the sheet's printing
// to it with reprintedAs. Needs the book of each sheet entry (baseline/live.json rep.src, from dump.py).
const SHEET_SRC = live.src || {};
const _bkCache = new Map();
const bookOfUid = (src, name) => { const k = lc(src); if (!_bkCache.has(k)) { let b = null; try { const real = Object.keys(J).find((x) => lc(x) === k); b = bookOf({ source: real || src, name }); } catch (e) {} _bkCache.set(k, b); } return _bkCache.get(k); };
const RPL = new Map();   // "kind|name|book" -> ["kind|name|book" it was reprinted as]
const UPKINDS = { spell: data.spell, feat: data.feat, background: data.background, race: data.race, class: data.class, subclass: data.subclass };
const rpId = (kind, e, book) => kind + '|' + (kind === 'subclass' ? classKey(e.className) + '/' + lc(e.shortName || e.name) : lc(e.name)) + '|' + book;
for (const [kind, L] of Object.entries(UPKINDS)) for (const e of L || []) {
  if (!e.reprintedAs || !e.reprintedAs.length) continue; let b; try { b = bookOf(e); } catch (err) { continue; }
  const to = e.reprintedAs.map((rp) => { const p = String(typeof rp === 'string' ? rp : rp.uid || '').split('|'); if (!p[0] || !p[1]) return null; const tb = bookOfUid(kind === 'subclass' ? p[p.length - 1] : p[1], p[0]); return tb ? kind + '|' + (kind === 'subclass' ? classKey(p[1] || e.className) + '/' : '') + lc(p[0]) + '|' + tb : null; }).filter(Boolean);
  if (to.length) RPL.set(rpId(kind, e, b), to);
}
const reaches = (from, target) => { const seen = new Set([from]); let q = [from]; for (let d = 0; d < 6 && q.length; d++) { const nq = []; for (const x of q) for (const y of RPL.get(x) || []) { if (y === target) return true; if (!seen.has(y)) { seen.add(y); nq.push(y); } } q = nq; } return false; };
let newer = 0, newerSame = 0;
const SHEET_TXT = live.txt || {};
const _words = (t) => new Set(String(t || '').toLowerCase().replace(/<[^>]+>/g, ' ').match(/[a-z]{4,}/g) || []);
const _sim = (a, b) => { const A = _words(a), B = _words(b); if (!A.size || !B.size) return 0; let n = 0; for (const w of A) if (B.has(w)) n++; return n / (A.size + B.size - n); };
const _byPrint = new Map(); for (const [kind, L] of Object.entries(UPKINDS)) for (const e of L || []) { try { _byPrint.set(kind + '|' + (kind === 'subclass' ? classKey(e.className) + '/' + lc(e.shortName || e.name) : lc(e.name)) + '|' + bookOf(e), e); } catch (err) {} }
const _txtOf = (e) => { if (!e) return ''; if (e.subclassFeatures) { try { const F = featureList(e.subclassFeatures, 'subclass', e.name); return [F._intro || '', ...F.map((f) => (f.name || '') + ' ' + (f.desc || ''))].join(' '); } catch (err) { return ''; } } return RH.render(e.entries || [], 0); };
for (const [kind, L] of Object.entries(UPKINDS)) for (const e of L || []) tryAdd(() => {
  if (e.reprintedAs && e.reprintedAs.length) return;   // only the last printing
  const ck = kind === 'subclass' ? classKey(e.className) : '';
  const tries = kind === 'subclass' ? [ck + '/' + lc(e.shortName || e.name), ck + '/' + lc(e.name), ck + '/' + core(e.name)] : kind === 'race' ? [lc(e.name), bare(e.name)] : [lc(e.name)];
  const nm = tries.find((t) => (SHEET_SRC[kind] || {})[t]); const S = nm && SHEET_SRC[kind][nm]; if (!S) return;
  const b = bookOf(e); if (!b || b === S) return;
  const from = kind === 'subclass' ? [ck + '/' + lc(e.shortName || e.name)] : [lc(e.name)];
  if (!from.some((f) => reaches(kind + '|' + f + '|' + S, rpId(kind, e, b)))) return;
  // only when the sheet's own text is still the older printing's (its book label can be out of date while its text is not)
  const mine = (SHEET_TXT[kind] || {})[nm]; const oldE = _byPrint.get(kind + '|' + from[0] + '|' + S);
  if (!mine || !oldE) return; const sOld = _sim(mine, _txtOf(oldE)), sNew = _sim(mine, _txtOf(e)); if (!(sOld > sNew + 0.05)) { newerSame++; return; }
  const html = kind === 'subclass' ? (() => { try { const F = featureList(e.subclassFeatures, 'subclass', e.name); return (F._intro ? `<p>${F._intro}</p>` : '') + F.map((f) => `<p><b>${f.name}${f.level ? ' (level ' + f.level + ')' : ''}.</b> ${f.desc || ''}</p>`).join(''); } catch (err) { return ''; } })() : RH.render(e.entries || [], 0) + (e.entriesHigherLevel ? RH.render(e.entriesHigherLevel, 0) : '');
  const o = { key: 'update|' + kind + '|' + nm, name: e.name, of: kind, from: S, html };
  push('update', b, Object.assign(o, meta('update', Object.assign({}, e, { name: kind + ': ' + e.name }), b, { auto: [], todo: [`Newer printing: the sheet's ${kind} is from ${S}; ${b} reprinted it`] })));
  newer++;
});

// ── rules: the glossary (variant and optional rules, actions, senses, skills, statuses, conditions, diseases) ──
// Single words that are everyday English stay out of the automatic links (every "attack" or "help" would become one);
// they are still in the glossary. Multi-word terms, diseases and these distinctive words are linked.
const LINK_WORDS = new Set(['blindsight', 'darkvision', 'tremorsense', 'truesight', 'bloodied', 'concentration', 'exhaustion', 'dash', 'disengage', 'dodge', 'acrobatics', 'athletics', 'arcana', 'deception', 'insight', 'intimidation', 'investigation', 'perception', 'persuasion', 'stealth', 'survival']);
const RULEKIND = { variantrule: 'Rule', action: 'Action', sense: 'Sense', skill: 'Skill', status: 'Status', condition: 'Condition', disease: 'Disease' };
const RTYPE = { C: 'Rules glossary', O: 'Optional rule', V: 'Variant rule', VO: 'Variant optional rule', VV: 'Variant rule' };
const DATE = (b) => { for (const v of Object.values(J)) if (Array.isArray(v) && v[0] === b) return v[1] || ''; return ''; };
const bestRule = new Map();   // name -> the entry to use: newest official printing, else the first of the others
for (const kind of Object.keys(RULEKIND)) for (const e of data[kind] || []) tryAdd(() => {
  const n = lc(e.name); if (!n || have.rule.has(n)) { if (n) skipped++; return; }
  const b = bookOf(e), off = OFFICIAL.has(b) && !names[b];
  const cur = bestRule.get(n + '|' + (off ? '' : b));
  if (!cur || (off && DATE(b) > DATE(cur.b))) bestRule.set(n + '|' + (off ? '' : b), { e, kind, b });
});
for (const { e, kind, b } of bestRule.values()) tryAdd(() => {
  const html = RH.render(e.entries || (e.entry != null ? [e.entry] : []), 0).replace(/<a class="r5"[^>]*>([\s\S]*?)<\/a>/g, '$1');
  if (!html.trim()) return;
  const single = !/[\s-]/.test(e.name.trim());
  const link = !single || LINK_WORDS.has(lc(e.name)) || kind === 'disease';
  const what = kind === 'variantrule' ? (RTYPE[e.ruleType] || 'Rule') : RULEKIND[kind];
  const w = { auto: ['Glossary entry (' + what.toLowerCase() + ')', link ? 'Linked wherever it appears in rules text' : 'In the glossary only: a common word, so not linked in text'], todo: [] };
  push('rule', b, Object.assign({ key: lc(e.name), name: e.name, source: b, html, kind: what, nolink: link ? undefined : 1 }, meta('rule', e, b, w)));
});

// ── write: whole books per file, homebrew from the full collection never mixed with the rest ──
fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) if (/^s_.*\.json$|^index\.json$/.test(f)) fs.unlinkSync(path.join(OUT, f));
const LIMIT = 650000;
const index = { v: 1, kinds: {}, extra: [], official: [], playtest: [], total: 0, skipped, nfails: fails.length, fails: fails.slice(0, 20) };
const order = ['spell', 'feat', 'background', 'race', 'class', 'subclass', 'invocation', 'maneuver', 'metamagic', 'arcaneshot', 'rune', 'rule', 'update'];
for (const kind of order) {
  const B = out[kind]; if (!B) continue;
  const ki = index.kinds[kind] = { n: 0, counts: {}, files: [] };
  // files never mix groups: official books, playtest, the homebrew books the sheet already used, the rest of homebrew
  const grp = (a) => extra.has(a) ? 'x' : names[a] ? (names[a][3] === 'playtest' ? 'u' : 'b') : 'o';
  const books = Object.keys(B).sort((x, y) => grp(x).localeCompare(grp(y)) || x.localeCompare(y));
  let cur = null, size = 0, part = 0;
  const flush = () => { if (!cur || !cur.rows.length) return; const name = `s_${kind}_${++part}.json`; const txt = JSON.stringify(cur.rows); fs.writeFileSync(path.join(OUT, name), txt);
    ki.files.push({ f: name, h: crypto.createHash('sha1').update(txt).digest('hex').slice(0, 12), n: cur.rows.length, b: cur.books, g: cur.g, x: cur.g === 'x' ? 1 : undefined }); };
  for (const a of books) {
    const rows = B[a].sort((x, y) => String(x.name).localeCompare(String(y.name))); const g = grp(a);
    ki.counts[a] = rows.length; ki.n += rows.length; index.total += rows.length;
    for (const r of rows) { const z = JSON.stringify(r).length + 1; if (!cur || cur.g !== g || (size + z > LIMIT && cur.rows.length)) { flush(); cur = { rows: [], books: [], g }; size = 0; } cur.rows.push(r); size += z; if (!cur.books.includes(a)) cur.books.push(a); }
  }
  flush();
}
const used = new Set(Object.values(index.kinds).flatMap((k) => Object.keys(k.counts)));
// book names live in the bestiary and library indexes; this one is read by every sheet, so it stays small
index.playtest = [...used].filter((a) => names[a] && names[a][3] === 'playtest').sort();
index.extra = [...extra].filter((a) => used.has(a)).sort();
index.official = [...used].filter((a) => OFFICIAL.has(a) && !names[a]).sort();
fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index));
console.log(JSON.stringify({ total: index.total, skipped, old2014, newer, newerSame, kinds: Object.fromEntries(Object.entries(index.kinds).map(([k, v]) => [k, v.n])), official: Object.fromEntries(Object.entries(index.kinds).map(([k, v]) => [k, Object.entries(v.counts).filter(([a]) => index.official.includes(a)).reduce((s, [, n]) => s + n, 0)])), files: Object.values(index.kinds).reduce((s, v) => s + v.files.length, 0), fails: fails.length, firstFails: fails.slice(0, 4) }));
