# 02 (EDN variant, no valid time): Datomic as it comes

The same structure as [`02-datomic-edn`](../02-datomic-edn): all Datomic code is in
[`bank.edn`](bank.edn), and [`demo.py`](demo.py) only sends forms from it by name. This one
**doesn't model valid time at all**: no `:customer/valid-from`, just `name` and `risk-rating`.

```sh
docker compose up -d --wait      # first build downloads Datomic Pro (~270 MB)
pip install -r requirements.txt
python demo.py                   # --no-pause to run straight through
```

It runs on port 8997, so it can run alongside `02-datomic` (8998) and `02-datomic-edn` (8999).

What it shows:

- **Q2: what did we believe on 2026-01-10?** It's built in: the `rating` query against the
  database `as-of` 2026-01-10 returns LOW.
- **Q1: what do we now believe was true on 2026-01-10?** It can't be asked. The closest is the
  current database, HIGH, but that describes now, not 2026-01-10.
- The history query even says Alice became HIGH on **2026-01-15**, the day of the correction.
  "Since 2026-01-01" has nowhere to go.

Run it before `02-datomic-edn` to show the gap, then show how a hand-modelled `valid-from`
fills it.
