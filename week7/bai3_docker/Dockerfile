FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt pyproject.toml ./
COPY product_api ./product_api
COPY bai1_product_api ./bai1_product_api
COPY bai2_orders ./bai2_orders
COPY bai4_healthcheck ./bai4_healthcheck
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps .

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && chown app:app /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app bai3_docker/wsgi.py bai3_docker/gunicorn.conf.py bai3_docker/entrypoint.sh ./
USER app
EXPOSE 5000
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
