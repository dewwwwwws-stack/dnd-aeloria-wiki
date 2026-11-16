import re
# Hand-made cell boundaries for tables the CSV squashed together. Each spec: the start of the squashed
# paragraph ('m'), the number of columns, the text where each cell starts (header first, in order),
# an optional caption (text before the header) and where the text after the table begins ('end').
# The cells are cut from the CSV text itself, so the words stay 1:1.
DMG4 = ['Acid', 'Cold', 'Fire', 'Lightning', 'Poison', 'Psychic', 'Radiant', 'Thunder']
def rows(*cells): return list(cells)
SPECS = [
 dict(m='ColorDamage TypeRedFireYellow', cols=2, a=['Color', 'Damage Type', 'Red', 'Fire', 'Yellow', 'Lightning', 'Green', 'Poison', 'Blue', 'Cold'], end='Range. A Range'),
 dict(m='d6Light ColorDamage Type1-2', cols=3, a=['d6', 'Light Color', 'Damage Type', '1-2', 'Blue or Purple', 'Cold', '3-4', 'Red or Orange', 'Fire', '5-6', 'Yellow or Green', 'Lightning']),
 dict(m='Damage TypeEffectColdThe target', cols=2, a=['Damage Type', 'Effect', 'Cold', "The target's speed is halved", 'Fire', 'The target takes an extra 6', 'Lightning', "The target can't take reactions", 'Radiant', 'The next attack roll'], end='Heavy. Creatures'),
 dict(m='Ammunition MetalAreaDamage', cols=3, a=['Ammunition Metal', 'Area', 'Damage Type', 'Brass', '60-foot line', 'Fire', 'Bronze', '90-foot line', 'Lightning', 'Copper', '60-foot line', 'Acid', 'Gold', '60-foot cone', 'Fire', 'Silver', '60-foot cone', 'Cold']),
 dict(m='Terrain TypeDamage TypeArctic', cols=2, a=['Terrain Type', 'Damage Type', 'Arctic or Underwater', 'Cold', 'Coast', 'Lightning', 'Desert', 'Fire', 'Forest', 'Poison', 'Grassland', 'Radiant', 'Hill or Mountain', 'Thunder', 'Swamp', 'Acid', 'Underground', 'Necrotic', 'Urban', 'Psychic'], end='Heavy. Creatures'),
 dict(m='1d6ColorDamage Type1RedFire', cols=3, a=['1d6', 'Color', 'Damage Type', '1', 'Red', 'Fire', '2', 'Orange', 'Acid', '3', 'Yellow', 'Lightning', '4', 'Green', 'Poison', '5', 'Blue', 'Cold', '6', 'Special', 'The creature is struck'], end='Thrown. If'),
 dict(m='d4Light ColorDamageType/Effect', cols=4, a=['d4', 'Light Color', 'Damage', 'Type/Effect', '1', 'Blue', 'Cold', 'Until the end', '2', 'Green', 'Poison', 'The target has disadvantage', '3', 'Orange', 'Acid', "The target's AC", '4', 'Red', 'Fire', 'The target immediately']),
 dict(m='Rod PiecesPieceSpellFirst', cols=2, cap='Rod Pieces', a=['Piece', 'Spell', 'First', 'Commune', 'Second', 'Arcane Gate', 'Third', 'Reverse Gravity', 'Fourth', 'Regenerate', 'Fifth', 'Find the Path', 'Sixth', 'Mirage Arcane', 'Seventh', 'Simulacrum'], end='Possessing the Whole Rod'),
 dict(m='AlignmentAppearanceLightDamage', cols=4, a=['Alignment', 'Appearance', 'Light', 'Damage Type', 'Good', 'A shimmering', 'Yellow', 'Radiant', 'Neutral', 'A blade of reflective', 'Purple', 'Force', 'Evil', 'A dark, serrated', 'Green', 'Necrotic'], end='A target hit by'),
 dict(m='Call LightningDivine WordFinger', cols=0, a=['Call Lightning', 'Divine Word', 'Finger of Death'], end='Once you use the sword'),
 dict(m='1d10The Weapon Transforms', cols=2, a=['1d10', 'The Weapon Transforms into a...', '1', 'Bracelet', '2', 'Comb', '3', 'Crutch', '4', 'Fake coin', '5', 'Hairpin', '6', 'Jingle bell', '7', 'Pendant necklace', '8', 'Playing card', '9', 'Quill pen', '10', 'Spoon']),
 dict(m='DragonResistanceBlackAcid', cols=2, a=['Dragon', 'Resistance', 'Black', 'Acid', 'Blue', 'Lightning', 'Brass', 'Fire', 'Bronze', 'Lightning', 'Copper', 'Acid', 'Gold', 'Fire', 'Green', 'Poison', 'Red', 'Fire', 'Silver', 'Cold', 'White', 'Cold'], end=['Range. A weapon', 'In addition, when']),
 dict(m='LiquidMax AmountBeer4 gallonsBoiling', cols=2, a=['Liquid', 'Max Amount', 'Beer', '4 gallons', 'Boiling Hot Tea', '1 quart', 'Honey', '1 gallon', 'Mayonnaise', '2 gallons', 'Oil', '1 quart', 'Vinegar', '2 gallons', 'Water, fresh', '8 gallons', 'Water, salt', '12 gallons', 'Wine', '1 gallon']),
 dict(m='LiquidMax AmountBeer4 gallonsHoney', cols=2, a=['Liquid', 'Max Amount', 'Beer', '4 gallons', 'Honey', '1 gallon', 'Mayonnaise', '2 gallons', 'Oil', '1 quart', 'Soy Sauce', '1 gallon', 'Vinegar', '2 gallons', 'Water, fresh', '8 gallons', 'Water, salt', '12 gallons', 'Wine', '1 gallon']),
 dict(m='1d100Effect015d4 toadstools', cols=2, a=['1d100', 'Effect', '01', '5d4 toadstools', '02-10', 'A geyser', '11-20', 'A Treant', '21-30', 'An animate', '31-40', 'A campfire', '41-50', 'Three Shrieker', '51-60', '1d4 + 4 bright-pink', '61-70', 'A hungry', '71-80', 'A fruit tree', '81-90', 'A nest of', '91-95', 'A pyramid', '96-00', 'A giant beanstalk']),
 dict(m='d6Block ShapeDimensions1Cylinder', cols=3, a=['d6', 'Block Shape', 'Dimensions', '1', 'Cylinder, long', '2 in. diameter, 8', '2', 'Cylinder, short', '2 in. diameter, 1', '3', 'Plank, long', '1 in. wide, ¼ in. tall, 8', '4', 'Plank, short', '1 in. wide, ¼ in. tall, 2', '5', 'Square', '1 in. tall, 8 in.', '6', 'Triangle', '3 in. on a side'], end='You can assemble'),
 dict(m='PatternAppearanceBenefitArctic', cols=3, a=['Pattern', 'Appearance', 'Benefit', 'Arctic', 'All white', 'Difficult terrain', 'Jungle', 'Orange and white', 'You gain a +3', 'Mountain', 'A mix of brown', 'You gain a climbing', 'Savannah', 'Dull yellow', 'You can move an extra']),
 dict(m='d4Color (Smell Name)Rare Effect', cols=3, a=['d4', 'Color (Smell Name)', 'Rare Effect', '1', 'Red (Goodberry)', 'You gain 2d8', '2', 'Yellow (Solaris Orchid)', 'You have advantage', '3', "Green (Dryad's Glen)", "You can't become", '4', 'Blue (Ashen Blue)', 'You lose one level']),
 dict(m='RarityRangeSave DCCumulative', cols=4, a=['Rarity', 'Range', 'Save DC', 'Cumulative Effects', 'Uncommon', '15 ft.', '13', 'Not Applicable', 'Rare', '20 ft.', '15', 'If the creature is on the Ethereal', 'Very rare', '25 ft.', '16', "If the creature's challenge", 'Legendary', '30 ft.', '17', 'The creature is turned']),
 dict(m='RarityChargesMaximum Spell Level', cols=3, a=['Rarity', 'Charges', 'Maximum Spell Level', 'Uncommon', '3', '1', 'Rare', '7', '4', 'Very Rare', '10', '7'], end='Lastly, when you cast'),
 dict(m='Damage TypeEffectAcidThe creature', cols=2, a=['Damage Type', 'Effect', 'Acid', 'The creature must succeed on a Constitution saving throw or take half', 'Cold', "The creature's speed", 'Fire', 'Each other creature', 'Lightning', "The creature can't make", 'Poison', 'The creature must succeed on a Constitution saving throw or be poisoned', 'Thunder', 'For each matching']),
 dict(m='LayerColorDamage typeCoruscating', cols=3, a=['Layer', 'Color', 'Damage type', 'Coruscating', 'Orange', 'Lightning', 'Corrosive', 'Green', 'Acid', 'Frozen', 'Blue', 'Cold', 'Rotting', 'Gray', 'Necrotic', 'Sickly', 'Purple', 'Poison'], end='While wearing the cloak'),
 dict(m='SeasonColorDamage TypeWinter', cols=3, a=['Season', 'Color', 'Damage Type', 'Winter', 'Blue', 'Cold', 'Spring', 'Green', 'Radiant', 'Summer', 'Gold', 'Fire', 'Autumn', 'Orange', 'Necrotic']),
 dict(m='LensesLens ColorSpellFuel Cost', cols=3, cap='Lenses', a=['Lens Color', 'Spell', 'Fuel Cost', 'Amethyst', 'Reverse Gravity', '3,000 gp', 'Diamond', 'Disintegrate', '2,000 gp', 'Emerald', 'Haste', '500 gp', 'Jacinth', 'Flame Strike', '1,000 gp', 'Ruby', 'Hold Monster', '1,000 gp', 'Sapphire', 'Fear', '500 gp', 'Topaz', 'Slow', '500 gp', 'Any four colors', 'Prismatic Wall', '5,000 gp'], end='Destroying the Lantern'),
 dict(m='d8SuitDragonDamage Type1-2Clubs', cols=4, a=['d8', 'Suit', 'Dragon', 'Damage Type', '1-2', 'Clubs', 'Black', 'Acid', '3-4', 'Diamonds', 'Red', 'Fire', '5-6', 'Hearts', 'Bronze', 'Lightning', '7-8', 'Spades', 'Silver', 'Cold'], end='A thrown card'),
 dict(m='SpellCharge CostMagic Circle1', cols=2, a=['Spell', 'Charge Cost', 'Magic Circle', '1', 'Magic Jar', '3', 'Planar Ally', '3', 'Planar Binding', '2', 'Plane Shift (to the Abyss only)', '3', 'Summon Fiend', '3', "Tasha's Hideous Laughter", '0'], end='Destroying the Demonomicon'),
 dict(m='d6SceneCastDroppedShaken', cols=7, a=['d6', 'Scene', 'Cast', 'Dropped', 'Shaken', 'Spun', 'Placed',
     '1', 'Marsh', 'Loud wildlife', 'Heavy rainfall', 'A hunting party', 'A whirpool', 'Quiet and still',
     '2', 'Library', 'Silence', 'Disturbed dust', 'Strewen books', 'Toppeled bookshelves', 'Candelit reading nook',
     '3', 'Cave', 'Tumbling boulders', 'Dripping water', 'Caved in', 'Shimmering, glowing crystals', 'Empty with quiet echos',
     '4', 'Tavern', 'A singing bard', 'Filthy, wet floors', 'Patrons dancing', 'A druken brawl', 'A person drinking alone',
     '5', 'Forest', 'Singing birds', 'Large wildlife', 'Falling leaves', "Floating will-o'-wisps", 'A windstill meadow',
     '6', 'Castle', 'Throne room', 'Under siege', 'In ruins or disrepair', 'A gold-strewn royal treasury', 'A small castle on a hill']),
 dict(m='d12effect1-2The dodecahedron', cols=2, a=['d12', 'effect', '1-2', 'The dodecahedron explodes', '3-4', 'The dodecahedron casts light', '5-6', 'The dodecahedron casts ray', '7-8', 'The dodecahedron casts shocking', '9-10', 'The dodecahedron casts darkness', '11-12', 'The next creature']),
 dict(m='MetalDamage TypeBrassFireBronze', cols=2, a=['Metal', 'Damage Type', 'Brass', 'Fire', 'Bronze', 'Lightning', 'Copper', 'Acid', 'Gold', 'Fire', 'Silver', 'Cold']),
 dict(m='Dragon AgeBonus DamageRarity', cols=3, a=['Dragon Age', 'Bonus Damage', 'Rarity', 'Wyrmling', '+1d4', 'Uncommon', 'Young', '+2d4', 'Rare', 'Adult', '+3d4', 'Very Rare', 'Ancient', '+4d4', 'Legendary'],
      then=dict(cols=2, a=['Dragon', 'Bonus Damage Type', 'Black', 'Acid', 'Blue', 'Lightning', 'Brass', 'Fire', 'Bronze', 'Lightning', 'Copper', 'Acid', 'Gold', 'Fire', 'Green', 'Poison', 'Red', 'Fire', 'Silver', 'Cold', 'White', 'Cold'])),
 dict(m='d20Volume TitleFavored Enemy', cols=4, a=['d20', 'Volume Title', 'Favored Enemy and Language', 'Wild Shape Option (Costs 2 Uses)',
     '1', 'Aberration:', 'Aberrations;', 'Gibbering Mouther', '2', 'Beast:', 'Beasts;', 'Giant Scorpion', '3', 'Celestial:', 'Celestials;', 'Pegasus',
     '4', 'Constructs:', 'Constructs;', 'Rug of Smothering', '5', 'Dragon:', 'Dragons;', 'Gold Dragon Wyrmling', '6', 'Elemental:', 'Elementals;', 'Gargoyle',
     '7', 'Fey:', 'Fey;', 'Dryad', '8', 'Fiend:', 'Fiends;', 'Hell Hound', '9', 'Giant:', 'Giants;', 'Ogre', '10', 'Humanoid:', 'Humanoids (any', 'You cast the alter self',
     '11', 'Monstrosity:', 'Monstrosities;', 'Owlbear', '12', 'Ooze:', 'Oozes;', 'Ochre Jelly', '13', 'Plant:', 'Plants;', 'Awakened Tree', '14', 'Undead:', 'Undead;', 'Minotaur Skeleton',
     '15-19', 'Roll again', '-', '-', '20', 'Roll two d20s', '-', '-'], end='Once you gain the book'),
 dict(m='1d8ColorEffect1RedReleases', cols=3, a=['1d8', 'Color', 'Effect', '1', 'Red', 'Releases a harmless', '2', 'Orange', 'Releases a small flash', '3', 'Yellow', 'Releases small spiraling', '4', 'Green', 'Releases a cloud', '5', 'Blue', 'Releases a series', '6', 'Purple', 'Releases the sound', '7', 'White', 'Releases a dazzling', '8', 'Black', 'Releases a mystery']),
 dict(m='1d8ColorEffect1WhiteYou can', cols=3, a=['1d8', 'Color', 'Effect', '1', 'White', 'You can breathe', '2', 'Black', 'You have Resistance to Acid', '3', 'Blue', 'Whenever you successfully', '4', 'Gray', 'You have Advantage on saving', '5', 'Gold', 'You gain a Climb', '6', 'Red', 'You gain 1d8', '7', 'Green', 'You have Resistance to Poison', '8', 'Yellow', 'You have Resistance to Lightning']),
 dict(m='d20 & Décor Amount', cols=2, a=['d20 & Décor Amount (Less-More)', 'Celebration Type (Choose Two)', '1', 'Generic', '2', 'Historical Event', '3', 'Astrological', '4', 'Equinox or Solstice', '5', 'Winter', '6', 'Spring', '7', 'Summer', '8', 'Autumn', '9', 'Harvest', '10', 'New Year', '11', 'Birthday', '12', 'Life Event', '13', 'Wedding', '14', 'Accomplishment', '15', 'Mourning', '16', 'Religious', '17', 'Spiritualism', '18', 'Food', '19', 'Gala', '20', 'Other']),
 dict(m='EmotionColorAngerRed', cols=2, a=['Emotion', 'Color', 'Anger', 'Red', 'Anticipation', 'Orange', 'Joy', 'Yellow', 'Love', 'Lime Green', 'Fear', 'Green', 'Sadness', 'Navy Blue', 'Disappointment', 'Indigo', 'Disgust', 'Violet', 'Jealousy', 'Black', 'Surprise', 'White']),
 dict(m='GodSpellAthreos', cols=2, a=['God', 'Spell', 'Athreos', 'protection from evil', 'Ephara', 'sanctuary', 'Erebos', 'inflict wounds', 'Heliod', 'guiding bolt', 'Iroas', 'heroism', 'Karametra', 'goodberry', 'Keranos', 'thunderous smite', 'Klothys', 'entangle', 'Kruphix', 'dissonant whispers', 'Mogis', 'hellish rebuke', 'Nylea', 'faerie fire', 'Pharika', 'lesser restoration', 'Phenax', 'charm person', 'Purphoros', 'searing smite', 'Thassa', 'identify']),
 dict(m='1d100Horn TypeSpiritsRequirement', cols=4, a=['1d100', 'Horn Type', 'Spirits', 'Requirement', '01-40', 'Silver', '2', 'None', '41-75', 'Brass', '3', 'Proficiency with all Simple', '76-90', 'Bronze', '4', 'Training with', '91-00', 'Iron', '5', 'Proficiency with all Martial']),
 dict(m='d20GolemTimeCost1-5', cols=4, a=['d20', 'Golem', 'Time', 'Cost', '1-5', 'Manual of Clay', '30 days', '65,000 GP', '6-17', 'Manual of Flesh', '60 days', '50,000 GP', '18', 'Manual of Iron', '120 days', '100,000 GP', '19-20', 'Manual of Stone', '90 days', '80,000 GP'], end='To create a golem'),
 dict(m='Potion NameSuccess Threshold', cols=2, a=['Potion Name', 'Success Threshold', 'Oil of Slipperiness', '80', 'Potion of Clairvoyance', '70', 'Potion of Climbing', '95', 'Potion of Diminution', '60', 'Potion of Flying', '50', 'Potion of Giant Strength', '75 (Hill', 'Potion of Growth', '40', 'Potion of Healing', '95 (Healing)', 'Potion of Mind Reading', '70', 'Potion of Poison', '80', 'Potion of Resistance', '95 (any', 'Potion of Water Breathing', '95'], end="Once you've named"),
 dict(m='d8CharmSummoned Creatures', cols=3, a=['d8', 'Charm', 'Summoned Creatures', '1', 'Monkey', '4 baboons', '2', 'Bear', '2 black bears', '3', 'Boar', '4 boars', '4', 'Deer (stag)', '4 deer', '5', 'Frog', '4 frogs', '6', 'Panther', '4 panthers', '7', 'Ram', '4 goats', '8', 'Wolf', '4 wolf']),
 dict(m='d8SpellExtra Spell1Slow', cols=3, a=['d8', 'Spell', 'Extra Spell', '1', 'Slow;', 'Rope trick', '2', 'Call lightning', 'Bane', '3', 'Hypnotic pattern', 'Bless', '4', 'Spirit guardians', 'Disguise self', '5', 'Dimension door', 'Magic missile', '6', 'Fireball', 'Invisibility', '7', 'Ice storm', 'Flaming sphere', '8', 'Haste;', 'Pass without trace'], end='You can cast a spell from the scroll'),
 dict(m='ColorDamage ResistanceRedFire', cols=2, a=['Color', 'Damage Resistance', 'Red', 'Fire', 'Orange', 'Acid', 'Yellow', 'Lightning', 'Green', 'Poison', 'Blue', 'Cold', 'Indigo', 'Thunder', 'Violet', 'Psychic', 'Black', 'Necrotic', 'White', 'Radiant'], end=['Crystal Binding', 'Crystal Blast', 'Crystal ']),
 dict(m='1d20BeadSpell1-6', cols=3, a=['1d20', 'Bead', 'Spell', '1-6', 'Bead of Blessing', 'Bless', '7-12', 'Bead of Curing', 'Cure Wounds', '13-16', 'Bead of Favor', 'Greater Restoration', '17-18', 'Bead of Smiting', 'Shining Smite', '19', 'Bead of Summons', 'Guardian of Faith', '20', 'Bead of Wind Walking', 'Wind Walk']),
 dict(m='SpellCharge CostDisguise Self0', cols=2, a=['Spell', 'Charge Cost', 'Disguise Self', '0', 'Fire Shield', '2', 'Hold Person', '1', 'See Invisibility', '1', 'Summon Dragon (level 9 version)', '4'], end='Dragon Transformation'),
 dict(m='SpellCharge CostCure Wounds (level 9', cols=2, a=['Spell', 'Charge Cost', 'Cure Wounds (level 9 version)', '4', 'Daylight', '1', 'Death Ward', '2', 'Detect Magic', '0', 'Scrying (save DC 18)', '3'], end='Call Dragons'),
 dict(m='RaritySave DCMax CRUncommon', cols=3, a=['Rarity', 'Save DC', 'Max CR', 'Uncommon', '13', '2', 'Rare', '15', '6', 'Very rare', '16', '13', 'Legendary', '17', '-'], end='You can use an action to hold'),
 dict(m='ConnectionSave ModifierLikeness', cols=2, a=['Connection', 'Save Modifier', 'Likeness or picture', '–2', 'Possession or garment', '–4', 'Body part', '–8']),
 dict(m='RarityDamageSave DCUncommon2d10', cols=3, a=['Rarity', 'Damage', 'Save DC', 'Uncommon', '2d10', '13', 'Rare', '3d10', '15', 'Very Rare', '4d10', '16'], end='When crafting a Potion'),
 dict(m='d4AppearanceMephit1Beige', cols=3, a=['d4', 'Appearance', 'Mephit', '1', 'Beige stone', 'Dust Mephit', '2', 'Glass with swirls of soft', 'Ice Mephit', '3', 'Obsidian glass', 'Magma Mephit', '4', 'Glass with watery', 'Steam Mephit'], end='You can use an action to throw'),
 dict(m='ColorDamage TypeRedFireOrangeAcid', cols=2, a=['Color', 'Damage Type', 'Red', 'Fire', 'Orange', 'Acid', 'Yellow', 'Lightning', 'Green', 'Poison', 'Blue', 'Cold', 'Purple', 'Necrotic', 'White', 'Radiant']),
 dict(m='d10Damage TypeGem1AcidPearl', cols=3, a=['d10', 'Damage Type', 'Gem', '1', 'Acid', 'Pearl', '2', 'Cold', 'Tourmaline', '3', 'Fire', 'Garnet', '4', 'Force', 'Sapphire', '5', 'Lightning', 'Citrine', '6', 'Necrotic', 'Jet', '7', 'Poison', 'Amethyst', '8', 'Psychic', 'Jade', '9', 'Radiant', 'Topaz', '10', 'Thunder', 'Spinel']),
 dict(m='1d100Patch01-08Bag', cols=2, a=['1d100', 'Patch', '01-08', 'Bag of 100', '09-15', 'Silver coffer', '16-22', 'Iron door', '23-30', '10 gems', '31-44', 'Wooden ladder', '45-51', 'Riding Horse', '52-59', 'Open pit', '60-68', '4 Potions', '69-75', 'Rowboat', '76-83', 'Spell Scroll', '84-90', '2 Mastiffs', '91-96', 'Window', '97-00', 'Portable Ram']),
 dict(m='d10Beam ColorAdditional Effect', cols=3, a=['d10', 'Beam Color', 'Additional Effect', '1', 'Red', 'The target must succeed on a Wisdom saving throw or be charmed', '2', 'Orange', 'The target must succeed on a Constitution', '3', 'Yellow', 'The target must succeed on a Wisdom saving throw or be frightened', '4', 'Green', 'The target must succeed on a Strength', '5', 'Cyan', 'The target must succeed on a Dexterity saving throw or have', '6', 'Blue', 'The target must succeed on a Wisdom saving throw or fall', '7', 'Indigo', 'The target must succeed on a Dexterity saving throw or become', '8', 'Violet', 'The target must make a Dexterity saving throw, taking an extra 4d6', '9', 'Indigo', 'The target must make a Dexterity saving throw, taking an extra 6d6', '10', 'Black', 'The target must make a Dexterity saving throw, taking an extra 8d6'], end='Alternatively, you can expend'),
 dict(m='d6CommonRare1Nothing', cols=3, a=['d6', 'Common', 'Rare', '1', 'Nothing happens.', 'Nothing happens.', '2', 'Your eyes become', 'You have blindsight', '3', 'Your tongue becomes', 'You have advantage', '4', 'Your skin becomes', 'You have resistance', '5', 'Your footsteps', 'You gain the benefits', '6', "Whenever you make an 'S' sound", 'You grow snakelike']),
 dict(m='SpellCharge CostAugury1Commune3', cols=2, a=['Spell', 'Charge Cost', 'Augury', '1', 'Commune', '3']),
 dict(m='Censer SpellsSpellCharge Cost', cols=2, cap='Censer Spells', a=['Spell', 'Charge Cost', 'Banishment', '4', 'Bless', '1', 'Circle of Power', '5', 'Dispel Magic', '3', 'Remove Curse', '3'], end='Protective Incense'),
 dict(m='SpellCharge CostBurning Hands1', cols=2, a=['Spell', 'Charge Cost', 'Burning Hands', '1', 'Fireball', '3', 'Wall of Fire', '4'], end='Regaining Charges'),
 dict(m='SpellCharge CostCone of Cold5Fog', cols=2, a=['Spell', 'Charge Cost', 'Cone of Cold', '5', 'Fog Cloud', '1', 'Ice Storm', '4', 'Wall of Ice', '4'], end='Regaining Charges'),
 dict(m='SpellCharge CostCure Wounds1 charge', cols=2, a=['Spell', 'Charge Cost', 'Cure Wounds', '1 charge per spell level', 'Lesser Restoration', '2', 'Mass Cure Wounds', '5'], end='Regaining Charges'),
 dict(m='SpellCharge CostCone of Cold5Fireball', cols=2, a=['Spell', 'Charge Cost', 'Cone of Cold', '5', 'Fireball (level 5 version)', '5', 'Globe of Invulnerability', '6', 'Hold Monster', '5', 'Levitate', '2', 'Lightning Bolt (level 5 version)', '5', 'Magic Missile', '1', 'Ray of Enfeeblement', '1', 'Wall of Force', '5'], end='Regaining Charges'),
 dict(m='SpellCharge CostGiant Insect4', cols=2, a=['Spell', 'Charge Cost', 'Giant Insect', '4', 'Insect Plague', '5'], end='Regaining Charges'),
 dict(m='SpellCharge CostArcane Lock0', cols=2, a=['Spell', 'Charge Cost', 'Arcane Lock', '0', 'Conjure Elemental', '7', 'Detect Magic', '0', 'Dispel Magic', '3', 'Enlarge/Reduce', '0', 'Fireball (level 7 version)', '7', 'Flaming Sphere', '2', 'Ice Storm', '4', 'Invisibility', '2', 'Knock', '2', 'Light', '0', 'Lightning Bolt (level 7 version)', '7', 'Mage Hand', '0', 'Passwall', '5', 'Plane Shift', '7', 'Protection from Evil and Good', '0', 'Telekinesis', '5', 'Wall of Fire', '4', 'Web', '2'], end='Regaining Charges'),
 dict(m='SpellCharge CostAnimal Friendship1', cols=2, a=['Spell', 'Charge Cost', 'Animal Friendship', '1', 'Awaken', '5', 'Barkskin', '2', 'Locate Animals or Plants', '2', 'Pass without Trace', '2', 'Speak with Animals', '1', 'Speak with Plants', '3', 'Wall of Thorns', '6'], end='Tree Form'),
 dict(m='WeightDistance TeleportedUp to 1', cols=2, a=['Weight', 'Distance Teleported', 'Up to 1 pound', 'Up to 10 miles', '1–2 pounds', 'Up to 25 miles', '3–5 pounds', 'Up to 50 miles', '6–10 pounds', 'Up to 100 miles', '11–15 pounds', '—', '16–25 pounds', '—'], end='You can halve'),
 dict(m='d4NameBenefit1Acrobatic', cols=3, a=['d4', 'Name', 'Benefit', '1', 'Acrobatic', 'Until the end of your turn, you can jump', '2', 'Evasive', 'You take the Dash', '3', 'Tricky', 'You can immediately', '4', 'Choose', 'You choose which']),
 dict(m='SpellCharge CostHold Monster5Hold', cols=2, a=['Spell', 'Charge Cost', 'Hold Monster', '5', 'Hold Person', '2'], end='Regaining Charges'),
 dict(m='SpellCharge CostCommand', cols=2, a=['Spell', 'Charge Cost', 'Command ("flee" or "grovel" only)', '1', 'Fear (60-foot Cone)', '3'], end='Regaining Charges'),
 dict(m='2d6Effect2Slither', cols=2, a=['2d6', 'Effect', '2', 'Slither.', '3', 'Nullify.', '4', 'Slick.', '5', 'Misty.', '6', 'Jelly.', '7', 'Lucky.', '8', 'Bramble.', '9', 'Alarm.', '10', 'Revelry.', '11', 'Zap.', '12', 'Explode.']),
 dict(m='d12Item Name1potion', cols=3, a=['d12', 'Item Name', '', '1', 'potion of climbing', '25gp', '2', 'potion of healing, common', '25gp', '3', 'spell scroll, 1st level', '25gp', '4', 'broom of flying', '50gp', '5', 'dust of disappearance', '50gp', '6', 'eversmoking bottle', '50gp', '7', 'goggles of night', '50gp', '8', 'immovable rod', '50gp', '9', 'potion of growth', '50gp', '10', 'potion of resistance', '50gp', '11', 'restorative ointment, 2 uses', '50gp', '12', 'ring of water walking', '50gp'], end='While the toy is animated'),
 dict(m="d8ElementTrumpsWizards' Bout", cols=4, a=['d8', 'Element', 'Trumps', "Wizards' Bout Effect", '1', 'Radiant', 'Thunder, Poison', 'Roll another d8', '2', 'Nature', 'Earth, Radiant', 'You gain 2 points', '3', 'Earth', 'Air, Thunder', 'The opposing player loses 1 point. The next', '4', 'Water', 'Fire, Earth', 'The opposing player loses 1 point, or 3', '5', 'Poison', 'Water, Nature', 'The opposing player loses 1 point if', '6', 'Thunder', 'Air, Water', 'The opposing player loses 1 point, or 2', '7', 'Fire', 'Nature', 'The opposing player loses 2 points', '8', 'Air', 'Poison, Fire', 'The opposing player immediately']),
 dict(m='Chromatic RosesColorVisual Effect', cols=3, cap='Chromatic Roses', a=['Color', 'Visual Effect', 'Damage Type', 'Black', 'Drips acid', 'Acid', 'Blue', 'Crackles with lightning', 'Lightning', 'Green', 'Issues green gas', 'Poison', 'Red', 'Wreathed in fire', 'Fire', 'White', 'Covered in frost', 'Cold']),
 dict(m='Shard SolitaireSpellsAll', cols=2, a=['Shard Solitaire', 'Spells', 'All', 'Banishment (3 charges', 'Black sapphire', 'Blight', 'Diamond', 'Ice storm', 'Jacinth', 'Fireball (2', 'Rainbow pearl', 'Prismatic spray', 'Ruby', 'Fly (2']),
 dict(m='ColorDamage TypeBlackAcidBlue', cols=2, a=['Color', 'Damage Type', 'Black', 'Acid', 'Blue', 'Lightning', 'Green', 'Poison', 'Red', 'Fire', 'White', 'Cold']),
 dict(m='Delerium CrystalsCrystal Size', cols=6, cap='Delerium Crystals', a=['Crystal Size', 'Market Value', 'Weight', 'AC', 'HP', 'Extraction Time',
     'Chip', '10 gold', '1/4 lbs', '15', '5', '1 action', 'Fragment', '100 gold', '1/2 lbs', '17', '10', '1 minute',
     'Shard', '500 gold', '1 lbs', '19', '15', '5 minutes', 'Crystal', '1,000 gold', '2 lbs', '21', '20', '30 minutes',
     'Geode', '5,000 gold', '20 lbs +', '23', '25', '1 hour', 'Massive Cluster', 'Priceless', '8,000 lbs +', '25', '50', '7 days'], end='Delerium Properties'),
]


def _cut(text, spec, pos=0):
    """-> (table markdown, index where the table ends) or raises ValueError"""
    cols, anchors = spec['cols'], spec['a']
    starts = []
    for n, a in enumerate(anchors):
        if a == '':
            starts.append((pos, 0)); continue
        nxt_a = next((x for x in anchors[n + 1:n + 2] if x), None)
        i = text.find(a, pos)
        # the next cell must follow straight after this one's text (stops "2" matching inside "20 feet")
        while i >= 0 and nxt_a and re.fullmatch(r'[0-9]+(?:[-–][0-9]+)?', a) and not text[i + len(a):].lstrip().startswith(nxt_a):
            i = text.find(a, i + 1)
        if i < 0: raise ValueError('cell not found: %r after %r' % (a, text[pos:pos + 40]))
        if starts and i == starts[-1][0] and starts[-1][1] > 0: raise ValueError('empty cell before %r' % a)
        starts.append((i, len(a))); pos = i + len(a)
    end = len(text)
    ends = spec.get('end')
    if ends:
        for e in ([ends] if isinstance(ends, str) else ends):
            j = text.find(e, pos)
            if j >= 0: end = j; break
        else: raise ValueError('end not found %r' % ends)
    if 'then' in spec:
        j = text.find(spec['then']['a'][0], pos)
        end = min(end, j)
    cells = []
    for k, (i, ln) in enumerate(starts):
        if ln == 0: cells.append(''); continue
        nxt = next((st for st, l2 in starts[k + 1:] if l2 > 0 or True), None)
        nxt = starts[k + 1][0] if k + 1 < len(starts) else end
        c = text[i:nxt].strip()
        if not c: raise ValueError('empty cell at %r' % text[i:i + 30])
        cells.append(c.replace('|', '/'))
    if cols == 0:
        return '\n'.join('- ' + c for c in cells), end
    if len(cells) % cols: raise ValueError('%d cells is not a multiple of %d columns' % (len(cells), cols))
    rws = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    md = '| ' + ' | '.join(rws[0]) + ' |\n|' + '---|' * cols + '\n' + '\n'.join('| ' + ' | '.join(r) + ' |' for r in rws[1:])
    return md, end

def rebuild(para):
    """-> new paragraph text or None"""
    for spec in SPECS:
        if not para.startswith(spec['m']): continue
        pos, out = 0, []
        if spec.get('cap'):
            if not para.startswith(spec['cap']): raise ValueError('caption')
            out.append('**' + spec['cap'] + '**'); pos = len(spec['cap'])
        md, end = _cut(para, spec, pos); out.append(md)
        if 'then' in spec:
            md2, end = _cut(para, spec['then'], end); out.append(md2)
        tail = para[end:].strip()
        if tail: out.append(tail)
        return '\n\n'.join(out)
    return None
