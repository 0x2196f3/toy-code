FROM nginx:latest

RUN apt-get update && \
    apt-get install -y nginx-module-njs && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]