FROM node:20-bookworm-slim AS development
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless wget && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json ./
RUN npm ci
COPY shadow-cljs.edn ./
COPY . .
RUN mkdir -p public/fonts \
    && cp node_modules/@fontsource/manrope/files/manrope-cyrillic-400-normal.woff2 public/fonts/ \
    && cp node_modules/@fontsource/manrope/files/manrope-cyrillic-600-normal.woff2 public/fonts/ \
    && cp node_modules/@fontsource/manrope/files/manrope-cyrillic-700-normal.woff2 public/fonts/ \
    && cp node_modules/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-500-normal.woff2 public/fonts/
RUN npx shadow-cljs compile app
RUN chmod +x /app/entrypoint.sh /app/dev.sh
EXPOSE 3000 9630
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["npx", "shadow-cljs", "watch", "app"]

FROM development AS builder
RUN npx shadow-cljs release app

FROM nginx:1.27-alpine AS production
COPY --from=builder /app/public /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY production-entrypoint.sh /docker-entrypoint.d/40-stitchcraft-config.sh
RUN chmod +x /docker-entrypoint.d/40-stitchcraft-config.sh
EXPOSE 80
