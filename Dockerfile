FROM python:3.13.11-slim

WORKDIR /code

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# pyproject.tomlとuv.lockをコピー
COPY pyproject.toml uv.lock* ./

# システム環境に直接インストール
ENV UV_PROJECT_ENVIRONMENT=/usr/local

RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*
    
RUN uv sync --frozen --extra batch

COPY . .

CMD ["uv", "run", "--frozen" , "manage.py", "runserver", "0.0.0.0", "--port", "8000"]
