#!/usr/bin/env sh
set -eu
npx shadow-cljs watch app &
watch_pid=$!
trap 'kill "$watch_pid" 2>/dev/null || true' EXIT INT TERM
exec node /app/dev-server.mjs

