# ---- 阶段 1: 安装依赖 ----
FROM python:3.13-alpine AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- 阶段 2: 运行环境 ----
FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /install /usr/local

COPY *.py ./
COPY routes/ routes/
COPY adapters/ adapters/
COPY utils/ utils/
COPY static/ static/

RUN addgroup -S appuser \
    && adduser -S -G appuser -u 1000 appuser \
    && mkdir -p /app/data/logs \
    && chown -R appuser:appuser /app

COPY entrypoint.sh /app/entrypoint.sh

EXPOSE 3029

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "start.py"]
