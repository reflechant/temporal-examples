"""Bitemporal credit file in plain PostgreSQL: every bit of time handling is hand-made.

Run:  docker compose up -d && python demo.py          (add --no-pause to run straight through)
"""
import datetime as dt
import pathlib
import sys

import psycopg
from psycopg.types.range import Range

DSN = "postgresql://postgres:demo@localhost:54321/postgres"
PAUSE = sys.stdin.isatty() and "--no-pause" not in sys.argv


# ---------------------------------------------------------------- presentation helpers

def fmt(v):
    if isinstance(v, Range):
        return f"[{fmt(v.lower)}, {fmt(v.upper) if v.upper else '∞'})"
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    if isinstance(v, (int, float)) or type(v).__name__ == "Decimal":
        return f"{v:,.0f}"
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


# ---------------------------------------------------------------- the demo

REPORT = """
SELECT customer_id, risk, credit_limit
FROM customer_version
WHERE valid    @> timestamptz '2026-03-31 18:00Z'  -- business time: quarter end
  AND recorded @> {known_at}  -- system time: as the DB knew it at that moment
ORDER BY customer_id"""

with psycopg.connect(DSN, autocommit=True) as db:
    db.execute(pathlib.Path(__file__).with_name("schema.sql").read_text())

    step("2026-01-10  alice onboards two customers")
    sql(db, """
INSERT INTO customer_version VALUES
  ('ACME',   'LOW',    1000000, tstzrange('2026-01-10 09:00Z', NULL), tstzrange('2026-01-10 09:00Z', NULL), 'alice', 'onboarding'),
  ('GLOBEX', 'MEDIUM',  500000, tstzrange('2026-01-10 09:00Z', NULL), tstzrange('2026-01-10 09:00Z', NULL), 'alice', 'onboarding')""")

    step("2026-02-01  alice raises ACME's limit (through our hand-written procedure)")
    sql(db, """
CALL set_customer('ACME', NULL, 2000000, tstzrange('2026-02-01 10:00Z', NULL),
                  'alice', 'annual review', p_now => '2026-02-01 10:00Z')""")

    step("2026-03-31  Q1 regulatory report is generated and filed")
    sql(db, REPORT.format(known_at="timestamptz '2026-03-31 18:00Z'"))

    step("2026-04-07  bob: adverse media about ACME dated 2026-01-20 -> HIGH risk, backdated")
    sql(db, """
CALL set_customer('ACME', 'HIGH', NULL, tstzrange('2026-01-20 00:00Z', NULL),
                  'bob', 'KYC-123 adverse media', p_now => '2026-04-07 14:00Z')""")

    step("Auditor, June: 1) reproduce the filed Q1 report exactly")
    sql(db, REPORT.format(known_at="timestamptz '2026-03-31 18:00Z'"))

    step("Auditor: 2) what was really true on 2026-03-31, with what we know today?")
    sql(db, REPORT.format(known_at="now()"))

    step("Auditor: 3) which figures in the filed report are now known to be wrong?")
    sql(db, """
SELECT filed.customer_id,
       filed.risk AS filed_risk, today.risk AS actual_risk,
       filed.credit_limit AS filed_limit, today.credit_limit AS actual_limit
FROM customer_version filed
JOIN customer_version today USING (customer_id)
WHERE filed.valid    @> timestamptz '2026-03-31 18:00Z'
  AND filed.recorded @> timestamptz '2026-03-31 18:00Z'
  AND today.valid    @> timestamptz '2026-03-31 18:00Z'
  AND upper_inf(today.recorded)
  AND (filed.risk, filed.credit_limit) IS DISTINCT FROM (today.risk, today.credit_limit)""")

    step("Auditor: 4) full history of ACME: who changed what, when, why")
    sql(db, """
SELECT risk, credit_limit, valid, recorded, changed_by, reason
FROM customer_version WHERE customer_id = 'ACME'
ORDER BY lower(recorded), lower(valid)""")

    step("Pitfall 1: the 'obvious' query a new developer writes. What is ACME's limit?")
    sql(db, "SELECT risk, credit_limit FROM customer_version WHERE customer_id = 'ACME'")

    step("Pitfall 2: 2026-04-08, a DBA hotfixes GLOBEX's limit with a plain UPDATE")
    sql(db, "UPDATE customer_version SET credit_limit = 600000 WHERE customer_id = 'GLOBEX'")
    print("  ... and the filed Q1 report can no longer be reproduced. Nothing complained:\n")
    sql(db, REPORT.format(known_at="timestamptz '2026-03-31 18:00Z'"))
