# 01-postgres: bitemporality built by hand in PostgreSQL

Both time axes, hand-made in [`schema.sql`](schema.sql) (~70 lines for one table), so that
plain SQL writes keep full history and history can't be rewritten.

## Run

From this folder, with the Python environment from the [top-level README](../README.md#running):

```sh
docker compose up -d --wait   # PostgreSQL 17 on port 54321, data in memory
python demo.py                # --no-pause to run straight through; re-run any time
docker compose down           # when done
```

## What to look at

- The writes are the same SQL as in [`03-xtdb`](../03-xtdb):
  ```sql
  INSERT INTO customers (_id, name, risk_rating) VALUES (1, 'Alice', 'LOW');
  INSERT INTO customers (_id, name, risk_rating, _valid_from) VALUES (1, 'Alice', 'HIGH', '2026-01-01');
  ```
- Q1 and Q2 call `customers_as_of(valid_at, known_at)`, a hand-written function, since Postgres
  has no `FOR … AS OF`.
- The last step tries to rewrite history directly (an `UPDATE` and a backdated `INSERT` on the
  history table); both are rejected.
- Then open [`schema.sql`](schema.sql). It contains:
  - `customers_history`: every version with `_valid_from/_to` (when it was true) and
    `_system_from/_to` (when the database believed it), plus a GiST exclusion constraint so no
    two beliefs overlap.
  - `customers`: a view of what we believe now, about now. `INSTEAD OF` triggers turn plain
    `INSERT` (an upsert from `_valid_from`, default now), `UPDATE` (patches changed columns
    from now on, per column) and `DELETE` into versioned writes.
  - A guard trigger that makes the history table append-only: new beliefs start now, and now
    never goes backwards.

## Notes

What it still doesn't cover is listed at the bottom of `schema.sql`. Most notably, a superuser
can switch all of it off (`DROP`/`DISABLE TRIGGER`, `session_replication_role = replica`), and
everything has to be repeated for every table. The demo clock (`SET app.now`) exists only to
replay January; in production it's `now()`.
