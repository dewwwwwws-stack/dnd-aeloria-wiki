# 5e.tools sync for the Character Sheet

Once a week this checks 5e.tools and writes a **pack** file that the Character Sheet reads when it opens.
The pack holds what 5e.tools has that the sheet does not. It only ever **adds**: nothing the sheet already has is changed.

## Set-up (once)

1. Copy the two folders in this zip into the **main branch** of `dewwwwwws-stack/dnd-aeloria-wiki`:
   - `sync5e/`
   - `.github/workflows/5etools-sync.yml`
2. In the repo on GitHub: **Settings → Actions → General → Workflow permissions → Read and write permissions**, and save.
3. **Actions → 5e.tools sync → Run workflow** to try it once. After that it runs by itself every Monday (03:17 UTC).
4. Use the `CharacterSheet.html` that came with this zip (or newer). Older sheets ignore the pack.

The pack is written to `chars/_5etools_pack.json` on the `data` branch (plus `_5etools_pack_1.json`… if it is large)
with a readable `chars/_5etools_report.md` beside it. If your data folder or branch is named differently, change
`DATA_BRANCH` / `DATA_DIR` at the top of the workflow.

## What you will see

- **Nothing new:** the run is green and nothing is committed.
- **New things:** the pack is updated; sheets pick it up when opened (and every 30 minutes).
  Vault → Sources shows the pack date and how much it added. A **new book starts switched off** for players.
- **Needs a look** (for example a weapon with no weapon type): the pack is still published and an issue is opened with the list.
- **Failed** (5e.tools changed shape, a download failed): the run is red, an issue is opened, and **the old pack stays in place**.

## Reports: what changed in each sync

- **In the sheet:** Vault → Sources → "📄 What changed in recent syncs" lists each run (newest first) with the new entries by kind and book. The last 20 runs are kept.
- **On GitHub:** each run writes `chars/_5etools_report.md` on the `data` branch (a readable report that starts with "What changed since the last sync"), shows the same report on the run's summary page, and keeps it as a download on the run.
- **Notifications:** when a run finds something new it opens an issue titled "5e.tools sync: N new (date)" with the report, so GitHub notifies you (by email if your GitHub notifications are on). Problems open a "needs a look" or "FAILED" issue.
- **Run it now:** Vault → Sources → "↻ Run 5e.tools sync now" (or Actions → 5e.tools sync → Run workflow on GitHub).

## What it covers

Magic items, gear, valuables, mounts and vehicles, the weapon and armour types new items need, item pictures and book names.
Spells, feats, classes, species and backgrounds are not synced yet.

## When the sheet is rebuilt

`sync5e/baseline/live.json` is the list of what the sheet already has. When a new `CharacterSheet.html` is built with the
pack's items folded in, replace this file with the new one that comes with it; the pack then shrinks back to "new since that build".

## Run it by hand

```
python3 sync5e/run.py --site 5etools-src --brew homebrew --ua unearthed-arcana --img 5etools-img --out out
```
Needs Python 3.10+, `pip install playwright && python -m playwright install chromium`, and Node 18+.

## Bestiary

Each run also builds the creatures from every 5e.tools book and from the whole 5e.tools homebrew collection (about 28,000 creatures in all, about 66 MB on the `data` branch). Homebrew books from the full collection stay off, and are not downloaded by the sheet or the plugin, until you turn them on in Vault > Sources (there is a "Find a homebrew book" box). The 26 homebrew books the sheet already used behave as before. It writes them to `chars/_bestiary/` on the `data` branch: `index.json` plus one file per book, with large books split. The "## Bestiary" part of the report gives the count and lists any creature that could not be built. Those are usually homebrew that copies a creature from a book that isn't loaded.

- **The sheet:** the DM sees them in Vault > Bestiary, in the books ticked on Vault > Sources. Players see a "Creatures" page with only the creatures the DM marked "Players can see", plus their character's own familiars, summons and Wild Shape forms.
- **Obsidian:** the Character Sheet Sync plugin (1.11.0 or later) has the command "Sync bestiary from the character sheet". It writes the notes and tokens into the vault.

## 5e.tools library (DM only)

Each run also builds everything else in 5e.tools from the official books, the playtest (Unearthed Arcana) collection and the whole homebrew collection. That covers spells, classes and subclasses with their features, species, backgrounds, feats, class options, items, rules, conditions, deities, tables and more, about 85,000 entries in 38 categories. It goes into `chars/_5etools_raw/` on the `data` branch, about 120 MB.

The sheet shows it on the DM's Vault > 5e.tools page, as 5e.tools has it. It is kept apart from the sheet's own lists and never changes a character. A category downloads when you first open it. Homebrew from the full collection only appears once its book is turned on in Vault > Sources. Players never see this page.

The first run after installing this pushes about 190 MB (library plus bestiary). Later runs only push the files that changed.

## New for the sheet

Each run also converts the spells, feats, species, backgrounds, classes, subclasses and class options (invocations, maneuvers, metamagic, Arcane Shots, Rune Knight runes) that the sheet doesn't have yet into the sheet's own format, in `chars/_5etools_sheet/`. It is add-only: anything the sheet already has, by name or by a newer printing, is left out, so the sheet's own versions and house rules win.

- **Which books:** every sheet adds the new entries from official books when it opens. Playtest and homebrew books add theirs once you tick them on Vault > Sources > "Add to the sheet". That list is separate from "Players may browse".
- **Wired automatically:** feat ability score increases, spells and uses; subclass features, bonus spells and uses; background ability scores, skills, tools, origin feat and equipment; species speed, size, darkvision and resistances; invocation spells and prerequisites; spell class lists.
- **Review list:** everything else is listed on the DM's Vault > New from 5e.tools page. Mark entries "wired" or "not needed" and add notes there (`chars/_dm_review.json`). Claude reads the same list in later sessions to wire the rest.
- **A book switched off later:** a character keeps anything it already took from that book. It's marked ⚠ on its sheet, the book is named in the tooltip, and a note shows when the character opens. The character records which books its entries came from, so they still load.
- **After a sheet rebuild:** regenerate `baseline/live.json` (`fivetools/dump.py NEW_SHEET`). It now also lists the sheet's spells, feats and so on, so things the sheet gains natively drop out of the pack.

## Homebrew: stored only once approved

The sync keeps a list of every homebrew and playtest book in `chars/_5etools_books.json`: its name, author and how many spells, creatures, items and so on it has. Your Vault > Sources page uses that list. A homebrew book's contents (creatures, library entries, new-for-the-sheet entries) are stored only if:
- you approved it on either Sources list ("Players may browse" or "Add to the sheet"), or
- a character still uses something from it.

When you approve a book that isn't stored yet, it shows ⏳ and saving starts the sync, so its contents arrive a few minutes later. Turning a book off removes its contents at the next run, unless a character still uses something from it.

Playtest (Unearthed Arcana) books are small and always stored. The 26 homebrew books that the item import already used still feed new items as before.
