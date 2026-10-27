# 02: System time for free with Datomic

```sh
docker compose up -d --wait      # first build downloads Datomic Pro (~270 MB)
pip install -r requirements.txt
python demo.py                   # --no-pause to run straight through
```

The container runs Datomic Pro's bundled REST server (`bin/rest`) over in-memory storage;
`demo.py` sends EDN over HTTP (Datomic has no official Python client, and the REST server is
[legacy but still shipped](https://docs.datomic.com/reference/rest.html)). Each run creates
a fresh database.

What to point at while it runs:

- No history tables, no triggers, no `valid_from` columns: the schema is just the business
  attributes. A database is an immutable **value**; writes accrete facts.
- Who and why are attributes of the **transaction**, written atomically with the data.
- The report is computed against a database value and stamped with its `basis-t`. Re-running
  the same query `:as-of` that `basis-t` returns the same answer forever.
- History is a query over `(d/history db)`; "what changed since the report" is a query over
  `(d/since db t)`, joined with the current db
  ([filters docs](https://docs.datomic.com/reference/filters.html)).
- Last step, deliberately: as-of 2026-03-31 still says LOW. Datomic's time is **when the
  database learned it**. "HIGH since 2026-01-20" has no place to live except a field you model
  yourself. That gap is what a bitemporal database fills (see `03-xtdb`).
