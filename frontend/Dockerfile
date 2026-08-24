FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./

RUN node --version && npm --version
RUN npm ci --legacy-peer-deps --no-audit --no-fund --verbose

COPY . ./

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
