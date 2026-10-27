# Temporal & bitemporal databases vs. Postgres: live demos

Three independent demos, each a single Python script plus a `docker compose` file, all replaying
**the same banking story**, so the audience compares one thing only: how much of the time
handling you have to build yourself.

| Demo | Time axes | What it proves |
|---|---|---|
| [`01-postgres`](01-postgres) | both, **hand-made** | Can be done; costs a split-the-periods procedure per table, two range predicates per table per query, and history is only as safe as everyone's discipline |
| [`02-datomic`](02-datomic) | system time, **built-in** | "What did we know, when, who, why?" is free and tamper-proof. "What was *true* at date X?" after a backdated correction is not |
| [`03-xtdb`](03-xtdb) | system + business time, **built-in** | Both questions are one SQL clause; existing report SQL runs unchanged at any point of either timeline |

## The story (identical in all three)

| Recorded at (system time) | Event |
|---|---|
| 2026-01-10 09:00 | alice onboards ACME (risk LOW, limit 1,000,000) and GLOBEX (MEDIUM, 500,000) |
| 2026-02-01 10:00 | alice raises ACME's limit to 2,000,000 (annual review) |
| 2026-03-31 18:00 | **Q1 regulatory report is generated and filed** |
| 2026-04-07 14:00 | bob finds adverse media about ACME **dated 2026-01-20** → risk HIGH, backdated (KYC-123) |
| 2026-04-08 | a DBA hotfixes GLOBEX's limit with a plain `UPDATE` (Postgres and XTDB demos) |

Then an auditor asks, in June:

1. Reproduce the filed Q1 report **exactly**.
2. What was *actually* true on 2026-03-31, given what we know today?
3. Which figures in the filed report are now known to be wrong?
4. Who changed what, when, and why?

Questions 1 and 4 are *system time* ("when did the bank know it?"), question 2 is *business/valid
time* ("when was it true in the world?"), question 3 needs both at once. That is
[bitemporal modelling](https://en.wikipedia.org/wiki/Bitemporal_modeling); banks live in it
already (booking date vs. value date), and regulators expect reproducible risk reporting
([BCBS 239](https://www.bis.org/publ/bcbs239.htm)).

## Running

Prerequisites: Docker with compose, Python ≥ 3.10.

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r 01-postgres/requirements.txt -r 02-datomic/requirements.txt -r 03-xtdb/requirements.txt

cd 01-postgres && docker compose up -d --wait && python demo.py
```

Same for `02-datomic` (first build downloads Datomic Pro, ~270 MB) and `03-xtdb`.
Ports don't clash (54321, 8998, 54322), so start all three containers before the talk.

Each script pauses before every step when run in a terminal (press Enter: the next statement is
printed, then its result), so you can talk over it. `--no-pause` runs straight through.
Every demo can be re-run: Postgres recreates its table, Datomic creates a new database per run,
XTDB needs a fresh container (`docker compose down && docker compose up -d --wait`) because
system time can only move forward.

## Suggested 12-minute flow

1. **(1 min)** The story table above and the four auditor questions.
2. **(4 min)** `01-postgres`: show [`schema.sql`](01-postgres/schema.sql) for ~20 s (the
   procedure is the point), run it. Land on the history table (6 rows for 3 business
   facts), then the two pitfalls: the naive query returns 6 limits, and a plain `UPDATE` makes
   the filed report silently irreproducible.
3. **(3 min)** `02-datomic`: same story, no history modelling at all. Report stamped with
   `basis-t`, audit trail with who/why on the transaction itself. Last step: backdating is
   *not* expressible. Honest transition to bitemporality.
4. **(3 min)** `03-xtdb`: plain `INSERT`/`UPDATE`, one `FOR PORTION OF VALID_TIME` for the
   backdated fix, the *same* report query with a `SETTING` prefix answers questions 1 and 2,
   and the DBA's plain `UPDATE` no longer destroys anything.
5. **(1 min)** Trade-offs below.

## Why these choices

- **Versioned rows, not event sourcing, for Postgres.** Range-versioned rows (SCD type 2
  extended to two axes) are what most bank systems actually have, and they are the strongest
  hand-made baseline: native range types, a GiST exclusion constraint against overlapping
  beliefs. An event-sourced log moves the same problem into projections: every as-of question
  becomes a replay or a per-axis snapshot table you also maintain.
- **Postgres is set up fairly**: [range types](https://www.postgresql.org/docs/current/rangetypes.html),
  exclusion constraint, a single atomic procedure. Postgres 18 adds `WITHOUT OVERLAPS` keys
  ([release notes](https://www.postgresql.org/docs/release/18.0/)), which replace the
  exclusion constraint but not the procedure; `UPDATE … FOR PORTION OF` is only slated for
  Postgres 19 and still covers business time only.
- **Simulated system time.** All three demos replay a timeline in seconds, so the write timestamp
  is set explicitly: a procedure argument in Postgres, `:db/txInstant` in Datomic, `SYSTEM_TIME`
  on `BEGIN` in XTDB. Both databases only accept monotonically increasing values, so this
  cannot be used to rewrite the past.
- **Datomic from Python** goes through the REST server bundled with Datomic Pro. Datomic has no
  official Python client, and the REST server is
  [documented as legacy](https://docs.datomic.com/reference/rest.html) (still shipped, critical
  fixes only). Fine for a demo; production code would use the JVM peer or client API.

## Trade-offs worth saying out loud

- Datomic is uni-temporal: excellent audit and reproducibility, but business time is your
  modelling job. It is a JVM/Clojure-first ecosystem.
- XTDB 2.x is young compared to Postgres: smaller ecosystem, fewer operational war stories.
  It speaks the Postgres wire protocol, so drivers and many tools work, but it is not Postgres.
- Immutability is not "never delete": both have a controlled erasure path for legal deletion
  (GDPR): XTDB [`ERASE`](https://docs.xtdb.com/reference/main/sql/txs), Datomic
  [excision](https://docs.datomic.com/reference/excision.html).
- Postgres can get there, with code you own per table, and guarantees that hold only as long as
  nobody bypasses them.
