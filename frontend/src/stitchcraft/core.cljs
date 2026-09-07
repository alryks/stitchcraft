(ns stitchcraft.core
  (:require [reagent.core :as r]
            [reagent.dom.client :as rdom]
            [stitchcraft.api :as api]
            [stitchcraft.canvas :as pattern-canvas]
            [stitchcraft.state :as state]))

(defonce root (atom nil))

(defn logo []
  [:div.brand
   [:svg {:viewBox "0 0 42 42" :aria-hidden true}
    [:path {:d "M5 5h14v14H5zM23 5h14v14H23zM5 23h14v14H5z"}]
    [:path.accent {:d "M23 23h14v14H23zM25 25l10 10m0-10L25 35"}]]
   [:div [:strong "Нить"] [:span "Конструктор схем"]]])

(defn field [label child & [hint]]
  [:label.field [:span label] child (when hint [:small hint])])

(defn number-input [key opts]
  [:input (merge {:type "number" :value (or (get-in @state/app-state [:options key]) "")
                  :on-change #(state/set-option! key (let [value (.. % -target -value)]
                                                       (when-not (= value "") (js/Number value))))} opts)])

(defn toggle [key label]
  [:label.toggle
   [:input {:type "checkbox" :checked (true? (get-in @state/app-state [:options key]))
            :on-change #(state/set-option! key (.. % -target -checked))}]
   [:span.switch] [:span label]])

(defn upload-card []
  (let [{:keys [preview file]} @state/app-state]
    [:div.upload-card {:class (when preview "has-preview")}
     (if preview
       [:img {:src preview :alt "Исходное изображение"}]
       [:div.upload-empty [:span.thread-loop "×"] [:strong "Перетащите изображение"] [:span "или выберите файл до 12 МБ"]])
     [:label.upload-action
      [:input {:type "file" :accept "image/png,image/jpeg,image/webp"
               :on-change (fn [event]
                            (when-let [next-file (aget (.. event -target -files) 0)]
                              (when preview (js/URL.revokeObjectURL preview))
                              (swap! state/app-state assoc :file next-file :preview (js/URL.createObjectURL next-file) :error nil)))}]
      (if file "Заменить изображение" "Выбрать изображение")]]))

(defn options-panel []
  (let [options (:options @state/app-state)]
    [:aside.settings
     [upload-card]
     [:section.control-group
      [:h2 "Размер схемы"]
      [:div.segmented
       [:button {:class (when (= "stitches" (:size_unit options)) "active") :on-click #(state/set-option! :size_unit "stitches")} "Крестики"]
       [:button {:class (when (= "cm" (:size_unit options)) "active") :on-click #(state/set-option! :size_unit "cm")} "Сантиметры"]]
      [field "Опорная сторона"
       [:select {:value (:size_axis options)
                 :on-change (fn [event]
                              (let [axis (.. event -target -value)]
                                (state/set-option! :size_axis axis)
                                (when (= "stitches" (:size_unit options))
                                  (let [current (or (:width options) (:height options) 72)]
                                    (state/set-option! :width (when (= axis "width") current))
                                    (state/set-option! :height (when (= axis "height") current))))))}
        [:option {:value "width"} "Ширина"]
        [:option {:value "height"} "Высота"]]]
      (if (= "stitches" (:size_unit options))
        [field (if (= "width" (:size_axis options)) "Ширина" "Высота")
         [number-input (if (= "width" (:size_axis options)) :width :height) {:min 8 :max 220 :step 1}]
         "Вторая сторона сохранит пропорции"]
        [field (if (= "width" (:size_axis options)) "Ширина вышивки" "Высота вышивки")
         [number-input :physical_size {:min 2 :max 100 :step 1}] "см"])
      [:div.two-fields
       [field "Канва" [:select {:value (:canvas_count options) :on-change #(state/set-option! :canvas_count (js/Number (.. % -target -value)))}
                         (for [count [11 14 16 18]] ^{:key count} [:option {:value count} (str "Aida " count)])]]
       [field "Цветов" [number-input :max_colors {:min 2 :max 40 :step 1}]]]]
     [:section.control-group
      [:h2 "Нити и стежки"]
      [field "Палитра" [:select {:value (:palette options) :on-change #(state/set-option! :palette (.. % -target -value))}
                         [:option {:value "dmc"} "DMC"] [:option {:value "anchor"} "Anchor"]]]
      [field "Цвет канвы"
       [:select {:value (or (:canvas_color options) "")
                 :on-change #(let [value (.. % -target -value)] (state/set-option! :canvas_color (when-not (= value "") value)))}
        [:option {:value ""} "Подобрать автоматически"]
        [:option {:value "white"} "Белая"]
        [:option {:value "antique-white"} "Античная белая"]
        [:option {:value "natural"} "Натуральный лён"]
        [:option {:value "black"} "Чёрная"]
        [:option {:value "navy"} "Тёмно-синяя"]
        [:option {:value "pale-blue"} "Бледно-голубая"]]]
      [:div.toggle-stack [toggle :blends "Смешанные цвета"] [toggle :half_cross "Полукрест на границах"] [toggle :backstitch "Шов назад иголку"]]
      [:details.advanced
       [:summary "Расход и очистка"]
       [:div.two-fields
        [field "Отрезок, мм" [number-input :thread_length_mm {:min 200 :max 3000 :step 50}]]
        [field "Рабочих нитей" [number-input :strands {:min 1 :max 6 :step 1}]]]
       [:div.two-fields
        [field "Сложение" [:select {:value (:fold_parts options) :on-change #(state/set-option! :fold_parts (js/Number (.. % -target -value)))}
                           [:option {:value 2} "Пополам"] [:option {:value 3} "На 3 части"]]]
        [field "Min. участок" [number-input :min_component_size {:min 1 :max 20 :step 1}]]]]]
     [:button.primary-action {:on-click api/generate! :disabled (contains? #{:generating :planning} (:status @state/app-state))}
      (if (= :generating (:status @state/app-state)) [:<> [:span.spinner] "Строю схему…"] "Создать схему")]
     (when-let [error (:error @state/app-state)] [:p.error-message error])]))

(defn empty-workspace []
  [:div.empty-workspace
   [:div.mini-grid (for [i (range 64)] ^{:key i} [:i {:class (when (contains? #{18 19 26 27 28 35 36 43} i) "marked")}])]
   [:h1 "Из изображения — в понятную схему"]
   [:p "Загрузите фотографию или рисунок. Система сохранит заметные контуры, подберёт реальные цвета мулине и рассчитает удобный порядок вышивания."]
   [:div.capabilities [:span "DMC и Anchor"] [:span "Маршрут нити"] [:span "Печатный лист"]]])

(defn metric-strip [pattern]
  (let [m (:metrics pattern)]
    [:div.metric-strip
     [:div [:b (:color_count m)] [:span "цветов"]]
     [:div [:b (:regions m)] [:span "участков"]]
     [:div [:b (:mean_delta_e m)] [:span "ΔE"]]
     [:div [:b (str (js/Math.round (* 100 (:ssim m))) "%")] [:span "сходство"]]]))

(defn canvas-toolbar [pattern]
  (let [{:keys [zoom show-backstitch]} @state/app-state]
    [:div.canvas-toolbar
     [:div
      [:strong (str (:width pattern) " × " (:height pattern))]
      [:span (str (:physical_width_mm pattern) " × " (:physical_height_mm pattern) " мм")]]
     [:div.toolbar-actions
      [:label.zoom-control [:span "Масштаб"] [:input {:type "range" :min 0.65 :max 2.5 :step 0.05 :value zoom
                                                       :on-change #(state/set-state! :zoom (js/Number (.. % -target -value)))}] [:b (str (js/Math.round (* zoom 100)) "%")]]
      [:button.icon-button {:class (when show-backstitch "active") :title "Показать backstitch"
                            :on-click #(state/set-state! :show-backstitch (not show-backstitch))} "⌁"]]]))

(defn color-list [pattern]
  (let [{:keys [hidden-colors selected-color]} @state/app-state
        counts (frequencies (map :primary_color (:stitches pattern)))]
    [:div.color-list
     (for [color (:colors pattern)]
       (let [id (:id color) hidden? (contains? hidden-colors id)]
         ^{:key id}
         [:button.color-row {:class (str (when (= selected-color id) "selected ") (when hidden? "hidden"))
                             :on-click #(state/set-state! :selected-color (when-not (= selected-color id) id))}
          [:span.swatch {:style {:background (:hex color)}} (:symbol color)]
          [:span.color-copy [:strong id] [:small (:name color)]]
          [:span.count (get counts id 0)]
          [:span.eye {:on-click (fn [event] (.stopPropagation event) (state/toggle-set! :hidden-colors id))} (if hidden? "○" "●")]]))]))

(defn materials-panel [pattern]
  (let [{:keys [canvas needle threads total_thread_m]} (:materials pattern)]
    [:div.panel-content
     [:div.material-hero
      [:div.canvas-swatch {:style {:background (str "rgb(" (.join (clj->js (:rgb canvas)) ",") ")")}}]
      [:div [:span "Канва"] [:strong (str "Aida " (:count canvas) ", " (:name canvas))]
       [:small (str (:width_mm canvas) " × " (:height_mm canvas) " мм")]]]
     [:div.needle-line [:span "Иголка"] [:b (str (:type needle) " №" (:size needle))]]
     [:div.panel-heading [:h3 "Мулине"] [:span (str total_thread_m " м всего")]]
     [:div.thread-list
      (for [thread threads]
        ^{:key (:id thread)} [:div.thread-row [:i {:style {:background (:hex thread)}}] [:b (:id thread)]
                              [:span (:metres thread) " м"] [:em (:skeins thread) " мот."]])]]))

(defn route-panel [pattern]
  (let [region-id (:selected-region @state/app-state)
        plan (get (:plans pattern) region-id)
        max-steps (reduce + 0 (map #(count (:route %)) (:segments plan)))
        step (:route-step @state/app-state)]
    [:div.panel-content
     [:div.panel-heading [:h3 "Маршрут иглы"] [:span (or region-id "Выберите клетку")]]
     (if plan
       [:<>
        [:div.route-method [:span "Метод"] [:strong (case (:method plan) "danish" "Датский" "english" "Английский" "mixed" "Смешанный" (:method plan))]]
        [:label.step-control [:span (str "Показано: " (min step max-steps) " / " max-steps)]
         [:input {:type "range" :min 1 :max (max 1 max-steps) :value (min step (max 1 max-steps))
                  :on-change #(state/set-state! :route-step (js/Number (.. % -target -value)))}]]
        [:div.route-stats
         [:div [:b (get-in plan [:stats :thread_segments])] [:span "отрезков"]]
         [:div [:b (str (js/Math.round (get-in plan [:stats :total_thread_mm])) " мм")] [:span "нить"]]
         [:div [:b (get-in plan [:stats :diagonal_moves])] [:span "диагоналей"]]]
        [:div.segment-list
         (for [[index segment] (map-indexed vector (:segments plan))]
           ^{:key index} [:div [:b (str "Отрезок " (inc index))] [:span (str (count (:stitches segment)) " ст. · " (:length_mm segment) " мм")]])]]
       [:div.route-empty
        [:p (if (seq (:plans pattern)) "Для выбранного участка маршрут ещё не рассчитан." "Prolog выберет метод и разделит участки по длине нити.")]
        [:button.secondary-action {:on-click api/plan! :disabled (= :planning (:status @state/app-state))}
         (if (= :planning (:status @state/app-state)) "Планирую…" "Оптимизировать маршрут")]])]))

(defn inspector [pattern]
  (let [panel (:panel @state/app-state)]
    [:aside.inspector
     [:div.panel-tabs
      [:button {:class (when (= panel :materials) "active") :on-click #(state/set-state! :panel :materials)} "Материалы"]
      [:button {:class (when (= panel :colors) "active") :on-click #(state/set-state! :panel :colors)} "Цвета"]
      [:button {:class (when (= panel :route) "active") :on-click #(state/set-state! :panel :route)} "Маршрут"]]
     (case panel :colors [color-list pattern] :route [route-panel pattern] [materials-panel pattern])
     [:div.export-actions
      [:a.secondary-action {:href (api/export-url (:id pattern)) :target "_blank" :rel "noreferrer"} "Открыть печатную схему"]
      (when-let [region (:selected-region @state/app-state)]
        [:a.text-link {:href (api/facts-url (:id pattern) region) :target "_blank" :rel "noreferrer"} "Факты Prolog участка"])] ]))

(defn workspace [pattern]
  [:<>
   [:main.workspace
    [options-panel]
    [:section.pattern-stage [canvas-toolbar pattern] [pattern-canvas/pattern-canvas] [metric-strip pattern]]
    [inspector pattern]]])

(defn app []
  (let [pattern (:pattern @state/app-state)]
    [:div.app-shell
     [:header.topbar [logo]
      [:div.top-note [:i] [:span "Backend + Prolog готовы к работе"]]]
     (if pattern
       [workspace pattern]
       [:main.workspace
        [options-panel]
        [:section.pattern-stage [empty-workspace]]
        [:aside.inspector.intro-panel
         [:h2 "Рабочий порядок"]
         [:ol
          [:li "Настройте размер и палитру"]
          [:li "Создайте схему"]
          [:li "Оптимизируйте маршрут"]
          [:li "Распечатайте результат"]]]])]))

(defn ^:dev/after-load reload! []
  (when @root (.render @root (r/as-element [app]))))

(defn init []
  (reset! root (rdom/create-root (.getElementById js/document "app")))
  (reload!))
