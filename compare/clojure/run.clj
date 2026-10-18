;;;; Run a mini-basic program with Clojure:
;;;;   java -cp "<clojure jars>" clojure.main compare/clojure/run.clj program.lisp

(load-file (str (.getParent (java.io.File. ^String *file*)) "/mini_basic.clj"))

;; Programs see the statements and only the arithmetic and comparisons of clojure.core
(def bbc-user (create-ns 'bbc-user))

(binding [*ns* bbc-user]
  (refer 'clojure.core :only '[+ - * / < > <= >= = == not= not mod])
  (refer 'mini-basic)
  (load-file (first *command-line-args*)))
