(ns stitchcraft.api
  (:require [stitchcraft.state :as state]))

(defn base-url []
  (or (some-> js/window .-STITCHCRAFT_CONFIG .-apiUrl) "http://localhost:8000"))

(defn parse-response [response]
  (if (.-ok response)
    (.json response)
    (-> (.json response)
        (.then (fn [body] (throw (js/Error. (or (.-detail body) "Ошибка запроса"))))))))

(defn generate! []
  (let [{:keys [file options]} @state/app-state
        form (js/FormData.)]
    (if-not file
      (state/set-state! :error "Выберите изображение")
      (do
        (state/set-state! :status :generating)
        (state/set-state! :error nil)
        (.append form "image" file)
        (.append form "options" (.stringify js/JSON (clj->js options)))
        (-> (js/fetch (str (base-url) "/patterns") #js {:method "POST" :body form})
            (.then parse-response)
            (.then (fn [body]
                     (state/set-state! :pattern (js->clj body :keywordize-keys true))
                     (state/set-state! :selected-region (some-> (aget body "regions") (aget 0) (aget "id")))
                     (state/set-state! :status :ready)))
            (.catch (fn [error]
                      (state/set-state! :error (.-message error))
                      (state/set-state! :status :idle))))))))

(defn plan! []
  (when-let [pattern (:pattern @state/app-state)]
    (state/set-state! :status :planning)
    (-> (js/fetch (str (base-url) "/patterns/" (:id pattern) "/plan")
                  #js {:method "POST" :headers #js {"Content-Type" "application/json"} :body "{}"})
        (.then parse-response)
        (.then (fn [body]
                 (swap! state/app-state assoc-in [:pattern :plans] (js->clj (aget body "plans") :keywordize-keys false))
                 (state/set-state! :status :ready)))
        (.catch (fn [error]
                  (state/set-state! :error (.-message error))
                  (state/set-state! :status :ready))))))

(defn export-url [pattern-id] (str (base-url) "/patterns/" pattern-id "/export"))
(defn facts-url [pattern-id region-id] (str (base-url) "/patterns/" pattern-id "/regions/" region-id "/facts"))
