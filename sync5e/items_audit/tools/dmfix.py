# DM-edited and homebrew items: wiring their own text calls for that the DM edit doesn't carry (reviewed one by one,
# 27 Oct). Each fix holds a hash of the DM text it was made from; the sheet applies it only while the DM's text is
# unchanged, so a later DM edit always wins. Fixes only add: they never remove or lower anything the DM set, except
# where the DM's own wiring contradicts the DM's own text (noted).
# Output: items_dmfix.json  {key: {h, name, fx?, effects?, charges?, spells?, notes}}
import json, sys
sys.path.insert(0, '/home/claude/cs/tooling/items_audit/tools'); import ifx
DM = json.load(open('/home/claude/cs/tooling/items_audit/dm_live_28oct.json'))['items']   # the user's live DM file (28 Oct); the corrected copy keeps the same text for every kept item

def h(s):
    x = 0
    for ch in s or '':
        x = (x * 33 + ord(ch)) & 0xffffffff
    return x

FIX = {
  'amulet_of_the_watcher': {
    'effects': {'skillProfOrExpert': ['perception']},                      # "Gain proficiency in perception. If you already have proficiency, gain expertise instead."
    'charges': {'recovery': 'dawn', 'recoveryNote': 'regains 1d4'},        # "regains 1d4 daily at Dawn" (was set to no recovery)
    'fx': {'notes': ['Third Eye: +1d4 to Perception or Investigation checks involving sight']},
  },
  'urnblade': {
    'effects': {'weaponBonusByEffect': {'shadow_ally': 2}, 'dmgTypeOverride': 'necrotic'},   # "deals necrotic damage", "+2 while the summoned shadow exists"
  },
  'dwarven_thrower': {
    'effects': {'weaponBonus': 3},                                         # DM text: "+3 bonus"; DM wiring said +2
    'fx': {'p': {'wNotes': ['+1d8 when thrown']}},
  },
  'crimson_moon_blade': {
    'charges': {'recovery': 'dawn', 'recoveryNote': 'regains 1d6+1'},      # "regains 1d6 + 1 expended charges daily at dawn"
    'fx': {'p': {'wNotes': ['+2d6 Radiant (expend 1 charge when you hit)']}},
  },
  'eye_of_the_watcher': {
    'fx': {'u': {'senses': {'darkvision': 120}}, 'notes': ['Use while looking through the Eye (bonus action): Darkvision 120 ft']},
  },
  'the_king_in_yellow': {
    'fx': {'u': {'senses': {'truesight': 30}}, 'notes': ['I Wear No Mask: Use for Truesight 30 ft (1 minute)', 'Advantage on saving throws against the Frightened condition']},
  },
  'candle_of_invocation': {
    'fx': {'u': {'advSaves': ['all'], 'advChecks': ['str', 'dex', 'con', 'int', 'wis', 'cha']}, 'notes': ['Use while within the lit candle\'s light: Advantage on D20 Tests']},
    'spells': [{'spellName': 'Gate', 'grantType': 'limited', 'usesMax': 1, 'recovery': 'none', 'note': 'when first lit; destroys the candle'}],
  },
  'amulet_of_the_planes': {
    'spells': [{'spellName': 'Plane Shift', 'grantType': 'atWill', 'note': 'after a DC 15 Intelligence (Arcana) check'}],
  },
  'magebane_bolas': {                                                     # no Bolas on the sheet: the item is its own weapon, shown like a save cantrip
    'fx': {'p': {'wSelf': {'key': 'magebane_bolas', 'count': 1, 'die': 4, 'type': 'bludgeoning'}, 'wAbility': 'dex',
                 'wSaveAtk': {'save': 'str', 'dcAb': 'dex', 'range': 'Thrown', 'dmg': '1d4 Bludgeoning',
                              'note': 'Large or smaller. Fail: Prone and entangled (Restrained, can\'t speak); spellcasters subtract 1d6 from this and escape saves. Escape: action, DC 12 Strength check (DC 18 vs Spellcasting or Pact Magic)'}}},
  },
  'aboleth_brain': {
    'fx': {'p': {'organicNote': 'Devouring Urge (once per turn, on a hit): +1d6 Necrotic or Psychic; you can spend a Hit Die to regain its roll + Con modifier HP (min 1); the DM gives you a mutation for 1 minute'}},
  },
  'trollblood_potion': {
    'fx': {'notes': ['When drunk: regain 5 HP at the start of each turn for 1 minute (ends on Fire or Acid damage)']},
  },
}
out = {}
for k, f in FIX.items():
    d = DM[k]
    out[k] = {'h': h(d.get('desc') or ''), 'name': d.get('name'), **f}
json.dump(out, open('/home/claude/cs/tooling/items_audit/items_dmfix.json', 'w'), indent=1, ensure_ascii=False)
print(len(out), 'DM item fixes')
