#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Long lived engine. Same contract as the bridge, without paying the startup twice"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.engine import EXPECTED, handle_request
from core import library
from core.pipeline import INDEX_DIR, load_index

# one trace at a time. The engine is not reentrant in any interesting way and a
# walker clicking twice should uqeue, not race
_lock = threading.Lock()

# an uploaded fichier gpx is the only thing that makes a request big, and the engine caps
# those at eight megabytes, doubled here for the json escaping around it. Reading a
# Content-Length on trust is how a header that announces four gigabytes fills the
# memoire before anyone looks at the body
MAX_BODY = 16 * 1024 * 1024


def _plan(request):
    notes = []
    with _lock:
        result = handle_request(request, log=notes.append)

    for note in notes:
        print("   %s" % note, file=sys.stderr)
    return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return None

    def _reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if (self.close_connection):
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if (self.path.rstrip("/") != "/health"):
            self._reply(404, {"error": "chemin inconnu"})
            return

        zones = [{"name": e["name"], "label": e["label"], "bbox": list(e["bbox"])}
                 for e in library.available(INDEX_DIR)]
        self._reply(200, {"status": "pret", "zones": zones})

    def do_POST(self):
        # every early reply leaves the body unread, and on a kept alive connection the
        # next request would be parsed out of that body. Closing the socket avoids it
        if (self.path.rstrip("/") != "/route"):
            self.close_connection = True
            self._reply(404, {"error": "chemin inconnu"})
            return

        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.close_connection = True
            self._reply(400, {"error": "en-tete Content-Length illisible"})
            return

        if (size > MAX_BODY):
            self.close_connection = True
            self._reply(413, {"error": "requete trop volumineuse"})
            return

        try:
            request = json.loads(self.rfile.read(size) or b"{}")
        except ValueError as exc:
            self._reply(400, {"error": "requete illisible : %s" % exc})
            return

        started = time.perf_counter()
        try:
            result = _plan(request)
        except EXPECTED as exc:
            self._reply(422, {"error": str(exc)})
            return

        print("Trace en %.2f s : %.2f km" % (time.perf_counter() - started,
                                             result["stats"]["km"]), file=sys.stderr)
        self._reply(200, result)


def warm(log=print):
    """Loads indexes up front, the first walker should not pay for the others.

    Only as many as the memo keeps : past that, warming an index evicts one that
    was just warmed and the whole exercise buys nothing"""
    entries = library.available(INDEX_DIR)
    kept = load_index.cache_parameters()["maxsize"]
    if (kept is not None and len(entries) > kept):
        log("   %d index pour %d places, le reste se chargera a la demande"
            % (len(entries), kept))
        entries = entries[:kept]

    for entry in entries:
        started = time.perf_counter()
        load_index(entry["path"])
        log("   %s charge en %.1f s" % (entry["label"], time.perf_counter() - started))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cli.serve", description="Moteur resident pour l'interface web")
    parser.add_argument("-p", "--port", type=int, default=8765)
    # the loopback, tihs only ever speaks to a front running on the same machine and
    # never to a seperate host
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-warm", action="store_true",
                        help="ne pas precharger les index au demarrage")

    args = parser.parse_args(argv)

    if (not args.no_warm):
        print("Prechargement des index...")
        warm()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Moteur pret sur http://%s:%d" % (args.host, args.port))
    print("Ctrl+C pour arreter")

    interrupted = False
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        interrupted = True
    finally:
        server.server_close()

    if (interrupted):
        # a ctrl+c is how one stops a resident server, the shell wants the usual code
        print()
        print("Arret")
        return 130

    return 0


if (__name__ == "__main__"):
    raise SystemExit(main())
