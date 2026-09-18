---
name: lookbook
description: Pick a website's visual direction before writing any UI code. Opens a local web UI where a human picks a ground (light or dark) and then a look from eleven presets, tunes the palette, and drops in reference screenshots; writes design tokens to .claude/branding.json for every UI-generating skill in the project to obey. Covers light pigment looks (editorial, swiss, brutalist, dense product UI) and the dark developer-product family - a dark ground lit by one source with hairline borders instead of shadows, as on Vercel, GitHub, Linear-style consoles and component catalogs. Tokens cover colour, lighting and glow, typography including monospace, density, radius and motion. Use when starting a new UI, redesigning an existing one, when the user asks to set or change a project's visual direction, branding, theme, dark mode or aesthetic, when they want a site that looks premium rather than generic, or when a UI skill needs tokens and .claude/branding.json is missing.
---

# lookbook

Left unconstrained, models converge on the same output: Inter, an indigo/violet
gradient on white, rounded cards, a three-icon feature grid. That is
distributional convergence, not a bug. Safe choices dominate the training data.

lookbook fixes the input side. A human clicks a look, and the result is a token
file this project's UI skills read and obey.

---

## Run it

```bash
python <skill-dir>/scripts/pick.py --project . --print-url
```

That is the whole interface. It prints two things:

```
  URL: http://127.0.0.1:6780/?t=<token>
RESULT: /abs/path/to/.claude/branding.json
```

**Always pass `--print-url`.** Without it the command opens a browser on the
machine running Claude, which is not always where the human is.

**Never pass `--wait`.** It blocks until submission; your bash call dies at
about two minutes and takes the server down with it. `--wait` is for humans
running the command by hand.

### The handshake

The server outlives the bash call. The result comes back through the
filesystem, not through the tool call.

1. Run the command above. It returns immediately.
2. **Give the user the URL on your very first pass.** They cannot pick anything
   until they see it. Say it plainly: *"Open <URL> and choose a direction."*
3. Poll for the result file:

   ```bash
   for i in $(seq 1 12); do
     [ -f .claude/branding.json ] && break
     sleep 10
   done
   cat .claude/branding.json
   ```

   Run that loop up to five times (≈10 minutes) before giving up. Between
   loops, tell the user you are still waiting and repeat the URL.
4. When the file appears, read it. **If `references[]` is non-empty, read every
   image at those paths before writing any markup.** That is the whole point of
   the upload: a picture stops you falling back on a familiar archetype.

The server shuts itself down the moment the form is submitted, and self-
terminates after `--timeout` seconds (default 900) if nobody ever shows up.

### Where is the browser?

The server binds `127.0.0.1`. That address means *this machine*, so the URL is
only clickable when the browser and the server are the same machine. Three
cases, and the command sorts them out for you:

| case | what happens |
| --- | --- |
| Terminal on the user's own laptop | The URL works. Nothing to do. |
| Terminal on a remote box over SSH | The URL is dead until a port is forwarded. The run detects `SSH_CONNECTION` and prints the exact `ssh -L` line to paste in a second terminal. **Relay that block to the user verbatim**, since it contains their host and port. |
| VS Code / Cursor over SSH | The editor usually forwards the port already, so the URL just works. The `ssh -L` block is printed anyway and costs nothing. |

A browser is never opened automatically when the shell is remote, because opening one
on the box the user is SSH'd into helps nobody.

**Containers, WSL and Codespaces** normally forward the port themselves, and
`SSH_CONNECTION` does not catch them. When they do not forward, the URL simply
fails to open. That is what `--emit-html` is for.

### When no port can be forwarded

```bash
python <skill-dir>/scripts/pick.py --project . --emit-html
```

This writes a single self-contained HTML file with presets, styles and images all
inlined, no server, no network. The user opens it however they can (scp it,
their editor's remote file browser, a file share). Because the page has no way
to reach back, it hands them a command:

```
python .../pick.py --project . --apply <blob>
```

They paste that into the terminal they already have open, and *that* writes the
config. Tell them this step is required, because picking alone writes nothing.

Two limits of this path: reference-image upload is off (there is no server to
receive the file), and `--apply` writes even when a valid config exists, since
pasting it is itself an explicit choice. It reports what it replaced.

### Idempotence

If a valid `.claude/branding.json` already exists, the command prints it and
exits 0 **without launching anything**. This is deliberate and applies to every
mode, headless included. Do not work around it.

Re-pick only when the user explicitly asks to change the look:

```bash
python <skill-dir>/scripts/pick.py --project . --print-url --force
```

### Headless

When the user names a look outright ("make it brutalist", "use the dark luxe
one") and does not want to fiddle with a UI, skip the browser entirely:

```bash
python <skill-dir>/scripts/pick.py --project . --preset brutalist --accent '#00AAFF'
```

`--accent` requires `--preset`.

Light-ground presets: `editorial-warm`, `swiss-neutral`, `brutalist`,
`product-dense`.
Dark-ground presets: `void`, `platform`, `bloom`, `gallery`, `console`,
`dark-luxe`.
Plus `custom`, which belongs to both.

### Resync requests

The picker checks whether the copy of this plugin you are running is behind a
copy already sitting on the disk -- a newer version Claude Code fetched but
never installed, or a marketplace clone whose files no longer match. It makes
no network calls; it only reads what Claude Code has already downloaded.

When it finds something it says so in the launch output, and the browser shows
a cloud in the corner with a **Resync** button. That button does not reinstall
anything. The picker is executing out of the directory a reinstall replaces,
so self-replacement is how you end up with a half-written plugin.

Instead it writes `.claude/branding/.lookbook-resync.json`. **After the picker
returns, check for that file.** If it is there, the human asked for the resync:
tell them what is stale, offer to run the two commands it lists (they are
slash commands -- the human runs them, you cannot), then delete the file so it
does not ask twice.

```json
{ "level": "update", "installed": "2.0.0", "available": "2.1.0",
  "commands": ["/plugin marketplace update <market>",
               "/plugin install <plugin>@<market>"] }
```

`level` is `update` when a newer version is genuinely on disk, `drift` when the
files differ at the same version number, `orphaned` when Claude Code no longer
counts the running copy as installed, and `stale` when nothing local has
checked in three weeks. Only `update` means a new version certainly exists --
do not upgrade the others' wording when you relay them.

### Exit codes

| code | meaning |
| --- | --- |
| 0 | a valid config exists, or the picker is up and `RESULT:` names the file to poll |
| 2 | timed out, or the user abandoned it |
| 3 | bad arguments, or the project directory is not writable |

---

## Using the tokens

```json
{
  "schemaVersion": 2,
  "preset": "bloom",
  "mode":   "dark",
  "family": "dark-dev",
  "tokens": {
    "color":    { "bg": "…", "surface": "…", "text": "…", "muted": "…", "accent": "…", "border": "…" },
    "ground":   { "base": "#060507", "cast": "#1A0B2E" },
    "lighting": { "type": "field", "hue": ["#A855F7","#4C1D95"], "intensity": 0.7,
                  "position": "bottom-left", "grain": true },
    "surface":  { "elevation": "border", "border": "rgba(255,255,255,0.08)",
                  "raise": "rgba(255,255,255,0.04)" },
    "type":     { "display": {"family":"…","weights":[…]}, "body": {…}, "mono": {…},
                  "accentWord": null, "scale": [12,14,16,20,30,48,80] },
    "radius":   { "sm": "6px", "md": "10px", "lg": "16px", "button": "999px" },
    "spacing":  { "base": 8 },
    "shadow":   "none",
    "density":  "marketing",
    "motion":   { "load": "staggered", "stagger": "60ms", "micro": "standard" }
  },
  "altMode":    null,
  "avoid":      ["…"],
  "references": [{ "path": ".claude/branding/refs/a1f2.png", "note": "spacing and type scale, not the colours" }],
  "notes":      "free text from the human, present only if they wrote some",
  "meta":       { "createdAt": "…", "tool": "lookbook" }
}
```

### The two families

`family: "pigment"` puts the colour in the ink: a pale ground, a pigment accent,
elevation by shadow.

`family: "dark-dev"` puts the colour in the **emission**: a dark ground lit by
one source, with the interface built out of 1px hairline borders instead of
shadows. This is not dark mode, which is only a colour inversion. These pages
are *lit*: one thing glows and everything else stays near-monochrome so the
glow reads. If you take one token from this family, take
`surface.elevation: "border"`: getting shadows out of the output does more than
any colour choice.

### The v2 groups

| group | what it settles |
| --- | --- |
| `ground` | the page ground, and the hue cast washing through it |
| `lighting` | `none` / `spot` / `field` / `wash`, its hue, intensity, position and grain |
| `surface` | where elevation comes from, and the exact hairline and raise colours |
| `type.mono` | first-class. Every one of these sites shows code; an unconsidered mono is instantly wrong |
| `type.accentWord` | at most **one word per headline** in a contrasting face. Obey the `use` string |
| `density` | `marketing` / `catalog` / `console` |
| `motion` | one orchestrated page-load beats scattered micro-interactions; `stagger` is the value, do not reinvent it |
| `radius.button` | `999px` means pills. Separate from container radius on purpose |

**`lighting.grain: true` matters more than it sounds.** A large gradient without
noise bands on real displays and reads cheap.

### altMode

`altMode` is an optional palette for the opposite mode. It carries only the
groups that change with mode (`color`, `ground`, `lighting`, `surface`), since
type, radius, spacing, density and motion do not.

**`altMode: null` is an instruction, not an omission.** That look has no other
mode. Do not invent one, and do not add a theme toggle.

Rules when you consume this file:

- **Use the values exactly.** Do not round a hex, swap a font for a "similar"
  one, or substitute a default for anything the file specifies.
- **Treat `avoid` as hard constraints.** The list is generated per-project
  against the chosen palette, so it forbids the default nobody picked, not a
  colour family someone deliberately wanted. `bloom` is deliberately purple;
  that is a choice, not the failure the list guards against.
- **Obey `lighting`.** One light source. A second glow, or an accent that
  matches the glow colour, breaks the whole family.
- **Read every image in `references[]`** before writing markup, and honour each
  `note`, which says what to take from that image and what to ignore.
- `notes` is free text from the human. It outranks your own instincts.
- `spacing.base` is the unit; derive the rest from it rather than inventing
  values.
- `type.scale` is the full set of font sizes. Do not add sizes between them.

Full token tables for every preset are in `references/presets.md`. Read that
only when you need to quote or compare exact values, not on every run.

---

## Declaring lookbook as a precondition

Any skill that generates UI should depend on lookbook one-way: it does not
import it, wrap it, or reimplement it. Paste this into that skill:

```markdown
## Before generating any UI

1. Check for `.claude/branding.json`.
2. If missing or invalid, run:
   `python <lookbook>/scripts/pick.py --project . --print-url`
   Give the user the URL, then poll for the file.
3. Read the tokens. Use them exactly. Do not substitute defaults for anything
   the file specifies.
4. Read every image in `references[]` before writing markup.
```

---

## Notes for the maintainer

- Python 3 stdlib only. No pip, no npm, no `uv`, no build step.
- `scripts/schema.py` is the single source of truth for presets, defaults and
  validation. `references/presets.md` is generated from it; the server serves
  `schema.PRESETS` directly, so the UI can never drift from the schema.
- `assets/ui/index.html` is one file with inline CSS and JS and no
  dependencies. It renders each preset preview in that preset's own tokens,
  which is what makes the choice legible.
- The picker page is offline by default. The "load the real fonts" checkbox is
  opt-in because fetching from Google Fonts leaks the visit.
- `schemaVersion` is 2. **A v1 file is migrated on read, not rejected**. Every
  v2 group is derived from what the v1 file already says, so an existing install
  keeps its look and is never sent back to the picker. The file on disk is left
  alone until the next write. A file from a *future* version is still refused,
  since half-understanding it would silently mis-render someone's brand.
- Every v2 field is additive and optional, so a v1 consumer keeps working. The
  `mark` skill was written against v1 and reads a v2 config unchanged.

### Security

This ships publicly and runs on other people's machines. A plain localhost
server is reachable by **any page in the user's browser**. Without these
guards, any website could silently rewrite someone's branding config or read it
back.

- Binds `127.0.0.1` only, never `0.0.0.0`.
- Port 6780, walking up to 6799 on collision; the bound port is printed.
- A fresh random token per launch, required on every request, compared with
  `hmac.compare_digest`.
- Cross-origin `Origin`/`Referer` rejected; POSTs must prove same-origin.
- `Cache-Control: no-store` and a restrictive CSP on every response.
- Serves a fixed whitelist of files from `assets/ui/`, so there is no traversal surface.
- Uploads: magic bytes checked rather than the extension, capped at 5 MB,
  stored under `.claude/branding/refs/` under generated names. A
  client-supplied filename never reaches a path.
- Self-terminates at `--timeout`, so an abandoned run leaves no listener open.

### Runtime files

While a picker is live it keeps `.claude/branding/.lookbook-run.json` (port,
token, pid) and appends to `.claude/branding/.lookbook-server.log`. The run
file is removed on shutdown. Re-running the command while a picker is already
up reuses it rather than stacking a second server.

A resync request from the picker's cloud button lands in
`.claude/branding/.lookbook-resync.json`. Unlike the run file it is *not*
cleaned up on shutdown -- it is a message, and it stays until whoever reads it
deletes it.
