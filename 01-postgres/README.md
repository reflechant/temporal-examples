# 01: Hand-made bitemporality in PostgreSQL

```sh
docker compose up -d --wait
pip install -r requirements.txt
python demo.py            # --no-pause to run straight through
```

- [`schema.sql`](schema.sql): one table with two `tstzrange` columns (`valid` = business time,
  `recorded` = system time), a GiST exclusion constraint so no two beliefs overlap, and
  `set_customer`, the procedure that retires overlapping versions and re-asserts the split
  slices. That procedure is the thing you would write, test and maintain **per table**.
- [`demo.py`](demo.py): replays the story and asks the auditor's questions in SQL.

What to point at while it runs:

- The ACME history: three business facts became **six rows** after one backdated correction.
- Every query needs `valid @> …` **and** `recorded @> …` on every table it touches;
  question 3 (a self-join) already has four time predicates.
- *Pitfall 1*: the obvious `SELECT … WHERE customer_id = 'ACME'` returns six limits.
- *Pitfall 2*: a plain `UPDATE` from a DBA rewrites history; the filed report can no longer
  be reproduced and nothing in the database noticed. Preventing that means more code:
  `REVOKE`, triggers, review processes.
