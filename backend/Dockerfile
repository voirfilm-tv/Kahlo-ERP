FROM python:3.12-slim

WORKDIR /app

# Dépendances Python (psycopg2-binary ne nécessite pas libpq-dev)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Démarrage avec uvicorn (rechargement auto en dev)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
