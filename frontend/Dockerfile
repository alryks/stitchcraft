FROM node:20-bookworm-slim AS development
WORKDIR /app
COPY package.json shadow-cljs.edn ./
RUN npm install
COPY . .
RUN mkdir -p public/fonts \
    && cp node_modules/@fontsource/manrope/files/manrope-cyrillic-400-normal.woff2 public/fonts/ \
    && cp node_modules/@fontsource/manrope/files/manrope-cyrillic-600-normal.woff2 public/fonts/ \
    && cp node_modules/@fontsource/manrope/files/manrope-cyrillic-700-normal.woff2 public/fonts/ \
    && cp node_modules/@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-500-normal.woff2 public/fonts/
RUN chmod +x /app/entrypoint.sh
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
