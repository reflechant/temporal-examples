"""Credit file in Datomic: system time (when did we know it?) comes for free.

All Datomic code (schema, transactions, queries) lives in bank.edn. This script only replays
the story: it sends forms from that file to Datomic Pro's bundled REST server (bin/rest) and
picks the database value each query runs against.

Run:  docker compose up -d --wait && python demo.py   (add --no-pause to run straight through)
"""
import datetime as dt
import pathlib
import re
import sys
import uuid

import edn_format
import requests

BASE = "http://localhost:8999"
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


# ---------------------------------------------------------------- tiny Datomic REST client

def db(**opts):
    """A database *value*: db(), db(as_of=1004), db(history=True), db(since=1004)."""
    opts = "".join(f" :{k.replace('_', '-')} {'true' if v is True else v}" for k, v in opts.items())
    return f'{{:db/alias "mem/{DB}"{opts}}}'


def transact(key):
    print(f"\033[2m;; {key}\n{form(key)}\033[0m\n")
    r = requests.post(f"{BASE}/data/mem/{DB}/", data={"tx-data": form(key)}, headers=EDN)
    assert r.ok, r.text


def query(key, *args):
    print(f"\033[2m;; {key}\n{form(key)}\n;; args: {' '.join(args)}\033[0m\n")
    r = requests.get(f"{BASE}/api/query", params={"q": form(key), "args": f"[{' '.join(args)}]"},
                     headers=EDN)
    assert r.ok, r.text
    return sorted(edn_format.loads(r.text), key=lambda row: [str(v) for v in row])


def basis_t():
    r = requests.get(f"{BASE}/data/mem/{DB}/-/", headers=EDN)
    return edn_format.loads(r.text)[edn_format.Keyword("basis-t")]


# ---------------------------------------------------------------- presentation helpers

def fmt(v):
    if isinstance(v, bool):
        return "+" if v else "-"
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def table(cols, rows):
    rows = [[fmt(v) for v in r] for r in rows]
    w = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
    print("  " + " | ".join(c.ljust(n) for c, n in zip(cols, w)))
    print("  " + "-+-".join("-" * n for n in w))
    for r in rows:
        print("  " + " | ".join(v.ljust(n) for v, n in zip(r, w)))
    print()


def step(title):
    if PAUSE:
        input("\n[enter] ")
    print(f"\n\033[1m=== {title}\033[0m\n")


# ---------------------------------------------------------------- the demo

requests.post(f"{BASE}/data/mem/", data={"db-name": DB}, headers=EDN).raise_for_status()

step("Schema: just the business attributes, plus who/why for transactions")
transact("schema")

step("2026-01-10  alice onboards two customers")
transact("onboarding")

step("2026-02-01  alice raises ACME's limit: a plain write, history is kept by the database")
transact("limit-raise")

step("2026-03-31  Q1 report: run against ONE immutable database value, stamp it with its basis-t")
report_t = basis_t()
print(f"  report basis-t = {report_t}\n")
table(["customer", "risk", "limit"], query("report", db(as_of=report_t)))

step("2026-04-07  bob: adverse media about ACME dated 2026-01-20 -> HIGH risk")
transact("kyc-correction")

step("Auditor, June: 1) reproduce the filed Q1 report exactly (same query, as-of its basis-t)")
table(["customer", "risk", "limit"], query("report", db(as_of=report_t)))

step("Auditor: 2) full history of ACME: who changed what, when, why")
table(["when", "attribute", "value", "op", "by", "why"],
      query("audit-trail", db(history=True), '"ACME"'))

step("Auditor: 3) what changed after the report was filed?")
table(["customer", "attribute", "new value", "when", "by"],
      query("changed-since", db(), db(since=report_t)))

step("Auditor: 4) what was really true on 2026-03-31, with what we know today?")
table(["customer", "risk", "limit"], query("report", db(as_of='#inst "2026-03-31T18:00:00Z"')))
print("  Still LOW: Datomic's time axis is *when we learned it*, not *when it was true*.\n"
      "  'HIGH since 2026-01-20' only survives in a free-text reason. Answering this needs\n"
      "  business time modelled by hand, i.e. a second time axis: bitemporality.")
