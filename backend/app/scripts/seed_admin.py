"""Seed the default admin tenant and user on first startup."""
import asyncio
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.auth import hash_password
from app.models.tenant import Tenant
from app.models.user import User


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.email == settings.FIRST_ADMIN_EMAIL))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Admin user already exists: {settings.FIRST_ADMIN_EMAIL}")
            return

        # Create default tenant
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            name="Default Organization",
            slug="default-org",
            plan="enterprise",
        )
        db.add(tenant)

        # Create admin user
        admin = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=settings.FIRST_ADMIN_EMAIL,
            full_name=settings.FIRST_ADMIN_NAME,
            hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"Admin user created: {settings.FIRST_ADMIN_EMAIL}")
        print(f"Default tenant created: {tenant.name}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
