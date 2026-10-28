# 02-datomic: system time for free, valid time by hand

Datomic keeps every past database value, so Q2 is the same query run against the database
as of 2026-01-10. Valid time isn't built in, so Q1 relies on a hand-modelled
`:customer/valid-from`. The EDN is inline in Python; [`02-datomic-edn`](../02-datomic-edn) is
the same demo with it in a separate file.

## Run

From this folder, with the Python environment from the [top-level README](../README.md#running):

```sh
docker compose up -d --wait   # first time: builds an image with Datomic Pro (~270 MB download)
python demo.py                # --no-pause to run straight through; re-run any time
docker compose down           # when done
```

The container runs Datomic Pro's bundled REST server on port 8998 over in-memory storage.
Each run creates a fresh database.

## What to look at

- There's no history code. Writes add facts, and a database is an immutable **value**.
- One query answers both questions: Q1 runs it against the database now, Q2 against the
  database as of 2026-01-10 ([filters docs](https://docs.datomic.com/reference/filters.html)).
- `:customer/valid-from` is modelled by hand. A single attribute is enough for one "true
  since" date; real business-time history would need an entity per version.

## Notes

Datomic has no official Python client, so `demo.py` sends EDN to the REST server, which is
[legacy but still shipped](https://docs.datomic.com/reference/rest.html).
