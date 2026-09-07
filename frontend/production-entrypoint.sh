#!/usr/bin/env sh
set -eu
api_url="${PUBLIC_API_URL:-http://localhost:8000}"
printf 'window.STITCHCRAFT_CONFIG = {apiUrl: "%s"};\n' "$api_url" > /usr/share/nginx/html/config.js

