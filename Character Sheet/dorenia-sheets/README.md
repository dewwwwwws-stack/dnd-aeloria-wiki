# Dorenia Character Sheets

A read-only, web-based character sheet system for the Dorenia D&D campaign. Each character is a JSON file. The frontend is static HTML/CSS/JS — no server, no database, no build step.

## File Structure

```
dorenia-sheets/
├── index.html              ← landing page (roster of all characters)
├── sheet.html              ← the character sheet viewer
├── README.md               ← this file
├── characters/
│   ├── index.json          ← manifest of all characters (must update when adding)
│   ├── _template.json      ← copy this when making a new character
│   ├── klein.json          ← Klein the Warlock
│   └── ...                 ← one .json per character
└── content/
    └── mpmb_library.json   ← homebrew items/feats/subclasses (exported from MPMBScriptGen)
```

## URLs

After deployment to GitHub Pages at `https://<user>.github.io/dorenia-sheets/`:

- **Roster**: `https://<user>.github.io/dorenia-sheets/`
- **One character**: `https://<user>.github.io/dorenia-sheets/sheet.html?char=klein`

The `?char=<id>` parameter must match the filename in `characters/`.

## Setup: GitHub Pages

### 1. Create the repo

```bash
cd C:\Users\corey\Documents\
git init dorenia-sheets
cd dorenia-sheets
# Copy index.html, sheet.html, characters/, content/ into this folder
git add .
git commit -m "Initial commit"
```

### 2. Push to GitHub

Create a new repo at github.com (call it `dorenia-sheets`), then:

```bash
git remote add origin https://github.com/<your-username>/dorenia-sheets.git
git branch -M main
git push -u origin main
```

### 3. Enable Pages

In the repo on GitHub:
- Settings → Pages
- Source: **Deploy from a branch**
- Branch: **main** / root (`/`)
- Save

After ~1 minute, the site is live at `https://<your-username>.github.io/dorenia-sheets/`.

### 4. Test it

Visit the URL. You should see the roster page with Klein's card. Click it; the sheet should load.

If you see "The scroll is illegible" — check the browser console (F12). Most likely cause: a typo in `characters/index.json` or the JSON file isn't valid.

## Setup: Obsidian Publish embedding

Each player gets their own note in the vault with an iframe pointing to their sheet.

In your Obsidian vault, create a note like `Players/Klein.md`:

```markdown
# Klein

<iframe
  src="https://<your-username>.github.io/dorenia-sheets/sheet.html?char=klein"
  width="100%"
  height="1400"
  style="border:none; background:#f4ecd8;"
  loading="lazy">
</iframe>
```

Publish that note. The player accesses their sheet via the Obsidian Publish URL, which is more memorable than the GitHub URL.

**Notes on the iframe:**
- `height="1400"` is roughly right for the Combat tab on desktop. Adjust to taste.
- The sheet has its own internal scroll, so a fixed height is fine.
- You can drop the iframe in any Obsidian note — not just on Publish. It will render in local Obsidian preview mode too.

## Workflow: Adding a new character

1. Copy `characters/_template.json` to `characters/<id>.json` (use lowercase, no spaces — e.g. `cabbage.json`).
2. Fill it in. Remove all `_comment` fields. Use Klein's file as a reference.
3. Add an entry to `characters/index.json`:
   ```json
   { "id": "cabbage", "name": "Cabbage", "player": "", "summary": "...", "active": true }
   ```
4. Commit and push. Within a minute, the site updates.

## Workflow: Updating after level-up

1. Open `characters/<id>.json`
2. Bump the class level. Update `hitDiceRolled`, `state.hp.maxBase`, `state.hitDice`, and `state.spellSlots`.
3. Add any new feats/invocations to the build arrays.
4. Commit + push.

A future "level up" UI is planned — for now, level-ups are manual JSON edits.

## Workflow: Adding homebrew via MPMB scripts (auto-discovery)

**The fully automatic workflow:** save a script in MPMBScriptGen → push the script to GitHub → refresh the sheet. Items, feats, and subclasses appear with zero conversion step.

### Setup (one-time)

Open `sheet.html` and find the `GITHUB_CONFIG` block near the top of the `<script>` section:

```javascript
const GITHUB_CONFIG = {
  user: 'YOUR_GITHUB_USERNAME',   // ← change me
  repo: 'dorenia-sheets',         // ← repo name
  branch: 'main',
  scriptsPath: 'content',         // ← folder containing .js scripts
  cacheKey: 'dorenia_homebrew_cache_v1'
};
```

Set `user` to your GitHub username. Commit and push. From that point on, the viewer will scan `https://github.com/<user>/<repo>/tree/<branch>/<scriptsPath>` on every load, find every `.js` file, parse it, and merge everything into the homebrew library.

### Workflow

1. Build content in MPMBScriptGen — items, feats, subclasses
2. Click **Download** in the script generator to get a `.js` file
3. Drop it into the `content/` folder of your repo
4. Commit and push
5. Players' sheets see the new content on next refresh

The viewer caches results in `sessionStorage` keyed on the file SHAs from the GitHub API. If you haven't pushed changes, no scripts are re-fetched on a refresh — just the (cheap) folder listing call.

### How the parser works

MPMB scripts are JavaScript that defines globals (`MagicItemsList["..."] = {...}`, `FeatsList["..."] = {...}`, `ClassList["..."] = {...}`) and calls `AddSubClass(parent, key, def)`. The viewer evaluates each script inside a sandbox where these globals and helpers (`desc()`, `toUni()`, `How()`, `What()`) are stubbed, captures everything that gets assigned, and translates the result into the viewer's homebrew shape.

Scripts can use real MPMB syntax — regex literals (`regExpSearch: /.../i`), nested functions (`prereqeval: function(v) {...}`), `desc([...])` array helpers, multi-line string concatenation — and parsing handles all of it.

### What gets detected

The parser captures all of the following MPMB content types:

- **Magic Items** (`MagicItemsList["..."] = {...}`) — name, type, rarity, attunement, descriptions, weight, usages, recovery
- **Feats** (`FeatsList["..."] = {...}`) — name, prerequisite, description, full description, action, usages
- **Subclasses** (`AddSubClass(parent, key, {...})`) — parent class, name, features dict keyed by level
- **Classes** (`ClassList["..."] = {...}`) — full class definitions including hit die, primary ability, saves, skill choices, armor/weapon proficiencies, ASI levels, spellcasting factor, subclass scaffolding, and features by level. This is what enables entirely new classes like **Artificer** or **Psion** to be defined in homebrew scripts and rendered correctly on character sheets.
- **Races** (`RaceList["..."] = {...}`) — name, size, speed, languages, vision, traits
- **Backgrounds** (`BackgroundList["..."] = {...}`) — name, skills, tools, languages, equipment, feature

When a character JSON references a homebrew class, race, or background by key (e.g. `"key": "artificer"`), the Features tab automatically pulls in the full data — class features unlocked at the character's current level, racial traits, etc. — and displays them with DOR badges to mark them as homebrew.

For spells, the same applies: any spell in the character's `spellsKnown` list that matches a homebrew `SpellsList` entry becomes clickable in the Spells tab. Clicking opens a modal showing the spell's full mechanical info — level, school, casting time, range, components, duration, save, description, ritual/concentration markers. Spells with a known level get grouped under "Level 1", "Level 2", etc. headers; spells without a homebrew entry (SRD spells) appear under "Other Known Spells" or "Known Spells" with no special styling.

### Rate limits

GitHub's unauthenticated API allows **60 requests per hour per IP**. Each page load uses one listing call + (only on cache miss) one fetch per new/changed script. For normal use this is a non-issue. If you hit the limit, the viewer falls back to the local `content/mpmb_library.json` if present, or shows the sheet without homebrew lookups.

### Fallback behavior

If GitHub is unreachable, rate-limited, or the config is left at the default `YOUR_GITHUB_USERNAME`, the viewer falls back to reading `content/mpmb_library.json` locally. The sheet still works fully — it just won't auto-discover new scripts.

## Workflow: Manual homebrew (no GitHub)

If you'd rather not use GitHub auto-discovery, leave the config alone. The viewer still reads `content/mpmb_library.json` from the local filesystem, which can be in either:

1. **MPMBScriptGen's native format** (an array of envelope objects) — what the MPMB Script Generator tool writes via Dorenia Sync.
2. **Direct viewer format** (a keyed object with `magicItems`, `feats`, `subclasses` top-level keys) — hand-authored.

The adapter auto-detects which format it got and translates internally.

### Item key matching

The viewer's lookup is **resilient to key formatting differences**. An item saved in MPMBScriptGen as `"Azeros' Shard"` becomes the key `azeros-shard` after normalization. A character's inventory can reference it as any of:

- `"azeros-shard"`
- `"azeros shard"`
- `"Azeros' Shard"`
- `"AZEROS_SHARD"`

All resolve to the same library entry.

### Adding to a character

To give a character a homebrew item, add an inventory entry in their JSON:

```json
{ "key": "azeros-shard", "name": "Azeros' Shard", "source": "DOR", "qty": 1, "homebrew": true }
```

The sheet will show the item with a "DOR" badge. Clicking it opens the full description pulled from the library.

## Local testing

Browsers block `fetch()` on `file://` URLs, so opening `sheet.html` directly won't work. Use a local server:

```bash
cd dorenia-sheets
python3 -m http.server 8000
# Now visit http://localhost:8000/
```

(Python 3 is built into recent Windows and Mac. If on Windows without Python, install Node and use `npx serve` instead.)

## What this does NOT do (yet)

- **No editing.** This is read-only. Updates are git commits.
- **No live HP/slots.** Players tracking damage/slots during a session should do it on paper or in a separate tool; this sheet shows the post-session state.
- **No spell descriptions.** Only spell names. A future SRD content file (`content/srd_spells.json`) would enable click-to-view spell details, mirroring how homebrew items work today.
- **No SRD class feature descriptions.** Same approach as spells — drop in an SRD content file later.
- **No character builder.** Building a character requires editing JSON directly. A future builder tool is planned.

## Phases on the roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Read-only viewer + GitHub Pages + Obsidian embed | ✓ Built |
| 2 | SRD content files (spells, class features) for click-to-view details | Pending |
| 3 | "Level up" builder UI (still generates JSON, no auth needed) | Pending |
| 4 | Player edit mode (HP, slots, conditions during play) — needs write backend | Pending |
| 5 | DM edit mode with overrides | Pending |

For phase 4+, writes will need either a Cloudflare Worker / Supabase Edge Function holding a GitHub API token, or migrating off git storage entirely. Until then, edits go through git.

## Troubleshooting

**"The scroll is illegible"** — Character JSON failed to load. Check:
- File exists at `characters/<id>.json`
- JSON parses (use `python3 -m json.tool characters/<id>.json`)
- `?char=` parameter matches filename (case-sensitive on Linux/GitHub Pages)

**Homebrew item not clickable** — The `key` in the inventory entry must match a key in `content/mpmb_library.json` under `magicItems`. Check spelling. Without a match the item still renders, just not clickable.

**Sheet looks wrong / unstyled** — The Google Fonts request may be blocked. The sheet still works with fallback serifs.

**Iframe doesn't show in Obsidian** — Obsidian's reading-mode renderer allows iframes. If using a plugin-restricted setup or the iframe doesn't appear, check that you're not in a sandboxed view. The `obsidian-html-plugin` (nuthrash) is NOT needed for this — these are plain iframes loading from an external host.
