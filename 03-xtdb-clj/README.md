# 03 (Clojure variant): Bitemporality built in, with XTDB, from the REPL

The same story as [`03-xtdb`](../03-xtdb), in Clojure only, using XTDB's Clojure API
(`xtdb.api`) against an XTDB server running in Docker. Queries are in XTQL, XTDB's
data-oriented query language; SQL works through the same calls.

```sh
docker compose up -d --wait   # XTDB 2.2.0, Postgres wire protocol on port 54323
```

Then jack in from this folder (Calva: *Start a Project REPL and Connect*, CIDER:
`cider-jack-in-clj`; plain `deps.edn`, no aliases needed), load `src/bank.clj`, and evaluate the
forms in the `comment` block one by one.

What's in [`src/bank.clj`](src/bank.clj):

- **The story as data**: each step is `{:ops [...] :opts {...}}`, passed to `xt/execute-tx`.
  Who and why are transaction `:metadata` (they end up in the `xt/txs` table). The backdated
  correction is a SQL op (`UPDATE … FOR PORTION OF VALID_TIME`), because `patch-docs` doesn't
  accept a valid-time range from a remote client yet.
- **The auditor's questions in XTQL**. `report` contains no time at all; the point in time is
  chosen per call: `:snapshot-time` = system time (what the database knew),
  `:current-time` = valid time (when it was true). `filed-vs-actual` joins the table with
  itself at two points of system time; `audit-trail` joins every version with the who/why of
  the transaction that wrote it.
- **The `comment` block**: the four auditor questions, the naive query, the DBA's plain
  `UPDATE` that leaves the filed report intact, then extras: the same time options on SQL,
  ACME's risk timeline as known today vs. as known at quarter end, and the transaction log.

To replay the story, run `docker compose restart`. Data lives in memory and system time only
moves forward.

`deps.edn` lists `next.jdbc` explicitly: `xtdb.api`'s remote client needs it at runtime, but
`xtdb-api` 2.2.0 doesn't declare it. It comes from Clojars, the others from Maven Central.
