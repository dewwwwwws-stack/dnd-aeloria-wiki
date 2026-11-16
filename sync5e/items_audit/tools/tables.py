# Squashed tables (28 Oct): in Items.csv every table lost its cell breaks, e.g.
#   "Deck of Illusions1d100Illusion01-03Adult Red Dragon04-06Archmage..."
# This turns such text back into markdown pipe tables (the item window renders those), word for word:
# only row and cell breaks are added. Rows are found by their roll numbers (1, 2, 3 ... or 01-03, 04-06 ...,
# each starting one after the last ended); cells by the places two words run together ("molar)9 cats").
# Tables without a die column, or that don't follow the pattern, are given by hand in MANUAL.
import re

DIE = r'1?d(?:4|6|8|10|12|20|100)'

def glue_points(s):
    """Positions where two words run together: 'catsThe', 'molar)9', 'Rare75' - but not inside dice ('2d6')."""
    out = []
    for i in range(1, len(s)):
        a, b = s[i - 1], s[i]
        if b == ' ' or a == ' ': continue
        if b.isupper() or b in '(“"':
            if a.islower() or a in ').]\'"%’”!?*':
                out.append(i)
        elif b.isdigit():
            if a in ').]\'"%’”!?*': out.append(i)
            elif a.isalpha() and not (a == 'd' and i >= 2 and s[i - 2].isdigit()) and not (a in 'dx×' and i >= 2 and s[i - 2] == ' '):
                out.append(i)
    return out

def _num(s):
    return 100 if s == '00' else int(s)

def _is_label_at(body, k, loose=False):
    if k > 0 and body[k - 1] in ' ,+-–(/:#$': return False
    if k >= 2 and body[k - 1] in 'x×' and (body[k - 2].isdigit() or body[k - 2] == ' '): return False   # "2 x 4", "3x"
    if k >= 2 and body[k - 1] == 'd' and body[k - 2].isdigit(): return False   # 2d6
    if k > 0 and body[k - 1].isdigit() and not loose: return False   # "...the number 458..." only as a last resort
    return True

def find_rows(body, dmax):
    """Split body into [(label, text)] whose labels run 1.. with no gaps."""
    out = []
    dead = set()   # (pos, next label) already known not to lead to a full table - stops long d100 tables blowing up
    def rec(pos, nxt):
        if (pos, nxt) in dead: return None
        r = _rec(pos, nxt)
        if not r: dead.add((pos, nxt))
        return r
    def _rec(pos, nxt):
        for w in (2, 1, 3):
            lab = body[pos:pos + w]
            if not lab.isdigit() or _num(lab) != nxt: continue
            if nxt == 1 and w == 2 and lab != '01': continue
            p = pos + w
            ends = [None]
            if body[p:p + 1] in '-–':
                ends = []
                for ew in (2, 1, 3):
                    e = body[p + 1:p + 1 + ew]
                    if e.isdigit() and _num(e) > nxt and (not dmax or _num(e) <= dmax): ends.append((ew, _num(e)))
            for en in ends:
                q = p if en is None else p + 1 + en[0]
                last = nxt if en is None else en[1]
                label = body[pos:q]
                if dmax and last >= dmax:
                    out.append((label, body[q:])); return True
                nl = last + 1
                cands = {str(nl), '%02d' % nl} | ({'00'} if nl == 100 else set())
                ks = [q + 1 + m.start() for m in re.finditer(r'(?=\d)', body[q + 1:])]
                ks = [k for k in ks if any(body.startswith(c, k) for c in cands)]
                for k in [k for k in ks if _is_label_at(body, k)] + [k for k in ks if not _is_label_at(body, k) and _is_label_at(body, k, True)]:
                    out.append((label, body[q:k]))
                    if rec(k, nl): return True
                    out.pop()
                if not dmax:
                    out.append((label, body[q:])); return True
        return None
    return out if rec(0, 1) else None

def split_cells(text, n):
    text = text.strip()
    if n <= 1: return [text]
    if re.fullmatch('—+', text) and len(text) == n: return list(text)
    cuts = glue_points(text)
    if len(cuts) < n - 1: return None
    cuts = cuts[:n - 1]
    parts, prev = [], 0
    for c in cuts: parts.append(text[prev:c]); prev = c
    parts.append(text[prev:])
    return parts

def esc(s):
    return s.replace('|', '\\|').strip()

def to_md(title, head, rows):
    L = []
    if title and title.strip(' -'): L.append('**' + title.strip(' -') + '**')
    L.append('| ' + ' | '.join(esc(h) for h in head) + ' |')
    L.append('|' + '---|' * len(head))
    for r in rows: L.append('| ' + ' | '.join(esc(c) for c in r) + ' |')
    return '\n'.join(L)

# a table starts with an optional title glued to its die, a header, then row 1 glued to the header
START = re.compile(r'(?:(?<=[A-Za-z\)\'’])|^)(' + DIE + r')(?=[A-Za-z])')
TRAIL = re.compile(r'(?<=[a-z\.\)\]’\'"!?]) (?=(?:[A-Z][\w\'’-]*)(?: (?:[A-Z][\w\'’-]*|of|the|and|or|a|an|to|in|on|for|with|at|by)){0,5}\. [A-Z])')

def _table_starts(line):
    """[(title_start, die_start, die_end)] for each table on the line."""
    res = []
    for m in START.finditer(line):
        rest = line[m.end():m.end() + 90]
        if not re.match(r'[A-Za-z][^0-9]{0,80}?(?<=[A-Za-z\)\'’\. ])0?1(?=[^0-9]|-)', rest): continue
        ds = m.start(1)
        gl = [g for g in glue_points(line[:ds]) if ds - g <= 60]
        ts = gl[-1] if gl else (0 if ds <= 60 else ds)
        if res and ts < res[-1][2]: ts = ds
        res.append((ts, ds, m.end(1)))
    return res

def rebuild_line(line, trail=True):
    """Return text with squashed tables turned into markdown, or None if there are none."""
    st = _table_starts(line)
    if not st: return None
    pieces, prev = [], 0
    for i, (ts, ds, de) in enumerate(st):
        if ts > prev: pieces.append(('text', line[prev:ts]))
        end = st[i + 1][0] if i + 1 < len(st) else len(line)
        pieces.append(('table', line[ts:ds], line[ds:de], line[de:end]))
        prev = end
    out = []
    for pc in pieces:
        if pc[0] == 'text':
            out.append(pc[1].strip()); continue
        _, title, die, rest = pc
        dmax = int(die.lstrip('1')[1:])
        first = re.search(r'(?<=[A-Za-z\)\'’\. ])(0?1)(?=[^0-9]|-)', rest)
        if not first: return None
        hdr, body = rest[:first.start()], rest[first.start():]
        heads = [hdr[a:b].strip() for a, b in zip([0] + glue_points(hdr), glue_points(hdr) + [len(hdr)]) if hdr[a:b].strip()]
        rows = find_rows(body, dmax)
        if not rows: return None
        tail = ''
        if trail and pc is pieces[-1]:
            lab, txt = rows[-1]
            m = TRAIL.search(txt)
            if m: rows[-1] = (lab, txt[:m.start()]); tail = txt[m.end():]
        cells = []
        for lab, txt in rows:
            c = split_cells(txt, len(heads))
            if c is None: return None
            cells.append([lab] + c)
        out.append(to_md(title, [die] + heads, cells))
        if tail: out.append(tail.strip())
    return '\n\n'.join(x for x in out if x)

MANUAL = {'medzo_s_crossbow': [("Matching NumberEffect1You can reroll one of the weapon's damage dice, even if it was a matching number. You must use the new roll.2The next attack roll made against the target before the end of your next turn has advantage.3The target has disadvantage on attack rolls it makes until the end of your next turn.4If the target is a hostile creature, 30gp magically appears at your feet. Range.", "\n\n| Matching Number | Effect |\n|---|---|\n| 1 | You can reroll one of the weapon's damage dice, even if it was a matching number. You must use the new roll. |\n| 2 | The next attack roll made against the target before the end of your next turn has advantage. |\n| 3 | The target has disadvantage on attack rolls it makes until the end of your next turn. |\n| 4 | If the target is a hostile creature, 30gp magically appears at your feet. |\n\nRange.")], 'abjurer_s_bangle': [('RarityWard Hit PointsUncommon30Rare75Very Rare120', '\n\n| Rarity | Ward Hit Points |\n|---|---|\n| Uncommon | 30 |\n| Rare | 75 |\n| Very Rare | 120 |\n\n')], 'belt_of_giant_strength': [('BeltStr. RarityBelt of Hill Giant Strength21RareBelt of Frost Giant Strength or Belt of Stone Giant Strength23Very RareBelt of Fire Giant Strength25Very RareBelt of Cloud Giant Strength27LegendaryBelt of Storm Giant Strength29Legendary', '\n\n| Belt | Str. | Rarity |\n|---|---|---|\n| Belt of Hill Giant Strength | 21 | Rare |\n| Belt of Frost Giant Strength or Belt of Stone Giant Strength | 23 | Very Rare |\n| Belt of Fire Giant Strength | 25 | Very Rare |\n| Belt of Cloud Giant Strength | 27 | Legendary |\n| Belt of Storm Giant Strength | 29 | Legendary |\n\n')], 'cube_of_force': [("Cube of Force FacesSpellCharge CostMage Armor1Shield1Leomund's Tiny Hut3Mordenkainen's Private Sanctum4Otiluke's Resilient Sphere4Wall of Force5", "\n\n**Cube of Force Faces**\n| Spell | Charge Cost |\n|---|---|\n| Mage Armor | 1 |\n| Shield | 1 |\n| Leomund's Tiny Hut | 3 |\n| Mordenkainen's Private Sanctum | 4 |\n| Otiluke's Resilient Sphere | 4 |\n| Wall of Force | 5 |\n\n")], 'eye_of_vecna': [('Eye of Vecna SpellsSpellCharge CostClairvoyance2Crown of Madness1Disintegrate4Dominate Monster5Eyebite4', '\n\n**Eye of Vecna Spells**\n| Spell | Charge Cost |\n|---|---|\n| Clairvoyance | 2 |\n| Crown of Madness | 1 |\n| Disintegrate | 4 |\n| Dominate Monster | 5 |\n| Eyebite | 4 |\n\n')], 'hand_of_vecna': [('Hand of Vecna SpellsSpellCharge CostFinger of Death5Sleep1Slow2Teleport3', '\n\n**Hand of Vecna Spells**\n| Spell | Charge Cost |\n|---|---|\n| Finger of Death | 5 |\n| Sleep | 1 |\n| Slow | 2 |\n| Teleport | 3 |\n\n')], 'eye_and_hand_of_vecna': [('Eye of Vecna SpellsSpellCharge CostClairvoyance2Crown of Madness1Disintegrate4Dominate Monster5Eyebite4', '\n\n**Eye of Vecna Spells**\n| Spell | Charge Cost |\n|---|---|\n| Clairvoyance | 2 |\n| Crown of Madness | 1 |\n| Disintegrate | 4 |\n| Dominate Monster | 5 |\n| Eyebite | 4 |\n\n'), ('Hand of Vecna SpellsSpellCharge CostFinger of Death5Sleep1Slow2Teleport3', '\n\n**Hand of Vecna Spells**\n| Spell | Charge Cost |\n|---|---|\n| Finger of Death | 5 |\n| Sleep | 1 |\n| Slow | 2 |\n| Teleport | 3 |\n\n')], 'luba_s_tarokka_of_souls': [('13SeerVampire14TempterVampire spawn15-100——The released soul', '13SeerVampire14TempterVampire spawn15-100——\x03The released soul')], 'absorbing_tattoo': [('10OrangeThunder Absorbing Tattoo Damage Absorption.', '10OrangeThunder Absorbing Tattoo\u0003Damage Absorption.')], 'deck_of_many_more_things': [("67-00Roll again* Found in the Deck of Many Things as depicted in the Dungeon Master's Guide Aberration.", "67-00Roll again\x03* Found in the Deck of Many Things as depicted in the Dungeon Master's Guide\x03Aberration.")]}
# Sovereignseed Satchel: one seed per paragraph after the header
SEEDS = ['Binding Bur', 'Bouncing Bloom', 'Cloaking Cotton', 'Fiddle-Ferry Fig', 'Rose of Radiance', 'Spanning Sprout']

def rebuild_text(key, text):
    if not text: return text, 0
    n = 0
    for old, new in MANUAL.get(key, []):
        if old in text: text = text.replace(old, new); n += 1
    if key == 'sovereignseed_satchel' and 'Optional Captiond6Seed1 ' in text:
        i = text.index('Optional Captiond6Seed1 ')
        paras = text[i:].split('\n\n')
        rows = []
        for j, nm in enumerate(SEEDS):
            p = paras[j]
            p = p[len('Optional Captiond6Seed1 '):] if j == 0 else p[len(str(j + 1)) + 1:]
            rows.append([str(j + 1), p])
        text = text[:i] + to_md('Optional Caption', ['d6', 'Seed'], rows) + ('\n\n' + '\n\n'.join(paras[len(SEEDS):]) if len(paras) > len(SEEDS) else '')
        n += 1
    out = []
    for line in text.split('\n'):
        if '\u0003' in line:
            head, *rest = line.split('\u0003')
            md = rebuild_line(head, trail=False)
            if md: out.append('\n' + md + '\n\n' + '\n\n'.join(rest) + '\n'); n += 1; continue
            line = ' '.join([head] + rest)
        md = None if '|' in line else rebuild_line(line)
        if md: out.append('\n' + md + '\n'); n += 1
        else: out.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip('\n'), n
