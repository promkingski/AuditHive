#!/usr/bin/env python3
"""AuditHive live dashboard server (Python stdlib only).

Serves the dashboard UI, the current run's status.json, per-agent model info
parsed from agent frontmatter, and the generated audit-output reports. Also
accepts config writes and surgical per-agent model edits from the launcher GUI.

Usage:
    python serve.py [AGENTS_DIR] [--port N]

AGENTS_DIR defaults to C:\\Users\\carte\\.claude\\agents.
The working directory (os.getcwd()) is treated as the audit working directory:
audithive.config.json and audit-output/ are read/written there.
"""

import json
import os
import re
import sys
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Configuration -----------------------------------------------------------

DEFAULT_AGENTS_DIR = r"C:\Users\carte\.claude\agents"
ALLOWED_MODELS = ("haiku", "sonnet", "opus", "fable")
PREFERRED_PORTS = list(range(8787, 8800))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_HTML = os.path.join(SCRIPT_DIR, "dashboard.html")

AGENTS_DIR = DEFAULT_AGENTS_DIR
WORK_DIR = os.getcwd()


# --- Frontmatter helpers -----------------------------------------------------

def _frontmatter_bounds(lines):
    """Return (start, end) line indices of the frontmatter body (between the
    opening and closing '---' fences), or (None, None) if there is no block."""
    if not lines or lines[0].strip() != "---":
        return None, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return 1, i  # body is lines[1:i]; closing fence at i
    return None, None


def read_agent_model(path):
    """Parse the `model:` value from an agent .md frontmatter. None if absent."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    start, end = _frontmatter_bounds(lines)
    if start is None:
        return None
    for ln in lines[start:end]:
        m = re.match(r"^\s*model:\s*(.+?)\s*$", ln)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def read_agent_name(path):
    """Parse the `name:` value, falling back to the filename stem."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = []
    start, end = _frontmatter_bounds(lines)
    if start is not None:
        for ln in lines[start:end]:
            m = re.match(r"^\s*name:\s*(.+?)\s*$", ln)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return os.path.splitext(os.path.basename(path))[0]


def list_agents():
    """Return {agent-name: model-or-null} for every .md in the agents dir."""
    out = {}
    if not os.path.isdir(AGENTS_DIR):
        return out
    for fn in sorted(os.listdir(AGENTS_DIR)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(AGENTS_DIR, fn)
        out[read_agent_name(path)] = read_agent_model(path)
    return out


def agent_path_by_name(name):
    """Find the .md file whose frontmatter name (or filename) matches `name`."""
    if not os.path.isdir(AGENTS_DIR):
        return None
    # Prefer exact filename match, then frontmatter-name match.
    direct = os.path.join(AGENTS_DIR, name + ".md")
    if os.path.isfile(direct):
        return direct
    for fn in sorted(os.listdir(AGENTS_DIR)):
        if fn.endswith(".md") and read_agent_name(os.path.join(AGENTS_DIR, fn)) == name:
            return os.path.join(AGENTS_DIR, fn)
    return None


def set_agent_model(name, model):
    """Surgically edit only the `model:` frontmatter line of one agent file.

    - Validates model against the allowlist.
    - Writes a one-time <file>.bak backup before the first modification.
    - Adds a model line to the frontmatter if none exists (rather than
      rewriting the file). Never touches content below the frontmatter.

    Returns (ok, message).
    """
    if model not in ALLOWED_MODELS:
        return False, "model '%s' not in allowlist %s" % (model, list(ALLOWED_MODELS))
    path = agent_path_by_name(name)
    if not path:
        return False, "agent '%s' not found" % name

    with open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    # Preserve the file's newline style.
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)

    start, end = _frontmatter_bounds(lines)
    if start is None:
        return False, "no frontmatter block in %s" % os.path.basename(path)

    # One-time backup.
    bak = path + ".bak"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    replaced = False
    for i in range(start, end):
        if re.match(r"^\s*model:\s*", lines[i]):
            lines[i] = "model: " + model
            replaced = True
            break
    if not replaced:
        # Insert just before the closing fence.
        lines.insert(end, "model: " + model)

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nl.join(lines))
    action = "updated" if replaced else "added"
    return True, "%s model line in %s -> %s" % (action, os.path.basename(path), model)


# --- HTTP handler ------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "AuditHive/1.0"

    def log_message(self, fmt, *args):  # quieter logging
        sys.stderr.write("[dashboard] " + (fmt % args) + "\n")

    # -- helpers --
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            self._send(404, {"error": "not found: %s" % path})
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            return None

    @staticmethod
    def _guess_ctype(path):
        ext = os.path.splitext(path)[1].lower()
        return {
            ".html": "text/html; charset=utf-8",
            ".htm": "text/html; charset=utf-8",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".css": "text/css",
            ".js": "text/javascript",
            ".md": "text/markdown; charset=utf-8",
        }.get(ext, "application/octet-stream")

    # -- GET --
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html", "/dashboard.html"):
            self._send_file(DASHBOARD_HTML, "text/html; charset=utf-8")
            return

        if path == "/status":
            sp = os.path.join(WORK_DIR, "audit-output", "status.json")
            if os.path.isfile(sp):
                self._send_file(sp, "application/json")
            else:
                self._send(200, {"phase": None})
            return

        if path == "/agents":
            self._send(200, list_agents())
            return

        if path.startswith("/audit-output/"):
            # Serve any report / screenshot artifact, guarding against traversal.
            rel = path[len("/audit-output/"):]
            base = os.path.join(WORK_DIR, "audit-output")
            full = os.path.normpath(os.path.join(base, rel))
            if not full.startswith(os.path.normpath(base)):
                self._send(403, {"error": "forbidden"})
                return
            self._send_file(full, self._guess_ctype(full))
            return

        self._send(404, {"error": "no route %s" % path})

    # -- POST --
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        body = self._read_body()
        if body is None:
            self._send(400, {"error": "invalid JSON body"})
            return

        if path == "/config":
            # Whitelist known keys; ignore anything unexpected.
            cfg = {}
            for key in ("disabled_agents", "industry", "viewports", "html_report"):
                if key in body:
                    cfg[key] = body[key]
            dest = os.path.join(WORK_DIR, "audithive.config.json")
            try:
                with open(dest, "w", encoding="utf-8") as fh:
                    json.dump(cfg, fh, indent=2)
            except OSError as exc:
                self._send(500, {"error": str(exc)})
                return
            self._send(200, {"ok": True, "wrote": dest, "config": cfg})
            return

        if path == "/models":
            if not isinstance(body, dict) or not body:
                self._send(400, {"error": "expected {agent: model} object"})
                return
            results = {}
            all_ok = True
            for name, model in body.items():
                ok, msg = set_agent_model(name, model)
                results[name] = {"ok": ok, "detail": msg}
                all_ok = all_ok and ok
            self._send(200 if all_ok else 207,
                       {"ok": all_ok, "results": results, "agents": list_agents()})
            return

        self._send(404, {"error": "no route %s" % path})


# --- Boot --------------------------------------------------------------------

def pick_port(preferred):
    for p in preferred:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    # Fall back to an ephemeral port.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main(argv):
    global AGENTS_DIR
    port = None
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--port":
            i += 1
            port = int(argv[i])
        elif a.startswith("--port="):
            port = int(a.split("=", 1)[1])
        else:
            positional.append(a)
        i += 1
    if positional:
        AGENTS_DIR = positional[0]

    if port is None:
        port = pick_port(PREFERRED_PORTS)

    os.makedirs(os.path.join(WORK_DIR, "audit-output"), exist_ok=True)
    url = "http://localhost:%d/" % port
    # Record the URL so the orchestrator can open the right port.
    try:
        with open(os.path.join(WORK_DIR, "audit-output", ".dashboard-url"), "w",
                  encoding="utf-8") as fh:
            fh.write(url)
    except OSError:
        pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("AuditHive dashboard: %s" % url, flush=True)
    print("  agents dir : %s" % AGENTS_DIR, flush=True)
    print("  working dir: %s" % WORK_DIR, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    main(sys.argv[1:])
