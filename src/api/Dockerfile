# Cloud Run向けの本番実行用イメージ
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 依存解決にuvを利用
RUN pip install --no-cache-dir uv==0.9.21

# 依存解決に必要なファイルを先にコピーしてキャッシュ効率を上げる
COPY pyproject.toml uv.lock README.md ./
COPY stock ./stock/
COPY alembic ./alembic/

# 本番用依存のみインストール（/app/.venv に作成され、上の PATH で `python` から参照される）
RUN uv sync --frozen --no-dev

EXPOSE 8080

# Cloud RunはPORT環境変数を注入する
CMD ["sh", "-c", "uv run uvicorn stock.app:app --host 0.0.0.0 --port ${PORT:-8080} --log-level info"]
