# python3.11のイメージをダウンロード
FROM python:3.11-buster

# pythonの出力表示をDocker用に調整
ENV PYTHONUNBUFFERED=1

WORKDIR /src

# pipを使ってuvをインストール
RUN pip install uv

# 必要なファイルのみをコピー
COPY pyproject.toml uv.lock ./
COPY stock ./stock/
COPY alembic ./alembic/
COPY README.md ./

# uvでライブラリをインストール
RUN if [ -f pyproject.toml ]; then uv sync; fi

# uvicornのサーバーを立ち上げる
ENTRYPOINT ["uv", "run", "uvicorn", "stock.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]
