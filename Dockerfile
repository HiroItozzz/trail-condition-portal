FROM python:3.13-slim

WORKDIR /code

# Poetryをインストール
RUN pip install --no-cache-dir poetry

# pyproject.tomlとpoetry.lockをコピー
COPY pyproject.toml poetry.lock* ./

# venvを作らずに依存関係をインストール
RUN poetry config virtualenvs.create false && \
    poetry install --no-root

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]