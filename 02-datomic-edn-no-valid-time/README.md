# 02-datomic-edn-no-valid-time: Datomic as it comes

The same structure as [`02-datomic-edn`](../02-datomic-edn) (all Datomic code in
[`bank.edn`](bank.edn)), but **without any valid time**: just `name` and `risk-rating`. It shows
what Datomic gives you for free (Q2) and what it doesn't (Q1).

## Run

From this folder, with the Python environment from the [top-level README](../README.md#running):

```sh
docker compose up -d --wait   # first time: builds an image with Datomic Pro (~270 MB download)
python demo.py                # --no-pause to run straight through; re-run any time
docker compose down           # when done
```

The REST server listens on port 8997, so this can run alongside the other Datomic demos.

## What to look at

- **Q2: what did we believe on 2026-01-10?** It's built in: the `rating` query against the
  database as of 2026-01-10 returns LOW.
- **Q1: what do we now believe was true on 2026-01-10?** It can't be asked: there's no date to
  put in the query. The closest is the current database, which says HIGH. That matches Q1's
  answer only because the correction still holds today; it would give the same answer for any
  date, including 2025-12-31, before Alice was a customer. The demo says so right after the
  result.
- The history query even says Alice became HIGH on **2026-01-15**, the day of the correction.
  "Since 2026-01-01" has nowhere to go.

Run this before [`02-datomic-edn`](../02-datomic-edn) to show the gap, then show how a
hand-modelled `valid-from` fills it.
