"""LAB SITE -- stands in for the real Windows IIS site and the real Java (Tomcat) app, until the
AWS Windows and Linux machines exist. It is a small always-on HTTPS server per target that watches
its certificate/key files and reloads its TLS context when they change, so "activate" in the
adapters below does not need a process restart -- the same principle as an IIS binding update or an
Apache graceful reload (FR-DEP-007: activate without a restart wherever possible).

Two endpoints run here:
  https://127.0.0.1:8443  (SNI web01.lab.example.com)  -- stands in for the Windows/IIS target
  https://127.0.0.1:8445  (SNI api.lab.example.com)     -- stands in for the Java/Tomcat target

Run:  python lab_site/server.py
"""
import http.server
import ssl
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CERTS = HERE / "certs"
CERTS.mkdir(exist_ok=True)

TARGETS = {
    8443: {"cert": CERTS / "win01.pem", "key": CERTS / "win01.key.pem", "sni": "web01.lab.example.com"},
    8445: {"cert": CERTS / "api.pem", "key": CERTS / "api.key.pem", "sni": "api.lab.example.com"},
}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        body = f"CDM lab site OK on port {self.server.server_port}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ReloadingHTTPSServer(http.server.ThreadingHTTPServer):
    def __init__(self, port, cert_path, key_path):
        super().__init__(("127.0.0.1", port), Handler)
        self._cert_path = cert_path
        self._key_path = key_path
        self._mtime = None
        self._reload()

    def _reload(self):
        # Build a fresh SSL context from the current cert/key files. get_request() below wraps
        # each new connection with whatever context is current, so a reload takes effect on the
        # very next connection with no process restart -- the same effect as an IIS binding
        # update or an Apache graceful reload (FR-DEP-007).
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(self._cert_path), keyfile=str(self._key_path))
        self._context = ctx

    def get_request(self):
        newsock, addr = self.socket.accept()
        wrapped = self._context.wrap_socket(newsock, server_side=True)
        return wrapped, addr

    def watch_and_reload(self, poll_seconds=1.5):
        def loop():
            while True:
                try:
                    m = self._cert_path.stat().st_mtime
                    if m != self._mtime:
                        self._mtime = m
                        self._reload()
                        print(f"[lab_site:{self.server_port}] reloaded certificate ({self._cert_path.name})")
                except FileNotFoundError:
                    pass
                time.sleep(poll_seconds)
        t = threading.Thread(target=loop, daemon=True)
        t.start()


def _bootstrap_placeholder(cert_path: Path, key_path: Path, cn: str):
    """If no certificate exists yet (first run before seed.py), create a throwaway one so the
    server can start; seed.py / adapters overwrite this immediately after."""
    if cert_path.exists() and key_path.exists():
        return
    import sys
    sys.path.insert(0, str(HERE.parent))
    from ca_simulator.certs import issue_certificate, cert_to_pem, key_to_pem
    key, cert = issue_certificate(cn, [cn], valid_days=1)
    cert_path.write_text(cert_to_pem(cert))
    key_path.write_text(key_to_pem(key))


def run():
    servers = []
    for port, t in TARGETS.items():
        _bootstrap_placeholder(t["cert"], t["key"], t["sni"])
        srv = ReloadingHTTPSServer(port, t["cert"], t["key"])
        srv.watch_and_reload()
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        print(f"lab_site listening on https://127.0.0.1:{port}/  (stands in for: {t['sni']})")
    print("Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
