(ns bank
  "Credit file in XTDB: both time axes (when it was true, when we knew it) are built in.

  REPL-first: start XTDB with `docker compose up -d --wait`, jack in (Calva/CIDER) in this
  folder, then evaluate the forms in the `comment` block at the bottom, one by one."
  (:require [clojure.pprint :refer [print-table]]
            [xtdb.api :as xt]))

(def node
  "A client to the XTDB server in Docker (a DataSource: opens connections as needed)."
  (xt/client {:port 54323}))

;; ---------------------------------------------------------------- the story, as data
;; No schema: tables and columns appear on first write. Every write is versioned on both axes.
;; Who and why go into the transaction's metadata (queryable in the `xt/txs` table).
;; :system-time is pinned only to replay the story; normally it's the transaction's own time.

(def onboarding
  {:ops  [[:put-docs :customers
           {:xt/id "ACME"   :risk "LOW"    :credit-limit 1000000}
           {:xt/id "GLOBEX" :risk "MEDIUM" :credit-limit 500000}]]
   :opts {:system-time #inst "2026-01-10T09:00:00Z" :metadata {:by "alice" :reason "onboarding"}}})

(def limit-raise                        ; true from now on: the default
  {:ops  [[:patch-docs :customers {:xt/id "ACME" :credit-limit 2000000}]]
   :opts {:system-time #inst "2026-02-01T10:00:00Z" :metadata {:by "alice" :reason "annual review"}}})

(def kyc-correction                     ; true since 2026-01-20: backdated, one clause
  ;; patch-docs can't take a valid-time range from a remote client yet, so this one is SQL
  {:ops  [["UPDATE customers FOR PORTION OF VALID_TIME FROM TIMESTAMP '2026-01-20T00:00:00Z'
            SET risk = 'HIGH' WHERE _id = 'ACME'"]]
   :opts {:system-time #inst "2026-04-07T14:00:00Z"
          :metadata {:by "bob" :reason "KYC-123 adverse media dated 2026-01-20"}}})

(def dba-hotfix                         ; a plain UPDATE, straight from a SQL console
  {:ops  [["UPDATE customers SET credit_limit = 600000 WHERE _id = 'GLOBEX'"]]
   :opts {:system-time #inst "2026-04-08T08:00:00Z" :metadata {:by "dba" :reason "OPS-77"}}})

(defn transact! [{:keys [ops opts]}]
  (xt/execute-tx node ops opts))

;; ---------------------------------------------------------------- the auditor's questions (XTQL)
;; `report` mentions no time at all: time comes from the query options,
;;   :snapshot-time = system time (what the database knew), :current-time = valid time (when).

(def report
  '(-> (from :customers [{:xt/id customer} risk credit-limit])
       (order-by customer)))

(def filed-vs-actual                    ; one table, two points of system time, joined
  '(fn [t]
     (-> (unify (from :customers {:bind [{:xt/id customer} {:risk filed-risk} {:credit-limit filed-limit}]
                                  :for-valid-time (at t) :for-system-time (at t)})
                (from :customers {:bind [{:xt/id customer} {:risk actual-risk} {:credit-limit actual-limit}]
                                  :for-valid-time (at t)}))
         (where (or (<> filed-risk actual-risk) (<> filed-limit actual-limit)))
         (return customer filed-risk actual-risk filed-limit actual-limit))))

(def audit-trail                        ; every version on both axes, with who/why of its tx
  '(fn [id]
     (-> (unify (from :customers {:bind [{:xt/id id} risk credit-limit
                                         xt/valid-from xt/valid-to xt/system-from xt/system-to]
                                  :for-valid-time :all-time :for-system-time :all-time})
                (from :xt/txs [{:system-time xt/system-from} user-metadata]))
         (with {:by (. user-metadata by)} {:why (. user-metadata reason)})
         (return risk credit-limit xt/valid-from xt/valid-to xt/system-from xt/system-to by why)
         (order-by xt/system-from xt/valid-from))))

;; ---------------------------------------------------------------- play

(comment
  ;; 2026-01-10  alice onboards two customers
  (transact! onboarding)

  ;; 2026-02-01  alice raises ACME's limit
  (transact! limit-raise)

  ;; 2026-03-31  Q1 report: what we knew at quarter end, about quarter end
  (def q1-end #inst "2026-03-31T18:00:00Z")
  (print-table (xt/q node report {:snapshot-time q1-end :current-time q1-end}))

  ;; 2026-04-07  bob: adverse media about ACME dated 2026-01-20 -> HIGH risk, backdated
  (transact! kyc-correction)

  ;; Auditor 1) reproduce the filed report exactly: same query, same two times
  (print-table (xt/q node report {:snapshot-time q1-end :current-time q1-end}))

  ;; Auditor 2) what was really true at quarter end, with what we know today?
  (print-table (xt/q node report {:current-time q1-end}))

  ;; Auditor 3) which figures in the filed report are now known to be wrong?
  (print-table (xt/q node [filed-vs-actual q1-end]))

  ;; Auditor 4) full history of ACME: who changed what, when, why
  (print-table [:risk :credit-limit :xt/valid-from :xt/valid-to :xt/system-from :xt/system-to :by :why]
               (xt/q node [audit-trail "ACME"]))

  ;; The 'obvious' query: no options means now / now. One row per customer.
  (print-table (xt/q node report))

  ;; 2026-04-08  a DBA hotfixes GLOBEX's limit with a plain UPDATE ...
  (transact! dba-hotfix)
  ;; ... and the filed report is untouched
  (print-table (xt/q node report {:snapshot-time q1-end :current-time q1-end}))

  ;; ------------------------------------------------ more to play with

  ;; the same time options work for SQL
  (print-table (xt/q node "SELECT _id, risk, credit_limit FROM customers ORDER BY _id"
                     {:snapshot-time q1-end :current-time q1-end}))

  ;; ACME's risk over business time, as we know it today
  (print-table (xt/q node '(-> (from :customers {:bind [{:xt/id "ACME"} risk xt/valid-from xt/valid-to]
                                                 :for-valid-time :all-time})
                               (order-by xt/valid-from))))

  ;; ... and as we knew it at quarter end
  (print-table (xt/q node '(-> (from :customers {:bind [{:xt/id "ACME"} risk xt/valid-from xt/valid-to]
                                                 :for-valid-time :all-time
                                                 :for-system-time (at #inst "2026-03-31T18:00:00Z")})
                               (order-by xt/valid-from))))

  ;; the transaction log, with its metadata
  (print-table (xt/q node '(-> (from :xt/txs [xt/id system-time committed user-metadata])
                               (order-by system-time))))

  ;; to replay the story: system time only moves forward, so restart the (in-memory) node
  ;;   docker compose restart
  )
