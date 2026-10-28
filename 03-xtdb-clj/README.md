# 03-xtdb-clj: XTDB from the REPL

The same story as [`03-xtdb`](../03-xtdb), in Clojure only, using XTDB's Clojure API
(`xtdb.api`) and XTQL against an XTDB server running in Docker.

## Run

From this folder:

```sh
docker compose up -d --wait   # XTDB 2.2.0 on port 54323, data in memory
```

Then either jack in from this folder (Calva: *Start a Project REPL and Connect*; CIDER:
`cider-jack-in-clj`), open [`src/bank.clj`](src/bank.clj) and load it, or run `clj` here and:

```clojure
(require 'bank)
(in-ns 'bank)
```

Evaluate the forms in the `comment` block one by one. To replay, run `docker compose restart`:
data lives in memory, and XTDB's system time only moves forward. Stop with
`docker compose down`.

## What to look at

- The writes are data for `xt/execute-tx`: two `put-docs`, the second with a `:valid-from`.
- Both questions run the same query, `customers`. The options pick the point in time:
  `:current-time` sets valid time (Q1), and adding `:snapshot-time` pins system time too (Q2).

## Notes

`deps.edn` lists `next.jdbc` explicitly: `xtdb.api`'s remote client needs it at runtime, but
`xtdb-api` 2.2.0 doesn't declare it. It comes from Clojars; the other dependencies come from
Maven Central.
