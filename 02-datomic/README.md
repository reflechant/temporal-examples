# 02: System time for free with Datomic

```sh
docker compose up -d --wait      # first build downloads Datomic Pro (~270 MB)
pip install -r requirements.txt
python demo.py                   # --no-pause to run straight through
```

The container runs Datomic Pro's bundled REST server (`bin/rest`) over in-memory storage;
`demo.py` sends EDN over HTTP. Datomic has no official Python client, and the REST server is
[legacy but still shipped](https://docs.datomic.com/reference/rest.html). Each run creates a
fresh database.

What to point at while it runs:

- There's no history code. Writes accrete facts, and a database is an immutable **value**.
- One query answers both questions. Q1 runs it against the database now, Q2 against the
  database as of 2026-01-10 ([filters docs](https://docs.datomic.com/reference/filters.html)).
- `:customer/valid-from` is modelled by hand: Datomic has no valid time. A single attribute is
  enough for one "true since" date; real business-time history would need an entity per version.
