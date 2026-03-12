# Mise à jour du logiciel depuis l'interface admin

## Stratégie retenue

Kahlo-ERP est déployé en **Docker Compose** avec des volumes persistants (`postgres_data`, `uploads_data`, etc.).
La stratégie la plus sûre est donc une approche **C (conteneurs)**:

1. vérifier la dernière release GitHub,
2. basculer le code sur le tag cible,
3. relancer uniquement les services applicatifs avec `docker compose up -d --build ...`,
4. ne jamais utiliser `docker compose down -v`.

Cette stratégie préserve la base PostgreSQL, les volumes et le fichier `.env`.

## Ce que fait la fonctionnalité

Dans **Paramètres > Mise à jour** (admin uniquement):

- affiche la version locale et la dernière release GitHub,
- indique l'état: à jour / mise à jour disponible / vérification impossible,
- permet de vérifier les mises à jour,
- permet de lancer la mise à jour.

Le backend conserve:

- un log simplifié orienté utilisateur,
- des logs techniques,
- le dernier résultat dans `/backups/kahlo/system_update_status.json`.

## Mode automatique vs semi-automatique

Par défaut, l'auto-update est désactivé pour éviter un faux sentiment de sécurité.

- `KAHLO_AUTO_UPDATE_ENABLED=true` active l'exécution automatique (si `git`, `docker`, droits repo et `docker-compose.yml` sont disponibles côté runtime).
- Sinon, l'API renvoie un mode **semi-automatique** avec les commandes exactes à exécuter sur l'hôte.

## Préservation des données et garde-fous

- Refus de lancer une seconde mise à jour si une est déjà en cours.
- Vérifications préalables: dépôt Git, commande `git`, commande `docker`, droits d'écriture.
- Aucun effacement de `.env`.
- Aucune suppression de volumes.
- Aucune suppression de base PostgreSQL.

## Limites connues

- Si le backend tourne dans un conteneur sans accès au dépôt hôte et sans Docker CLI/socket, l'auto-update ne peut pas être exécuté de manière fiable.
- Dans ce cas, le mode semi-automatique est volontairement utilisé et affiché clairement dans l'interface.
