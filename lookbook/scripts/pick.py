#!/usr/bin/env python3
"""lookbook -- pick a website's visual direction before any UI code is written.

Single entry point: CLI + local server. Python 3 stdlib only.

    pick.py --project <dir> [options]

      --print-url            print URL and exit, do not open a browser
      --force                re-pick even if a valid config exists
      --preset <name>        headless: write tokens without the UI
      --accent <#hex>        headless: override the preset accent
      --timeout <seconds>    server self-terminate, default 900
      --wait                 block until submission (humans only, not agents)
      --emit-html [path]     write a picker that needs no server, then exit
      --apply <blob>         write the config from a static picker's paste-back

    exit 0   valid config now exists, or the server is up and the result path
             is printed for the caller to poll
    exit 2   timed out or aborted by user
    exit 3   invalid arguments, unwritable project dir, or the server could
             not be started

The server binds 127.0.0.1, so the printed URL only works when the browser is
on the same machine. Over SSH it is not, and the run prints the `ssh -L` line
to fix that. Where no port can be forwarded at all -- a locked-down box, a
container that does not forward -- `--emit-html` drops the server entirely and
returns the result as a command to paste back.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import getpass
import hmac
import http.client
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resync  # noqa: E402
import schema  # noqa: E402

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(SKILL_ROOT, "assets", "ui")

PORT_START = 6780
PORT_END = 6799
DEFAULT_TIMEOUT = 900

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = 256 * 1024  # JSON submissions; uploads have their own cap

# The drift check walks two plugin trees. Cheap, but there is no reason to
# pay for it twice in one process, nor at all on the headless paths.
_RESYNC: dict = {}


def resync_state() -> dict | None:
    if "v" not in _RESYNC:
        _RESYNC["v"] = resync.check(SKILL_ROOT)
    return _RESYNC["v"]


EXIT_OK = 0
EXIT_ABORTED = 2
EXIT_BADARGS = 3


class LaunchError(RuntimeError):
    """The detached server could not be started."""

# Only these files are ever served. No directory walk, no traversal surface.
SERVABLE = {
    "/": "index.html",
    "/index.html": "index.html",
    "/logo.png": "logo.png",
    "/favicon.png": "favicon.png",
    "/favicon.ico": "favicon.png",
}

# Magic bytes, checked instead of the extension. (prefix, offset, ext, mime)
IMAGE_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", 0, ".png", "image/png"),
    (b"\xff\xd8\xff", 0, ".jpg", "image/jpeg"),
    (b"GIF87a", 0, ".gif", "image/gif"),
    (b"GIF89a", 0, ".gif", "image/gif"),
    (b"WEBP", 8, ".webp", "image/webp"),
]


# ==========================================================================
# Runtime state -- how the detached child reports back to the parent
# ==========================================================================


def runtime_path(project: str) -> str:
    return os.path.join(
        os.path.abspath(project), ".claude", "branding", ".lookbook-run.json"
    )


def log_path(project: str) -> str:
    return os.path.join(
        os.path.abspath(project), ".claude", "branding", ".lookbook-server.log"
    )


def read_runtime(project: str) -> dict | None:
    try:
        with open(runtime_path(project), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def write_runtime(project: str, data: dict) -> None:
    path = runtime_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)


def clear_runtime(project: str) -> None:
    try:
        os.remove(runtime_path(project))
    except OSError:
        pass


def server_alive(info: dict) -> bool:
    """Ping an advertised server. Confirms it is ours, not just a busy port."""
    if not info or not info.get("port") or not info.get("token"):
        return False
    try:
        conn = http.client.HTTPConnection("127.0.0.1", int(info["port"]), timeout=1.5)
        conn.request("GET", "/api/ping?t=" + info["token"])
        resp = conn.getresponse()
        body = resp.read(512)
        conn.close()
        if resp.status != 200:
            return False
        return json.loads(body.decode("utf-8")).get("launchId") == info.get("launchId")
    except Exception:
        return False


# ==========================================================================
# Where is the browser?
#
# The server binds 127.0.0.1. That address means "this machine", so the printed
# URL is only clickable when the browser runs on the same machine as the server.
#
#   local      terminal on your own laptop -- browser is right here, works
#   ssh        terminal on a remote box    -- browser is elsewhere, URL is dead
#   forwarded  a container or WSL          -- usually forwarded for you, maybe not
#
# Detection is one variable: SSH_CONNECTION. Everything it misses is what
# --emit-html exists for.
# ==========================================================================


def detect_location() -> tuple[str, dict]:
    """Returns (kind, details). kind is 'local', 'ssh' or 'forwarded'."""
    ssh = os.environ.get("SSH_CONNECTION", "").split()
    if len(ssh) >= 4:
        return "ssh", {"host": ssh[2], "port": ssh[3]}
    if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"):
        return "ssh", {}

    # Technically local, but the browser may still be across a boundary. These
    # hosts normally forward ports themselves; when they do not, the URL simply
    # fails to open and --emit-html is the way out.
    if os.environ.get("CODESPACES"):
        return "forwarded", {"what": "a GitHub Codespace"}
    if os.environ.get("REMOTE_CONTAINERS") or os.environ.get("DEVCONTAINER"):
        return "forwarded", {"what": "a dev container"}
    if os.path.exists("/.dockerenv"):
        return "forwarded", {"what": "a container"}
    if os.environ.get("WSL_DISTRO_NAME"):
        return "forwarded", {"what": "WSL"}
    return "local", {}


def access_lines(url: str, port: int, kind: str, details: dict) -> list[str]:
    """How this particular user actually reaches that URL."""
    if kind == "ssh":
        host = details.get("host", "<this-host>")
        ssh_port = details.get("port", "22")
        try:
            user = getpass.getuser()
        except Exception:
            user = "<user>"
        flag = "" if ssh_port in ("22", "") else f" -p {ssh_port}"
        lines = [
            "",
            "  This shell is over SSH, so 127.0.0.1 here is not 127.0.0.1 in your",
            "  browser. Forward the port first -- run this in a second terminal",
            "  on your own machine, and leave it running:",
            "",
            f"    ssh -N{flag} -L {port}:127.0.0.1:{port} {user}@{host}",
            "",
            "  Then open the URL above in your browser as normal.",
            "  (If you connected through VS Code or Cursor, the port is likely",
            "  already forwarded -- try the URL first.)",
            "",
            "  Cannot forward a port? Re-run with --emit-html for a picker file",
            "  that needs no server.",
        ]
        return lines

    if kind == "forwarded":
        what = details.get("what", "this environment")
        return [
            f"  ({what} usually forwards this port for you. If the URL does not",
            "   open, re-run with --emit-html for a picker that needs no server.)",
        ]
    return []


def print_resync() -> None:
    """The terminal surface. A browser is not the only place this shows up."""
    for line in resync.banner_lines(resync_state()):
        print(line)


# ==========================================================================
# Server
# ==========================================================================


class PickServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # a stale listener must not be silently adopted

    def __init__(self, addr, handler, *, project, token, launch_id):
        self.resync_ack = False
        super().__init__(addr, handler)
        self.project = project
        self.token = token
        self.launch_id = launch_id
        self.origins = {
            f"http://127.0.0.1:{addr[1]}",
            f"http://localhost:{addr[1]}",
        }
        self.result: dict | None = None
        self.done = threading.Event()


class PickHandler(BaseHTTPRequestHandler):
    server_version = "lookbook"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # -- plumbing ---------------------------------------------------------

    def log_message(self, fmt, *args):  # keep the console clean
        sys.stderr.write("[lookbook] %s %s\n" % (self.address_string(), fmt % args))

    def _send(self, status, body=b"", ctype="application/json", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, obj):
        self._send(status, json.dumps(obj), "application/json")

    def _fail(self, status, message):
        self._json(status, {"ok": False, "error": message})

    # -- guards -----------------------------------------------------------

    def _token_ok(self, query) -> bool:
        supplied = ""
        if "t" in query and query["t"]:
            supplied = query["t"][0]
        header = self.headers.get("X-Lookbook-Token")
        if header:
            supplied = header
        return hmac.compare_digest(supplied, self.server.token)

    def _origin_ok(self) -> bool:
        """Any page in the browser can reach 127.0.0.1. Only our own may talk."""
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self.server.origins:
            return False
        referer = self.headers.get("Referer")
        if referer:
            parsed = urlparse(referer)
            base = f"{parsed.scheme}://{parsed.netloc}"
            if base not in self.server.origins:
                return False
        # State-changing requests must prove same-origin, not merely not-cross.
        if self.command == "POST" and origin is None:
            return False
        return True

    def _drain(self) -> None:
        """Empty the request body even when the route ignores it.

        This is HTTP/1.1 with keep-alive. Bytes left unread do not vanish:
        they sit in the socket and the parser reads them as the start of
        the next request line, which turns a following POST into garbage
        like "{}POST /api/submit" and a 501. Any handler that does not
        call _read_body must call this.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return
        remaining = max(0, min(length, MAX_BODY_BYTES))
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                return
            remaining -= len(chunk)

    def _read_body(self, limit: int) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > limit:
            return None
        data = self.rfile.read(length)
        return data if len(data) == length else None

    # -- routes -----------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        path = parsed.path

        if not self._origin_ok():
            return self._fail(403, "cross-origin request rejected")
        if not self._token_ok(query):
            return self._fail(403, "bad or missing token")

        if path == "/api/ping":
            return self._json(200, {"ok": True, "launchId": self.server.launch_id})

        if path == "/api/presets":
            return self._json(
                200,
                {
                    "ok": True,
                    "presets": [
                        {
                            "name": name,
                            "label": p["label"],
                            "blurb": p["blurb"],
                            "mode": p["mode"],
                            "note": p.get("note"),
                            "family": p["family"],
                            "tokens": p["tokens"],
                            "altMode": p["altMode"],
                            "avoid": p["avoid"],
                        }
                        for name, p in schema.PRESETS.items()
                    ],
                    "project": os.path.basename(os.path.abspath(self.server.project))
                    or self.server.project,
                    "resync": resync_state(),
                },
            )

        filename = SERVABLE.get(path)
        if not filename:
            return self._fail(404, "not found")
        return self._serve_asset(filename)

    do_HEAD = do_GET

    def _serve_asset(self, filename: str):
        full = os.path.join(UI_DIR, filename)
        # Belt and braces: the name came from a fixed table, confirm it anyway.
        if os.path.dirname(os.path.abspath(full)) != os.path.abspath(UI_DIR):
            return self._fail(403, "forbidden")
        try:
            with open(full, "rb") as fh:
                body = fh.read()
        except OSError:
            return self._fail(404, "not found")
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        extra = {}
        if filename.endswith(".html"):
            ctype = "text/html; charset=utf-8"
            body = body.replace(b"__LOOKBOOK_TOKEN__", self.server.token.encode())
            body = body.replace(b"__LOOKBOOK_MODE__", b"server")
            body = body.replace(b"__LOOKBOOK_DATA__", b"null")
            extra["Content-Security-Policy"] = (
                "default-src 'none'; "
                "img-src 'self' data: blob:; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "script-src 'unsafe-inline'; "
                "connect-src 'self'; "
                "form-action 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
        return self._send(200, body, ctype, extra)

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if not self._origin_ok():
            return self._fail(403, "cross-origin request rejected")
        if not self._token_ok(query):
            return self._fail(403, "bad or missing token")

        if parsed.path == "/api/upload":
            return self._handle_upload()
        if parsed.path == "/api/submit":
            return self._handle_submit()
        if parsed.path == "/api/resync":
            return self._handle_resync()
        if parsed.path == "/api/cancel":
            self._drain()
            self._json(200, {"ok": True})
            self.server.result = None
            threading.Thread(target=self._stop, daemon=True).start()
            return
        return self._fail(404, "not found")

    def _handle_resync(self):
        """Record the request. Do NOT perform it.

        This process is executing out of the very directory a reinstall
        replaces, with .in_use held open beneath it. Self-replacement is how
        you get a half-written plugin and a Windows file lock. Claude runs
        the commands afterwards, from outside.
        """
        self._drain()
        state = resync_state()
        if not state:
            return self._fail(409, "nothing to resync")
        self.server.resync_ack = True
        resync.write_marker(self.server.project, state)
        return self._json(200, {"ok": True, "commands": state["commands"]})

    def _stop(self):
        time.sleep(0.3)  # let the response flush
        self.server.done.set()
        self.server.shutdown()

    # -- uploads ----------------------------------------------------------

    def _handle_upload(self):
        """Raw bytes, not multipart. The browser posts the ArrayBuffer directly,
        which keeps us clear of multipart parsing (and of `cgi`, gone in 3.13)."""
        data = self._read_body(MAX_UPLOAD_BYTES)
        if data is None:
            return self._fail(413, f"image must be under {MAX_UPLOAD_BYTES // 1024 // 1024} MB")

        ext = None
        for sig, offset, e, _mime in IMAGE_SIGNATURES:
            if data[offset : offset + len(sig)] == sig:
                ext = e
                break
        if ext is None:
            return self._fail(415, "not a PNG, JPEG, GIF or WebP image")

        # Generated name. The client's filename never touches a path.
        name = secrets.token_hex(2) + ext
        dest_dir = schema.refs_dir(self.server.project)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, name)
        while os.path.exists(dest):
            name = secrets.token_hex(3) + ext
            dest = os.path.join(dest_dir, name)
        with open(dest, "wb") as fh:
            fh.write(data)

        rel = os.path.join(schema.REFS_RELDIR, name).replace(os.sep, "/")
        return self._json(200, {"ok": True, "path": rel, "bytes": len(data)})

    # -- submit -----------------------------------------------------------

    def _handle_submit(self):
        raw = self._read_body(MAX_BODY_BYTES)
        if raw is None:
            return self._fail(413, "payload too large")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._fail(400, "body must be JSON")
        if not isinstance(payload, dict):
            return self._fail(400, "body must be a JSON object")

        refs = []
        for ref in payload.get("references") or []:
            if not isinstance(ref, dict):
                continue
            path = str(ref.get("path", ""))
            # Only paths we generated, inside the project's refs dir.
            if not path.startswith(schema.REFS_RELDIR.replace(os.sep, "/") + "/"):
                continue
            if ".." in path:
                continue
            refs.append(
                {"path": path, "note": str(ref.get("note", "")).strip()[:400]}
            )

        try:
            doc = schema.build_config(
                preset=str(payload.get("preset", "")),
                accent=payload.get("accent") or None,
                tokens_override=payload.get("tokens")
                if isinstance(payload.get("tokens"), dict)
                else None,
                avoid_extra=[
                    str(a)[:200] for a in (payload.get("avoid") or [])[:40]
                ],
                references=refs,
                notes=str(payload.get("notes", ""))[:4000] or None,
            )
            path = schema.write_config(self.server.project, doc)
        except schema.SchemaError as exc:
            return self._fail(400, str(exc))
        except OSError as exc:
            return self._fail(500, f"could not write config: {exc}")

        self.server.result = doc
        self._json(200, {"ok": True, "path": path, "preset": doc["preset"]})
        threading.Thread(target=self._stop, daemon=True).start()


def bind_server(project: str, token: str, launch_id: str) -> PickServer:
    """Walk 6780..6799. Two projects open at once is a normal Tuesday."""
    last = None
    for port in range(PORT_START, PORT_END + 1):
        try:
            return PickServer(
                ("127.0.0.1", port),
                PickHandler,
                project=project,
                token=token,
                launch_id=launch_id,
            )
        except OSError as exc:
            last = exc
            continue
    raise LaunchError(
        f"every port from {PORT_START} to {PORT_END} is busy ({last}). "
        "Close another lookbook picker, or wait for one to time out."
    )


def serve(project: str, token: str, launch_id: str, timeout: int) -> int:
    """Run the server until submission or timeout. Returns an exit code."""
    try:
        httpd = bind_server(project, token, launch_id)
    except LaunchError as exc:
        sys.stderr.write(f"lookbook: {exc}\n")
        return EXIT_BADARGS
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/?t={token}"

    write_runtime(
        project,
        {
            "launchId": launch_id,
            "port": port,
            "token": token,
            "url": url,
            "pid": os.getpid(),
            "startedAt": time.time(),
            "timeout": timeout,
            "resultPath": schema.config_path(project),
        },
    )

    def guillotine():
        # An abandoned run must not leave a listener open on someone's laptop.
        if not httpd.done.wait(timeout):
            httpd.done.set()
            httpd.shutdown()

    threading.Thread(target=guillotine, daemon=True).start()

    try:
        httpd.serve_forever(poll_interval=0.4)
    finally:
        httpd.server_close()
        clear_runtime(project)

    return EXIT_OK if httpd.result is not None else EXIT_ABORTED


def spawn_detached(project: str, token: str, launch_id: str, timeout: int) -> dict:
    """Fork the server off, then wait for it to report the port it actually got.

    Agent bash calls time out around two minutes; a server that blocks while a
    human fiddles with colour pickers gets killed mid-thought. So the result
    comes back through the filesystem, not through this process.
    """
    clear_runtime(project)
    os.makedirs(os.path.dirname(runtime_path(project)), exist_ok=True)

    # `--opt=value`, never `--opt value`: a urlsafe token can begin with "-",
    # and argparse would read that as the next flag rather than as this one's
    # value. Roughly one launch in sixty-four, which is exactly the kind of
    # failure that looks random.
    cmd = [
        sys.executable,
        os.path.abspath(__file__),
        f"--project={os.path.abspath(project)}",
        "--serve",
        f"--token={token}",
        f"--launch-id={launch_id}",
        f"--timeout={timeout}",
    ]

    kwargs: dict = {"cwd": os.path.abspath(project), "close_fds": True}
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = (
            DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True

    logfile = open(log_path(project), "ab", buffering=0)
    try:
        subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=logfile, stderr=logfile, **kwargs
        )
    finally:
        logfile.close()

    deadline = time.time() + 15
    while time.time() < deadline:
        info = read_runtime(project)
        if info and info.get("launchId") == launch_id:
            return info
        time.sleep(0.15)

    # The child failed before it could advertise itself. Its complaint is in the
    # log; surfacing it beats making the user go and read the file.
    reason = ""
    try:
        with open(log_path(project), "r", encoding="utf-8", errors="replace") as fh:
            tail = [ln.strip() for ln in fh.readlines()[-12:] if ln.strip()]
        reason = next((ln for ln in reversed(tail) if "lookbook:" in ln or "no free port" in ln), "")
        reason = reason or (tail[-1] if tail else "")
    except OSError:
        pass

    raise LaunchError(
        "the picker server did not start within 15s."
        + (f"\n  {reason}" if reason else "")
        + f"\n  Full log: {log_path(project)}"
    )


# ==========================================================================
# No-server path: a static picker plus a paste-back command
#
# Port forwarding is not always possible or wanted. This writes a single
# self-contained HTML file with the same UI, which the user opens however they
# can get at it. Since the page cannot reach back, it hands them a command to
# paste into the terminal they already have open.
# ==========================================================================


def ui_source() -> str:
    with open(os.path.join(UI_DIR, "index.html"), "r", encoding="utf-8") as fh:
        return fh.read()


def _data_uri(filename: str) -> str:
    with open(os.path.join(UI_DIR, filename), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")


def render_ui(mode: str, token: str, data: dict | None) -> str:
    html = ui_source()

    if mode == "static":
        # Opened from the filesystem, so "/logo.png" resolves to nothing. The
        # images have to travel inside the file.
        for name in ("logo.png", "favicon.png"):
            html = html.replace(f"/{name}?t=__LOOKBOOK_TOKEN__", _data_uri(name))

    html = html.replace("__LOOKBOOK_TOKEN__", token)
    html = html.replace("__LOOKBOOK_MODE__", mode)
    html = html.replace(
        "__LOOKBOOK_DATA__",
        json.dumps(data, ensure_ascii=False) if data is not None else "null",
    )
    return html


def emit_html(project: str, dest: str) -> str:
    """Write the self-contained picker. Returns the path written."""
    script = os.path.abspath(__file__)
    data = {
        "presets": [
            {
                "name": name,
                "label": p["label"],
                "blurb": p["blurb"],
                "mode": p["mode"],
                "note": p.get("note"),
                "family": p["family"],
                "tokens": p["tokens"],
                "altMode": p["altMode"],
                "avoid": p["avoid"],
            }
            for name, p in schema.PRESETS.items()
        ],
        "project": os.path.basename(project) or project,
        "command": f'python "{script}" --project "{project}" --apply ',
        "resync": resync_state(),
    }
    html = render_ui("static", "static", data)

    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(html)
    return dest


def apply_blob(project: str, blob: str) -> dict:
    """Decode what the static picker handed back and write the config."""
    text = blob.strip().strip("'\"")
    padded = text + "=" * (-len(text) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise schema.SchemaError(
            f"could not read that --apply value ({exc}). Copy the whole command "
            "the picker showed, including the long token at the end."
        ) from None
    if not isinstance(payload, dict):
        raise schema.SchemaError("--apply payload is not an object")

    doc = schema.build_config(
        preset=str(payload.get("preset", "")),
        accent=payload.get("accent") or None,
        tokens_override=payload.get("tokens")
        if isinstance(payload.get("tokens"), dict)
        else None,
        avoid_extra=[str(a)[:200] for a in (payload.get("avoid") or [])[:40]],
        references=[],
        notes=str(payload.get("notes", ""))[:4000] or None,
    )
    schema.write_config(project, doc)
    return doc


# ==========================================================================
# CLI
# ==========================================================================


class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"lookbook: {message}\n")
        self.print_usage(sys.stderr)
        raise SystemExit(EXIT_BADARGS)


def build_parser() -> Parser:
    p = Parser(prog="pick.py", description="Pick a visual direction, write .claude/branding.json")
    p.add_argument("--project", required=True, help="project directory to write into")
    p.add_argument("--print-url", action="store_true", help="print URL, do not open a browser")
    p.add_argument("--force", action="store_true", help="re-pick even if a valid config exists")
    p.add_argument("--preset", help="headless: write tokens without the UI")
    p.add_argument("--accent", help="headless: override the preset accent")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="server self-terminate seconds")
    p.add_argument("--wait", action="store_true", help="block until submission (humans only)")
    p.add_argument("--emit-html", nargs="?", const="", metavar="PATH",
                   help="write a self-contained picker that needs no server, and exit "
                        "(default path: .claude/lookbook-picker.html)")
    p.add_argument("--apply", metavar="BLOB",
                   help="write the config from a static picker's paste-back value")
    # internal: the detached child re-enters here
    p.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--token", help=argparse.SUPPRESS)
    p.add_argument("--launch-id", help=argparse.SUPPRESS)
    return p


def check_project(path: str) -> str | None:
    """Returns an error string, or None if the directory is usable."""
    abspath = os.path.abspath(path)
    if not os.path.isdir(abspath):
        return f"not a directory: {abspath}"
    if not os.access(abspath, os.W_OK | os.X_OK):
        return f"not writable: {abspath}"
    return None


def report_existing(project: str, config: dict) -> None:
    print(f"lookbook: {schema.config_path(project)} already exists and is valid.")
    print(f"  preset: {config['preset']}   accent: {config['tokens']['color']['accent']}")
    print("  Re-run with --force to pick again.")
    print_resync()
    print(f"RESULT: {schema.config_path(project)}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    err = check_project(args.project)
    if err:
        sys.stderr.write(f"lookbook: {err}\n")
        return EXIT_BADARGS
    project = os.path.abspath(args.project)

    if args.timeout <= 0:
        sys.stderr.write("lookbook: --timeout must be positive\n")
        return EXIT_BADARGS

    # Internal re-entry from spawn_detached.
    if args.serve:
        if not args.token or not args.launch_id:
            return EXIT_BADARGS
        return serve(project, args.token, args.launch_id, args.timeout)

    # ---- Paste-back from a static picker. ----
    # An explicit human action: they picked, then pasted. Writing is the whole
    # point, so this does not stop for an existing config -- but it says what
    # it replaced.
    if args.apply:
        previous = schema.read_config(project)
        try:
            doc = apply_blob(project, args.apply)
        except schema.SchemaError as exc:
            sys.stderr.write(f"lookbook: {exc}\n")
            return EXIT_BADARGS
        except OSError as exc:
            sys.stderr.write(f"lookbook: could not write config: {exc}\n")
            return EXIT_BADARGS
        if previous:
            print(f"lookbook: replaced the {previous['preset']} config.")
        print(f"lookbook: wrote {doc['preset']} tokens")
        print(f"  accent: {doc['tokens']['color']['accent']}")
        print(f"RESULT: {schema.config_path(project)}")
        return EXIT_OK

    # ---- Static picker, for when no port can be forwarded. ----
    if args.emit_html is not None:
        dest = args.emit_html or os.path.join(project, ".claude", "lookbook-picker.html")
        try:
            written = emit_html(project, dest)
        except OSError as exc:
            sys.stderr.write(f"lookbook: could not write {dest}: {exc}\n")
            return EXIT_BADARGS
        kind, _details = detect_location()
        print(f"lookbook: wrote a self-contained picker to\n  {written}")
        print("\n  It needs no server and no forwarded port. Open it in a browser:")
        if kind == "ssh":
            print(f"    scp {getpass.getuser()}@<host>:'{written}' . && open ./"
                  + os.path.basename(written))
            print("  or open it through your editor's remote file browser.")
        else:
            print(f"    open {written}   (or double-click it)")
        print("\n  Pick a direction, then paste the command it gives you back into")
        print("  this terminal. That is what writes the config.")
        print(f"RESULT: {schema.config_path(project)}")
        return EXIT_OK

    if args.preset and args.preset not in schema.PRESETS:
        sys.stderr.write(
            f"lookbook: unknown preset {args.preset!r}; "
            f"expected one of {', '.join(schema.PRESET_NAMES)}\n"
        )
        return EXIT_BADARGS
    if args.accent:
        try:
            schema.normalize_hex(args.accent, "--accent")
        except schema.SchemaError as exc:
            sys.stderr.write(f"lookbook: {exc}\n")
            return EXIT_BADARGS
    if args.accent and not args.preset:
        sys.stderr.write("lookbook: --accent requires --preset\n")
        return EXIT_BADARGS

    # ---- Idempotence. The single most important property in this file. ----
    # Without it every caller's run pops a browser window and the skill gets
    # uninstalled within a week.
    if not args.force:
        existing = schema.read_config(project)
        if existing is not None:
            report_existing(project, existing)
            return EXIT_OK

    # ---- Headless ----
    if args.preset:
        try:
            doc = schema.build_config(args.preset, accent=args.accent)
            path = schema.write_config(project, doc)
        except schema.SchemaError as exc:
            sys.stderr.write(f"lookbook: {exc}\n")
            return EXIT_BADARGS
        except OSError as exc:
            sys.stderr.write(f"lookbook: could not write config: {exc}\n")
            return EXIT_BADARGS
        print(f"lookbook: wrote {args.preset} tokens")
        print(f"  accent: {doc['tokens']['color']['accent']}")
        print_resync()
        print(f"RESULT: {path}")
        return EXIT_OK

    # ---- UI ----
    if args.wait:
        # Humans only. Agents must never take this path -- their bash call dies
        # at ~2 minutes and takes the server with it.
        token = secrets.token_urlsafe(24)
        launch_id = secrets.token_hex(8)
        try:
            httpd = bind_server(project, token, launch_id)
        except LaunchError as exc:
            sys.stderr.write(f"lookbook: {exc}\n")
            return EXIT_BADARGS
        port = httpd.server_address[1]
        url = f"http://127.0.0.1:{port}/?t={token}"
        kind, details = detect_location()
        print(f"lookbook: open {url}")
        for line in access_lines(url, port, kind, details):
            print(line)
        print_resync()
        print(f"RESULT: {schema.config_path(project)}")
        # Opening a browser on the box the user is SSH'd into helps nobody.
        if not args.print_url and kind == "local":
            webbrowser.open(url)

        def guillotine():
            if not httpd.done.wait(args.timeout):
                httpd.done.set()
                httpd.shutdown()

        threading.Thread(target=guillotine, daemon=True).start()
        write_runtime(
            project,
            {
                "launchId": launch_id,
                "port": port,
                "token": token,
                "url": url,
                "pid": os.getpid(),
                "startedAt": time.time(),
                "timeout": args.timeout,
                "resultPath": schema.config_path(project),
            },
        )
        try:
            httpd.serve_forever(poll_interval=0.4)
        except KeyboardInterrupt:
            print("\nlookbook: aborted")
        finally:
            httpd.server_close()
            clear_runtime(project)
        if httpd.resync_ack:
            print(f"lookbook: resync requested -> {resync.marker_path(project)}")
        if httpd.result is not None:
            print(f"lookbook: wrote {schema.config_path(project)}")
            return EXIT_OK
        print("lookbook: no selection made", file=sys.stderr)
        return EXIT_ABORTED

    # Poll mode: reuse a live server for this project rather than stacking up
    # a new one every time an agent re-runs the command.
    kind, details = detect_location()

    info = read_runtime(project)
    if info and server_alive(info):
        print("lookbook: a picker is already running for this project.")
        print(f"  URL: {info['url']}")
        for line in access_lines(info["url"], int(info["port"]), kind, details):
            print(line)
        print_resync()
        print(f"RESULT: {info['resultPath']}")
        return EXIT_OK

    token = secrets.token_urlsafe(24)
    launch_id = secrets.token_hex(8)
    try:
        info = spawn_detached(project, token, launch_id, args.timeout)
    except LaunchError as exc:
        sys.stderr.write(f"lookbook: {exc}\n")
        return EXIT_BADARGS

    print("lookbook: picker running. Open this and choose a direction:")
    print(f"  URL: {info['url']}")
    print(f"  expires in {args.timeout}s")
    for line in access_lines(info["url"], int(info["port"]), kind, details):
        print(line)
    print_resync()
    print(f"RESULT: {info['resultPath']}")
    # Opening a browser on the box the user is SSH'd into helps nobody.
    if not args.print_url and kind == "local":
        webbrowser.open(info["url"])
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(EXIT_ABORTED)
