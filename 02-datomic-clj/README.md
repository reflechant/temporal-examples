# 02-datomic-clj: Datomic from the REPL, with and without valid time

The same story in Clojure only, using the Datomic peer API directly against a Datomic
transactor running in Docker. There are two independent namespaces, so you can show the gap
and then how it's filled:

| Namespace | Valid time | Q1: what do we now believe was true on 2026-01-10? | Q2: what did we believe on 2026-01-10? |
|---|---|---|---|
| [`bank.without-valid-time`](src/bank/without_valid_time.clj) | none: Datomic as it comes | can't be asked ¹ | `(d/q rating (d/as-of db jan-10))`: LOW |
| [`bank.with-valid-time`](src/bank/with_valid_time.clj) | hand-modelled `:customer/valid-from` | `(d/q rating-on db jan-10)`: HIGH | `(d/q rating-on (d/as-of db jan-10) jan-10)`: LOW |

¹ The current database says HIGH, but that query has no date in it. It matches Q1's answer
only because the correction still holds today. The history even says Alice became HIGH on
2026-01-15, not 2026-01-01.

## Run

From this folder:

```sh
docker compose up -d --wait   # first time: builds an image with Datomic Pro (~270 MB download)
```

Then either jack in from this folder (Calva: *Start a Project REPL and Connect*; CIDER:
`cider-jack-in-clj`), open a namespace file and load it, or run `clj` here and:

```clojure
(require 'bank.without-valid-time)
(in-ns 'bank.without-valid-time)   ; later: bank.with-valid-time
```

Evaluate the forms in the namespace's `comment` block one by one. `(def conn (fresh-conn))`
creates a brand-new database each time, so you can replay the story as often as you like.
Stop with `docker compose down`.

## Notes

- Ports: 4334 (transactor) and 4335 (dev storage, which the peer in your REPL reads directly).
- The hand-modelled `:customer/valid-from` is enough for one "true since" date. Real
  business-time history in Datomic would need an entity per version.
- If connecting fails with `AMQ219007: Cannot connect to server(s)` while the container is
  healthy, check that your JVM doesn't override `javax.net.ssl.trustStore` (for example via
  `JAVA_TOOL_OPTIONS`). The peer talks to the transactor over an encrypted channel, and that
  setting breaks it.
