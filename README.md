# Temporal & bitemporal databases vs. Postgres: live demos

Independent demos, each replaying **the same tiny story**, so the audience compares one thing
only: how much of the time handling you have to build yourself.

| Demo | Time axes | What it shows |
|---|---|---|
| [`01-postgres`](01-postgres) | both, **hand-made** | Possible: the writes are the same SQL as XTDB's, but behind them sit ~70 lines of views, triggers, a time-travel function and guards per table, which a superuser can still switch off |
| [`02-datomic`](02-datomic) | system time, **built-in** | "What did we believe then?" is free: the same query against the database as of then. Valid time has to be modelled by hand |
| [`02-datomic-edn`](02-datomic-edn) | system time, **built-in** | Same, with all Datomic code in one `bank.edn` to put next to `schema.sql`; Python only orchestrates |
| [`02-datomic-edn-no-valid-time`](02-datomic-edn-no-valid-time) | system time, **built-in** | Same structure, but Datomic as it comes, without the hand-modelled `valid-from`: Q2 is free, Q1 can't be asked |
| [`02-datomic-clj`](02-datomic-clj) | system time, **built-in** | Same, in Clojure only, from a REPL against Datomic in Docker, in two versions: without valid time (Q1 can't be asked) and with it modelled by hand |
| [`03-xtdb`](03-xtdb) | both, **built-in** | No schema, no code: the same `INSERT`s as Postgres, and one `FOR … AS OF` clause per time axis |
| [`03-xtdb-clj`](03-xtdb-clj) | both, **built-in** | Same, in Clojure only (`xtdb.api`, XTQL), from a REPL against XTDB in Docker |

## The story

| Date | Event |
|---|---|
| 2026-01-01 | the bank records customer Alice as **LOW** risk |
| 2026-01-10 | the bank approves a loan, based on that |
| 2026-01-15 | the bank discovers Alice should have been **HIGH** risk since 2026-01-01 |

Each demo answers exactly two questions:

| Question | Answer | Time axis |
|---|---|---|
| Q1: what do we **now** believe was true on 2026-01-10? | HIGH | valid time: when it was true |
| Q2: what did we believe **on** 2026-01-10? | LOW, the basis of the loan decision | both: when it was true, as known then |

Q2 is what an auditor asks about any past decision. A database that overwrites can only
answer Q1. That is [bitemporal modelling](https://en.wikipedia.org/wiki/Bitemporal_modeling);
banks live in it already (booking date vs. value date), and regulators expect reproducible risk
reporting ([BCBS 239](https://www.bis.org/publ/bcbs239.htm)).

The data is only `_id`, `name`, `risk_rating` and `_valid_from`, spelled the way each database
spells them.

## Running

Prerequisites: Docker with compose; Python ≥ 3.10 for the Python demos; the
[Clojure CLI](https://clojure.org/guides/install_clojure) for the `-clj` ones.

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r 01-postgres/requirements.txt -r 02-datomic/requirements.txt -r 03-xtdb/requirements.txt

cd 01-postgres && docker compose up -d --wait && python demo.py
```

The same applies to `02-datomic`, `02-datomic-edn`, `02-datomic-edn-no-valid-time` (the first build downloads Datomic Pro,
~270 MB) and `03-xtdb`. Ports don't clash (54321, 8997, 8998, 8999, 4334–4335, 54322, 54323), so
start all the containers you need before the talk.

The Python scripts pause before every step when run in a terminal (press Enter: the next
statement is printed, then its result); `--no-pause` runs straight through. The Postgres and
Datomic demos can be re-run as is. XTDB needs a fresh container
(`docker compose down && docker compose up -d --wait`), because system time only moves forward.

## Suggested 10-minute flow

1. **(1 min)** The story and the two questions.
2. **(4 min)** `01-postgres`: run it. The writes look like ordinary SQL, the answers are right,
   and direct attempts to rewrite history are rejected. Then open
   [`schema.sql`](01-postgres/schema.sql): that's what it took, for one table.
3. **(2 min)** `02-datomic`: no history code. Q2 is the same query against the database as of
   2026-01-10. Point out the hand-modelled `valid-from`: valid time isn't built in.
4. **(2 min)** `03-xtdb`: the *same* two `INSERT`s as Postgres, no schema at all, and
   `FOR VALID_TIME AS OF` / `FOR SYSTEM_TIME AS OF` instead of a hand-written function.
5. **(1 min)** Trade-offs below.

## Why these choices

- **Postgres is made to behave like XTDB**, as fairly as I could: a `customers` view takes plain
  `INSERT` (an upsert from `_valid_from`, default now), `UPDATE` (patches changed columns from
  now on) and `DELETE` through `INSTEAD OF` triggers into a bitemporal history table. Range
  exclusion stops overlapping beliefs, and a guard makes the history table append-only.
  Postgres 18's `WITHOUT OVERLAPS` keys ([release notes](https://www.postgresql.org/docs/release/18.0/))
  would replace the exclusion constraint, but none of the rest.
- **Simulated system time.** The demos replay January in seconds, so the write time is pinned:
  `SET app.now` in Postgres, `:db/txInstant` in Datomic, `SYSTEM_TIME` in XTDB. Each only
  accepts increasing values (in Postgres, because the guard enforces it), so this can't
  rewrite the past.
- **Datomic's `valid-from` is a plain attribute.** It's enough to answer Q1 here (one customer,
  one "true since" date), but real business-time history in Datomic needs an entity per
  version: building a bitemporal database by hand again.
- **Datomic from Python** goes through the REST server bundled with Datomic Pro. Datomic has no
  official Python client, and the REST server is
  [documented as legacy](https://docs.datomic.com/reference/rest.html) (still shipped, critical
  fixes only). The `-clj` variant uses the native peer API.

## Trade-offs worth saying out loud

- Datomic is uni-temporal: excellent audit and reproducibility, but business time is your
  modelling job. It's a JVM/Clojure-first ecosystem.
- XTDB 2.x is young compared to Postgres: smaller ecosystem, fewer operational war stories.
  It speaks the Postgres wire protocol, so drivers and many tools work, but it is not Postgres.
- Immutability is not "never delete": both have a controlled erasure path for legal deletion
  (GDPR): XTDB [`ERASE`](https://docs.xtdb.com/reference/main/sql/txs), Datomic
  [excision](https://docs.datomic.com/reference/excision.html).
- Postgres can get there, with code you own per table, and guarantees that hold only as long as
  no superuser switches them off.
