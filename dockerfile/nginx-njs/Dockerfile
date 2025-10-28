# docker run -d --name nginx-njs -p 8080:8080 -v /full/path/on/host/nginx.conf:/etc/nginx/nginx.conf:ro -v /full/path/on/host/static:/usr/share/nginx/html:ro -v /full/path/on/host/script.js:/etc/nginx/njs/script.js:ro ghcr.io/0x2196f3/nginx-njs:latest

FROM nginx:latest

RUN apt-get update && \
    apt-get install -y nginx-module-njs && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
