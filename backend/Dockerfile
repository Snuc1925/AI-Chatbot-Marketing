FROM python:3.11-slim

WORKDIR /app/backend

# Build-time only proxy (used for pip install). Not persisted as ENV, so it
# never leaks into the running container - pass via docker-compose `build.args`,
# sourced from .env, empty/unset on machines that don't need a proxy.
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

COPY requirements.txt .
RUN if [ -n "$HTTP_PROXY" ]; then \
        pip install --no-cache-dir \
            --proxy "$HTTP_PROXY" \
            --trusted-host pypi.org \
            --trusted-host files.pythonhosted.org \
            --trusted-host pypi.python.org \
            -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
