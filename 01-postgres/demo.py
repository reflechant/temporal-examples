"""Alice's risk rating in plain PostgreSQL: bitemporality, built by hand (see schema.sql).

Run:  docker compose up -d --wait && python demo.py   (add --no-pause to run straight through)
"""
import datetime as dt
import pathlib
import sys

import psycopg

DSN = "postgresql://postgres:demo@localhost:54321/postgres"
PAUSE = sys.stdin.isatty() and "--no-pause" not in sys.argv


def step(title):
    if PAUSE:
        input("\n[enter] ")
    print(f"\n\033[1m=== {title}\033[0m\n")


def sql(conn, text):
    print("\033[2m" + text.strip() + "\033[0m\n")
    try:
        cur = conn.execute(text)
    except psycopg.Error as e:
        print(f"  REJECTED: {e.diag.message_primary}\n")
        return
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


schema = pathlib.Path(__file__).with_name("schema.sql").read_text()
code_lines = [l for l in schema.splitlines() if l.strip() and not l.strip().startswith("--")]

with psycopg.connect(DSN, autocommit=True, options="-c timezone=UTC") as db:
    db.execute(schema)
    print(f"schema.sql: {len(code_lines)} lines of SQL and PL/pgSQL you own, for ONE table")

    step("2026-01-01  the bank records Alice as LOW risk")
    sql(db, "SET app.now = '2026-01-01 09:00Z'  -- demo clock")
    sql(db, "INSERT INTO customers (_id, name, risk_rating) VALUES (1, 'Alice', 'LOW')")

    step("2026-01-10  the bank approves a loan, based on LOW")

    step("2026-01-15  the bank discovers Alice should have been HIGH since 2026-01-01")
    sql(db, "SET app.now = '2026-01-15 10:00Z'  -- demo clock")
    sql(db, "INSERT INTO customers (_id, name, risk_rating, _valid_from) VALUES (1, 'Alice', 'HIGH', '2026-01-01')")
    db.execute("RESET app.now")

    step("Q1: what do we now believe was true on 2026-01-10?")
    sql(db, "SELECT * FROM customers_as_of('2026-01-10 12:00Z')")

    step("Q2: what did we believe on 2026-01-10?")
    sql(db, "SELECT * FROM customers_as_of('2026-01-10 12:00Z', known_at => '2026-01-10 12:00Z')")

    step("Postgres only: the guards that keep the answer to Q2 true")
    sql(db, "UPDATE customers_history SET risk_rating = 'HIGH' WHERE _id = 1")
    sql(db, "INSERT INTO customers_history VALUES (1, 'Alice', 'HIGH', '2026-01-01', NULL, '2026-01-05', NULL)")
