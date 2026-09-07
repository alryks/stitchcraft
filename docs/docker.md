# Docker

Development-конфигурация монтирует исходники backend, frontend и Prolog. Uvicorn и shadow-cljs следят за изменениями. Health checks используют `/health`; Compose запускает зависимые сервисы после готовности предыдущего.

Production overlay отключает hot reload, собирает оптимизированный ClojureScript и отдаёт статику через nginx. Значения переменных документированы в `.env.example` и имеют рабочие defaults.

## Деплой за Traefik

Для VPS с общей внешней сетью Traefik используется дополнительный overlay:

```bash
docker network create proxy  # выполнить один раз, если сети ещё нет
docker compose \
  -f compose.yml \
  -f compose.prod.yml \
  -f compose.traefik.yml \
  up -d --build
```

Перед запуском задайте в `.env`:

```text
STITCHCRAFT_HOST=stitch.example.com
STITCHCRAFT_API_HOST=stitch-api.example.com
PUBLIC_API_URL=https://stitch-api.example.com
```

Frontend и backend подключаются к сети `proxy` и получают HTTPS-маршруты через Traefik. Prolog остаётся доступен только внутри Docker-сети. Host-порты отключены, поэтому сервис не конфликтует с другими приложениями на VPS.

Для полной очистки контейнеров проекта выполните:

```bash
docker compose down --remove-orphans
```
