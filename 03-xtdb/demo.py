"""Alice's risk rating in XTDB: both time axes are built in, and it's still just SQL.

XTDB speaks the Postgres wire protocol, so this uses the same driver as the Postgres demo.

Run:  docker compose up -d --wait && python demo.py   (add --no-pause to run straight through)
"""
import datetime as dt
import sys

import psycopg

DSN = "postgresql://xtdb@localhost:54322/xtdb"
PAUSE = sys.stdin.isatty() and "--no-pause" not in sys.argv


def step(title):
    if PAUSE:
        input("\n[enter] ")
    print(f"\n\033[1m=== {title}\033[0m\n")


def sql(conn, text):
    print("\033[2m" + text.strip() + "\033[0m\n")
    cur = conn.execute(text)
    if cur.description:
        cols = [d.name for d in cur.description]
        rows = [[v.strftime("%Y-%m-%d %H:%M") if isinstance(v, dt.datetime) else str(v) for v in r]
                for r in cur.fetchall()]
        w = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
        print("  " + " | ".join(c.ljust(n) for c, n in zip(cols, w)))
        print("  " + "-+-".join("-" * n for n in w))
        for r in rows:
            print("  " + " | ".join(v.ljust(n) for v, n in zip(r, w)))
        print()


def tx(conn, at, text):
    """A write transaction. SYSTEM_TIME is pinned only to replay January; normally it's now."""
    sql(conn, f"BEGIN READ WRITE WITH (SYSTEM_TIME = TIMESTAMP '{at}')  -- demo clock")
    sql(conn, text)
    conn.execute("COMMIT")


with psycopg.connect(DSN, autocommit=True) as db:
    if db.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'customers'").fetchone():
        sys.exit("XTDB already has data: run `docker compose down && docker compose up -d --wait` first")
    print("schema: none")

    step("2026-01-01  the bank records Alice as LOW risk")
    tx(db, "2026-01-01T09:00:00Z",
       "INSERT INTO customers (_id, name, risk_rating) VALUES (1, 'Alice', 'LOW')")

    step("2026-01-10  the bank approves a loan, based on LOW")

    step("2026-01-15  the bank discovers Alice should have been HIGH since 2026-01-01")
    tx(db, "2026-01-15T10:00:00Z",
       "INSERT INTO customers (_id, name, risk_rating, _valid_from) VALUES (1, 'Alice', 'HIGH', DATE '2026-01-01')")

    step("Q1: what do we now believe was true on 2026-01-10?")
    sql(db, """
SELECT _id, name, risk_rating, _valid_from FROM customers
  FOR VALID_TIME AS OF TIMESTAMP '2026-01-10T12:00:00Z'""")

    step("Q2: what did we believe on 2026-01-10?")
    sql(db, """
SELECT _id, name, risk_rating, _valid_from FROM customers
  FOR VALID_TIME  AS OF TIMESTAMP '2026-01-10T12:00:00Z'
  FOR SYSTEM_TIME AS OF TIMESTAMP '2026-01-10T12:00:00Z'""")
