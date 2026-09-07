# Цель

Разработать законченную систему, которая по исходному изображению и пользовательским параметрам генерирует схему вышивки крестиком, оптимизированную по визуальному сходству с изображением и удобству реального процесса вышивания.

Система должна:

* преобразовывать изображение в сетку крестиков заданного размера;
* использовать реальные палитры мулине;
* подбирать канву и материалы;
* уменьшать количество мелких разрозненных цветовых участков;
* поддерживать full cross, half cross, blended colors и backstitch;
* учитывать физическую длину нити;
* строить удобный порядок вышивания;
* учитывать английский, датский и смешанный способы вышивания;
* ограничивать неудобные переходы нити;
* использовать Prolog как содержательную часть логики;
* использовать ClojureScript как часть функционального программирования и пользовательского интерфейса;
* полностью запускаться через Docker Compose без необходимости вручную устанавливать Python, SWI-Prolog, Node.js/Clojure tooling или другие зависимости на хостовую систему.

---

# 1. Технологический стек

Использовать следующую архитектуру.

## Python

Основной вычислительный backend.

Ответственность:

* загрузка и обработка изображения;
* изменение масштаба;
* пикселизация;
* анализ цвета;
* сопоставление с палитрами нитей;
* сегментация;
* удаление confetti;
* определение акцентных областей;
* построение backstitch;
* расчёт цветовых ошибок;
* работа с blended colors;
* подготовка данных для Prolog;
* расчёт материалов;
* генерация схемы и экспорта.

Предпочтительные библиотеки:

* Pillow;
* NumPy;
* OpenCV;
* scikit-image;
* scikit-learn, если понадобится кластеризация;
* FastAPI для API backend.

---

## Prolog

Использовать как систему правил и планировщик процесса вышивания.

Prolog не должен заниматься компьютерным зрением.

Ему передаются уже сформированные участки схемы.

Ответственность:

* проверка допустимости переходов между крестиками;
* предпочтение горизонтальных и вертикальных переходов;
* ограничение диагональных переходов;
* выбор English / Danish / mixed method;
* построение порядка вышивания связного участка;
* расчёт переходов по изнанке;
* контроль оставшейся длины нити;
* разбиение участка на несколько отрезков нити;
* применение экспертных правил;
* оценка качества нескольких возможных маршрутов.

Использовать SWI-Prolog.

---

## ClojureScript

Использовать для frontend.

Желательный стек:

* ClojureScript;
* Reagent или другой React wrapper.

Ответственность:

* загрузка изображения;
* настройка параметров;
* отображение исходного изображения;
* интерактивная схема вышивки;
* отображение используемых цветов;
* просмотр отдельных цветовых слоёв;
* визуализация backstitch;
* отображение маршрута иглы;
* пошаговое отображение порядка вышивания;
* отображение границ отдельных отрезков нити;
* список материалов;
* экспорт.

Использовать функциональные преобразования состояния, immutable structures, map/filter/reduce и другие характерные возможности ClojureScript.

---

# 2. Docker и запуск проекта

Весь проект должен быть контейнеризирован.

Пользователь должен иметь возможность клонировать репозиторий и запустить систему одной командой:

```bash
docker compose up --build
```

После этого frontend и backend должны быть доступны без дополнительной настройки среды разработки.

Использовать Docker Compose минимум для следующих компонентов:

```text
frontend
backend
prolog
```

Предпочтительная архитектура:

```text
Browser
   ↓
ClojureScript frontend
   ↓ HTTP
Python FastAPI backend
   ↓
Prolog planning service
```

---

## 2.1. Backend container

Отдельный Docker image для Python backend.

Он должен содержать:

* Python;
* все Python-зависимости;
* FastAPI;
* OpenCV;
* Pillow;
* NumPy;
* библиотеки обработки изображения.

Пример структуры:

```text
backend/
├── Dockerfile
├── requirements.txt / pyproject.toml
└── app/
```

Запуск внутри контейнера:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 2.2. Prolog container

SWI-Prolog должен работать в отдельном контейнере.

Не требовать установки SWI-Prolog на машине пользователя.

Структура:

```text
prolog/
├── Dockerfile
├── movement.pl
├── methods.pl
├── thread.pl
├── planner.pl
└── expert_rules.pl
```

Предпочтительно сделать небольшой HTTP API вокруг Prolog.

Например:

```text
POST /plan
```

Вход:

```json
{
  "region": "...",
  "thread_length_mm": 500,
  "canvas_count": 14
}
```

Выход:

```json
{
  "method": "danish",
  "segments": [],
  "cost": 123.5
}
```

Можно использовать HTTP-возможности SWI-Prolog.

Python backend должен обращаться к сервису по Docker Compose service name:

```text
http://prolog:8080
```

Не использовать `localhost` для межконтейнерного взаимодействия.

---

## 2.3. Frontend container

ClojureScript frontend также должен запускаться в отдельном контейнере.

Контейнер должен:

* устанавливать зависимости;
* собирать ClojureScript;
* запускать dev server в development-режиме;
* поддерживать production build.

Структура:

```text
frontend/
├── Dockerfile
├── shadow-cljs.edn
├── deps.edn / package.json
└── src/
```

Можно использовать shadow-cljs.

Frontend должен обращаться к backend через корректно настроенный API URL.

---

## 2.4. Docker Compose

В корне проекта должен находиться:

```text
docker-compose.yml
```

или:

```text
compose.yml
```

Пример сервисов:

```yaml
services:
  backend:
    build: ./backend
    depends_on:
      - prolog

  prolog:
    build: ./prolog

  frontend:
    build: ./frontend
    depends_on:
      - backend
```

Настроить:

* внутреннюю Docker network;
* health checks;
* зависимости сервисов;
* environment variables;
* проброс нужных портов;
* volumes для development-режима.

---

## 2.5. Конфигурация

Не хардкодить адреса сервисов.

Использовать environment variables.

Например:

```text
PROLOG_URL=http://prolog:8080
BACKEND_PORT=8000
```

Для frontend предусмотреть API base URL.

Добавить:

```text
.env.example
```

с документированными параметрами.

Проект должен иметь рабочие значения по умолчанию, чтобы обычный запуск не требовал создания `.env`.

---

## 2.6. Development и production режимы

Желательно предусмотреть два сценария.

Development:

```bash
docker compose up --build
```

С:

* hot reload backend;
* hot reload frontend;
* подключенными source volumes.

Production:

```bash
docker compose -f compose.yml -f compose.prod.yml up --build
```

Production frontend можно собирать в статические файлы и отдавать через nginx.

Production-режим является желательным, но development Docker Compose обязателен.

---

## 2.7. Docker health checks

Добавить health endpoints.

Backend:

```text
GET /health
```

Prolog:

```text
GET /health
```

Docker Compose должен использовать health checks, чтобы backend не начинал обращаться к Prolog до того, как тот готов принимать запросы.

---

## 2.8. Тесты через Docker

Все тесты должны запускаться без установки локальных зависимостей.

Предусмотреть команды вроде:

```bash
docker compose run --rm backend pytest
```

```bash
docker compose run --rm prolog swipl -q -g run_tests -t halt tests.pl
```

Для frontend:

```bash
docker compose run --rm frontend npm test
```

или соответствующую ClojureScript-команду.

Желательно добавить общий скрипт:

```bash
./scripts/test.sh
```

или Makefile:

```bash
make test
```

который запускает все тесты внутри контейнеров.

---

# 3. Модель данных

Сразу определить внутреннее представление схемы.

Каждая клетка:

```text
Stitch {
    x
    y
    primary_color
    secondary_color | null
    stitch_type
    region_id
    importance
}
```

`stitch_type`:

```text
FULL
HALF_FORWARD
HALF_BACKWARD
```

Смешанный цвет:

```text
primary_color = DMC_310
secondary_color = DMC_317
```

Backstitch хранить отдельно как набор сегментов:

```text
BackstitchSegment {
    from_x
    from_y
    to_x
    to_y
    color
}
```

Участок одного цвета:

```text
Region {
    id
    stitches[]
    color
    bounding_box
}
```

План вышивания:

```text
ThreadPlan {
    color
    secondary_color | null
    method
    segments[]
}
```

Отдельный отрезок нити:

```text
ThreadSegment {
    stitches[]
    start
    end
    estimated_length
    route
}
```

---

# 4. Палитры нитей

Добавить реальные таблицы цветов хотя бы для:

* DMC;
* Anchor.

Для каждого цвета хранить:

```text
id
name
RGB
Lab
```

Основное сравнение цветов выполнять в CIELAB.

Использовать Delta E, предпочтительно CIEDE2000.

Не сопоставлять цвета только по евклидовому расстоянию RGB.

---

# 5. Этап обработки изображения

## 5.1. Входные параметры

Минимально пользователь задаёт:

* изображение;
* ширину или высоту вышивки;
* единицу: крестики или сантиметры;
* fabric count;
* палитру нитей;
* максимальное количество цветов;
* разрешены ли blends;
* разрешён ли half-cross;
* разрешён ли backstitch;
* длину исходного отрезка мулине;
* количество рабочих нитей.

Предусмотреть разумные значения по умолчанию.

---

# 6. Масштабирование изображения

Нельзя ограничиваться обычным resize.

Необходимо сравнить несколько вариантов уменьшения:

* nearest neighbour;
* bilinear/bicubic;
* Lanczos;
* area resampling;
* edge-aware вариант.

После уменьшения изображение должно сохранять основные объекты и контуры.

Реализовать минимум один механизм сохранения значимых элементов.

Например:

1. определить границы объектов;
2. увеличить вес пикселей около сильных границ;
3. учитывать их при последующей квантизации.

Для MVP допускается Lanczos + последующая edge-aware обработка.

---

# 7. Цветовая квантизация

Ограничить исходное изображение заданным числом цветов.

Исследовать:

* k-means в Lab;
* median cut;
* готовые алгоритмы Pillow.

Выбрать один основной метод.

Квантизацию желательно выполнять в Lab.

После этого каждый полученный цвет сопоставить ближайшему реальному цвету выбранной палитры нитей.

---

# 8. Confetti reduction

Это отдельный обязательный алгоритмический этап.

После сопоставления цветов найти:

* одиночные клетки;
* очень маленькие компоненты;
* узкие разрозненные участки.

Использовать connected components.

Для небольшого компонента рассмотреть замену его цвета на один из цветов соседей.

Стоимость замены должна учитывать:

```text
color_error
+
fragmentation_penalty
+
importance_penalty
```

Не удалять небольшую область, если она относится к важному контрастному элементу.

Ввести параметр минимального размера компонента.

---

# 9. Цветовые акценты

Попытаться сохранить значимые детали объекта.

Реализовать хотя бы базовый вариант:

1. построить edge map;
2. определить области высокого локального контраста;
3. пометить такие клетки повышенным `importance`;
4. при confetti reduction сложнее заменять их цвет;
5. на наиболее значимых границах при необходимости добавить backstitch.

---

# 10. Half-cross

Добавить half-cross как дополнительный способ приблизить цвет или форму.

Использовать его преимущественно:

* на границах объектов;
* для сглаживания диагональных линий;
* для менее плотных участков.

Для каждого half-cross хранить направление.

---

# 11. Blended colors

Реализовать смешивание двух цветов нитей.

Предварительно вычислить виртуальную палитру допустимых пар:

```text
blend(A, B)
```

Для каждого целевого цвета сравнить:

* ближайший одиночный цвет;
* лучший blend двух цветов.

Использовать blend только если он достаточно уменьшает Delta E.

Ограничить количество blend-комбинаций.

---

# 12. Выбор канвы

Создать список поддерживаемых:

* цветов канвы;
* fabric count.

Автоматический выбор цвета канвы выполнить через функцию оценки контраста и соответствия фону.

Пользователь должен иметь возможность изменить выбор вручную.

---

# 13. Backstitch

Автоматически добавлять backstitch на значимые границы.

Использовать:

* edge map;
* границы между сильно различающимися областями;
* importance map.

Не обводить каждую клетку.

После генерации упрощать линии.

---

# 14. Сегментация схемы на участки

После визуальной обработки разбить каждый цвет на connected components.

Каждый связный одноцветный участок становится отдельной задачей планирования.

Не отправлять всю картину целиком в Prolog.

---

# 15. Представление задачи в Prolog

Для каждого региона генерировать факты примерно такого вида:

```prolog
stitch(s1, 0, 0, full).
stitch(s2, 1, 0, full).
stitch(s3, 2, 0, full).

adjacent(s1, s2, horizontal).
adjacent(s2, s3, horizontal).

thread_length(500).
tail_length(60).
canvas_count(14).
```

Единицы длины внутри Prolog должны быть одинаковыми, например миллиметры.

---

# 16. Правила переходов в Prolog

Приоритет:

```text
горизонтальный соседний
вертикальный соседний
```

Допустимый, но менее предпочтительный:

```text
диагональный переход на одну клетку
```

Запрещённый:

```text
диагональный переход более чем на одну клетку
```

Для перехода определять:

```text
allowed
cost
thread_consumption
```

---

# 17. English, Danish и mixed method

Prolog должен выбирать способ прохождения участка.

Danish предпочтителен для длинных прямых рядов.

English подходит для:

* одиночных крестиков;
* коротких нерегулярных участков;
* случаев, где возврат Danish создаёт неудобный маршрут.

Mixed method может комбинировать оба подхода.

Использовать оценку стоимости вариантов.

---

# 18. Модель физического расхода нити

Из fabric count получить физический шаг:

```text
cell_size = 25.4 mm / count
```

Учитывать:

* диагонали;
* переходы по изнанке;
* возврат Danish;
* закрепление начала;
* закрепление конца;
* хвост длиной `needle_length + 1–2 cm`.

Формулы вынести в отдельный модуль и покрыть тестами.

---

# 19. Разбиение на отрезки нити

Учитывать складывание нити пополам или на три части.

При построении маршрута контролировать оставшуюся длину.

Если следующего стежка уже нельзя безопасно выполнить:

1. закончить текущий ThreadSegment;
2. оставить запас на завершение;
3. начать новый ThreadSegment.

---

# 20. Оптимизация маршрута

Целевая функция должна учитывать:

```text
number_of_thread_segments
number_of_color_changes
travel_distance
diagonal_moves
empty-space travels
method switches
```

Коэффициенты вынести в конфигурацию.

Для больших регионов применять эвристики:

* разбиение на строки;
* подрегионы;
* greedy;
* ограниченный backtracking.

---

# 21. Экспертные правила

Спроектировать Prolog так, чтобы новые критерии добавлялись без изменения Python-кода.

Например:

```text
prolog/
├── movement.pl
├── methods.pl
├── thread.pl
├── planner.pl
├── expert_rules.pl
└── tests/
```

---

# 22. API между Python и Prolog

Основной вариант взаимодействия:

```text
Python FastAPI
        ↓ HTTP/JSON
SWI-Prolog service
```

Формат ответа:

```json
{
  "method": "mixed",
  "segments": [
    {
      "stitches": ["s1", "s2", "s3"],
      "length_mm": 423
    }
  ]
}
```

---

# 23. Backend API

FastAPI.

Минимальные endpoint:

```text
POST /patterns
GET  /patterns/{id}
POST /patterns/{id}/plan
GET  /palettes
GET  /canvas
GET  /health
```

---

# 24. ClojureScript frontend

Главный экран:

```text
┌────────────────┬────────────────────┐
│ Original image │ Generated pattern  │
│                │                    │
└────────────────┴────────────────────┘

Palette: DMC
Size: 120 × 90
Fabric: Aida 14
Colors: 24

[x] blends
[x] half-cross
[x] backstitch

[Generate]
```

---

# 25. Интерактивная схема

Поддержать:

* zoom;
* pan;
* номера строк и столбцов;
* символы цветов;
* скрытие отдельных цветов;
* выделение выбранного цвета;
* backstitch;
* выбор региона.

---

# 26. Визуализация маршрута

При выборе участка показывать порядок:

```text
1 → 2 → 3 → 4
            ↓
8 ← 7 ← 6 ← 5
```

Показывать:

* текущую нить;
* оставшуюся длину;
* English/Danish/mixed;
* ThreadSegment;
* переходы по изнанке.

---

# 27. Материалы

Сформировать Bill of Materials:

```text
Canvas:
Aida 14, white
220 × 180 mm

Needle:
Tapestry needle №24

Threads:

DMC 310
1.8 m
1 skein
```

Для каждого цвета вычислять общий расход и число мотков.

---

# 28. Итоговая схема

Генерировать PDF или пригодный для печати HTML.

Включить:

* размер;
* physical dimensions;
* fabric count;
* сетку;
* линии каждые 10 клеток;
* символы;
* legend;
* цвета нитей;
* количество нитей;
* blends;
* backstitch;
* материалы.

---

# 29. Этапы реализации

## Этап 1

```text
Docker Compose
→ backend
→ frontend
→ Prolog
→ health checks
```

Сначала убедиться, что все три компонента запускаются одной командой и взаимодействуют между собой.

---

## Этап 2

```text
image
→ resize
→ quantization
→ DMC mapping
→ grid
→ UI
```

---

## Этап 3

Добавить:

* Lab;
* Delta E;
* confetti reduction;
* preservation of important edges.

---

## Этап 4

Prolog MVP:

* connected regions;
* факты;
* правила переходов;
* маршрут;
* English/Danish selection.

---

## Этап 5

Добавить физическую длину нити и ThreadSegment.

---

## Этап 6

Добавить оптимизацию маршрутов.

---

## Этап 7

Добавить:

* half-cross;
* blends;
* backstitch.

---

## Этап 8

Добавить:

* canvas selection;
* needle;
* thread estimation;
* skein count.

---

## Этап 9

Довести ClojureScript UI, экспорт и итоговую Docker-конфигурацию.

---

# 30. Тестирование

Unit tests:

* RGB → Lab;
* Delta E;
* nearest thread;
* blend selection;
* physical stitch length;
* connected components;
* confetti replacement;
* thread segmentation.

Prolog tests:

```text
XXXXX
```

```text
X
X
X
X
```

```text
XXX
  X
  X
```

Проверять:

* метод;
* маршрут;
* длинные диагонали;
* длину нити.

Все тесты должны запускаться внутри Docker.

---

# 31. Метрики

Визуальная часть:

* Delta E;
* SSIM;
* число цветов;
* число connected components;
* число confetti stitches.

Планирование:

* total thread length;
* number of thread segments;
* travel distance;
* diagonal moves;
* long jumps;
* method changes.

---

# 32. Структура репозитория

```text
project/
│
├── compose.yml
├── compose.prod.yml
├── .env.example
├── Makefile
│
├── backend/
│   ├── Dockerfile
│   ├── app/
│   └── tests/
│
├── prolog/
│   ├── Dockerfile
│   ├── movement.pl
│   ├── methods.pl
│   ├── thread.pl
│   ├── planner.pl
│   ├── expert_rules.pl
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── shadow-cljs.edn
│   └── src/
│
├── palettes/
│   ├── dmc.json
│   └── anchor.json
│
├── examples/
│
├── scripts/
│   └── test.sh
│
├── docs/
│   ├── architecture.md
│   ├── algorithms.md
│   ├── prolog.md
│   └── docker.md
│
└── README.md
```

---

# 33. README

README должен позволять запустить проект с нуля.

Минимальные инструкции:

```bash
git clone ...
cd ...
docker compose up --build
```

Указать:

* URL frontend;
* URL backend API;
* как остановить систему;
* как запустить тесты;
* как пересобрать контейнеры;
* основные environment variables.

---

# 34. Что обязательно должно работать перед сдачей

Проверить запуск на чистой машине, где установлен только:

* Docker;
* Docker Compose.

После:

```bash
docker compose up --build
```

должны автоматически запуститься:

```text
ClojureScript frontend
Python backend
SWI-Prolog
```

И пользователь должен иметь возможность полностью выполнить сценарий:

```text
upload image
→ configure pattern
→ generate
→ optimize
→ inspect stitching route
→ inspect materials
→ export pattern
```

без установки дополнительных языков или библиотек на хостовую систему.

---

# 35. Что показать преподавателю

Во время демонстрации:

1. запустить весь проект через `docker compose up`;
2. показать три работающих сервиса;
3. загрузить изображение;
4. получить схему;
5. показать Prolog-факты одного региона;
6. показать правила;
7. показать рассчитанный маршрут;
8. изменить одно экспертное правило;
9. повторно построить маршрут;
10. показать изменение результата;
11. показать использование ClojureScript на frontend;
12. показать расчёт материалов и экспорт.

---

# Итоговый критерий проекта

На входе пользователь предоставляет изображение и параметры.

На выходе система предоставляет:

1. визуальную схему вышивки;
2. реальные номера цветов нитей;
3. выбранную канву;
4. рекомендуемую иглу;
5. количество необходимых нитей;
6. blended colors;
7. full/half-cross;
8. backstitch;
9. порядок вышивания;
10. English/Danish/mixed;
11. разбиение по длине нити;
12. интерактивную визуализацию;
13. список материалов;
14. экспорт.

Весь проект должен быть воспроизводимо развёртываемым через Docker Compose и не зависеть от локально установленных Python, SWI-Prolog, ClojureScript или Node.js.
