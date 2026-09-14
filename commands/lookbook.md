---
description: Pick this project's visual direction, then write .claude/branding.json
argument-hint: [preset] | --force | --emit-html | --status
---

Open the lookbook picker for the current project so the human can choose a
visual direction. Their choice is written to `.claude/branding.json`, which
every UI-generating skill in this project then reads and obeys.

User arguments: `$ARGUMENTS`

---

## 1. Find the script

Use the first of these paths that actually exists. Check them with `ls` or
`test -f` before running anything:

1. `${CLAUDE_PLUGIN_ROOT}/lookbook/scripts/pick.py`
2. `~/.claude/skills/lookbook/scripts/pick.py`
3. `.claude/skills/lookbook/scripts/pick.py`
4. `./lookbook/scripts/pick.py`

If the first path still contains the literal text `${CLAUDE_PLUGIN_ROOT}`, the
skill is not installed as a plugin, so skip it and try the rest. If none exist,
tell the user lookbook is not installed and point them at
`https://github.com/jalonlivan/claude-lookbook`. Do not try to reimplement it.

Call it with `python` or `python3`, whichever this machine has. It needs only
the Python 3 standard library, so there is nothing to install.

## 2. Pick the mode from the arguments

| arguments | what to run |
| --- | --- |
| *(empty)* | `pick.py --project . --print-url` |
| a preset name | `pick.py --project . --preset <name>` |
| `--force` | `pick.py --project . --print-url --force` |
| `--emit-html` | `pick.py --project . --emit-html` |
| `--status` | just read `.claude/branding.json` and summarise it. Do not launch anything. |

Valid preset names are `editorial-warm`, `swiss-neutral`, `brutalist`,
`dark-luxe`, `product-dense`, `console`, `void`, `bloom`, `platform`,
`gallery`, `custom`. Anything else that starts with `-` should be passed
through to the script unchanged.

**Always pass `--print-url`** for the UI modes. Without it the script opens a
browser on the machine running Claude, which is not always where the human is.

**Never pass `--wait`.** It blocks until submission, and your bash call dies at
about two minutes and takes the server down with it.

## 3. Relay the output verbatim

The script prints a URL and, when it detects the shell is remote, an `ssh -L`
block containing the user's real host and port. **Print that block to the user
exactly as the script emitted it.** Do not paraphrase it, shorten it, or
substitute a placeholder hostname. It is the only way they reach the picker.

This matters because the server binds `127.0.0.1`, which means *this machine*:

- **Terminal on the user's own laptop:** the URL works, nothing else to do.
- **VS Code or Cursor, local:** same, the URL works.
- **SSH, or VS Code connected over SSH:** the browser is on a different machine.
  The editor often forwards the port already, so tell them to try the URL first,
  and give them the `ssh -L` line as the fallback.
- **Container, WSL or Codespace:** usually forwarded automatically. If the URL
  does not open, `--emit-html` is the way out.

## 4. Wait for the human

The server outlives your bash call, so the answer comes back through the
filesystem rather than through the tool result.

1. Give the user the URL on your **very first** pass. They cannot pick anything
   until they see it.
2. Poll for the file, roughly every ten seconds:

   ```bash
   for i in $(seq 1 12); do
     [ -f .claude/branding.json ] && break
     sleep 10
   done
   ```

3. Repeat that loop up to five times, about ten minutes total. Between loops,
   say you are still waiting and repeat the URL.
4. If it times out, say so plainly and offer `--emit-html`.

## 5. Use the result

When the file appears:

- Read it.
- **If `references[]` is non-empty, read every image at those paths before
  writing any markup.** That is the entire point of the upload: a picture stops
  you falling back on a familiar archetype.
- Summarise the pick for the user in two or three lines: the preset, the
  accent, the fonts, and whether it is a light or dark ground.
- Do not start building UI unless they asked for that too.

## Notes

- If a valid `.claude/branding.json` already exists, the script exits
  immediately without launching anything and prints the existing pick. That is
  deliberate. Only add `--force` when the user explicitly asks to change the
  look.
- `--emit-html` writes a self-contained picker that needs no server and no
  forwarded port. The page hands the user a command to paste back into their
  terminal, and **that paste is what writes the config**. Make sure they know
  the picking alone does nothing.
- To generate a logo and favicons that match the pick afterwards, use the
  `mark` skill from the same plugin.
