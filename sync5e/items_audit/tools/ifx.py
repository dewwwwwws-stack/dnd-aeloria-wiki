#!/usr/bin/env python3
"""Read each item's text (Items.csv wording) into mechanical effects for the sheet.

  extract(text, item) -> {'p': passive fields, 'u': fields applied when used/activated,
                          'charges': {...}, 'spells': [...], 'req': attunement requirement,
                          'notes': [...], 'found': [...labels...]}

Field names follow SPELL_FX (modules/29_spell_effects.js): ac, speed, fly/climb/swim/burrow ('walk' or feet),
resist/immune/vuln/condImm, advSaves/advChecks (ability keys or 'all'), saveBonus, senses, hpMax, skillAdv,
skillBonus, plus item fields: scores (set a score), scoreInc {ab: [n, max]}, init, initAdv, spellAtk, spellDC,
wBonus, wDice [n, die, type], wNotes, wAbility (this weapon), acIf {n, noArmour, noShield}, saveBonusAb {ab: n},
checkBonus {ab|'all': n}, hpMaxPerLevel, heal, tempHP.

Sweep 2 (27 Oct): the old book wording is lower case ("darkvision", "a swimming speed", "advantage on"), so every
rule matches either case; conditions are read from the clause the effect is in, not the whole sentence; spells are
found by name after "cast" (lists, either/or, per-spell charge costs), whatever their capitals.
"""
import re

AB = {'strength': 'str', 'dexterity': 'dex', 'constitution': 'con', 'intelligence': 'int', 'wisdom': 'wis', 'charisma': 'cha'}
ABRX = 'Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma'
DMG = ['acid', 'bludgeoning', 'cold', 'fire', 'force', 'lightning', 'necrotic', 'piercing', 'poison', 'psychic', 'radiant', 'slashing', 'thunder']
DMGRX = '|'.join(DMG)
CONDS = ['blinded', 'charmed', 'deafened', 'exhaustion', 'frightened', 'grappled', 'incapacitated', 'invisible', 'paralyzed',
         'petrified', 'poisoned', 'prone', 'restrained', 'stunned', 'unconscious']
CONDRX = '|'.join(CONDS)
SKILLS = ['acrobatics', 'animal handling', 'arcana', 'athletics', 'deception', 'history', 'insight', 'intimidation', 'investigation',
          'medicine', 'nature', 'perception', 'performance', 'persuasion', 'religion', 'sleight of hand', 'stealth', 'survival']
WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
           'eleven': 11, 'twelve': 12, 'twenty': 20, 'fifty': 50, 'a': 1, 'an': 1}
CLASSES = ['artificer', 'barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk', 'paladin', 'ranger', 'rogue', 'sorcerer',
           'warlock', 'wizard', 'psion', 'blood hunter', 'illrigger', 'gunslinger']

# an activated / temporary effect: the sentence says you take an action, expend charges, drink, for a duration...
USE = re.compile(r"\b(as an? (?:magic |bonus )?action|as a bonus action|as a reaction|you can use an? (?:action|bonus action|reaction)|"
                 r"take a (?:magic|bonus) action|expend \d+ (?:of its )?charges?|for (?:the next )?(?:1|one|\d+) (?:minute|hour|round|day)s?\b|"
                 r"until the (?:end|start) of|when you drink|drink(?:ing)? (?:this|the) potion|for the duration|once per|until you|"
                 r"you can speak (?:its|the|a) command word|after you|the next time|when you hit|on a hit|immediately)", re.I)
PASSIVE = re.compile(r"\bwhile (?:you(?:'re| are)? )?(?:wearing|holding|wielding|attuned|carrying|you wear|you hold|you carry|it is|this)|"
                     r"\bwhile (?:you )?(?:wear|hold|carry)", re.I)
STRONG = re.compile(r"\b(magic action|bonus action|as an action|use an action|use your action|reaction|expend\b|for (?:the next )?(?:1|one|\d+|ten) (?:minute|hour|round)s?|"
                    r"for the duration|command word|drink|until the (?:end|start))", re.I)
CHKP = r'''(?:\s+(?:you make )?(?:made (?!while (?:holding|wearing|wielding|carrying))|to |that |related |regarding |involving |about |against |when |if |in order |with |using |for |based |during ))'''
COND_WORDS = re.compile(r"\b(against|(?<!as )if the|(?<!as )if you|(?<!as )if it|when|whenever|in dim light|in darkness|(?:while|when|if|only) (?:you(?:'re| are) )?underwater|while (?:in|on|the|it|your|you're (?:not|in|on|raging|flying))|"
                        r"on a (?:critical|roll)|of the type|chosen|your choice|vs\.?|made to|that rely|to (?:avoid|resist|escape|end|maintain|track|find|identify|notice|detect|recall|hide|climb|swim|jump|grapple|shove|break|open|navigate|understand|interact)|"
                        r"for every|for each|per (?:ally|creature)|unless|instead of|within \d+ feet of (?:a|an|at least|one|another|any|your)|while you(?:'re| are) within)\b", re.I)
NOARM = re.compile(r"(?:if|while|when) you(?:'re| are)? (?:aren't |are not |not )?wearing no armor|(?:if|while|when) you (?:aren't|are not|do not|don't) (?:wearing |wear )?(?:any )?armor|"
                   r"wearing no armor|(?:if|while|when) you(?:'re| are)? (?:not )?(?:unarmored|without armor)|if you do not wear armor", re.I)
NOSHIELD = re.compile(r"(?:if|while|when) you(?:'re| are)? (?:using|wielding|holding) no shield|(?:if|while|when) you (?:aren't|are not|do not|don't) (?:using|use|wielding|wield|holding|hold) a shield|"
                      r"using no shield|(?:or|nor) (?:use|using|wield|wielding) a shield(?: at the same time)?|without (?:using )?a shield|if you are using no shield", re.I)

def _num(s):
    s = (s or '').lower().strip()
    return int(s) if s.isdigit() else WORDNUM.get(s)

def clean(text):
    text = (text or '').replace('’', "'").replace('‘', "'")
    return re.sub(r'(?<![\w*])\*{1,2}(?=\S)|(?<=\S)\*{1,2}(?![\w*])', '', text)   # markdown *italics*

def sentences(text):
    text = re.sub(r'\n+', ' \n ', clean(text))
    text = re.sub(r'(?<=[A-Za-z0-9)])\.(?=[A-Z][a-z]+ )', '. ', text)          # "AC.When you roll" (missing space in the source)
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"(-])|\s\n\s', text)
    return [p.strip() for p in parts if p.strip()]

HOLDER = re.compile(r"\b(?:creature|wearer|bearer|wielder|holder|owner|user)\b (?:who is |that is )?(?:holding|wearing|wielding|carrying|attuned|that (?:carries|wears|holds|wields)|with (?:the|this) \w+ in its possession)|\b(?:the|its) (?:wearer|bearer|wielder|intended wearer)\b|^To its intended wearer", re.I)
OTHER = re.compile(r"\b(?:it|its|they|their|target|creatures?|ally|allies|beast|mount|steed|familiar|companion|fish|lion|treant|construct|statue|mirror|figure|versions?|cart|vehicle|ship|boat|wagon|chariot|swarm|spirit|projection|tree|sphere|elemental|the \w+ (?:has|is|uses|gains))\b", re.I)
STATBLOCK = re.compile(r"\bAC (?:of )?\d+\b|^(?:Armor Class|Hit Points|Skills|Senses|Speed) |\b(?:STR|DEX|CON) \d+ \(|\bHP \d+\b|stat ?block|statistics (?:of|as|for)|\d+ hit points(?:,| and)|weighs \d+", re.I)

def mine(s, start):
    """True when the effect at s[start:] belongs to you (the item's owner), not a target, ally or the item itself."""
    pre = s[:start]
    clause = re.split(r'[,;:]', pre)[-1]
    if re.search(r"\b(?:is|functions as|can be (?:wielded|used) as) an? [\w' -]*?(?:that|which) grants?(?: you)? an?\s*$|\bgrants? (?:its|the) (?:wearer|bearer|wielder|user) an?\s*$", clause, re.I): return True
    if re.match(r"^\s*(?:The|This) [\w' -]{2,40}? grants?(?: you)?\s*$", clause) and not re.search(r"\b(?:creature|target|ally|allies)\b", clause, re.I): return True
    if re.search(r"\byou(?:r|'re)?\b", clause, re.I) or HOLDER.search(clause): return True
    if OTHER.search(clause): return False
    if re.search(r"\byou(?:r|'re)?\b", s, re.I) or HOLDER.search(s): return True
    return False

POSSESS = re.compile(r"\b(?:while|as long as|when) (?:you(?:'re| are)? |the \w+ (?:is |are )?|this \w+ (?:is )?|it(?:'s| is) |they(?:'re| are) )?(?:(?:is |are )?(?:on your person|in your possession|worn|held|wielded|in hand|attuned to you)|"
                     r"(?:are )?(?:wearing|holding|wielding|carrying|attuned to|wear|hold|wield|carry)\b[^,;]*)|\beven if [^,;]*|\bin addition\b|\bif (?:you|the (?:bearer|wearer|wielder)) (?:aren't|isn't|are not|is not) incapacitated|\bwhen it's used to make a ranged attack|\b(?:while|when) [\w' ]{0,40}? (?:is )?in (?:a|an|its) (?:dormant|awakened|exalted) state", re.I)
def cond_for(s, a, b):
    """A condition on the effect at s[a:b]: in its own clause (before or after it), or in a leading "While/If/When ..., " clause.
    Being worn, held, carried or attuned is not a condition."""
    pre = s[:a]
    local = re.split(r";|, and |, but |, while |\. ", pre)[-1]
    lead = re.match(r"^(?:In addition, )?((?:while|if|when|whenever|as long as|until|against|during)\b[^,]*),", s, re.I)
    post = re.split(r"[,;]|\b(?:and|but) (?=you|if|when|it|the|your|have|has|gain|are|is|can|grants?|makes?)|\bwhich\b", s[b:])[0]
    chk = lambda t: COND_WORDS.search(POSSESS.sub('', t or ''))
    light = re.search(r'\bin (?:an area of )?(?:dim light|darkness|bright light)', local + ' ' + post + ' ' + (lead.group(1) if lead else ''), re.I)
    return chk(local) or (lead and chk(lead.group(1))) or chk(post) or light

def _list(s):
    return [w.strip().lower() for w in re.split(r',\s*(?:and|or)?\s*|\s+(?:and|or)\s+', s) if w.strip()]

def extract(text, item=None, spell_names=None):
    p, u, notes, found = {}, {}, [], []
    item = item or {}
    text = clean(text)
    # random-draw items (a card's effect happens once, when drawn): nothing applies while you own them
    random_item = bool(re.match(r'Deck of Many|Teeth of Dahlver-Nar', item.get('name') or ''))   # charges still count
    is_consumable = (item.get('type') or '').lower() in ('potion', 'scroll') or re.search(r'\b(potion|elixir|oil of|philter|draught)\b', (item.get('name') or ''), re.I)
    is_weapon = item.get('isWeapon') or item.get('isAmmo')
    is_armour = item.get('isArmour')
    ctx = {'use': False, 'bullet_you': False}
    def my(s, a):
        return True if (s.startswith('- ') and ctx['bullet_you'] and not OTHER.search(s[:a])) else mine(s, a)
    def put(field, val, s, label):
        tgt = u if (is_consumable or ctx['use'] or STRONG.search(s) or (USE.search(s) and not PASSIVE.search(s))) else p
        if field in ('resist', 'immune', 'vuln', 'condImm', 'advSaves', 'advChecks', 'skillAdv'):
            tgt.setdefault(field, [])
            for v in (val if isinstance(val, list) else [val]):
                if v not in tgt[field]: tgt[field].append(v)
        elif field in ('senses', 'scores', 'scoreInc', 'skillBonus', 'saveBonusAb', 'checkBonus'):
            tgt.setdefault(field, {}).update(val)
        else:
            tgt[field] = val
        found.append(('use:' if tgt is u else '') + label)
    prev_use = False; bullet_use = None
    for s in ([] if random_item else sentences(text)):
        low = s.lower()
        # a table row (random roll, pick-one options): nothing in it applies on its own
        if s.lstrip().startswith('|'): prev_use = False; continue
        ctx['use'] = prev_use and bool(re.match(r'(If you do|When you do|For the duration|While (?:it is|active|flying)|Until|The effect|This (?:effect|property) lasts)', s))
        # a state you switch on (rage, an aura, the item's own state, time of day, class level): applied with Use, not always
        s_main = re.split(r', or (?:an? )?\+\d', s)[0]
        if re.search(r"\b(?:in|within) (?:the|its|this) aura\b|^While (?:the|this|your|it(?:'s| is)) [\w' -]{0,30}?(?:is|are|in the form of|in (?:its|a) \w+ (?:state|form))\b(?! worn| held| attached| on your person)|^While your Rage|between dusk and dawn|\bat night\b|in sunlight|^If you have \d+ or more levels|^While (?:in|you're in) (?:this|your) \w+ (?:form|state)|^While [\w ]{0,25}in this (?:way|manner|form|state)\b|^While (?:you(?:'re| are) )?(?:in (?:the |this |your |a |beast )?)?(?:form of|\w+ form\b|transformed|shapechanged|polymorphed|wild shape|raging)", s_main, re.I) and not re.search(r'(?:dormant|awakened|exalted) state', s_main, re.I): ctx['use'] = True
        if re.search(r'you and (?:your |any |all )?(?:all(?:y|ies)|creatures (?:friendly|of your choice))', s, re.I) and re.search(r'\baura\b|while in|extended|within \d+ feet', s, re.I): ctx['use'] = True
        if s.startswith('- ') and bullet_use is not None: ctx['use'] = ctx['use'] or bullet_use
        elif not s.startswith('- '): bullet_use = None
        if s.rstrip().endswith(':'):
            bullet_use = bool(STRONG.search(s)) or ctx['use'] or bool(USE.search(s) and not PASSIVE.search(s))
            ctx['bullet_you'] = bool(re.search(r"\byou(?:r|'re)?\b", s, re.I) or HOLDER.search(s))
        elif not s.startswith('- '): ctx['bullet_you'] = False
        prev_use = bool(STRONG.search(s)) or ctx['use']
        stat = bool(STATBLOCK.search(s))
        # ── "+N bonus to ..." (AC, saves, checks, spells, initiative, this weapon), single or as a list ──
        for m in re.finditer(r'\+(\d+) bonus to (.+?)(?=[.;:]|, (?:which|but|and you|and if|and when|and while|and on|or|as well as any|potentially|while|if|when)\b|,? and (?:it|its|attacks|the weapon|they|deals|does)\b|,? and (?:an? |your )?\+\d| while | if | when | as long as| for every| for each|$)', s, re.I):
            n = int(m.group(1)); tail = m.group(2)
            if stat or re.search(r"(?:not have|lose|loses|without|instead of|no longer (?:have|gain)) (?:its |the |a |an )?$", s[max(0, m.start() - 25):m.start()], re.I): continue
            is_mine = my(s, m.start())
            if re.search(r'for every|for each|up to a maximum', s[m.end():m.end() + 40], re.I): continue
            pieces = [x.strip() for x in re.split(r',\s*(?:and |as well as )?|\s+and\s+(?=(?:to |your |all |any )?(?:AC|Armor Class|saving|ability|spell|attack|damage|initiative|%s|the saving)\b)' % ABRX, tail, flags=re.I) if x.strip()]
            c = None if ctx['use'] else cond_for(s, m.start(), m.end())
            last_ab = None
            for pc in pieces:
                pl = pc.lower().replace('your ', '').replace('to ', '', 1) if pc.lower().startswith('to ') else pc.lower().replace('your ', '')
                if re.search(r'\bagainst\b|\bmade to\b|\bthat rely\b|\bto (?:identify|find|track|understand|interact|climb|swim|grapple|break|open)\b|\bwith (?:a|an|any) (?!this)|\busing (?!this|it|the weapon|these)|unarmed|marked|while', pl): continue
                ab = re.search(r'\b(%s)\b' % ABRX, pc, re.I)
                if ab: last_ab = AB[ab.group(1).lower()]
                if not is_mine and not re.search(r'damage rolls', pl): continue
                if re.match(r'(?:the )?(?:armor class|ac)\b', pl):
                    na, ns = bool(NOARM.search(s)), bool(NOSHIELD.search(s))
                    s2 = NOSHIELD.sub('', NOARM.sub('', s)); m2 = re.search(r'\+%d bonus to (?:your )?(?:Armor Class|AC)\b' % n, s2, re.I)
                    c2 = cond_for(s2, m2.start(), m2.end()) if m2 else c
                    if (na or ns) and not c2 and not ctx['use']:
                        p['acIf'] = {'n': n, **({'noArmour': True} if na else {}), **({'noShield': True} if ns else {})}; found.append('AC +%d (%s)' % (n, 'no armour' if na else 'no shield')); continue
                    if c: continue
                    if is_armour and not ctx['use'] and re.search(r"while (?:you(?:'re| are) )?(?:wearing|holding|wielding|you wear|you hold) (?:this|it|the)|this (?:armor|shield)|(?:wearing|holding) (?:this|it)\b", low): p['armourBonus'] = n; found.append('armour +%d' % n)
                    else: put('ac', n, s, 'AC +%d' % n)
                elif c and not re.search(r'damage rolls', pl): continue
                elif re.match(r'(?:all )?saving throws\b|saves\b', pl):
                    if last_ab and re.search(r'checks', pieces[0], re.I) and pieces.index(pc) > 0 and not re.search(r'ability checks', pieces[0], re.I): put('saveBonusAb', {last_ab: n}, s, '%s saves +%d' % (last_ab, n))
                    else: put('saveBonus', n, s, 'saves +%d' % n)
                elif re.match(r'(%s) saving throws' % ABRX, pc, re.I): put('saveBonusAb', {AB[re.match(ABRX, pc, re.I).group(0).lower()]: n}, s, 'save +%d' % n)
                elif re.search(r'checks%s' % CHKP, pl): continue
                elif re.match(r'(?:all )?ability checks\b', pl): put('checkBonus', {'all': n}, s, 'checks +%d' % n)
                elif re.match(r'(%s)(?: ability)? checks\b' % ABRX, pc, re.I): put('checkBonus', {last_ab: n}, s, '%s checks +%d' % (last_ab, n))
                elif re.match(r'(%s) \(([A-Za-z ]+)\)(?: and (?:%s) \(([A-Za-z ]+)\))? checks' % (ABRX, ABRX), pc, re.I):
                    for sk in re.findall(r'\(([A-Za-z ]+)\)', pc):
                        if sk.lower() in SKILLS: put('skillBonus', {sk.lower(): n}, s, '%s +%d' % (sk, n))
                elif re.match(r'spell attack(?: rolls| bonus)?$', pl) or pl == 'spell attack': put('spellAtk', n, s, 'spell attack +%d' % n)
                elif re.match(r'(?:spell save dcs?|the saving throw dcs? of (?:your )?(?:\w+ )?spells|spell save dc)$', pl) or re.match(r'(?:spell )?save dc', pl): put('spellDC', n, s, 'spell DC +%d' % n)
                elif re.match(r'initiative(?: rolls)?\b', pl): put('init', n, s, 'Initiative +%d' % n)
                elif re.match(r'attack(?: rolls)?$', pl) and re.match(r'damage rolls', (pieces[pieces.index(pc) + 1] if pieces.index(pc) + 1 < len(pieces) else ''), re.I): continue
                elif re.match(r'(?:the )?attack (?:rolls )?(?:and|&) damage rolls|damage rolls', pl):
                    rest = pl.split('damage rolls', 1)[1]
                    if 'damage rolls' in pl and pl.startswith('damage') and not re.search(r'attack', tail[:tail.lower().find('damage')], re.I): continue
                    if not is_weapon and is_mine and not rest.strip() and not c and not ctx['use'] and not STRONG.search(s):
                        p['allAtk'] = n; found.append('all attacks +%d' % n); continue
                    if is_weapon and not re.search(r'unarmed|against|marked|organic|redsmith|a creature|for the duration', rest) and not COND_WORDS.search(POSSESS.sub('', re.split(r"[,;]|\b(?:and|but) (?=you|if|when|it|the|your|have|has|gain|are|is|can|grants?|makes?|attacks|deals|does|they)|\bwhich\b", s[m.end():])[0])):
                        if re.search(r'instead of', tail, re.I) or 'wBonus' in p: continue
                        if ctx['use'] or STRONG.search(s): u.setdefault('wBonus', n); found.append('use:weapon +%d' % n)
                        else: p['wBonus'] = n; found.append('weapon +%d' % n)
        m = re.search(r'your (?:base )?Armor Class (?:is|equals|becomes) (\d+) (?:\+|plus) your Dexterity modifier', s, re.I)
        if m: put('acBase', int(m.group(1)), s, 'base AC %s + Dex' % m.group(1))
        m = re.search(r'your spell save DC and spell attack bonus (?:each )?increase by (\d)', s, re.I)
        if m: put('spellAtk', int(m.group(1)), s, 'spell attack +' + m.group(1)); put('spellDC', int(m.group(1)), s, 'spell DC +' + m.group(1))
        # ── ability scores ──
        for m in re.finditer(r'your (%s) (?:score )?(?:is|becomes|changes to|equals) (\d+)' % ABRX, s, re.I):
            put('scores', {AB[m.group(1).lower()]: int(m.group(2))}, s, '%s %s' % (m.group(1)[:3], m.group(2)))
        for m in re.finditer(r'your (%s)(?: score)? increases by (\d)(?:,? (?:to a maximum of|up to a maximum of) (\d+))?' % ABRX, s, re.I):
            if re.search(r'as does your maximum|permanently|this increase|you read|the book', low): notes.append('permanent increase when used: ' + s[:120]); continue
            put('scoreInc', {AB[m.group(1).lower()]: [int(m.group(2)), int(m.group(3) or 20)]}, s, '%s +%s' % (m.group(1)[:3], m.group(2)))
        # ── speed and movement ──
        m = re.search(r'your (?:walking )?Speed (?:increases|is increased) by (\d+) (?:feet|ft)', s, re.I)
        if m and not stat and my(s, m.start()) and not cond_for(s, m.start(), m.end()): put('speed', int(m.group(1)), s, 'Speed +%s' % m.group(1))
        if re.search(r'double your (?:walking )?Speed|your (?:walking )?Speed is doubled', s, re.I) and not stat: put('speedMult', 2, s, 'Speed x2')
        for kind, rx in (('fly', 'fly(?:ing)?'), ('swim', 'swim(?:ming)?'), ('climb', 'climb(?:ing)?'), ('burrow', 'burrow(?:ing)?')):
            m = re.search(r"(?:gain|gaining|have|has|grant(?:s|ing)? you|you)(?: also)? an? %s speed (?:of (\d+) (?:feet|ft)|equal to (?:your )?(?:normal |walking |current )?(?:walking )?speed)" % rx, s, re.I)
            if not m or stat or not my(s, m.start()): continue
            if cond_for(s, m.start(), m.end()) and not STRONG.search(s) and not ctx['use']: notes.append('conditional %s: %s' % (kind, s[:100])); continue
            put(kind, int(m.group(1)) if m.group(1) else 'walk', s, '%s %s' % (kind, m.group(1) or '= Speed'))
        # ── senses ──
        for m in re.finditer(r'\b(darkvision|blindsight|tremorsense|truesight)(?: out)?(?: to)?(?: a range of| with a range of)? (\d+) (?:feet|ft)', s, re.I):
            if re.search(r'additional|increases? by|extra', low) or stat or not my(s, m.start()): continue
            if cond_for(s, m.start(), m.end()) and not ctx['use'] and not STRONG.search(s): notes.append('conditional %s: %s' % (m.group(1), s[:100])); continue
            put('senses', {m.group(1).lower(): int(m.group(2))}, s, '%s %s' % (m.group(1), m.group(2)))
        m = re.search(r'\byou have (darkvision|blindsight|truesight)(?:,| and) (darkvision|blindsight|truesight)(?:,? (?:and )?(darkvision|blindsight|truesight))?,? (?:both |all )?(?:with a range of|out to) (\d+) (?:feet|ft)', s, re.I)
        if m and not stat and my(s, m.start()) and not (cond_for(s, m.start(), m.end()) and not ctx['use']):
            put('senses', {x.lower(): int(m.group(4)) for x in m.groups()[:3] if x}, s, 'senses %s ft' % m.group(4))
        # ── defences ──
        for m in re.finditer(r'resistance to ((?:(?:%s)(?: damage)?(?:, | and | or |, and |, or )?)+?) damage' % DMGRX, s, re.I):
            if stat or not my(s, m.start()): continue
            if re.search(r"(?:ignor\w*|overcom\w*|loses?|lose|without|doesn't have|does not have|bypass\w*)\s+(?:\w+\s+){0,2}$", s[max(0, m.start() - 30):m.start()], re.I): continue
            if re.search(r'of your choice|one of the following|chosen|that type|the triggering|the type|associated', low): continue
            if re.match(r' from nonmagical|\s*\(', s[m.end():m.end() + 20], re.I) and 'nonmagical' in s[m.end():m.end() + 20].lower(): continue
            if cond_for(s, m.start(), m.end()) and not ctx['use'] and not STRONG.search(s): notes.append('conditional resistance: ' + s[:100]); continue
            put('resist', [d.capitalize() for d in _list(m.group(1).replace(' damage', '')) if d in DMG], s, 'Resistance ' + m.group(1))
        if re.search(r'resistance to all damage(?! (?:dealt|from|caused|that|of|by|while|when|if))', s, re.I) and not stat and my(s, re.search(r'resistance to all damage', s, re.I).start()) and not re.search(r'except|other than', low): put('resistAll', True, s, 'Resistance to all damage')
        for m in re.finditer(r'(?:immunity|immune) to ((?:(?:%s)(?:, | and | or |, and )?)+) damage' % DMGRX, s, re.I):
            if stat or not my(s, m.start()) or re.search(r'of your choice|chosen|unless|if it|creature is immune|a creature', low): continue
            if cond_for(s, m.start(), m.end()) and not ctx['use'] and not STRONG.search(s): continue
            put('immune', [d.capitalize() for d in _list(m.group(1)) if d in DMG], s, 'Immunity ' + m.group(1))
        for m in re.finditer(r"(?:immunity to|immune to) (?:the |being )?((?:(?:%s)(?:, | and | or |, and )?)+)(?: conditions?)?" % CONDRX, s, re.I):
            if stat or not my(s, m.start()) or re.search(r'if it|unless it|a creature (?:is|that)|creatures? (?:that|with)|ignores this', low): continue
            if cond_for(s, m.start(), m.end()) and not ctx['use'] and not STRONG.search(s): continue
            put('condImm', [c for c in _list(m.group(1)) if c in CONDS], s, 'Immune ' + m.group(1))
        m = re.search(r"(?:you )?can't be ((?:%s)(?:,? (?:or|and) (?:%s))*)\b" % (CONDRX, CONDRX), s, re.I)
        if m and not stat and my(s, m.start()) and not re.search(r'by (?:the|a) |\bspell\b|automatically|is immune to this|in this way|again', low[m.end():m.end() + 40]) and not re.search(r'\bif it\b|\bunless it\b', low):
            put('condImm', [c for c in _list(m.group(1)) if c in CONDS], s, "can't be " + m.group(1))
        m = re.search(r'Vulnerability to ((?:%s)) damage' % DMGRX, s, re.I)
        if m and not stat and my(s, m.start()) and not re.search(r'does not have|doesn\'t have', low): put('vuln', [m.group(1).capitalize()], s, 'Vulnerability ' + m.group(1))
        # ── advantage ──
        for m in re.finditer(r'\badvantage on ((?:(?:%s)(?:, | and |, and | or )?)+) saving throws' % ABRX, s, re.I):
            if stat or not my(s, m.start()) or (cond_for(s, m.start(), m.end()) and not ctx['use']): continue
            put('advSaves', [AB[a.lower()] for a in re.findall(ABRX, m.group(1), re.I)], s, 'Adv. saves ' + m.group(1))
        m = re.search(r'\badvantage on (?:all )?saving throws(?=[.,;]| while| when|$)', s, re.I)
        if m and not stat and my(s, m.start()) and not (cond_for(s, m.start(), m.end()) and not ctx['use']): put('advSaves', ['all'], s, 'Adv. saves')
        for m in re.finditer(r'\badvantage on (?:any |all )?((?:(?:initiative rolls|(?:%s) \([A-Za-z ]+\))(?:, | and |, and | or )?)+) checks' % ABRX, s, re.I):
            if stat or not my(s, m.start()) or (cond_for(s, m.start(), m.end()) and not ctx['use']): continue
            if re.match(CHKP, s[m.end():]): continue
            for sk in re.findall(r'\(([A-Za-z ]+)\)', m.group(1)):
                if sk.lower() in SKILLS: put('skillAdv', [sk.lower()], s, 'Adv. ' + sk)
        for m in re.finditer(r'\badvantage on (%s)(?: ability)? checks' % ABRX, s, re.I):
            if stat or not my(s, m.start()) or (cond_for(s, m.start(), m.end()) and not ctx['use']): continue
            if re.match(CHKP, s[m.end():]): continue
            put('advChecks', [AB[m.group(1).lower()]], s, 'Adv. %s checks' % m.group(1)[:3])
        m = re.search(r'\badvantage on initiative(?: rolls)?', s, re.I)
        if m and not stat and my(s, m.start()) and not re.search(r'\bif you\'re\b|first in', low): put('initAdv', True, s, 'Adv. Initiative')
        # ── hit points ──
        m = re.search(r'hit point maximum (?:increases|is increased) by (\d+)(?! for each| per | times)(?: \+ your (?:character )?level)?', s, re.I)
        if m and not stat and my(s, m.start()) and not re.search(r'\beats?\b|\bthe creature\'s\b', low):
            put('hpMax', int(m.group(1)), s, 'HP max +' + m.group(1))
            if re.search(r'\+ your (?:character )?level', m.group(0), re.I): put('hpMaxPerLevel', 1, s, 'HP max +level')
        m = re.search(r'hit point maximum (?:increases|is increased) by an amount equal to (\d+) \+ your (?:character )?level', s, re.I)
        if m and not stat and my(s, m.start()): put('hpMax', int(m.group(1)), s, 'HP max +' + m.group(1)); put('hpMaxPerLevel', 1, s, 'HP max +level')
        m = re.search(r'hit point maximum (?:increases|is increased) by (?:an amount equal to )?(?:your|twice your|1 for each level you have attained|1 per level)', s, re.I)
        if m and not stat and my(s, m.start()): put('hpMaxPerLevel', 2 if 'twice' in low else 1, s, 'HP max +level')
        m = re.search(r'\byou regain (\d+d\d+(?: ?\+ ?\d+)?) hit points', s, re.I) or (is_consumable and re.search(r'(?:that drinks|who drinks|drinker|that receives it|who receives it)[^.]*? regains (\d+d\d+(?: ?\+ ?\d+)?) hit points', s, re.I))
        if m and (is_consumable or STRONG.search(s) or 'drink' in low) and not re.search(r'for each|per |if you slay|when you hit|at the start', low): u['heal'] = m.group(1).replace(' ', ''); found.append('use:heal ' + m.group(1))
        m = re.search(r'(?:gain|give yourself|grants? you) (\d+d\d+(?: ?\+ ?\d+)?|\d+) temporary hit points', s, re.I)
        if m and my(s, m.start()) and (is_consumable or STRONG.search(s)) and not re.search(r'whenever|each time|for each|when you (?:hit|reduce|slay|score|succeed)|if you|at the start', low): u['tempHP'] = m.group(1).replace(' ', ''); found.append('use:temp HP ' + m.group(1))
        # ── this weapon ──
        if is_weapon:
            for m in re.finditer(r'(?:deals?|takes?) an? (?:extra|additional) (\d+)d(\d+) (%s) damage' % DMGRX, s, re.I):
                d = [int(m.group(1)), int(m.group(2)), m.group(3).capitalize()]
                if cond_for(s, m.start(), m.end()) or USE.search(s): (p.setdefault('wNotes', [])).append('+%dd%d %s %s' % (d[0], d[1], d[2], _cond_bit(s)))
                else: p['wDice'] = d
                found.append('weapon +%dd%d %s' % tuple(d))
            m = re.search(r'use your (%s) modifier,? instead of (?:your )?(?:Strength|Dexterity)' % ABRX, s, re.I)
            if m and not cond_for(s, m.start(), m.end()): p['wAbility'] = AB[m.group(1).lower()]; found.append('weapon uses ' + m.group(1)[:3])
            m = re.search(r'(?:score|scores) a Critical Hit on a roll of (\d+)(?:–|-| or )20', s, re.I)
            if m: p.setdefault('wNotes', []).append('critical hit on %s-20' % m.group(1)); found.append('crit %s-20' % m.group(1))
    # ── charges ──
    ch = {}
    m = (re.search(r'\b(?:has|have|holds?|starts? with) (\d+|\w+) charges', text, re.I) or re.search(r'\bcan (?:have|hold) up to (\d+) charges', text, re.I)
         or re.search(r'\bgives? (?:the \w+ )?(\d+) charges', text, re.I) or re.search(r'\b(\d+) charges\b', text))
    dm = re.search(r'\b(?:has|have) (\d+)d(\d+)(?: ?\+ ?(\d+))? charges', text, re.I)
    if dm:
        ch['max'] = int(dm.group(1)) * int(dm.group(2)) + int(dm.group(3) or 0); ch['note'] = 'starts with %sd%s%s charges' % (dm.group(1), dm.group(2), (' + ' + dm.group(3)) if dm.group(3) else '')
    elif m and _num(m.group(1)) and _num(m.group(1)) > 1 or (m and m.group(1).isdigit()):
        ch['max'] = _num(m.group(1))
    if ch:
        r = re.search(r'regains? (all (?:expended )?charges|(\d+d\d+(?: ?\+ ?\d+)?|\d+|1) expended charges?|expended charges)[^.]*?(daily at dawn|at dawn|each dawn|at dusk|daily at dusk|when you finish a (?:Long|Short) Rest|after a (?:Long|Short) Rest|at midnight|every \w+)', text, re.I)
        if r:
            ch['regain'] = 'all' if 'all' in r.group(1).lower() or not r.group(2) else r.group(2).replace(' ', '')
            w = r.group(3).lower()
            ch['recovery'] = 'dawn' if 'dawn' in w else 'dusk' if 'dusk' in w else 'long' if 'long' in w else 'short' if 'short' in w else 'dawn'
        found.append('%s charges' % ch['max'])
    # ── spells cast from the item ──
    spells = [] if random_item else find_spells(text, item, spell_names or {}, bool(ch))
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

# ── spells ──
NEG_CAST = re.compile(r"as if (?:you |it |they )?(?:had |were |was )?(?:been )?cast|as if by|if (?:it|they) were cast|when (?:you|a creature|it|someone|another creature|an ally) casts?\b|whenever (?:you|a creature) casts?\b|"
                      r"you cast (?:a|any|another|the) spell\b|is cast (?:on|upon|at|within|with|by)|(?:were|was|been|being) cast|can't cast|cannot cast|casts? spells\b|"
                      r"effects? of (?:a|an|the)\b|affected by|(?:a|any|the) spell (?:you|that you) cast|spells you cast|you can't|unable to cast|instead of casting|without casting|"
                      r"cast(?:ing)? a spell|cast(?:ing)? (?:the|that) spell (?:using|with) a spell slot|spell (?:slot|level) (?:used|expended) to cast|by casting|(?:if|once|after|before|unless) (?:you|a creature|someone|it) casts?\b|when cast\b|is cast\b|can normally cast|unable to cast|\band can cast|when casting|while casting|\b(?:if|when|whenever)\b[^,.]{0,40}\bcasts\b|as if (?:they|he|she|it) had cast", re.I)
_SPRX = {}
def _spell_rx(names):
    k = id(names)
    if k not in _SPRX:
        alt = sorted(names, key=len, reverse=True)
        _SPRX[k] = re.compile(r"(?<![\w'])(%s)(?![\w'])" % '|'.join(re.escape(a) for a in alt), re.I)
    return _SPRX[k]
def _cost(after):
    m = re.match(r"\s*(?:spell\s*)?\(([^)]*)\)", after)
    if not m: return None
    t = m.group(1).lower()
    c = re.search(r'(\d+|one|two|three|four|five|six|seven|eight|nine) charges?', t)
    if c: return _num(c.group(1))
    if re.search(r'no charges?|at will|0 charges?|free', t): return 0
    return None
def find_spells(text, item, names, has_charges):
    out = []
    if not names: return out
    if (item.get('type') or '').lower() == 'scroll': return out
    rx = _spell_rx(names)
    def add(nm, gt, cost=None, uses=None, rec=None, note=None):
        if any(x['spellName'] == nm for x in out): return
        e = {'spellName': nm, 'grantType': gt}
        if gt == 'itemCharges': e['chargeCost'] = cost or 1
        if gt == 'limited': e['usesMax'] = uses or 1; e['recovery'] = rec or 'long'
        if note: e['note'] = note
        out.append(e)
    # tables: | spell | charges |
    for line in text.split('\n'):
        m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', line)
        if m and m.group(1).lower() not in ('spell', 'spells'):
            sp = re.sub(r'\s*\(.*\)$', '', m.group(1)).strip()
            if sp.lower() in names:
                c = re.match(r'(\d+)', m.group(2))
                add(names[sp.lower()], 'atWill' if (c and int(c.group(1)) == 0) else 'itemCharges' if (c or has_charges) else 'atWill', int(c.group(1)) if c else 1,
                    note=(m.group(1)[len(sp):].strip(' ()') or None) if m.group(1) != sp else None)
    S = sentences(text)
    for i, s in enumerate(S):
        if s.lstrip().startswith('|'): continue
        nxt = ' '.join(S[i + 1:i + 3])
        for m in re.finditer(r'\bcast(?:s|ing)?\b', s, re.I):
            win = s[max(0, m.start() - 40):m.end() + 30]
            if NEG_CAST.search(win): continue
            if re.match(r"\s+(?:in|down|on it|upon it|off|out|aside|a shadow|shadows|light on|its)\b", s[m.end():], re.I): continue
            pre_c = re.split(r'[,;:]', s[:m.start()])[-1]
            if not re.search(r"\byou(?:r)?\b|can be used to|lets? you|allows? you|allowing you|grants? you|its (?:wearer|bearer|wielder)|the (?:wearer|bearer|wielder)|attuned", s[:m.start()], re.I): continue
            if OTHER.search(pre_c) and not re.search(r"\byou\b|can be used to|its (?:wearer|bearer|wielder)|attuned to it", pre_c, re.I): continue
            if re.search(r"\b(?:the|this|that) [\w' -]{1,25}? (?:can|will|may|then|also)?\s*$", pre_c, re.I) and not re.search(r"\byou\b|can be used to|HOLDERX", pre_c, re.I) and not HOLDER.search(pre_c): continue
            rest = s[m.end():]
            # the list after "one of the following spells ... :" or straight after "cast (the|either)"
            lm = re.match(r"\s+(?:any |one |either |both |each |up to \w+ )?(?:of )?(?:the |these )?(?:following(?: \w+)? )?spells?[^:.]*:\s*(.*)", rest, re.I)
            seg = lm.group(1) if lm else rest
            pos = 0; got = []
            while True:
                mm = re.match(r"\s*(?:(?:the|either|both|a|an|its|that|one of) )*(?:(?:\d+(?:st|nd|rd|th)|\w+)-level (?:version of (?:the )?)?|level \d+ version of (?:the )?)?", seg[pos:], re.I)
                pos += mm.end()
                sm = rx.match(seg, pos)
                if not sm: break
                nm = names[sm.group(1).lower()]
                after = seg[sm.end():]
                got.append((nm, _cost(after), sm.start()))
                cm = re.match(r"(?:\s*spells?)?(?:\s*\([^)]*\))?(?:\s*(?:,\s*(?:or|and)?|or|and|/)\s*)", after, re.I)
                if not cm or not cm.group(0).strip(): break
                pos = sm.end() + cm.end()
            if not got: continue
            before = s[max(0, m.start() - 70):m.start()]
            ce = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)(?: or more)?\s+(?:of (?:its|the \w+'s|the|his|her|their) )?charges?(?:\s+[\w']+){0,3}?\s+(?:to|and)\s*$", before, re.I)
            seg_txt = s[m.start():m.start() + 220]
            limited = re.search(r"\bcast[^.]{0,80}\bonce\b(?! you)|can't (?:be used|cast|use)[^.]*again until|(?:once|one time) (?:per|each) (?:day|dawn|long rest)|1/day|once you(?:'ve)? (?:use|cast)|until the next dawn|until you finish a long rest|regains? (?:the )?(?:ability|use)", s + ' ' + nxt, re.I)
            times = re.search(r'\b(two|three|\d+) times (?:per|each) day', s + ' ' + nxt, re.I)
            atwill = re.search(r'at will|no charges? (?:required|needed)|without expending', seg_txt, re.I)
            usech = re.search(r'expend|charges?', s[max(0, m.start() - 80):m.start() + 160], re.I) and has_charges
            for nm, cost, _ in got:
                if cost == 0: add(nm, 'atWill')
                elif cost: add(nm, 'itemCharges', cost)
                elif ce: add(nm, 'itemCharges', _num(ce.group(1)) or 1)
                elif times: add(nm, 'limited', uses=_num(times.group(1)), rec='dawn')
                elif limited and not re.search(r'\bat will\b', seg_txt, re.I): add(nm, 'limited', rec='dawn' if 'dawn' in (s + nxt).lower() else 'long')
                elif atwill: add(nm, 'atWill')
                elif usech: add(nm, 'itemCharges', 1)
                else: add(nm, 'atWill')
    return out

def _cond_bit(s):
    m = re.search(r'\b(against [^,.;]+|to (?:any|a|each) (?:creature|target)[^,.;]*|while [^,.;]+|when [^,.;]+|if [^,.;]+)', s, re.I)
    return ('(' + m.group(1)[:60] + ')') if m else '(see item)'
