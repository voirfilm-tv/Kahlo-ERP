FROM python:3.12-alpine

WORKDIR /app

# Dépendances système : pg_dump (sauvegarde), curl (healthcheck),
# fonts-liberation + pango (WeasyPrint PDF avec typographie correcte)
# gcc/musl-dev nécessaires pour compiler certaines dépendances Python sur Alpine
RUN apk add --no-cache \
        postgresql16-client curl \
        font-liberation pango \
        gcc musl-dev libffi-dev \
        su-exec

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Dossiers runtime (config persistante, uploads, factures, backups)
RUN mkdir -p /app/data /app/uploads /app/factures /backups/kahlo

# Utilisateur non-root pour la sécurité. L'entrypoint démarre en root
# UNIQUEMENT pour corriger les permissions des volumes (Docker les crée
# en root), puis exécute l'app via su-exec en tant qu'appuser.
RUN adduser -D appuser && \
    chown -R appuser:appuser /app/data /app/uploads /app/factures /backups/kahlo

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
