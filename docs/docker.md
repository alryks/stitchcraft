# Docker

Development-конфигурация монтирует исходники backend, frontend и Prolog. Uvicorn и shadow-cljs следят за изменениями. Health checks используют `/health`; Compose запускает зависимые сервисы после готовности предыдущего.

Production overlay отключает hot reload, собирает оптимизированный ClojureScript и отдаёт статику через nginx. Значения переменных документированы в `.env.example` и имеют рабочие defaults.

Для полной очистки контейнеров проекта выполните:

```bash
docker compose down --remove-orphans
```

