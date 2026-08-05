#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""On disk memo of elevation samples, keyed on the coordinate itself"""

import os

# a browser build has no sqlite and no disk to put one on. The memo is an accelerator
# its absence costs calls to the elevation api and nothing else
try:
    import sqlite3
    Error = sqlite3.Error
    AVAILABLE = True
except ImportError:
    sqlite3 = None
    AVAILABLE = False

    class Error(Exception):
        pass

# a tenth of a metre. Quantising hrder would move points across the dem grid
PRECISION = 6

SCHEMA = """
CREATE TABLE IF NOT EXISTS sample (
    lat INTEGER NOT NULL,
    lon INTEGER NOT NULL,
    ele REAL NOT NULL,
    PRIMARY KEY (lat, lon)
)
"""

WANTED = "CREATE TEMP TABLE IF NOT EXISTS wanted (lat INTEGER, lon INTEGER)"


def key(point):
    scale = 10 ** PRECISION
    return (int(round(point[0] * scale)), int(round(point[1] * scale)))


class Cache:
    """Sqlite rather than a json blob : the web front spawns one process per trace,
    and two of them landing at once must not shred each other's fichier"""

    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(path)
        if (folder):
            os.makedirs(folder, exist_ok=True)  

        # two traces landing at once must queue on the write lock, not explode. Wal
        # serves reads during someone else's write
        self._link = sqlite3.connect(path, timeout=30.0)
        self._link.execute("PRAGMA journal_mode=WAL")
        self._link.execute(SCHEMA)
        self._link.commit()

    def lookup(self, points):
        """Heights already known, keyed the same way as the caller's points.

        An IN list would mean pasting placeholders into the sql text and chunking
        around the bound variable ceiling. A temp table and a join dodge both"""
        found = {}
        if (not points):
            return found

        self._link.execute(WANTED)
        self._link.execute("DELETE FROM wanted")
        self._link.executemany("INSERT INTO wanted (lat, lon) VALUES (?, ?)",
                               [key(p) for p in points])

        rows = self._link.execute( 
            "SELECT s.lat, s.lon, s.ele FROM sample s "
            "JOIN wanted w ON s.lat = w.lat AND s.lon = w.lon")

        for lat, lon, ele in rows:
            found[(lat, lon)] = ele

        return found

    def store(self, pairs):
        """pairs is a sequence of (point, height)"""
        if (not pairs):
            return 0

        rows = [(key(p)[0], key(p)[1], float(h)) for p, h in pairs]
        self._link.executemany(
            "INSERT OR REPLACE INTO sample (lat, lon, ele) VALUES (?, ?, ?)", rows)
        self._link.commit()
        return len(rows)

    def count(self):
        return self._link.execute("SELECT COUNT(*) FROM sample").fetchone()[0]

    def close(self):
        self._link.close()
