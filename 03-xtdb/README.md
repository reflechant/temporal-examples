# 03-xtdb: bitemporality built in

Both time axes are built into XTDB: no schema, no code. The writes are the same SQL as in
[`01-postgres`](../01-postgres), and each time axis is one `FOR … AS OF` clause.

## Run

From this folder, with the Python environment from the [top-level README](../README.md#running):

```sh
docker compose up -d --wait   # XTDB 2.2.0, Postgres wire protocol on port 54322
python demo.py                # --no-pause to run straight through
docker compose down           # when done
```

To run it again, start from an empty database: `docker compose down && docker compose up -d --wait`.
XTDB's system time only moves forward, so January can't be replayed on top of itself; the
script tells you if you forget.

## What to look at

- There's no schema. The two writes are the same `INSERT`s as in the Postgres demo: the first
  is valid from now (the default), the second from `_valid_from`
  ([DML docs](https://docs.xtdb.com/reference/main/sql/txs)).
- Q1 is `FOR VALID_TIME AS OF`; Q2 adds `FOR SYSTEM_TIME AS OF`. Postgres needs the
  hand-written `customers_as_of` function for the same thing.

## Notes

XTDB speaks the Postgres wire protocol, so the driver is the same `psycopg` as in `01-postgres`.
The compose file overrides the image's built-in healthcheck, which never reports healthy.
