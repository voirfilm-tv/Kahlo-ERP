-- KAHLO CAFÉ — Données initiales
-- Exécuté au premier démarrage de PostgreSQL

-- Fournisseurs de départ
INSERT INTO fournisseurs (nom, email, pays, delai_moyen, score) VALUES
  ('Café Imports Lyon', 'contact@cafeimports-lyon.fr', 'France', 5, 4.5),
  ('Origine Direct', 'hello@origine-direct.com', 'France', 7, 4.8),
  ('Terra Coffee', 'pro@terracoffee.eu', 'Belgique', 10, 4.2)
ON CONFLICT DO NOTHING;

-- Index sur les champs fréquemment recherchés
CREATE INDEX IF NOT EXISTS idx_lots_origine ON lots(origine);
CREATE INDEX IF NOT EXISTS idx_lots_actif ON lots(actif);
CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut);
CREATE INDEX IF NOT EXISTS idx_commandes_date ON commandes(date_commande);
CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);
CREATE INDEX IF NOT EXISTS idx_evenements_date ON evenements(date_debut);
CREATE INDEX IF NOT EXISTS idx_marches_date ON marches(date);
