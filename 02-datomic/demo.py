"""Credit file in Datomic: system time (when did we know it?) comes for free.

Python has no official Datomic client, so this talks EDN over the REST server bundled with
Datomic Pro (bin/rest). Queries are Datalog, i.e. plain data.

Run:  docker compose up -d && python demo.py          (add --no-pause to run straight through)
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


# ---------------------------------------------------------------- tiny Datomic REST client

def db(**opts):
    """A database *value*, as EDN: e.g. db(), db(as_of=1005), db(history=True)."""
    extra = "".join(f" :{k.replace('_', '-')} {str(v).lower() if v is True else v}" for k, v in opts.items())
    return f'{{:db/alias "mem/{DB}"{extra}}}'


def transact(at, by, why, *ops):
    """One atomic transaction. Who and why are facts about the transaction itself."""
    audit = f' :audit/by "{by}" :audit/reason "{why}"' if by else ""
    tx = f'{{:db/id "datomic.tx" :db/txInstant #inst "{at}"{audit}}}'
    tx_data = "[" + "\n ".join((*ops, tx)) + "]"
    print("\033[2m" + tx_data + "\033[0m\n")
    r = requests.post(f"{BASE}/data/mem/{DB}/", data={"tx-data": tx_data}, headers=EDN)
    assert r.ok, r.text
    return edn_format.loads(r.text)[edn_format.Keyword("db-after")][edn_format.Keyword("basis-t")]


def q(query, *args):
    print("\033[2m" + query.strip() + f"\n;; args: {' '.join(args)}\033[0m\n")
    r = requests.get(f"{BASE}/api/query", params={"q": query, "args": f"[{' '.join(args)}]"}, headers=EDN)
    assert r.ok, r.text
    return sorted(edn_format.loads(r.text), key=lambda row: [str(v) for v in row])


# ---------------------------------------------------------------- presentation helpers

def fmt(v):
    if isinstance(v, bool):
        return "+" if v else "-"
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    if isinstance(v, int) and not isinstance(v, bool):
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

REPORT = """
[:find ?id ?risk ?limit
 :where [?c :customer/id ?id]
        [?c :customer/risk ?risk]
        [?c :customer/limit ?limit]]"""

requests.post(f"{BASE}/data/mem/", data={"db-name": DB}, headers=EDN).raise_for_status()

step("Schema: customers, plus who/why attributes that will live on transactions")
transact("2026-01-01T00:00:00Z", None, None, """
 {:db/ident :customer/id    :db/valueType :db.type/string  :db/cardinality :db.cardinality/one :db/unique :db.unique/identity}
 {:db/ident :customer/risk  :db/valueType :db.type/keyword :db/cardinality :db.cardinality/one}
 {:db/ident :customer/limit :db/valueType :db.type/long    :db/cardinality :db.cardinality/one}
 {:db/ident :audit/by       :db/valueType :db.type/string  :db/cardinality :db.cardinality/one}
 {:db/ident :audit/reason   :db/valueType :db.type/string  :db/cardinality :db.cardinality/one}""")

step("2026-01-10  alice onboards two customers")
transact("2026-01-10T09:00:00Z", "alice", "onboarding",
         '{:customer/id "ACME"   :customer/risk :low    :customer/limit 1000000}',
         '{:customer/id "GLOBEX" :customer/risk :medium :customer/limit 500000}')

step("2026-02-01  alice raises ACME's limit: a plain write, history is kept by the database")
transact("2026-02-01T10:00:00Z", "alice", "annual review",
         '[:db/add [:customer/id "ACME"] :customer/limit 2000000]')

step("2026-03-31  Q1 report: query ONE immutable database value and stamp the report with its basis-t")
report_t = requests.get(f"{BASE}/data/mem/{DB}/-/", headers=EDN)
report_t = edn_format.loads(report_t.text)[edn_format.Keyword("basis-t")]
print(f"  report basis-t = {report_t}\n")
table(["customer", "risk", "limit"], q(REPORT, db(as_of=report_t)))

step("2026-04-07  bob: adverse media about ACME dated 2026-01-20 -> HIGH risk")
transact("2026-04-07T14:00:00Z", "bob", "KYC-123 adverse media dated 2026-01-20",
         '[:db/add [:customer/id "ACME"] :customer/risk :high]')

step("Auditor, June: 1) reproduce the filed Q1 report exactly (same query, as-of its basis-t)")
table(["customer", "risk", "limit"], q(REPORT, db(as_of=report_t)))

step("Auditor: 2) full history of ACME: who changed what, when, why. No audit table, no triggers")
table(["when", "attribute", "value", "op", "by", "why"], q("""
[:find ?when ?attr ?v ?added ?by ?why
 :in $ ?id
 :where [?c :customer/id ?id]
        [?c ?a ?v ?tx ?added]
        [?a :db/ident ?attr]
        [?tx :db/txInstant ?when]
        [?tx :audit/by ?by]
        [?tx :audit/reason ?why]]""", db(history=True), '"ACME"'))

step("Auditor: 3) what changed after the report was filed?")
table(["customer", "attribute", "new value", "when", "by"], q("""
[:find ?id ?attr ?v ?when ?by
 :in $ $since
 :where [$since ?c ?a ?v ?tx true]
        [$ ?c :customer/id ?id]
        [$ ?a :db/ident ?attr]
        [$ ?tx :db/txInstant ?when]
        [$ ?tx :audit/by ?by]]""", db(), db(since=report_t)))

step("Auditor: 4) what was really true on 2026-03-31, with what we know today?")
table(["customer", "risk", "limit"], q(REPORT, db(as_of='#inst "2026-03-31T18:00:00Z"')))
print("  Still LOW: Datomic's time axis is *when we learned it*, not *when it was true*.\n"
      "  'HIGH since 2026-01-20' only survives in a free-text reason. Answering this needs\n"
      "  business time modelled by hand, i.e. a second time axis: bitemporality.")
