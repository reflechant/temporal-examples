# 02-datomic-edn: system time for free, valid time by hand (all Datomic code in one file)

The same demo as [`02-datomic`](../02-datomic), but all Datomic code lives in
[`bank.edn`](bank.edn): the schema, two transactions and one query. It's the counterpart of
`01-postgres/schema.sql`. [`demo.py`](demo.py) only sends forms from that file by name and
picks the database value the query runs against (now, or as of 2026-01-10).

## Run

From this folder, with the Python environment from the [top-level README](../README.md#running):

```sh
docker compose up -d --wait   # first time: builds an image with Datomic Pro (~270 MB download)
python demo.py                # --no-pause to run straight through; re-run any time
docker compose down           # when done
```

The REST server listens on port 8999, so this can run alongside the other Datomic demos.

## What to look at

- Put `bank.edn` next to `01-postgres/schema.sql` on screen.
- The `rating-on` query answers both questions. Q1 runs it against the current database, Q2
  against the database as of 2026-01-10.
- `:customer/valid-from` is modelled by hand: compare with
  [`02-datomic-edn-no-valid-time`](../02-datomic-edn-no-valid-time), where Q1 can't be asked.
- A last check asks what we now believe was true on 2025-12-31, before Alice was a customer,
  and correctly gets nothing. Without valid time that question can't even be put to the
  database (see [`02-datomic-edn-no-valid-time`](../02-datomic-edn-no-valid-time)).
