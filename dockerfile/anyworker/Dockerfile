# run /app/_worker.js
# sudo docker run -d --name=test -p 8080:8080 -v ./myapp:/app ghcr.io/0x2196f3/anyworker:latest

FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  ca-certificates \
  unzip \
  && rm -rf /var/lib/apt/lists/* && npm install -g wrangler@4

WORKDIR /app

EXPOSE 8080

CMD ["npx", "wrangler", "dev", "--port", "8080", "--ip", "0.0.0.0", "--no-bundle", "/app/_worker.js"]
