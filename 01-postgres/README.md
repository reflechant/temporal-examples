# 01: Hand-made bitemporality in PostgreSQL

```sh
docker compose up -d --wait
pip install -r requirements.txt
python demo.py            # --no-pause to run straight through
```

The demo's writes are the same SQL as in `03-xtdb`:

```sql
INSERT INTO customers (_id, name, risk_rating) VALUES (1, 'Alice', 'LOW');
INSERT INTO customers (_id, name, risk_rating, _valid_from) VALUES (1, 'Alice', 'HIGH', '2026-01-01');
```

What makes that work is [`schema.sql`](schema.sql), about 70 lines for **one** table:

- `customers_history`: every version, with `_valid_from/_to` (when it was true) and
  `_system_from/_to` (when the database believed it), plus a GiST exclusion constraint so no
  two beliefs overlap.
- `customers`: a view of what we believe now, about now. `INSTEAD OF` triggers turn plain
  `INSERT` (an upsert from `_valid_from`, default now), `UPDATE` (patches the changed columns
  from now on, per column) and `DELETE` into versioned writes that keep every earlier belief.
- `customers_as_of(valid_at, known_at)`: the time-travel query, since Postgres has no
  `FOR … AS OF`.
- A guard trigger that makes the history table append-only. New beliefs start now, and now
  never goes backwards. The last step of the demo shows a direct `UPDATE` and a backdated
  `INSERT` being rejected.

What it still doesn't cover is listed at the bottom of `schema.sql`. Most notably, a superuser
can switch all of it off (`DROP`/`DISABLE TRIGGER`, `session_replication_role = replica`), and
everything has to be repeated for every table.
