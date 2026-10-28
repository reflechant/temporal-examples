# Temporal & bitemporal databases vs. Postgres: live demos

Small, independent demos that replay **the same tiny story**, so the audience compares one thing
only: how much of the time handling you have to build yourself.

## The story

| Date | Event |
|---|---|
| 2026-01-01 | the bank records customer Alice as **LOW** risk |
| 2026-01-10 | the bank approves a loan, based on that |
| 2026-01-15 | the bank discovers Alice should have been **HIGH** risk since 2026-01-01 |

Two questions, asked afterwards:

| Question | Right answer | Needs |
|---|---|---|
| Q1: what do we **now** believe was true on 2026-01-10? | HIGH | valid time: when it was true |
| Q2: what did we believe **on** 2026-01-10? | LOW, the basis of the loan decision | system time too: what the database knew then |

Q2 is what an auditor asks about any past decision, and a database that overwrites can't
answer it. Having both axes is [bitemporal modelling](https://en.wikipedia.org/wiki/Bitemporal_modeling).
Banks already live in it (booking date vs. value date), and regulators expect reproducible risk
reporting ([BCBS 239](https://www.bis.org/publ/bcbs239.htm)).

The data is only `_id`, `name`, `risk_rating` and `_valid_from`, spelled the way each database
spells them.

## The demos

| Folder | Database | Language | Valid time | Q1 | Q2 |
|---|---|---|---|---|---|
| [`01-postgres`](01-postgres) | PostgreSQL 17 | Python + SQL | hand-made, with system time, in [`schema.sql`](01-postgres/schema.sql) (~70 lines for one table) | ✅ | ✅ |
| [`02-datomic`](02-datomic) | Datomic Pro | Python + inline EDN | hand-modelled `:customer/valid-from` | ✅ | ✅ built in |
| [`02-datomic-edn`](02-datomic-edn) | Datomic Pro | Python + [`bank.edn`](02-datomic-edn/bank.edn) | hand-modelled `:customer/valid-from` | ✅ | ✅ built in |
| [`02-datomic-edn-no-valid-time`](02-datomic-edn-no-valid-time) | Datomic Pro | Python + [`bank.edn`](02-datomic-edn-no-valid-time/bank.edn) | none | ❌ can't be asked | ✅ built in |
| [`02-datomic-clj`](02-datomic-clj) | Datomic Pro | Clojure (REPL) | two namespaces: none / hand-modelled | ❌ / ✅ | ✅ built in |
| [`03-xtdb`](03-xtdb) | XTDB 2.2 | Python + SQL | built in | ✅ | ✅ |
| [`03-xtdb-clj`](03-xtdb-clj) | XTDB 2.2 | Clojure (REPL), XTQL | built in | ✅ | ✅ |

The `02-datomic-edn` variants hold all Datomic code in one `bank.edn` file, to put next to
Postgres' `schema.sql`. `02-datomic` is the same demo with the EDN inline in Python.

## Running

Everything runs in Docker; each folder has its own `docker-compose.yml`, and all commands below
are run **from inside that folder**. Ports don't clash, so you can start every container you
need before the talk.

**Prerequisites:** Docker with Compose v2. Python ≥ 3.10 for the Python demos. For the
Clojure demos, a JDK ≥ 21 and the [Clojure CLI](https://clojure.org/guides/install_clojure),
or an editor that can jack in (Calva, CIDER).

**One-time Python setup** (from the repository root):

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r 01-postgres/requirements.txt -r 02-datomic/requirements.txt
```

**Per demo:**

| Folder | Start the database | Run | Replay | Port |
|---|---|---|---|---|
| `01-postgres` | `docker compose up -d --wait` | `python demo.py` | just run it again | 54321 |
| `02-datomic` | `docker compose up -d --wait` ¹ | `python demo.py` | just run it again (new database per run) | 8998 |
| `02-datomic-edn` | `docker compose up -d --wait` ¹ | `python demo.py` | just run it again | 8999 |
| `02-datomic-edn-no-valid-time` | `docker compose up -d --wait` ¹ | `python demo.py` | just run it again | 8997 |
| `02-datomic-clj` | `docker compose up -d --wait` ¹ | REPL, see below | `(def conn (fresh-conn))` | 4334–4335 |
| `03-xtdb` | `docker compose up -d --wait` | `python demo.py` | `docker compose down && docker compose up -d --wait` ² | 54322 |
| `03-xtdb-clj` | `docker compose up -d --wait` | REPL, see below | `docker compose restart` ² | 54323 |

¹ The first start builds an image that downloads Datomic Pro (~270 MB); it takes a few minutes.
² XTDB's system time only moves forward, so replaying January needs an empty database.

The Python scripts print each statement, then its result. In a terminal they pause before
every step (press Enter), so you can talk over them. `python demo.py --no-pause` runs straight
through.

**Clojure REPL demos:** start the database as above, then either

- jack in from the folder (Calva: *Start a Project REPL and Connect*; CIDER:
  `cider-jack-in-clj`), open the namespace file, load it, and evaluate the forms in its
  `comment` block one by one; or
- run `clj` in the folder and `(require 'bank)` then `(in-ns 'bank)` (for `02-datomic-clj`,
  use `bank.without-valid-time` or `bank.with-valid-time`), then paste the `comment`
  block's forms one by one.

**Stop** with `docker compose down` in the folder.

## Suggested 10-minute flow

1. **(1 min)** The story and the two questions.
2. **(4 min)** `01-postgres`: run it. The writes look like ordinary SQL, both answers are right,
   and direct attempts to rewrite history are rejected. Then open
   [`schema.sql`](01-postgres/schema.sql): that's what it took, for one table.
3. **(2 min)** Datomic: `02-datomic-edn-no-valid-time` first. Q2 is the same query against the
   database as of 2026-01-10, with no history code at all, but Q1 can't be asked. Then
   `02-datomic-edn`, where a hand-modelled `valid-from` fills the gap.
4. **(2 min)** `03-xtdb`: the *same* two `INSERT`s as Postgres, no schema at all, and
   `FOR VALID_TIME AS OF` / `FOR SYSTEM_TIME AS OF` instead of a hand-written function.
5. **(1 min)** Trade-offs below.

## Why these choices

- **Postgres is made to behave like XTDB**, as fairly as I could. A `customers` view takes plain
  `INSERT` (an upsert from `_valid_from`, default now), `UPDATE` (patches changed columns from
  now on) and `DELETE` through `INSTEAD OF` triggers into a bitemporal history table. A range
  exclusion constraint stops overlapping beliefs, and a guard makes the history table
  append-only. Postgres 18's `WITHOUT OVERLAPS` keys
  ([release notes](https://www.postgresql.org/docs/release/18.0/)) would replace the exclusion
  constraint, but none of the rest.
- **Simulated system time.** The demos replay January in seconds, so the write time is pinned:
  `SET app.now` in Postgres, `:db/txInstant` in Datomic, `SYSTEM_TIME` in XTDB. Each only
  accepts increasing values (in Postgres, because the guard enforces it), so this can't
  rewrite the past.
- **Datomic's `valid-from` is a plain attribute.** It's enough to answer Q1 here (one customer,
  one "true since" date). Real business-time history in Datomic needs an entity per version,
  which means building a bitemporal database by hand again.
- **Without valid time, Datomic's "now" looks like a Q1 answer, but isn't.** The current value
  is HIGH, which matches Q1 only because the correction still holds today. The query has no
  date in it, so it gives the same answer for any date, e.g. for 2025-12-31, before Alice was
  a customer. The with-valid-time Datomic demos end with that 2025-12-31 check, which
  correctly returns nothing.
- **Datomic from Python** goes through the REST server bundled with Datomic Pro. Datomic has no
  official Python client, and the REST server is
  [documented as legacy](https://docs.datomic.com/reference/rest.html) (still shipped, critical
  fixes only). `02-datomic-clj` uses the native peer API, and `03-xtdb-clj` uses XTDB's Clojure
  API (`xtdb.api`).

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
