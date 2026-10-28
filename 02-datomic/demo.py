"""Alice's risk rating in Datomic: system time (what did we believe, when?) is built in.

Python has no official Datomic client, so this talks EDN over the REST server bundled with
Datomic Pro (bin/rest). Queries are Datalog, i.e. plain data.

Run:  docker compose up -d --wait && python demo.py   (add --no-pause to run straight through)
"""
import datetime as dt
import sys
import uuid

import edn_format
import requests

BASE = "http://localhost:8998"
DB = f"bank-{uuid.uuid4().hex[:8]}"  # a fresh in-memory database on every run
PAUSE = sys.stdin.isatty() and "--no-pause" not in sys.argv
EDN = {"Accept": "application/edn"}


def step(title):
    if PAUSE:
        input("\n[enter] ")
    print(f"\n\033[1m=== {title}\033[0m\n")


def db(**opts):
    """A database *value*, as EDN: db() is now, db(as_of=...) is the past."""
    opts = "".join(f" :{k.replace('_', '-')} {v}" for k, v in opts.items())
    return f'{{:db/alias "mem/{DB}"{opts}}}'


def transact(tx_data):
    print("\033[2m" + tx_data.strip() + "\033[0m\n")
    r = requests.post(f"{BASE}/data/mem/{DB}/", data={"tx-data": tx_data}, headers=EDN)
    assert r.ok, r.text


def q(query, *args):
    print("\033[2m" + query.strip() + f"\n;; args: {' '.join(args)}\033[0m\n")
    r = requests.get(f"{BASE}/api/query", params={"q": query, "args": f"[{' '.join(args)}]"}, headers=EDN)
    assert r.ok, r.text
    cols = ["_id", "name", "risk_rating", "valid_from"]
    rows = [[v.strftime("%Y-%m-%d %H:%M") if isinstance(v, dt.datetime) else str(v) for v in row]
            for row in edn_format.loads(r.text)]
    w = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
    for r in [cols, ["-" * n for n in w], *rows]:
        print("  " + " | ".join(v.ljust(n) for v, n in zip(r, w)))
    print()


# Valid time is not built in: `valid-from` is an attribute we model ourselves. With one value per
# entity it only works for a single "true since" date; real business-time history would need an
# entity per version, i.e. building a bitemporal database by hand.
RATING_ON = """
[:find ?c ?name ?rating ?valid-from
 :in $ ?t
 :where [?c :customer/name ?name]
        [?c :customer/risk-rating ?rating]
        [?c :customer/valid-from ?valid-from]
        [(<= ?valid-from ?t)]]"""

requests.post(f"{BASE}/data/mem/", data={"db-name": DB}, headers=EDN).raise_for_status()

step("Schema")
transact("""
[{:db/ident :customer/name        :db/valueType :db.type/string  :db/cardinality :db.cardinality/one
  :db/unique :db.unique/identity}
 {:db/ident :customer/risk-rating :db/valueType :db.type/keyword :db/cardinality :db.cardinality/one}
 {:db/ident :customer/valid-from  :db/valueType :db.type/instant :db/cardinality :db.cardinality/one}
 {:db/id "datomic.tx" :db/txInstant #inst "2025-12-31T00:00:00Z"}]  ; demo clock""")

step("2026-01-01  the bank records Alice as LOW risk")
transact("""
[{:customer/name "Alice" :customer/risk-rating :low :customer/valid-from #inst "2026-01-01T09:00:00Z"}
 {:db/id "datomic.tx" :db/txInstant #inst "2026-01-01T09:00:00Z"}]  ; demo clock""")

step("2026-01-10  the bank approves a loan, based on LOW")

step("2026-01-15  the bank discovers Alice should have been HIGH since 2026-01-01")
transact("""
[{:customer/name "Alice" :customer/risk-rating :high :customer/valid-from #inst "2026-01-01T00:00:00Z"}
 {:db/id "datomic.tx" :db/txInstant #inst "2026-01-15T10:00:00Z"}]  ; demo clock""")

step("Q1: what do we now believe was true on 2026-01-10?")
q(RATING_ON, db(), '#inst "2026-01-10T12:00:00Z"')

step("Q2: what did we believe on 2026-01-10?  Same query, against the database as of then")
q(RATING_ON, db(as_of='#inst "2026-01-10T12:00:00Z"'), '#inst "2026-01-10T12:00:00Z"')
