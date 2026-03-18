FROM python:3.12-alpine

WORKDIR /app

# Dépendances système : pg_dump (sauvegarde), curl (healthcheck),
# fonts-liberation + pango (WeasyPrint PDF avec typographie correcte)
# gcc/musl-dev nécessaires pour compiler certaines dépendances Python sur Alpine
RUN apk add --no-cache \
        postgresql16-client curl \
        font-liberation pango \
        gcc musl-dev libffi-dev

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Créer les dossiers runtime AVANT de changer d'utilisateur
RUN mkdir -p /app/uploads /app/factures /backups/kahlo

# Utilisateur non-root pour la sécurité
RUN adduser -D appuser && \
    chown -R appuser:appuser /app/uploads /app/factures /backups/kahlo
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
