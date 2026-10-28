# 02 (Clojure variant): System time for free with Datomic, from the REPL

The same story as [`02-datomic`](../02-datomic), in Clojure only, using the Datomic peer
API directly (no REST server, no Python). Datomic runs in Docker; you play with it from a REPL.

```sh
docker compose up -d --wait   # transactor + dev storage; first build downloads Datomic Pro (~270 MB)
clj                           # or jack in from your editor: deps.edn in this folder
```

```clojure
(require 'bank)
(in-ns 'bank)
```

Then evaluate the forms in the `comment` block at the bottom of [`src/bank.clj`](src/bank.clj)
one by one. `(def conn (fresh-conn))` creates a brand-new database each time, so you can replay
the story as often as you like. The story pins transaction times, which can only move forward
within one database.

What's in [`src/bank.clj`](src/bank.clj):

- `schema`, `onboarding`, `limit-raise`, `kyc-correction`: plain data. Who and why are
  attributes of the transaction entity.
- `report`, `audit-trail`, `changed-since`: queries with no time in them. The point in time
  comes from the database value you pass: `(d/as-of db t)`, `(d/history db)`,
  `(d/since db t)` ([filters docs](https://docs.datomic.com/reference/filters.html)).
- The `comment` block: the talk's four auditor questions, then extras to play with: `pull`
  at any point in time, transactions as entities, what-if with `d/with`, raw datoms.

Ports: 4334 (transactor) and 4335 (dev storage, which the peer in your REPL reads directly).

If connecting fails with `AMQ219007: Cannot connect to server(s)` while the container is
healthy, check that your JVM doesn't override `javax.net.ssl.trustStore` (for example via
`JAVA_TOOL_OPTIONS`). The peer talks to the transactor over an encrypted channel, and that
setting breaks it.
