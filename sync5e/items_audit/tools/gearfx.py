# Gear wiring (28 Oct): what each mundane item's own text lets the sheet do.
#   acts:  rows for the Attacks panel - a saving throw (DC worked out or fixed) or an attack, damage, range
#   uses:  a tracker for items with a number of uses (Healer's Kit: ten uses)
#   use:   an item used up when used (flasks, vials, grenades, poisons): the Use button takes one off the quantity
#   notes: what the sheet can't do itself, shown as "Not automatic"
# Read from the text; MANUAL holds the few the reader can't phrase right. Output: items_gearfx.json {key: fx}
import json, re, sys
B = '/home/claude/cs/tooling/items_audit/'
G = json.load(open(B + 'sheetdata/PHB_GEAR.json')); P = json.load(open(B + 'items_patch.json'))
for g in G:
    if g['key'] in P['gearSet']: g.update(P['gearSet'][g['key']])
G += P['gearAdd']

AB = {'strength': 'str', 'dexterity': 'dex', 'constitution': 'con', 'intelligence': 'int', 'wisdom': 'wis', 'charisma': 'cha'}
CONDS = ['Blinded', 'Charmed', 'Deafened', 'Frightened', 'Grappled', 'Incapacitated', 'Paralyzed', 'Petrified', 'Poisoned', 'Prone', 'Restrained', 'Stunned', 'Unconscious']
USED_UP = re.compile(r'\b(vial|flask|grenade|dynamite|bomb|seed|keg|powder horn|pouch|dose)\b', re.I)

def first_para_with(t, pat):
    for p in t.split('\n\n'):
        if re.search(pat, p, re.I): return p
    return ''

def read(g):
    t = g.get('desc') or ''
    fx = {}
    m = re.search(r'\b(ten|five|three|two|twenty|\d+) uses\b', t, re.I)
    if m:
        n = {'ten': 10, 'five': 5, 'three': 3, 'two': 2, 'twenty': 20}.get(m.group(1).lower()) or int(m.group(1))
        fx['uses'] = {'max': n, 'recovery': 'none'}
    p = first_para_with(t, r'saving throw')
    trig = re.search(r'replace one of your attacks|\bthrow|\bspread|\bspill|\bset a\b|ignite|explode|Setting fire|\bcoat\b|As a Utilize action|as an? action|Bonus Action', p, re.I)
    sm = re.search(r'(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) saving throw', p)
    if p and trig and sm and not re.search(r'saving throws against|succeed on saving throws|automatically succeed', p, re.I):
        a = {'save': AB[sm.group(1).lower()]}
        dm = re.search(r'DC 8 plus your (\w+) modifier and (?:your )?Proficiency Bonus', p)
        if dm: a['dcAb'] = AB.get(dm.group(1).lower(), 'dex')
        else:
            m2 = re.search(r'DC (\d+)', p)
            if m2: a['dc'] = int(m2.group(1))
        m3 = re.search(r'\(?(\d+d\d+(?:\s*\+\s*\d+)?)\)?\s+([A-Za-z]+) damage', p) or re.search(r'\b(\d+)\s+(Piercing|Fire|Acid|Poison|Bludgeoning|Slashing|Cold|Radiant|Necrotic|Force|Thunder|Lightning|Psychic) damage', p, re.I)
        if m3: a['dmg'] = m3.group(1).replace(' ', '') + ' ' + m3.group(2).capitalize()
        if re.search(r'half as much', p, re.I): a['half'] = True
        cs = [c for c in CONDS if re.search(r'\b' + c + r'\b', p, re.I)]
        if cs: a['cond'] = cs
        if re.search(r'subjected to|Ingested|Injury|Inhaled|Contact', t): a['time'] = 'Poison'; fx['use'] = True
        elif re.search(r'replace one of your attacks', p, re.I): a['time'] = 'Attack'
        elif re.search(r'Bonus Action', p): a['time'] = 'Bonus Action'
        elif re.search(r'Utilize action', p): a['time'] = 'Utilize'
        else: a['time'] = 'Action'
        rm = re.search(r'within (\d+) feet of (?:yourself|you)', p) or re.search(r'(?:thrown?|throw (?:a|it|the)?\s*\w*)\s+(?:at a point )?up to (\d+) feet', t) or re.search(r'up to (\d+) feet away', t)
        if rm: a['range'] = rm.group(1) + ' ft'
        am = re.search(r'(\d+)-foot(?:-radius)? (Sphere|sphere|square|Cube|cube|radius)', p)
        if am: a['area'] = am.group(0).replace('-foot-radius', '-ft radius').replace('-foot', '-ft').lower()
        else:
            am = re.search(r'within (\d+) feet of (?:the|it|a)\b', p)
            if am: a['area'] = am.group(1) + ' ft around it'
        fx['acts'] = [a]
    if fx.get('acts') and (USED_UP.search(g['name']) or USED_UP.search(t[:200]) or g.get('category') == 'Explosive'):
        fx['use'] = True
    return fx

MANUAL = {
    'torch': {'acts': [{'atk': 'str', 'dmg': '1 Fire', 'time': 'Attack', 'range': 'melee', 'note': 'Simple Melee weapon'}]},
    'healer_s_kit': {'uses': {'max': 10, 'recovery': 'none'}, 'notes': ['Utilize action, 1 use: stabilize an Unconscious creature at 0 Hit Points without a Wisdom (Medicine) check']},
    'antitoxin': {'use': True, 'notes': ['Bonus Action to drink: Advantage on saving throws to avoid or end the Poisoned condition for 1 hour']},
    'basic_poison': {'use': True, 'notes': ['Bonus Action: coat one weapon or up to three pieces of ammunition; Piercing or Slashing damage from it deals an extra 1d4 Poison (1 minute or until dealt)']},
    'bedroll': {'notes': ['While in it: automatically succeed on saving throws against extreme cold']},
    'blanket': {'notes': ['While wrapped in it: Advantage on saving throws against extreme cold']},
    'clothing_cold_weather': {'notes': ['While dry: automatically succeed on saving throws against extreme cold']},
    'desert_clothing': {'notes': ['Without Medium or Heavy armour: automatically succeed on saving throws against extreme heat']},
    'warm_fungal_clothing': {'notes': ['Automatically succeed on saving throws against extreme cold']},
    'oil': {'use': True, 'acts': [{'save': 'dex', 'dcAb': 'dex', 'cond': [], 'time': 'Attack', 'range': '20 ft', 'note': 'covered in oil: +5 Fire if it takes Fire damage within 1 minute'}],
            'notes': ['Utilize action: pour on a 5-ft square within 5 feet; if lit it burns for 2 rounds, 5 Fire damage to a creature entering or ending its turn there', 'Fuel: burns 6 hours in a Lamp or Lantern']},
    'staff': {'acts': []},
    'ball_bearings': {'use': False},
    'eyescratch': {'use': True}, 'midnight_tears': {'use': True}, 'zabou': {'use': True},
    'soothsalts': {'acts': [], 'use': True, 'notes': ['A dose: Advantage on Intelligence checks for 1d4 hours (see the text for the risks)']},
    'black_ghost_orchid_seed': {'acts': [], 'use': True, 'notes': ['Eaten: the creature is affected by Feign Death (DC 16 Constitution save to resist if unwilling)']},
    'white_ghost_orchid_seed': {'use': True, 'notes': ['Ground and scattered over a dead body: Resurrection']},
    'keg_of_alchemist_s_fire': {'use': True, 'acts': [{'atk': 'str', 'dmg': '6d6 Fire', 'time': 'Action', 'note': 'lobbed; on a hit it is set ablaze and takes the damage again each turn until put out'}]},
    'smoke_grenade': {'use': True, 'acts': [{'time': 'Action', 'range': '60 ft', 'area': '20-ft radius sphere', 'note': 'Heavily Obscured for 1 minute'}]},
    'holy_water': {'use': True, 'extra': 'only against a Fiend or an Undead'},
    'alchemist_s_fire': {'use': True, 'extra': 'and it starts burning'},
    'net': {'extra': 'Huge or larger succeeds automatically; escape: DC 10 Strength (Athletics)'},
}

out = {}
for g in G:
    fx = read(g)
    m = MANUAL.get(g['key'])
    if m:
        m = dict(m); extra = m.pop('extra', None)
        fx.update(m)
        if fx.get('acts') == []: fx.pop('acts')
        if fx.get('use') is False: fx.pop('use')
        if extra and fx.get('acts'): fx['acts'][0]['note'] = extra
    if g['key'] == 'fragmentation_grenade' and fx.get('acts'): fx['acts'][0]['area'] = '20-ft radius sphere'
    if fx: out[g['key']] = fx
json.dump(out, open(B + 'items_gearfx.json', 'w'), indent=1, ensure_ascii=False)
if __name__ == '__main__':
    names = {g['key']: g['name'] for g in G}
    for k, v in out.items(): print(names[k], '|', json.dumps(v, ensure_ascii=False))
    print(len(out), 'gear items wired', file=sys.stderr)
