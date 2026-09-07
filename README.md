# Нить — конструктор схем вышивки

«Нить» преобразует изображение в схему для вышивки крестом, сопоставляет цвета с палитрами DMC или Anchor, очищает мелкие разрозненные участки и строит маршрут нити с помощью SWI-Prolog. Интерфейс написан на ClojureScript/Reagent, обработка изображения — на Python/FastAPI.

## Запуск

Нужны только Docker и Docker Compose.

```bash
git clone <адрес-репозитория>
cd SummerTask
docker compose up --build
```

После запуска доступны:

- интерфейс — <http://localhost:3000>;
- API и Swagger — <http://localhost:8000/docs>;
- Prolog API — <http://localhost:8080/health>.

Остановить сервисы:

```bash
docker compose down
```

Production-сборка интерфейса с nginx:

```bash
docker compose -f compose.yml -f compose.prod.yml up --build
```

## Рабочий сценарий

1. Откройте интерфейс и выберите PNG, JPEG или WebP.
2. Задайте размер, канву, палитру и число цветов.
3. Включите blends, полукрест и backstitch при необходимости.
4. Нажмите «Создать схему».
5. Выберите клетку или цвет, затем откройте вкладку «Маршрут» и запустите оптимизацию.
6. Просмотрите отрезки нити, материалы и факты Prolog выбранного участка.
7. Откройте печатную схему и сохраните её в PDF средствами браузера.

Схема поддерживает масштабирование, прокрутку с перетаскиванием, скрытие цветовых слоёв, выделение участка, backstitch и пошаговый просмотр маршрута.

## Проверки

Все проверки выполняются внутри контейнеров:

```bash
make test
```

Отдельные команды:

```bash
docker compose run --rm backend pytest -q
docker compose run --rm prolog swipl -q -s tests/tests.pl -g run_tests -t halt
docker compose run --rm frontend npm test
```

## Настройки

Рабочие значения уже заданы. Для изменения скопируйте `.env.example` в `.env`.

| Переменная | По умолчанию | Назначение |
|---|---:|---|
| `PROLOG_URL` | `http://prolog:8080` | адрес планировщика внутри Docker network |
| `BACKEND_PORT` | `8000` | порт FastAPI на хосте |
| `FRONTEND_PORT` | `3000` | порт интерфейса на хосте |
| `PUBLIC_API_URL` | `http://localhost:8000` | публичный адрес API для браузера |
| `MAX_UPLOAD_MB` | `12` | максимальный размер изображения |

Описание компонентов находится в каталоге [`docs`](docs/architecture.md).

