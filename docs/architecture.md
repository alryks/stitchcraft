# Архитектура

```text
Browser
  │ image + options / pattern JSON
  ▼
ClojureScript + Reagent :3000
  │ HTTP
  ▼
FastAPI :8000
  ├─ image processing, palettes, regions, materials, export
  │ HTTP/JSON for each connected region
  ▼
SWI-Prolog :8080
  └─ movement rules, method choice, thread segments, route cost
```

Compose создаёт три независимых сервиса. Backend ждёт успешный health check Prolog, frontend — backend. Адрес Prolog берётся из `PROLOG_URL`; браузер получает `PUBLIC_API_URL` через runtime-файл `config.js`.

Backend хранит созданные схемы в памяти. Это подходит для учебной демонстрации и не требует базы данных. Перезапуск контейнера очищает схемы.

## Модель схемы

Каждая клетка содержит координаты, основной и дополнительный цвет, тип стежка, важность, символ и идентификатор связного участка. Backstitch хранится отдельными отрезками. План региона состоит из метода шитья и одного или нескольких отрезков нити с маршрутом и оценкой длины.

