FROM python:3.10.6-slim-bullseye

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install --yes --no-install-recommends procps ca-certificates \
    iproute2 git curl libpq-dev curl gnupg g++ locales

WORKDIR /app

COPY cogstack.py .
COPY pyproject.toml .

RUN pip install -e .

ENTRYPOINT ["uvicorn", "cogstack:app", "--host", "0.0.0.0", "--port", "8000"]

