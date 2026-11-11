FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_USE_MOCK_DATA=false
ARG VITE_APP_NAME=AttributionIQ

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_USE_MOCK_DATA=${VITE_USE_MOCK_DATA} \
    VITE_APP_NAME=${VITE_APP_NAME}

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

