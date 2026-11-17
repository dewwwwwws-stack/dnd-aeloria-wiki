// ═══════════════════════════════════════════════════════════════════
// 5e.tools → bestiary notes: reading its data and turning a creature into the Fantasy Statblocks creature
// the bestiary notes hold. No Obsidian in here (tests run it in Node).
//
// The conversion is the one the existing notes were made with (convert.py, Oct 2026: every tag resolved,
// nothing dropped, spells linked to their notes), so new notes read like the ones already in the vault.
// ═══════════════════════════════════════════════════════════════════
const FiveTools = (() => {
  const V = FiveToolsVendor;
  const SIZES = { F: 'Fine', D: 'Diminutive', T: 'Tiny', S: 'Small', M: 'Medium', L: 'Large', H: 'Huge', G: 'Gargantuan', C: 'Colossal', V: 'Varies' };
  const ABILITY = { str: 'strength', dex: 'dexterity', con: 'constitution', int: 'intelligence', wis: 'wisdom', cha: 'charisma' };
  const ABILITY_ORDER = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  const norm = (s) => String(s == null ? '' : s).toLowerCase().replace(/[^a-z0-9]/g, '');
  const keyOf = (name, source) => `${String(name).toLowerCase()}|${String(source).toLowerCase()}`;
  /** Python's str.title(): every run of letters gets a capital. */
  const title = (s) => String(s).replace(/[A-Za-z]+/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase());

  // ── copies: a creature written as another plus changes ──
  /**
   * Resolves every `_copy` among `monsters` (all the books loaded) with 5e.tools' own code.
   * Returns { ok: [creatures], failed: [{ name, source, why }], needs: Set(sources to load first) }.
   */
  function resolveCopies(monsters, templates) {
    const byKey = new Map();
    for (const m of monsters) if (!byKey.has(keyOf(m.name, m.source))) byKey.set(keyOf(m.name, m.source), m);
    // templates can be written as copies of other templates too
    templates = V.MiscUtil.copyFast(templates || []);
    const NONE = { _MERGE_REQUIRES_PRESERVE: {} };
    for (let pass = 0; pass < 4; pass++) for (const t of templates) {
      if (!t._copy) continue;
      const parent = templates.find((x) => x !== t && keyOf(x.name, x.source) === keyOf(t._copy.name, t._copy.source));
      if (!parent || parent._copy) continue;
      try { V.copyApplier.getCopy(NONE, V.MiscUtil.copyFast(parent), t, null, {}); } catch (e) { /* left as it is: creatures using it are reported */ }
      delete t._copy;
    }
    templates = templates.filter((t) => t.apply);
    const needs = new Set(), failed = new Map(), busy = new Set();
    const resolve = (m) => {
      if (!m._copy) return true;
      const k = keyOf(m.name, m.source);
      if (failed.has(k)) return false;
      if (busy.has(k)) { failed.set(k, 'copies itself'); return false; }
      const parent = byKey.get(keyOf(m._copy.name, m._copy.source));
      if (!parent) { needs.add(m._copy.source); failed.set(k, `copies ${m._copy.name} (${m._copy.source}), which is not loaded`); return false; }
      busy.add(k);
      try {
        if (!resolve(parent)) { failed.set(k, `copies ${parent.name} (${parent.source}), which could not be worked out`); return false; }
        V.copyApplier.getCopy(V.MONSTER_IMPL, V.MiscUtil.copyFast(parent), m, templates || [], {});
        if (m._copy) delete m._copy;
        return true;
      } catch (e) { failed.set(k, String(e && e.message ? e.message : e)); return false; } finally { busy.delete(k); }
    };
    const ok = [];
    for (const m of monsters) if (resolve(m)) ok.push(m);
    return { ok, failed: monsters.filter((m) => failed.has(keyOf(m.name, m.source))).map((m) => ({ name: m.name, source: m.source, why: failed.get(keyOf(m.name, m.source)) })), needs };
  }

  // ── inline tags, e.g. {@damage 2d8 + 5} or {@condition Charmed|XPHB} ──
  const TAG = /\{@(\w+)((?:\s[^{}]*)?)\}/g;
  const ORDINAL_WORD = { 1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth' };
  const SPELL_ALIASES = { feeblemind: 'befuddlement', brandingsmite: 'shiningsmite' };
  const LINK_RE = /\[\[[^|\]]*\|([^\]]*)\]\]/g;
  const unlink = (s) => String(s).replace(LINK_RE, '$1');

  function attack(codes, roll) {
    const reach = [], kinds = new Set();
    for (let code of codes.split(',')) {
      code = code.trim(); if (!code) continue;
      reach.push({ m: 'Melee', r: 'Ranged', g: 'Magical', a: 'Area' }[code[0]] || code[0].toUpperCase());
      kinds.add({ w: 'Weapon ', s: 'Spell ', p: 'Power ' }[code[1]] || '');
    }
    const kind = kinds.size === 1 ? [...kinds][0] : '';
    return `${[...new Set(reach)].join(' or ')} ${roll ? '' : kind}Attack${roll ? ' Roll' : ''}:`;
  }

  /** A converter for one run: `spellNote(name)` gives the spell's note (path without .md) or null. */
  function converter(opts) {
    const spellNote = (opts && opts.spellNote) || (() => null);
    const sourceName = (opts && opts.sourceName) || ((s) => s);
    const spellLink = (name, shown) => {
      const k = norm(name);
      const note = spellNote(SPELL_ALIASES[k] || k, name);
      return note ? `[[${note}|${shown}]]` : shown;
    };
    const oneTag = (_all, tag, rest) => {
      const body = (rest || '').trim();
      const p = body ? body.split('|') : [''];
      const at = (i) => (p.length > i && p[i].trim() ? p[i].trim() : '');
      switch (tag) {
        case 'spell': return spellLink(p[0].trim(), at(2) || p[0].trim());
        case 'atk': return attack(body, false);
        case 'atkr': return attack(body, true);
        case 'hit': return /^[+\-−]/.test(p[0]) || !/^\d/.test(p[0]) ? p[0] : '+' + p[0];
        case 'h': return 'Hit: ';
        case 'hom': return 'Hit or Miss: ';
        case 'damage': case 'dice': case 'scaledice': case 'scaledamage': case 'autodice': {
          const shown = tag.startsWith('scale') ? (at(2) || p[0]) : (at(1) || p[0]);
          return shown.replace('summonSpellLevel', "the spell's level").replace('summonClassLevel', 'your class level');
        }
        case 'dc': return at(1) || `DC ${p[0]}`;
        case 'd20': return at(1) || (/^[+\-]/.test(p[0]) ? p[0] : '+' + p[0]);
        case 'skillCheck': { const n = body.split(' ').pop(); return /^[+\-]/.test(n) ? n : '+' + n; }
        case 'actSave': return `${title(ABILITY[p[0]] || p[0])} Saving Throw:`;
        case 'actSaveFail': return `${ORDINAL_WORD[p[0]] || ''} Failure:`.trim();
        case 'actSaveFailBy': return `Failure by ${p[0]} or More:`;
        case 'actSaveSuccess': return 'Success:';
        case 'actSaveSuccessOrFail': return 'Failure or Success:';
        case 'actTrigger': return 'Trigger:';
        case 'actResponse': return p[0] === 'd' ? 'Response—' : 'Response:';
        case 'recharge': return p[0] && p[0] !== '6' ? `(Recharge ${p[0]}–6)` : '(Recharge 6)';
        case 'hitYourSpellAttack': return body || 'your spell attack modifier';
        case 'dcYourSpellSave': return body || 'your spell save DC';
        case 'chance': return at(1) || `${p[0]} percent`;
        case 'quickref': return at(4) || p[0];
        case 'deity': return at(3) || p[0];
        case 'variantrule': return at(2) || p[0].replace(/\s*\[[^\]]*\]$/, '');
        case 'note': case 'i': case 'b': case 'bold': case 'italic': case 'u': case 's': case 'filter': case 'book': case 'adventure':
        case 'link': case '5etools': case 'color': case 'highlight': case 'sup': case 'sub': case 'kbd': case 'code': case 'homebrew':
          return p[0];
      }
      return at(2) || p[0];
    };
    const tags = (s) => {
      s = String(s);
      for (let i = 0; i < 8; i++) { const next = s.replace(TAG, oneTag); if (next === s) break; s = next; }
      return s.replace(/[ \t\r\n]+/g, ' ').replace(/ +([,.;!?)])/g, '$1').trim();
    };

    // ── entries → text ──
    const label = (name) => { name = unlink(tags(name)); return !name || '.:!?—'.includes(name[name.length - 1]) ? name : name + '.'; };
    const cellText = (c) => {
      if (c && typeof c === 'object') {
        if (c.type === 'cell') { const r = c.roll || {}; return 'exact' in r ? String(r.exact) : 'min' in r ? `${r.min}–${r.max}` : text(c.entry || ''); }
        return text(c);
      }
      return tags(c);
    };
    const tableText = (t) => {
      const cols = (t.colLabels || []).map(tags);
      const rows = (t.rows || []).map((r) => { const cells = (r && !Array.isArray(r) ? (r.row || []) : r).map(cellText); return cells.length > 1 ? `${cells[0]}: ${cells.slice(1).join('; ')}` : cells[0] || ''; });
      let head = tags(t.caption || '');
      if (cols.length) head = (head ? head + ' ' : '') + '(' + cols.join(' / ') + ')';
      return (head ? head + ' ' : '') + rows.filter(Boolean).join(' | ');
    };
    const text = (e) => {
      if (e == null) return '';
      if (typeof e !== 'object') return tags(e);
      if (Array.isArray(e)) return e.map(text).filter(Boolean).join(' ');
      const kind = e.type;
      if (kind === 'list') return (e.items || []).map(text).filter(Boolean).map((t) => '• ' + t).join(' ');
      if (kind === 'item' || kind === 'itemSub' || kind === 'itemSpell') return `${label(e.name || '')} ${text(e.entries != null ? e.entries : e.entry != null ? e.entry : '')}`.trim();
      if (kind === 'table') return tableText(e);
      if (kind === 'image' || kind === 'gallery') return '';
      const body = text(e.entries != null ? e.entries : e.entry != null ? e.entry : e.items != null ? e.items : '');
      return e.name ? `${label(e.name)} ${body}`.trim() : body;
    };
    const isNamedList = (e) => e && typeof e === 'object' && e.type === 'list' && (e.items || []).length
      && e.items.every((i) => i && typeof i === 'object' && ['item', 'itemSub', 'itemSpell'].includes(i.type) && i.name);
    /** A trait's text with its named parts as a list under it: "- **Name.** text". */
    const withList = (desc, lines) => {
      const list = lines.filter(([, d]) => d).map(([n, d]) => (n ? `- **${n}** ${d}` : `- ${d}`)).join('\n');
      return list ? (desc ? `${desc}\n\n${list}` : list) : desc;
    };
    /** A { name, entries } block as a trait. */
    const trait = (block, name) => {
      const desc = [], nested = [];
      for (const e of block.entries || []) {
        if (isNamedList(e)) for (const i of e.items) nested.push([label(i.name), text(i.entries != null ? i.entries : i.entry != null ? i.entry : '')]);
        else if (e && typeof e === 'object' && ['entries', 'inset', 'variantInner', 'variant'].includes(e.type) && e.name) nested.push([label(e.name), text(e.entries || '')]);
        else if (e && typeof e === 'object' && e.type === 'table') nested.push([label(e.caption || ''), tableText(Object.assign({}, e, { caption: '' }))]);
        else { const t = text(e); if (!t) continue; if (nested.length) nested.push(['', t]); else desc.push(t); }
      }
      return { name: unlink(tags(name == null ? block.name || '' : name)), desc: withList(desc.join(' '), nested) };
    };

    // ── spellcasting ──
    const ordinal = (n) => { n = Number(n); return `${n}${n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th'}`; };
    const spellNames = (arr) => (arr || []).map((s) => { if (s && typeof s === 'object') { if (s.hidden) return ''; s = s.entry || ''; } return tags(s); }).filter(Boolean).join(', ');
    const FREQUENCY = [['daily', 'Day'], ['rest', 'Rest'], ['restLong', 'Long Rest'], ['weekly', 'Week'], ['monthly', 'Month'], ['yearly', 'Year']];
    const spellTrait = (sc) => {
      const hidden = new Set(sc.hidden || []);
      const lines = [];
      const count = (k) => -Number(String(k).replace(/\D/g, '') || 0);
      const sorted = (o) => Object.keys(o).sort((a, b) => count(a) - count(b));
      if (sc.constant && !hidden.has('constant')) lines.push(['Constant:', spellNames(sc.constant)]);
      if (sc.will && !hidden.has('will')) lines.push(['At Will:', spellNames(sc.will)]);
      for (const [key, unit] of FREQUENCY) if (sc[key] && !hidden.has(key)) for (const k of sorted(sc[key])) lines.push([`${k.replace(/e+$/, '')}/${unit}${k.endsWith('e') ? ' Each' : ''}:`, spellNames(sc[key][k])]);
      if (sc.recharge && !hidden.has('recharge')) for (const k of sorted(sc.recharge)) lines.push([k !== '6' ? `Recharge ${k}–6:` : 'Recharge 6:', spellNames(sc.recharge[k])]);
      if (sc.charges && !hidden.has('charges')) for (const k of sorted(sc.charges)) lines.push([`${k} Charge${k === '1' ? '' : 's'}:`, spellNames(sc.charges[k])]);
      if (sc.legendary && !hidden.has('legendary')) for (const k of sorted(sc.legendary)) lines.push([`${k} Legendary Action${k === '1' ? '' : 's'}:`, spellNames(sc.legendary[k])]);
      if (sc.ritual && !hidden.has('ritual')) lines.push(['Rituals:', spellNames(sc.ritual)]);
      if (sc.spells && !hidden.has('spells')) {
        for (const lvl of Object.keys(sc.spells).sort((a, b) => Number(a) - Number(b))) {
          const o = sc.spells[lvl] || {};
          let lab;
          if (lvl === '0') lab = 'Cantrips (at will):';
          else if (o.lower) lab = `${ordinal(o.lower)}–${ordinal(lvl)} level (${o.slots} ${ordinal(lvl)}-level slot${o.slots === 1 ? '' : 's'}):`;
          else if (o.slots) lab = `${ordinal(lvl)} level (${o.slots} slot${o.slots === 1 ? '' : 's'}):`;
          else lab = `${ordinal(lvl)} level:`;
          lines.push([lab, spellNames(o.spells)]);
        }
      }
      const footer = text(sc.footerEntries);
      let desc = withList(text(sc.headerEntries), lines);
      if (footer) desc = desc ? `${desc}\n\n${footer}` : footer;
      return { name: unlink(tags(sc.name || 'Spellcasting')), desc };
    };

    // ── header fields ──
    const ALIGN = { L: 'lawful', N: 'neutral', NX: 'neutral', NY: 'neutral', C: 'chaotic', G: 'good', E: 'evil', U: 'unaligned', A: 'any alignment' };
    const alignList = (codes) => {
      const s = new Set(codes), has = (...x) => x.every((c) => s.has(c));
      if (codes.length === 1) return ALIGN[codes[0]] || codes[0];
      if (codes.length === 2) return codes.map((c) => ALIGN[c] || c).join(' ');
      if (codes.length === 3 && s.size === 3 && has('NX', 'NY', 'N')) return 'any neutral alignment';
      if (codes.length === 4) {
        for (const [axis, word] of [[['L', 'NX', 'C'], { G: 'good', E: 'evil' }], [['G', 'NY', 'E'], { L: 'lawful', C: 'chaotic' }]]) {
          const rest = [...s].filter((c) => !axis.includes(c));
          if (has(...axis) && rest.length === 1 && word[rest[0]]) return `any ${word[rest[0]]} alignment`;
        }
      }
      if (codes.length === 5) for (const [missing, word] of [['G', 'good'], ['E', 'evil'], ['L', 'lawful'], ['C', 'chaotic']]) {
        const want = ['L', 'NX', 'C', 'G', 'NY', 'E'].filter((c) => c !== missing);
        if (s.size === 5 && has(...want)) return `any non-${word} alignment`;
      }
      return [...new Set(codes.map((c) => ALIGN[c] || c))].join(' ');
    };
    const alignment = (m) => {
      const a = m.alignment; if (!a || !a.length) return '';
      let out;
      if (a.every((x) => typeof x === 'string')) out = alignList(a);
      else out = a.map((x) => (typeof x === 'string' ? ALIGN[x] || x : 'special' in x ? tags(x.special) : 'alignment' in x ? alignList(x.alignment) + (x.chance ? ` (${x.chance}%)` : '') + (x.note ? ` ${tags(x.note)}` : '') : '')).filter(Boolean).join(' or ');
      return m.alignmentPrefix ? `${tags(m.alignmentPrefix)} ${out}`.trim() : out;
    };
    const creatureType = (m) => {
      const t = m.type;
      if (typeof t === 'string') return [t, ''];
      let base = t.type;
      if (base && typeof base === 'object') base = (base.choose || []).join(' or ');
      const sub = [];
      if (t.swarmSize) sub.push(`swarm of ${SIZES[t.swarmSize] || t.swarmSize} ${base}s`);
      for (const tag of t.tags || []) sub.push(typeof tag === 'string' ? tag : `${tag.prefix || ''} ${tag.tag || ''}`.trim());
      if (t.note) sub.push(tags(t.note).replace(/^[()]+|[()]+$/g, ''));
      return [String(base), sub.filter(Boolean).join(', ')];
    };
    const armorClass = (m) => {
      const items = m.ac || []; if (!items.length) return [null, ''];
      const notes = []; let ac; const first = items[0];
      if (typeof first === 'number') ac = first;
      else if (first && typeof first === 'object' && 'special' in first) ac = tags(first.special);
      else if (first && typeof first === 'object') {
        ac = first.ac; const bits = (first.from || []).map(tags); if (first.condition) bits.push(tags(first.condition)); if (bits.length) notes.push(bits.join(', '));
      } else ac = tags(first);
      for (const other of items.slice(1)) {
        if (typeof other === 'number') notes.push(String(other));
        else if ('special' in other) notes.push(tags(other.special));
        else { const bits = [String(other.ac)]; if (other.from) bits.push('(' + other.from.map(tags).join(', ') + ')'); if (other.condition) bits.push(tags(other.condition)); notes.push(bits.join(' ')); }
      }
      return [ac, notes.join('; ')];
    };
    const speed = (m) => {
      const sp = m.speed;
      if (typeof sp === 'number') return `${sp} ft.`;
      if (!sp || typeof sp !== 'object') return tags(sp || '');
      const one = (mode, v) => {
        const prefix = mode === 'walk' ? '' : mode + ' ';
        if (v === true) return `${prefix}equal to walking speed`;
        if (v && typeof v === 'object') return `${prefix}${v.number || 0} ft.${v.condition ? ' ' + tags(v.condition) : ''}`;
        return `${prefix}${v} ft.`;
      };
      const parts = [];
      for (const mode of ['walk', 'burrow', 'climb', 'fly', 'swim']) if (mode in sp) parts.push(one(mode, sp[mode]));
      for (const [mode, alts] of Object.entries(sp.alternate || {})) for (const v of alts) parts.push(one(mode, v));
      if (sp.choose) parts.push(`${(sp.choose.from || []).join(' or ')} ${sp.choose.amount} ft.${sp.choose.note ? ' ' + tags(sp.choose.note) : ''}`);
      if (!('walk' in sp) && parts.length) parts.unshift('0 ft.');
      return parts.join(', ');
    };
    const defences = (items, key) => {
      if (!items || !items.length) return '';
      const groups = []; let plain = [];
      const group = (x) => [tags(x.preNote || ''), inner(x[key] || []), tags(x.note || '')].filter(Boolean).join(' ');
      const inner = (xs) => xs.map((x) => (typeof x === 'string' ? tags(x) : 'special' in x ? tags(x.special) : group(x))).join(', ');
      for (const it of items) {
        if (typeof it === 'string') plain.push(tags(it));
        else if (it && 'special' in it) plain.push(tags(it.special));
        else if (it) { if (plain.length) { groups.push(plain.join(', ')); plain = []; } groups.push(group(it)); }
      }
      if (plain.length) groups.push(plain.join(', '));
      return groups.filter(Boolean).join('; ');
    };
    const bonusList = (d, names) => {
      const out = [];
      for (const [k, v] of Object.entries(d || {})) {
        if (k === 'other') { for (const o of v || []) if (o && o.oneOf) out.push({ 'plus one of': Object.entries(o.oneOf).map(([s, b]) => `${title(s)} ${b}`).join(', ') }); continue; }
        if (k === 'special') { out.push({ special: tags(v) }); continue; }
        const sv = String(v).trim(), mm = /^([+\-−]?)(\d+)$/.exec(sv);
        out.push({ [(names || {})[k] || k]: mm ? (mm[1] === '-' || mm[1] === '−' ? -Number(mm[2]) : Number(mm[2])) : tags(sv) });
      }
      return out;
    };
    const CR_XP = V.Parser.XP_CHART_ALT;
    const crValue = (cr) => { if (cr == null) return null; const s = String(cr); if (s.includes('/')) { const [a, b] = s.split('/'); return Number(a) / Number(b); } const n = Number(s); return Number.isFinite(n) ? n : null; };
    const proficiency = (cr) => { const v = crValue(cr); return v == null ? 2 : 2 + Math.max(0, Math.floor((Math.ceil(v) - 1) / 4)); };
    const mod = (score) => (typeof score === 'number' ? Math.floor((score - 10) / 2) : 0);
    const signed = (n) => (n >= 0 ? `+${n}` : `${n}`);
    const commas = (n) => Number(n).toLocaleString('en-US');
    const gear = (items) => (items || []).map((g) => {
      if (typeof g === 'string') return title(g.split('|')[0]);
      const name = g.displayName || title(String(g.item || '').split('|')[0]);
      return g.quantity && g.quantity !== 1 ? `${name} (${g.quantity})` : name;
    }).filter(Boolean).join(', ');

    /** One creature (its copies resolved) as the Fantasy Statblocks creature a bestiary note holds. */
    function convert(m) {
      const o = { image: null, name: m.name };
      o.source = [...new Set([m.source].concat((m.otherSources || []).map((x) => x && x.source).filter(Boolean)).map(sourceName))];
      const sizes = (m.size || []).map((s) => SIZES[s] || s);
      o.size = (sizes.join(' or ') + (m.sizeNote ? ' ' + tags(m.sizeNote) : '')).trim();
      [o.type, o.subtype] = creatureType(m);
      o.alignment = alignment(m);
      const extra = [];
      const [ac, acClass] = armorClass(m);
      if (ac != null) o.ac = ac;
      if (acClass) o.ac_class = acClass;
      const hp = m.hp || {};
      if ('average' in hp) { o.hp = hp.average; if (hp.formula) o.hit_dice = tags(hp.formula); }
      else if ('special' in hp) {
        const special = tags(hp.special), lead = /^(\d+)\s*\((.+)\)$/.exec(special);
        if (/^\d+$/.test(special)) o.hp = Number(special);
        else if (lead) { o.hp = Number(lead[1]); o.hit_dice = lead[2]; }
        else extra.push({ name: 'Hit Points', desc: special });
      }
      o.speed = speed(m);
      o.stats = ABILITY_ORDER.map((a) => {
        const v = m[a];
        if (typeof v === 'number') return v;
        const note = v && typeof v === 'object' && 'special' in v ? tags(v.special) : '';
        if (note && !extra.some((t) => t.desc === note)) extra.push({ name: 'Ability Scores', desc: note });
        return 10;
      });
      const saves = bonusList(m.save, ABILITY); if (saves.length) o.saves = saves;
      const skills = bonusList(m.skill); if (skills.length) o.skillsaves = skills;
      o.damage_vulnerabilities = defences(m.vulnerable, 'vulnerable');
      o.damage_resistances = defences(m.resist, 'resist');
      o.damage_immunities = defences(m.immune, 'immune');
      o.condition_immunities = defences(m.conditionImmune, 'conditionImmune');
      const senses = (m.senses || []).map(tags);
      if (m.passive != null) senses.push(`passive Perception ${m.passive}`);
      o.senses = senses.join(', ');
      o.languages = (m.languages || []).map(tags).join(', ') || '—';
      const cr = m.cr, baseCr = cr && typeof cr === 'object' ? cr.cr : cr;
      if (baseCr != null) o.cr = String(baseCr);
      if (cr && typeof cr === 'object') {
        const withXp = (v, xp) => { xp = xp || CR_XP[String(v)]; return xp ? `${v} (${commas(xp)} XP)` : String(v); };
        if (cr.lair) extra.push({ name: 'Challenge in Lair', desc: withXp(cr.lair, cr.xpLair) });
        else if (cr.xpLair) extra.push({ name: 'Challenge in Lair', desc: `${baseCr} (${commas(cr.xpLair)} XP)` });
        if (cr.coven) extra.push({ name: 'Challenge in Coven', desc: withXp(cr.coven) });
        if (cr.xp && cr.xp !== CR_XP[String(baseCr)]) extra.push({ name: 'Experience', desc: `${commas(cr.xp)} XP` });
      }
      if (m.pbNote) extra.push({ name: 'Proficiency Bonus', desc: tags(m.pbNote) });
      // initiative: the stated value where the data has one, otherwise the Dexterity modifier
      const init = m.initiative; let bonus = mod(m.dex), adv = '';
      if (typeof init === 'number') bonus = Math.trunc(init);
      else if (init && typeof init === 'object') {
        if ('initiative' in init) bonus = Math.trunc(init.initiative); else bonus += Math.trunc(init.proficiency || 0) * proficiency(baseCr);
        adv = { adv: ', Advantage', dis: ', Disadvantage' }[init.advantageMode] || '';
      }
      if (init != null) o.modifier = bonus;
      o.initiative_text = `${signed(bonus)} (${10 + bonus}${adv})`;
      if (m.gear) o.gear = gear(m.gear);
      if (m.environment) o.habitat = m.environment.map((e) => title(String(e).replace(/_/g, ' '))).join(', ');
      if (m.treasure) o.treasure = m.treasure.map((t) => title(t)).join(', ');
      const sections = { trait: [], action: [], bonus: [], reaction: [], legendary: [], mythic: [] };
      for (const key of Object.keys(sections)) for (const block of m[key] || []) sections[key].push(trait(block));
      for (const sc of m.spellcasting || []) { const where = sc.displayAs || 'trait'; sections[where in sections ? where : 'trait'].push(spellTrait(sc)); }
      for (const v of m.variant || []) sections.trait.push(trait(v, 'Variant: ' + tags(v.name || '')));
      if (m.reactionHeader) sections.reaction.unshift({ name: '', desc: text(m.reactionHeader) });
      o.traits = extra.concat(sections.trait);
      o.actions = sections.action;
      o.bonus_actions = sections.bonus;
      o.reactions = sections.reaction;
      o.legendary_actions = sections.legendary;
      if (sections.legendary.length) {
        if (m.legendaryHeader) o.legendary_description = text(m.legendaryHeader);
        else {
          const n = m.legendaryActions == null ? 3 : m.legendaryActions, lair = m.legendaryActionsLair;
          o.legendary_description = `Legendary action uses: ${n}${lair ? ` (${lair} in its lair)` : ''}. One can be taken immediately after another creature's turn, and all uses come back at the start of this creature's turn.`;
        }
      }
      o.mythic_actions = sections.mythic;
      if (m.mythicHeader) o.mythic_description = text(m.mythicHeader);
      if (m.legendaryGroup) o.lair_group = m.legendaryGroup.name || '';
      for (const k of ['traits', 'actions', 'bonus_actions', 'reactions', 'legendary_actions', 'mythic_actions']) if (!o[k].length) delete o[k];
      return o;
    }
    return { convert, tags, text };
  }

  // ── where things are in the repos ──
  /** A creature's token in the image repo ("bestiary/tokens/XMM/Aboleth.webp"), or null when it has none. */
  function tokenPath(m) {
    if (m.token && m.token.name && m.token.source) return `bestiary/tokens/${m.token.source}/${V.Parser.nameToTokenName(m.token.name)}.webp`;
    if (m.tokenUrl || m.tokenHref || m.hasToken === false) return m.hasToken ? `bestiary/tokens/${m.source}/${V.Parser.nameToTokenName(m.name)}.webp` : null;
    return m.hasToken ? `bestiary/tokens/${m.source}/${V.Parser.nameToTokenName(m.name)}.webp` : null;
  }
  /** Atlas' default footprint for a creature's token (its size multiplier); undefined: one square. */
  const tokenSize = (m) => ({ L: 2, H: 3, G: 4 }[(m.size || [])[(m.size || []).length - 1]]);
  /** A name safe as a note's file name. */
  const fileName = (name) => String(name).replace(/[\\/:*?"<>|#^[\]]/g, '').replace(/\s+/g, ' ').replace(/\.+$/, '').trim().slice(0, 120);
  /** The name Atlas reads from a token image it stored ("Aberrant_Death_s_Head_1791961139908_m8l.webp" → "Aberrant Death s Head"). */
  const assetName = (file) => String(file).replace(/^.*\//, '').replace(/\.[^.]+$/, '').replace(/_\d{10,}_[a-z0-9]{1,8}$/, '').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();

  /**
   * What to do for the books chosen. `monsters`: resolved creatures of those books; `have`: the vault's bestiary
   * notes as [{ path, name, sources: [codes or names] }]; `tokens`: token images as [{ path }]; `dates`: source →
   * published date; `older`: also make older printings of a creature a newer chosen book reprints.
   * Returns { make: [{ m, note, token }], link: [{ path, token }], skipped: { have, reprinted, npc }, tokensHave }.
   */
  function plan({ monsters, have, tokens, dates, older, sourceName }) {
    const byName = new Map();
    for (const h of have) { const k = norm(h.name); if (!byName.has(k)) byName.set(k, []); byName.get(k).push(h); }
    const tokenBy = new Map();
    for (const t of tokens) { const k = norm(assetName(t.path)); if (k && !tokenBy.has(k)) tokenBy.set(k, t.path); }
    const sameSource = (h, src) => (h.sources || []).some((s) => norm(s) === norm(src) || norm(s) === norm(sourceName ? sourceName(src) : src));
    const chosen = new Set(monsters.map((m) => norm(m.source)));
    const newest = new Map();   // name → the chosen book's creature printed last
    const date = (m) => (dates && dates[m.source]) || '';
    for (const m of monsters) { const k = norm(m.name), cur = newest.get(k); if (!cur || date(m) > date(cur)) newest.set(k, m); }
    const out = { make: [], link: [], skipped: { have: 0, reprinted: 0 }, tokensHave: 0 };
    const taken = new Set(have.map((h) => norm(h.path.replace(/^.*\//, '').replace(/\.md$/, ''))));
    for (const m of monsters) {
      const k = norm(m.name), mine = byName.get(k) || [];
      const exact = mine.find((h) => sameSource(h, m.source));
      const token = tokenBy.get(k) || null;
      if (exact) { out.skipped.have++; if (token) out.tokensHave++; out.link.push({ path: exact.path, token, m }); continue; }
      // a newer printing stands in for this one: in the vault already, or among the books chosen
      const reprints = (m.reprintedAs || []).map((r) => String(typeof r === 'string' ? r : r.uid || '').split('|'));
      const reprinted = reprints.some(([n, s]) => s && ((byName.get(norm(n)) || []).some((h) => sameSource(h, s)) || (chosen.has(norm(s)) && monsters.some((x) => norm(x.name) === norm(n) && norm(x.source) === norm(s)))));
      if (!older && (reprinted || newest.get(k) !== m || mine.length)) { out.skipped.reprinted++; continue; }
      // the plain name for the first of a name; a later one of the same name carries its book
      let note = fileName(m.name);
      if (taken.has(norm(note)) || newest.get(k) !== m) note = fileName(`${m.name} (${m.source})`);
      if (taken.has(norm(note))) { out.skipped.have++; continue; }
      taken.add(norm(note));
      out.make.push({ m, note, token });
    }
    return out;
  }

  return { resolveCopies, converter, tokenPath, tokenSize, fileName, assetName, plan, norm, keyOf };
})();
