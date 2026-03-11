"""KAHLO CAFÉ — Service Stock"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Lot
import logging

logger = logging.getLogger(__name__)


async def decrementer_stock(db: AsyncSession, lot_id: int, quantite_kg: float):
    """Décrémente le stock d'un lot (appelé par webhook SumUp et sync offline)"""
    if quantite_kg <= 0:
        raise ValueError(f"quantite_kg doit être > 0 (reçu: {quantite_kg})")
    result = await db.execute(select(Lot).where(Lot.id == lot_id).with_for_update())
    lot = result.scalar_one_or_none()
    if not lot:
        logger.warning(f"Lot {lot_id} introuvable pour décrémentation")
        return

    ancien = lot.stock_kg
    lot.stock_kg = max(0, lot.stock_kg - quantite_kg)
    logger.info(f"Stock {lot.origine}: {ancien}kg → {lot.stock_kg}kg (-{quantite_kg}kg)")

    if lot.est_critique:
        logger.warning(f"⚠ Stock critique atteint: {lot.origine} ({lot.stock_kg}kg)")
