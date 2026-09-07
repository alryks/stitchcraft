(ns stitchcraft.canvas
  (:require [reagent.core :as r]
            [stitchcraft.state :as state]))

(def margin 28)

(defn color-map [pattern] (into {} (map (juxt :id identity) (:colors pattern))))

(defn route-points [pattern region-id]
  (let [plan (get (:plans pattern) region-id)]
    (->> (:segments plan) (mapcat :route) vec)))

(defn draw! [canvas pattern zoom hidden selected-color selected-region route-step show-backstitch]
  (when (and canvas pattern)
    (let [cell (* 12 zoom) width (:width pattern) height (:height pattern)
          pixel-width (+ margin (* width cell)) pixel-height (+ margin (* height cell))
          ctx (.getContext canvas "2d") colors (color-map pattern)]
      (set! (.-width canvas) pixel-width)
      (set! (.-height canvas) pixel-height)
      (set! (.-fillStyle ctx) "#f9faf8") (.fillRect ctx 0 0 pixel-width pixel-height)
      (doseq [{:keys [x y primary_color secondary_color symbol stitch_type region_id]} (:stitches pattern)]
        (when-not (contains? hidden primary_color)
          (let [color (get colors primary_color) active? (or (nil? selected-color) (= selected-color primary_color))
                alpha (if active? 1 0.16) px (+ margin (* x cell)) py (+ margin (* y cell))]
            (set! (.-globalAlpha ctx) alpha)
            (set! (.-fillStyle ctx) (:hex color))
            (if (= stitch_type "full")
              (.fillRect ctx px py cell cell)
              (do (.beginPath ctx) (.moveTo ctx px py)
                  (if (= stitch_type "half_forward")
                    (do (.lineTo ctx (+ px cell) py) (.lineTo ctx (+ px cell) (+ py cell)))
                    (do (.lineTo ctx px (+ py cell)) (.lineTo ctx (+ px cell) (+ py cell))))
                  (.closePath ctx) (.fill ctx)))
            (when (and secondary_color (>= cell 10))
              (set! (.-strokeStyle ctx) (:hex (get colors secondary_color)))
              (set! (.-lineWidth ctx) (/ cell 3)) (.beginPath ctx)
              (.moveTo ctx (+ px 2) (+ py cell -2)) (.lineTo ctx (+ px cell -2) (+ py 2)) (.stroke ctx))
            (when (and (= selected-region region_id) (> cell 8))
              (set! (.-strokeStyle ctx) "#ff2f6d") (set! (.-lineWidth ctx) 2)
              (.strokeRect ctx (+ px 1) (+ py 1) (- cell 2) (- cell 2)))
            (when (>= cell 14)
              (set! (.-fillStyle ctx) (if (> (reduce + (:rgb color)) 390) "#18202b" "#ffffff"))
              (set! (.-font ctx) (str (max 7 (* 0.46 cell)) "px 'IBM Plex Mono'"))
              (set! (.-textAlign ctx) "center") (set! (.-textBaseline ctx) "middle")
              (.fillText ctx symbol (+ px (/ cell 2)) (+ py (/ cell 2)))))
          (set! (.-globalAlpha ctx) 1)))
      (set! (.-strokeStyle ctx) "rgba(41,57,76,.18)") (set! (.-lineWidth ctx) 0.5)
      (doseq [x (range (inc width))]
        (set! (.-lineWidth ctx) (if (zero? (mod x 10)) 1.6 0.45))
        (.beginPath ctx) (.moveTo ctx (+ margin (* x cell)) margin)
        (.lineTo ctx (+ margin (* x cell)) (+ margin (* height cell))) (.stroke ctx))
      (doseq [y (range (inc height))]
        (set! (.-lineWidth ctx) (if (zero? (mod y 10)) 1.6 0.45))
        (.beginPath ctx) (.moveTo ctx margin (+ margin (* y cell)))
        (.lineTo ctx (+ margin (* width cell)) (+ margin (* y cell))) (.stroke ctx))
      (set! (.-fillStyle ctx) "#586577") (set! (.-font ctx) "8px 'IBM Plex Mono'")
      (doseq [x (range 0 width 10)] (.fillText ctx (str x) (+ margin (* x cell) 7) 15))
      (doseq [y (range 0 height 10)] (.fillText ctx (str y) 12 (+ margin (* y cell) 9)))
      (when show-backstitch
        (set! (.-strokeStyle ctx) "#222530") (set! (.-lineWidth ctx) (max 1.4 (* zoom 1.2)))
        (doseq [{:keys [from_x from_y to_x to_y]} (:backstitch pattern)]
          (.beginPath ctx) (.moveTo ctx (+ margin (* from_x cell)) (+ margin (* from_y cell)))
          (.lineTo ctx (+ margin (* to_x cell)) (+ margin (* to_y cell))) (.stroke ctx)))
      (let [points (take route-step (route-points pattern selected-region))]
        (when (seq points)
          (set! (.-strokeStyle ctx) "#ff2f6d") (set! (.-lineWidth ctx) (max 2 (* zoom 2)))
          (set! (.-lineJoin ctx) "round") (.beginPath ctx)
          (doseq [[index point] (map-indexed vector points)]
            (let [px (+ margin (* (+ (:x point) 0.5) cell)) py (+ margin (* (+ (:y point) 0.5) cell))]
              (if (zero? index) (.moveTo ctx px py) (.lineTo ctx px py))))
          (.stroke ctx))))))

(defn pattern-canvas []
  (let [node (atom nil) drag (atom nil)]
    (r/create-class
      {:display-name "pattern-canvas"
       :component-did-mount #(let [{:keys [pattern zoom hidden-colors selected-color selected-region route-step show-backstitch]} @state/app-state]
                               (draw! @node pattern zoom hidden-colors selected-color selected-region route-step show-backstitch))
       :component-did-update #(let [{:keys [pattern zoom hidden-colors selected-color selected-region route-step show-backstitch]} @state/app-state]
                                (draw! @node pattern zoom hidden-colors selected-color selected-region route-step show-backstitch))
       :reagent-render
       (fn []
         (let [{:keys [pattern zoom hidden-colors selected-color selected-region route-step show-backstitch]} @state/app-state
               cell (* 12 zoom)]
           [:div.pattern-scroll
            {:on-mouse-down (fn [event]
                              (reset! drag {:x (.-clientX event) :y (.-clientY event)
                                            :left (.-scrollLeft (.-currentTarget event))
                                            :top (.-scrollTop (.-currentTarget event))}))
             :on-mouse-move (fn [event]
                              (when-let [start @drag]
                                (let [target (.-currentTarget event)]
                                  (set! (.-scrollLeft target) (- (:left start) (- (.-clientX event) (:x start))))
                                  (set! (.-scrollTop target) (- (:top start) (- (.-clientY event) (:y start)))))))
             :on-mouse-up #(reset! drag nil) :on-mouse-leave #(reset! drag nil)}
            [:canvas {:ref #(reset! node %)
                      :aria-label "Интерактивная схема вышивки"
                      :on-click (fn [event]
                                  (let [rect (.getBoundingClientRect @node)
                                        x (js/Math.floor (/ (- (.-clientX event) (.-left rect) margin) cell))
                                        y (js/Math.floor (/ (- (.-clientY event) (.-top rect) margin) cell))]
                                    (when (and (>= x 0) (>= y 0) (< x (:width pattern)) (< y (:height pattern)))
                                      (let [stitch (nth (:stitches pattern) (+ x (* y (:width pattern))))]
                                        (state/set-state! :selected-region (:region_id stitch))
                                        (state/set-state! :selected-color (:primary_color stitch))))))}]]))})))

