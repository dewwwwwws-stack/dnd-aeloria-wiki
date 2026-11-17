// Raw 5e.tools library: every category except creatures (those are the bestiary pack), from the official data, the
// playtest (Unearthed Arcana) collection and the homebrew collection, for the DM's Vault > 5e.tools page.
// Kept apart from the sheet's own lists: nothing here changes a character. Text is rendered to safe, plain HTML.
// Usage: node raw_pack.cjs SITE BREW UA brew_files.json json2abv.json OUT_DIR
//   ALL_BREW=1: every homebrew book (the ones not in brew_files.json are listed in index.extra and stay off until the
//   DM turns them on); without it only the brew_files.json books.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const [SITE, BREW, UA, BF, J2A, OUT] = process.argv.slice(2);

// ── categories: [key, label, group] ──
const CATS = [
  ['spell', 'Spells', 'Magic'], ['psionic', 'Psionics', 'Magic'],
  ['class', 'Classes', 'Character'], ['subclass', 'Subclasses', 'Character'], ['race', 'Species', 'Character'], ['subrace', 'Subspecies', 'Character'],
  ['background', 'Backgrounds', 'Character'], ['feat', 'Feats', 'Character'], ['optionalfeature', 'Class options', 'Character'], ['charoption', 'Other options', 'Character'],
  ['item', 'Magic & special items', 'Items'], ['baseitem', 'Basic gear & weapons', 'Items'], ['magicvariant', 'Item templates', 'Items'], ['itemGroup', 'Item groups', 'Items'],
  ['itemMastery', 'Weapon masteries', 'Items'], ['itemProperty', 'Item properties', 'Items'], ['vehicle', 'Vehicles', 'Items'], ['vehicleUpgrade', 'Vehicle upgrades', 'Items'],
  ['action', 'Actions', 'Rules'], ['condition', 'Conditions', 'Rules'], ['disease', 'Diseases', 'Rules'], ['status', 'Statuses', 'Rules'], ['variantrule', 'Rules & variant rules', 'Rules'],
  ['skill', 'Skills', 'Rules'], ['sense', 'Senses', 'Rules'], ['language', 'Languages', 'Rules'],
  ['deity', 'Deities', 'World'], ['cult', 'Cults', 'World'], ['boon', 'Boons', 'World'], ['reward', 'Rewards & blessings', 'World'], ['facility', 'Bastion facilities', 'World'],
  ['recipe', 'Recipes', 'World'], ['table', 'Tables', 'World'], ['deck', 'Decks', 'World'], ['card', 'Cards', 'World'], ['object', 'Objects', 'World'], ['trap', 'Traps', 'World'], ['hazard', 'Hazards', 'World'],
];
const CAT = new Set(CATS.map((c) => c[0]));
const FEATURES = ['classFeature', 'subclassFeature'];

const { data, srcOf, names, extra, abv, fails, bookOf, srcField, norm } = require('./load_data.cjs')({ SITE, BREW, UA, BF, J2A, all: !!process.env.ALL_BREW, cats: CATS.map((c) => c[0]) });

// ── text → safe HTML ──
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const TAG = /\{@(\w+)((?:\s[^{}]*)?)\}/g;
const LINK = { spell: 'spell', item: 'item', creature: 'monster', condition: 'condition', disease: 'disease', status: 'status', feat: 'feat', background: 'background', race: 'race',
  class: 'class', optfeature: 'optionalfeature', skill: 'skill', sense: 'sense', action: 'action', variantrule: 'variantrule', deity: 'deity', language: 'language', reward: 'reward',
  psionic: 'psionic', object: 'object', trap: 'trap', hazard: 'hazard', cult: 'cult', boon: 'boon', table: 'table', vehicle: 'vehicle', vehupgrade: 'vehicleUpgrade', recipe: 'recipe',
  card: 'card', deck: 'deck', facility: 'facility', itemMastery: 'itemMastery', itemProperty: 'itemProperty', charoption: 'charoption', classFeature: 'classFeature', subclassFeature: 'subclassFeature' };
const ABIL = { str: 'Strength', dex: 'Dexterity', con: 'Constitution', int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma' };
function attack(codes, roll) {
  const reach = [], kinds = new Set();
  for (let code of codes.split(',')) { code = code.trim(); if (!code) continue; reach.push({ m: 'Melee', r: 'Ranged', g: 'Magical', a: 'Area' }[code[0]] || code[0].toUpperCase()); kinds.add({ w: 'Weapon ', s: 'Spell ', p: 'Power ' }[code[1]] || ''); }
  const kind = kinds.size === 1 ? [...kinds][0] : '';
  return `<i>${[...new Set(reach)].join(' or ')} ${roll ? '' : kind}Attack${roll ? ' Roll' : ''}:</i>`;
}
const oneTag = (_m, tag, rest) => {   // text is already escaped; only our own markup is added
  const body = (rest || '').trim(), p = body ? body.split('|') : [''];
  const at = (i) => (p.length > i && p[i].trim() ? p[i].trim() : '');
  switch (tag) {
    case 'b': case 'bold': return `<b>${body}</b>`;
    case 'i': case 'italic': return `<i>${body}</i>`;
    case 'u': case 'underline': case 's': case 'strike': case 'sup': case 'sub': case 'code': case 'kbd': case 'note': return body;
    case 'atk': return attack(body, false); case 'atkr': return attack(body, true);
    case 'h': return '<i>Hit:</i> '; case 'hom': return '<i>Hit or Miss:</i> ';
    case 'hit': return /^[+\-−]/.test(p[0]) || !/^\d/.test(p[0]) ? p[0] : '+' + p[0];
    case 'damage': case 'dice': case 'autodice': return at(1) || p[0];
    case 'scaledice': case 'scaledamage': return at(2) || p[0];
    case 'dc': return at(1) || `DC ${p[0]}`;
    case 'd20': return at(1) || (/^[+\-]/.test(p[0]) ? p[0] : '+' + p[0]);
    case 'chance': return at(1) || `${p[0]} percent`;
    case 'recharge': return p[0] && p[0] !== '6' ? `(Recharge ${p[0]}–6)` : '(Recharge 6)';
    case 'actSave': return `<i>${ABIL[p[0]] || p[0]} Saving Throw:</i>`;
    case 'actSaveFail': return '<i>Failure:</i>'; case 'actSaveSuccess': return '<i>Success:</i>'; case 'actSaveSuccessOrFail': return '<i>Failure or Success:</i>';
    case 'actTrigger': return '<i>Trigger:</i>'; case 'actResponse': return '<i>Response:</i>';
    case 'hitYourSpellAttack': return body || 'your spell attack modifier'; case 'dcYourSpellSave': return body || 'your spell save DC';
    case 'filter': case 'link': case '5etools': case 'book': case 'adventure': case 'homebrew': case 'color': case 'highlight': case 'footnote': case 'quickref': return tag === 'quickref' ? (at(4) || p[0]) : p[0];
  }
  const t = LINK[tag];
  const shown = tag === 'class' ? (at(2) || p[0]) : tag === 'classFeature' ? (at(5) || p[0]) : tag === 'subclassFeature' ? (at(7) || p[0]) : tag === 'deity' ? (at(3) || p[0]) : (at(2) || p[0]);
  if (t) return `<a class="r5" data-t="${t}" data-n="${p[0]}${at(1) ? '|' + at(1) : ''}">${shown}</a>`;
  return shown;
};
const tags = (s) => { s = esc(s); for (let i = 0; i < 8; i++) { const n = s.replace(TAG, oneTag); if (n === s) break; s = n; } return s; };
const ORD = (n) => n === 0 ? 'Cantrip' : n + (n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th');
let FEAT_MAP = null;   // class/subclass feature lookups for references
function render(e, depth) {
  depth = depth || 0;
  if (e == null) return '';
  if (typeof e === 'string' || typeof e === 'number') return `<p>${tags(e)}</p>`;
  if (Array.isArray(e)) return e.map((x) => render(x, depth)).join('');
  const kids = (x) => render(x, depth + 1);
  const head = (n) => n ? `<div class="r5h${Math.min(depth, 2)}">${tags(n)}</div>` : '';
  switch (e.type) {
    case undefined: case 'entries': case 'section': case 'variantInner': case 'variantSub': case 'options':
      return `${head(e.name)}${kids(e.entries || e.items || [])}`;
    case 'inset': case 'insetReadaloud': case 'variant':
      return `<div class="r5box">${head(e.name)}${kids(e.entries || [])}</div>`;
    case 'quote': return `<blockquote>${kids(e.entries || [])}${e.by ? `<p>— ${tags(e.by)}${e.from ? ', <i>' + tags(e.from) + '</i>' : ''}</p>` : ''}</blockquote>`;
    case 'list': return `<ul>${(e.items || []).map((i) => `<li>${typeof i === 'string' ? tags(i) : i && (i.type === 'item' || i.type === 'itemSub' || i.type === 'itemSpell') ? `<b>${tags(i.name || '')}</b> ${render(i.entries || i.entry || '', depth + 1).replace(/^<p>|<\/p>$/g, '')}` : render(i, depth + 1)}</li>`).join('')}</ul>`;
    case 'item': case 'itemSub': case 'itemSpell': return `<p><b>${tags(e.name || '')}</b> ${render(e.entries || e.entry || '', depth + 1).replace(/<\/?p>/g, ' ').trim()}</p>`;
    case 'table': {
      const cell = (c) => c && typeof c === 'object' ? (c.type === 'cell' ? (c.roll ? ('exact' in c.roll ? String(c.roll.exact) : `${c.roll.min}–${c.roll.max}`) : render(c.entry || '', depth + 1).replace(/<\/?p>/g, ' ').trim()) : render(c, depth + 1).replace(/<\/?p>/g, ' ').trim()) : tags(c == null ? '' : c);
      const rows = (e.rows || []).map((r) => (r && !Array.isArray(r) ? r.row || [] : r || []));
      return `${e.caption ? `<div class="r5cap">${tags(e.caption)}</div>` : ''}<table class="r5t">${(e.colLabels || []).length ? `<tr>${e.colLabels.map((c) => `<th>${tags(c)}</th>`).join('')}</tr>` : ''}${rows.map((r) => `<tr>${r.map((c) => `<td>${cell(c)}</td>`).join('')}</tr>`).join('')}</table>`;
    }
    case 'tableGroup': return (e.tables || []).map(kids).join('');
    case 'inline': case 'inlineBlock': return `<p>${(e.entries || []).map((x) => typeof x === 'string' ? tags(x) : render(x, depth + 1).replace(/<\/?p>/g, '')).join('')}</p>`;
    case 'abilityDc': return `<p class="r5c"><b>${tags(e.name)} save DC</b> = 8 + your proficiency bonus + your ${(e.attributes || []).map((a) => ABIL[a] || a).join(' or ')} modifier</p>`;
    case 'abilityAttackMod': return `<p class="r5c"><b>${tags(e.name)} attack modifier</b> = your proficiency bonus + your ${(e.attributes || []).map((a) => ABIL[a] || a).join(' or ')} modifier</p>`;
    case 'abilityGeneric': return `<p class="r5c">${e.name ? `<b>${tags(e.name)}</b> = ` : ''}${tags(e.text || '')}</p>`;
    case 'hr': return '<hr>';
    case 'image': case 'gallery': case 'flowchart': case 'flowBlock': return e.type === 'flowBlock' ? `${head(e.name)}${kids(e.entries || [])}` : '';
    case 'dice': return `<p>${esc((e.toRoll || []).map((d) => `${d.number}d${d.faces}`).join(' + '))}</p>`;
    case 'link': return `<p>${tags(e.text || '')}</p>`;
    case 'bonus': return `<p>+${esc(e.value)}</p>`; case 'bonusSpeed': return `<p>+${esc(e.value)} ft.</p>`;
    case 'statblock': case 'statblockInline': return `<p><i>(see ${tags(e.name || (e.data && e.data.name) || e.tag || '')})</i></p>`;
    case 'spellcasting': return `${head(e.name)}${kids(e.headerEntries || [])}${Object.entries(e.spells || {}).map(([l, v]) => `<p><b>${l === '0' ? 'Cantrips' : ORD(+l) + ' level'}:</b> ${(v.spells || []).map(tags).join(', ')}</p>`).join('')}${['will', 'daily', 'rest'].map((k) => e[k] ? (k === 'will' ? `<p><b>At will:</b> ${e.will.map(tags).join(', ')}</p>` : Object.entries(e[k]).map(([n, L]) => `<p><b>${esc(n.replace('e', ''))}/${k === 'daily' ? 'day' : 'rest'}${n.endsWith('e') ? ' each' : ''}:</b> ${L.map(tags).join(', ')}</p>`).join('')) : '').join('')}${kids(e.footerEntries || [])}`;
    case 'refClassFeature': case 'refSubclassFeature': case 'refOptionalfeature': {
      const id = e.classFeature || e.subclassFeature || e.optionalfeature || '';
      const f = FEAT_MAP && (e.type === 'refOptionalfeature' ? FEAT_MAP.get(norm(String(id).split('|').slice(0, 2).join('|'))) || FEAT_MAP.get(norm(String(id).split('|')[0])) : featLookup(e.type === 'refClassFeature' ? 'class' : 'subclass', String(id).split('|')));
      return f ? `<div class="r5ref">${head(f.name)}${render(f.entries || [], depth + 1)}</div>` : `<p><i>See ${tags(String(id).split('|')[0])}.</i></p>`;
    }
    case 'homebrew': return kids(e.entries || []);
  }
  if (e.entries || e.entry || e.items) return `${head(e.name)}${kids(e.entries || e.entry || e.items)}`;
  return '';
}

// ── per category: the line under the name, filters, and the text ──
const SCHOOL = { A: 'Abjuration', C: 'Conjuration', D: 'Divination', E: 'Enchantment', V: 'Evocation', I: 'Illusion', N: 'Necromancy', T: 'Transmutation', P: 'Psionic' };
const FEAT_CAT = { O: 'Origin', G: 'General', FS: 'Fighting Style', 'FS:P': 'Fighting Style (Paladin)', 'FS:R': 'Fighting Style (Ranger)', EB: 'Epic Boon', D: 'Dragonmark' };
const OPT = { EI: 'Eldritch Invocation', 'MV:B': 'Battle Master Maneuver', MV: 'Maneuver', 'MV:C2-UA': 'Maneuver (UA)', 'AS:V1-UA': 'Arcane Shot (UA)', 'AS:V2-UA': 'Arcane Shot (UA)', AS: 'Arcane Shot',
  'FS:F': 'Fighting Style', 'FS:B': 'Fighting Style (Bard)', 'FS:P': 'Fighting Style (Paladin)', 'FS:R': 'Fighting Style (Ranger)', MM: 'Metamagic', AI: 'Artificer Infusion', PB: 'Pact Boon',
  ED: 'Elemental Discipline', AF: 'Alchemical Formula', TT: "Traveler's Trick", OR: 'Onomancy Resonant', RN: 'Rune Knight Rune', OTH: 'Other', 'IWM:W': 'Infernal War Machine Upgrade', 'IWM:A': 'Infernal War Machine Upgrade', 'IWM:G': 'Infernal War Machine Upgrade', SHP: 'Ship Upgrade', 'SHP:H': 'Ship Upgrade', 'SHP:M': 'Ship Upgrade', 'SHP:W': 'Ship Upgrade', 'SHP:F': 'Ship Upgrade', 'SHP:O': 'Ship Upgrade', PSI: 'Psionic Discipline' };
const RAR = (r) => r && r !== 'none' && r !== 'unknown' ? r.replace(/\b\w/g, (c) => c.toUpperCase()) : '';
const ITYPE = { M: 'Melee weapon', R: 'Ranged weapon', A: 'Ammunition', LA: 'Light armour', MA: 'Medium armour', HA: 'Heavy armour', S: 'Shield', RD: 'Rod', RG: 'Ring', P: 'Potion', SC: 'Scroll', WD: 'Wand', ST: 'Staff', G: 'Adventuring gear', AT: "Artisan's tools", T: 'Tools', GS: 'Gaming set', INS: 'Instrument', SCF: 'Spellcasting focus', MNT: 'Mount', VEH: 'Vehicle', TAH: 'Tack and harness', FD: 'Food and drink', TG: 'Trade good', '$': 'Treasure', '$C': 'Coins', '$G': 'Gemstone', '$A': 'Art object', OTH: 'Other', EXP: 'Explosive', AF: 'Futuristic', SHP: 'Ship', SPC: 'Spacecraft', AIR: 'Airship', GV: 'Generic variant', IDG: 'Illegal drug', TB: 'Trade bar' };
const spellTime = (t) => (t || []).map((x) => `${x.number || ''} ${x.unit === 'bonus' ? 'bonus action' : x.unit || ''}${x.condition ? ', ' + x.condition : ''}`.trim()).join(' or ');
const spellRange = (r) => !r ? '' : r.type === 'special' ? 'Special' : r.distance ? (r.distance.type === 'self' ? 'Self' : r.distance.type === 'touch' ? 'Touch' : r.distance.type === 'sight' ? 'Sight' : r.distance.type === 'unlimited' ? 'Unlimited' : `${r.distance.amount || ''} ${r.distance.type}`) + (r.type !== 'point' ? ` (${r.type})` : '') : r.type;
const spellComp = (c) => !c ? '' : [c.v && 'V', c.s && 'S', c.m && ('M' + (typeof c.m === 'string' ? ` (${c.m})` : c.m && c.m.text ? ` (${c.m.text})` : '')), c.r && 'R'].filter(Boolean).join(', ');
const spellDur = (d) => (d || []).map((x) => x.type === 'instant' ? 'Instantaneous' : x.type === 'permanent' ? 'Until dispelled' : x.type === 'special' ? 'Special' : `${x.concentration ? 'Concentration, up to ' : ''}${x.duration ? `${x.duration.amount} ${x.duration.type}${x.duration.amount > 1 ? 's' : ''}` : ''}`).join(' or ');
const prereq = (p) => (p || []).map((o) => Object.entries(o).map(([k, v]) => k === 'level' ? (typeof v === 'object' ? `${v.class ? v.class.name + ' ' : ''}level ${v.level}` : `level ${v}`) : k === 'ability' ? v.map((a) => Object.entries(a).map(([s, n]) => `${(ABIL[s] || s).slice(0, 3)} ${n}`).join(' or ')).join('; ') : k === 'race' || k === 'species' ? v.map((r) => r.displayEntry || r.name + (r.subrace ? ` (${r.subrace})` : '')).join(' or ') : k === 'spellcasting' || k === 'spellcasting2020' || k === 'spellcastingFeature' ? 'can cast spells' : k === 'pact' ? `Pact of the ${v}` : k === 'patron' ? `${v} patron` : k === 'spell' ? v.map((s) => String(typeof s === 'string' ? s : s.entry || s.choose || '').split('#')[0].split('|')[0].replace(/\{@\w+ ([^|}]+)[^}]*\}/g, '$1')).join(' or ') : k === 'feat' ? v.map((f) => String(f).split('|')[0]).join(' or ') : k === 'feature' ? v.join(' or ') : k === 'other' || k === 'otherSummary' ? (typeof v === 'string' ? v : v.entry || '') : k === 'proficiency' ? v.map((x) => Object.entries(x).map(([a, b]) => `${b} ${a}`).join(', ')).join(' or ') : k === 'campaign' ? v.join(' or ') + ' campaign' : k === 'background' ? v.map((b) => b.name).join(' or ') : k === 'item' ? v.join(' or ') : '').filter(Boolean).join(', ')).filter(Boolean).join('; or ');
const speed = (s) => typeof s === 'number' ? `${s} ft.` : s && typeof s === 'object' ? Object.entries(s).filter(([, v]) => v).map(([k, v]) => `${k === 'walk' ? '' : k + ' '}${v === true ? 'equal to walking' : typeof v === 'object' ? v.number : v} ft.`).join(', ') : '';
const ability = (a) => (a || []).map((o) => Object.entries(o).map(([k, v]) => k === 'choose' ? `choose ${v.count || 1} +${v.amount || 1}` : `${(ABIL[k] || k).slice(0, 3)} ${v >= 0 ? '+' : ''}${v}`).join(', ')).join('; or ');

function describe(c, e) {
  const f = {}; let m = '';
  switch (c) {
    case 'spell': {
      const lvl = e.level === 0 ? 'Cantrip' : `${ORD(e.level)}-level`; const sch = SCHOOL[e.school] || e.school || '';
      m = e.level === 0 ? `${sch} cantrip` : `${lvl} ${sch.toLowerCase()}`; f.lvl = [e.level === 0 ? 'Cantrip' : `Level ${e.level}`]; f.sch = [sch];
      if (e.meta && e.meta.ritual) (f.has = f.has || []).push('Ritual');
      if ((e.duration || []).some((d) => d.concentration)) (f.has = f.has || []).push('Concentration');
      const head = [['Casting Time', spellTime(e.time)], ['Range', spellRange(e.range)], ['Components', spellComp(e.components)], ['Duration', spellDur(e.duration)]];
      return { m, f, pre: head.filter(([, v]) => v).map(([k, v]) => `<p class="r5c"><b>${k}:</b> ${tags(v)}</p>`).join(''), post: e.entriesHigherLevel ? render(e.entriesHigherLevel, 1) : '' };
    }
    case 'feat': { const cat = FEAT_CAT[e.category] || (e.category ? e.category : 'General'); f.cat = [cat]; const p = prereq(e.prerequisite); m = cat + ' feat' + (p ? ' · ' + p : ''); if (e.ability) f.has = ['Ability score increase']; if (p) (f.has = f.has || []).push('Prerequisite'); return { m, f, pre: p ? `<p class="r5c"><b>Prerequisite:</b> ${tags(p)}</p>` : '' }; }
    case 'optionalfeature': { const t = (e.featureType || []).map((x) => OPT[x] || x); f.cat = t; const p = prereq(e.prerequisite); m = t.join(', ') + (p ? ' · ' + p : ''); return { m, f, pre: p ? `<p class="r5c"><b>Prerequisite:</b> ${tags(p)}</p>` : '' }; }
    case 'race': case 'subrace': {
      const sz = (e.size || []).map((s) => ({ T: 'Tiny', S: 'Small', M: 'Medium', L: 'Large', H: 'Huge', G: 'Gargantuan', V: 'Varies' }[s] || s)).join(' or ');
      m = [sz, speed(e.speed), ability(e.ability)].filter(Boolean).join(' · '); if (c === 'subrace') m = `Subspecies of ${e.raceName}` + (m ? ' · ' + m : ''); if (sz) f.sz = sz.split(' or ');
      if (e.darkvision) (f.has = f.has || []).push('Darkvision'); if (e.additionalSpells) (f.has = f.has || []).push('Spells');
      return { m, f, pre: [['Size', sz], ['Speed', speed(e.speed)], ['Ability scores', ability(e.ability)], ['Darkvision', e.darkvision ? e.darkvision + ' ft.' : '']].filter(([, v]) => v).map(([k, v]) => `<p class="r5c"><b>${k}:</b> ${tags(v)}</p>`).join('') };
    }
    case 'background': { const sk = (e.skillProficiencies || []).map((o) => Object.keys(o).filter((k) => o[k] === true).map((k) => k.replace(/\b\w/g, (x) => x.toUpperCase())).join(', ')).filter(Boolean).join('; or '); m = sk ? 'Skills: ' + sk : ''; if (e.feats) (f.has = f.has || []).push('Origin feat'); return { m, f }; }
    case 'class': { m = [e.hd ? `Hit die d${e.hd.faces}` : '', (e.proficiency || []).map((a) => (ABIL[a] || a).slice(0, 3)).join(', ') ? 'Saves: ' + (e.proficiency || []).map((a) => (ABIL[a] || a).slice(0, 3)).join(', ') : '', e.spellcastingAbility ? 'Spellcasting: ' + (ABIL[e.spellcastingAbility] || e.spellcastingAbility) : ''].filter(Boolean).join(' · '); if (e.spellcastingAbility) f.has = ['Spellcasting']; return { m, f }; }
    case 'subclass': { m = `${e.className} subclass`; f.cls = [e.className]; if (e.spellcastingAbility || e.additionalSpells) f.has = ['Spells']; return { m, f }; }
    case 'item': case 'baseitem': case 'magicvariant': {
      const it = e.inherits || e; const ty = String(it.type || '').split('|')[0]; const tn = ITYPE[ty] || (it.wondrous ? 'Wondrous item' : ty ? ty : c === 'magicvariant' ? 'Template' : 'Item');
      const rar = RAR(it.rarity); m = [tn, rar, it.reqAttune ? 'needs attunement' + (typeof it.reqAttune === 'string' ? ' ' + it.reqAttune : '') : ''].filter(Boolean).join(' · ');
      f.typ = [tn]; if (rar) f.rar = [rar]; if (it.reqAttune) (f.has = f.has || []).push('Attunement');
      const facts = [['Cost', e.value ? `${e.value / 100} gp` : ''], ['Weight', e.weight ? `${e.weight} lb.` : ''], ['Damage', e.dmg1 ? `${e.dmg1}${e.dmgType ? ' ' + ({ B: 'bludgeoning', P: 'piercing', S: 'slashing', N: 'necrotic', R: 'radiant', F: 'fire', C: 'cold', L: 'lightning', T: 'thunder', A: 'acid', I: 'poison', Y: 'psychic', O: 'force' }[e.dmgType] || e.dmgType) : ''}${e.dmg2 ? ` (${e.dmg2} two-handed)` : ''}` : ''], ['Armour Class', e.ac ? String(e.ac) : ''], ['Properties', (e.property || []).map((p) => String(typeof p === 'object' ? p.uid || '' : p).split('|')[0]).join(', ')], ['Mastery', (e.mastery || []).map((x) => String(x).split('|')[0]).join(', ')]];
      return { m, f, pre: facts.filter(([, v]) => v).map(([k, v]) => `<p class="r5c"><b>${k}:</b> ${tags(v)}</p>`).join('') };
    }
    case 'deity': { m = [e.pantheon, (e.alignment || []).join(''), (e.domains || []).join(', ')].filter(Boolean).join(' · '); if (e.pantheon) f.cat = [e.pantheon]; return { m, f, pre: [['Domains', (e.domains || []).join(', ')], ['Symbol', e.symbol]].filter(([, v]) => v).map(([k, v]) => `<p class="r5c"><b>${k}:</b> ${tags(v)}</p>`).join('') }; }
    case 'psionic': { m = `${e.type === 'T' ? 'Talent' : 'Discipline'}${e.order ? ' · ' + e.order : ''}`; f.cat = [e.type === 'T' ? 'Talent' : 'Discipline']; return { m, f }; }
    case 'reward': case 'charoption': case 'recipe': case 'facility': case 'language': case 'card': case 'variantrule': case 'trap': case 'hazard': case 'vehicle': {
      const t = e.type || e.ruleType || e.trapHazType || e.vehicleType || e.facilityType || e.set || ''; const tt = typeof t === 'string' ? t : ''; if (tt) { f.cat = [tt]; m = tt; } return { m, f };
    }
  }
  return { m, f };
}

// class and subclass features, found by their 5e.tools ids, shown under the class or subclass by level
FEAT_MAP = new Map();
for (const x of data.classFeature) FEAT_MAP.set(norm([x.name, x.className, x.classSource, x.level, x.source].join('|')), x);
for (const x of data.subclassFeature) FEAT_MAP.set(norm([x.name, x.className, x.classSource, x.subclassShortName, x.subclassSource, x.level, x.source].join('|')), x);
for (const x of data.optionalfeature) FEAT_MAP.set(norm([x.name, x.source].join('|')), x), FEAT_MAP.set(norm(x.name), FEAT_MAP.get(norm(x.name)) || x);
function featLookup(cls, p) {   // 5e.tools ids leave the book out when it is the 2014 Player's Handbook
  if (cls === 'class') { const [n, cn, cs0, lv, fs0] = p; const cs = cs0 || 'PHB'; return FEAT_MAP.get(norm([n, cn, cs, lv, fs0 || cs].join('|'))); }
  const [n, cn, cs0, sn, ss0, lv, fs0] = p; const cs = cs0 || 'PHB', ss = ss0 || 'PHB'; return FEAT_MAP.get(norm([n, cn, cs, sn, ss, lv, fs0 || ss].join('|')));
}
const featId = (ref, defSrc) => { const s = String(typeof ref === 'object' ? ref.classFeature || ref.subclassFeature || '' : ref); const p = s.split('|'); return { id: s, p }; };
function features(list, cls) {
  const out = [];
  for (const ref of list || []) {
    const { id, p } = featId(ref);
    const f = featLookup(cls, p);
    if (!f) { const lvl = cls === 'class' ? p[3] : p[5]; out.push(`<div class="r5h1">Level ${esc(lvl || '?')}: ${tags(p[0])}</div><p><i>(feature text not found)</i></p>`); continue; }
    out.push(`<div class="r5h1">Level ${esc(f.level)}: ${tags(f.name)}</div>${render(f.entries || [], 2)}`);
  }
  return out.join('');
}

// ── build ──
const out = {};   // cat -> book -> [entries]
let total = 0;
for (const [c] of CATS) {
  for (const e of data[c]) {
    try {
      const a = bookOf(e);
      const d = describe(c, e);
      let n = e.name;
      if (c === 'subrace') n = e.name ? `${e.raceName} (${e.name})` : e.raceName;
      let h = (d.pre || '') + render(e.entries || (e.entry != null ? [e.entry] : []), 0) + (d.post || '');
      if (c === 'class') h += `<div class="r5h0">Class features</div>` + features(e.classFeatures, 'class');
      if (c === 'subclass') h += features(e.subclassFeatures, 'subclass');
      if (c === 'table' && e.rows) h += render({ type: 'table', colLabels: e.colLabels, rows: e.rows, caption: '' }, 0);
      if (c === 'itemGroup' && e.items) h += `<p class="r5c"><b>Items:</b> ${e.items.map((x) => tags(`{@item ${x}}`)).join(', ')}</p>`;
      if ((c === 'cult' || c === 'boon') && e.goal) h = ['goal', 'cultists', 'signaturespells'].filter((k) => e[k]).map((k) => `<p class="r5c"><b>${k[0].toUpperCase() + k.slice(1)}:</b> ${render(e[k].entry || e[k], 1).replace(/<\/?p>/g, ' ')}</p>`).join('') + h;
      const rp = (e.reprintedAs || [])[0]; const rpk = rp ? String(typeof rp === 'string' ? rp : rp.uid || '') : '';
      const k = c + '|' + norm(n) + '|' + norm(srcField(e)) + (c === 'subclass' ? '|' + norm(e.className) : '');
      const row = { k, n, a, s: srcField(e), m: d.m || undefined, f: Object.keys(d.f).length ? d.f : undefined, p: e.page || undefined, h, rp: rpk ? c + '|' + norm(rpk.split('|')[0]) + '|' + norm(rpk.split('|')[1] || '') : undefined, x: e.__o === 'extra' ? 1 : undefined };
      ((out[c] = out[c] || {})[a] = out[c][a] || []).push(row); total++;
    } catch (err) { fails.push(`${e.name} (${e.source}, ${c}): ${String(err && err.message || err).slice(0, 120)}`); }
  }
}
fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) if (/^r_.*\.json$|^index\.json$/.test(f)) fs.unlinkSync(path.join(OUT, f));
// whole books packed into files of up to 650 KB per category; homebrew from the full collection never shares a file
// with the rest, so the sheet downloads it only for books that are turned on
const LIMIT = 650000;
const index = { v: 1, cats: {}, names: {}, extra: [], total, nfails: fails.length, fails: fails.slice(0, 200) };
for (const [c, label, group] of CATS) {
  const B = out[c]; if (!B) continue;
  const ci = index.cats[c] = { label, group, n: 0, counts: {}, files: [] };
  const books = Object.keys(B).sort((x, y) => (extra.has(x) - extra.has(y)) || x.localeCompare(y));
  let cur = null, size = 0, part = 0;
  const flush = () => { if (!cur || !cur.rows.length) return; const name = `r_${c}_${++part}.json`; const txt = JSON.stringify(cur.rows); fs.writeFileSync(path.join(OUT, name), txt); ci.files.push({ f: name, h: crypto.createHash('sha1').update(txt).digest('hex').slice(0, 12), n: cur.rows.length, b: cur.books, x: cur.x ? 1 : undefined }); };
  for (const a of books) {
    const L = B[a].sort((x, y) => x.n.localeCompare(y.n)); const isX = extra.has(a);
    ci.counts[a] = L.length; ci.n += L.length;
    for (const r of L) {
      const z = JSON.stringify(r).length + 1;
      if (!cur || cur.x !== isX || (size + z > LIMIT && cur.rows.length)) { flush(); cur = { rows: [], books: [], x: isX }; size = 0; }
      cur.rows.push(r); size += z; if (!cur.books.includes(a)) cur.books.push(a);
    }
  }
  flush();
}
const used = new Set(Object.values(index.cats).flatMap((ci) => Object.keys(ci.counts)));
index.names = Object.fromEntries(Object.entries(names).filter(([a]) => used.has(a)));
index.extra = [...extra].filter((a) => used.has(a)).sort();
fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index));
console.log(JSON.stringify({ total, cats: Object.fromEntries(Object.entries(index.cats).map(([c, v]) => [c, v.n])), files: Object.values(index.cats).reduce((s, v) => s + v.files.length, 0), fails: fails.length, firstFails: fails.slice(0, 5) }));
