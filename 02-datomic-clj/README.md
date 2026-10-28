# 02 (Clojure variant): System time for free with Datomic, from the REPL

The same story as [`02-datomic`](../02-datomic), in Clojure only, using the Datomic peer API
directly. Datomic runs in Docker; you play with it from a REPL. There are two independent
namespaces, so you can show the gap and then how it's filled:

| Namespace | Valid time | Q2: what did we believe on 2026-01-10? | Q1: what do we now believe was true on 2026-01-10? |
|---|---|---|---|
| [`bank.without-valid-time`](src/bank/without_valid_time.clj) | none: Datomic as it comes | `(d/q rating (d/as-of db jan-10))`: LOW | can't be asked; the history even says Alice became HIGH on 2026-01-15 |
| [`bank.with-valid-time`](src/bank/with_valid_time.clj) | modelled by hand: `:customer/valid-from` | same query `as-of` 2026-01-10: LOW | same query against the current db: HIGH |

The hand-modelled `:customer/valid-from` is enough here (one customer, one "true since" date).
Real business-time history in Datomic would need an entity per version, which means building
a bitemporal database yourself.

```sh
docker compose up -d --wait   # transactor + dev storage; first build downloads Datomic Pro (~270 MB)
clj                           # or jack in from your editor: deps.edn in this folder
```

```clojure
(require 'bank.without-valid-time)
(in-ns 'bank.without-valid-time)   ; later: bank.with-valid-time
```

Then evaluate the forms in the namespace's `comment` block one by one. `(def conn (fresh-conn))`
creates a brand-new database each time, so you can replay the story as often as you like.

Ports: 4334 (transactor) and 4335 (dev storage, which the peer in your REPL reads directly).

If connecting fails with `AMQ219007: Cannot connect to server(s)` while the container is
healthy, check that your JVM doesn't override `javax.net.ssl.trustStore` (for example via
`JAVA_TOOL_OPTIONS`). The peer talks to the transactor over an encrypted channel, and that
setting breaks it.
