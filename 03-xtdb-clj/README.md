# 03 (Clojure variant): Bitemporality built in, with XTDB, from the REPL

The same story as [`03-xtdb`](../03-xtdb), in Clojure only, using XTDB's Clojure API
(`xtdb.api`) and XTQL against an XTDB server running in Docker.

```sh
docker compose up -d --wait   # XTDB 2.2.0, Postgres wire protocol on port 54323
```

Then jack in from this folder (Calva: *Start a Project REPL and Connect*, CIDER:
`cider-jack-in-clj`; plain `deps.edn`, no aliases needed), load `src/bank.clj`, and evaluate the
forms in the `comment` block one by one.

- The writes are data for `xt/execute-tx`: `put-docs`, the second one with a `:valid-from`.
- Both questions run the same query. The options pick the point in time: `:current-time` is
  valid time (Q1), and adding `:snapshot-time` pins system time too (Q2).
- To replay, run `docker compose restart`. Data lives in memory and system time only moves
  forward.

`deps.edn` lists `next.jdbc` explicitly: `xtdb.api`'s remote client needs it at runtime, but
`xtdb-api` 2.2.0 doesn't declare it. It comes from Clojars, the others from Maven Central.
