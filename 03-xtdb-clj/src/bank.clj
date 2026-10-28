(ns bank
  "Alice's risk rating in XTDB: both time axes (when it was true, when we knew it) are built in.

  REPL-first: start XTDB with `docker compose up -d --wait`, jack in (Calva/CIDER) in this
  folder, then evaluate the forms in the `comment` block at the bottom, one by one."
  (:require [xtdb.api :as xt]))

(def node
  "A client to the XTDB server in Docker (a DataSource: opens connections as needed)."
  (xt/client {:port 54323}))

;; No schema: tables and columns appear on first write. :system-time is pinned only to
;; replay January; normally it's the transaction's own time.

(def record-alice                       ; true from now on: the default
  {:ops  [[:put-docs :customers {:xt/id 1 :name "Alice" :risk-rating "LOW"}]]
   :opts {:system-time #inst "2026-01-01T09:00:00Z"}})                      ; demo clock

(def correct-alice                      ; true since 2026-01-01: backdated
  {:ops  [[:put-docs {:into :customers :valid-from #inst "2026-01-01T00:00:00Z"}
           {:xt/id 1 :name "Alice" :risk-rating "HIGH"}]]
   :opts {:system-time #inst "2026-01-15T10:00:00Z"}})                      ; demo clock

(defn transact! [{:keys [ops opts]}]
  (xt/execute-tx node ops opts))

;; Both questions use this one query. Which question it answers depends only on the options:
;;   :current-time = valid time (when it was true), :snapshot-time = system time (when we knew it).
(def customers
  '(from :customers [xt/id name risk-rating xt/valid-from]))

(comment
  ;; 2026-01-01  the bank records Alice as LOW risk
  (transact! record-alice)

  ;; 2026-01-10  the bank approves a loan, based on LOW
  (def jan-10 #inst "2026-01-10T12:00:00Z")

  ;; 2026-01-15  the bank discovers Alice should have been HIGH since 2026-01-01
  (transact! correct-alice)

  ;; Q1: what do we now believe was true on 2026-01-10?
  (xt/q node customers {:current-time jan-10})

  ;; Q2: what did we believe on 2026-01-10?
  (xt/q node customers {:current-time jan-10 :snapshot-time jan-10})

  ;; to replay: system time only moves forward, so restart the (in-memory) node
  ;;   docker compose restart
  )
