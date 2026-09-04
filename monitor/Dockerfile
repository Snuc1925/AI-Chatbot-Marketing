FROM node:20-alpine

WORKDIR /app

# Build-time only proxy (used for npm install). Not persisted as ENV, so it
# never leaks into the running container - pass via docker-compose `build.args`,
# sourced from .env, empty/unset on machines that don't need a proxy.
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

COPY package*.json ./
RUN if [ -n "$HTTP_PROXY" ]; then \
        npm config set proxy "$HTTP_PROXY" && \
        npm config set https-proxy "$HTTPS_PROXY" && \
        npm config set strict-ssl false; \
    fi && \
    npm install

COPY . .

EXPOSE 3001

CMD ["npm", "run", "dev"]
