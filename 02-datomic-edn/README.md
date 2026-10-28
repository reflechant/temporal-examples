# 02 (EDN variant): System time for free with Datomic

Same demo as [`02-datomic`](../02-datomic), restructured for readability: **all Datomic code
lives in [`bank.edn`](bank.edn)**, the counterpart of `01-postgres/schema.sql`. That's about 60
lines for the schema, the story's transactions and the auditor's queries, with no history
modelling anywhere. [`demo.py`](demo.py) only replays the story: it sends forms from that
file to the database by name and chooses the database value each query runs against
(`as-of`, `history`, `since`).

```sh
docker compose up -d --wait      # first build downloads Datomic Pro (~270 MB)
pip install -r requirements.txt
python demo.py                   # --no-pause to run straight through
```

This runs on port 8999, so it can run alongside `02-datomic` (8998).

Talking points are the same as in [`02-datomic`](../02-datomic/README.md). The extra one here:
put `bank.edn` next to `schema.sql` on screen. Every query in `bank.edn` is time-free; time is
a property of the database *value* you pass in, not of the query.
