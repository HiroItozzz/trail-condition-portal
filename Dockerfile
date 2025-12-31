FROM python:3.13-slim

WORKDIR /workspace

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# pyproject.tomlとuv.lockをコピー
COPY pyproject.toml uv.lock* ./

# システム環境に直接インストール
RUN uv sync --dev --frozen

COPY . .

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
