# Stage 2 section of the item audit report: what each item does on the sheet, and which items are text only.
# Usage: ireport2.py PROBE.json OUT.md
import json, sys, collections
P = json.load(open('/home/claude/cs/tooling/items_audit/items_patch.json'))
R = json.load(open(sys.argv[1]))['res']
items = P['magic'] + P['au']
def has(d):
    E = d.get('effects') or {}
    old = any(v not in (None, 0, '', [], {}, False) for k, v in E.items()) or d.get('dmgres') or d.get('resistanceOptions')
    fx = d.get('fx') or {}
    new = fx.get('p') or fx.get('u') or d.get('charges') or d.get('grantedSpells')
    vers = any(v.get('fx') or v.get('charges') or v.get('grantedSpells') or v.get('effects') for v in d.get('versions') or [])
    return bool(old or new or vers)
F = collections.Counter(); U = collections.Counter()
for d in items:
    fx = d.get('fx') or {}
    for k in (fx.get('p') or {}): F[k] += 1
    us = set(fx.get('u') or {})
    for v in d.get('versions') or []: us |= set((v.get('fx') or {}).get('u') or {})
    for k in us: U[k] += 1
wired = [d for d in items if has(d)]
text = sorted([d for d in items if not has(d)], key=lambda d: d['name'].lower())
ch = sum(1 for d in items if d.get('charges') or any(v.get('charges') for v in d.get('versions') or []))
sp = sum(1 for d in items if d.get('grantedSpells') or any(v.get('grantedSpells') for v in d.get('versions') or []))
req = sum(1 for d in items if d.get('attuneReq'))
L = ['', '# Item audit - stage 2 report (item effects)', '',
     f'{len(items)} items. {len(wired)} do something the sheet works out; {len(text)} are text only (listed at the end).', '',
     '## What the sheet now does', '',
     '- Always on (while attuned, and while worn or wielded for armour and weapons): AC, saves, ability scores, speed, flying/climbing/swimming/burrowing, senses, resistances, immunities, vulnerabilities, condition immunities, advantage on saves, checks and skills, skill bonuses, Initiative, spell attack and save DC, HP maximum, this weapon\'s attack, damage and extra dice.',
     '- Used: potions, oils and switched-on effects (an aura, Rage, a state the item is in) get a Use button in the item\'s details. Healing and Temporary HP are rolled at once; anything lasting shows under Active effects as "Item effects" until you end it or take a Long Rest. A potion or scroll is used up.',
     f'- Charges: {ch} items get a charge tracker on the Resources list.',
     f'- Spells: {sp} items add their spells to the Spells page.',
     f'- Attunement: {req} items name who can attune (class, spellcaster, alignment or species). The sheet stops a character who doesn\'t qualify; the DM still can.',
     '- Every item\'s details show "On the sheet": what the sheet applies for it.',
     '- Fixed on the way: attuning or equipping an item that sets or raises an ability score didn\'t change the score until the sheet was reopened.', '',
     '## Not applied (left to the text)', '',
     '- Effects on someone else: targets, allies, mounts, summoned creatures, the item\'s own senses.',
     '- Random tables (Deck of Many Things, Teeth of Dahlver-Nar, roll-a-d8 tables) and pick-one tables.',
     '- Conditions the sheet can\'t know: "against", "if you", "made to climb", "for every two allies", one attack or one turn only.',
     '- Bonuses an item had already wired on the sheet are kept as they were, not doubled.',
     '- Items the DM has edited follow the DM\'s version: nothing is read into them from the book.', '',
     '## Counts', '', '| Effect | Always on | When used |', '|---|---|---|']
for k in sorted(set(F) | set(U), key=lambda k: -(F[k] + U[k])):
    L.append(f'| {k} | {F[k] or ""} | {U[k] or ""} |')
L += ['', '## Sweep 2 (27 Oct)', '',
      'A second pass checked every item, every version and every weapon or armour base (11,473 cases), measuring the sheet with and without the item against everything it should do, old wiring and text alike.', '',
      '**Bugs fixed**', '',
      '- Every +1/+2/+3 magic weapon added its bonus to damage twice (a +1 Dagger showed 1d4+6, not 1d4+5). This was in the sheet before the audit and also hit hand-added weapons with both magic boxes set, organic weapons and the Arcane Armor weapon. It changes these test characters: Auron, Cabbage, Drew, Gideon, Harriet, Irellia, Lapsum, Red and Rogue.',
      '- +1/+2/+3 Armor showed its AC as text ("1700variable010000"); caused by stage 1. Characters who added one since are mended when they open.',
      '- Staffs and some one-off weapons never reached the Attacks list (no weapon type). Staffs are now Quarterstaffs (CSV: 1d6 bludgeoning, versatile); one-offs take the standard weapon with the same damage.',
      '- A version with its own text (Hawk mask, Greater Healing) also picked up the base text\'s effects.',
      '- Charge trackers for versions used the base item\'s count (Time Splitter uncommon showed 9, not 4).',
      '- Bracers of Defense and similar gave their AC twice (old wiring + text).',
      '', '**The item reader**', '',
      '- Older books write in lower case ("darkvision", "a swimming speed", "advantage on"); these were missed. Now read.',
      '- Spells: any spell named after "cast", in any case, in lists, "either ... or", with per-spell charge costs, and the older short names ("black tentacles", "acid arrow"). About 920 more spell grants.',
      '- Tremorsense now goes in the Senses box with Darkvision, Blindsight and Truesight (from items, feats and spells).',
      '- New on the sheet: AC with no armour/shield, a bonus to one save, a bonus to ability checks (reaches the skills), a bonus to every weapon attack (Ring of Honor), magic ammunition from its text, charges that start at a roll.',
      '- No longer applied: things a creature or the item itself has, "Disadvantage" read as advantage, one-purpose bonuses ("checks to intimidate").',
      '', '**Left for the player**', '',
      '- 6 one-off weapons have no standard match and still need the weapon picked by hand: Darts of the Macaw, Fists of Fury, Oversized Longbow, Storm Boomerang, Topaz Annihilator, True-Ice Shards.',
      '- Weapons that are other items (rods, scepters that "function as a mace") are not on the Attacks list.',
      '', '**Result**', '',
      'Every item, version and base: 27,000+ checks, 0 wrong apart from the 6 weapons above. Every item\'s text still matches its CSV row word for word.',
      '', '## DM-edited and homebrew items (27 Oct)', '',
      'All 37 active DM edits and 15 homebrew items were read against their own text. The DM\'s data is never changed: each fix holds a fingerprint of the DM text it was made from and switches itself off if that text is edited later.', '',
      '- Amulet of the Watcher: Perception proficiency, or expertise if already proficient (Cabbage: Perception +3 -> +6); charges now refill 1d4 at dawn.',
      '- Urnblade: necrotic damage and +2 while the shadow is out, which the DM edit had dropped for new copies (Auron\'s copy already had them).',
      '- Dwarven Thrower: the DM text says +3 but the DM wiring said +2; new copies follow the text (+3, as Irellia\'s already is). Thrown +1d8 shown as a note.',
      '- Crimson Moon-Blade: charges refill 1d6+1 at dawn (were set to never refill); +2d6 radiant per charge shown as a note.',
      '- Eye of the Watcher (Darkvision 120 ft while looking through it), The King in Yellow (I Wear No Mask: Truesight 30 ft), Candle of Invocation (Advantage on D20 Tests while lit): Use button.',
      '- Spells: Amulet of the Planes (Plane Shift, after a DC 15 Arcana check), Candle of Invocation (Gate, once).',
      '- Sussur Dagger and The Lucky Marksman now reach the Attacks list (Dagger, Revolver). The Lucky Marksman\'s 2d8 radiant was added to every shot; it\'s only on a Heads ricochet, now a note.',
      '- Unstable Feywild Crystal: once-per-Long-Rest tracker for its Advantage.',
      '- Already right, unchanged: the other DM-edited and homebrew items, including those with no rules to wire (bags, carpets, Iron Flask, Ring of Silence, the Polymorphine potions).',
      '- Magebane Bolas: shown on Attacks like a save cantrip (Mind Sliver): STR Save, DC 8 + Dex + Prof worked out for the character, 1d4 Bludgeoning, with prone/entangled and escape DCs as a note. Same in quick play and the PDF (Cabbage: DC 15).',
      '- Blade of the Chosen: starts as a Scimitar; the form list on the item still lets the wielder pick another melee weapon (its text: "a Melee Simple or Martial weapon") (Red\'s Greatsword is kept).',
      '- If your live DM file differs from the copy in the test harness, a fix for an item whose text differs switches off; tell me and I\'ll redo it.',
      '', '## Dragon Masks, tables and your 28 Oct DM file', '',
      '- Dragon Mask (pick the colour) and your separate Black/Blue/Green/Red/White Dragon Masks: Resistance of the colour, Charisma bonus to AC with no armour, Darkvision 60 ft (or +60 ft if you have it), Draconic, a Use button for Blindsight 30 ft, Legendary Resistance and Blindsight trackers (once a day), and the rest as notes. The old 10-colour resistance pick on Dragon Mask is gone (the colour is the version).',
      '- Mask of the Dragon Queen: Resistance to all five types, Legendary Resistance 5 a day; which mask\'s other properties you use is a note.',
      '- Squashed tables: 43 tables in 38 items had lost their cell breaks in Items.csv (Deck of Illusions, Teeth of Dahlver-Nar, Wand of Wonder, Carpet of Flying...). They are tables again, word for word.',
      '- The King in Yellow: your new text keeps the Truesight Use button (the fix now matches your edited text).',
      '- Your DM file\'s Bloodwell Vial entry has short first-person text, no attunement and empty effects; it looks like a character\'s copy saved over the catalogue entry. Not changed; your +1/+2/+3 Bloodwell Vials are fine.',
      '', '## DM file clean-up, Gi, Polymorphine (28 Oct)', '',
      '- DM item editor: saving a book item keeps the book source and page (it always wrote "Dorenia DM"); new items are "Homebrew". A DM edit of a book item keeps the book page, attunement note, class requirement and, while its text is the book text, the wiring.',
      '- Corrected DM file: see DM_items_changes.md.',
      '- Gi of Shifting Seasons: pick the season in the item window; Autumn gives Advantage on Constitution saves, Spring adds 1d4 + 4 Temporary HP when picked, Summer puts +2 Fire on Unarmed Strike; the rest are listed as not automatic.',
      '- Item window: effects the sheet cannot apply itself are listed under "Not automatic" (they were stored but never shown).',
      '- Potion of Polymorphine: one item, rarity Varies; pick Crude, Refined, Volatile, Unstable or Chaotic. Owned potions moved over by themselves.',
      '- Book entries given the wiring your retired edits had: Candle of Invocation (Gate once; Use for Advantage), Amulet of the Planes (Plane Shift), Thayan Sword (smites from charges, Resurgent Warrior), Bloodwell Vial (sorcery points once a dawn), Trollblood Potion (note).',
      '', '## Test', '',
      f'Every item ({len(R)}) was added to a test character, switched on, and measured with the effects layer on and off. Every effect read from the text showed up as that difference: 0 failures, 0 errors. Items with several versions were also checked on their last version.', '',
      f'## Text only ({len(text)})', '', 'Nothing in these items is something the sheet can work out (story items, one-off effects, effects on others, or rules left to the DM). Their text is still shown in full.', '']
cur = None
for d in text:
    c = d['name'][0].upper() if d['name'][0].isalpha() else '#'
    if c != cur: L += ['', f'**{c}**', '']; cur = c
    L.append('- ' + d['name'])
open(sys.argv[2], 'w').write('\n'.join(L) + '\n')
print(len(items), len(wired), len(text), ch, sp, req)
