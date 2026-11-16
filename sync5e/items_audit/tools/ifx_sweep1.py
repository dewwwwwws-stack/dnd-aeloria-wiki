#!/usr/bin/env python3
"""Read each item's text (Items.csv wording) into mechanical effects for the sheet.

  extract(text, item) -> {'p': passive fields, 'u': fields applied when used/activated,
                          'charges': {...}, 'spells': [...], 'req': attunement requirement,
                          'wNotes': [...], 'found': [...labels...]}

Field names follow SPELL_FX (modules/29_spell_effects.js): ac, speed, fly/climb/swim/burrow ('walk' or feet),
resist/immune/vuln/condImm, advSaves/advChecks (ability keys or 'all'), saveBonus, senses, hpMax, skillAdv,
skillBonus, plus item fields: scores (set a score), scoreInc {ab: [n, max]}, init, spellAtk, spellDC, wBonus,
wDice [n, die, type] (this weapon), tempHP.
"""
import re

AB = {'strength': 'str', 'dexterity': 'dex', 'constitution': 'con', 'intelligence': 'int', 'wisdom': 'wis', 'charisma': 'cha'}
DMG = ['acid', 'bludgeoning', 'cold', 'fire', 'force', 'lightning', 'necrotic', 'piercing', 'poison', 'psychic', 'radiant', 'slashing', 'thunder']
CONDS = ['blinded', 'charmed', 'deafened', 'exhaustion', 'frightened', 'grappled', 'incapacitated', 'invisible', 'paralyzed',
         'petrified', 'poisoned', 'prone', 'restrained', 'stunned', 'unconscious']
SKILLS = ['acrobatics', 'animal handling', 'arcana', 'athletics', 'deception', 'history', 'insight', 'intimidation', 'investigation',
          'medicine', 'nature', 'perception', 'performance', 'persuasion', 'religion', 'sleight of hand', 'stealth', 'survival']
WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
           'twelve': 12, 'twenty': 20, 'fifty': 50}
CLASSES = ['artificer', 'barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk', 'paladin', 'ranger', 'rogue', 'sorcerer',
           'warlock', 'wizard', 'psion', 'blood hunter', 'illrigger', 'gunslinger']

# an activated / temporary effect: the sentence says you take an action, expend charges, drink, for a duration...
USE = re.compile(r"\b(as an? (?:magic |bonus )?action|as a bonus action|as a reaction|you can use an? (?:action|bonus action|reaction)|"
                 r"take a (?:magic|bonus) action|expend \d+ (?:of its )?charges?|for (?:the next )?(?:1|one|\d+) (?:minute|hour|round|day)s?\b|"
                 r"until the (?:end|start) of|when you drink|drink(?:ing)? (?:this|the) potion|for the duration|once per|until you|"
                 r"you can speak (?:its|the|a) command word|after you|the next time|when you hit|on a hit|immediately)", re.I)
PASSIVE = re.compile(r"\bwhile (?:you(?:'re| are)? )?(?:wearing|holding|wielding|attuned|carrying|you wear|you hold|you carry|it is|this)|"
                     r"\bwhile (?:you )?(?:wear|hold|carry)", re.I)
COND_WORDS = re.compile(r"\b(against|if the|if you|when|whenever|in dim light|in darkness|underwater|while (?:in|on|the|it|your|you're (?:not|in|on|raging|flying))|"
                        r"on a (?:critical|roll)|of the type|chosen|your choice|vs\.?)\b", re.I)

def _num(s):
    s = (s or '').lower().strip()
    return int(s) if s.isdigit() else WORDNUM.get(s)

def sentences(text):
    text = re.sub(r'\n+', ' \n ', text or '')
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])|\s\n\s', text)
    return [p.strip() for p in parts if p.strip()]

HOLDER = re.compile(r"\b(?:creature|wearer|bearer|wielder|holder|owner)\b (?:who is |that is )?(?:holding|wearing|wielding|carrying|attuned|that (?:carries|wears|holds|wields)|with (?:the|this) \w+ in its possession)|\b(?:the|its) (?:wearer|bearer|wielder)\b", re.I)
OTHER = re.compile(r"\b(?:it|its|they|their|target|creatures?|ally|allies|beast|mount|steed|familiar|companion|fish|lion|treant|construct|statue|mirror|figure|versions?|cart|vehicle|ship|boat|wagon|chariot|swarm|the \w+ (?:has|is|uses|gains))\b", re.I)
STATBLOCK = re.compile(r"\bAC (?:of )?\d+\b|^(?:Armor Class|Hit Points|Skills|Senses|Speed) |\b(?:STR|DEX|CON) \d+ \(|\bHP \d+\b|stat ?block|statistics (?:of|as)|\d+ hit points(?:,| and)|weighs \d+", re.I)

def mine(s, start):
    """True when the effect at s[start:] belongs to you (the item's owner), not a target, ally or the item itself."""
    pre = s[:start]
    clause = re.split(r'[,;:]', pre)[-1]
    if re.search(r'\byou(?:r)?\b', clause, re.I) or HOLDER.search(clause): return True
    if OTHER.search(clause): return False
    if re.search(r'\byou(?:r)?\b', s, re.I) or HOLDER.search(s): return True
    return not OTHER.search(s)

def _list(s):
    return [w.strip().lower() for w in re.split(r',\s*(?:and|or)?\s*|\s+(?:and|or)\s+', s) if w.strip()]

def extract(text, item=None, spell_names=None):
    p, u, notes, found = {}, {}, [], []
    item = item or {}
    # random-draw items (a card's effect happens once, when drawn): nothing applies while you own them
    if re.match(r'Deck of Many|Teeth of Dahlver-Nar', item.get('name') or ''):
        return {'p': {}, 'u': {}, 'charges': None, 'spells': [], 'req': None, 'notes': [], 'found': []}
    is_consumable = (item.get('type') or '').lower() in ('potion', 'scroll') or re.search(r'\b(potion|elixir|oil of|philter|draught)\b', (item.get('name') or ''), re.I)
    is_weapon = item.get('isWeapon')
    is_armour = item.get('isArmour')
    STRONG = re.compile(r"\b(magic action|bonus action|as an action|use an action|reaction|expend|for (?:1|one|\d+) (?:minute|hour|round)s?|for the duration|command word|drink|until the (?:end|start))", re.I)
    ctx = {'use': False}
    def put(field, val, s, label):
        tgt = u if (is_consumable or ctx['use'] or STRONG.search(s) or (USE.search(s) and not PASSIVE.search(s))) else p
        if field in ('resist', 'immune', 'vuln', 'condImm', 'advSaves', 'advChecks', 'skillAdv'):
            tgt.setdefault(field, [])
            for v in (val if isinstance(val, list) else [val]):
                if v not in tgt[field]: tgt[field].append(v)
        elif field in ('senses', 'scores', 'scoreInc', 'skillBonus'):
            tgt.setdefault(field, {}).update(val)
        else:
            tgt[field] = val
        found.append(('use:' if tgt is u else '') + label)
    prev_use = False
    for s in sentences(text):
        low = s.lower()
        # a table row (random roll, pick-one options): nothing in it applies on its own
        if s.lstrip().startswith('|'): prev_use = False; continue
        cond = COND_WORDS.search(s) or re.search(r'\bin (?:an area of )?(?:dim light|darkness|bright light)', s, re.I)
        ctx['use'] = prev_use and bool(re.match(r'(If you do|When you do|For the duration|While (?:it is|active|flying)|Until|The effect|This (?:effect|property) lasts)', s))
        # a state you switch on (rage, an aura, the item's own state, time of day, class level): applied with Use, not always
        if re.search(r'\b(?:in|within) (?:the|its|this) aura\b|^While (?:the|this|your) [\w\' -]{1,30}? (?:is|are) (?!worn|held|attached|on your person)|^While your Rage|between dusk and dawn|\bat night\b|in sunlight|^If you have \d+ or more levels', s, re.I): ctx['use'] = True
        if re.search(r'you and (?:your |any )?all(?:y|ies)', s, re.I) and re.search(r'\baura\b|while in|extended|within \d+ feet', s, re.I): ctx['use'] = True
        prev_use = bool(STRONG.search(s)) or ctx['use']
        stat = bool(STATBLOCK.search(s))
        # ── AC / saves ──
        m = re.search(r'\+(\d) bonus to (?:your )?(?:Armor Class|AC)\b', s)
        if m and (stat or not mine(s, m.start()) or re.search(r'for every|for each', low)): m = None
        if m and is_armour and not ctx['use'] and re.search(r'while (?:you(?:\'re| are) )?(?:wearing|holding) (?:this|it)|this (?:armor|shield)', low) and not re.search(r'\bif you\b|\bagainst\b', low):
            p['armourBonus'] = int(m.group(1)); found.append('armour +' + m.group(1))
        elif m and (ctx['use'] or not (is_armour and re.search(r'while (?:wearing|holding) this (?:armor|shield)|this (?:armor|shield)', low))) and not re.search(r'\b(?:creatures?|allies|ally|target)\b', s[:m.start()], re.I) and not re.search(r'\bif you\b|\bagainst\b', low):
            put('ac', int(m.group(1)), s, 'AC +%s' % m.group(1))
        m = re.search(r'\+(\d) bonus to (?:AC and |Armor Class and )?(?:all )?saving throws', s)
        if m and not stat and mine(s, m.start()) and not re.search(r'saving throws? (?:against|made to|to )', low):
            put('saveBonus', int(m.group(1)), s, 'saves +%s' % m.group(1))
        m = re.search(r'\+(\d) bonus to ((?:(?:your )?(?:Armor Class|AC|saving throws|spell attack rolls|the saving throw DCs of your spells|spell save DCs?)(?:, | and |, and )?){2,})', s)
        if m and not stat and mine(s, m.start()) and not re.search(r'\bagainst\b|\bif you\b', low):
            n = int(m.group(1)); parts = m.group(2).lower()
            if 'armor class' in parts or re.search(r'\bac\b', parts):
                if not (is_armour and 'this armor' in low): put('ac', n, s, 'AC +%d' % n)
            if 'saving throws' in parts and 'dc' not in parts.split('saving throws')[1][:4]: put('saveBonus', n, s, 'saves +%d' % n)
            if 'spell attack' in parts: put('spellAtk', n, s, 'spell attack +%d' % n)
            if 'dc' in parts: put('spellDC', n, s, 'spell DC +%d' % n)
        m = re.search(r'your base Armor Class is (\d+) \+ your Dexterity modifier|your base Armor Class is (\d+) plus your Dexterity modifier', s)
        if m: put('acBase', int(m.group(1) or m.group(2)), s, 'base AC %s + Dex' % (m.group(1) or m.group(2)))
        m = re.search(r'[Yy]our spell save DC and spell attack bonus (?:each )?increase by (\d)', s)
        if m: put('spellAtk', int(m.group(1)), s, 'spell attack +' + m.group(1)); put('spellDC', int(m.group(1)), s, 'spell DC +' + m.group(1))
        if re.search(r'Advantage on Initiative', s): put('initAdv', True, s, 'Adv. Initiative')
        for m in re.finditer(r'Advantage on (?:Initiative rolls and )?(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) \(([A-Za-z ]+)\) checks\.', s):
            if m.group(2).lower() in SKILLS and not stat and mine(s, m.start()): put('skillAdv', [m.group(2).lower()], s, 'Adv. ' + m.group(2))
        # ── ability scores ──
        for m in re.finditer(r'[Yy]our (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) (?:score )?(?:is|becomes|changes to|equals) (\d+)', s):
            put('scores', {AB[m.group(1).lower()]: int(m.group(2))}, s, '%s %s' % (m.group(1)[:3], m.group(2)))
        for m in re.finditer(r'[Yy]our (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)(?: score)? increases by (\d)(?:,? (?:to a maximum of|up to a maximum of) (\d+))?', s):
            if re.search(r'as does your maximum|permanently|this increase|you read|the book', low): notes.append('permanent increase when used: ' + s[:120]); continue
            put('scoreInc', {AB[m.group(1).lower()]: [int(m.group(2)), int(m.group(3) or 20)]}, s, '%s +%s' % (m.group(1)[:3], m.group(2)))
        # ── speed and movement ──
        m = re.search(r'[Yy]our (?:walking )?Speed (?:increases|is increased) by (\d+) feet', s)
        if m and not cond: put('speed', int(m.group(1)), s, 'Speed +%s' % m.group(1))
        if re.search(r'double your (?:walking )?Speed|your (?:walking )?Speed is doubled', s): put('speedMult', 2, s, 'Speed x2')
        for kind in ('Fly', 'Swim', 'Climb', 'Burrow'):
            m = re.search(r'(?:gain|gaining|have|has) an? %s(?:ing)? Speed (?:of (\d+) feet|equal to your (?:walking )?Speed)' % kind, s, re.I)
            if m and (stat or not mine(s, m.start())): continue
            if m and cond and not STRONG.search(s): notes.append('conditional %s: %s' % (kind, s[:100])); continue
            if m: put(kind.lower(), int(m.group(1)) if m.group(1) else 'walk', s, '%s %s' % (kind, m.group(1) or '= Speed'))
        # ── senses ──
        for m in re.finditer(r'\b(Darkvision|Blindsight|Tremorsense|Truesight)(?: out)?(?: to)?(?: a range of| with a range of)? (\d+) feet', s):
            if re.search(r'additional|increases? by|extra', low) or stat or not mine(s, m.start()): continue
            put('senses', {m.group(1).lower(): int(m.group(2))}, s, '%s %s' % (m.group(1), m.group(2)))
        # ── defences ──
        m = re.search(r'(?:have|gain|has) Resistance to ((?:(?:%s)(?:, | and | or |, and |, or )?)+) damage' % '|'.join(DMG), s, re.I)
        if m and not stat and mine(s, m.start()) and not re.search(r'of your choice|one of the following|chosen|that type|the triggering|the type', low):
            put('resist', [d.capitalize() for d in _list(m.group(1)) if d in DMG], s, 'Resistance ' + m.group(1))
        if re.search(r'Resistance to all damage', s): put('resistAll', True, s, 'Resistance to all damage')
        m = re.search(r'\byou(?: also)? (?:have|gain|are) (?:Immunity|immune) to ((?:(?:%s)(?:, | and | or |, and )?)+) damage' % '|'.join(DMG), s, re.I)
        if m and not re.search(r'of your choice|chosen', low):
            put('immune', [d.capitalize() for d in _list(m.group(1)) if d in DMG], s, 'Immunity ' + m.group(1))
        m = re.search(r'\byou(?: also)? (?:have|gain|are) (?:Immunity to|immune to) (?:the )?((?:(?:%s)(?:, | and | or |, and )?)+) conditions?' % '|'.join(CONDS), s, re.I)
        if m: put('condImm', [c for c in _list(m.group(1)) if c in CONDS], s, 'Immune ' + m.group(1))
        m = re.search(r"(?:you )?can't be ((?:%s)(?:,? (?:or|and) (?:%s))*)\b" % ('|'.join(CONDS), '|'.join(CONDS)), s, re.I)
        if m and not stat and mine(s, m.start()) and not re.search(r'by (?:the|a) |\bspell\b|automatically|is immune to this', low[m.end():m.end() + 40]) and not re.search(r'\bif it\b|\bunless it\b', low):
            put('condImm', [c for c in _list(m.group(1)) if c in CONDS], s, "can't be " + m.group(1))
        m = re.search(r'Vulnerability to ((?:%s)) damage' % '|'.join(DMG), s, re.I)
        if m and not stat and mine(s, m.start()): put('vuln', [m.group(1).capitalize()], s, 'Vulnerability ' + m.group(1))
        # ── advantage ──
        for m in re.finditer(r'Advantage on (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) saving throws', s):
            if not stat and mine(s, m.start()) and not re.search(r'saving throws? (?:against|to |made to)', low[m.start():m.end() + 30]): put('advSaves', [AB[m.group(1).lower()]], s, 'Adv. %s saves' % m.group(1)[:3])
        if re.search(r'Advantage on (?:all )?saving throws(?=[.,;]| while| when)', s): put('advSaves', ['all'], s, 'Adv. saves')
        for m in re.finditer(r'Advantage on (?:any |all )?(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) \(([A-Za-z ]+)\) checks(?![^.]*\b(?:made to|to |against|when|if|that rely|while (?!wearing|holding)))', s):
            sk = m.group(2).lower()
            if sk in SKILLS and not stat and mine(s, m.start()): put('skillAdv', [sk], s, 'Adv. ' + m.group(2))
        for m in re.finditer(r'Advantage on (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) checks', s):
            if not cond and not stat and mine(s, m.start()): put('advChecks', [AB[m.group(1).lower()]], s, 'Adv. %s checks' % m.group(1)[:3])
        m = re.search(r'\+(\d+) bonus to Initiative', s, re.I)
        if m and mine(s, m.start()): put('init', int(m.group(1)), s, 'Initiative +' + m.group(1))
        for m in re.finditer(r'\+(\d) bonus to (?:Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) \(([A-Za-z ]+)\) checks', s):
            sk = m.group(2).lower()
            if sk in SKILLS and not cond and not stat and mine(s, m.start()) and not re.match(r' made to| to ', s[m.end():m.end() + 9]): put('skillBonus', {sk: int(m.group(1))}, s, '%s +%s' % (m.group(2), m.group(1)))
        # ── hit points ──
        m = re.search(r'Hit Point maximum (?:increases|is increased) by (\d+)', s)
        if m and mine(s, m.start()) and not re.search(r'\beats?\b', low): put('hpMax', int(m.group(1)), s, 'HP max +' + m.group(1))
        m = re.search(r'Hit Point maximum (?:increases|is increased) by (?:an amount equal to )?(?:your|twice your) (?:character )?level', s)
        if m: put('hpMaxPerLevel', 2 if 'twice' in low else 1, s, 'HP max +level')
        m = re.search(r'(?:You|you) regain (\d+d\d+(?: ?\+ ?\d+)?) Hit Points', s) or (is_consumable and re.search(r'(?:that drinks|who drinks|drinker)[^.]*? regains (\d+d\d+(?: ?\+ ?\d+)?) Hit Points', s))
        if m and (is_consumable or STRONG.search(s) or 'drink' in low): u['heal'] = m.group(1).replace(' ', ''); found.append('use:heal ' + m.group(1))
        m = re.search(r'gain (\d+d\d+(?: \+ \d+)?|\d+) Temporary Hit Points', s)
        if m and (is_consumable or USE.search(s)): u['tempHP'] = m.group(1).replace(' ', ''); found.append('use:temp HP ' + m.group(1))
        # ── spellcasting ──
        m = re.search(r'\+(\d) bonus to spell attack rolls', s)
        if m: put('spellAtk', int(m.group(1)), s, 'spell attack +' + m.group(1))
        m = re.search(r'\+(\d) bonus to (?:the )?(?:spell )?save DCs? of your spells|\+(\d) bonus to (?:your )?spell save DC|to the saving throw DCs? of your (?:\w+ )?spells', s)
        if m:
            n = m.group(1) or m.group(2) or (re.search(r'\+(\d) bonus', s) or [None, None])[1]
            if n: put('spellDC', int(n), s, 'spell DC +' + str(n))
        # ── this weapon ──
        if is_weapon:
            m = re.search(r'\+(\d) bonus to attack (?:rolls )?and damage rolls made (?:with|using) (?:this|it)', s)
            if m: p['wBonus'] = int(m.group(1)); found.append('weapon +' + m.group(1))
            for m in re.finditer(r'(?:deals?|takes?) an? (?:extra|additional) (\d+)d(\d+) (%s) damage' % '|'.join(DMG), s, re.I):
                d = [int(m.group(1)), int(m.group(2)), m.group(3).capitalize()]
                if cond or USE.search(s): (p.setdefault('wNotes', [])).append('+%dd%d %s %s' % (d[0], d[1], d[2], _cond_bit(s)))
                else: p['wDice'] = d
                found.append('weapon +%dd%d %s' % tuple(d))
            m = re.search(r'use your (Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) modifier,? instead of (?:your )?(?:Strength|Dexterity)', s)
            if m and not cond: p['wAbility'] = AB[m.group(1).lower()]; found.append('weapon uses ' + m.group(1)[:3])
            m = re.search(r'(?:score|scores) a Critical Hit on a roll of (\d+)(?:–|-| or )20', s, re.I)
            if m: p.setdefault('wNotes', []).append('critical hit on %s-20' % m.group(1)); found.append('crit %s-20' % m.group(1))
    # ── charges ──
    ch = {}
    m = re.search(r'\bhas (\d+|\w+) charges', text or '') or re.search(r'\b(\d+) charges\b', text or '')
    if m and _num(m.group(1)):
        ch['max'] = _num(m.group(1))
        r = re.search(r'regains? (all (?:expended )?charges|(\d+d\d+(?: ?\+ ?\d+)?|\d+|1) expended charges?|expended charges)[^.]*?(daily at dawn|at dawn|each dawn|at dusk|daily at dusk|when you finish a (?:Long|Short) Rest|after a (?:Long|Short) Rest|at midnight|every \w+)', text or '', re.I)
        if r:
            ch['regain'] = 'all' if 'all' in r.group(1).lower() or not r.group(2) else r.group(2).replace(' ', '')
            w = r.group(3).lower()
            ch['recovery'] = 'dawn' if 'dawn' in w else 'dusk' if 'dusk' in w else 'long' if 'long' in w else 'short' if 'short' in w else 'dawn'
        found.append('%s charges' % ch['max'])
    # ── spells cast from the item ──
    spells = []
    names = spell_names or {}
    for line in (text or '').split('\n'):
        m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', line)
        if m and m.group(1).lower() not in ('spell', 'spells'):
            sp = re.sub(r'\s*\(.*\)$', '', m.group(1)).strip()
            if sp.lower() in names:
                cost = re.match(r'(\d+)', m.group(2))
                spells.append({'spellName': names[sp.lower()], 'grantType': 'itemCharges', 'chargeCost': int(cost.group(1)) if cost else 1,
                               **({'note': m.group(1)[len(sp):].strip(' ()')} if m.group(1) != sp else {})})
    for s in sentences(text):
        for m in re.finditer(r'(?:expend|use) (\d+|one|two|three|four|five|six|seven|\d+ or more)(?: of its)? charges? (?:to cast|and cast)(?: the)? ((?:[A-Z][\w\'/-]*(?: (?:of|and|from|the|with|to|on|in)?\s?[A-Z]?[\w\'/-]+){0,5}))', s):
            nm = _match_spell(m.group(2), names)
            if nm and not any(x['spellName'] == nm for x in spells):
                spells.append({'spellName': nm, 'grantType': 'itemCharges', 'chargeCost': _num(m.group(1)) or 1})
        for m in re.finditer(r'(?:you can |can )?cast (?:the )?((?:[A-Z][\w\'/-]*(?: (?:of|and|from|the|with|to|on|in)?\s?[A-Z]?[\w\'/-]+){0,5}))(?: spell)? (?:from (?:it|the \w+|this \w+))', s):
            nm = _match_spell(m.group(1), names)
            if nm and not any(x['spellName'] == nm for x in spells):
                limited = re.search(r'once|can\'t (?:be used|cast) (?:it |this property |that spell )?again until|1/day', s, re.I)
                atwill = re.search(r'at will|no charges? required|without expending', s, re.I)
                spells.append({'spellName': nm, 'grantType': 'atWill' if atwill and not limited else 'limited' if limited else 'itemCharges',
                               **({'usesMax': 1, 'recovery': 'dawn' if 'dawn' in s.lower() else 'long'} if limited else {}),
                               **({'chargeCost': 1} if not atwill and not limited else {})})
        for m in re.finditer(r'(?<!as if you had )(?<!as if by )\bcast (?:the )?((?:[A-Z][\w\'/-]*(?: (?:of|and|from|the|with|to|on|in)?\s?[A-Z]?[\w\'/-]+){0,5}))', s):
            nm = _match_spell(m.group(1), names)
            if not nm or any(x['spellName'] == nm for x in spells): continue
            if re.search(r'as if|is affected by|the effects? of', s[max(0, m.start() - 25):m.start()], re.I): continue
            limited = re.search(r"once|can't (?:be used|cast|use) (?:it |this property |that spell |this \w+ )?again until|per day|1/day", s, re.I)
            atwill = re.search(r'at will|no charges? required|without expending', s, re.I)
            usech = re.search(r'expend|charges?', s, re.I)
            gt = 'atWill' if (atwill and not limited) else 'limited' if limited else 'itemCharges' if usech else 'atWill'
            spells.append({'spellName': nm, 'grantType': gt, **({'usesMax': 1, 'recovery': 'dawn' if 'dawn' in s.lower() else 'long'} if gt == 'limited' else {}),
                           **({'chargeCost': 1} if gt == 'itemCharges' else {})})
    # ── attunement requirement ──
    req = None
    note = (item.get('attunementNote') or '').strip()
    if note:
        n = note.lower()
        cl = [c for c in CLASSES if re.search(r'\b%ss?\b' % c, n)]
        req = {'text': note}
        if cl: req['classes'] = cl
        if 'spellcaster' in n: req['spellcaster'] = True
        al = re.search(r'(good|evil|lawful|chaotic|neutral) alignment', n)
        if al: req['alignment'] = al.group(1)
        sp = re.search(r'by an? (dwarf|elf|halfling|gnome|dragonborn|tiefling|orc|warforged|aasimar|goliath|human|half-elf|half-orc|kenku|tabaxi|genasi)', n)
        if sp: req['species'] = sp.group(1)
    return {'p': p, 'u': u, 'charges': ch or None, 'spells': spells, 'req': req, 'notes': notes, 'found': found}

def _cond_bit(s):
    m = re.search(r'\b(against [^,.;]+|to (?:any|a|each) (?:creature|target)[^,.;]*|while [^,.;]+|when [^,.;]+|if [^,.;]+)', s, re.I)
    return ('(' + m.group(1)[:60] + ')') if m else '(see item)'

def _match_spell(phrase, names):
    words = phrase.strip().split()
    for k in range(min(6, len(words)), 0, -1):
        cand = ' '.join(words[:k]).strip(' ,.;:').lower()
        if cand in names: return names[cand]
    return None
