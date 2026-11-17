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
