/**
 * KAHLO CAFÉ — Hook useOfflineSync
 * Détecte la connectivité et gère la queue offline
 */

import { useState, useEffect, useCallback } from "react";
import { lancerSync, getSyncStatus } from "../services/api";

export function useOfflineSync() {
  const [online, setOnline] = useState(navigator.onLine);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const [queueSize, setQueueSize] = useState(0);
  const [syncResult, setSyncResult] = useState(null);

  // Écouter les changements de connexion
  useEffect(() => {
    const handleOnline = async () => {
      setOnline(true);
      // Sync automatique au retour de connexion
      if (queueSize > 0) {
        await triggerSync();
      }
    };

    const handleOffline = () => setOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [queueSize]);

  // Vérifier la queue toutes les 30s
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const status = await getSyncStatus();
        setQueueSize(status.queue_size || 0);
      } catch {
        // Backend unreachable — mode offline
        setOnline(false);
      }
    }, 30_000);

    return () => clearInterval(interval);
  }, []);

  const triggerSync = useCallback(async () => {
    if (!online || syncing) return;
    setSyncing(true);
    try {
      const result = await lancerSync();
      setSyncResult(result);
      setQueueSize(0);
      setLastSync(new Date());
    } catch (e) {
      console.error("Erreur sync:", e);
    } finally {
      setSyncing(false);
    }
  }, [online, syncing]);

  return { online, syncing, lastSync, queueSize, syncResult, triggerSync };
}
