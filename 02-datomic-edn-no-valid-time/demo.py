"""Alice's risk rating in Datomic as it comes: system time only, no valid time modelled.
Q2 (what did we believe then?) is free; Q1 (what was true then?) cannot be asked.

All Datomic code (schema, transactions, queries) lives in bank.edn. This script only replays the
story: it sends forms from that file to Datomic Pro's bundled REST server (bin/rest) and picks
the database value each query runs against.

Run:  docker compose up -d --wait && python demo.py   (add --no-pause to run straight through)
"""
import datetime as dt
import pathlib
import re
import sys
import uuid

import edn_format
import requests

BASE = "http://localhost:8997"
DB = f"bank-{uuid.uuid4().hex[:8]}"  # a fresh in-memory database on every run
PAUSE = sys.stdin.isatty() and "--no-pause" not in sys.argv
EDN = {"Accept": "application/edn"}
SOURCE = pathlib.Path(__file__).with_name("bank.edn").read_text()


def form(key):
    """Source text of the form stored under `key` in bank.edn, exactly as written there."""
    start = re.search(rf"(?m)^[{{ ]*:{key}\b.*\n?\s*", SOURCE).end()
    i, depth = start, 0
    while True:
        c = SOURCE[i]
        if c == '"':
            i = SOURCE.index('"', i + 1)  # bank.edn has no escaped quotes
        elif c == ";":
            i = SOURCE.index("\n", i)
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    indent = start - SOURCE.rindex("\n", 0, start) - 1
    return "\n".join(line[indent:] if n else line
                     for n, line in enumerate(SOURCE[start:i + 1].split("\n")))


def step(title):
    if PAUSE:
        input("\n[enter] ")
    print(f"\n\033[1m=== {title}\033[0m\n")


def db(**opts):
    """A database *value*, as EDN: db() is now, db(as_of=...) is the past."""
    opts = "".join(f" :{k.replace('_', '-')} {v}" for k, v in opts.items())
    return f'{{:db/alias "mem/{DB}"{opts}}}'


def transact(key):
    print(f"\033[2m;; {key}\n{form(key)}\033[0m\n")
    r = requests.post(f"{BASE}/data/mem/{DB}/", data={"tx-data": form(key)}, headers=EDN)
    assert r.ok, r.text


def query(key, cols, *args):
    print(f"\033[2m;; {key}\n;; args: {' '.join(args)}\033[0m\n")
    r = requests.get(f"{BASE}/api/query", params={"q": form(key), "args": f"[{' '.join(args)}]"},
                     headers=EDN)
    assert r.ok, r.text
    rows = [[v.strftime("%Y-%m-%d %H:%M") if isinstance(v, dt.datetime) else str(v) for v in row]
            for row in edn_format.loads(r.text)]
    w = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
    for r in [cols, ["-" * n for n in w], *rows]:
        print("  " + " | ".join(v.ljust(n) for v, n in zip(r, w)))
    print()


requests.post(f"{BASE}/data/mem/", data={"db-name": DB}, headers=EDN).raise_for_status()

step("Schema")
transact("schema")

step("2026-01-01  the bank records Alice as LOW risk")
transact("record-alice")

step("2026-01-10  the bank approves a loan, based on LOW")

step("2026-01-15  the bank discovers Alice should have been HIGH since 2026-01-01")
transact("correct-alice")

step("The query")
print(f"\033[2m;; rating\n{form('rating')}\033[0m")

step("Q2: what did we believe on 2026-01-10?  The database as of then: built in")
query("rating", ["_id", "name", "risk_rating"], db(as_of='#inst "2026-01-10T12:00:00Z"'))

step("Q1: what do we now believe was true on 2026-01-10?  Can't be asked: the query has no date in it")
print("  The closest is what we believe now, which is about now, not about 2026-01-10:\n")
query("rating", ["_id", "name", "risk_rating"], db())
print("  HIGH matches Q1 only because the correction still holds today. There is no date to pass:\n"
      "  asked about 2025-12-31, before Alice was a customer, this is still the only query, and it\n"
      "  still says HIGH.\n")

step("... and the database's own history says Alice became HIGH on 2026-01-15, not 2026-01-01")
print(f"\033[2m;; rating-since\n{form('rating-since')}\033[0m")
query("rating-since", ["_id", "name", "risk_rating", "since"], db(history="true"))
print("  Answering Q1 means modelling valid time yourself: see 02-datomic-edn.")
