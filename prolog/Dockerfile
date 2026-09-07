FROM swipl:9.2.9
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/*
COPY . .
EXPOSE 8080
CMD ["swipl", "-q", "-s", "server.pl", "-g", "server(8080)"]

