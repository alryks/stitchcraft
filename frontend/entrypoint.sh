#!/usr/bin/env sh
set -eu
api_url="${PUBLIC_API_URL:-http://localhost:8000}"
mkdir -p /app/public/fonts
cp /app/node_modules/@fontsource/manrope/files/manrope-cyrillic-400-normal.woff2 /app/public/fonts/
cp /app/node_modules/@fontsource/manrope/files/manrope-cyrillic-600-normal.woff2 /app/public/fonts/
cp /app/node_modules/@fontsource/manrope/files/manrope-cyrillic-700-normal.woff2 /app/public/fonts/
cp /app/node_modules/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-500-normal.woff2 /app/public/fonts/
printf 'window.STITCHCRAFT_CONFIG = {apiUrl: "%s"};\n' "$api_url" > /app/public/config.js
exec "$@"
