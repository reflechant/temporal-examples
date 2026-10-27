"""Bitemporal credit file in XTDB: both time axes are built in, and it's still just SQL.

XTDB speaks the Postgres wire protocol, so this uses the same driver as the Postgres demo.

Run:  docker compose up -d && python demo.py          (add --no-pause to run straight through)
"""
import datetime as dt
import sys

import psycopg

DSN = "postgresql://xtdb@localhost:54322/xtdb"
PAUSE = sys.stdin.isatty() and "--no-pause" not in sys.argv


# ---------------------------------------------------------------- presentation helpers

def fmt(v):
    if v is None:
        return "∞"
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


def sql(conn, text):
    print("\033[2m" + text.strip() + "\033[0m\n")
    cur = conn.execute(text)
    if cur.description:
        table([d.name for d in cur.description], cur.fetchall())


def tx(conn, at, text):
    """A write transaction. SYSTEM_TIME is set only to replay the timeline; normally it's now."""
    print(f"\033[2m-- transaction recorded at {at}\033[0m")
    conn.execute(f"BEGIN READ WRITE WITH (SYSTEM_TIME = TIMESTAMP '{at}')")
    sql(conn, text)
    conn.execute("COMMIT")


# ---------------------------------------------------------------- the demo

# An ordinary report query: no time columns, no time predicates.
REPORT = "SELECT _id AS customer, risk, credit_limit FROM customers ORDER BY _id"

with psycopg.connect(DSN, autocommit=True) as db:
    if db.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'customers'").fetchone():
        sys.exit("XTDB already has data: run `docker compose down && docker compose up -d` first")

    step("2026-01-10  alice onboards two customers (no schema, no history tables)")
    tx(db, "2026-01-10T09:00:00Z", """
INSERT INTO customers (_id, risk, credit_limit, changed_by, reason) VALUES
  ('ACME',   'LOW',    1000000, 'alice', 'onboarding'),
  ('GLOBEX', 'MEDIUM',  500000, 'alice', 'onboarding')""")

    step("2026-02-01  alice raises ACME's limit: a plain UPDATE")
    tx(db, "2026-02-01T10:00:00Z", """
UPDATE customers SET credit_limit = 2000000, changed_by = 'alice', reason = 'annual review'
WHERE _id = 'ACME'""")

    step("2026-03-31  Q1 regulatory report is generated and filed")
    sql(db, "SETTING DEFAULT VALID_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z',\n"
            "        DEFAULT SYSTEM_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z'\n" + REPORT)

    step("2026-04-07  bob: adverse media about ACME dated 2026-01-20 -> HIGH risk, backdated")
    tx(db, "2026-04-07T14:00:00Z", """
UPDATE customers FOR PORTION OF VALID_TIME FROM TIMESTAMP '2026-01-20T00:00:00Z'
SET risk = 'HIGH', changed_by = 'bob', reason = 'KYC-123 adverse media'
WHERE _id = 'ACME'""")

    step("Auditor, June: 1) reproduce the filed Q1 report exactly: same query, both times pinned")
    sql(db, "SETTING DEFAULT VALID_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z',\n"
            "        DEFAULT SYSTEM_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z'\n" + REPORT)

    step("Auditor: 2) what was really true on 2026-03-31, with what we know today?")
    sql(db, "SETTING DEFAULT VALID_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z'\n" + REPORT)

    step("Auditor: 3) which figures in the filed report are now known to be wrong?")
    sql(db, """
SELECT _id AS customer,
       filed.risk AS filed_risk, today.risk AS actual_risk,
       filed.credit_limit AS filed_limit, today.credit_limit AS actual_limit
FROM customers FOR VALID_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z'
               FOR SYSTEM_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z' AS filed
JOIN customers FOR VALID_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z' AS today USING (_id)
WHERE filed.risk <> today.risk OR filed.credit_limit <> today.credit_limit""")

    step("Auditor: 4) full history of ACME: who changed what, when, why")
    sql(db, """
SELECT risk, credit_limit, _valid_from, _valid_to, _system_from, _system_to, changed_by, reason
FROM customers FOR ALL VALID_TIME FOR ALL SYSTEM_TIME
WHERE _id = 'ACME'
ORDER BY _system_from, _valid_from""")

    step("The 'obvious' query a new developer writes. What is ACME's limit?")
    sql(db, "SELECT risk, credit_limit FROM customers WHERE _id = 'ACME'")

    step("2026-04-08, a DBA hotfixes GLOBEX's limit with a plain UPDATE")
    tx(db, "2026-04-08T08:00:00Z", "UPDATE customers SET credit_limit = 600000 WHERE _id = 'GLOBEX'")
    print("  ... and the filed Q1 report is still reproducible, untouched:\n")
    sql(db, "SETTING DEFAULT VALID_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z',\n"
            "        DEFAULT SYSTEM_TIME AS OF TIMESTAMP '2026-03-31T18:00:00Z'\n" + REPORT)
