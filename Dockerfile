FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# La configuració i els secrets es munten en temps d'execució:
#   - config.yaml  -> /app/config.yaml  (ro)
#   - .env         -> variables d'entorn
#   - state/       -> /app/state        (volum persistent)
RUN mkdir -p /app/state

CMD ["python", "-m", "src.main"]
