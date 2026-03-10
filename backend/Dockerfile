FROM python:3.12-slim

WORKDIR /app

# Dépendances système : pg_dump (sauvegarde), curl (healthcheck),
# fonts-liberation + pango (WeasyPrint PDF avec typographie correcte)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-client curl \
        fonts-liberation libpango-1.0-0 libpangoft2-1.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Créer les dossiers runtime AVANT de changer d'utilisateur
RUN mkdir -p /app/uploads /app/factures /backups/kahlo

# Utilisateur non-root pour la sécurité
RUN adduser --disabled-password --no-create-home appuser && \
    chown -R appuser:appuser /app/uploads /app/factures /backups/kahlo
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
