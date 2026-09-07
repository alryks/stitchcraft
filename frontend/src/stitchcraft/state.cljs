(ns stitchcraft.state
  (:require [reagent.core :as r]))

(def defaults
  {:width 72 :height nil :size_unit "stitches" :physical_size 18 :size_axis "width"
   :canvas_count 14 :palette "dmc" :max_colors 14 :blends true :half_cross true
   :backstitch true :min_component_size 3 :thread_length_mm 1000 :strands 2
   :fold_parts 2 :needle_length_mm 40 :canvas_color nil})

(defonce app-state
  (r/atom {:options defaults :file nil :preview nil :pattern nil :status :idle :error nil
           :zoom 1.0 :hidden-colors #{} :selected-color nil :selected-region nil :drag-over false
           :route-step 99999 :show-backstitch true :panel :materials
           :left-panel-open true :right-panel-open true}))

(defn set-option! [key value] (swap! app-state assoc-in [:options key] value))
(defn set-state! [key value] (swap! app-state assoc key value))
(defn toggle-set! [key value] (swap! app-state update key #(if (contains? % value) (disj % value) (conj % value))))
