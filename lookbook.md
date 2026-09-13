# lookbook — build spec

A Claude Code skill that opens a local web UI where a human picks a website's
visual direction *before* Claude writes any UI code. It writes design tokens to
`.claude/branding.json`, which any UI-generating skill then reads and obeys.

This file is the working spec. Update it as decisions change.

---

## 1. Problem

Left unconstrained, models converge on the same output: Inter, an indigo/violet
gradient on white, rounded cards, a three-icon feature grid. This is
distributional convergence, not a bug — safe choices dominate the training data.

Existing design skills fix this with *heuristics* ("avoid Inter", "pick an
aesthetic direction"). They know what generic looks like but have no idea what
**your** product should look like. The remaining gap is the input side: today the
only way to express taste is to hand-write a token spec or paste a prompt prefix
every session.

lookbook is a GUI for that. Click a look, drop a reference screenshot, get a
persisted token file.

---

## 2. Locked decisions

| Decision | Value |
| --- | --- |
| Name | `lookbook` |
| Audience | Public skill, others install it |
| Config location | Per-project `.claude/branding.json` |
| Dependency direction | One-way. lookbook knows nothing about its callers. |
| Runtime | Python 3 stdlib only. No pip, no npm, no `uv`. |
| Bind address | `127.0.0.1` only |

---

## 3. Layout

```
lookbook/
├── SKILL.md
├── scripts/
│   ├── pick.py          # CLI + server, single entry point
│   └── schema.py        # validation + defaults
├── assets/
│   └── ui/index.html    # single file, inline CSS/JS, no build step
└── references/
    └── presets.md       # full token values per preset
```

Keep `SKILL.md` under ~500 lines. Preset token tables live in
`references/presets.md` and are read only when needed.

---

## 4. CLI contract

Everything the skill does goes through one command. Callers depend on this
signature, so treat it as public API.

```
pick.py --project <dir> [options]

  --print-url            print URL and exit, do not open a browser
  --force                re-pick even if a valid config exists
  --preset <name>        headless: write tokens without the UI
  --accent <#hex>        headless: override the preset accent
  --timeout <seconds>    server self-terminate, default 900
  --wait                 block until submission (humans only, not agents)

exit 0   valid config now exists (pre-existing or newly written)
exit 2   timed out or aborted by user
exit 3   invalid arguments / unwritable project dir
```

**Idempotence is the most important property here.** If a valid
`.claude/branding.json` already exists and `--force` is absent, exit 0
immediately and launch nothing. Without this, every callers' run pops a browser
window and the skill gets uninstalled within a week.

---

## 5. The handshake

Agent bash calls time out (~2 minutes by default). A server that blocks while a
human fiddles with colour pickers will be killed mid-thought. So the data comes
back through the filesystem, not the tool call.

1. `pick.py` binds the port, forks a detached server, prints the URL **and the
   result path**, exits immediately.
2. `SKILL.md` instructs Claude to poll for `.claude/branding.json` in a loop
   (e.g. `sleep 10` × 60), reporting the URL to the user on the first pass.
3. The form POSTs, the handler validates and writes the JSON, the server shuts
   itself down.
4. Claude reads the file. If a reference image was uploaded, Claude reads the
   image too.

`--wait` exists for humans running it by hand. Agents always use poll mode.

---

## 6. Server rules

Since this ships publicly, it runs on other people's machines. A plain localhost
server is reachable by **any page in the user's browser** — any website can POST
to `127.0.0.1:6780` and silently rewrite someone's branding config, or read it
back.

- Bind `127.0.0.1` only. Never `0.0.0.0`.
- Port: try 6780, walk upward to 6799 on `EADDRINUSE`, print the port actually
  bound. Two projects open at once is a normal Tuesday.
- Generate a random token per launch. Put it in the URL query, require it on
  every POST, compare in constant time.
- Reject any request carrying a cross-origin `Origin` or `Referer` header.
- Send `Cache-Control: no-store`.
- Self-terminate at `--timeout`. An abandoned run must not leave a listener open
  on someone's laptop.
- Serve only from `assets/ui/`. No path traversal, no arbitrary file reads.

**Uploads:** validate magic bytes (not the extension), cap at ~5 MB, store under
`.claude/branding/refs/` with generated filenames, never echo the original
filename back into a path.

---

## 7. Output schema

```json
{
  "schemaVersion": 1,
  "preset": "editorial-warm",
  "tokens": {
    "color": {
      "bg":      "#FBF3EF",
      "surface": "#FFFFFF",
      "text":    "#1C1512",
      "muted":   "#7A6A62",
      "accent":  "#C2603F",
      "border":  "#E8DBD3"
    },
    "type": {
      "display": { "family": "Fraunces", "weights": [600, 900] },
      "body":    { "family": "Source Sans 3", "weights": [400, 600] },
      "scale":   [12, 14, 16, 20, 28, 44, 72]
    },
    "radius":  { "sm": "2px", "md": "4px", "lg": "8px" },
    "spacing": { "base": 8 },
    "shadow":  "none"
  },
  "avoid": [
    "Inter, Roboto, DM Sans",
    "indigo/violet gradients",
    "glassmorphism and blur panels",
    "three equal-weight icon+heading+sentence cards",
    "gradient text"
  ],
  "references": [
    { "path": ".claude/branding/refs/a1f2.png", "note": "spacing and type scale, not the colours" }
  ],
  "meta": { "createdAt": "2026-09-13T12:00:00Z", "tool": "lookbook" }
}
```

`schemaVersion` goes in from day one. The token shape will change once real
output exists, and public installs will be sitting on old files.

**The `avoid` list is per-project and generated relative to the picked palette.**
A global "never purple" rule is wrong — plenty of brands are deliberately purple.
What the list forbids is the *default*, the colour nobody chose.

---

## 8. Presets

Five looks plus custom. Each ships concrete values in `references/presets.md` —
hexes, font families, weights, a spacing base. Adjectives alone ("editorial,
warm") do nothing on the next turn.

1. **editorial-warm** — serif display, cream ground, warm single accent, near-zero radius
2. **swiss-neutral** — grotesk, white/black, one accent, visible grid, generous whitespace
3. **brutalist** — weight extremes (200 vs 900), hard edges, one loud colour, no shadow
4. **dark-luxe** — near-black ground, thin type, image-led, minimal chrome
5. **product-dense** — muted low-saturation, tight radii, high information density, full state coverage
6. **custom** — image upload plus free-text instructions

The custom path is the strongest feature, not a fallback. A picture beats prose
because it stops the model falling back on a familiar archetype. Store the path
and let the calling session read the image directly.

Preset 5 exists because the other four optimise for expressive marketing pages.
Dashboards, tables and settings live or die on density and state coverage
(loading, empty, error), which "be distinctive" does not address.

---

## 9. Contract for consuming skills

Any UI-generating skill declares lookbook as a precondition. It does not import
it, wrap it, or reimplement it.

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

## 10. Build order

Each step is independently testable. Do not start the UI until step 2 passes.

1. `schema.py` — write, read, validate. No server, no UI.
2. Headless flags (`--preset`, `--accent`). This proves the whole contract
   end-to-end with zero frontend.
3. Server: port walk, token auth, origin check, detached launch, timeout.
4. `index.html` with the five presets.
5. Upload path and custom instructions.
6. Trigger evals, then package as `.skill`.

---

## 11. Open questions

- **graphify integration.** What does it map, and what does it emit? That decides
  whether it needs the full token set or only colour.
- Should lookbook also write `branding.css` (CSS custom properties) and a
  Tailwind config fragment to disk, or stay format-agnostic?
- What exactly makes an existing `branding.json` "invalid"? Schema mismatch only,
  or also a missing referenced image?
- Headless installs: is `--print-url` enough for SSH users, or does the flag path
  need an interactive terminal fallback?