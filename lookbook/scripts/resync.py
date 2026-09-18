"""Is the copy of this plugin we are running behind a copy already on disk?

Not an update checker. The picker makes no outbound connections and never
will, so it cannot learn that a release exists. What it can do is read what
Claude Code has already fetched:

    ~/.claude/plugins/marketplaces/<market>/   a git clone, refreshed by Claude Code
    ~/.claude/plugins/cache/<market>/<plugin>/<version>/   the copy actually running
    ~/.claude/plugins/known_marketplaces.json  when that clone was last refreshed

So this is a drift detector. It reports, with certainty, that the running copy
is behind something local -- and where it cannot be certain it says so in those
words. The distinction matters: a bubble that cries "update available" off a
guess gets ignored by the second launch, and then the one that matters is
ignored too.

Every path here is a read of a local file. Nothing in this module opens a
socket, and check() never raises -- a confused answer about plugin versions is
not worth failing a picker over.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time

# Noise that legitimately differs between a git clone and an installed copy.
# Miss one of these and the detector reports drift on every single launch.
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".in_use", ".venv", ".idea",
    ".pytest_cache", ".mypy_cache",
}
SKIP_FILES = {".orphaned_at", ".DS_Store", "Thumbs.db", ".gitignore"}

STALE_DAYS = 21
MAX_FILES = 4000
MAX_BYTES = 48 * 1024 * 1024


def check(skill_root: str) -> dict | None:
    """Returns a verdict dict, or None when there is nothing to say."""
    try:
        return _check(skill_root)
    except Exception:
        return None


# ==========================================================================
# The check
# ==========================================================================


def _check(skill_root: str) -> dict | None:
    installed = _plugin_root(skill_root)
    if not installed:
        return None  # not packaged as a plugin at all

    manifest = _read_json(os.path.join(installed, ".claude-plugin", "plugin.json"))
    if not isinstance(manifest, dict):
        return None
    plugin = str(manifest.get("name") or "").strip()
    version = str(manifest.get("version") or "").strip()
    if not plugin:
        return None

    plugins_dir = _plugins_dir(installed)
    if not plugins_dir:
        # Running from a dev checkout or a hand-placed ~/.claude/skills copy.
        # There is no marketplace to resync against, so say nothing.
        return None

    market, clone, refreshed = _marketplace_for(plugins_dir, installed, plugin)
    if not clone or not os.path.isdir(clone):
        return None
    if os.path.abspath(clone) == os.path.abspath(installed):
        return None  # we ARE the clone; resyncing would be a no-op

    base = {
        "plugin": plugin,
        "marketplace": market,
        "installed": version,
        "available": None,
        "commands": [
            f"/plugin marketplace update {market}",
            f"/plugin install {plugin}@{market}",
        ],
    }

    # -- 1. Version drift. The only signal that earns the word "update". ----
    available = _clone_version(clone, plugin)
    if available and _newer(available, version):
        base["available"] = available
        base["level"] = "update"
        base["title"] = f"{plugin} {available} is on your disk"
        base["detail"] = (
            f"You are running {version}. Claude Code already fetched {available} "
            "but it has not been installed yet."
        )
        return base

    # -- 2. Content drift at the same version. The author's daily reality. --
    a, b = _tree_hash(installed), _tree_hash(clone)
    if a and b and a != b:
        base["level"] = "drift"
        base["title"] = "Your installed copy is out of date"
        base["detail"] = (
            f"The {market} source on this machine differs from the {version} "
            "copy you are running. Reinstall to pick the changes up."
        )
        return base

    # -- 3. Orphaned. Claude Code no longer counts this copy as installed. --
    if os.path.exists(os.path.join(installed, ".orphaned_at")):
        base["level"] = "orphaned"
        base["title"] = "This copy is no longer registered"
        base["detail"] = (
            "Claude Code has marked this cached version as orphaned, which "
            "usually means the plugin was disabled or superseded."
        )
        return base

    # -- 4. Nobody has looked in a while. An admission, not a claim. -------
    if refreshed and (time.time() - refreshed) > STALE_DAYS * 86400:
        when = time.strftime("%d %b %Y", time.localtime(refreshed))
        base["level"] = "stale"
        base["title"] = "Update check is overdue"
        base["detail"] = (
            f"Claude Code last refreshed {market} on {when}. This picker makes "
            "no network calls, so it cannot tell you whether anything newer "
            "exists -- only that nothing here has looked recently."
        )
        return base

    return None


# ==========================================================================
# Locating the pieces
# ==========================================================================


def _plugin_root(skill_root: str) -> str | None:
    """Walk up from the skill directory to the plugin that contains it."""
    cur = os.path.abspath(skill_root)
    for _ in range(6):
        if os.path.isfile(os.path.join(cur, ".claude-plugin", "plugin.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def _plugins_dir(start: str) -> str | None:
    """The ~/.claude/plugins directory we live under, if we live under one."""
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.isfile(os.path.join(cur, "known_marketplaces.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def _marketplace_for(
    plugins_dir: str, installed: str, plugin: str
) -> tuple[str, str | None, float | None]:
    """Which marketplace this install came from, where its clone is, and when
    that clone was last refreshed."""
    known = _read_json(os.path.join(plugins_dir, "known_marketplaces.json"))
    known = known if isinstance(known, dict) else {}

    # The cache path names the marketplace: cache/<market>/<plugin>/<version>.
    name = ""
    try:
        parts = os.path.relpath(installed, plugins_dir).split(os.sep)
        if len(parts) >= 3 and parts[0] == "cache":
            name = parts[1]
    except ValueError:
        pass

    # Otherwise ask each known marketplace whether it ships this plugin.
    if name not in known:
        name = ""
        for candidate, meta in known.items():
            loc = (meta or {}).get("installLocation")
            if not loc:
                continue
            doc = _read_json(os.path.join(loc, ".claude-plugin", "marketplace.json"))
            if not isinstance(doc, dict):
                continue
            for entry in doc.get("plugins") or []:
                if isinstance(entry, dict) and entry.get("name") == plugin:
                    name = candidate
                    break
            if name:
                break
    if not name:
        return "", None, None

    meta = known.get(name) or {}
    clone = meta.get("installLocation") or os.path.join(plugins_dir, "marketplaces", name)
    return name, clone, _refreshed_at(clone, meta.get("lastUpdated"))


def _refreshed_at(clone: str, last_updated) -> float | None:
    """Most recent evidence that this clone was refreshed."""
    stamps = []
    if isinstance(last_updated, str):
        ts = _parse_iso(last_updated)
        if ts:
            stamps.append(ts)
    # A fetch touches FETCH_HEAD even when it changes nothing.
    for rel in (os.path.join(".git", "FETCH_HEAD"), os.path.join(".git", "HEAD")):
        try:
            stamps.append(os.path.getmtime(os.path.join(clone, rel)))
        except OSError:
            pass
    return max(stamps) if stamps else None


def _parse_iso(text: str) -> float | None:
    try:
        from datetime import datetime

        cleaned = text.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned).timestamp()
    except Exception:
        return None


def _clone_version(clone: str, plugin: str) -> str | None:
    """The version the marketplace clone advertises for this plugin."""
    doc = _read_json(os.path.join(clone, ".claude-plugin", "marketplace.json"))
    if isinstance(doc, dict):
        for entry in doc.get("plugins") or []:
            if isinstance(entry, dict) and entry.get("name") == plugin:
                got = str(entry.get("version") or "").strip()
                if got:
                    return got
    doc = _read_json(os.path.join(clone, ".claude-plugin", "plugin.json"))
    if isinstance(doc, dict):
        got = str(doc.get("version") or "").strip()
        if got:
            return got
    return None


# ==========================================================================
# Comparing
# ==========================================================================


def _newer(a: str, b: str) -> bool:
    """Is a a later version than b? Unparseable either side means 'no'."""
    pa, pb = _parts(a), _parts(b)
    if pa is None or pb is None:
        return False
    return pa > pb


def _parts(v: str) -> tuple[int, ...] | None:
    nums = re.findall(r"\d+", v or "")
    if not nums:
        return None
    out = [int(n) for n in nums[:4]]
    out += [0] * (4 - len(out))
    return tuple(out)


def _tree_hash(root: str) -> str | None:
    """A digest of the plugin's payload. None if the tree is too big to bother."""
    h = hashlib.sha256()
    files = 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name in SKIP_FILES or name.endswith((".pyc", ".pyo", ".log")):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            h.update(rel.encode("utf-8", "replace") + b"\0")
            try:
                with open(full, "rb") as fh:
                    while True:
                        chunk = fh.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                        total += len(chunk)
                        if total > MAX_BYTES:
                            return None
            except OSError:
                return None
            files += 1
            if files > MAX_FILES:
                return None
    return h.hexdigest() if files else None


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


# ==========================================================================
# Surfaces
# ==========================================================================


def banner_lines(state: dict | None) -> list[str]:
    """The terminal rendering. Same verdict, no browser required."""
    if not state:
        return []
    lines = ["", f"  ! {state['title']}.", f"    {state['detail']}", ""]
    lines += [f"    {c}" for c in state["commands"]]
    return lines


def marker_path(project: str) -> str:
    return os.path.join(
        os.path.abspath(project), ".claude", "branding", ".lookbook-resync.json"
    )


def write_marker(project: str, state: dict) -> str | None:
    """Leave the request where Claude will find it after the picker exits.

    The picker normally runs detached, so its stdout is a log file nobody
    reads. The filesystem is the only channel back.
    """
    path = marker_path(project)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = dict(state)
        payload["requestedAt"] = time.time()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, path)
        return path
    except OSError:
        return None
