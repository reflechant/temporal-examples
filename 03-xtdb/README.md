# 03: Bitemporality built in, with XTDB

```sh
docker compose up -d --wait
pip install -r requirements.txt
python demo.py            # --no-pause to run straight through
```

XTDB 2.x speaks the Postgres wire protocol, so the driver is the same `psycopg` as in
`01-postgres`. System time only moves forward, so re-running needs a fresh container:
`docker compose down && docker compose up -d --wait`.

What to point at while it runs:

- No schema, no history columns, no procedure. Onboarding is an `INSERT`, the limit change a
  plain `UPDATE`; both are versioned automatically on both axes.
- The backdated correction is one clause: `UPDATE … FOR PORTION OF VALID_TIME FROM …`. XTDB
  splits the periods and keeps the February limit change intact, the work the Postgres
  procedure does by hand ([DML docs](https://docs.xtdb.com/reference/main/sql/txs)).
- The report is ordinary SQL with no time predicates. `SETTING DEFAULT VALID_TIME AS OF …,
  DEFAULT SYSTEM_TIME AS OF …` runs the **same** query as filed (question 1) or as we know it
  now (question 2), joins included.
- Question 3 joins the table with itself at two points of system time.
- The naive `SELECT` returns the current state, one row. The DBA's plain `UPDATE` adds a
  version instead of overwriting one, so the filed report is still reproducible.
