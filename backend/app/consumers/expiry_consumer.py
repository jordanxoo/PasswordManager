import asyncio 
import logging
from datetime import datetime,timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.models import Vault,User
from app.publishers.notification_publisher import publish_expiry_reminder
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def check_expiring_passwords():
    # engine = create_async_engine(settings.DATABASE_URL)
    # async_session = sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)

    while True:
        await asyncio.sleep(86400)
        logger.info("Checking expiring passwords...")

        try:
            async with AsyncSessionLocal() as db:
                now = datetime.now()
                soon = now + timedelta(days=7)

                result = await db.execute(
                    select(Vault,User).join(User,Vault.user_id == User.id)
                    .where(Vault.expires_at.isnot(None))
                    .where(Vault.expires_at <= soon)
                    .where(Vault.expires_at > now)
                )
                entries = result.all()

                for vault,user in entries:
                    await publish_expiry_reminder(
                        email=user.email,
                        vault_name=vault.name,
                        expires_at=vault.expires_at.strftime("%Y-%m-%d")
                    )
                    logger.info("Expiry reminder sent for vault %s to %s",vault.name,user.email)

            
        except Exception as e:
            logger.error("Error checking expiring passwords: %s",e)

