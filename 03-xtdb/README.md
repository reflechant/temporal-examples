# 03: Bitemporality built in, with XTDB

```sh
docker compose up -d --wait
pip install -r requirements.txt
python demo.py            # --no-pause to run straight through
```

XTDB 2.x speaks the Postgres wire protocol, so the driver is the same `psycopg` as in
`01-postgres`. System time only moves forward, so re-running needs a fresh container:
`docker compose down && docker compose up -d --wait`.

What to point at while it runs:

- There's no schema and no code. The two writes are the same `INSERT`s as in the Postgres
  demo: the first is valid from now (the default), the second from `_valid_from`
  ([DML docs](https://docs.xtdb.com/reference/main/sql/txs)).
- Q1 is `FOR VALID_TIME AS OF`; Q2 adds `FOR SYSTEM_TIME AS OF`. Postgres needs the
  hand-written `customers_as_of` function for the same thing.
