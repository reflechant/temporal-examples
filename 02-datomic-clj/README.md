# 02 (Clojure variant): System time for free with Datomic, from the REPL

The same story as [`02-datomic`](../02-datomic), in Clojure only, using the Datomic peer API
directly. Datomic runs in Docker; you play with it from a REPL.

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
the story as often as you like.

The two questions are the same query, `rating-on`, against two database values:
`(d/db conn)` for Q1 and `(d/as-of (d/db conn) jan-10)` for Q2.

Ports: 4334 (transactor) and 4335 (dev storage, which the peer in your REPL reads directly).

If connecting fails with `AMQ219007: Cannot connect to server(s)` while the container is
healthy, check that your JVM doesn't override `javax.net.ssl.trustStore` (for example via
`JAVA_TOOL_OPTIONS`). The peer talks to the transactor over an encrypted channel, and that
setting breaks it.
