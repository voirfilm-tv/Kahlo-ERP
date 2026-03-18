FROM nginx:1.27-alpine

# Supprimer la config par défaut
RUN rm -f /etc/nginx/conf.d/default.conf

# Copier la config directement dans l'image (élimine les bind mounts)
COPY nginx.conf /etc/nginx/nginx.conf

# Préparer le dossier SSL (les certs seront montés en volume si nécessaire)
RUN mkdir -p /etc/nginx/ssl

EXPOSE 80 443
