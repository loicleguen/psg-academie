FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM alpine:latest
COPY --from=builder /app/dist /app/dist
CMD ["tail", "-f", "/dev/null"]
