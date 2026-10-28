# 02 (EDN variant): System time for free with Datomic

Same demo as [`02-datomic`](../02-datomic), restructured for readability: **all Datomic code
lives in [`bank.edn`](bank.edn)**, the counterpart of `01-postgres/schema.sql`: the schema,
two transactions and one query. [`demo.py`](demo.py) only sends forms from that file by name
and picks the database value the query runs against (now, or `as-of` 2026-01-10).

```sh
docker compose up -d --wait      # first build downloads Datomic Pro (~270 MB)
pip install -r requirements.txt
python demo.py                   # --no-pause to run straight through
```

This runs on port 8999, so it can run alongside `02-datomic` (8998). Talking points are the
same as in [`02-datomic`](../02-datomic/README.md); the extra one is to put `bank.edn` next to
`schema.sql` on screen.
