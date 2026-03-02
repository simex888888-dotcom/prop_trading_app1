FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_BOT_USERNAME
ARG VITE_BUILD_TIME=unknown

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_BOT_USERNAME=$VITE_BOT_USERNAME
ENV VITE_BUILD_TIME=$VITE_BUILD_TIME

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
