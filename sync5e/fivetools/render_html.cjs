// 5e.tools entries -> plain, safe HTML (everything escaped; only our own tags). Shared by raw_pack.cjs (the DM's
// 5e.tools page) and sheet_pack.cjs (rules glossary entries). ctx: { FEAT_MAP (getter), featLookup, norm }.
module.exports = function makeRender(ctx) {
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
      const f = ctx.FEAT_MAP && (e.type === 'refOptionalfeature' ? ctx.FEAT_MAP.get(ctx.norm(String(id).split('|').slice(0, 2).join('|'))) || ctx.FEAT_MAP.get(ctx.norm(String(id).split('|')[0])) : ctx.featLookup(e.type === 'refClassFeature' ? 'class' : 'subclass', String(id).split('|')));
      return f ? `<div class="r5ref">${head(f.name)}${render(f.entries || [], depth + 1)}</div>` : `<p><i>See ${tags(String(id).split('|')[0])}.</i></p>`;
    }
    case 'homebrew': return kids(e.entries || []);
  }
  if (e.entries || e.entry || e.items) return `${head(e.name)}${kids(e.entries || e.entry || e.items)}`;
  return '';
}

  return { esc, tags, render, ORD, ABIL };
};
