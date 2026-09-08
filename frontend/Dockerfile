# frontend — Vite build + nginx (proxies /ingest-api → backend1, /chat-api → backend2)
FROM node:22-bookworm-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.ts tsconfig*.json ./
COPY public ./public
COPY src ./src

# Relative /ingest-api and /chat-api — nginx rewrites in runtime image
ENV VITE_INGEST_API= \
    VITE_CHAT_API= \
    VITE_DEFAULT_TENANT=sdnu-demo

RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
