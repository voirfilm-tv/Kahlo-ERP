-- KAHLO CAFÉ — Initialisation PostgreSQL
-- Exécuté au premier démarrage de PostgreSQL (avant FastAPI)
--
-- NOTE : Les tables sont créées par SQLAlchemy au démarrage de FastAPI.
-- Ce script ne contient que des opérations idempotentes qui seront
-- ré-exécutées sans erreur quand les tables existent.

-- Index sur les champs fréquemment recherchés
-- (CREATE INDEX IF NOT EXISTS est safe même si la table n'existe pas encore
--  sur PostgreSQL 16+ ; sur les versions antérieures ces lignes seront
--  ignorées sans erreur grâce au IF NOT EXISTS)
DO $$
BEGIN
    -- Ces index seront créés lors du premier redémarrage du conteneur
    -- après que FastAPI ait créé les tables
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lots') THEN
        CREATE INDEX IF NOT EXISTS idx_lots_origine ON lots(origine);
        CREATE INDEX IF NOT EXISTS idx_lots_actif ON lots(actif);
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'commandes') THEN
        CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut);
        CREATE INDEX IF NOT EXISTS idx_commandes_date ON commandes(date_commande);
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'clients') THEN
        CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'evenements') THEN
        CREATE INDEX IF NOT EXISTS idx_evenements_date ON evenements(date_debut);
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'marches') THEN
        CREATE INDEX IF NOT EXISTS idx_marches_date ON marches(date);
    END IF;
END $$;
